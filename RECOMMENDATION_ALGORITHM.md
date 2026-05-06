# Repository Recommendation Algorithm

## Overview
The system recommends **4-5 top repositories** to users based on their profile, role, interests, and similarity scores. Only repositories with scores **≥ 50% (0.5)** are recommended.

---

## Recommendation Flow

### 1. **Candidate Selection** (`get_recommendation_candidates`)
- **Input**: User node ID, Graph
- **Process**:
  - Selects all repository nodes from the graph (excludes user's own repos)
  - Filters candidates based on user's languages and topics (profile-based pre-filtering)
  - Prioritizes repositories matching user's primary languages
  - Limits to top 500 candidates for performance

### 2. **Multi-Factor Scoring System**

The system computes three types of scores and combines them:

#### **A. Cosine Similarity Score** (Weight: 70%)
- Uses Node2Vec graph embeddings
- Computes cosine similarity between user and repository embeddings
- Measures structural similarity in the graph

#### **B. Graph Heuristic Score** (Weight: 30%)
- Uses Jaccard coefficient
- Measures how similar the user's connections are to the repository's connections
- Based on shared neighbors in the graph

#### **C. Profile-Based Score** (Additive Boost)
- **Language Match**: +0.25 if repository language matches user's top languages
- **Topic Match**: +0.15 per matching topic in repository description/name
- **Role Keyword Match**: +0.2 if repository matches user's predicted role (e.g., "data scientist", "backend developer")
- **Star Quality**: +0.0 to +0.3 (log-scaled based on repository stars)

**Profile Score Formula:**
```python
profile_score = language_match(0.25) + topic_matches(0.15 each) + role_match(0.2) + star_quality(0-0.3)
profile_score = min(profile_score, 0.9)  # Capped at 0.9
```

### 3. **Score Combination**

```python
# Step 1: Combine cosine similarity and heuristic (weighted average)
base_score = (0.7 × cosine_similarity) + (0.3 × heuristic_score)

# Step 2: Add profile boost
final_score = base_score + profile_score

# Step 3: Apply embedding-based reranking
# Uses Sentence-BERT to compute semantic similarity between:
# - User profile text (role + languages + topics)
# - Repository text (name + description + language)
reranked_score = final_score + (0.6 × semantic_similarity)
```

### 4. **Filtering & Ranking**

1. **Filter Low Scores**: Remove all repositories with score < 0.5 (50%)
2. **Sort**: Rank by final score (descending)
3. **Limit**: Return top 4-5 repositories

---

## Key Features

### ✅ **Personalization Factors**

1. **User's Predicted Role**
   - Extracted from: `ai_role` or `predicted_role` in user node
   - Used for: Role keyword matching in repository descriptions

2. **User's Profile Languages**
   - Extracted from: `top_repo_languages` (top 5 languages)
   - Used for: Language matching with repository languages

3. **User's Topics/Interests**
   - Extracted from: `topics` (top 5 topics)
   - Used for: Topic matching in repository descriptions/names

4. **User's Work**
   - Inferred from: User's connected repositories in the graph
   - Used for: Graph-based similarity calculations

### ✅ **Quality Threshold**

- **Minimum Score**: 0.5 (50%)
- Only repositories scoring ≥ 0.5 are recommended
- Ensures recommendations are relevant and high-quality

### ✅ **Output Constraints**

- **Count**: Exactly 4-5 repositories (prefers 5, minimum 4)
- **Order**: Sorted by final score (highest first)
- **Format**: Includes score, language, description, stars, URL

---

## Example Scoring Scenario

**User Profile:**
- Role: "Data Scientist"
- Languages: ["Python", "SQL"]
- Topics: ["machine-learning", "data-science"]

**Repository: "tensorflow/tensorflow"**
- Language: "Python"
- Description: "Open source machine learning framework"
- Stars: 150,000

**Score Calculation:**
```
cosine_similarity = 0.65 (from graph embeddings)
heuristic_score = 0.45 (Jaccard coefficient)
base_score = (0.7 × 0.65) + (0.3 × 0.45) = 0.59

profile_score = 0.25 (Python match) + 0.15 (machine-learning topic) + 0.20 (data scientist role) + 0.30 (high stars)
              = 0.90 (capped)
final_score = 0.59 + 0.90 = 1.49

semantic_similarity = 0.72 (Sentence-BERT similarity)
reranked_score = 1.49 + (0.6 × 0.72) = 1.92 ✅ (Above 0.5 threshold)
```

---

## Fallback Mechanism

If fewer than 4 high-quality recommendations are found:

1. **GitHub API Search** (as fallback)
   - Query built from: user's role + top language + top topic
   - Example: "data scientist language:Python topic:machine-learning"
   - Results filtered to match user profile
   - Only repositories with score ≥ 0.5 are added

---

## API Endpoint

```
GET /recommend/{node_id}?limit=5
```

**Parameters:**
- `node_id`: User's node ID (e.g., "github:username")
- `limit`: Number of recommendations (default: 5, constrained to 4-5)

**Response:**
```json
[
  {
    "node_id": "github:org/repo",
    "label": "org/repo",
    "type": "repository",
    "score": 0.8234,
    "html_url": "https://github.com/org/repo",
    "language": "Python",
    "description": "Repository description",
    "stargazers_count": 1000,
    "features": {
      "cosine_similarity": 0.65,
      "heuristic_score": 0.45
    }
  },
  ...
]
```

---

## Summary

The recommendation system uses a **multi-factor scoring approach** combining:
- Graph structure (embeddings + heuristics)
- User profile (role, languages, topics)
- Semantic similarity (Sentence-BERT)
- Quality signals (stars)

Only repositories scoring **≥ 50%** are recommended, and the system returns **4-5 top matches** personalized to each user's profile and interests.

