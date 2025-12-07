# GitStack Connect

<div align="center">

**A Developer Intelligence Platform using Social Network Analysis**

*Connecting Developers, Discovering Communities, Recommending Projects*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19.2.0-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688.svg)](https://fastapi.tiangolo.com/)
[![NetworkX](https://img.shields.io/badge/NetworkX-Latest-green.svg)](https://networkx.org/)

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Algorithms & Methodologies](#algorithms--methodologies)
- [Screenshots](#screenshots)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

**GitStack Connect** is a comprehensive developer intelligence platform that analyzes GitHub and StackOverflow profiles to build knowledge graphs, detect communities, and provide personalized repository recommendations. The system combines social network analysis, machine learning, and AI to deliver actionable insights about developer networks and collaboration patterns.

### Key Capabilities

- 🔍 **Profile Enrichment**: Aggregates data from GitHub and StackOverflow
- 📊 **Network Analysis**: Builds knowledge graphs and computes centrality metrics
- 👥 **Community Detection**: Identifies developer communities using Louvain algorithm
- 🎯 **Smart Recommendations**: Provides personalized repository suggestions
- 🤖 **AI-Powered Insights**: Generates summaries and predicts developer roles
- 📈 **Interactive Visualization**: Real-time network graph with multiple layout options

---

## ✨ Features

### 1. **Comprehensive Profile Analysis**
- GitHub profile data (repos, commits, collaborators, languages)
- StackOverflow integration (reputation, badges, tags)
- AI-generated professional summaries (5-6 lines)
- Top worked repositories based on commit activity
- Activity metrics and statistics

### 2. **Network Visualization**
- Interactive graph using Cytoscape.js
- Multiple node types: Users, Repositories, Collaborators, Owners
- Color-coded edges: Pink for repos, Blue for collaborators, Orange for StackOverflow
- Community highlighting with green borders
- 6 different layout options (Force Directed, Circle, Grid, etc.)
- Node type legend for easy understanding

### 3. **Network Metrics**
- **Degree Centrality**: Measures direct connections
- **Betweenness Centrality**: Identifies bridge/broker roles
- **Closeness Centrality**: Measures reachability
- **Influence Score**: Composite metric (0-100)
- Interactive tooltips explaining each metric

### 4. **Personalized Recommendations**
- Profile-based filtering (languages, topics, interests)
- Graph embedding similarity (Node2Vec)
- Topological similarity (Jaccard coefficient)
- AI-powered final ranking (Groq LLM)
- Different suggestions for different users

### 5. **Role Prediction**
- AI-based classification (primary method)
- Rule-based fallback (when AI unavailable)
- Multiple role categories (Frontend, Backend, Full Stack, ML, DevOps, etc.)
- Confidence scores and probability distributions

### 6. **Project Search**
- Multi-source search: GitHub repositories, StackOverflow questions, Research papers
- Independent pagination for each source
- Query-based filtering

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Profile Card │  │  Graph View   │  │Recommendations│     │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/REST API
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Enrich  │  │Recommend │  │ Predict  │  │ Metrics │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │   NLP    │  │  Graph   │  │   LLM    │  │ Storage │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│              External APIs & Data Sources                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ GitHub   │  │StackOver │  │ Research │                  │
│  │   API    │  │  flow    │  │  Papers  │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    Data Storage Layer                        │
│  ┌──────────┐  ┌──────────┐                                │
│  │ SQLite   │  │ NetworkX │                                │
│  │ Database │  │   Graph  │                                │
│  └──────────┘  └──────────┘                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

### Frontend
- **React** 19.2.0 - UI framework
- **Cytoscape.js** 3.33.1 - Network graph visualization
- **Axios** 1.13.2 - HTTP client
- **Lucide React** 0.554.0 - Icon library

### Backend
- **FastAPI** - REST API framework
- **Uvicorn** - ASGI server
- **NetworkX** - Graph data structures and algorithms
- **Node2Vec** - Graph embedding generation
- **Gensim** - Word2Vec implementation
- **SQLAlchemy** - ORM for database operations
- **SQLite** - Relational database
- **Sentence Transformers** - NLP embeddings (SBERT)
- **Scikit-learn** - Machine learning utilities
- **BeautifulSoup4** - HTML parsing
- **Groq** - LLM API integration

### External APIs
- **GitHub API** - User profiles, repositories, commits
- **StackOverflow API** - User profiles, tags, questions
- **Research Papers API** - Academic paper search

---

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- Node.js 16 or higher
- npm or yarn

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd SNA_MINI_PROJECT
```

### Step 2: Backend Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment:**
   - Windows: `.\venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Step 3: Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install Node dependencies:**
   ```bash
   npm install
   ```

3. **Return to root directory:**
   ```bash
   cd ..
   ```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# GitHub API (Optional - for higher rate limits)
GITHUB_API_TOKEN=your_github_token_here

# Groq API (Required for AI features)
GROQ_API_KEY=your_groq_api_key_here

# Gemini API (Optional - fallback)
GEMINI_API_KEY=your_gemini_api_key_here
```

### Getting API Keys

1. **GitHub Token** (Optional):
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate a token with `public_repo` scope

2. **Groq API Key** (Required):
   - Sign up at [console.groq.com](https://console.groq.com)
   - Generate an API key from the dashboard

3. **Gemini API Key** (Optional):
   - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

---

## 🚀 Usage

### Starting the Application

#### 1. Start the Backend Server

```bash
# Activate virtual environment (if not already activated)
.\venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # macOS/Linux

# Start FastAPI server
uvicorn backend.app:app --reload
```

The backend will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Interactive API: `http://localhost:8000/redoc`

#### 2. Start the Frontend Development Server

```bash
# In a new terminal
cd frontend
npm start
```

The frontend will be available at `http://localhost:3000`

### Using the Application

1. **Search for a User**:
   - Enter a GitHub username in the search box
   - Click "Search" to enrich the profile

2. **View Profile**:
   - See comprehensive profile information
   - Check network metrics
   - View top languages and topics

3. **Explore Network Graph**:
   - Interactive visualization of connections
   - Switch between different layouts
   - Hover over nodes for details
   - Click nodes to focus

4. **Get Recommendations**:
   - View personalized repository suggestions
   - Click recommendations to open in GitHub

5. **Search Projects**:
   - Switch to "Project Idea" mode
   - Search across GitHub, StackOverflow, and research papers

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/enrich/{username}` | GET | Enrich GitHub user profile and build graph |
| `/recommend/{node_id}` | GET | Get personalized repository recommendations |
| `/predict/{user_id}` | GET | Predict developer role with confidence scores |
| `/metrics/{node_id}` | GET | Compute network centrality metrics |
| `/search/project` | GET | Search projects across multiple sources |

### Example API Calls

```bash
# Enrich a user profile
curl http://localhost:8000/enrich/torvalds

# Get recommendations
curl http://localhost:8000/recommend/github:torvalds

# Get network metrics
curl http://localhost:8000/metrics/github:torvalds

# Predict role
curl http://localhost:8000/predict/github:torvalds
```

---

## 📁 Project Structure

```
SNA_MINI_PROJECT/
├── backend/
│   ├── app.py                 # FastAPI application and routes
│   ├── enrich.py              # Profile enrichment logic
│   ├── recommendation.py      # Recommendation engine
│   ├── graph_ops.py           # Graph algorithms (Node2Vec, centrality)
│   ├── nlp_ops.py             # NLP operations (topics, summarization)
│   ├── llm.py                 # LLM integration (Groq)
│   ├── storage.py             # Database operations
│   ├── config.py              # Configuration management
│   ├── db.py                  # Database connection
│   ├── graph_mapping.py       # Graph node/edge mapping
│   ├── train_model.py         # Role classification model training
│   ├── fetchers/
│   │   ├── github.py          # GitHub API client
│   │   ├── stackoverflow.py   # StackOverflow API client
│   │   └── research.py        # Research papers API client
│   └── models/
│       └── role_clf.joblib    # Trained role classifier
│
├── frontend/
│   ├── src/
│   │   ├── App.js             # Main application component
│   │   ├── api.js             # API client
│   │   ├── components/
│   │   │   ├── ProfileCard.jsx        # Profile display
│   │   │   ├── GraphView.jsx          # Network visualization
│   │   │   ├── TopRecommendations.jsx # Recommendations panel
│   │   │   └── ProjectResults.jsx     # Project search results
│   │   ├── App.css            # Application styles
│   │   └── index.js           # Entry point
│   ├── public/                # Static assets
│   └── package.json           # Frontend dependencies
│
├── scripts/
│   ├── populate_data.py       # Data population script
│   └── train_model.py         # Model training script
│
├── docs/                      # Additional documentation
├── notebooks/                 # Jupyter notebooks
├── tests/                     # Test files
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── .env                       # Environment variables (create this)
```

---

## 🧮 Algorithms & Methodologies

### 1. Knowledge Graph Construction
- **Nodes**: Users (GitHub, StackOverflow), Repositories, Tags, Topics
- **Edges**: OWNS, CONTRIBUTES_TO, COLLABORATES_WITH, HAS_TAG, HAS_PROFILE
- **Storage**: SQLite database with NetworkX graph representation

### 2. Network Analysis

#### Centrality Metrics
- **Degree Centrality**: `C_D(v) = deg(v) / (n-1)`
- **Betweenness Centrality**: Measures bridge role in network
- **Closeness Centrality**: `C_C(v) = (n-1) / Σd(v,t)`
- **Influence Score**: `(Degree × 0.4 + Betweenness × 0.4 + Closeness × 0.2) × 100`

#### Community Detection
- **Louvain Algorithm**: Hierarchical community detection
- **Modularity Optimization**: Maximizes connections within communities
- **Visual Highlighting**: Green borders for same-community members

### 3. Recommendation System

#### Multi-Stage Pipeline
1. **Candidate Selection**: Profile-based filtering (languages, topics)
2. **Graph Embeddings**: Node2Vec (64 dimensions, walk_length=10, num_walks=100)
3. **Similarity Scoring**:
   - Cosine Similarity: `cos(θ) = (A·B) / (||A|| × ||B||)`
   - Jaccard Coefficient: `J(A,B) = |A ∩ B| / |A ∪ B|`
4. **Score Combination**: `α × cosine_sim + (1-α) × jaccard` (α=0.7)
5. **Profile Boost**: Additional scoring for language/topic matches
6. **AI Ranking**: Groq LLM final ranking based on user profile context

### 4. Natural Language Processing

#### Topic Extraction
- **Method**: SBERT embeddings + K-Means clustering
- **Model**: `all-MiniLM-L6-v2` (Sentence Transformers)
- **Process**: Extract text → Generate embeddings → Cluster → Extract keywords

#### Summarization
- **Method**: Centroid-based extractive summarization
- **Output**: 5-6 line professional summaries
- **Process**: Select sentences closest to text centroid

#### Role Classification
- **Primary**: AI-based using Groq LLM
- **Fallback**: Rule-based keyword matching
- **Categories**: Frontend, Backend, Full Stack, ML Engineer, DevOps, Mobile, Security, etc.

---

## 📸 Screenshots

### Main Features
- **Profile Card**: Comprehensive developer information with metrics
- **Network Graph**: Interactive visualization with community highlighting
- **Recommendations**: Personalized repository suggestions
- **Metrics Dashboard**: Network centrality measures with explanations

---

## 📚 Documentation

Additional documentation is available in the `docs/` directory:

- **PROJECT_REPORT.md**: Comprehensive project report
- **PRESENTATION_OUTLINE.md**: Presentation guide with 25 slides
- **QUICK_REFERENCE.md**: Quick reference guide
- **HARDCODED_ANALYSIS.md**: Code analysis report

---

## 🧪 Testing

Run tests using:

```bash
# Backend tests
python -m pytest tests/

# Frontend tests
cd frontend
npm test
```

---

## 🚧 Development

### Populating Data

To populate the database with sample users:

```bash
python scripts/populate_data.py
```

### Training Role Classifier

To train the role classification model:

```bash
python scripts/train_model.py
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- **NetworkX** - Graph algorithms and data structures
- **Node2Vec** - Graph embedding generation
- **Sentence Transformers** - NLP embeddings
- **Groq** - LLM API for AI features
- **Cytoscape.js** - Network visualization
- **FastAPI** - Modern web framework
- **React** - UI framework

---

## 📧 Contact

For questions, issues, or contributions, please open an issue on GitHub.

---

## 🎯 Future Roadmap

- [ ] Add more data sources (GitLab, Bitbucket)
- [ ] Implement real-time graph updates
- [ ] Graph database migration (Neo4j)
- [ ] Machine learning model improvements
- [ ] Mobile application
- [ ] Advanced analytics dashboard
- [ ] Collaborative filtering for recommendations
- [ ] Real-time collaboration features

---

<div align="center">

**Built with ❤️ using Social Network Analysis, Machine Learning, and AI**

⭐ Star this repo if you find it useful!

</div>
