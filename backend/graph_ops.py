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

if __name__ == "__main__":
    # CLI Usage
    print("--- Graph Ops: Node Embeddings ---")
    
    # 1. Load Graph
    print("Loading graph from database...")
    G = load_graph_as_networkx()
    print(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
    
    if G.number_of_nodes() > 0:
        # 2. Compute Embeddings
        # Using deterministic seed
        embeddings = compute_node2vec_embeddings(G, dimensions=64, walk_length=10, num_walks=100, seed=42)
        
        # 3. Save to DB
        save_embeddings_to_db(embeddings)
        
        # 4. Print Sample
        first_node = list(embeddings.keys())[0]
        print(f"\nSample Embedding for node '{first_node}':")
        print(embeddings[first_node][:5], "... (truncated)")
    else:
        print("Graph is empty. Run graph_mapping.py first to populate data.")
