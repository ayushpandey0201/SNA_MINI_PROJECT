"""
Quick test of enrich_profile with both GitHub and StackOverflow.
"""

import sys
import os
import json

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from backend.enrich import enrich_profile

def test_enrich_with_so():
    """Test enrichment with a real user that has both GitHub and StackOverflow."""
    
    print("=" * 70)
    print("Testing enrich_profile() with GitHub + StackOverflow")
    print("=" * 70)
    
    # Using Jon Skeet as an example - famous on both platforms
    # GitHub: jonskeet
    # StackOverflow: 22656 (Jon Skeet - #1 user on SO)
    
    github_username = "jonskeet"
    so_user_id = 22656
    
    print(f"\nEnriching profile:")
    print(f"  GitHub: {github_username}")
    print(f"  StackOverflow ID: {so_user_id}")
    print()
    
    try:
        profile = enrich_profile(github_username, so_user_id=so_user_id)
        
        print("\n" + "=" * 70)
        print("ENRICHMENT RESULTS")
        print("=" * 70)
        
        # Node IDs
        print("\n📍 Node IDs:")
        for key, value in profile['node_ids'].items():
            print(f"   {key}: {value}")
        
        # GitHub Stats
        print("\n🐙 GitHub Stats:")
        gh_stats = profile['github_stats']
        print(f"   Name: {gh_stats.get('name')}")
        print(f"   Bio: {gh_stats.get('bio')}")
        print(f"   Location: {gh_stats.get('location')}")
        print(f"   Company: {gh_stats.get('company')}")
        print(f"   Followers: {gh_stats.get('followers', 0):,}")
        print(f"   Public Repos: {gh_stats.get('public_repos', 0)}")
        
        # StackOverflow Stats
        if profile['so_stats']:
            print("\n📚 StackOverflow Stats:")
            so_stats = profile['so_stats']
            print(f"   Display Name: {so_stats.get('display_name')}")
            print(f"   Reputation: {so_stats.get('reputation', 0):,}")
            badges = so_stats.get('badge_counts', {})
            print(f"   Badges: 🥇{badges.get('gold', 0)} 🥈{badges.get('silver', 0)} 🥉{badges.get('bronze', 0)}")
        
        # Activity Counts
        print("\n📈 Activity Metrics:")
        activity = profile['activity_counts']
        print(f"   Repositories: {activity['repo_count']}")
        print(f"   Total Stars: {activity['total_stars']:,}")
        print(f"   Total Forks: {activity['total_forks']:,}")
        
        # Top Languages
        print("\n💻 Top Languages:")
        for lang, count in profile['top_repo_languages'][:5]:
            print(f"   • {lang}: {count} repos")
        
        # Top SO Tags
        if profile['top_so_tags']:
            print("\n🏷️  Top StackOverflow Tags:")
            for tag, score in profile['top_so_tags'][:5]:
                print(f"   • {tag}: {score} score")
        
        # Topics
        if profile['top_topics']:
            print("\n🔍 Extracted Topics:")
            print(f"   {', '.join(profile['top_topics'][:10])}")
        
        # Bio Summary
        if profile['bio_summary']:
            print("\n📝 Bio Summary:")
            print(f"   {profile['bio_summary'][:200]}...")
        
        # Errors
        if profile['errors']:
            print("\n⚠️  Errors:")
            for error in profile['errors']:
                print(f"   • {error}")
        
        print("\n" + "=" * 70)
        print("✅ ENRICHMENT COMPLETE")
        print("=" * 70)
        
        # Save to JSON file for inspection
        output_file = "enriched_profile_test.json"
        with open(output_file, 'w') as f:
            json.dump(profile, indent=2, fp=f, default=str)
        print(f"\n💾 Full profile saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Error during enrichment: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enrich_with_so()
