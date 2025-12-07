"""
Enrichment module for creating merged developer profiles.

This module combines GitHub activity and StackOverflow tags into a single
flattened feature dictionary suitable for ML models and UI display.
"""

import sys
import os
import json
from typing import Optional, Dict, Any, List
from collections import Counter

# Add the parent directory to sys.path to allow imports from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.fetchers.github import fetch_github_user, fetch_github_repos, fetch_repo_readme, fetch_repo_contributors, fetch_repo_collaborators, fetch_user_commit_stats
from backend.fetchers.stackoverflow import fetch_so_user, fetch_so_top_tags, search_so_users
from backend.fetchers.research import search_research_papers
from backend.storage import upsert_node, insert_edge
from backend.nlp_ops import extract_topics, short_summary, clean_html, generate_bio_summary
from backend.graph_mapping import (
    get_github_user_id, 
    get_so_user_id, 
    get_repo_id, 
    get_tag_id
)
from backend.llm import generate_gemini_summary


def enrich_profile(github_username: str, so_user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Create a merged developer profile combining GitHub activity and StackOverflow tags.
    
    This function:
    1. Fetches GitHub user, repos, and README texts
    2. Fetches StackOverflow tags if so_user_id is provided
    3. Upserts nodes and edges into the database
    4. Extracts features: top_repo_languages, top_so_tags, top_topics, activity_counts
    5. Returns a merged JSON profile with these fields and node IDs
    
    Args:
        github_username (str): GitHub username to fetch
        so_user_id (int, optional): StackOverflow user ID
        
    Returns:
        dict: Enriched profile containing:
            - node_ids: dict with github_user_id, so_user_id (if available)
            - github_stats: followers, public_repos, etc.
            - so_stats: reputation, badges, etc. (if available)
            - top_repo_languages: list of (language, count) tuples
            - top_so_tags: list of (tag, score) tuples (if available)
            - top_topics: list of extracted topic keywords
            - activity_counts: dict with repo_count, total_stars, total_forks
            - bio_summary: short summary of user bio/README content
            - errors: list of any errors encountered
    """
    profile = {
        "node_ids": {},
        "github_stats": {},
        "so_stats": {},
        "top_repo_languages": [],
        "top_so_tags": [],
        "top_topics": [],
        "repos": [],
        "collaborations": [],
        "collaborators": {},
        "activity_counts": {
            "repo_count": 0,
            "total_stars": 0,
            "total_forks": 0
        },
        "bio_summary": "",
        "ai_analysis": None,
        "errors": []
    }
    print(f"Fetching GitHub user: {github_username}...")
    gh_user = fetch_github_user(github_username)
    
    if not gh_user:
        profile["errors"].append(f"Failed to fetch GitHub user: {github_username}")
        return profile
    
    # Store GitHub node ID
    gh_node_id = get_github_user_id(github_username)
    profile["node_ids"]["github_user_id"] = gh_node_id
    
    # Upsert GitHub user node
    upsert_node(gh_node_id, "github_user", gh_user)
    
    # Combine bio and README texts for NLP (will be populated later)
    # We initialize it here to ensure the key exists
    text_corpus_list = []
    if gh_user.get("bio"):
        text_corpus_list.append(gh_user.get("bio"))
        
    # Extract GitHub stats
    profile["github_stats"] = {
        "login": gh_user.get("login"),
        "name": gh_user.get("name"),
        "bio": gh_user.get("bio"),
        "company": gh_user.get("company"),
        "location": gh_user.get("location"),
        "email": gh_user.get("email"),
        "followers": gh_user.get("followers", 0),
        "following": gh_user.get("following", 0),
        "public_repos": gh_user.get("public_repos", 0),
        "public_gists": gh_user.get("public_gists", 0),
        "created_at": gh_user.get("created_at"),
        "updated_at": gh_user.get("updated_at")
    }
    
    # Fetch repositories
    print(f"Fetching repos for {github_username}...")
    all_repos = fetch_github_repos(github_username)
    
    # Separte Owned Repos vs Collaborations
    owned_repos = []
    collaborations = []
    
    for r in all_repos:
        if r.get("owner", {}).get("login", "").lower() == github_username.lower():
            owned_repos.append(r)
        else:
            collaborations.append(r)
            
    # Populate collaborations in profile
    profile["collaborations"] = [
        {
            "name": r.get("name"),
            "full_name": r.get("full_name"),
            "owner": r.get("owner", {}).get("login"),
            "stars": r.get("stargazers_count", 0),
            "url": r.get("html_url"),
            "description": r.get("description")
        }
        for r in collaborations
    ]
    
    # Sort owned repos by stars (desc) then updated (desc) to prioritize best content
    owned_repos.sort(key=lambda x: (x.get('stargazers_count', 0), x.get('updated_at', '')), reverse=True)

    # Sort collaborations by stars to process them all
    collaborations.sort(key=lambda x: x.get('stargazers_count', 0), reverse=True)

    readme_fetch_count = 0
    language_counter = Counter()
    total_stars = 0
    total_forks = 0
    readme_texts = []
    
    # Process ONLY owned repos for graph and stats logic
    for repo in owned_repos:
        repo_full_name = repo.get('full_name')
        if not repo_full_name:
            continue
        
        # Upsert repo node
        repo_node_id = get_repo_id(repo_full_name)
        upsert_node(repo_node_id, "github_repo", repo)
        
        # Create edge: User -> Repo
        insert_edge(gh_node_id, repo_node_id, "CONTRIBUTED_TO")
        
        # Collect language stats
        lang = repo.get('language')
        if lang:
            language_counter[lang] += 1
        
        # Collect activity stats
        total_stars += repo.get('stargazers_count', 0)
        total_forks += repo.get('forks_count', 0)
        
        # Fetch README for top 5 repos regardless of stars
        if readme_fetch_count < 5:
            owner, repo_name = repo_full_name.split('/')
            readme = fetch_repo_readme(owner, repo_name)
            if readme:
                readme_texts.append(readme)
                readme_fetch_count += 1

    # Sort repos by "Active Work" (Non-forks first, then most recently pushed)
    # User complained that star-based sort showed "random" (likely popular forks)
    top_repos = sorted(
        owned_repos, 
        key=lambda x: (not x.get('fork', False), x.get('size', 0), x.get('pushed_at', '')), 
        reverse=True
    )
    
    # Limit to top 15 for README fetching and initial processing
    top_repos_candidates = top_repos[:15]
    
    # For "top worked repos", we need to check ALL repos (owned + collaborations)
    # to find where user has made the most contributions, regardless of recency
    # Check all owned repos (no limit) + all collaborations to get accurate contribution counts
    # This ensures we find repos where user worked a lot, even if they're older/less recent
    all_repos_for_contrib_check = owned_repos + collaborations
    
    my_contributions_map = {}  # Store basic commit count
    my_detailed_stats = {}     # Store detailed commit statistics
    
    print(f"Fetching contribution counts and detailed stats for {len(all_repos_for_contrib_check)} repos to find most worked repos...")
    
    for repo in all_repos_for_contrib_check:
        repo_full_name = repo.get('full_name')
        if not repo_full_name: continue
        
        # Add to profile repos list
        profile["repos"].append({
            "name": repo.get("name"),
            "full_name": repo_full_name,
            "owner": repo.get("owner", {}).get("login"),  # Add owner field
            "stars": repo.get("stargazers_count", 0),
            "language": repo.get("language"),
            "url": repo.get("html_url")
        })
        
        # Fetch contributors AND collaborators to ensure we catch everyone (committers + members)
        owner, repo_name = repo_full_name.split('/')
        
        contributors = fetch_repo_contributors(owner, repo_name, limit=100)
        collaborators = fetch_repo_collaborators(owner, repo_name, limit=100)
        
        # Merge lists by login to deduplicate
        all_people = {c['login']: c for c in contributors if c.get('login')}
        for c in collaborators:
            if c.get('login'):
                all_people[c['login']] = c
                
        merged_contributors = list(all_people.values())
        
        contributors = merged_contributors # Override for downstream logic
        
        # Filter out the main user from contributors
        valid_contributors = []
        if contributors:
            valid_contributors = [
                c.get('login') for c in contributors 
                if c.get('login') and c.get('login').lower() != github_username.lower()
            ]
        
        # Capture MY contribution count (commits/changes made by user)
        my_count = 0
        for c in contributors:
             if c.get('login', '').lower() == github_username.lower():
                 my_count = c.get('contributions', 0)  # This is the total commit count
                 break
        
        # SPECIAL CASE: For owned repos, if user is the owner but not in contributors list,
        # we should still count their work. Check if this is an owned repo.
        if my_count == 0:
            repo_owner = repo.get('owner', {}).get('login', '').lower() if isinstance(repo.get('owner'), dict) else str(repo.get('owner', '')).lower()
            if repo_owner == github_username.lower():
                # This is the user's own repo - they definitely worked on it
                # Use a default estimate or fetch commit stats to get actual count
                # For now, we'll mark it but the detailed stats fetch will get the real count
                pass  # Will be handled by detailed stats fetch
        
        my_contributions_map[repo_full_name] = my_count
        
        # Fetch detailed commit statistics for repos with potential contributions
        # Fetch for owned repos even if contributors list shows 0 (owner might not be in contributors)
        # Also fetch for repos where user has commits
        is_owned_repo = repo.get('owner', {}).get('login', '').lower() == github_username.lower() if isinstance(repo.get('owner'), dict) else False
        if my_count > 0 or is_owned_repo:
            print(f"Fetching detailed commit stats for {repo_name} (user has {my_count} commits, owned: {is_owned_repo})...")
            detailed_stats = fetch_user_commit_stats(owner, repo_name, github_username)
            # Use the more accurate commit count from detailed stats if available
            actual_commits = detailed_stats.get("commits", 0)
            if actual_commits > 0:
                my_contributions_map[repo_full_name] = actual_commits
                print(f"  → Found {actual_commits} commits from detailed stats")
            else:
                # If detailed stats show 0 commits, this means user hasn't actually worked on this repo
                # Set to 0 and don't include in top worked repos
                my_contributions_map[repo_full_name] = 0
                print(f"  → No commits found - user hasn't worked on this repo")
            my_detailed_stats[repo_full_name] = detailed_stats
        else:
            # Not an owned repo and no commits from contributors list - definitely 0
            my_contributions_map[repo_full_name] = 0
            my_detailed_stats[repo_full_name] = {"commits": 0, "last_commit_date": None, "commit_frequency": 0}
        
        print(f"DEBUG: Repo {repo_name} - User contributions: {my_contributions_map.get(repo_full_name, 0)} commits")

        # Only process collaborators for repos we're tracking in detail (top 15 + collaborations)
        if repo in top_repos_candidates or repo in collaborations:
            if valid_contributors:
                # Store list of dicts with login and url
                profile["collaborators"][repo_full_name] = [
                    {"login": c.get("login"), "url": c.get("html_url")} 
                    for c in contributors 
                    if c.get("login") and c.get("login").lower() != github_username.lower()
                ]
                
                # Upsert contributor nodes and edges
                for contrib in contributors:
                    c_login = contrib.get('login')
                    if not c_login or c_login.lower() == github_username.lower():
                        continue
                        
                    c_node_id = get_github_user_id(c_login)
                    # We don't have full user details, just basic info
                    upsert_node(c_node_id, "github_user", {"login": c_login, "type": "contributor"})
                    
                    # Edge: Contributor -> Repo
                    repo_node_id = get_repo_id(repo_full_name)
                    insert_edge(c_node_id, repo_node_id, "CONTRIBUTED_TO")
    
    # Update activity counts
    profile["activity_counts"]["repo_count"] = len(all_repos)
    profile["activity_counts"]["total_stars"] = total_stars
    profile["activity_counts"]["total_forks"] = total_forks
    
    # Top languages
    profile["top_repo_languages"] = language_counter.most_common(10)
    
    # ===== STACKOVERFLOW DATA =====
    # Auto-discover SO user if not provided
    if not so_user_id:
        print(f"Attempting to find StackOverflow user for {github_username}...")
        # Try searching by GitHub login first
        so_users = search_so_users(gh_user.get("login"))
        if not so_users and gh_user.get("name"):
            # Try searching by real name
            so_users = search_so_users(gh_user.get("name"))
            
        if so_users:
            found_user = so_users[0]
            so_user_id = found_user.get("user_id")
            print(f"Found matching SO user: {found_user.get('display_name')} (ID: {so_user_id})")
        else:
            print("No matching StackOverflow user found.")

    if so_user_id:
        print(f"Fetching StackOverflow user: {so_user_id}...")
        so_user = fetch_so_user(so_user_id)
        
        if so_user:
            so_node_id = get_so_user_id(so_user_id)
            profile["node_ids"]["so_user_id"] = so_node_id
            
            # Upsert SO user node
            upsert_node(so_node_id, "so_user", so_user)
            
            # Extract SO stats
            profile["so_stats"] = {
                "display_name": so_user.get("display_name"),
                "reputation": so_user.get("reputation", 0),
                "badge_counts": so_user.get("badge_counts", {}),
                "account_id": so_user.get("account_id"),
                "creation_date": so_user.get("creation_date"),
                "location": so_user.get("location"),
                "link": so_user.get("link")
            }
            
            # Link GitHub <-> StackOverflow
            insert_edge(gh_node_id, so_node_id, "SAME_AS")
            insert_edge(so_node_id, gh_node_id, "SAME_AS")
            
            # Fetch tags
            print(f"Fetching tags for SO user {so_user_id}...")
            tags = fetch_so_top_tags(so_user_id)
            
            tag_scores = []
            for tag in tags:
                tag_name = tag.get('tag_name')
                if not tag_name:
                    continue
                
                # Upsert tag node
                tag_node_id = get_tag_id(tag_name)
                upsert_node(tag_node_id, "stackoverflow_tag", tag)
                
                # Create edge: SO User -> Tag
                edge_attrs = {
                    "count": tag.get('answer_count', 0),
                    "score": tag.get('answer_score', 0)
                }
                insert_edge(so_node_id, tag_node_id, "HAS_TAG", edge_attrs)
                
                # Collect tag scores
                tag_scores.append((tag_name, tag.get('answer_score', 0)))
            
            profile["top_so_tags"] = sorted(tag_scores, key=lambda x: x[1], reverse=True)[:10]
        else:
            profile["errors"].append(f"Failed to fetch SO user: {so_user_id}")
    
    # ===== NLP ENRICHMENT =====
    print("Extracting topics and generating summary...")
    
    # Combine bio and README texts for NLP
    text_corpus = []
    if gh_user.get("bio"):
        text_corpus.append(gh_user.get("bio"))
    
    # Clean and combine README texts
    readme_corpus_only = []
    for readme in readme_texts[:10]:  # Limit to top 10 READMEs for better context
        cleaned = clean_html(readme)
        if cleaned:
            cleaned_trunk = cleaned[:2000]
            text_corpus_list.append(cleaned_trunk)  # Increased limit for better classification
            readme_corpus_only.append(cleaned_trunk)
            
    # If text corpus is sparse, generate synthetic context from structured data
    # This guarantees we ALWAYS have content for the AI summarizer
    structured_context = []
    
    # identity
    dev_name = gh_user.get("name") or gh_user.get("login")
    structured_context.append(f"{dev_name} is a developer on GitHub.")
    
    # location/company
    if gh_user.get("location"):
        structured_context.append(f"They are based in {gh_user.get('location')}.")
    if gh_user.get("company"):
        structured_context.append(f"They work at {gh_user.get('company')}.")
        
    # languages
    if language_counter:
        top_langs = [l[0] for l in language_counter.most_common(3)]
        structured_context.append(f"Their primary programming languages are {', '.join(top_langs)}.")
        
    # repos
    if owned_repos:
        top_repo_names = [r.get("name") for r in owned_repos[:3]]
        structured_context.append(f"They have contributed to projects like {', '.join(top_repo_names)}.")
        
    # Add this structured context to the corpus acting as a fallback
    synthetic_text = " ".join(structured_context)
    text_corpus_list.append(synthetic_text)

    # Save the combined text corpus to the user node for prediction
    full_text_corpus = " ".join(text_corpus_list)
    # Re-upsert user node with the corpus
    # Load existing node attributes first to preserve them
    from backend.storage import SessionLocal, Node
    session = SessionLocal()
    try:
        existing_node = session.query(Node).filter(Node.id == gh_node_id).first()
        if existing_node and existing_node.attrs:
            try:
                existing_attrs = json.loads(existing_node.attrs)
                gh_user_with_corpus = {**existing_attrs, **gh_user}
            except:
                gh_user_with_corpus = gh_user.copy()
        else:
            gh_user_with_corpus = gh_user.copy()
        
        gh_user_with_corpus["text_corpus"] = full_text_corpus
        # Clear old ai_role if it exists (will be set fresh by AI analysis)
        if "ai_role" in gh_user_with_corpus:
            del gh_user_with_corpus["ai_role"]
        if "ai_analysis" in gh_user_with_corpus:
            del gh_user_with_corpus["ai_analysis"]
        
        upsert_node(gh_node_id, "github_user", gh_user_with_corpus)
    finally:
        session.close()

    text_corpus = text_corpus_list # For backward compatibility with local var usage below
    
    research_highlights = []
    
    if text_corpus:
        combined_text = " ".join(text_corpus)
        readme_combined = " ".join(readme_corpus_only)
        
        # Extract topics
        try:
            topics_dict = extract_topics(combined_text, num_clusters=3, top_n=5)
            # Flatten topics into a single list
            all_topics = []
            for cluster_topics in topics_dict.values():
                all_topics.extend(cluster_topics)
            # Filter minimal length topics
            profile["top_topics"] = [t for t in list(set(all_topics)) if len(t) > 3][:10]
        except Exception as e:
            profile["errors"].append(f"Topic extraction failed: {e}")
        
        # Fetch Research Highlights based on top topic
        if profile["top_topics"]:
            try:
                # Use the most relevant topic for research search
                top_topic = profile["top_topics"][0]
                print(f"Fetching research highlights for topic: {top_topic}...")
                papers_data = search_research_papers(top_topic, limit=3)
                # Handle both dict (new) and list (old) formats
                if isinstance(papers_data, dict):
                    research_highlights = papers_data.get("items", [])
                else:
                    research_highlights = papers_data
            except Exception as e:
                print(f"Error fetching research highlights: {e}")

        # Dynamic AI Analysis (Model-based)
        try:
            # PRIORITIZE README CONTENT if available, otherwise use mixed corpus
            print("Generating AI analysis...")
            # Use the combined text which now includes the synthetic profile info
            # We want the richest context for the LLM
            source_text = combined_text + " " + readme_combined
            
            ai_summary = generate_gemini_summary(source_text)
            
            # Handle different return types from AI
            if not ai_summary:
                # Empty result - use fallback
                profile["ai_analysis"] = None
                profile["ai_role"] = None
            elif isinstance(ai_summary, dict):
                # Dictionary response (expected format)
                summary_text = ai_summary.get("summary")
                ai_role_value = ai_summary.get("role")
                
                # Only use AI role if it's valid and not a generic fallback
                if ai_role_value and ai_role_value not in ["Developer", "Unknown", None, ""]:
                    # Check if summary is valid (not an error message)
                    if summary_text and summary_text.strip() and "unavailable" not in summary_text.lower() and "error" not in summary_text.lower():
                        profile["ai_analysis"] = summary_text.replace("\n", " ")
                        profile["ai_role"] = ai_role_value
                        print(f"AI Role predicted: {ai_role_value}")
                    else:
                        # Invalid summary - don't use AI role
                        profile["ai_analysis"] = None
                        profile["ai_role"] = None
                else:
                    # Invalid or generic role - use fallback
                    profile["ai_analysis"] = None
                    profile["ai_role"] = None
            elif isinstance(ai_summary, str):
                # String response (fallback format)
                if ai_summary.strip() and "unavailable" not in ai_summary.lower() and "error" not in ai_summary.lower():
                    profile["ai_analysis"] = ai_summary.replace("\n", " ")
                    profile["ai_role"] = None
                else:
                    profile["ai_analysis"] = None
                    profile["ai_role"] = None
            else:
                # Unknown format - use fallback
                profile["ai_analysis"] = None
                profile["ai_role"] = None
                
        except Exception as e:
            print(f"AI Summary generation failed: {e}")
            profile["errors"].append(f"Summary generation failed: {e}")
            # Fallback to the synthetic text if Model fails
            profile["ai_analysis"] = synthetic_text
            profile["ai_role"] = None
        
        # Update the user node in database with AI role and analysis (if available)
        try:
            from backend.storage import SessionLocal, Node
            session = SessionLocal()
            try:
                existing_node = session.query(Node).filter(Node.id == gh_node_id).first()
                if existing_node and existing_node.attrs:
                    try:
                        existing_attrs = json.loads(existing_node.attrs)
                        # Update with AI data
                        existing_attrs["ai_role"] = profile.get("ai_role")
                        existing_attrs["ai_analysis"] = profile.get("ai_analysis")
                        existing_node.attrs = json.dumps(existing_attrs)
                        session.commit()
                    except Exception as e:
                        print(f"Error updating node with AI data: {e}")
            finally:
                session.close()
        except Exception as e:
            print(f"Error saving AI data to node: {e}")
    
    # Structural/Heuristic Summary (Rule-based) - Always run this as fallback
    # Use rule-based summary if AI summary is not available
    try:
        summary = generate_bio_summary(profile, research_highlights)
        profile["bio_summary"] = summary
        # If AI analysis failed, use rule-based summary as the main summary
        if not profile.get("ai_analysis"):
            profile["ai_analysis"] = summary
    except Exception as e:
        profile["errors"].append(f"Bio summary failed: {e}")
        # Final fallback
        if not profile.get("ai_analysis"):
            profile["ai_analysis"] = synthetic_text

    # Add top worked repos for UI - sorted by comprehensive work score
    # This shows repos where user has worked the most based on commits, activity, and frequency
    profile["top_active_repos"] = []
    
    # Get ALL repos with their contribution counts and detailed stats
    # Include both owned repos and collaborations
    all_repos_with_contribs = []
    
    def calculate_work_score(contrib_count, detailed_stats, repo_data):
        """
        Calculate a comprehensive work score based on multiple factors:
        - Commit count (primary factor)
        - Recent activity (last commit date)
        - Commit frequency (commits per month)
        - Repo activity (stars, forks as secondary indicators)
        """
        score = 0.0
        
        # Primary factor: Total commits (weight: 60%)
        score += contrib_count * 0.6
        
        # Secondary factor: Recent activity (weight: 25%)
        # Boost repos with recent commits (within last 6 months)
        if detailed_stats and detailed_stats.get("last_commit_date"):
            try:
                from datetime import datetime, timezone
                last_commit = datetime.fromisoformat(detailed_stats["last_commit_date"].replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                days_since_commit = (now - last_commit).days
                
                # Boost score if committed in last 6 months
                if days_since_commit < 180:
                    recency_boost = (180 - days_since_commit) / 180.0  # 0 to 1
                    score += contrib_count * 0.25 * recency_boost
            except:
                pass
        
        # Tertiary factor: Commit frequency (weight: 10%)
        # Boost repos with consistent activity
        if detailed_stats and detailed_stats.get("commit_frequency", 0) > 0:
            # Normalize frequency (assume max 50 commits/month is very active)
            freq_score = min(detailed_stats["commit_frequency"] / 50.0, 1.0)
            score += contrib_count * 0.10 * freq_score
        
        # Quaternary factor: Repo significance (weight: 5%)
        # Slight boost for repos with more stars/forks (indicates important work)
        stars = repo_data.get("stargazers_count", 0)
        forks = repo_data.get("forks_count", 0)
        repo_significance = min((stars + forks * 2) / 1000.0, 1.0)  # Normalize
        score += contrib_count * 0.05 * repo_significance
        
        return score
    
    # Add owned repos with contribution counts and scores
    for repo in owned_repos:
        repo_full_name = repo.get('full_name')
        if repo_full_name and repo_full_name in my_contributions_map:
            contrib_count = my_contributions_map[repo_full_name]
            # STRICT FILTER: Only include repos where user has made AT LEAST 1 commit
            # This ensures we only show repos where user actually worked
            if contrib_count > 0:
                detailed_stats = my_detailed_stats.get(repo_full_name, {})
                work_score = calculate_work_score(contrib_count, detailed_stats, repo)
                # Double-check: work_score should be > 0 if contrib_count > 0, but verify
                if work_score > 0:
                    all_repos_with_contribs.append({
                        "repo": repo,
                        "contributions": contrib_count,
                        "work_score": work_score,
                        "detailed_stats": detailed_stats,
                        "full_name": repo_full_name
                    })
                else:
                    print(f"WARNING: Repo {repo_full_name} has {contrib_count} commits but work_score is 0 - skipping")
    
    # Add collaboration repos with contribution counts and scores
    for repo in collaborations:
        repo_full_name = repo.get('full_name')
        if repo_full_name and repo_full_name in my_contributions_map:
            contrib_count = my_contributions_map[repo_full_name]
            # STRICT FILTER: Only include repos where user has made AT LEAST 1 commit
            if contrib_count > 0:
                detailed_stats = my_detailed_stats.get(repo_full_name, {})
                work_score = calculate_work_score(contrib_count, detailed_stats, repo)
                if work_score > 0:
                    all_repos_with_contribs.append({
                        "repo": repo,
                        "contributions": contrib_count,
                        "work_score": work_score,
                        "detailed_stats": detailed_stats,
                        "full_name": repo_full_name
                    })
                else:
                    print(f"WARNING: Repo {repo_full_name} has {contrib_count} commits but work_score is 0 - skipping")
    
    # Final safety filter: Remove any repos with 0 commits or 0 work score
    all_repos_with_contribs = [r for r in all_repos_with_contribs if r["contributions"] > 0 and r["work_score"] > 0]
    
    # Sort by work score (descending) - repos with most work first
    # Secondary sort by commit count to break ties
    all_repos_with_contribs.sort(key=lambda x: (x["work_score"], x["contributions"]), reverse=True)
    
    # Take top 10 repos where user has worked the most
    top_worked_repos = all_repos_with_contribs[:10]
    
    # Debug: Print what we're including
    if top_worked_repos:
        print(f"\n=== TOP WORKED REPOS (sorted by work score) ===")
        for item in top_worked_repos:
            print(f"  {item['repo'].get('name')}: {item['contributions']} commits, work_score: {item['work_score']:.2f}")
    else:
        print("WARNING: No repos with commits found for top_worked_repos")
        print(f"  Total repos checked: {len(owned_repos) + len(collaborations)}")
        print(f"  Repos with commits > 0: {sum(1 for r in my_contributions_map.values() if r > 0)}")
    
    profile["top_active_repos"] = [
        {
            "id": item["repo"].get("id"),
            "name": item["repo"].get("name"),
            "html_url": item["repo"].get("html_url"),
            "full_name": item["full_name"],
            "stargazers_count": item["repo"].get("stargazers_count", 0),
            "forks_count": item["repo"].get("forks_count", 0),
            "language": item["repo"].get("language"),
            "commit_count": item["contributions"],  # Total commits made by user
            "work_score": round(item["work_score"], 2),  # Comprehensive work score
            "last_commit_date": item["detailed_stats"].get("last_commit_date"),
            "commit_frequency": round(item["detailed_stats"].get("commit_frequency", 0), 2),
            "description": item["repo"].get("description", "")
        }
        for item in top_worked_repos
    ]
    
    # Format the output string to avoid f-string backslash issue
    repo_summaries = [(r['name'], f"{r['commit_count']} commits, score: {r['work_score']}") for r in profile['top_active_repos']]
    print(f"Top worked repos (by work score): {repo_summaries}")
    
    return profile


if __name__ == "__main__":
    # Example usage
    import json
    
    print("=== Enrichment Demo ===\n")
    
    # Test with a well-known developer
    username = "gaearon"  # Dan Abramov (React core team)
    
    print(f"Enriching profile for: {username}\n")
    enriched = enrich_profile(username)
    
    print("\n=== Enriched Profile ===")
    print(json.dumps(enriched, indent=2, default=str))
