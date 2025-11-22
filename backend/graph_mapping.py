import sys
import os
import json

# Add the parent directory to sys.path to allow imports from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.fetchers.github import fetch_github_user, fetch_github_repos
from backend.fetchers.stackoverflow import fetch_so_user, fetch_so_top_tags
from backend.storage import upsert_node, insert_edge

# --- Canonical ID Helpers ---

def get_github_user_id(username):
    """Returns canonical ID for a GitHub user."""
    return f"github:{username.lower()}"

def get_so_user_id(user_id):
    """Returns canonical ID for a StackOverflow user."""
    return f"so:{user_id}"

def get_repo_id(full_name):
    """Returns canonical ID for a GitHub repository."""
    return f"repo:{full_name.lower()}"

def get_tag_id(tag_name):
    """Returns canonical ID for a StackOverflow tag."""
    return f"tag:{tag_name.lower()}"

# --- Main Logic ---

def normalize_and_merge_profiles(github_username, so_user_id=None):
    """
    Fetches GitHub and (optionally) StackOverflow data, normalizes it,
    and upserts nodes and edges into the graph database.

    Args:
        github_username (str): The GitHub username to fetch.
        so_user_id (int or str, optional): The StackOverflow user ID.

    Returns:
        dict: A summary of the operations performed (nodes/edges created).
    """
    summary = {
        "nodes_upserted": 0,
        "edges_inserted": 0,
        "errors": []
    }

    # 1. Fetch and Process GitHub User
    print(f"Fetching GitHub user: {github_username}...")
    gh_user = fetch_github_user(github_username)
    gh_node_id = None

    if gh_user:
        gh_node_id = get_github_user_id(github_username)
        upsert_node(gh_node_id, "github_user", gh_user)
        summary["nodes_upserted"] += 1
        
        # Fetch Repositories
        print(f"Fetching repos for {github_username}...")
        repos = fetch_github_repos(github_username)
        for repo in repos:
            repo_full_name = repo.get('full_name')
            if not repo_full_name:
                continue
                
            repo_node_id = get_repo_id(repo_full_name)
            upsert_node(repo_node_id, "github_repo", repo)
            summary["nodes_upserted"] += 1
            
            # Edge: CONTRIBUTED_TO (User -> Repo)
            insert_edge(gh_node_id, repo_node_id, "CONTRIBUTED_TO")
            summary["edges_inserted"] += 1
    else:
        summary["errors"].append(f"Failed to fetch GitHub user: {github_username}")

    # 2. Fetch and Process StackOverflow User
    so_node_id = None
    if so_user_id:
        print(f"Fetching StackOverflow user: {so_user_id}...")
        so_user = fetch_so_user(so_user_id)
        
        if so_user:
            so_node_id = get_so_user_id(so_user_id)
            upsert_node(so_node_id, "so_user", so_user)
            summary["nodes_upserted"] += 1
            
            # Fetch Tags
            print(f"Fetching tags for SO user {so_user_id}...")
            tags = fetch_so_top_tags(so_user_id)
            for tag in tags:
                tag_name = tag.get('tag_name')
                if not tag_name:
                    continue
                    
                tag_node_id = get_tag_id(tag_name)
                upsert_node(tag_node_id, "stackoverflow_tag", tag)
                summary["nodes_upserted"] += 1
                
                # Edge: HAS_TAG (User -> Tag)
                # Storing count and score as edge attributes
                edge_attrs = {
                    "count": tag.get('answer_count', 0),
                    "score": tag.get('answer_score', 0)
                }
                insert_edge(so_node_id, tag_node_id, "HAS_TAG", edge_attrs)
                summary["edges_inserted"] += 1
        else:
            summary["errors"].append(f"Failed to fetch SO user: {so_user_id}")

    # 3. Link Profiles (SAME_AS)
    # If both profiles were successfully fetched/created, link them.
    # This assumes the caller has verified these belong to the same person.
    if gh_node_id and so_node_id:
        print("Linking GitHub and StackOverflow profiles...")
        insert_edge(gh_node_id, so_node_id, "SAME_AS")
        insert_edge(so_node_id, gh_node_id, "SAME_AS") # Bidirectional
        summary["edges_inserted"] += 2

    return summary

if __name__ == "__main__":
    # Example Usage
    print("--- Graph Mapping Demo ---")
    
    # Example: Linus Torvalds (GitHub) and a dummy SO ID (or a real one if known)
    # Using a known SO ID for demonstration: 22656 (Jon Skeet) - obviously not Linus, but for structural test.
    # In a real scenario, you'd match them correctly.
    
    gh_user = "torvalds"
    so_id = 22656
    
    print(f"Normalizing and merging: GitHub={gh_user}, SO={so_id}")
    result = normalize_and_merge_profiles(gh_user, so_id)
    
    print("\nOperation Summary:")
    print(json.dumps(result, indent=2))
    
    # Note on CO_CONTRIB:
    # The CO_CONTRIB edge (Developer <-> Developer) represents two developers contributing to the same repository.
    # This edge is typically derived from the graph structure (User A -> Repo X <- User B) rather than direct API fetch.
    # To materialize it, one would query for all users connected to a repo and create edges between them.
