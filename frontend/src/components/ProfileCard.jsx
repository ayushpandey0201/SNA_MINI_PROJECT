import React from 'react';
import { Github, Star, GitFork, MapPin, Briefcase, Award } from 'lucide-react';

const ProfileCard = ({ profile, prediction }) => {
    if (!profile) return null;

    const { github_stats, so_stats, top_repo_languages, top_topics, activity_counts, bio_summary } = profile;

    return (
        <div className="profile-container">
            {/* Header Section */}
            <div className="profile-header">
                <div className="header-content">
                    <h2>{github_stats.name || github_stats.login}</h2>
                    <span className="username">@{github_stats.login}</span>
                    {prediction && (
                        <div className="role-badge">
                            Role: <strong>{prediction.predicted_role.toUpperCase()}</strong>
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

            {/* Stats Grid */}
            <div className="stats-grid">
                <div className="stat-card">
                    <h3>GitHub Activity</h3>
                    <div className="stat-row">
                        <span>Repos:</span> <strong>{activity_counts.repo_count}</strong>
                    </div>
                    <div className="stat-row">
                        <span>Stars:</span> <strong>{activity_counts.total_stars}</strong>
                    </div>
                    <div className="stat-row">
                        <span>Forks:</span> <strong>{activity_counts.total_forks}</strong>
                    </div>
                </div>

                {so_stats && so_stats.reputation && (
                    <div className="stat-card">
                        <h3>StackOverflow</h3>
                        <div className="stat-row">
                            <span>Reputation:</span> <strong>{so_stats.reputation}</strong>
                        </div>
                        <div className="stat-row">
                            <span>Badges:</span>
                            <span className="badges">
                                <span className="badge gold">● {so_stats.badge_counts?.gold || 0}</span>
                                <span className="badge silver">● {so_stats.badge_counts?.silver || 0}</span>
                                <span className="badge bronze">● {so_stats.badge_counts?.bronze || 0}</span>
                            </span>
                        </div>
                    </div>
                )}
            </div>

            {/* Languages & Topics */}
            <div className="tags-section">
                <h3>Top Languages</h3>
                <div className="tag-cloud">
                    {top_repo_languages.map(([lang, count]) => (
                        <span key={lang} className="tag language-tag">
                            {lang} <small>({count})</small>
                        </span>
                    ))}
                </div>
            </div>

            <div className="tags-section">
                <h3>Topics</h3>
                <div className="tag-cloud">
                    {top_topics.map((topic) => (
                        <span key={topic} className="tag topic-tag">#{topic}</span>
                    ))}
                </div>

                {/* Summary */}
                {bio_summary && (
                    <div className="summary-section">
                        <h3>Summary</h3>
                        <p>{bio_summary}</p>
                    </div>
                )}
            </div>


        </div>
    );
};

export default ProfileCard;
