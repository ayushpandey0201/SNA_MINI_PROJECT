import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';

const GraphView = ({ profile, recommendations, showRecommendations }) => {
    const containerRef = useRef(null);
    const cyRef = useRef(null);

    useEffect(() => {
        if (!profile || !containerRef.current) return;

        const mainUserId = profile.node_ids.github_user_id || 'user';
        const mainUserName = profile.github_stats.login || 'User';

        const nodes = [];
        const edges = [];

        // 1. Central Node
        nodes.push({
            data: { id: 'main', label: mainUserName, type: 'user', bg_color: '#3b82f6', size: 60 }
        });

        // 2. Language Nodes
        profile.top_repo_languages.slice(0, 5).forEach(([lang, count]) => {
            const langId = `lang_${lang}`;
            nodes.push({
                data: { id: langId, label: lang, type: 'language', bg_color: '#10b981', size: 40 }
            });
            edges.push({
                data: { source: 'main', target: langId, type: 'uses', line_style: 'solid', line_color: '#cbd5e1' }
            });
        });

        // 3. Topic Nodes
        profile.top_topics.slice(0, 5).forEach((topic) => {
            const topicId = `topic_${topic}`;
            nodes.push({
                data: { id: topicId, label: topic, type: 'topic', bg_color: '#8b5cf6', size: 30 }
            });
            edges.push({
                data: { source: 'main', target: topicId, type: 'interested_in', line_style: 'solid', line_color: '#cbd5e1' }
            });
        });

        // 4. Recommendations
        if (showRecommendations && recommendations) {
            recommendations.forEach((rec) => {
                const recId = rec.node_id;
                const label = rec.node_id.split(':')[1] || rec.node_id;

                nodes.push({
                    data: { id: recId, label: label, type: 'recommendation', score: rec.score, bg_color: '#f59e0b', size: 50 }
                });

                edges.push({
                    data: { source: 'main', target: recId, type: 'recommended', line_style: 'dashed', line_color: '#f59e0b' }
                });
            });
        }

        // Initialize or Update Cytoscape
        if (cyRef.current) {
            cyRef.current.destroy();
        }

        cyRef.current = cytoscape({
            container: containerRef.current,
            elements: { nodes, edges },
            layout: {
                name: 'cose',
                animate: false, // Disable animation to prevent errors during unmount
                idealEdgeLength: 100,
                nodeOverlap: 20,
                refresh: 20,
                fit: true,
                padding: 30,
                componentSpacing: 100,
                nodeRepulsion: 400000,
                edgeElasticity: 100,
                nestingFactor: 5,
            },
            style: [
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'color': '#fff',
                        'text-outline-width': 2,
                        'text-outline-color': '#333',
                        'font-size': '12px',
                        'background-color': 'data(bg_color)',
                        'width': 'data(size)',
                        'height': 'data(size)'
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': 'data(line_color)',
                        'target-arrow-color': 'data(line_color)',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'line-style': 'data(line_style)'
                    }
                }
            ]
        });

        // Cleanup
        return () => {
            if (cyRef.current) {
                cyRef.current.destroy();
                cyRef.current = null;
            }
        };

    }, [profile, recommendations, showRecommendations]);

    return (
        <div className="graph-container" style={{ height: '500px', border: '1px solid #eee', borderRadius: '8px', overflow: 'hidden' }}>
            <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
        </div>
    );
};

export default GraphView;
