import sys
import os
import networkx as nx
import numpy as np
from typing import List, Dict, Any, Tuple

from sentence_transformers import SentenceTransformer, util

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.storage import load_graph_as_networkx
from backend.llm import rank_recommendations_with_gemini
from backend.graph_ops import (
    get_or_compute_embeddings,
    cosine_similarity_scores,
    graph_heuristic_scores,
    combine_scores
)

# Lazy-loaded sentence transformer for profile-aware reranking
_st_model = None


def _get_st_model():
    global _st_model
    if _st_model is None:
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _st_model


def _profile_rerank(ranked_list: list, G: nx.DiGraph, user_node: dict, max_items: int = 50) -> list:
    """
    Rerank candidates using sentence-embedding similarity to the user profile
    (role + languages + topics) plus existing graph scores.
    """
    if not ranked_list:
        return ranked_list

    # Build profile text from role, languages, topics
    role = user_node.get("ai_role") or user_node.get("predicted_role") or ""
    langs = user_node.get("top_repo_languages") or []
    lang_tokens = []
    for l in langs[:5]:
        if isinstance(l, (list, tuple)):
            lang_tokens.append(str(l[0]))
        else:
            lang_tokens.append(str(l))
    topics = user_node.get("topics") or []

    profile_parts = [
        f"role: {role}",
        f"languages: {' '.join(lang_tokens)}",
        f"topics: {' '.join(map(str, topics[:8]))}",
    ]
    profile_text = " | ".join([p for p in profile_parts if p.strip()])

    try:
        model = _get_st_model()
        profile_emb = model.encode(profile_text, convert_to_tensor=True)
    except Exception:
        return ranked_list  # fallback: no rerank

    reranked = []
    for node_id, score, features in ranked_list[:max_items]:
        data = G.nodes[node_id]
        cand_text = " ".join(
            filter(
                None,
                [
                    str(data.get("label") or data.get("name") or node_id),
                    str(data.get("description") or ""),
                    str(data.get("language") or ""),
                    str(data.get("type") or ""),
                ],
            )
        )
        try:
            cand_emb = model.encode(cand_text, convert_to_tensor=True)
            sim = util.cos_sim(profile_emb, cand_emb).item()
        except Exception:
            sim = 0.0

        # Combine original score with embedding similarity
        combined = score + 0.6 * sim
        reranked.append((node_id, combined, features))

    reranked.sort(key=lambda x: x[1], reverse=True)
    # For items beyond max_items, append unchanged
    if len(ranked_list) > max_items:
        reranked.extend(ranked_list[max_items:])
    return reranked

def get_recommendation_candidates(G: nx.DiGraph, source_id: str, max_candidates: int = 500) -> List[str]:
    """
    Selects candidate nodes for recommendation based on type.
    """
    source_id_str = str(source_id)
    if source_id_str not in G:
        return []
        
    source_type = G.nodes[source_id_str].get("type")
    candidates = []
    
    target_type = "repo" # Default to repo for everyone (User request: "dont recommend any user")
    
    # We explicitly want to recommend REPOS to USERS now
    if source_type in ["user", "so_user", "github_user", "developer"]:
        target_type = "repo"
    elif source_type in ["repo", "github_repo"]:
        target_type = "repo"
        
    for node, data in G.nodes(data=True):
        if str(node) == source_id_str:
            continue
        ntype = data.get("type", "")
        
        # Strict filtering for Repositories
        if target_type == "repo" and ntype in ["repo", "github_repo", "project", "repository"]:
            candidates.append(node)
            
    neighbors = set(G.neighbors(source_id_str))
    candidates = [c for c in candidates if c not in neighbors]
    
    # Profile-based filtering: prioritize repos matching user's languages and topics
    source_node = G.nodes[source_id_str]
    user_languages = source_node.get("top_repo_languages", [])
    user_topics = source_node.get("topics", [])
    
    if user_languages or user_topics:
        # Extract language names from tuples if needed
        lang_names = []
        if user_languages:
            if isinstance(user_languages[0], (list, tuple)):
                lang_names = [lang[0].lower() if isinstance(lang, (list, tuple)) else str(lang).lower() for lang in user_languages[:5]]
            else:
                lang_names = [str(lang).lower() for lang in user_languages[:5]]
        
        topic_names = [str(topic).lower() for topic in user_topics[:5]] if user_topics else []
        
        # Score candidates based on profile match
        scored_candidates = []
        for cand_id in candidates:
            cand_data = G.nodes[cand_id]
            score = 0
            
            # Language match
            cand_lang = str(cand_data.get("language", "")).lower()
            if cand_lang and any(lang in cand_lang or cand_lang in lang for lang in lang_names):
                score += 10
            
            # Topic/keyword match in description
            cand_desc = str(cand_data.get("description", "")).lower()
            cand_name = str(cand_data.get("label", cand_data.get("name", ""))).lower()
            cand_text = f"{cand_desc} {cand_name}"
            
            for topic in topic_names:
                if topic in cand_text:
                    score += 5
            
            # Language match in description
            for lang in lang_names:
                if lang in cand_text:
                    score += 3
            
            scored_candidates.append((score, cand_id))
        
        # Sort by score (descending), then by node_id for determinism
        scored_candidates.sort(key=lambda x: (-x[0], str(x[1])))
        candidates = [cand_id for _, cand_id in scored_candidates]
    
    # Limit candidates deterministically (no random shuffle)
    if len(candidates) > max_candidates:
        candidates = candidates[:max_candidates]
    
    return candidates

def recommend_for_node(source_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Generates recommendations for a given node.
    """
    # Normalize source_id to string for consistent access
    source_id_str = str(source_id)
    
    # 1. Load Graph & Embeddings
    G = load_graph_as_networkx()
    if source_id_str not in G:
        print(f"Node {source_id} not found in graph.")
        return []

    # Get embeddings (will compute if missing)
    emb_dict = get_or_compute_embeddings(G)
    
    if source_id_str not in emb_dict:
        # Fallback to simple candidates if no embedding
        emb_dict = {} 
        
    # 2. Select Candidates
    candidates = get_recommendation_candidates(G, source_id_str)
    
    if not candidates:
        return []
        
    # 3. Compute Scores
    # A. Cosine Similarity
    if emb_dict:
        cos_scores = cosine_similarity_scores(emb_dict, source_id_str, candidates)
    else:
        cos_scores = {c: 0.0 for c in candidates}
    
    # B. Heuristics
    G_undirected = G.to_undirected()
    heur_scores = graph_heuristic_scores(G_undirected, source_id_str, candidates, method="jaccard")
    
    # C. Profile and role-based scoring (languages, topics, role keywords, stars)
    profile_scores = {}
    user_node = G.nodes[source_id_str]
    user_languages = user_node.get("top_repo_languages", [])
    user_topics = user_node.get("topics", [])
    user_role = (user_node.get("ai_role") or user_node.get("predicted_role") or "").lower()
    
    lang_names = []
    if user_languages:
        if isinstance(user_languages[0], (list, tuple)):
            lang_names = [lang[0].lower() if isinstance(lang, (list, tuple)) else str(lang).lower() for lang in user_languages[:5]]
        else:
            lang_names = [str(lang).lower() for lang in user_languages[:5]]
    
    topic_names = [str(topic).lower() for topic in user_topics[:5]] if user_topics else []
    
    for cand_id in candidates:
        cand_data = G.nodes[cand_id]
        profile_score = 0.0
        
        cand_lang = str(cand_data.get("language", "")).lower()
        cand_desc = str(cand_data.get("description", "")).lower()
        cand_name = str(cand_data.get("label", cand_data.get("name", ""))).lower()
        cand_text = f"{cand_desc} {cand_name} {cand_lang}"
        
        # Language match
        if cand_lang and any(lang in cand_lang or cand_lang in lang for lang in lang_names):
            profile_score += 0.25
        
        # Topic match
        for topic in topic_names:
            if topic in cand_text:
                profile_score += 0.15
        
        # Role keyword match
        if user_role:
            role_tokens = [tok.strip() for tok in user_role.replace("/", " ").split() if tok]
            if any(tok in cand_text for tok in role_tokens):
                profile_score += 0.2
        
        # Star/quality hint (log-scaled)
        stars = cand_data.get("stargazers_count") or cand_data.get("stars") or 0
        if stars:
            profile_score += min(np.log1p(stars) / 50.0, 0.3)
        
        profile_scores[cand_id] = min(profile_score, 0.9)  # Cap to keep balance
    
    # 4. Combine & Rank (with profile boost)
    ranked_list = combine_scores(cos_scores, heur_scores, alpha=0.7)
    
    # Apply profile boost
    for i, (node_id, score, features) in enumerate(ranked_list):
        if node_id in profile_scores:
            ranked_list[i] = (node_id, score + profile_scores[node_id], features)
    
    # Re-sort after profile boost
    ranked_list.sort(key=lambda x: x[1], reverse=True)

    # 4b. Embedding-based rerank using user role/languages/topics
    ranked_list = _profile_rerank(ranked_list, G, user_node)
    
    # Limit preliminary list to larger pool for Gemini (e.g. top 20)
    preliminary_top = ranked_list[:20]
    
    # 5. Format for Output / Gemini
    results_for_llm = []
    for node_id, score, features in preliminary_top:
        node_data = G.nodes[node_id]
        
        # Clean Label Logic
        raw_label = node_data.get("label") or node_data.get("name") or str(node_id)
        if raw_label.startswith("github:"):
            label = raw_label.replace("github:", "")
        elif raw_label.startswith("user:"):
             label = raw_label.replace("user:", "")
        else:
             label = raw_label

        results_for_llm.append({
            "node_id": node_id,
            "label": label,
            "type": node_data.get("type"),
            "score": round(score, 4),
            "html_url": node_data.get("html_url") or node_data.get("url"),
            "language": node_data.get("language"),
            "description": node_data.get("description"),
            "stargazers_count": node_data.get("stars") or node_data.get("stargazers_count"),
            "features": {
                "cosine_similarity": round(features["cosine_similarity"], 4),
                "heuristic_score": round(features["heuristic_score"], 4)
            }
        })
        
    # 6. LLM rerank disabled; use locally ranked (reranked) results
    return results_for_llm[:top_k]

if __name__ == "__main__":
    print("--- Recommendation Service Demo ---")
    
    # You can change this to a valid ID in your DB
    # Example: "github:torvalds" or a repo ID
    test_node = "github:torvalds" 
    
    print(f"Generating recommendations for: {test_node}")
    try:
        recs = recommend_for_node(test_node, top_k=5)
        
        if recs:
            print(f"\nTop {len(recs)} Recommendations:")
            for i, r in enumerate(recs):
                print(f"{i+1}. {r['label']} ({r['type']}) - Score: {r['score']}")
                print(f"   Features: {r['features']}")
        else:
            print("No recommendations found (or node invalid).")
            
    except Exception as e:
        print(f"Error during demo: {e}")
