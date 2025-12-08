import React from 'react';
import { Lightbulb, GitBranch, User } from 'lucide-react';

const TopRecommendations = ({ recommendations, onSelectRecommendation, profile, prediction }) => {
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="bento-card" style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
        <p>No recommendations available.</p>
      </div>
    );
  }

  // Profile context
  const userLangs = (profile?.top_repo_languages || [])
    .map(l => (Array.isArray(l) ? String(l[0] || '').toLowerCase() : String(l || '').toLowerCase()))
    .filter(Boolean);
  const userRole = (prediction?.predicted_role || profile?.ai_role || '').toLowerCase();

  // Prefer repo-type items; if none, fall back to top scored items
  const repoItems = recommendations.filter(item => {
    const type = (item.type || '').toLowerCase();
    return type === 'repo' || type === 'github_repo' || type === 'project' || type === 'repository';
  });

  // Apply lightweight client-side boost based on role/languages
  const boosted = (repoItems.length ? repoItems : recommendations).map(item => {
    let boost = 0;
    const lang = (item.features?.language || item.language || '').toLowerCase();
    const text = `${item.label || ''} ${item.name || ''} ${item.description || ''}`.toLowerCase();

    if (lang && userLangs.some(l => lang.includes(l) || l.includes(lang))) boost += 0.15;
    if (userRole && text.includes(userRole)) boost += 0.2;

    return { ...item, __boostedScore: (item.score || 0) + boost };
  });

  const list = boosted
    .slice()
    .sort((a, b) => (b.__boostedScore || 0) - (a.__boostedScore || 0))
    .slice(0, 7);

  return (
    <div className="bento-card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
        <Lightbulb size={20} color="#eab308" />
        <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Top Recommendations</h3>
      </div>

      <div className="repo-list" style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
        {list.length === 0 && (
          <div style={{ padding: '12px', color: '#64748b' }}>No recommendations available.</div>
        )}
        {list.map(item => {
          const scorePercent = item.__boostedScore ? Math.round(item.__boostedScore * 100) : item.score ? Math.round(item.score * 100) : 0;
          const language = item.features?.language || item.language;
          const stars = item.features?.stars ?? item.stargazers_count;
          const type = item.type || 'Repository';
          return (
            <div
              key={item.node_id || item.label || item.name}
              onClick={() => {
                if (item.html_url || item.url) {
                  window.open(item.html_url || item.url, '_blank');
                }
                if (onSelectRecommendation) onSelectRecommendation(item.node_id);
              }}
              style={{
                padding: '12px',
                background: '#fff',
                borderRadius: '6px',
                border: '1px solid #e2e8f0',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer'
              }}
              className="recommendation-row"
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#f8fafc';
                e.currentTarget.style.borderColor = '#cbd5e1';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#fff';
                e.currentTarget.style.borderColor = '#e2e8f0';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                <div style={{ 
                  width: '32px', height: '32px', borderRadius: '8px', 
                  background: '#f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <GitBranch size={16} color="#475569" />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    <span style={{ fontWeight: 600, color: '#1e293b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {item.label || item.name || item.full_name || 'Recommendation'}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                      {[language, stars != null ? `⭐ ${stars}` : null, scorePercent ? `Score ${scorePercent}%` : null, type]
                        .filter(Boolean)
                        .join(' • ')}
                    </span>
                </div>
              </div>

            </div>
          );
        })}
      </div>
    </div>
  );
};

export default TopRecommendations;
