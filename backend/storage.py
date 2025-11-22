import json
import sys
import os

# Add the parent directory to sys.path to allow imports from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import Column, String, Text, Integer
import networkx as nx
from backend.db import Base, engine, SessionLocal

# Define Models
class Node(Base):
    __tablename__ = "nodes"
    id = Column(String, primary_key=True, index=True)
    type = Column(String)
    attrs = Column(Text) # JSON string

class Edge(Base):
    __tablename__ = "edges"
    id = Column(Integer, primary_key=True, index=True)
    src = Column(String, index=True)
    dst = Column(String, index=True)
    rel = Column(String)
    attrs = Column(Text) # JSON string

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def upsert_node(node_id, node_type, attributes=None):
    """
    Insert or update a node in the database.
    """
    session = SessionLocal()
    try:
        if attributes is None:
            attributes = {}
        
        # Check if node exists
        node = session.query(Node).filter(Node.id == node_id).first()
        if node:
            node.type = node_type
            node.attrs = json.dumps(attributes)
        else:
            node = Node(id=node_id, type=node_type, attrs=json.dumps(attributes))
            session.add(node)
        
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error upserting node {node_id}: {e}")
    finally:
        session.close()

def insert_edge(src, dst, rel, attributes=None):
    """
    Insert an edge into the database.
    """
    session = SessionLocal()
    try:
        if attributes is None:
            attributes = {}
            
        edge = Edge(src=src, dst=dst, rel=rel, attrs=json.dumps(attributes))
        session.add(edge)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error inserting edge {src}->{dst}: {e}")
    finally:
        session.close()

def load_graph_as_networkx():
    """
    Load the entire graph from the database into a NetworkX DiGraph.
    """
    session = SessionLocal()
    G = nx.DiGraph()
    
    try:
        nodes = session.query(Node).all()
        for node in nodes:
            attrs = json.loads(node.attrs) if node.attrs else {}
            attrs['type'] = node.type
            G.add_node(node.id, **attrs)
            
        edges = session.query(Edge).all()
        for edge in edges:
            attrs = json.loads(edge.attrs) if edge.attrs else {}
            attrs['relation'] = edge.rel
            G.add_edge(edge.src, edge.dst, **attrs)
            
        return G
    except Exception as e:
        print(f"Error loading graph: {e}")
        return nx.DiGraph()
    finally:
        session.close()

if __name__ == "__main__":
    # Example Usage
    print("--- Storage Demo ---")
    
    # 1. Upsert Nodes
    print("Upserting node 'torvalds'...")
    upsert_node("torvalds", "github_user", {"name": "Linus Torvalds", "location": "Portland"})
    
    print("Upserting node 'linux'...")
    upsert_node("linux", "github_repo", {"language": "C", "stars": 100000})
    
    # 2. Insert Edge
    print("Inserting edge 'torvalds' -> 'linux'...")
    insert_edge("torvalds", "linux", "CONTRIBUTED_TO", {"commits": 1000})
    
    # 3. Load and Verify
    print("Loading graph into NetworkX...")
    g = load_graph_as_networkx()
    
    print(f"\nGraph Stats:")
    print(f"Nodes: {g.number_of_nodes()}")
    print(f"Edges: {g.number_of_edges()}")
    
    print("\nNode Data:")
    for n, d in g.nodes(data=True):
        print(f" - {n}: {d}")
        
    print("\nEdge Data:")
    for u, v, d in g.edges(data=True):
        print(f" - {u} -> {v}: {d}")
