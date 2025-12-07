import os
import sys
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.storage import load_graph_as_networkx

def train_role_model():
    """
    Train a simple classifier to predict developer roles based on node embeddings.
    In a real scenario, we would need a labeled dataset of (user_id, role).
    Here, we will generate a synthetic labeled dataset for demonstration.
    """
    print("Loading graph...")
    G = load_graph_as_networkx()
    
    # 1. Collect Embeddings and Generate Synthetic Labels
    X = []
    y = []
    
    print("Generating synthetic training data...")
    for node, data in G.nodes(data=True):
        if data.get("type") == "github_user" and "embedding" in data:
            emb = data["embedding"]
            if isinstance(emb, list):
                emb = np.array(emb)
            
            # Robust Rule-Based Labeling for Synthetic Data
            bio = data.get("bio", "").lower() if data.get("bio") else ""
            
            # Collect languages from connected repos
            repo_languages = []
            try:
                neighbors = G.neighbors(node)
                for n in neighbors:
                    if G.nodes[n].get("type") == "github_repo":
                        lang = G.nodes[n].get("language")
                        if lang:
                            repo_languages.append(lang.lower())
            except:
                pass
                
            full_text = bio + " " + " ".join(repo_languages)
            
            # Scoring System
            scores = {
                "Data Scientist": 0,
                "Frontend Developer": 0,
                "Backend Developer": 0,
                "DevOps Engineer": 0,
                "Mobile Developer": 0,
                "Security Engineer": 0,
                "Game Developer": 0
            }
            
            # Keywords
            keywords = {
                "Data Scientist": ["data", "scientist", "analyst", "machine learning", "ai", "deep learning", "computer vision", "nlp", "pytorch", "tensorflow", "pandas", "numpy", "scikit", "keras", "python", "jupyter", "r"],
                "Frontend Developer": ["frontend", "ui", "ux", "react", "vue", "angular", "svelte", "nextjs", "nuxt", "html", "css", "tailwind", "bootstrap", "javascript", "typescript", "web", "design", "figma"],
                "Backend Developer": ["backend", "api", "server", "database", "sql", "postgres", "mongo", "django", "flask", "fastapi", "spring", "java", "c#", ".net", "node", "express", "nestjs", "go", "golang", "rust", "ruby", "rails", "php", "laravel", "microservices"],
                "DevOps Engineer": ["devops", "sre", "cloud", "aws", "azure", "gcp", "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins", "ci/cd", "linux", "bash", "shell"],
                "Mobile Developer": ["mobile", "android", "ios", "swift", "kotlin", "flutter", "react native", "dart", "obj-c", "app"],
                "Security Engineer": ["security", "cyber", "pentest", "hacker", "infosec", "vulnerability", "cryptography", "ctf"],
                "Game Developer": ["game", "unity", "unreal", "godot", "c++", "c#", "graphics", "opengl", "vulkan", "shader"]
            }
            
            for role, keys in keywords.items():
                for key in keys:
                    if key in full_text:
                        scores[role] += 1
            
            role = max(scores, key=scores.get)
            if scores[role] == 0:
                role = "Software Engineer"
            
            X.append(emb)
            y.append(role)
            
    if not X:
        print("No embeddings found in graph. Generating purely synthetic data for demonstration...")
        # Generate 50 random samples with 64 dimensions
        X = np.random.rand(50, 64)
        # Assign roles based on "synthetic features" (just to have classes)
        # In a real app, we'd map dimensions to features. Here we just want valid classes.
        roles = ["Frontend Developer", "Backend Developer", "Data Scientist", "DevOps Engineer", "Mobile Developer"]
        y = [np.random.choice(roles) for _ in range(50)]

    X = np.array(X)
    y = np.array(y)
    
    print(f"Training on {len(X)} samples...")
    
    # 2. Train Model
    # Logistic Regression is simple and effective for this
    clf = make_pipeline(StandardScaler(), LogisticRegression(multi_class='ovr'))
    clf.fit(X, y)
    
    # 3. Save Model
    model_dir = os.path.join(os.path.dirname(__file__), 'models')
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, 'role_clf.joblib')
    
    joblib.dump(clf, model_path)
    print(f"Model saved to {model_path}")
    print("Classes:", clf.classes_)

if __name__ == "__main__":
    train_role_model()
