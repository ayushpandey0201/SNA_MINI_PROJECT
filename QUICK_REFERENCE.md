# GitStack Connect - Quick Reference Guide

## Project Overview
**GitStack Connect** is a developer intelligence platform that analyzes GitHub and StackOverflow profiles to build knowledge graphs, detect communities, and provide personalized repository recommendations.

---

## Key Technologies

### Frontend
- React 19.2.0
- Cytoscape.js (graph visualization)
- Axios (HTTP client)

### Backend
- FastAPI (REST API)
- NetworkX (graph algorithms)
- Node2Vec (graph embeddings)
- Sentence Transformers (NLP)
- Groq LLM (AI features)
- SQLite (database)

---

## Core Algorithms

### 1. Node2Vec Embeddings
- **Purpose**: Convert graph to vector representations
- **Dimensions**: 64
- **Use**: Similarity computation for recommendations

### 2. Louvain Community Detection
- **Purpose**: Identify developer communities
- **Method**: Modularity optimization
- **Output**: Community IDs for each node

### 3. Centrality Metrics
- **Degree**: Number of connections
- **Betweenness**: Bridge role in network
- **Closeness**: Average distance to others
- **Influence**: Composite score (0-100)

### 4. Recommendation Pipeline
1. Profile-based candidate filtering
2. Node2Vec cosine similarity
3. Jaccard coefficient (topology)
4. Profile boost (language/topic match)
5. LLM-based final ranking

### 5. Project Ideas Search
- **Sources**: GitHub repositories, StackOverflow questions, Dev.to articles
- **Method**: Parallel API calls with independent pagination
- **Query**: User enters any project idea, technology, or topic
- **Results**: Unified display with separate sections for each source

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/enrich/{username}` | GET | Enrich GitHub profile |
| `/recommend/{node_id}` | GET | Get recommendations |
| `/predict/{user_id}` | GET | Predict role |
| `/metrics/{node_id}` | GET | Network metrics |
| `/search/project` | GET | Search project ideas across GitHub, StackOverflow, and Dev.to |

---

## Data Flow

```
User Input → GitHub API → Data Processing → Graph Building → Storage
                                                      ↓
Recommendations ← LLM Ranking ← Scoring ← Embeddings ← Graph

Project Search: Query → Parallel API Calls (GitHub, SO, Dev.to) → Unified Results
```

---

## Key Features

1. **Profile Enrichment**: GitHub + StackOverflow data aggregation
2. **Network Visualization**: Interactive graph with Cytoscape.js
3. **Community Detection**: Louvain algorithm with visual highlighting
4. **Recommendations**: Multi-stage personalized repository suggestions
5. **Role Prediction**: AI + rule-based classification
6. **Network Metrics**: Centrality measures with explanations
7. **Project Ideas Search**: Multi-source search (GitHub repos, StackOverflow questions, Dev.to articles)

---

## File Structure

```
backend/
  ├── app.py              # FastAPI application
  ├── enrich.py           # Profile enrichment
  ├── recommendation.py   # Recommendation engine
  ├── graph_ops.py        # Graph algorithms
  ├── nlp_ops.py          # NLP operations
  ├── llm.py              # LLM integration
  ├── storage.py          # Database operations
  └── fetchers/           # API clients

frontend/src/
  ├── App.js              # Main application
  ├── components/
  │   ├── ProfileCard.jsx
  │   ├── GraphView.jsx
  │   ├── TopRecommendations.jsx
  │   └── ProjectResults.jsx
  └── api.js              # API client
```

---

## Important Formulas

### Influence Score
```
Influence = (Degree × 0.4 + Betweenness × 0.4 + Closeness × 0.2) × 100
```

### Recommendation Score
```
Score = α × Cosine_Similarity + (1-α) × Jaccard + Profile_Boost
where α = 0.7
```

### Jaccard Coefficient
```
J(A,B) = |A ∩ B| / |A ∪ B|
```

---

## Configuration

### Environment Variables
- `GITHUB_API_TOKEN`: GitHub API token (optional)
- `GROQ_API_KEY`: Groq API key (required for AI features)
- `GEMINI_API_KEY`: Gemini API key (optional, fallback)

### Default Ports
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

---

## Performance Metrics

- **Enrichment**: 5-15 seconds per user
- **Recommendations**: 1-3 seconds
- **Metrics**: <1 second
- **Project Search**: 1-2 seconds (parallel API calls)
- **Graph Rendering**: Real-time

---

## Common Use Cases

1. **Discover Projects**: Find repositories matching your skills
2. **Network Analysis**: Understand your position in developer community
3. **Community Detection**: Identify developer clusters
4. **Profile Analysis**: Get comprehensive developer insights
5. **Role Prediction**: Automatically classify developer roles
6. **Project Ideas Search**: Enter any query to find projects, solutions, and articles from GitHub, StackOverflow, and Dev.to

---

## Troubleshooting

### Issue: API Quota Exceeded
- **Solution**: System automatically falls back to rule-based methods

### Issue: No Recommendations
- **Check**: User must have enriched profile in database
- **Check**: Graph must have sufficient nodes

### Issue: Slow Performance
- **Solution**: Embeddings are cached, first run may be slower
- **Solution**: Limit candidate pool size

---

## Future Enhancements

- More data sources (GitLab, Bitbucket)
- Graph database migration (Neo4j)
- Real-time updates
- Mobile application
- Advanced analytics dashboard

