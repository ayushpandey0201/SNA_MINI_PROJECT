    import time
from scholarly import scholarly, ProxyGenerator
'''
def _configure_proxy():
    """
    Configures a proxy for scholarly to avoid rate limiting.
    Uses FreeProxies by default.
    """
    try:
        print("Configuring proxy for Google Scholar (this may take a moment)...")
        pg = ProxyGenerator()
        if pg.FreeProxies():
            scholarly.use_proxy(pg)
            print("Proxy configured successfully.")
        else:
            print("Failed to find a working free proxy. Continuing with direct connection.")
    except Exception as e:
        print(f"Error configuring proxy: {e}")

# Flag to ensure we only try to configure the proxy once
_PROXY_CONFIGURED = False
'''
def fetch_scholar_author_by_name(name):
    """
    Fetches author metadata from Google Scholar.
    
    Args:
        name (str): The name of the author to search for.
        
    Returns:
        dict: A dictionary containing author details or None if not found/error.
              Keys: name, affiliation, hindex, i10, publications
    """
    try:
        # Polite delay before request
        time.sleep(1.0)
        
        search_query = scholarly.search_author(name)
        try:
            author = next(search_query)
        except StopIteration:
            print(f"Author '{name}' not found.")
            return None

        # Polite delay before filling details
        time.sleep(1.0)
        
        # Fill author details (basics, indices, publications)
        # We limit publications to a small number to avoid excessive traffic/time
        author = scholarly.fill(author, sections=['basics', 'indices', 'publications'])
        
        publications = []
        # Get top 3-5 publications
        for pub in author.get('publications', [])[:5]:
            publications.append({
                'title': pub.get('bib', {}).get('title'),
                'year': pub.get('bib', {}).get('pub_year'),
                'venue': pub.get('bib', {}).get('venue'),
                'num_citations': pub.get('num_citations')
            })

        return {
            'name': author.get('name'),
            'affiliation': author.get('affiliation'),
            'hindex': author.get('hindex'),
            'i10': author.get('i10index'),
            'publications': publications
        }

    except Exception as e:
        print(f"Error fetching scholar data for '{name}': {e}")
        return None

if __name__ == "__main__":
    # Simple test
    result = fetch_scholar_author_by_name("Andrew Ng")
    if result:
        print(f"Name: {result['name']}")
        print(f"H-index: {result['hindex']}")
        print(f"Top Pub: {result['publications'][0]['title'] if result['publications'] else 'None'}")
