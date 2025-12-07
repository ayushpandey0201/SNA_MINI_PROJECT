import os
import requests
import base64
import sys

# Attempt to load environment variables if not already loaded
try:
    from dotenv import load_dotenv
    # Explicitly load from the backend directory
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(backend_dir, '.env')
    load_dotenv(env_path)
except ImportError:
    pass

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

def fetch_github_user(username):
    """
    Fetch GitHub user metadata.
    
    Args:
        username (str): GitHub username.
        
    Returns:
        dict: User metadata or None if failed.
    """
    url = f"https://api.github.com/users/{username}"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching user {username}: {e}", file=sys.stderr)
        return None

def fetch_github_repos(username, per_page=100):
    """
    Fetch ALL GitHub user repositories (handling pagination).
    
    Args:
        username (str): GitHub username.
        per_page (int): Number of repos per page (max 100).
        
    Returns:
        list: List of all repository dicts.
    """
    url = f"https://api.github.com/users/{username}/repos"
    all_repos = []
    page = 1
    
    while True:
        params = {"per_page": per_page, "page": page, "type": "all"}
        try:
            response = requests.get(url, headers=HEADERS, params=params)
            response.raise_for_status()
            repos = response.json()
            
            if not repos:
                break
                
            all_repos.extend(repos)
            
            if len(repos) < per_page:
                break
                
            page += 1
            
        except requests.RequestException as e:
            print(f"Error fetching repos for {username} (page {page}): {e}", file=sys.stderr)
            break
            
    return all_repos

def fetch_repo_readme(owner, repo):
    """
    Fetch and decode repository README.
    
    Args:
        owner (str): Repository owner.
        repo (str): Repository name.
        
    Returns:
        str: Decoded README content or None if failed.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        content = data.get("content", "")
        encoding = data.get("encoding", "")
        
        if encoding == "base64":
            return base64.b64decode(content).decode("utf-8", errors="replace")
        else:
            return content
    except requests.RequestException as e:
        if e.response is not None and e.response.status_code == 404:
            # README not found, this is common and not an error
            return None
        print(f"Error fetching README for {owner}/{repo}: {e}", file=sys.stderr)
        return None

def fetch_repo_contributors(owner, repo, limit=5):
    """
    Fetch contributors for a repository.
    
    Args:
        owner (str): Repository owner.
        repo (str): Repository name.
        limit (int): Max contributors to return.
        
    Returns:
        list: List of contributor dicts (login, avatar_url, etc.)
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
    params = {"per_page": limit}
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        
        if response.status_code == 204:
            return []
            
        response.raise_for_status()
        
        if not response.content:
            return []
            
        return response.json()
    except requests.RequestException as e:
        if e.response is not None and e.response.status_code == 403:
            # 403 Forbidden (often due to repo size or rate limits on contributors endpoint)
            # Log as warning but don't fail
            print(f"Warning: Access forbidden (403) for contributors of {owner}/{repo}. Skipping.", file=sys.stderr)
            return []
        elif e.response is not None and e.response.status_code == 404:
             return []
             
        print(f"Error fetching contributors for {owner}/{repo}: {e}", file=sys.stderr)
        return []
    except ValueError as e:
        print(f"Error decoding JSON for {owner}/{repo}: {e}", file=sys.stderr)
        return []

def fetch_user_commit_stats(owner, repo, username):
    """
    Fetch detailed commit statistics for a specific user in a repository.
    
    Args:
        owner (str): Repository owner.
        repo (str): Repository name.
        username (str): GitHub username to get stats for.
        
    Returns:
        dict: Statistics including commits, additions, deletions, and last commit date.
    """
    stats = {
        "commits": 0,
        "additions": 0,
        "deletions": 0,
        "total_changes": 0,
        "last_commit_date": None,
        "commit_frequency": 0  # commits per month (estimated)
    }
    
    try:
        # Get commits by author
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        params = {
            "author": username,
            "per_page": 100,  # Get up to 100 commits for stats
            "page": 1
        }
        
        all_commits = []
        page = 1
        
        while page <= 3:  # Limit to 3 pages (300 commits max) to avoid rate limits
            params["page"] = page
            response = requests.get(url, headers=HEADERS, params=params)
            
            if response.status_code == 404:
                break
            if response.status_code == 403:
                # Rate limited or forbidden - return what we have
                break
                
            response.raise_for_status()
            commits = response.json()
            
            if not commits:
                break
                
            all_commits.extend(commits)
            
            if len(commits) < 100:
                break
                
            page += 1
        
        if not all_commits:
            return stats
        
        stats["commits"] = len(all_commits)
        
        # Get the first commit date (oldest) and last commit date (newest)
        if all_commits:
            commit_dates = [c.get("commit", {}).get("author", {}).get("date") for c in all_commits if c.get("commit", {}).get("author", {}).get("date")]
            if commit_dates:
                stats["last_commit_date"] = max(commit_dates)  # Most recent commit
        
        # Fetch detailed stats for a sample of commits to estimate additions/deletions
        # We'll use the contributors API which gives us aggregated stats
        contributors_url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
        contributors_response = requests.get(contributors_url, headers=HEADERS, params={"per_page": 100})
        
        if contributors_response.status_code == 200:
            contributors = contributors_response.json()
            for contrib in contributors:
                if contrib.get("login", "").lower() == username.lower():
                    # GitHub contributors API provides additions/deletions in some cases
                    # But it's not always available, so we'll use commit count as primary metric
                    stats["commits"] = contrib.get("contributions", stats["commits"])
                    break
        
        # Calculate total changes estimate (if we had additions/deletions, use them)
        stats["total_changes"] = stats["additions"] + stats["deletions"]
        
        # Estimate commit frequency (commits per month)
        if stats["last_commit_date"] and len(all_commits) > 1 and commit_dates:
            from datetime import datetime
            try:
                last_date = datetime.fromisoformat(stats["last_commit_date"].replace('Z', '+00:00'))
                first_date = datetime.fromisoformat(min(commit_dates).replace('Z', '+00:00'))  # Oldest commit
                days_diff = (last_date - first_date).days
                if days_diff > 0:
                    months = days_diff / 30.0
                    stats["commit_frequency"] = stats["commits"] / months if months > 0 else stats["commits"]
            except Exception as e:
                # Silently fail - frequency calculation is optional
                pass
        
    except requests.RequestException as e:
        # Silently fail - we'll use basic commit count from contributors API
        pass
    except Exception as e:
        print(f"Error fetching commit stats for {owner}/{repo}: {e}", file=sys.stderr)
    
    return stats

def fetch_repo_collaborators(owner, repo, limit=100):
    """
    Fetch collaborators (users with push access) for a repository.
    Requires authentication and admin/push rights on the repo.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/collaborators"
    params = {"per_page": limit}
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        
        if response.status_code == 403:
            # Expected if we don't have permission (not our repo)
            return []
            
        if response.status_code == 204:
            return []
            
        response.raise_for_status()
        
        if not response.content:
            return []
            
        return response.json()
    except requests.RequestException:
        # Silently fail for collaborators as it's often restricted
        return []

def search_repositories(query, limit=5, page=1, sort="stars", order="desc"):
    """
    Search for repositories by query.
    """
    url = f"https://api.github.com/search/repositories?q={query}&sort={sort}&order={order}&per_page={limit}&page={page}"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        total_count = data.get("total_count", 0)
        
        # Calculate if there are more pages
        has_next = (page * limit) < total_count
        
        repo_list = [
            {
                "full_name": item["full_name"],
                "html_url": item["html_url"],
                "description": item["description"],
                "stargazers_count": item["stargazers_count"],
                "language": item["language"]
            }
            for item in items
        ]
        
        return {
            "items": repo_list,
            "has_next": has_next
        }
    except requests.RequestException as e:
        print(f"Error searching repos: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
             print(f"GitHub API Response: {e.response.text}", file=sys.stderr)
        return {"items": [], "has_next": False}

if __name__ == "__main__":
    # CLI Demo
    if len(sys.argv) < 2:
        print("Usage: python github.py [user|repos|readme] [args...]")
        print("Example: python github.py user torvalds")
        sys.exit(1)

    action = sys.argv[1]
    
    if action == "user" and len(sys.argv) > 2:
        user_data = fetch_github_user(sys.argv[2])
        if user_data:
            print(f"User: {user_data.get('login')}")
            print(f"Name: {user_data.get('name')}")
            print(f"Bio: {user_data.get('bio')}")
    
    elif action == "repos" and len(sys.argv) > 2:
        repos = fetch_github_repos(sys.argv[2])
        print(f"Found {len(repos)} repositories.")
        if repos:
            print(f"First repo: {repos[0]['name']} - {repos[0]['description']}")
            
    elif action == "readme" and len(sys.argv) > 3:
        readme = fetch_repo_readme(sys.argv[2], sys.argv[3])
        if readme:
            print("--- README START ---")
            print(readme[:500] + ("..." if len(readme) > 500 else ""))
            print("--- README END ---")
    
    else:
        print("Invalid arguments.")
