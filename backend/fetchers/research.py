import requests
import sys

def search_research_papers(query, limit=5, page=1):
    """
    Search for technical articles using the Dev.to API (free, no key required).
    Acts as a reliable source for "Research/Articles" for the presentation.
    """
    # Dev.to API endpoint for searching articles
    # We use 'tag' if the query is a single word, or 'q' for general search
    # For better results with multi-word queries, we'll use 'q'
    url = "https://dev.to/api/articles"
    
    params = {
        "tag": query.replace(" ", ""), # Try to use as tag first
        "per_page": limit,
        "page": page,
        "top": 365 # Get top articles from the last year for better quality
    }
    
    # If query has spaces, use it as a general search term instead of tag
    if " " in query:
        del params["tag"]
        # Dev.to doesn't have a direct 'q' param in the main endpoint, 
        # but we can use the search endpoint or just fetch latest/top with tags.
        # Actually, the /articles endpoint filters by tag. 
        # Let's try to find the most relevant tag from the query.
        # Fallback: Use the first word as tag
        params["tag"] = query.split(" ")[0]

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        articles = response.json()
        
        results = []
        for article in articles:
            # Map Dev.to fields to our expected schema
            results.append({
                "title": article.get("title"),
                "authors": [article.get("user", {}).get("name", "Unknown Author")],
                "year": article.get("published_at", "")[:4], # Extract year from ISO date
                "url": article.get("url"),
                "abstract": article.get("description", "No description available.")
            })
            
        return {
            "items": results,
            "has_next": len(results) == limit # Simple heuristic
        }
        
    except Exception as e:
        print(f"Error fetching Dev.to articles: {e}", file=sys.stderr)
        # Fallback to empty list so app doesn't crash
        return {
            "items": [],
            "has_next": False
        }
