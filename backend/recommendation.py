import sys
import os
import networkx as nx
import numpy as np
from typing import List, Dict, Any, Tuple

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

def get_recommendation_candidates(G: nx.DiGraph, source_id: str, max_candidates: int = 500) -> List[str]:
    """
    Selects candidate nodes for recommendation based on type.
    """
    if str(source_id) not in G:
        return []
        
    source_type = G.nodes[source_id].get("type")
    candidates = []
    
    target_type = "repo" # Default to repo for everyone (User request: "dont recommend any user")
    
    # We explicitly want to recommend REPOS to USERS now
    if source_type in ["user", "so_user", "github_user", "developer"]:
        target_type = "repo"
    elif source_type in ["repo", "github_repo"]:
        target_type = "repo"
        
    for node, data in G.nodes(data=True):
        if str(node) == str(source_id):
            continue
        ntype = data.get("type", "")
        
        # Strict filtering for Repositories
        if target_type == "repo" and ntype in ["repo", "github_repo", "project", "repository"]:
            candidates.append(node)
            
    neighbors = set(G.neighbors(source_id))
    candidates = [c for c in candidates if c not in neighbors]
    
    # Profile-based filtering: prioritize repos matching user's languages and topics
    source_node = G.nodes[source_id]
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
    # 1. Load Graph & Embeddings
    G = load_graph_as_networkx()
    if str(source_id) not in G:
        print(f"Node {source_id} not found in graph.")
        return []

    # Get embeddings (will compute if missing)
    emb_dict = get_or_compute_embeddings(G)
    
    if str(source_id) not in emb_dict:
        # Fallback to simple candidates if no embedding
        emb_dict = {} 
        
    # 2. Select Candidates
    candidates = get_recommendation_candidates(G, source_id)
    
    if not candidates:
        return []
        
    # 3. Compute Scores
    # A. Cosine Similarity
    if emb_dict:
        cos_scores = cosine_similarity_scores(emb_dict, source_id, candidates)
    else:
        cos_scores = {c: 0.0 for c in candidates}
    
    # B. Heuristics
    G_undirected = G.to_undirected()
    heur_scores = graph_heuristic_scores(G_undirected, source_id, candidates, method="jaccard")
    
    # C. Profile-based scoring (additional boost for matching languages/topics)
    profile_scores = {}
    user_languages = G.nodes[source_id].get("top_repo_languages", [])
    user_topics = G.nodes[source_id].get("topics", [])
    
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
            profile_score += 0.2
        
        # Topic match
        for topic in topic_names:
            if topic in cand_text:
                profile_score += 0.15
        
        profile_scores[cand_id] = min(profile_score, 0.5)  # Cap at 0.5
    
    # 4. Combine & Rank (with profile boost)
    ranked_list = combine_scores(cos_scores, heur_scores, alpha=0.7)
    
    # Apply profile boost
    for i, (node_id, score, features) in enumerate(ranked_list):
        if node_id in profile_scores:
            ranked_list[i] = (node_id, score + profile_scores[node_id], features)
    
    # Re-sort after profile boost
    ranked_list.sort(key=lambda x: x[1], reverse=True)
    
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
        
    # 6. Apply Gemini Ranking
    # Get user profile context
    # Get user profile context
    user_node = G.nodes[source_id]
    profile_context = f"User: {user_node.get('name')}\nBio: {user_node.get('bio')}\nTopics: {user_node.get('topics')}\nLang: {user_node.get('top_repo_languages')}\n\nProject Analysis (from READMEs):\n{user_node.get('ai_analysis')}"
    
    final_results = rank_recommendations_with_gemini(results_for_llm, profile_context)
    
    return final_results[:top_k]

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
