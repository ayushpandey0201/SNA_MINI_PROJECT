"""
Enrichment module for creating merged developer profiles.

This module combines GitHub activity and StackOverflow tags into a single
flattened feature dictionary suitable for ML models and UI display.
"""

import sys
import os
from typing import Optional, Dict, Any, List
from collections import Counter

# Add the parent directory to sys.path to allow imports from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.fetchers.github import fetch_github_user, fetch_github_repos, fetch_repo_readme
from backend.fetchers.stackoverflow import fetch_so_user, fetch_so_top_tags
from backend.storage import upsert_node, insert_edge
from backend.nlp_ops import extract_topics, short_summary, clean_html, generate_bio_summary
from backend.graph_mapping import (
    get_github_user_id, 
    get_so_user_id, 
    get_repo_id, 
    get_tag_id
)


def enrich_profile(github_username: str, so_user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Create a merged developer profile combining GitHub activity and StackOverflow tags.
    
    This function:
    1. Fetches GitHub user, repos, and README texts
    2. Fetches StackOverflow tags if so_user_id is provided
    3. Upserts nodes and edges into the database
    4. Extracts features: top_repo_languages, top_so_tags, top_topics, activity_counts
    5. Returns a merged JSON profile with these fields and node IDs
    
    Args:
        github_username (str): GitHub username to fetch
        so_user_id (int, optional): StackOverflow user ID
        
    Returns:
        dict: Enriched profile containing:
            - node_ids: dict with github_user_id, so_user_id (if available)
            - github_stats: followers, public_repos, etc.
            - so_stats: reputation, badges, etc. (if available)
            - top_repo_languages: list of (language, count) tuples
            - top_so_tags: list of (tag, score) tuples (if available)
            - top_topics: list of extracted topic keywords
            - activity_counts: dict with repo_count, total_stars, total_forks
            - bio_summary: short summary of user bio/README content
            - errors: list of any errors encountered
    """
    profile = {
        "node_ids": {},
        "github_stats": {},
        "so_stats": {},
        "top_repo_languages": [],
        "top_so_tags": [],
        "top_topics": [],
        "activity_counts": {
            "repo_count": 0,
            "total_stars": 0,
            "total_forks": 0
        },
        "bio_summary": "",
        "errors": []
    }
    
    # ===== GITHUB DATA =====
    print(f"Fetching GitHub user: {github_username}...")
    gh_user = fetch_github_user(github_username)
    
    if not gh_user:
        profile["errors"].append(f"Failed to fetch GitHub user: {github_username}")
        return profile
    
    # Store GitHub node ID
    gh_node_id = get_github_user_id(github_username)
    profile["node_ids"]["github_user_id"] = gh_node_id
    
    # Upsert GitHub user node
    upsert_node(gh_node_id, "github_user", gh_user)
    
    # Extract GitHub stats
    profile["github_stats"] = {
        "login": gh_user.get("login"),
        "name": gh_user.get("name"),
        "bio": gh_user.get("bio"),
        "company": gh_user.get("company"),
        "location": gh_user.get("location"),
        "email": gh_user.get("email"),
        "followers": gh_user.get("followers", 0),
        "following": gh_user.get("following", 0),
        "public_repos": gh_user.get("public_repos", 0),
        "public_gists": gh_user.get("public_gists", 0),
        "created_at": gh_user.get("created_at"),
        "updated_at": gh_user.get("updated_at")
    }
    
    # Fetch repositories
    print(f"Fetching repos for {github_username}...")
    repos = fetch_github_repos(github_username)
    
    language_counter = Counter()
    total_stars = 0
    total_forks = 0
    readme_texts = []
    
    for repo in repos:
        repo_full_name = repo.get('full_name')
        if not repo_full_name:
            continue
        
        # Upsert repo node
        repo_node_id = get_repo_id(repo_full_name)
        upsert_node(repo_node_id, "github_repo", repo)
        
        # Create edge: User -> Repo
        insert_edge(gh_node_id, repo_node_id, "CONTRIBUTED_TO")
        
        # Collect language stats
        lang = repo.get('language')
        if lang:
            language_counter[lang] += 1
        
        # Collect activity stats
        total_stars += repo.get('stargazers_count', 0)
        total_forks += repo.get('forks_count', 0)
        
        # Fetch README for top repos (by stars)
        if repo.get('stargazers_count', 0) > 10:  # Only fetch READMEs for popular repos
            owner, repo_name = repo_full_name.split('/')
            readme = fetch_repo_readme(owner, repo_name)
            if readme:
                readme_texts.append(readme)
    
    # Update activity counts
    profile["activity_counts"]["repo_count"] = len(repos)
    profile["activity_counts"]["total_stars"] = total_stars
    profile["activity_counts"]["total_forks"] = total_forks
    
    # Top languages
    profile["top_repo_languages"] = language_counter.most_common(10)
    
    # ===== STACKOVERFLOW DATA =====
    if so_user_id:
        print(f"Fetching StackOverflow user: {so_user_id}...")
        so_user = fetch_so_user(so_user_id)
        
        if so_user:
            so_node_id = get_so_user_id(so_user_id)
            profile["node_ids"]["so_user_id"] = so_node_id
            
            # Upsert SO user node
            upsert_node(so_node_id, "so_user", so_user)
            
            # Extract SO stats
            profile["so_stats"] = {
                "display_name": so_user.get("display_name"),
                "reputation": so_user.get("reputation", 0),
                "badge_counts": so_user.get("badge_counts", {}),
                "account_id": so_user.get("account_id"),
                "creation_date": so_user.get("creation_date"),
                "location": so_user.get("location")
            }
            
            # Link GitHub <-> StackOverflow
            insert_edge(gh_node_id, so_node_id, "SAME_AS")
            insert_edge(so_node_id, gh_node_id, "SAME_AS")
            
            # Fetch tags
            print(f"Fetching tags for SO user {so_user_id}...")
            tags = fetch_so_top_tags(so_user_id)
            
            tag_scores = []
            for tag in tags:
                tag_name = tag.get('tag_name')
                if not tag_name:
                    continue
                
                # Upsert tag node
                tag_node_id = get_tag_id(tag_name)
                upsert_node(tag_node_id, "stackoverflow_tag", tag)
                
                # Create edge: SO User -> Tag
                edge_attrs = {
                    "count": tag.get('answer_count', 0),
                    "score": tag.get('answer_score', 0)
                }
                insert_edge(so_node_id, tag_node_id, "HAS_TAG", edge_attrs)
                
                # Collect tag scores
                tag_scores.append((tag_name, tag.get('answer_score', 0)))
            
            profile["top_so_tags"] = sorted(tag_scores, key=lambda x: x[1], reverse=True)[:10]
        else:
            profile["errors"].append(f"Failed to fetch SO user: {so_user_id}")
    
    # ===== NLP ENRICHMENT =====
    print("Extracting topics and generating summary...")
    
    # Combine bio and README texts for NLP
    text_corpus = []
    if gh_user.get("bio"):
        text_corpus.append(gh_user.get("bio"))
    
    # Clean and combine README texts
    for readme in readme_texts[:5]:  # Limit to top 5 READMEs to avoid overwhelming NLP
        cleaned = clean_html(readme)
        if cleaned:
            text_corpus.append(cleaned[:1000])  # Limit each README to 1000 chars
    
    if text_corpus:
        combined_text = " ".join(text_corpus)
        
        # Extract topics
        try:
            topics_dict = extract_topics(combined_text, num_clusters=3, top_n=5)
            # Flatten topics into a single list
            all_topics = []
            for cluster_topics in topics_dict.values():
                all_topics.extend(cluster_topics)
            profile["top_topics"] = list(set(all_topics))[:10]  # Deduplicate and limit
        except Exception as e:
            profile["errors"].append(f"Topic extraction failed: {e}")
        
        # Generate summary
        try:
            # Use structured heuristic summary
            summary = generate_bio_summary(profile)
            profile["bio_summary"] = summary
        except Exception as e:
            profile["errors"].append(f"Summary generation failed: {e}")
    
    return profile


if __name__ == "__main__":
    # Example usage
    import json
    
    print("=== Enrichment Demo ===\n")
    
    # Test with a well-known developer
    username = "gaearon"  # Dan Abramov (React core team)
    
    print(f"Enriching profile for: {username}\n")
    enriched = enrich_profile(username)
    
    print("\n=== Enriched Profile ===")
    print(json.dumps(enriched, indent=2, default=str))
