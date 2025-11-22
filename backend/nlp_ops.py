import re
import numpy as np
from typing import List, Union
from bs4 import BeautifulSoup
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# Global model cache to avoid reloading
_MODEL = None

def _get_model(model_name='all-MiniLM-L6-v2'):
    """
    Singleton accessor for the SentenceTransformer model.
    """
    global _MODEL
    if _MODEL is None:
        print(f"Loading SentenceTransformer model: {model_name}...")
        _MODEL = SentenceTransformer(model_name)
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
    # show_progress_bar=False to keep logs clean
    embeddings = model.encode(sentences, show_progress_bar=False)
    
    # Handle case where n_samples < n_clusters
    actual_n_clusters = min(num_clusters, len(sentences))
    if actual_n_clusters < 1:
        return {}

    # Clustering
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
    similarities = cosine_similarity(embeddings, centroid).flatten()
    
    # Get top N indices
    top_indices = np.argsort(similarities)[-num_sentences:]
    top_indices = sorted(top_indices) # Sort to keep original order of flow
    
    summary_sentences = [sentences[i] for i in top_indices]
    return " ".join(summary_sentences)

def generate_bio_summary(profile):
    """
    Generate a comprehensive professional summary using GitHub and StackOverflow data.
    """
    gh = profile.get("github_stats", {})
    so = profile.get("so_stats", {})
    langs = profile.get("top_repo_languages", [])
    topics = profile.get("top_topics", [])
    activity = profile.get("activity_counts", {})
    
    # Name
    name = gh.get("name") or gh.get("login") or "The user"
    
    summary_parts = []
    
    # 1. Intro & Focus
    intro = f"{name} is a developer"
    if gh.get("location"):
        intro += f" based in {gh.get('location')}"
    if gh.get("company"):
        intro += f", currently working at {gh.get('company')}"
    intro += "."
    summary_parts.append(intro)
    
    # 2. Languages
    if langs:
        top_langs = [l[0] for l in langs[:3]]
        if len(top_langs) > 1:
            lang_str = ", ".join(top_langs[:-1]) + " and " + top_langs[-1]
        else:
            lang_str = top_langs[0]
        summary_parts.append(f"They primarily specialize in {lang_str}.")
        
    # 3. GitHub Trust/Work
    stars = activity.get("total_stars", 0)
    followers = gh.get("followers", 0)
    
    if stars > 500:
        summary_parts.append(f"They have a significant open-source impact with over {stars:,} stars across their repositories.")
    elif followers > 100:
        summary_parts.append(f"They are an active member of the community with {followers:,} followers.")
        
    # 4. StackOverflow Trust
    if so and so.get("reputation", 0) > 0:
        rep = so.get("reputation")
        badges = so.get("badge_counts", {})
        gold = badges.get("gold", 0)
        
        so_part = f"On StackOverflow, they are a trusted contributor with {rep:,} reputation points"
        if gold > 0:
            so_part += f" and {gold} gold badges."
        else:
            so_part += "."
        summary_parts.append(so_part)

    # 5. Topics
    if topics:
        # Filter out generic topics if possible, but for now just take top 5
        clean_topics = [t for t in topics[:5] if len(t) > 2]
        if clean_topics:
            topic_str = ", ".join(clean_topics)
            summary_parts.append(f"Their work focuses on areas such as {topic_str}.")

    return " ".join(summary_parts)

if __name__ == "__main__":
    # Example Usage
    sample_readme = """
    <h1>Dev-Intel Social Network Analysis</h1>
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
