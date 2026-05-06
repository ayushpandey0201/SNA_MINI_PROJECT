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


def _compute_semantic_similarity(G: nx.DiGraph, user_node: dict, candidate_ids: List[str]) -> Dict[str, float]:
    """
    Compute Sentence-BERT semantic similarity between user profile and candidate repositories.
    
    Returns:
        Dictionary mapping candidate_id to semantic similarity score [0,1]
    """
    if not candidate_ids:
        return {}
    
    # Build profile text from role, languages, topics
    role = user_node.get("ai_role") or user_node.get("predicted_role") or ""
    langs = user_node.get("top_repo_languages", [])
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
        return {cand_id: 0.0 for cand_id in candidate_ids}  # fallback: no similarity

    semantic_scores = {}
    for node_id in candidate_ids:
        data = G.nodes.get(node_id, {})
        cand_text = " ".join(
            filter(
                None,
                [
                    str(data.get("label") or data.get("name") or node_id),
                    str(data.get("description") or ""),
                    str(data.get("language") or ""),
                ],
            )
        )
        try:
            cand_emb = model.encode(cand_text, convert_to_tensor=True)
            sim = util.cos_sim(profile_emb, cand_emb).item()
            semantic_scores[node_id] = max(0.0, min(1.0, sim))  # Ensure [0,1] range
        except Exception:
            semantic_scores[node_id] = 0.0

    return semantic_scores


def get_recommendation_candidates(G: nx.DiGraph, source_id: str, max_candidates: int = 200) -> List[str]:
    """
    Selects candidate repository nodes from restricted sources:
    - Direct collaborators' repositories
    - Same-community repositories
    - User's own repositories are EXCLUDED (not recommended to themselves)
    
    This restriction happens BEFORE scoring to improve relevance and stability.
    """
    source_id_str = str(source_id)
    if source_id_str not in G:
        return []
    
    candidates_set = set()
    user_repos = set()  # Track user's own repos to exclude them
    
    # 1. Get user's own repositories (to exclude them from recommendations)
    for neighbor in G.successors(source_id_str):
        neighbor_data = G.nodes.get(neighbor, {})
        if neighbor_data.get("type") in ["repo", "github_repo", "project", "repository"]:
            user_repos.add(neighbor)
    
    # 2. Get direct collaborators' repositories
    # Collaborators are users connected via shared repositories
    collaborators = set()
    for repo in user_repos:
        # Find other users who also contribute to this repo
        for predecessor in G.predecessors(repo):
            if predecessor != source_id_str:
                predecessor_data = G.nodes.get(predecessor, {})
                if predecessor_data.get("type") in ["user", "github_user", "so_user"]:
                    collaborators.add(predecessor)
        
        # Also check successors (reverse edges)
        for successor in G.successors(repo):
            if successor != source_id_str and G.nodes.get(successor, {}).get("type") in ["user", "github_user", "so_user"]:
                collaborators.add(successor)
    
    # Get repositories from collaborators (excluding user's own repos)
    for collab_id in collaborators:
        for repo in G.successors(collab_id):
            repo_data = G.nodes.get(repo, {})
            if repo_data.get("type") in ["repo", "github_repo", "project", "repository"]:
                if repo not in user_repos:  # Don't recommend user's own repos
                    candidates_set.add(repo)
    
    # 3. Get same-community repositories (if community info is available)
    try:
        import networkx as nx
        G_undirected = G.to_undirected()
        
        # Detect communities using Louvain (same as in metrics endpoint)
        communities = nx.community.louvain_communities(G_undirected, seed=42)
        
        # Find user's community
        user_community = None
        for comm in communities:
            if source_id_str in comm:
                user_community = comm
                break
        
        # Add repositories from same community
        if user_community:
            for node_id in user_community:
                if node_id == source_id_str:
                    continue
                node_data = G.nodes.get(node_id, {})
                node_type = node_data.get("type", "")
                
                # If it's a repo in the same community, add it
                if node_type in ["repo", "github_repo", "project", "repository"]:
                    if node_id not in user_repos:  # Don't recommend user's own repos
                        candidates_set.add(node_id)
                
                # If it's a user in same community, get their repos
                elif node_type in ["user", "github_user", "so_user"]:
                    for repo in G.successors(node_id):
                        repo_data = G.nodes.get(repo, {})
                        if repo_data.get("type") in ["repo", "github_repo", "project", "repository"]:
                            if repo not in user_repos:
                                candidates_set.add(repo)
    except Exception as e:
        # If community detection fails, continue with collaborators only
        print(f"Community detection failed: {e}, using collaborators only")
    
    # Convert to list and limit
    candidates = list(candidates_set)
    
    # Limit candidates
    if len(candidates) > max_candidates:
        candidates = candidates[:max_candidates]
    
    return candidates

def recommend_for_node(source_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Generates personalized recommendations for a given node.
    
    Returns 4-5 top repositories based on:
    - User's predicted role
    - User's profile (languages, topics)
    - User's work/interests
    - Top similarity scores (only scores >= 0.5 / 50%)
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
    
    # C. Semantic similarity as initial filter (MANDATORY)
    user_node = G.nodes[source_id_str]
    semantic_scores = _compute_semantic_similarity(G, user_node, candidates)
    
    # Filter candidates by semantic similarity threshold (0.45)
    SEMANTIC_THRESHOLD = 0.45
    semantically_relevant_candidates = [
        cand_id for cand_id in candidates 
        if semantic_scores.get(cand_id, 0.0) >= SEMANTIC_THRESHOLD
    ]
    
    if not semantically_relevant_candidates:
        return []  # No semantically relevant candidates
    
    # Update candidate list to only semantically relevant ones
    candidates = semantically_relevant_candidates
    
    # Update cos_scores and heur_scores to only include filtered candidates
    cos_scores = {c: cos_scores.get(c, 0.0) for c in candidates}
    heur_scores = {c: heur_scores.get(c, 0.0) for c in candidates}
    
    # D. Small profile-based boosts (language, role, topics) - NOT stars
    profile_boosts = {}
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
        boost = 0.0
        
        cand_lang = str(cand_data.get("language", "")).lower()
        cand_desc = str(cand_data.get("description", "")).lower()
        cand_name = str(cand_data.get("label", cand_data.get("name", ""))).lower()
        cand_text = f"{cand_desc} {cand_name} {cand_lang}"
        
        # Small boosts for profile matches
        if cand_lang and any(lang in cand_lang or cand_lang in lang for lang in lang_names):
            boost += 0.05  # Small language boost
        
        for topic in topic_names:
            if topic in cand_text:
                boost += 0.03  # Small topic boost
                break  # Only count once
        
        if user_role:
            role_tokens = [tok.strip() for tok in user_role.replace("/", " ").split() if tok]
            if any(tok in cand_text for tok in role_tokens):
                boost += 0.05  # Small role boost
        
        profile_boosts[cand_id] = min(boost, 0.15)  # Cap at 0.15 (small boost)
    
    # 4. Combine graph scores (Node2Vec + Jaccard)
    ranked_list = combine_scores(cos_scores, heur_scores, alpha=0.7)
    
    # Apply small profile boosts and add semantic similarity to features
    boosted_list = []
    for node_id, score, features in ranked_list:
        boost = profile_boosts.get(node_id, 0.0)
        new_score = score + boost
        new_features = {
            **features,
            "semantic_similarity": semantic_scores.get(node_id, 0.0)
        }
        boosted_list.append((node_id, new_score, new_features))
    
    ranked_list = boosted_list
    
    # Re-sort after profile boost
    ranked_list.sort(key=lambda x: x[1], reverse=True)
    
    # 5. Normalize scores to [0,1] range
    if ranked_list:
        max_score = max(score for _, score, _ in ranked_list)
        min_score = min(score for _, score, _ in ranked_list)
        score_range = max_score - min_score if max_score > min_score else 1.0
        
        normalized_list = []
        for node_id, score, features in ranked_list:
            if score_range > 0:
                normalized_score = (score - min_score) / score_range
            else:
                normalized_score = score if score <= 1.0 else 1.0
            
            normalized_list.append((node_id, normalized_score, features))
        
        ranked_list = normalized_list
    
    # 6. Filter by semantic similarity threshold (0.5) OR normalized score (0.5)
    # Use semantic similarity as the primary filter
    filtered_list = [
        (node_id, score, features) 
        for node_id, score, features in ranked_list 
        if features.get("semantic_similarity", 0.0) >= 0.5
    ]
    
    # 7. Format for Output with tie-breaking by stars (weak signal)
    results = []
    for node_id, score, features in filtered_list:
        node_data = G.nodes[node_id]
        stars = node_data.get("stargazers_count") or node_data.get("stars") or 0
        
        # Clean Label Logic
        raw_label = node_data.get("label") or node_data.get("name") or str(node_id)
        if raw_label.startswith("github:"):
            label = raw_label.replace("github:", "")
        elif raw_label.startswith("user:"):
             label = raw_label.replace("user:", "")
        else:
             label = raw_label

        results.append({
            "node_id": node_id,
            "label": label,
            "type": node_data.get("type"),
            "score": round(score, 4),
            "html_url": node_data.get("html_url") or node_data.get("url"),
            "language": node_data.get("language"),
            "description": node_data.get("description"),
            "stargazers_count": stars,
            "features": {
                "cosine_similarity": round(features.get("cosine_similarity", 0.0), 4),
                "heuristic_score": round(features.get("heuristic_score", 0.0), 4),
                "semantic_similarity": round(features.get("semantic_similarity", 0.0), 4)
            },
            "_sort_key": (score, stars)  # For tie-breaking
        })
    
    # 8. Sort by score (primary), then stars (weak tie-breaker), then return top 4-5
    results.sort(key=lambda x: x["_sort_key"], reverse=True)
    
    # Remove sort key before returning
    for r in results:
        r.pop("_sort_key", None)
    
    # Return top 4-5 recommendations
    final_limit = min(max(4, top_k), 5)
    return results[:final_limit]

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
