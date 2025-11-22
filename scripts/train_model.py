import sys
import os
import json
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.storage import load_graph_as_networkx

def train_role_classifier():
    # 1. Load Graph and Embeddings
    print("Loading graph from database...")
    G = load_graph_as_networkx()
    print(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")

    # 2. Prepare Data
    data = []

    # Define heuristics
    ML_KEYWORDS = {'python', 'jupyter', 'tensorflow', 'pytorch', 'scikit-learn', 'numpy', 'pandas', 'machine-learning', 'deep-learning', 'data-science', 'keras', 'cv', 'nlp', 'r', 'julia'}
    WEB_KEYWORDS = {'javascript', 'typescript', 'html', 'css', 'react', 'vue', 'angular', 'node', 'django', 'flask', 'web', 'frontend', 'backend', 'php', 'laravel', 'ruby', 'rails', 'java', 'spring'}
    DEVOPS_KEYWORDS = {'docker', 'kubernetes', 'aws', 'jenkins', 'ansible', 'terraform', 'ci/cd', 'devops', 'bash', 'shell', 'go', 'golang', 'linux', 'cloud', 'c', 'c++', 'rust', 'systems'}

    def determine_role(languages, tags):
        all_terms = [str(t).lower() for t in languages + tags]
        ml_score = sum(1 for item in all_terms if item in ML_KEYWORDS)
        web_score = sum(1 for item in all_terms if item in WEB_KEYWORDS)
        devops_score = sum(1 for item in all_terms if item in DEVOPS_KEYWORDS)
        
        scores = {'ml': ml_score, 'web': web_score, 'devops': devops_score}
        best_role = max(scores, key=scores.get)
        
        if scores[best_role] == 0:
            return 'unknown'
        return best_role

    print("Extracting features and labels...")
    for node_id, attrs in G.nodes(data=True):
        if attrs.get('type') not in ['github_user', 'so_user']:
            continue
            
        embedding = attrs.get('embedding')
        if not embedding:
            continue
            
        # Handle embedding if it's a string (JSON)
        if isinstance(embedding, str):
            try:
                embedding = json.loads(embedding)
            except json.JSONDecodeError:
                continue
                
        languages = []
        tags = []
        
        for neighbor in G.neighbors(node_id):
            n_attrs = G.nodes[neighbor]
            
            if n_attrs.get('type') == 'github_repo':
                lang = n_attrs.get('language')
                if lang:
                    languages.append(lang)
            elif n_attrs.get('type') == 'stackoverflow_tag':
                tag_name = n_attrs.get('tag_name')
                if tag_name:
                    tags.append(tag_name)
            elif n_attrs.get('type') == 'so_user' and attrs.get('type') == 'github_user':
                 for so_neighbor in G.neighbors(neighbor):
                     so_n_attrs = G.nodes[so_neighbor]
                     if so_n_attrs.get('type') == 'stackoverflow_tag':
                         tag_name = so_n_attrs.get('tag_name')
                         if tag_name:
                             tags.append(tag_name)
        
        role = determine_role(languages, tags)
        
        if role != 'unknown':
            data.append({
                'node_id': node_id,
                'embedding': embedding,
                'role': role,
                'languages': languages,
                'tags': tags
            })

    df = pd.DataFrame(data)
    print(f"Found {len(df)} labeled users.")
    if len(df) > 0:
        print(df['role'].value_counts())

    # 3. Train Classifier
    if len(df) < 2 or len(df['role'].unique()) < 2:
        print("Not enough data or classes to train. Please fetch more diverse data.")
        return

    X = np.array(df['embedding'].tolist())
    y = df['role']
    
    print(f"Training on {len(X)} samples...")
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    except ValueError:
        # Fallback if not enough samples for split
        X_train, y_train = X, y
        X_test, y_test = [], []
    
    clf = LogisticRegression(max_iter=1000, multi_class='ovr')
    clf.fit(X_train, y_train)
    
    # 4. Evaluation
    if len(X_test) > 0:
        y_pred = clf.predict(X_test)
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
    
    # 5. Save Model
    model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'models'))
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, 'role_clf.joblib')
    joblib.dump(clf, model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    train_role_classifier()
