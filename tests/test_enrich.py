"""
Unit tests for the enrich module.

Tests the enrich_profile function with a sample user.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.enrich import enrich_profile


class TestEnrichProfile(unittest.TestCase):
    """Test cases for enrich_profile function."""
    
    @patch('backend.enrich.fetch_github_user')
    @patch('backend.enrich.fetch_github_repos')
    @patch('backend.enrich.fetch_repo_readme')
    @patch('backend.enrich.fetch_so_user')
    @patch('backend.enrich.fetch_so_top_tags')
    @patch('backend.enrich.upsert_node')
    @patch('backend.enrich.insert_edge')
    def test_enrich_profile_with_github_only(
        self, 
        mock_insert_edge,
        mock_upsert_node,
        mock_fetch_so_tags,
        mock_fetch_so_user,
        mock_fetch_readme,
        mock_fetch_repos,
        mock_fetch_user
    ):
        """Test enriching a profile with GitHub data only."""
        
        # Mock GitHub user data
        mock_fetch_user.return_value = {
            "login": "testuser",
            "name": "Test User",
            "bio": "A passionate developer working on web technologies.",
            "company": "Test Corp",
            "location": "San Francisco",
            "email": "test@example.com",
            "followers": 100,
            "following": 50,
            "public_repos": 25,
            "public_gists": 5,
            "created_at": "2015-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        
        # Mock GitHub repos
        mock_fetch_repos.return_value = [
            {
                "full_name": "testuser/awesome-project",
                "language": "Python",
                "stargazers_count": 150,
                "forks_count": 30,
                "description": "An awesome Python project"
            },
            {
                "full_name": "testuser/web-app",
                "language": "JavaScript",
                "stargazers_count": 50,
                "forks_count": 10,
                "description": "A web application"
            },
            {
                "full_name": "testuser/ml-toolkit",
                "language": "Python",
                "stargazers_count": 200,
                "forks_count": 45,
                "description": "Machine learning toolkit"
            }
        ]
        
        # Mock README
        mock_fetch_readme.return_value = """
        # Awesome Project
        
        This is a machine learning library for data analysis.
        It includes neural networks, clustering algorithms, and visualization tools.
        Built with Python and TensorFlow.
        """
        
        # Execute
        profile = enrich_profile("testuser")
        
        # Assertions
        self.assertIn("node_ids", profile)
        self.assertIn("github_user_id", profile["node_ids"])
        self.assertEqual(profile["node_ids"]["github_user_id"], "github:testuser")
        
        # Check GitHub stats
        self.assertEqual(profile["github_stats"]["login"], "testuser")
        self.assertEqual(profile["github_stats"]["followers"], 100)
        self.assertEqual(profile["github_stats"]["public_repos"], 25)
        
        # Check activity counts
        self.assertEqual(profile["activity_counts"]["repo_count"], 3)
        self.assertEqual(profile["activity_counts"]["total_stars"], 400)
        self.assertEqual(profile["activity_counts"]["total_forks"], 85)
        
        # Check top languages
        self.assertIn(("Python", 2), profile["top_repo_languages"])
        self.assertIn(("JavaScript", 1), profile["top_repo_languages"])
        
        # Check that nodes were upserted
        self.assertTrue(mock_upsert_node.called)
        self.assertTrue(mock_insert_edge.called)
        
        # Check no SO data since we didn't provide so_user_id
        self.assertEqual(profile["so_stats"], {})
        self.assertEqual(profile["top_so_tags"], [])
        
        print("✓ Test passed: enrich_profile with GitHub only")
    
    @patch('backend.enrich.fetch_github_user')
    @patch('backend.enrich.fetch_github_repos')
    @patch('backend.enrich.fetch_repo_readme')
    @patch('backend.enrich.fetch_so_user')
    @patch('backend.enrich.fetch_so_top_tags')
    @patch('backend.enrich.upsert_node')
    @patch('backend.enrich.insert_edge')
    def test_enrich_profile_with_stackoverflow(
        self, 
        mock_insert_edge,
        mock_upsert_node,
        mock_fetch_so_tags,
        mock_fetch_so_user,
        mock_fetch_readme,
        mock_fetch_repos,
        mock_fetch_user
    ):
        """Test enriching a profile with both GitHub and StackOverflow data."""
        
        # Mock GitHub user
        mock_fetch_user.return_value = {
            "login": "testuser",
            "name": "Test User",
            "bio": "Full-stack developer",
            "followers": 100,
            "public_repos": 10
        }
        
        # Mock GitHub repos
        mock_fetch_repos.return_value = [
            {
                "full_name": "testuser/project1",
                "language": "JavaScript",
                "stargazers_count": 20,
                "forks_count": 5
            }
        ]
        
        mock_fetch_readme.return_value = None
        
        # Mock StackOverflow user
        mock_fetch_so_user.return_value = {
            "display_name": "Test User",
            "reputation": 5000,
            "badge_counts": {"gold": 2, "silver": 10, "bronze": 50},
            "account_id": 12345,
            "creation_date": 1400000000,
            "location": "San Francisco"
        }
        
        # Mock StackOverflow tags
        mock_fetch_so_tags.return_value = [
            {
                "tag_name": "python",
                "answer_count": 50,
                "answer_score": 200
            },
            {
                "tag_name": "javascript",
                "answer_count": 30,
                "answer_score": 150
            }
        ]
        
        # Execute with SO user ID
        profile = enrich_profile("testuser", so_user_id=12345)
        
        # Assertions
        self.assertIn("so_user_id", profile["node_ids"])
        self.assertEqual(profile["node_ids"]["so_user_id"], "so:12345")
        
        # Check SO stats
        self.assertEqual(profile["so_stats"]["display_name"], "Test User")
        self.assertEqual(profile["so_stats"]["reputation"], 5000)
        
        # Check SO tags
        self.assertEqual(len(profile["top_so_tags"]), 2)
        self.assertIn(("python", 200), profile["top_so_tags"])
        self.assertIn(("javascript", 150), profile["top_so_tags"])
        
        # Verify SAME_AS edges were created (bidirectional)
        same_as_calls = [
            call for call in mock_insert_edge.call_args_list 
            if len(call[0]) > 2 and call[0][2] == "SAME_AS"
        ]
        self.assertEqual(len(same_as_calls), 2)  # Bidirectional edge
        
        print("✓ Test passed: enrich_profile with StackOverflow")
    
    @patch('backend.enrich.fetch_github_user')
    def test_enrich_profile_github_failure(self, mock_fetch_user):
        """Test handling of GitHub API failure."""
        
        # Mock GitHub API failure
        mock_fetch_user.return_value = None
        
        # Execute
        profile = enrich_profile("nonexistent_user")
        
        # Assertions
        self.assertIn("errors", profile)
        self.assertTrue(len(profile["errors"]) > 0)
        self.assertIn("Failed to fetch GitHub user", profile["errors"][0])
        
        print("✓ Test passed: GitHub failure handling")


def run_integration_test():
    """
    Integration test with a real user (requires network and API access).
    This is separate from unit tests and should be run manually.
    """
    print("\n=== Integration Test ===")
    print("Testing with real GitHub user: karpathy")
    
    try:
        profile = enrich_profile("karpathy")
        
        print(f"\n✓ Profile enriched successfully!")
        print(f"  GitHub ID: {profile['node_ids'].get('github_user_id')}")
        print(f"  Name: {profile['github_stats'].get('name')}")
        print(f"  Repos: {profile['activity_counts']['repo_count']}")
        print(f"  Stars: {profile['activity_counts']['total_stars']}")
        print(f"  Top Languages: {profile['top_repo_languages'][:3]}")
        print(f"  Top Topics: {profile['top_topics'][:5]}")
        print(f"  Bio Summary: {profile['bio_summary'][:100]}...")
        
        if profile['errors']:
            print(f"  Warnings: {profile['errors']}")
        
        return True
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test enrich module")
    parser.add_argument(
        "--integration", 
        action="store_true", 
        help="Run integration test with real API calls"
    )
    args = parser.parse_args()
    
    if args.integration:
        # Run integration test
        run_integration_test()
    else:
        # Run unit tests
        print("=== Running Unit Tests ===\n")
        unittest.main(argv=[''], verbosity=2, exit=False)
