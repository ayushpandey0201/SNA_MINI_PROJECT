import sys
import os
import logging
import json
from functools import lru_cache
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
import joblib
import networkx as nx
import numpy as np

# Add the parent directory to sys.path to allow imports from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.storage import load_graph_as_networkx
from backend.enrich import enrich_profile
from backend.graph_ops import compute_node2vec_embeddings, save_embeddings_to_db
from backend.fetchers.github import search_repositories
from backend.fetchers.stackoverflow import search_questions
from backend.fetchers.research import search_research_papers
from backend.nlp_ops import classify_role_from_text

# Configure logging
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

app = FastAPI(title="GitStack Connect API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Cache for Graph and Embeddings
# In a production app, this might be a Redis cache or a more sophisticated state manager
GRAPH_CACHE = {
    "G": None,
    "embeddings": {},  # node_id -> np.array
    "undirected_G": None,
    "model": None
}

def get_graph_data():
    """
    Lazy loader for graph data.
    Loads the graph from the database and pre-processes embeddings.
    """
    if GRAPH_CACHE["G"] is None:
        logger.info("Loading graph from DB...")
        try:
            G = load_graph_as_networkx()
            GRAPH_CACHE["G"] = G
            
            # Create undirected view for Jaccard coefficient
            GRAPH_CACHE["undirected_G"] = G.to_undirected()
            
            # Extract embeddings from node attributes
            embeddings = {}
            for node, data in G.nodes(data=True):
                if "embedding" in data:
                    emb = data["embedding"]
                    # Handle case where embedding might be a JSON string or list
                    if isinstance(emb, str):
                        try:
                            emb = json.loads(emb)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse embedding for node {node}")
                            continue
                    
                    if isinstance(emb, list):
                        embeddings[node] = np.array(emb)
            
            GRAPH_CACHE["embeddings"] = embeddings
            logger.info(f"Graph loaded: {len(G.nodes)} nodes. {len(embeddings)} embeddings found.")
            
        except Exception as e:
            logger.error(f"Error loading graph data: {e}")
            # Initialize empty if failed to prevent crash loops, but endpoints will fail
            GRAPH_CACHE["G"] = nx.DiGraph()
            GRAPH_CACHE["undirected_G"] = nx.Graph()
            GRAPH_CACHE["embeddings"] = {}

    return GRAPH_CACHE

def update_embeddings_task():
    """
    Background task to re-compute embeddings for the updated graph.
    """
    logger.info("Starting background embedding update...")
    try:
        # 1. Load fresh graph
        G = load_graph_as_networkx()
        
        # 2. Compute Embeddings
        # Using smaller parameters for speed in this interactive demo
        embeddings = compute_node2vec_embeddings(G, dimensions=64, walk_length=10, num_walks=50, workers=1, seed=42)
        
        # 3. Save to DB
        save_embeddings_to_db(embeddings)
        
        # 4. Invalidate Cache
        GRAPH_CACHE["G"] = None
        logger.info("Background embedding update complete. Cache invalidated.")
        
    except Exception as e:
        logger.error(f"Error in background embedding update: {e}")

def load_model():
    """Load the trained role classification model."""
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'models', 'role_clf.joblib'))
    if os.path.exists(model_path):
        try:
            clf = joblib.load(model_path)
            GRAPH_CACHE["model"] = clf
            logger.info(f"Model loaded from {model_path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
    else:
        logger.warning(f"Model file not found at {model_path}")

@app.on_event("startup")
async def startup_event():
    """Load graph data on application startup."""
    get_graph_data()
    load_model()

def cosine_similarity(v1, v2):
    """Compute cosine similarity between two vectors."""
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(v1, v2) / (norm1 * norm2))


@app.get("/")
def read_root():
    return {"message": "GitStack Connect API is running. Use /recommend/{node_id} to get recommendations."}

from backend.recommendation import recommend_for_node

@app.get("/recommend/{node_id}")
def recommend_endpoint(node_id: str, limit: int = 7):
    """
    Get top-K recommendations for a given node based on graph embeddings and topology.
    Falls back to GitHub Search if local recommendations are insufficient.
    """
    # Ensure graph is loaded
    data = get_graph_data()
    G = data["G"]
    
    if node_id not in G:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found in the graph.")
        
    try:
        # 1. Local Graph Recommendations using new Service
        local_recs = recommend_for_node(node_id, top_k=limit)
        
        results = local_recs
        
        # 2. Fallback: GitHub Search API
        # If we have fewer than 'limit' results, fetch external suggestions
        if len(results) < limit:
            needed = limit - len(results)
            logger.info(f"Local graph returned only {len(results)} recommendations. Fetching {needed} from GitHub API...")
            
            node_data = G.nodes[node_id]
            
            # Extract keywords for search
            # 1. Top Language from owned repos (if available)
            # 2. Top Topics from profile (if available)
            
            query_parts = []
            
            # Try to get language from connected repos
            langs = []
            topics = []
            
            # Simple heuristic: Check node data or neighbor repos
            # Since strict node structure varies, we check neighbors for repo data
            for n in G.neighbors(node_id):
                node = G.nodes[n]
                if node.get('type') == 'github_repo':
                    l = node.get('language')
                    if l: langs.append(l)
                    
                    # Topics might be stored as comma-sep string or list? 
                    # In enrich.py 'topics' is a list.
                    t_list = node.get('topics', [])
                    if isinstance(t_list, list):
                        topics.extend(t_list)
            
            # Add AI-derived context if available (from README analysis)
            ai_role = node.get('ai_role')
            if ai_role:
                query_parts.append(ai_role.replace(' ', '+'))
            
            # Use most frequent language as strong filter
            if langs:
                top_lang = max(set(langs), key=langs.count)
                query_parts.append(f"language:{top_lang}")
                
            # Add Top Topic (most frequent)
            if topics:
                # Filter generic topics if needed, but for now just take top 1
                top_topic = max(set(topics), key=topics.count)
                query_parts.append(f"topic:{top_topic}")
                
            # Add generic sorting if specific enough
            query = " ".join(query_parts) if query_parts else "stars:>1000"
            if not query.strip(): query = "stars:>1000"
            
            logger.info(f"Fallback Search Query (AI Enhanced): '{query}'")
            
            # Fetch from GitHub
            external_repos = search_repositories(query, sort="stars", order="desc", page=1)
            
            existing_ids = {r["node_id"] for r in results}
            
            for item in external_repos.get("items", []):
                if len(results) >= limit:
                    break
                    
                # Avoid recommending self-owned or already recommended
                # item['html_url'] is unique enough
                repo_name = item['full_name'] # search_repositories returns dict with full_name
                
                # Check if user already owns/contributed (simple check by name)
                is_connected = False
                for n in G.neighbors(node_id):
                     if n == repo_name: 
                         is_connected = True
                         break
                
                if is_connected:
                    continue
                    
                if repo_name not in existing_ids:
                    # Format as recommendation result
                    results.append({
                        "node_id": repo_name,
                        "label": item.get('full_name') or item.get('name'), # Explicit label
                        "type": "repository", # Explicit type
                        "score": 0.5, # Lower score than local graph matches
                        "features": {
                            "source": "github_fallback",
                            "language": item.get('language'),
                            "stars": item.get('stargazers_count')
                        },
                        "name": item.get('name'),
                        "full_name": item.get('full_name'),
                        "description": item.get('description'),
                        "html_url": item.get('html_url'),
                        "language": item.get('language'),
                        "stargazers_count": item.get('stargazers_count')
                    })
                    existing_ids.add(repo_name)

        # Slice to requested limit (user asked for 4-6, standard is 10)
        return results[:limit]
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        # Return whatever we have or empty list instead of 500
        return []

class FetchRequest(BaseModel):
    github_username: str
    so_user_id: Optional[int] = None

@app.post("/fetch")
def trigger_fetch(request: FetchRequest, background_tasks: BackgroundTasks):
    """
    Trigger data fetching and enrichment for a user.
    """
    try:
        profile = enrich_profile(request.github_username, request.so_user_id)
        
        # Trigger background embedding update
        background_tasks.add_task(update_embeddings_task)
        
        return profile
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/enrich/{username}")
def enrich_endpoint(username: str):
    """
    Get enriched profile for a GitHub username.
    """
    try:
        print(f"DEBUG: Endpoint /enrich/{username} called")
        profile = enrich_profile(username)
        GRAPH_CACHE["G"] = None 
        return profile
    except Exception as e:
        logger.error(f"Enrichment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/predict/{user_id}")
def predict_role(user_id: str):
    """
    Predict developer role based on text content.
    Prioritizes AI-generated role if available, otherwise falls back to classifier.
    """
    # Ensure graph and model are loaded
    data = get_graph_data()
    G = data.get("G")
    
    if user_id not in G:
        raise HTTPException(status_code=404, detail="User not found")
        
    node = G.nodes[user_id]
    
    # 1. Check for AI-generated specific role (Highest Priority)
    # But only use it if it's not a generic/fallback role
    ai_role = node.get("ai_role")
    if ai_role and ai_role not in ["Developer", "Unknown", None, ""]:
        # Use AI role but also get probabilities from text classifier for confidence
        text_corpus = node.get("text_corpus", "")
        probabilities = {}
        if text_corpus:
            try:
                probabilities = classify_role_from_text(text_corpus)
            except:
                pass
        
        # If we have probabilities, use them; otherwise give AI role 100% confidence
        if probabilities:
            # Boost the AI role's probability
            if ai_role in probabilities:
                probabilities[ai_role] = min(probabilities[ai_role] * 1.5, 0.95)  # Cap at 95%
            else:
                probabilities[ai_role] = 0.8  # High confidence for AI role
            # Renormalize
            total = sum(probabilities.values())
            probabilities = {k: round(v/total, 4) for k, v in probabilities.items()}
        else:
            probabilities = {ai_role: 1.0}
        
        return {
            "predicted_role": ai_role,
            "probabilities": probabilities
        }

    # 2. Fallback to Text Classifier (Rule-based)
    text_corpus = node.get("text_corpus", "")
    if not text_corpus:
        return {"predicted_role": "Developer", "probabilities": {"Developer": 1.0}}
        
    try:
        probabilities = classify_role_from_text(text_corpus)
        if not probabilities:
             return {"predicted_role": "Developer", "probabilities": {"Developer": 1.0}}
             
        predicted_role = max(probabilities, key=probabilities.get)
        
        return {
            "predicted_role": predicted_role,
            "probabilities": probabilities
        }
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return {"predicted_role": "Developer", "probabilities": {"Developer": 1.0}}


@app.get("/metrics/{node_id}")
def get_network_metrics(node_id: str):
    """
    Compute network centrality metrics for a node.
    """
    data = get_graph_data()
    G = data["G"]
    
    if node_id not in G:
         raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
         
    try:
        # Degree Centrality (normalized)
        degree = nx.degree_centrality(G).get(node_id, 0)
        
        # Betweenness Centrality (expensive, so we limit k if graph is huge, but here it's small)
        # For better performance on larger graphs, use k=100 or similar approximation
        betweenness = nx.betweenness_centrality(G, k=None).get(node_id, 0)
        
        # Closeness Centrality
        closeness = nx.closeness_centrality(G, u=node_id)
        
        # Composite Influence Score (0-100)
        # Weighted combination of centralities (removed eigenvector as requested)
        # Formula: (degree * 0.4 + betweenness * 0.4 + closeness * 0.2) * 100
        influence_score = (degree * 0.4 + betweenness * 0.4 + closeness * 0.2) * 100
        
        # Community Detection (Greedy Modularity)
        # We compute this for the whole graph (or subgraph) to find which community the node belongs to
        # For performance, we might cache this, but for now we run it on demand for the demo
        try:
            # Louvain Community Detection (Requested by User)
            communities = nx.community.louvain_communities(data["undirected_G"], seed=42)
            
            # Find community ID for the target node
            node_community_id = -1
            community_map = {} # Map node_id -> community_id for neighbors
            
            for i, comm in enumerate(communities):
                if node_id in comm:
                    node_community_id = i
                
                # Map for all nodes in this community (to send back relevant ones)
                for n in comm:
                    community_map[n] = i
            
        except Exception as comm_e:
            logger.warning(f"Community detection failed: {comm_e}")
            node_community_id = -1
            community_map = {}

        return {
            "degree_centrality": round(degree, 4),
            "betweenness_centrality": round(betweenness, 4),
            "closeness_centrality": round(closeness, 4),
            "influence_score": round(influence_score, 1),
            "community_id": node_community_id,
            "community_map": community_map
        }
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        raise HTTPException(status_code=500, detail="Error computing metrics.")

@app.get("/search/project")
def search_project_endpoint(query: str, repo_page: int = 1, so_page: int = 1, paper_page: int = 1):
    """
    Search for project ideas across GitHub, StackOverflow, and Research Papers.
    """
    print(f"DEBUG: Received search request. Query: '{query}', Pages: repo={repo_page}, so={so_page}, paper={paper_page}")
    try:
        # Fetchers now return {"items": [], "has_next": bool}
        repos = search_repositories(query, page=repo_page)
        print(f"DEBUG: Repos found: {len(repos.get('items', []))}")
        
        questions = search_questions(query, page=so_page)
        print(f"DEBUG: Questions found: {len(questions.get('items', []))}")
        
        papers = search_research_papers(query, page=paper_page)
        print(f"DEBUG: Papers found: {len(papers.get('items', []))}")
        
        return {
            "repos": repos,
            "questions": questions,
            "papers": papers
        }
    except Exception as e:
        logger.error(f"Project search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
