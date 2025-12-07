import React from 'react';
import { Book, Code, FileText, ExternalLink } from 'lucide-react';

const PaginationControls = ({ page, onPageChange, loading, hasNext }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #e2e8f0' }}>
        <button 
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={page === 1 || loading}
            style={{ 
                background: 'transparent', 
                color: page === 1 ? '#cbd5e1' : '#64748b', 
                border: 'none', 
                cursor: page === 1 ? 'default' : 'pointer',
                fontSize: '0.85rem',
                padding: '4px 8px'
            }}
        >
            &larr; Prev
        </button>
        <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Page {page}</span>
        <button 
            onClick={() => onPageChange(page + 1)}
            disabled={!hasNext || loading}
            style={{ 
                background: 'transparent', 
                color: !hasNext ? '#cbd5e1' : '#3b82f6', 
                border: 'none', 
                cursor: !hasNext ? 'default' : 'pointer',
                fontSize: '0.85rem',
                padding: '4px 8px'
            }}
        >
            Next &rarr;
        </button>
    </div>
);

const ProjectResults = ({ results, pages, onPageChange, loading }) => {
    if (!results) return null;

    const { repos, questions, papers } = results;

    // Helper to extract items and hasNext safely, handling both new (dict) and old (list) formats
    const getListData = (data) => {
        if (!data) return { items: [], hasNext: false };
        if (Array.isArray(data)) return { items: data, hasNext: false }; // Old format
        return { items: data.items || [], hasNext: !!data.has_next }; // New format
    };

    const repoData = getListData(repos);
    const questionData = getListData(questions);
    const paperData = getListData(papers);

    return (
        <div className="project-results-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>
            
            {/* GitHub Repositories */}
            <div className="bento-card">
                <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                    <Code size={20} color="#3b82f6" />
                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Repositories</h3>
                </div>
                <div className="results-list" style={{ display: 'flex', flexDirection: 'column', gap: '12px', minHeight: '300px' }}>
                    {repoData.items.length > 0 ? (
                        repoData.items.map((repo) => (
                            <a 
                                key={repo.html_url} 
                                href={repo.html_url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                style={{ textDecoration: 'none', color: 'inherit' }}
                            >
                                <div className="result-item" style={{ padding: '12px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', transition: 'all 0.2s' }}>
                                    <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: '4px' }}>{repo.full_name}</div>
                                    <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '8px', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{repo.description}</div>
                                    <div style={{ display: 'flex', gap: '12px', fontSize: '0.8rem', color: '#475569' }}>
                                        <span>⭐ {repo.stargazers_count}</span>
                                        {repo.language && <span>🔵 {repo.language}</span>}
                                    </div>
                                </div>
                            </a>
                        ))
                    ) : (
                        <p style={{ color: '#94a3b8', fontStyle: 'italic' }}>No repositories found.</p>
                    )}
                </div>
                <PaginationControls 
                    page={pages.repo} 
                    onPageChange={(newPage) => onPageChange('repo', newPage)} 
                    loading={loading}
                    hasNext={repoData.hasNext}
                />
            </div>

            {/* StackOverflow Questions */}
            <div className="bento-card">
                <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                    <FileText size={20} color="#f97316" />
                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Discussions</h3>
                </div>
                <div className="results-list" style={{ display: 'flex', flexDirection: 'column', gap: '12px', minHeight: '300px' }}>
                    {questionData.items.length > 0 ? (
                        questionData.items.map((q) => (
                            <a 
                                key={q.link} 
                                href={q.link} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                style={{ textDecoration: 'none', color: 'inherit' }}
                            >
                                <div className="result-item" style={{ padding: '12px', background: '#fff7ed', borderRadius: '8px', border: '1px solid #ffedd5', transition: 'all 0.2s' }}>
                                    <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: '4px', fontSize: '0.9rem' }} dangerouslySetInnerHTML={{ __html: q.title }}></div>
                                    <div style={{ display: 'flex', gap: '12px', fontSize: '0.8rem', color: '#475569' }}>
                                        <span style={{ color: q.is_answered ? '#10b981' : '#64748b' }}>{q.is_answered ? '✓ Answered' : '○ Open'}</span>
                                        <span>Score: {q.score}</span>
                                    </div>
                                </div>
                            </a>
                        ))
                    ) : (
                        <p style={{ color: '#94a3b8', fontStyle: 'italic' }}>No discussions found.</p>
                    )}
                </div>
                <PaginationControls 
                    page={pages.so} 
                    onPageChange={(newPage) => onPageChange('so', newPage)} 
                    loading={loading}
                    hasNext={questionData.hasNext}
                />
            </div>

            {/* Research Papers */}
            <div className="bento-card">
                <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                    <Book size={20} color="#8b5cf6" />
                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Research Papers</h3>
                </div>
                <div className="results-list" style={{ display: 'flex', flexDirection: 'column', gap: '12px', minHeight: '300px' }}>
                    {paperData.items.length > 0 ? (
                        paperData.items.map((paper, idx) => (
                            <div key={idx} className="result-item" style={{ padding: '12px', background: '#f5f3ff', borderRadius: '8px', border: '1px solid #ede9fe' }}>
                                <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: '4px', fontSize: '0.9rem' }}>{paper.title}</div>
                                <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '6px' }}>
                                    {paper.authors.join(', ')} ({paper.year})
                                </div>
                                <div style={{ fontSize: '0.85rem', color: '#475569', marginBottom: '8px', fontStyle: 'italic' }}>
                                    "{paper.abstract}"
                                </div>
                                <a href={paper.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '0.8rem', color: '#8b5cf6', display: 'flex', alignItems: 'center', gap: '4px', textDecoration: 'none' }}>
                                    Read Paper <ExternalLink size={12} />
                                </a>
                            </div>
                        ))
                    ) : (
                        <p style={{ color: '#94a3b8', fontStyle: 'italic' }}>No papers found.</p>
                    )}
                </div>
                <PaginationControls 
                    page={pages.paper} 
                    onPageChange={(newPage) => onPageChange('paper', newPage)} 
                    loading={loading}
                    hasNext={paperData.hasNext}
                />
            </div>

        </div>
    );
};

export default ProjectResults;
