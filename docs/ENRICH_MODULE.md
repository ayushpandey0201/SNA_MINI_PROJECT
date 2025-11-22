# Profile Enrichment Module

## Overview

The `backend/enrich.py` module provides a unified interface for creating rich developer profiles by combining data from multiple sources (GitHub, StackOverflow) and applying NLP techniques to extract meaningful features.

## Key Function: `enrich_profile()`

### Signature
```python
def enrich_profile(github_username: str, so_user_id: Optional[int] = None) -> Dict[str, Any]
```

### Purpose
Creates a merged developer profile combining GitHub activity and StackOverflow tags, returning a flattened feature dictionary suitable for:
- Machine learning model training
- UI display
- API responses
- Analytics and recommendations

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    enrich_profile()                         │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   ┌─────────┐        ┌──────────┐       ┌──────────┐
   │ GitHub  │        │StackOver │       │   NLP    │
   │  Data   │        │flow Data │       │Processing│
   └─────────┘        └──────────┘       └──────────┘
        │                   │                   │
        ▼                   ▼                   ▼
   • User info        • User stats       • Topic extraction
   • Repositories     • Top tags         • Summarization
   • Languages        • Reputation       • Keyword analysis
   • READMEs          • Badges           
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                    ┌───────────────┐
                    │  Database     │
                    │  (Upsert)     │
                    └───────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Enriched      │
                    │ Profile JSON  │
                    └───────────────┘
```

### Parameters

- **github_username** (str, required): GitHub username to fetch and enrich
- **so_user_id** (int, optional): StackOverflow user ID for cross-platform enrichment

### Return Value

Returns a dictionary with the following structure:

```python
{
    "node_ids": {
        "github_user_id": "github:username",
        "so_user_id": "so:12345"  # if provided
    },
    
    "github_stats": {
        "login": str,
        "name": str,
        "bio": str,
        "company": str,
        "location": str,
        "email": str,
        "followers": int,
        "following": int,
        "public_repos": int,
        "public_gists": int,
        "created_at": str,
        "updated_at": str
    },
    
    "so_stats": {  # if so_user_id provided
        "display_name": str,
        "reputation": int,
        "badge_counts": {"gold": int, "silver": int, "bronze": int},
        "account_id": int,
        "creation_date": int,
        "location": str
    },
    
    "top_repo_languages": [
        ("Python", 25),
        ("JavaScript", 15),
        ("Go", 8),
        ...
    ],
    
    "top_so_tags": [  # if so_user_id provided
        ("python", 500),
        ("django", 300),
        ...
    ],
    
    "top_topics": [
        "machine-learning",
        "neural-networks",
        "data-science",
        ...
    ],
    
    "activity_counts": {
        "repo_count": int,
        "total_stars": int,
        "total_forks": int
    },
    
    "bio_summary": str,  # NLP-generated summary
    
    "errors": []  # List of any errors encountered
}
```

## Usage Examples

### Basic Usage (GitHub Only)

```python
from backend.enrich import enrich_profile

# Enrich a GitHub profile
profile = enrich_profile("karpathy")

print(f"Name: {profile['github_stats']['name']}")
print(f"Total Stars: {profile['activity_counts']['total_stars']}")
print(f"Top Language: {profile['top_repo_languages'][0]}")
print(f"Topics: {profile['top_topics']}")
```

### With StackOverflow Integration

```python
# Enrich with both GitHub and StackOverflow
profile = enrich_profile("username", so_user_id=12345)

print(f"GitHub Stars: {profile['activity_counts']['total_stars']}")
print(f"SO Reputation: {profile['so_stats']['reputation']}")
print(f"Top SO Tags: {profile['top_so_tags'][:5]}")
```

### For ML Feature Extraction

```python
# Extract features for ML model
profile = enrich_profile("developer")

features = {
    "languages": dict(profile['top_repo_languages']),
    "topics": profile['top_topics'],
    "activity_level": profile['activity_counts']['total_stars'],
    "community_engagement": profile['github_stats']['followers']
}
```

## Database Integration

The function automatically:
1. **Upserts nodes** for users, repositories, and tags
2. **Creates edges** for relationships:
   - `CONTRIBUTED_TO`: User → Repository
   - `HAS_TAG`: StackOverflow User → Tag
   - `SAME_AS`: GitHub User ↔ StackOverflow User (bidirectional)

### Node Types Created

- `github_user`: GitHub user profiles
- `github_repo`: GitHub repositories
- `so_user`: StackOverflow user profiles
- `stackoverflow_tag`: StackOverflow tags

## NLP Features

### Topic Extraction
- Uses **SBERT** (Sentence-BERT) embeddings
- Applies **KMeans clustering** to identify themes
- Extracts keywords from README files and bios
- Returns top 10 unique topics

### Summarization
- **Extractive summarization** using semantic similarity
- Selects sentences closest to text centroid
- Combines bio and top repository READMEs
- Generates 2-sentence summaries

## Performance Considerations

1. **README Fetching**: Only fetches READMEs for repos with >10 stars
2. **Text Limiting**: Limits each README to 1000 characters for NLP
3. **Batch Limiting**: Processes only top 5 READMEs to avoid API rate limits
4. **Model Caching**: SBERT model is loaded once and cached globally

## Error Handling

The function is designed to be resilient:
- Returns partial results if some API calls fail
- Collects errors in the `errors` list
- Continues processing even if NLP steps fail
- Never raises exceptions (returns error dict instead)

## Testing

### Unit Tests
```bash
# Run mocked unit tests
python tests/test_enrich.py
```

### Integration Tests
```bash
# Run with real API calls
python tests/test_enrich.py --integration
```

### Demo
```bash
# See enrichment in action
python scripts/demo_enrich.py
```

## API Integration Example

```python
from fastapi import FastAPI
from backend.enrich import enrich_profile

app = FastAPI()

@app.post("/enrich/{username}")
def enrich_user(username: str, so_user_id: int = None):
    """Enrich a developer profile."""
    profile = enrich_profile(username, so_user_id)
    return profile
```

## Future Enhancements

- [ ] Google Scholar integration
- [ ] LinkedIn profile enrichment
- [ ] Sentiment analysis on README content
- [ ] Skill level inference from code complexity
- [ ] Collaboration network analysis
- [ ] Trend detection in technology adoption

## Dependencies

- `backend.fetchers.github`: GitHub API client
- `backend.fetchers.stackoverflow`: StackOverflow API client
- `backend.storage`: Database operations
- `backend.nlp_ops`: NLP utilities
- `backend.graph_mapping`: ID canonicalization

## Related Modules

- `backend/graph_mapping.py`: Basic profile normalization
- `backend/graph_ops.py`: Graph embeddings (Node2Vec)
- `backend/app.py`: FastAPI endpoints
- `notebooks/role_classification.ipynb`: ML model training
