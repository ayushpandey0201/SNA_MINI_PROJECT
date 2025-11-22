import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const MOCK_PROFILE = {
    "node_ids": {
        "github_user_id": "github:gaearon",
        "so_user_id": "so:12345"
    },
    "github_stats": {
        "login": "gaearon",
        "name": "Dan Abramov",
        "bio": "Working on React.",
        "company": "@facebook",
        "location": "London, UK",
        "followers": 65000,
        "public_repos": 250
    },
    "so_stats": {
        "reputation": 15000,
        "badge_counts": { "gold": 10, "silver": 20, "bronze": 50 }
    },
    "top_repo_languages": [
        ["JavaScript", 150],
        ["TypeScript", 50],
        ["HTML", 20]
    ],
    "top_so_tags": [
        ["reactjs", 500],
        ["redux", 300],
        ["javascript", 200]
    ],
    "top_topics": ["react", "frontend", "ui", "state-management"],
    "activity_counts": {
        "repo_count": 250,
        "total_stars": 100000,
        "total_forks": 20000
    },
    "bio_summary": "Dan Abramov is a software engineer at Facebook working on React. He is the co-author of Redux and Create React App."
};

export const MOCK_RECOMMENDATIONS = [
    {
        "node_id": "github:sophiebits",
        "score": 0.92,
        "features": { "similarity": 0.95, "jaccard": 0.4 }
    },
    {
        "node_id": "github:acdlite",
        "score": 0.88,
        "features": { "similarity": 0.85, "jaccard": 0.35 }
    },
    {
        "node_id": "github:bvaughn",
        "score": 0.85,
        "features": { "similarity": 0.80, "jaccard": 0.3 }
    }
];

export const fetchProfile = async (username) => {
    try {
        // Try to fetch from real API
        const response = await axios.get(`${API_BASE_URL}/enrich/${username}`);
        return response.data;
    } catch (error) {
        console.warn("API fetch failed, falling back to mock data (if applicable) or re-throwing", error);
        // For development, if API is down, you might want to return mock:
        // return MOCK_PROFILE; 
        throw error;
    }
};

export const fetchRecommendations = async (nodeId) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/recommend/${nodeId}`);
        return response.data;
    } catch (error) {
        console.warn("API fetch failed", error);
        // return MOCK_RECOMMENDATIONS;
        throw error;
    }
};

export const fetchPrediction = async (userId) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/predict/${userId}`);
        return response.data;
    } catch (error) {
        console.warn("Prediction API failed", error);
        return null;
    }
}
