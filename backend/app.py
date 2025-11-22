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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dev-Intel API")

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

@lru_cache(maxsize=128)
def _compute_recommendations(node_id: str, top_k: int):
    """
    Cached worker function for recommendations.
    """
    data = get_graph_data()
    G = data["G"]
    undirected_G = data["undirected_G"]
    embeddings = data["embeddings"]
    
    if node_id not in G:
        return None

    # 1. Identify Candidates: All nodes except self and existing neighbors
    # We want to recommend NEW connections.
    neighbors = set(G.neighbors(node_id))
    neighbors.add(node_id)
    
    # Filter candidates to prioritize Users and Repos (exclude tags for now to make it more "social")
    candidates = [
        n for n in G.nodes() 
        if n not in neighbors 
        and G.nodes[n].get('type') in ['github_user', 'github_repo', 'so_user']
    ]
    
    if not candidates:
        return []

    # Get target node embedding
    target_emb = embeddings.get(node_id)
    
    # 2. Pre-calculate Heuristic Scores (Jaccard)
    # Jaccard Coefficient: Intersection / Union of neighbors
    jaccard_scores = {}
    try:
        # nx.jaccard_coefficient returns iterator of (u, v, p)
        # We pass pairs of (node_id, candidate)
        pairs = [(node_id, candidate) for candidate in candidates]
        preds = nx.jaccard_coefficient(undirected_G, pairs)
        for u, v, p in preds:
            # v is the candidate (or u, order doesn't matter in undirected)
            other = v if u == node_id else u
            jaccard_scores[other] = p
    except Exception as e:
        logger.error(f"Error computing Jaccard scores: {e}")
        # Fallback to 0.0 for all
        for c in candidates:
            jaccard_scores[c] = 0.0

    results = []
    
    for candidate in candidates:
        # Embedding Similarity
        cand_emb = embeddings.get(candidate)
        
        sim = 0.0
        if target_emb is not None and cand_emb is not None:
            sim = cosine_similarity(target_emb, cand_emb)
            
        # Heuristic Score
        jacc = jaccard_scores.get(candidate, 0.0)
        
        # Combined Score
        # Weights: 0.7 Embedding, 0.3 Heuristic (Boosted embedding weight)
        final_score = (0.7 * sim) + (0.3 * jacc)
        
        # Only return if score > 0 to avoid "junk"
        if final_score > 0:
            results.append({
                "node_id": candidate,
                "score": round(final_score, 4),
                "features": {
                    "similarity": round(sim, 4),
                    "jaccard": round(jacc, 4)
                }
            })
        
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return results[:top_k]

@app.get("/")
def read_root():
    return {"message": "Dev-Intel API is running. Use /recommend/{node_id} to get recommendations."}

@app.get("/recommend/{node_id}")
def recommend_endpoint(node_id: str, limit: int = 10):
    """
    Get top-K recommendations for a given node based on graph embeddings and topology.
    """
    # Ensure graph is loaded
    data = get_graph_data()
    
    if node_id not in data["G"]:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found in the graph.")
        
    try:
        recommendations = _compute_recommendations(node_id, limit)
        if recommendations is None:
             raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
             
        return recommendations
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during recommendation.")

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
        profile = enrich_profile(username)
        GRAPH_CACHE["G"] = None 
        return profile
    except Exception as e:
        logger.error(f"Enrichment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/predict/{user_id}")
def predict_role(user_id: str):
    """
    Predict the role (ML, Web, DevOps) for a given user.
    """
    # Ensure graph and model are loaded
    data = get_graph_data()
    if GRAPH_CACHE["model"] is None:
        load_model()
        if GRAPH_CACHE["model"] is None:
             raise HTTPException(status_code=503, detail="Model not available. Please train the model first.")
             
    embeddings = data["embeddings"]
    if user_id not in embeddings:
         raise HTTPException(status_code=404, detail=f"No embedding found for user '{user_id}'.")
         
    embedding = embeddings[user_id]
    clf = GRAPH_CACHE["model"]
    
    try:
        # Predict expects 2D array
        prediction = clf.predict([embedding])[0]
        probs = clf.predict_proba([embedding])[0]
        
        return {
            "user_id": user_id,
            "predicted_role": prediction,
            "probabilities": dict(zip(clf.classes_, probs))
        }
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Error during prediction.")
