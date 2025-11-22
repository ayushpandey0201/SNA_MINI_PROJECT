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
    Fetch GitHub user repositories.
    
    Args:
        username (str): GitHub username.
        per_page (int): Number of repos per page.
        
    Returns:
        list: List of repository dicts.
    """
    url = f"https://api.github.com/users/{username}/repos"
    params = {"per_page": per_page}
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching repos for {username}: {e}", file=sys.stderr)
        return []

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
        print(f"Error fetching README for {owner}/{repo}: {e}", file=sys.stderr)
        return None

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
