import React from 'react';
import { Lightbulb, GitBranch, User } from 'lucide-react';

const TopRecommendations = ({ recommendations, onSelectRecommendation }) => {
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="bento-card" style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
        <p>No recommendations available.</p>
      </div>
    );
  }

  return (
    <div className="bento-card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
        <Lightbulb size={20} color="#eab308" />
        <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Top Recommendations</h3>
      </div>

      <div className="repo-list" style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
        {recommendations
          .filter(item => {
            // Filter to show only repositories (repo, github_repo, project, repository types)
            const type = (item.type || '').toLowerCase();
            return type === 'repo' || type === 'github_repo' || type === 'project' || type === 'repository';
          })
          .slice(0, 7)
          .map(item => {
          // Determine icon based on type
          let Icon = GitBranch;
          if (item.type === 'user' || item.type === 'developer') Icon = User;
          
          const scorePercent = item.score ? Math.round(item.score * 100) : 0;
          
          return (
            <div
              key={item.node_id || item.label}
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
                  <Icon size={16} color="#475569" />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    <span style={{ fontWeight: 600, color: '#1e293b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {item.label || item.name}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'capitalize' }}>
                        {item.type || 'Repo'}
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
