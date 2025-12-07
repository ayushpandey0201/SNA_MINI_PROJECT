import re
import numpy as np
from typing import List, Union
from bs4 import BeautifulSoup

# Global model cache
_MODEL = None

# Disable tqdm globally for transformers if needed
import os
os.environ["TQDM_DISABLE"] = "1"

def _get_model(model_name='all-MiniLM-L6-v2'):
    """
    Singleton accessor for the SentenceTransformer model.
    """
    global _MODEL
    if _MODEL is None:
        print(f"Loading SentenceTransformer model: {model_name} (Force CPU)...")
        # Lazy import to avoid startup overhead/errors
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer(model_name, device='cpu')
    return _MODEL

def clean_html(html_content: str) -> str:
    """
    Cleans HTML content to plain text using BeautifulSoup.
    
    Args:
        html_content (str): The HTML string to clean.
        
    Returns:
        str: The plain text content.
    """
    if not html_content:
        return ""
    # Use lxml if available, else html.parser
    try:
        soup = BeautifulSoup(html_content, "lxml")
    except Exception:
        soup = BeautifulSoup(html_content, "html.parser")
        
    return soup.get_text(separator=" ", strip=True)

def extract_topics(texts: Union[str, List[str]], method='sbert+kmeans', num_clusters=3, top_n=5):
    """
    Extracts topic keywords from texts using SBERT embeddings and KMeans clustering.
    
    Args:
        texts: A single string (will be split by sentences) or a list of strings.
        method: Clustering method (default 'sbert+kmeans').
        num_clusters: Number of topics/clusters to find.
        top_n: Number of keywords to return per cluster.
        
    Returns:
        dict: {cluster_id: [keyword1, keyword2, ...]}
    """
    model = _get_model()
    
    # Preprocessing: Ensure we have a list of sentences/segments
    if isinstance(texts, str):
        # Simple sentence splitting: split on punctuation followed by space
        sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', texts) if s.strip()]
    else:
        sentences = [t.strip() for t in texts if t.strip()]
        
    if not sentences:
        return {}

    # Embed sentences
    # show_progress_bar=False to keep logs clean and avoid terminal size errors
    embeddings = model.encode(sentences, show_progress_bar=False)
    
    # Handle case where n_samples < n_clusters
    actual_n_clusters = min(num_clusters, len(sentences))
    if actual_n_clusters < 1:
        return {}

    # Clustering
    from sklearn.cluster import KMeans
    kmeans = KMeans(n_clusters=actual_n_clusters, random_state=42, n_init=10)
    kmeans.fit(embeddings)
    labels = kmeans.labels_
    
    # Extract keywords per cluster
    cluster_keywords = {}
    
    for i in range(actual_n_clusters):
        # Get all sentences belonging to this cluster
        cluster_sentences = [sentences[j] for j in range(len(sentences)) if labels[j] == i]
        combined_text = " ".join(cluster_sentences)
        
        # Use CountVectorizer to find frequent words (excluding stop words)
        try:
            from sklearn.feature_extraction.text import CountVectorizer
            vectorizer = CountVectorizer(stop_words='english', max_features=top_n)
            vectorizer.fit([combined_text])
            keywords = vectorizer.get_feature_names_out()
            cluster_keywords[i] = list(keywords)
        except ValueError:
            # Handle case where vocabulary is empty (e.g. only stop words or empty text)
            cluster_keywords[i] = []
            
    return cluster_keywords

def short_summary(text: Union[str, List[str]], num_sentences=2) -> str:
    """
    Generates a short summary by picking sentences closest to the centroid of the text.
    
    Args:
        text: Input text or list of sentences.
        num_sentences: Number of sentences to include in the summary.
        
    Returns:
        str: The summary text.
    """
    model = _get_model()
    
    if isinstance(text, str):
        sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', text) if s.strip()]
    else:
        sentences = [t.strip() for t in text if t.strip()]
        
    if not sentences:
        return ""
        
    if len(sentences) <= num_sentences:
        return " ".join(sentences)
        
    embeddings = model.encode(sentences, show_progress_bar=False)
    
    # Calculate centroid (mean of all embeddings)
    centroid = np.mean(embeddings, axis=0).reshape(1, -1)
    
    # Calculate cosine similarity of each sentence to the centroid
    from sklearn.metrics.pairwise import cosine_similarity
    similarities = cosine_similarity(embeddings, centroid).flatten()
    
    # Get top N indices
    top_indices = np.argsort(similarities)[-num_sentences:]
    top_indices = sorted(top_indices) # Sort to keep original order of flow
    
    summary_sentences = [sentences[i] for i in top_indices]
    return " ".join(summary_sentences)

def generate_bio_summary(profile, research_highlights=None):
    """
    Generate a comprehensive professional summary in 5-6 lines (medium length).
    Structure:
    1. Professional Identity (Role, Location, Company)
    2. Technical Expertise (Languages, Skills)
    3. Key Projects/Contributions
    4. Community Impact (Stars, Reputation)
    5. Focus Areas/Topics
    6. Research Interests (if applicable)
    """
    gh = profile.get("github_stats", {})
    so = profile.get("so_stats", {})
    langs = profile.get("top_repo_languages", [])
    topics = profile.get("top_topics", [])
    activity = profile.get("activity_counts", {})
    top_repos = profile.get("top_active_repos", [])
    
    # Name
    name = gh.get("name") or gh.get("login") or "The user"
    
    summary_lines = []
    
    # --- Line 1: Professional Identity ---
    role_parts = []
    if langs:
        top_lang = langs[0][0]
        role_parts.append(f"{top_lang} Developer")
    else:
        role_parts.append("Developer")
        
    if gh.get("company"):
        role_parts.append(f"at {gh.get('company')}")
        
    location = gh.get("location")
    loc_str = f" based in {location}" if location else ""
    
    line1 = f"{name} is a {' '.join(role_parts)}{loc_str}."
    summary_lines.append(line1)
    
    # --- Line 2: Technical Stack ---
    if langs:
        top_3_langs = [l[0] for l in langs[:3]]
        stack_str = ", ".join(top_3_langs)
        line2 = f"They specialize in {stack_str} and have expertise in modern software development practices."
    else:
        line2 = f"They are an active software developer with a focus on building scalable applications."
    summary_lines.append(line2)
    
    # --- Line 3: Key Projects/Work ---
    if top_repos and len(top_repos) > 0:
        top_repo_names = [r.get("name") for r in top_repos[:3] if r.get("name")]
        if top_repo_names:
            repo_str = ", ".join(top_repo_names)
            line3 = f"Their notable contributions include projects like {repo_str}, demonstrating their commitment to open-source development."
        else:
            repos_count = activity.get("repo_count", 0)
            line3 = f"They maintain {repos_count} repositories, showcasing their active involvement in software development."
    else:
        repos_count = activity.get("repo_count", 0)
        line3 = f"They have contributed to {repos_count} repositories, demonstrating their active involvement in software development."
    summary_lines.append(line3)
    
    # --- Line 4: Community Impact ---
    impact_parts = []
    stars = activity.get("total_stars", 0)
    repos = activity.get("repo_count", 0)
    
    if stars > 0:
        impact_parts.append(f"earned {stars:,} stars")
    if so and so.get("reputation", 0) > 0:
        rep = so.get("reputation")
        impact_parts.append(f"built a StackOverflow reputation of {rep:,}")
        
    if impact_parts:
        line4 = f"In the developer community, they have {' and '.join(impact_parts)}."
    else:
        line4 = f"They actively participate in the developer community through their contributions and collaborations."
    summary_lines.append(line4)

    # --- Line 5: Focus Areas ---
    if topics:
        clean_topics = [t for t in topics[:5] if len(t) > 2]
        if clean_topics:
            topic_str = ", ".join(clean_topics[:3])  # Top 3 topics
            line5 = f"Their work primarily focuses on {topic_str}, reflecting their deep interest in these domains."
        else:
            line5 = f"They are passionate about software engineering and continuously explore new technologies and methodologies."
    else:
        line5 = f"They are passionate about software engineering and continuously explore new technologies and methodologies."
    summary_lines.append(line5)

    # --- Line 6: Research/Additional Context (if applicable) ---
    if research_highlights:
        first_paper = research_highlights[0]
        paper_title = first_paper.get("title", "")
        paper_title = re.sub(r"^Page \d+:\s*", "", paper_title)
        if paper_title:
            # Truncate if too long
            if len(paper_title) > 60:
                paper_title = paper_title[:57] + "..."
            line6 = f"Their interests align with current research trends, particularly in areas related to {paper_title}."
            summary_lines.append(line6)
    elif gh.get("bio"):
        # Use bio if available and not too long
        bio = gh.get("bio", "")
        if bio and len(bio) < 150:
            line6 = f"{bio}"
            summary_lines.append(line6)
    
    # Ensure we have 5-6 lines
    if len(summary_lines) < 5:
        # Add a generic closing line if needed
        summary_lines.append("They are dedicated to creating high-quality software solutions and contributing to the open-source ecosystem.")
    
    # Join with single newline (not double) for medium-sized paragraphs
    return "\n".join(summary_lines[:6])  # Max 6 lines

if __name__ == "__main__":
    # Example Usage
    sample_readme = """
    <h1>GitStack Connect Social Network Analysis</h1>
    <p>This project aims to analyze developer networks using graph theory and machine learning. 
    We fetch data from GitHub and StackOverflow to build a comprehensive graph of developers, repositories, and tags.
    The system uses Node2Vec for generating embeddings and Logistic Regression for role classification.
    It is built with FastAPI and NetworkX.</p>
    <p>Installation is simple. Just run pip install -r requirements.txt. 
    Make sure to set up your environment variables in the .env file.</p>
    """
    
    print("--- Cleaning HTML ---")
    clean_text = clean_html(sample_readme)
    print(f"Cleaned Text: {clean_text}")
    
    print("\n--- Extracting Topics (2 clusters) ---")
    topics = extract_topics(clean_text, num_clusters=2)
    print(f"Topics: {topics}")
    
    print("\n--- Generating Summary (1 sentence) ---")
    summary = short_summary(clean_text, num_sentences=1)
    print(f"Summary: {summary}")

def classify_role_from_text(text: str) -> dict:
    """
    Classify a developer's role based on text content (Bio, READMEs, etc.)
    using keyword frequency analysis.
    
    Args:
        text (str): The input text corpus.
        
    Returns:
        dict: Dictionary of role probabilities.
    """
    if not text:
        return {}
        
    text = text.lower()
    
    # Expanded Keyword Dictionary
    keywords = {
        "Data Scientist": [
            "data scientist", "data analyst", "machine learning", "deep learning", "artificial intelligence", 
            "computer vision", "nlp", "natural language processing", "pytorch", "tensorflow", "keras", 
            "scikit-learn", "pandas", "numpy", "matplotlib", "seaborn", "jupyter", "kaggle", "big data", 
            "hadoop", "spark", "r language", "statistics", "regression", "clustering", "neural network", "llm", "transformer"
        ],
        "Frontend Developer": [
            "frontend", "front-end", "ui/ux", "user interface", "react", "reactjs", "vue", "vuejs", 
            "angular", "svelte", "next.js", "nuxt", "html5", "css3", "sass", "less", "tailwind", 
            "bootstrap", "material ui", "chakra ui", "javascript", "typescript", "webpack", "vite", 
            "responsive design", "accessibility", "a11y", "figma", "adobe xd"
        ],
        "Backend Developer": [
            "backend", "back-end", "server-side", "api", "restful", "graphql", "database", "sql", "nosql",
            "postgresql", "mysql", "mongodb", "redis", "django", "flask", "fastapi", "spring boot", 
            "nodejs", "express", "nestjs", "golang", "rust", "ruby on rails", "php", "laravel", 
            "microservices", "docker", "kubernetes", "system design", "distributed systems"
        ],
        "DevOps Engineer": [
            "devops", "sre", "site reliability", "ci/cd", "continuous integration", "jenkins", 
            "github actions", "gitlab ci", "circleci", "travis ci", "docker", "kubernetes", "k8s", 
            "helm", "terraform", "ansible", "chef", "puppet", "aws", "amazon web services", "azure", 
            "google cloud", "gcp", "linux", "bash", "shell scripting", "monitoring", "prometheus", "grafana"
        ],
        "Mobile Developer": [
            "mobile app", "ios", "android", "swift", "swiftui", "kotlin", "jetpack compose", 
            "flutter", "dart", "react native", "xcode", "android studio", "mobile development"
        ],
        "Security Engineer": [
            "cyber security", "infosec", "penetration testing", "pentesting", "ethical hacking", 
            "vulnerability", "exploit", "cryptography", "network security", "appsec", "owasp", 
            "reverse engineering", "malware", "forensics", "ctf"
        ],
        "Game Developer": [
            "game development", "gamedev", "unity", "unity3d", "unreal engine", "godot", "c#", "c++", 
            "shader", "opengl", "vulkan", "directx", "3d graphics", "blender", "game design"
        ]
    }
    
    scores = {role: 0 for role in keywords}
    total_hits = 0
    
    for role, keys in keywords.items():
        for key in keys:
            # Simple substring match, can be improved with regex for word boundaries
            count = text.count(key)
            if count > 0:
                # Weight matches by length of keyword (longer phrases are more specific)
                weight = 1 + (len(key.split()) * 0.5)
                scores[role] += count * weight
                total_hits += count * weight
                
    if total_hits == 0:
        return {}
        
    # Normalize to probabilities
    probabilities = {role: round(score / total_hits, 4) for role, score in scores.items()}
    return probabilities
