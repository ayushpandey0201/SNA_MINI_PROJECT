"""
Demo script for the enrich module.

Shows how to use enrich_profile to create rich developer profiles.
"""

import sys
import os
import json

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.enrich import enrich_profile


def demo_enrich():
    """Demonstrate profile enrichment with sample users."""
    
    print("=" * 70)
    print("DEVELOPER PROFILE ENRICHMENT DEMO")
    print("=" * 70)
    
    # Example 1: ML/AI Developer
    print("\n[1] Enriching ML/AI Developer Profile: karpathy")
    print("-" * 70)
    
    profile1 = enrich_profile("karpathy")
    
    print(f"\n📊 Profile Summary:")
    print(f"   Name: {profile1['github_stats'].get('name')}")
    print(f"   Bio: {profile1['github_stats'].get('bio')}")
    print(f"   Location: {profile1['github_stats'].get('location')}")
    print(f"\n📈 Activity Metrics:")
    print(f"   Repositories: {profile1['activity_counts']['repo_count']}")
    print(f"   Total Stars: {profile1['activity_counts']['total_stars']:,}")
    print(f"   Total Forks: {profile1['activity_counts']['total_forks']:,}")
    print(f"   Followers: {profile1['github_stats'].get('followers'):,}")
    print(f"\n💻 Top Languages:")
    for lang, count in profile1['top_repo_languages'][:5]:
        print(f"   • {lang}: {count} repos")
    print(f"\n🏷️  Extracted Topics:")
    print(f"   {', '.join(profile1['top_topics'][:8])}")
    print(f"\n📝 Bio Summary:")
    print(f"   {profile1['bio_summary'][:150]}...")
    
    # Example 2: Web Developer
    print("\n\n[2] Enriching Web Developer Profile: gaearon")
    print("-" * 70)
    
    profile2 = enrich_profile("gaearon")
    
    print(f"\n📊 Profile Summary:")
    print(f"   Name: {profile2['github_stats'].get('name')}")
    print(f"   Bio: {profile2['github_stats'].get('bio')}")
    print(f"\n📈 Activity Metrics:")
    print(f"   Repositories: {profile2['activity_counts']['repo_count']}")
    print(f"   Total Stars: {profile2['activity_counts']['total_stars']:,}")
    print(f"\n💻 Top Languages:")
    for lang, count in profile2['top_repo_languages'][:5]:
        print(f"   • {lang}: {count} repos")
    print(f"\n🏷️  Extracted Topics:")
    print(f"   {', '.join(profile2['top_topics'][:8])}")
    
    # Example 3: DevOps Engineer
    print("\n\n[3] Enriching DevOps Profile: kelseyhightower")
    print("-" * 70)
    
    profile3 = enrich_profile("kelseyhightower")
    
    print(f"\n📊 Profile Summary:")
    print(f"   Name: {profile3['github_stats'].get('name')}")
    print(f"\n📈 Activity Metrics:")
    print(f"   Repositories: {profile3['activity_counts']['repo_count']}")
    print(f"   Total Stars: {profile3['activity_counts']['total_stars']:,}")
    print(f"\n💻 Top Languages:")
    for lang, count in profile3['top_repo_languages'][:5]:
        print(f"   • {lang}: {count} repos")
    
    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nKey Features Demonstrated:")
    print("  ✓ GitHub data fetching (user, repos, READMEs)")
    print("  ✓ Database upsert (nodes and edges)")
    print("  ✓ Language statistics aggregation")
    print("  ✓ NLP topic extraction from READMEs")
    print("  ✓ Bio summarization")
    print("  ✓ Activity metrics calculation")
    print("\nNext Steps:")
    print("  • Add StackOverflow integration (pass so_user_id parameter)")
    print("  • Use profiles for ML model training")
    print("  • Expose via API endpoints")
    print()


if __name__ == "__main__":
    demo_enrich()
