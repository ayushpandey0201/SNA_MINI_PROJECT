import sys
import os
import time

# Add the parent directory to sys.path to allow imports from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.graph_mapping import normalize_and_merge_profiles

def populate():
    # List of diverse GitHub users (Web, ML, DevOps, etc.)
    users = [
        "torvalds",       # Linux (Systems)
        "gaearon",        # React (Web)
        "tj",             # Express/Node (Web/Systems)
        "rauchg",         # Next.js (Web)
        "karpathy",       # AI/ML
        "fchollet",       # Keras (ML)
        "ageron",         # Scikit-Learn (ML)
        "kelseyhightower",# Kubernetes (DevOps)
        "mitchellh",      # HashiCorp (DevOps)
        "kennethreitz",   # Requests (Python)
        "dabeaz",         # Python Compiler (Systems)
        "lukaseder",      # jOOQ (Java/SQL)
        "antirez",        # Redis (Systems)
        "fabpot",         # Symfony (PHP)
        "taylorotwell",   # Laravel (PHP)
        "yyx990803",      # Vue (Web)
        "evanphx",        # Ruby
        "defunkt",        # GitHub
        "mojombo",        # Jekyll
        "tpope"           # Vim plugins
    ]

    print(f"Starting population for {len(users)} users...")
    
    for i, user in enumerate(users):
        print(f"\n[{i+1}/{len(users)}] Processing {user}...")
        try:
            # We are only passing GitHub username for now. 
            # In a real scenario, we would map to SO IDs if available.
            summary = normalize_and_merge_profiles(user)
            print(f"  Nodes upserted: {summary['nodes_upserted']}")
            print(f"  Edges inserted: {summary['edges_inserted']}")
            if summary['errors']:
                print(f"  Errors: {summary['errors']}")
        except Exception as e:
            print(f"  CRITICAL ERROR processing {user}: {e}")
        
        # Polite delay to avoid hitting API rate limits too hard
        time.sleep(1)

    print("\nPopulation complete.")

if __name__ == "__main__":
    populate()
