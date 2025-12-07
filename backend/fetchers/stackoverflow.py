import requests
import time
import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_so_user(user_id):
    """
    Fetches StackOverflow user profile.
    """
    url = f"https://api.stackexchange.com/2.3/users/{user_id}"
    params = {
        "site": "stackoverflow",
        "key": "U4DMV*8nvpm3EOpvf69Rxw(("  # Public key for higher quota if needed, or remove if not used
    }
    # Note: 'key' is optional but recommended for higher request limits. 
    # For this example, I'll omit it to keep it simple unless the user provides one, 
    # or I can use a common public key if I had one, but best to stick to no key or env var.
    # Actually, let's just use the basic endpoint without a key for now, 
    # as the user didn't provide one.
    
    params = {"site": "stackoverflow"}
    
    try:
        response = requests.get(url, params=params, verify=False)
        
        # Handle rate limits
        if response.status_code == 429:
            print("Rate limit exceeded. Waiting...")
            # Check for 'backoff' field
            data = response.json()
            if 'backoff' in data:
                time.sleep(data['backoff'] + 1)
                return fetch_so_user(user_id) # Retry
            else:
                return None

        response.raise_for_status()
        data = response.json()
        
        if 'items' in data and len(data['items']) > 0:
            return data['items'][0]
        else:
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching user {user_id}: {e}")
        return None

def fetch_so_top_tags(user_id):
    """
    Fetches top tags for a StackOverflow user.
    """
    url = f"https://api.stackexchange.com/2.3/users/{user_id}/top-tags"
    params = {"site": "stackoverflow"}
    
    try:
        response = requests.get(url, params=params, verify=False)
        
        # Handle rate limits
        if response.status_code == 429:
            print("Rate limit exceeded. Waiting...")
            data = response.json()
            if 'backoff' in data:
                time.sleep(data['backoff'] + 1)
                return fetch_so_top_tags(user_id)
            else:
                return []

        response.raise_for_status()
        data = response.json()
        
        if 'items' in data:
            return data['items']
        else:
            return []

    except requests.exceptions.RequestException as e:
        print(f"Error fetching tags for user {user_id}: {e}")
        return []

def search_questions(query, limit=5, page=1):
    """
    Search for StackOverflow questions by query.
    """
    url = "https://api.stackexchange.com/2.3/search/advanced"
    params = {
        "order": "desc",
        "sort": "relevance",
        "q": query,
        "site": "stackoverflow",
        "pagesize": limit,
        "page": page
    }
    try:
        response = requests.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        has_more = data.get("has_more", False)
        
        question_list = [
            {
                "title": item["title"],
                "link": item["link"],
                "score": item["score"],
                "is_answered": item["is_answered"],
                "tags": item.get("tags", [])
            }
            for item in items
        ]
        
        return {
            "items": question_list,
            "has_next": has_more
        }
    except requests.RequestException as e:
        print(f"Error searching SO: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
             print(f"SO API Response: {e.response.text}", file=sys.stderr)
        return {"items": [], "has_next": False}

def search_so_users(name, limit=1):
    """
    Search for StackOverflow users by name.
    """
    url = "https://api.stackexchange.com/2.3/users"
    params = {
        "order": "desc",
        "sort": "reputation",
        "inname": name,
        "site": "stackoverflow",
        "pagesize": limit
    }
    try:
        response = requests.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])
    except requests.RequestException as e:
        print(f"Error searching SO users for {name}: {e}", file=sys.stderr)
        return []

if __name__ == "__main__":
    # Example usage
    # User ID for 'Jon Skeet' is 22656
    example_user_id = 22656 
    
    print(f"Fetching profile for user {example_user_id}...")
    profile = fetch_so_user(example_user_id)
    if profile:
        print(f"User: {profile.get('display_name')}")
        print(f"Reputation: {profile.get('reputation')}")
        print(f"Link: {profile.get('link')}")
    else:
        print("User not found.")

    print(f"\nFetching top tags for user {example_user_id}...")
    tags = fetch_so_top_tags(example_user_id)
    if tags:
        for tag in tags[:5]: # Show top 5
            print(f"{tag['tag_name']}: {tag['answer_count']} answers, {tag['answer_score']} score")
    else:
        print("No tags found.")
