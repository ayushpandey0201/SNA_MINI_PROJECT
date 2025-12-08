import React, { useState } from 'react';
import './App.css';
import ProfileCard from './components/ProfileCard';
import GraphView from './components/GraphView';
import ProjectResults from './components/ProjectResults';
import TopRecommendations from './components/TopRecommendations';
import { fetchProfile, fetchRecommendations, fetchPrediction, fetchMetrics, fetchProjectIdeas } from './api';
import { Search, Activity, Lightbulb, User } from 'lucide-react';

function App() {
  const [username, setUsername] = useState('');
  const [profile, setProfile] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [focusedNodeId, setFocusedNodeId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showRecommendations] = useState(true);
  const [isGraphFullScreen, setIsGraphFullScreen] = useState(false);

  // New State for Project Search
  const [searchMode, setSearchMode] = useState('user'); // 'user' or 'project'
  const [projectResults, setProjectResults] = useState(null);
  // Independent pagination state for each section
  const [pages, setPages] = useState({ repo: 1, so: 1, paper: 1 });

  const handleFetch = async (e, newPages = null) => {
    if (e) e.preventDefault();
    if (!username) return;

    setLoading(true);
    setError(null);

    const currentPages = newPages || pages;
    if (newPages) setPages(newPages);

    // Reset previous results based on mode only if it's a fresh search (all pages 1)
    if (!newPages) {
      // This is a fresh search from the form submit
      const resetPages = { repo: 1, so: 1, paper: 1 };
      setPages(resetPages);

      if (searchMode === 'user') {
        setProfile(null);
        setRecommendations([]);
        setPrediction(null);
      } else {
        setProjectResults(null);
      }
      // Use reset pages for the fetch
      await performFetch(username, searchMode, resetPages);
    } else {
      // This is a pagination update
      await performFetch(username, searchMode, currentPages);
    }
  };

  const performFetch = async (user, mode, currentPages) => {
    try {
      if (mode === 'user') {
        // 1. Fetch Profile
        const profileData = await fetchProfile(user);

        if (profileData.errors && profileData.errors.length > 0) {
          setError(profileData.errors.join(", "));
          setProfile(null);
          return;
        }

        setProfile(profileData);

        // 2. Fetch Recommendations, Prediction, and Metrics
        if (profileData && profileData.node_ids && profileData.node_ids.github_user_id) {
          const nodeId = profileData.node_ids.github_user_id;
          const [recs, pred, met] = await Promise.all([
            fetchRecommendations(nodeId),
            fetchPrediction(nodeId),
            fetchMetrics(nodeId)
          ]);
          setRecommendations(recs);
          setPrediction(pred);
          setMetrics(met);
        }
      } else {
        // Project Search Mode
        const results = await fetchProjectIdeas(user, currentPages);
        setProjectResults(results);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to fetch data. Ensure backend is running.");
    } finally {
      setLoading(false);
    }
  }

  const handleSectionPageChange = (section, newPage) => {
    const newPages = { ...pages, [section]: newPage };
    // Trigger fetch with new pages state
    handleFetch(null, newPages);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="logo">
          <Activity size={28} />
          <h1>GitStack Connect</h1>
        </div>
        <p>GitHub & StackOverflow Network Analysis</p>
      </header>

      <main>
        <div className="search-section">
          {/* Mode Toggle */}
          <div className="mode-toggle" style={{ display: 'flex', gap: '10px', marginBottom: '16px', justifyContent: 'center' }}>
            <button
              type="button"
              onClick={() => { setSearchMode('user'); setPages({ repo: 1, so: 1, paper: 1 }); }}
              style={{
                background: searchMode === 'user' ? '#0f172a' : '#e2e8f0',
                color: searchMode === 'user' ? 'white' : '#64748b',
                boxShadow: 'none'
              }}
            >
              <User size={16} /> User Search
            </button>
            <button
              type="button"
              onClick={() => { setSearchMode('project'); setPages({ repo: 1, so: 1, paper: 1 }); }}
              style={{
                background: searchMode === 'project' ? '#0f172a' : '#e2e8f0',
                color: searchMode === 'project' ? 'white' : '#64748b',
                boxShadow: 'none'
              }}
            >
              <Lightbulb size={16} /> Project Ideas
            </button>
          </div>

          <form onSubmit={(e) => handleFetch(e)} className="search-form">
            <input
              type="text"
              placeholder={searchMode === 'user' ? "Enter GitHub Username (e.g. torvalds)" : "Enter Project Topic (e.g. expense tracker)"}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <button type="submit" disabled={loading}>
              {loading ? 'Searching...' : <><Search size={18} /> Search</>}
            </button>
          </form>
          {error && <div className="error-message">{error}</div>}
        </div>

        {/* User Search Results */}
        {searchMode === 'user' && profile && (
          <div className="content-grid">
            <div className="left-panel">
              <ProfileCard profile={profile} prediction={prediction} metrics={metrics} />
            </div>

            <div className="right-panel">
              {/* AI Summary Section */}
              {(profile.ai_analysis || profile.bio_summary) && (
                <div className="bento-card" style={{ marginBottom: '24px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#0369a1' }}>
                    <span style={{ fontWeight: 'bold', textTransform: 'uppercase', fontSize: '0.8rem', letterSpacing: '0.05em' }}>Summary</span>
                  </div>
                  <p style={{ margin: 0, fontSize: '0.95rem', lineHeight: '1.6', color: '#334155' }}>
                    {profile.ai_analysis || profile.bio_summary}
                  </p>
                </div>
              )}

              <div className="panel-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <h2>Network Graph</h2>
                <button
                  type="button"
                  onClick={() => setIsGraphFullScreen(true)}
                  style={{ padding: '6px 10px', fontSize: '0.9rem' }}
                >
                  Full Screen
                </button>
              </div>

              <GraphView
                profile={profile}
                recommendations={recommendations}
                showRecommendations={showRecommendations}
                metrics={metrics}
                prediction={prediction}
                style={{ flex: 1 }}
                focusedNodeId={focusedNodeId}
              />


              {/* 2. Suggested Repositories (Swapped) */}
              <div style={{ marginTop: '24px', width: '100%', gridColumn: '1 / -1', flex: 1, display: 'flex', flexDirection: 'column' }}>
                <TopRecommendations
                  recommendations={recommendations}
                  onSelectRecommendation={(id) => setFocusedNodeId(id)}
                />
              </div>
            </div>
          </div>
        )}

        {/* Project Search Results */}
        {searchMode === 'project' && projectResults && (
          <div className="project-results-container">
            <h2 style={{ textAlign: 'center', marginBottom: '24px', color: '#1e293b' }}>
              Results for "{username}"
            </h2>
            <ProjectResults
              results={projectResults}
              pages={pages}
              onPageChange={handleSectionPageChange}
              loading={loading}
            />
          </div>
        )
        }
      </main >
      {/* Fullscreen Graph Overlay */}
      {isGraphFullScreen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            background: '#fff',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <h2 style={{ margin: 0 }}>Network Graph</h2>
            <button
              type="button"
              onClick={() => setIsGraphFullScreen(false)}
              style={{ padding: '6px 10px', fontSize: '0.9rem' }}
            >
              Minimize
            </button>
          </div>
          <div style={{ flex: 1, border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
            <GraphView
              profile={profile}
              recommendations={recommendations}
              showRecommendations={showRecommendations}
              metrics={metrics}
              prediction={prediction}
              style={{ width: '100%', height: '100%' }}
              focusedNodeId={focusedNodeId}
            />
          </div>
        </div>
      )}
    </div >
  );
}

export default App;
