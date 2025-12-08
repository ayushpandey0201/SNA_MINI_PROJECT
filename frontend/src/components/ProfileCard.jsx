import React, { useState } from 'react';
import { MapPin, Briefcase, Activity, Info } from 'lucide-react';

// MetricBox component with info tooltip
const MetricBox = ({ label, value, tooltip, highlight = false }) => {
    const [showTooltip, setShowTooltip] = useState(false);

    return (
        <div 
            className="stat-box" 
            style={{ 
                textAlign: 'center', 
                padding: '12px',
                position: 'relative',
                background: highlight ? '#f0fdf4' : 'transparent',
                border: highlight ? '1px solid #bbf7d0' : 'none'
            }}
        >
            <div style={{ 
                fontSize: '0.75rem', 
                color: highlight ? '#166534' : '#64748b', 
                marginBottom: '4px',
                fontWeight: highlight ? 'bold' : 'normal',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '4px'
            }}>
                {label}
                <Info 
                    size={12} 
                    style={{ cursor: 'pointer', color: highlight ? '#166534' : '#64748b' }}
                    onMouseEnter={() => setShowTooltip(true)}
                    onMouseLeave={() => setShowTooltip(false)}
                    onClick={() => setShowTooltip(!showTooltip)}
                />
            </div>
            <div style={{ 
                fontSize: '1.1rem', 
                fontWeight: 'bold', 
                color: highlight ? '#15803d' : '#0f172a' 
            }}>
                {value}
            </div>
            {showTooltip && (
                <div 
                    style={{
                        position: 'absolute',
                        bottom: '100%',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        marginBottom: '8px',
                        padding: '10px 12px',
                        backgroundColor: '#1e293b',
                        color: '#f1f5f9',
                        borderRadius: '6px',
                        fontSize: '0.75rem',
                        width: '280px',
                        zIndex: 1000,
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
                        lineHeight: '1.4',
                        textAlign: 'left'
                    }}
                    onMouseEnter={() => setShowTooltip(true)}
                    onMouseLeave={() => setShowTooltip(false)}
                >
                    <div style={{ fontWeight: 'bold', marginBottom: '4px', color: '#fbbf24' }}>
                        {label} Centrality
                    </div>
                    <div>{tooltip}</div>
                    <div 
                        style={{
                            position: 'absolute',
                            bottom: '-4px',
                            left: '50%',
                            transform: 'translateX(-50%)',
                            width: 0,
                            height: 0,
                            borderLeft: '6px solid transparent',
                            borderRight: '6px solid transparent',
                            borderTop: '6px solid #1e293b'
                        }}
                    />
                </div>
            )}
        </div>
    );
};

const ProfileCard = ({ profile, prediction, metrics }) => {
    if (!profile) return null;

    const { github_stats, so_stats, top_repo_languages, top_topics, activity_counts } = profile;

    return (
        <div className="profile-container">
            {/* Header Section - Bento Card */}
            <div className="bento-card profile-header-card">
                <div className="profile-header">
                    <h2>{github_stats.name || github_stats.login}</h2>
                    <span className="username">@{github_stats.login}</span>



                    {prediction && (
                        <div className="role-badge" style={{ marginTop: '8px', fontSize: '0.9rem', background: '#e0f2fe', color: '#0369a1', padding: '6px 12px' }}>
                            Role Prediction: {prediction.predicted_role}
                            {prediction.probabilities && prediction.probabilities[prediction.predicted_role] !== undefined && (
                                <span style={{ marginLeft: '4px', opacity: 0.8 }}>
                                    ({Math.round(prediction.probabilities[prediction.predicted_role] * 100)}%)
                                </span>
                            )}
                        </div>
                    )}
                    <p className="bio">{github_stats.bio}</p>

                    <div className="meta-info">
                        {github_stats.company && (
                            <span className="meta-item">
                                <Briefcase size={16} /> {github_stats.company}
                            </span>
                        )}
                        {github_stats.location && (
                            <span className="meta-item">
                                <MapPin size={16} /> {github_stats.location}
                            </span>
                        )}
                    </div>
                </div>
            </div>

            {/* AI Summary moved to parent component */}

            {/* Stats Grid - Bento Cards */}
            <div className="stats-grid">
                <div className="stat-box">
                    <h3>GitHub Activity</h3>
                    <div className="stat-row">
                        <span>Repos</span> <strong>{activity_counts.repo_count}</strong>
                    </div>
                    <div className="stat-row">
                        <span>Stars</span> <strong>{activity_counts.total_stars}</strong>
                    </div>
                    <div className="stat-row">
                        <span>Forks</span> <strong>{activity_counts.total_forks}</strong>
                    </div>
                </div>

                {so_stats && so_stats.reputation && (
                    <div className="stat-box">
                        <h3>StackOverflow</h3>
                        <div className="stat-row">
                            <span>Reputation</span> <strong>{so_stats.reputation}</strong>
                        </div>
                        <div className="stat-row">
                            <span>Badges</span>
                            <span className="badges">
                                <span className="badge gold">Gold ({so_stats.badge_counts?.gold || 0})</span>
                                <span className="badge silver">Silver ({so_stats.badge_counts?.silver || 0})</span>
                                <span className="badge bronze">Bronze ({so_stats.badge_counts?.bronze || 0})</span>
                            </span>
                        </div>
                    </div>
                )}
            </div>

            {/* Languages & Topics - Bento Card */}
            <div className="bento-card">
                <div className="tags-section">
                    <h3>Top Languages</h3>
                    <div className="tag-cloud">
                        {top_repo_languages.map(([lang, count]) => (
                            <span key={lang} className="tag language-tag">
                                {lang}
                            </span>
                        ))}
                    </div>
                </div>

                <div className="tags-section" style={{ marginTop: '24px' }}>
                    <h3>Topics</h3>
                    <div className="tag-cloud">
                        {top_topics.map((topic) => (
                            <span key={topic} className="tag topic-tag">#{topic}</span>
                        ))}
                    </div>
                </div>
            </div>




            {/* Network Metrics - Bento Card */}
            {metrics && (
                <div className="bento-card" style={{ marginTop: '24px' }}>
                    <div className="tags-section">
                        <h3>Network Metrics</h3>
                        <div className="stats-grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                            <MetricBox 
                                label="Degree" 
                                value={metrics.degree_centrality}
                                tooltip="Degree Centrality measures how many direct connections a node has. Higher values indicate more direct connections to other nodes in the network. Calculated as: (number of connections) / (total possible connections)."
                            />
                            <MetricBox 
                                label="Betweenness" 
                                value={metrics.betweenness_centrality}
                                tooltip="Betweenness Centrality measures how often a node acts as a bridge along the shortest path between two other nodes. Higher values indicate the node is crucial for connecting different parts of the network. Calculated by counting shortest paths that pass through this node."
                            />
                            <MetricBox 
                                label="Closeness" 
                                value={metrics.closeness_centrality}
                                tooltip="Closeness Centrality measures how close a node is to all other nodes in the network. Higher values indicate the node can reach all other nodes quickly. Calculated as: (number of nodes - 1) / (sum of shortest distances to all other nodes)."
                            />
                            <MetricBox 
                                label="Activity Score" 
                                value={`${Math.round(metrics.influence_score || 0)}%`}
                                tooltip="Activity Score summarizes network engagement using centralities: Degree (0.4), Betweenness (0.4), Closeness (0.2), scaled to ~0–100. Higher means more connected, bridging, and reachable."
                                highlight={true}
                            />
                        </div>
                    </div>
                </div>
            )}

            {/* Top Worked Repositories (Moved from App.js) */}
            {profile.top_active_repos && profile.top_active_repos.length > 0 && (
                <div className="bento-card" style={{ marginTop: '24px' }}>
                    <div className="tags-section">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                            <Activity size={20} color="#3b82f6" />
                            <h3 style={{ margin: 0, fontSize: '0.9rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Top Worked Repos</h3>
                        </div>

                        <div className="repo-list" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {profile.top_active_repos.slice(0, 4).map(repo => (
                                <a
                                    key={repo.id}
                                    href={repo.html_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ textDecoration: 'none', color: 'inherit' }}
                                >
                                    <div className="repo-row" style={{
                                        padding: '12px',
                                        background: '#fff',
                                        borderRadius: '6px',
                                        border: '1px solid #e2e8f0',
                                        transition: 'all 0.2s ease',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between'
                                    }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.backgroundColor = '#f8fafc';
                                            e.currentTarget.style.borderColor = '#cbd5e1';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.backgroundColor = '#fff';
                                            e.currentTarget.style.borderColor = '#e2e8f0';
                                        }}
                                    >
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500, color: '#1e293b' }}>
                                            {repo.name}
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', color: '#64748b', flexShrink: 0 }}>
                                            {repo.commit_count !== undefined && repo.commit_count > 0 && (
                                                <span style={{ fontWeight: 600, color: '#3b82f6' }}>💻 {repo.commit_count} commits</span>
                                            )}
                                            <span>⭐ {repo.stargazers_count}</span>
                                        </div>
                                    </div>
                                </a>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ProfileCard;
