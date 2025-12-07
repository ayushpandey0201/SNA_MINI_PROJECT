import sys
import os
import json
import networkx as nx
from node2vec import Node2Vec
import numpy as np

# Add the parent directory to sys.path to allow imports from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.storage import load_graph_as_networkx, Node, SessionLocal

def compute_node2vec_embeddings(G, dimensions=64, walk_length=10, num_walks=100, workers=1, seed=42):
    """
    Computes Node2Vec embeddings for the given graph.

    Args:
        G (nx.Graph): The NetworkX graph.
        dimensions (int): Dimensionality of the embeddings.
        walk_length (int): Length of each random walk.
        num_walks (int): Number of random walks per node.
        workers (int): Number of parallel workers.
        seed (int): Random seed for reproducibility.

    Returns:
        dict: A dictionary mapping node IDs to their embedding vectors (lists).
    """
    print(f"Computing Node2Vec embeddings (dims={dimensions}, walks={num_walks}, len={walk_length})...")
    
    # Initialize Node2Vec
    # Note: node2vec library might not support 'seed' directly in constructor in all versions, 
    # but we can set numpy seed globally if needed, or rely on the library's behavior.
    # We'll try to pass it if the library supports it, or just set np.random.seed.
    np.random.seed(seed)
    
    if len(G.nodes) == 0:
        print("Graph is empty. Returning empty embeddings.")
        return {}

    # Node2Vec requires a graph where nodes are strings or ints. Our IDs are strings.
    node2vec = Node2Vec(G, dimensions=dimensions, walk_length=walk_length, num_walks=num_walks, workers=workers, quiet=True)
    
    # Train the model
    # window: Maximum distance between the current and predicted word within a sentence.
    # min_count: Ignores all words with total frequency lower than this.
    model = node2vec.fit(window=10, min_count=1, batch_words=4, seed=seed)
    
    # Extract embeddings
    embeddings = {}
    for node_id in G.nodes():
        # The model.wv key might be the node ID as string
        if str(node_id) in model.wv:
            embeddings[node_id] = model.wv[str(node_id)].tolist()
            
    return embeddings

def save_embeddings_to_db(emb_dict):
    """
    Saves the computed embeddings to the database.
    Updates the 'embedding' key in the node's attributes.

    Args:
        emb_dict (dict): Dictionary mapping node IDs to embedding vectors.
    """
    print(f"Saving {len(emb_dict)} embeddings to database...")
    session = SessionLocal()
    try:
        count = 0
        for node_id, embedding in emb_dict.items():
            node = session.query(Node).filter(Node.id == node_id).first()
            if node:
                # Load existing attributes
                attrs = json.loads(node.attrs) if node.attrs else {}
                
                # Update embedding
                attrs['embedding'] = embedding
                
                # Save back
                node.attrs = json.dumps(attrs)
                count += 1
            else:
                print(f"Warning: Node {node_id} not found in DB, skipping embedding save.")
        
        session.commit()
        print(f"Successfully saved {count} embeddings.")
    except Exception as e:
        session.rollback()
        print(f"Error saving embeddings: {e}")
    finally:
        session.close()

def get_or_compute_embeddings(G=None, dimensions=64, walk_length=10, num_walks=100, workers=1, seed=42):
    """
    Retrieves embeddings from the graph/DB or computes them if missing.
    
    Args:
        G (nx.DiGraph, optional): The graph. If None, loads from DB.
        dimensions (int): Node2Vec dimensions.
        walk_length (int): Walk length.
        num_walks (int): Number of walks.
        workers (int): Parallel workers.
        seed (int): Random seed.
        
    Returns:
        dict: Mapping of node_id -> np.array embedding.
    """
    if G is None:
        print("Loading graph for embeddings...")
        G = load_graph_as_networkx()
        
    if len(G.nodes) == 0:
        return {}
        
    # Check if we have embeddings for a significant portion of nodes
    embeddings = {}
    missing_count = 0
    
    for node, data in G.nodes(data=True):
        if "embedding" in data:
            emb = data["embedding"]
            if isinstance(emb, str):
                try:
                    emb = json.loads(emb)
                except:
                    pass
            if isinstance(emb, list):
                embeddings[node] = np.array(emb)
        else:
            missing_count += 1
            
    # Heuristic: If > 50% nodes are missing embeddings, re-compute
    total_nodes = len(G.nodes)
    should_compute = missing_count > (total_nodes * 0.5) or len(embeddings) == 0
    
    if should_compute:
        print(f"Missing embeddings for {missing_count}/{total_nodes} nodes. Re-computing...")
        computed_embs = compute_node2vec_embeddings(G, dimensions, walk_length, num_walks, workers, seed)
        
        # Save back to DB
        save_embeddings_to_db(computed_embs)
        
        # Convert to numpy for return
        for k, v in computed_embs.items():
            embeddings[k] = np.array(v)
            
    return embeddings

def cosine_similarity_scores(emb_dict, source_id, candidate_ids):
    """
    Computes cosine similarity between source node and candidates.
    
    Args:
        emb_dict (dict): node_id -> np.array
        source_id (str): Source node ID
        candidate_ids (list): List of candidate node IDs
        
    Returns:
        dict: {candidate_id: score}
    """
    if source_id not in emb_dict:
        return {}
        
    source_emb = emb_dict[source_id]
    source_norm = np.linalg.norm(source_emb)
    if source_norm == 0:
        return {cid: 0.0 for cid in candidate_ids}
        
    scores = {}
    for cid in candidate_ids:
        if cid not in emb_dict:
            scores[cid] = 0.0
            continue
            
        cand_emb = emb_dict[cid]
        cand_norm = np.linalg.norm(cand_emb)
        
        if cand_norm == 0:
            scores[cid] = 0.0
        else:
            sim = np.dot(source_emb, cand_emb) / (source_norm * cand_norm)
            scores[cid] = float(sim)
            
    return scores

def graph_heuristic_scores(G, source_id, candidate_ids, method="jaccard"):
    """
    Computes graph topology-based scores (Jaccard or Adamic-Adar).
    
    Args:
        G (nx.Graph): The graph (should be undirected for these metrics).
        source_id (str): Source node ID.
        candidate_ids (list): Candidate node IDs.
        method (str): 'jaccard' or 'adamic_adar'.
        
    Returns:
        dict: {candidate_id: score}
    """
    scores = {}
    valid_candidates = [cid for cid in candidate_ids if G.has_node(cid)]
    
    if not G.has_node(source_id):
        return {cid: 0.0 for cid in candidate_ids}

    pairs = [(source_id, cid) for cid in valid_candidates]
    
    try:
        if method == "adamic_adar":
            preds = nx.adamic_adar_index(G, pairs)
        else:
            preds = nx.jaccard_coefficient(G, pairs)
            
        for u, v, p in preds:
            scores[v] = p
            
    except Exception as e:
        print(f"Error computing heuristic {method}: {e}")
        
    # Fill missing with 0
    for cid in candidate_ids:
        if cid not in scores:
            scores[cid] = 0.0
            
    return scores

def combine_scores(cos_sim, heur, alpha=0.6):
    """
    Combines cosine similarity and heuristic scores.
    
    Args:
        cos_sim (dict): {node_id: cosine_score}
        heur (dict): {node_id: heuristic_score}
        alpha (float): Weight for cosine similarity (0.0 - 1.0).
        
    Returns:
        list: Sorted list of tuples (node_id, final_score, features_dict)
    """
    combined = []
    
    # Union of keys
    all_keys = set(cos_sim.keys()) | set(heur.keys())
    
    for nid in all_keys:
        c = cos_sim.get(nid, 0.0)
        h = heur.get(nid, 0.0)
        
        # Normalize heuristic if needed? 
        # Jaccard is 0-1. Adamic-Adar is unbounded but usually low. 
        # For simplicity, we assume raw addition or simple weighted sum.
        
        final = (alpha * c) + ((1 - alpha) * h)
        
        combined.append((nid, final, {"cosine_similarity": c, "heuristic_score": h}))
        
    # Sort descending
    combined.sort(key=lambda x: x[1], reverse=True)
    
    return combined

if __name__ == "__main__":
    # CLI Usage
    print("--- Graph Ops: Node Embeddings ---")
    
    # 1. Load Graph
    print("Loading graph from database...")
    G = load_graph_as_networkx()
    print(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
    
    if G.number_of_nodes() > 0:
        # 2. Get or Compute Embeddings
        embeddings = get_or_compute_embeddings(G, dimensions=64, walk_length=10, num_walks=100)
        
        # 3. Print Sample
        first_node = list(embeddings.keys())[0]
        print(f"\nSample Embedding for node '{first_node}':")
        print(embeddings[first_node][:5], "... (truncated)")
        
        # 4. Storage check
        # save_embeddings_to_db(embeddings) # Already done in get_or_compute if needed
    else:
        print("Graph is empty. Run graph_mapping.py first to populate data.")
