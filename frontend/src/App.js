import React, { useState } from 'react';
import './App.css';
import ProfileCard from './components/ProfileCard';
import GraphView from './components/GraphView';
import { fetchProfile, fetchRecommendations, fetchPrediction, MOCK_PROFILE, MOCK_RECOMMENDATIONS } from './api';
import { Search, Share2, Activity } from 'lucide-react';

function App() {
  const [username, setUsername] = useState('');
  const [profile, setProfile] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showRecommendations, setShowRecommendations] = useState(true);

  const handleFetch = async (e) => {
    e.preventDefault();
    if (!username) return;

    setLoading(true);
    setError(null);
    setProfile(null);
    setRecommendations([]);
    setPrediction(null);

    try {
      // 1. Fetch Profile
      const profileData = await fetchProfile(username);

      if (profileData.errors && profileData.errors.length > 0) {
        setError(profileData.errors.join(", "));
        setProfile(null); // Don't show partial profile
        return;
      }

      setProfile(profileData);

      // 2. Fetch Recommendations (using the node ID from profile)
      if (profileData && profileData.node_ids && profileData.node_ids.github_user_id) {
        const nodeId = profileData.node_ids.github_user_id;

        // Parallel fetch for recommendations and prediction
        const [recs, pred] = await Promise.all([
          fetchRecommendations(nodeId),
          fetchPrediction(nodeId)
        ]);

        setRecommendations(recs);
        setPrediction(pred);
      }

    } catch (err) {
      console.error(err);
      setError("Failed to fetch data. Ensure backend is running.");
      // Fallback for demo if backend is offline
      // setProfile(MOCK_PROFILE);
      // setRecommendations(MOCK_RECOMMENDATIONS);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="logo">
          <Activity size={28} />
          <h1>Dev-Intel SNA</h1>
        </div>
        <p>Developer Social Network Analysis & Role Prediction</p>
      </header>

      <main>
        <div className="search-section">
          <form onSubmit={handleFetch} className="search-form">
            <input
              type="text"
              placeholder="Enter GitHub Username (e.g. torvalds)"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <button type="submit" disabled={loading}>
              {loading ? 'Analyzing...' : <><Search size={18} /> Analyze</>}
            </button>
          </form>
          {error && <div className="error-message">{error}</div>}
        </div>

        {profile && (
          <div className="content-grid">
            <div className="left-panel">
              <ProfileCard profile={profile} prediction={prediction} />
            </div>

            <div className="right-panel">
              <div className="panel-header">
                <h2>Network Graph</h2>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={showRecommendations}
                    onChange={(e) => setShowRecommendations(e.target.checked)}
                  />
                  <span className="slider"></span>
                  <span className="label-text">Show Recommendations</span>
                </label>
              </div>
              <GraphView
                profile={profile}
                recommendations={recommendations}
                showRecommendations={showRecommendations}
              />

              {recommendations.length > 0 && (
                <div className="recommendations-list">
                  <h3>Top Recommendations</h3>
                  <ul>
                    {recommendations.map(rec => (
                      <li key={rec.node_id}>
                        <Share2 size={14} />
                        <span className="rec-name">{rec.node_id.split(':')[1]}</span>
                        <span className="rec-score">{(rec.score * 100).toFixed(0)}% Match</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
