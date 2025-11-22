import requests
import os
import sys
from dotenv import load_dotenv

# Explicitly load .env from backend
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)

def check_rate_limit():
    token = os.getenv("GITHUB_TOKEN")
    # Mask token for printing
    masked_token = f"{token[:4]}...{token[-4:]}" if token and len(token) > 8 else "None"
    
    headers = {"Authorization": f"token {token}"} if token else {}
    
    print(f"Checking GitHub API status...")
    print(f"Loading .env from: {env_path}")
    print(f"Token present: {'Yes' if token else 'No'} ({masked_token})")
    
    try:
        response = requests.get("https://api.github.com/rate_limit", headers=headers)
        if response.status_code == 401:
             print("\nERROR: 401 Unauthorized. Your token is invalid or expired.")
             return

        response.raise_for_status()
        data = response.json()
        
        core = data['resources']['core']
        print(f"\nRate Limit Status:")
        print(f"Limit: {core['limit']}")
        print(f"Remaining: {core['remaining']}")
        print(f"Reset: {core['reset']}")
        
        if core['remaining'] == 0:
            print("\nCRITICAL: Rate limit exceeded!")
            
    except Exception as e:
        print(f"Error checking rate limit: {e}")

    print("\nAttempting to fetch user 'tj'...")
    try:
        resp = requests.get("https://api.github.com/users/tj", headers=headers)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Fetch error: {e}")

if __name__ == "__main__":
    check_rate_limit()
