import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';

const GraphView = ({ profile, recommendations, showRecommendations, metrics, prediction, style, focusedNodeId }) => {
    const containerRef = useRef(null);
    const cyRef = useRef(null);
    const [activeLayout, setActiveLayout] = useState('cose');
    const [hoverInfo, setHoverInfo] = useState(null);

    // 1. Initialize Graph Instance (Once)
    useEffect(() => {
        if (!containerRef.current) return;

        // Cleanup existing instance if any (safety check)
        if (cyRef.current) {
            try {
                if (!cyRef.current.destroyed()) {
                    cyRef.current.destroy();
                }
            } catch (e) {
                console.error("Error destroying old cy instance:", e);
            }
        }

        cyRef.current = cytoscape({
            container: containerRef.current,
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
                        'height': 'data(size)',
                        'border-width': 'data(border_width)',
                        'border-color': 'data(border_color)',
                        'text-wrap': 'wrap'
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 'data(width)',
                        'line-color': 'data(line_color)',
                        'target-arrow-color': 'data(line_color)',
                        'target-arrow-shape': 'triangle',
                        'target-arrow-size': 8, // Normal arrow size
                        'curve-style': 'bezier',
                        'line-style': 'data(line_style)',
                        'label': 'data(type)',
                        'font-size': '10px',
                        'color': '#64748b',
                        'text-rotation': 'autorotate',
                        'text-background-color': '#ffffff',
                        'text-background-opacity': 0.8
                    }
                }
            ]
        });

        // Event Listeners
        cyRef.current.on('tap', 'node', function(evt){
            const node = evt.target;
            const url = node.data('url');
            if(url){
                window.open(url, '_blank');
            }
        });

        // Hover Events
        cyRef.current.on('mouseover', 'node', (evt) => {
            const node = evt.target;
            const pos = node.renderedPosition();
            const data = node.data();
            setHoverInfo({
                x: pos.x,
                y: pos.y,
                label: data.label,
                type: data.type
            });
        });

        cyRef.current.on('mouseout', 'node', () => {
            setHoverInfo(null);
        });

        return () => {
            if (cyRef.current) {
                // IMPORTANT: Stop any animations/layouts before destroying
                // to prevent "Cannot read properties of null (reading 'notify')"
                try {
                    cyRef.current.stop(); 
                    if (!cyRef.current.destroyed()) {
                        cyRef.current.destroy();
                    }
                    cyRef.current = null;
                } catch (e) {
                    console.error("Error cleaning up cytoscape:", e);
                }
            }
        };
    }, []);

    // 2. Update Data (Nodes/Edges)
    useEffect(() => {
        if (!profile || !cyRef.current || cyRef.current.destroyed()) return;

        // Use requestAnimationFrame to ensure we don't update during a tear-down phase
        const rafId = requestAnimationFrame(() => {
            if (!cyRef.current || cyRef.current.destroyed()) return;

            const mainUserName = profile.github_stats.login || 'User';
            
            // Determine Community Highlighting using Louvain algorithm
            const communityMap = metrics?.community_map || {};
            const mainUserCommunity = metrics?.community_id;
            
            // Color palette for different communities (distinct colors)
            const communityColors = [
                '#3b82f6', // Blue
                '#ef4444', // Red
                '#10b981', // Green
                '#f59e0b', // Amber
                '#8b5cf6', // Purple
                '#ec4899', // Pink
                '#06b6d4', // Cyan
                '#84cc16', // Lime
                '#f97316', // Orange
                '#6366f1', // Indigo
            ];
            
            // Function to get community color
            const getCommunityColor = (communityId) => {
                if (communityId === undefined || communityId === -1) return null;
                return communityColors[communityId % communityColors.length];
            };

            const nodes = [];
            const edges = [];

            // 1. Central Node (Main User)
            const mainLabel = prediction ? `${mainUserName}\n(${prediction.predicted_role})` : mainUserName;
            
            // Get community color for main user
            const mainUserColor = getCommunityColor(mainUserCommunity) || '#3b82f6';
            
            nodes.push({
                data: { 
                    id: 'main', 
                    label: mainLabel, 
                    type: 'user', 
                    bg_color: mainUserColor, 
                    size: 60,
                    border_width: 4,
                    border_color: '#fbbf24' // Always highlight main user with yellow border
                }
            });

            // 4. Repository Nodes & Collaborators
            if (profile.repos) {
                profile.repos.forEach((repo) => {
                    const repoId = `repo_${repo.name}`;
                    nodes.push({
                        data: { id: repoId, label: repo.name, type: 'repo', bg_color: '#ec4899', size: 45, url: repo.url }
                    });
                    edges.push({
                        data: { 
                            source: 'main', 
                            target: repoId, 
                            type: 'owns', 
                            line_style: 'solid', 
                            line_color: '#ec4899', // Pink for repository edges
                            width: 2
                        }
                    });

                    // Add Owner Node if available (for owned repos)
                    if (repo.owner) {
                        const ownerName = repo.owner;
                        // If owner is the main user, use 'main' ID to unify nodes
                        const ownerId = ownerName === mainUserName ? 'main' : `user_${ownerName}`;
                        const backendOwnerId = `github:${ownerName}`;

                        // Only create owner node if NOT the main user (main already exists)
                        if (ownerName !== mainUserName && !nodes.find(n => n.data.id === ownerId)) {
                            // Get community color for owner
                            const ownerCommunityId = communityMap[backendOwnerId];
                            const ownerCommunityColor = getCommunityColor(ownerCommunityId);
                            const isSameCommunity = ownerCommunityId === mainUserCommunity && mainUserCommunity !== undefined;
                            
                            // Use community color if in same community, otherwise blue (same as collaborator)
                            let ownerColor = '#6366f1'; // Default blue (same as collaborator)
                            if (isSameCommunity && ownerCommunityColor) {
                                ownerColor = ownerCommunityColor;
                            }
                            
                            nodes.push({
                                data: { 
                                    id: ownerId, 
                                    label: isSameCommunity ? `${ownerName}\n(Community)` : ownerName, // Mark same community users
                                    type: 'repo_owner', 
                                    bg_color: ownerColor,
                                    size: 35, 
                                    url: `https://github.com/${ownerName}`,
                                    border_width: isSameCommunity ? 3 : 0, // Highlight same community with border
                                    border_color: isSameCommunity ? '#10b981' : 'transparent' // Green border for same community
                                }
                            });
                        }

                        // Edge: Owner -> Owns -> Repo (only if owner is different from main user)
                        if (ownerName !== mainUserName) {
                            const backendOwnerId = `github:${ownerName}`;
                            edges.push({
                                data: {
                                    id: `edge_${ownerId}_${repoId}`,
                                    source: ownerId,
                                    target: repoId,
                                    type: 'owns',
                                    line_style: 'solid',
                                    line_color: '#ec4899', // Pink for repository edges
                                    width: 2
                                }
                            });
                        }
                    }

                    if (profile.collaborators && profile.collaborators[repo.full_name]) {
                        profile.collaborators[repo.full_name].forEach((collabObj) => {
                            const collabName = typeof collabObj === 'string' ? collabObj : collabObj.login;
                            const collabUrl = typeof collabObj === 'string' ? null : collabObj.url;
                            // Use consistent ID format: user_${username} (same as owner nodes)
                            // This prevents duplicate nodes when someone is both collaborator and owner
                            const collabId = collabName === mainUserName ? 'main' : `user_${collabName}`;
                            
                            // Skip if this is the main user (already exists) or if node already exists
                            if (collabName === mainUserName || nodes.find(n => n.data.id === collabId)) {
                                // Just add the edge if node already exists
                                edges.push({
                                    data: { 
                                        id: `edge_${collabId}_${repoId}`,
                                        source: collabId, 
                                        target: repoId, 
                                        type: 'contributes', 
                                        line_style: 'dashed',
                                        line_color: '#3b82f6', // Blue for collaborator edges
                                        width: 2
                                    }
                                });
                                return; // Skip node creation
                            }
                            
                            // Check if this person is also an owner of any repo (to determine color)
                            const isOwner = profile.repos?.some(r => r.owner === collabName) || 
                                          profile.collaborations?.some(r => r.owner === collabName);
                            
                            // Get community color for this user
                            const backendId = `github:${collabName}`;
                            const userCommunityId = communityMap[backendId];
                            const communityColor = getCommunityColor(userCommunityId);
                            const isSameCommunity = userCommunityId === mainUserCommunity && mainUserCommunity !== undefined;
                            
                            // Base color: Blue for both owner and collaborator
                            let baseColor = '#6366f1';
                            // If in same community as main user, use community color
                            if (isSameCommunity && communityColor) {
                                baseColor = communityColor;
                            }
                            
                            nodes.push({
                                data: { 
                                    id: collabId, 
                                    label: isSameCommunity ? `${collabName}\n(Community)` : collabName, // Mark same community users
                                    type: isOwner ? 'repo_owner' : 'collaborator', 
                                    bg_color: baseColor,
                                    size: 35, 
                                    url: collabUrl,
                                    border_width: isSameCommunity ? 3 : 0, // Highlight same community with border
                                    border_color: isSameCommunity ? '#10b981' : 'transparent' // Green border for same community
                                }
                            });
                            
                            edges.push({
                                data: { 
                                    id: `edge_${collabId}_${repoId}`, // Explicit unique ID
                                    source: collabId, 
                                    target: repoId, 
                                    type: 'contributes', 
                                    line_style: 'dashed',
                                    line_color: '#3b82f6', // Blue for collaborator edges (same for all)
                                    width: 2
                                }
                            });
                        });
                    }
                    
                    // IMPORTANT: Also show the owner connection even if owner is not in collaborators list
                    // This ensures we see: repo → owner connection when viewing a collaborator's profile
                    if (repo.owner && repo.owner !== mainUserName) {
                        const ownerName = repo.owner;
                        const ownerId = `user_${ownerName}`;
                        const backendOwnerId = `github:${ownerName}`;
                        const ownerCommunityId = communityMap[backendOwnerId];
                        const ownerCommunityColor = getCommunityColor(ownerCommunityId);
                        const isSameCommunity = ownerCommunityId === mainUserCommunity && mainUserCommunity !== undefined;
                        
                        // Use community color if in same community, otherwise blue (same as collaborator)
                        let ownerColor = '#6366f1'; // Default blue (same as collaborator)
                        if (isSameCommunity && ownerCommunityColor) {
                            ownerColor = ownerCommunityColor;
                        }
                        
                        // Check if owner node already exists (might have been added earlier or as collaborator)
                        if (!nodes.find(n => n.data.id === ownerId)) {
                            nodes.push({
                                data: { 
                                    id: ownerId, 
                                    label: isSameCommunity ? `${ownerName}\n(Community)` : ownerName, // Mark same community users
                                    type: 'repo_owner', 
                                    bg_color: ownerColor,
                                    size: 35, 
                                    url: `https://github.com/${ownerName}`,
                                    border_width: isSameCommunity ? 3 : 0, // Highlight same community with border
                                    border_color: isSameCommunity ? '#10b981' : 'transparent' // Green border for same community
                                }
                            });
                        }
                        
                        // Add owner → repo connection if it doesn't exist
                        const ownerEdgeId = `edge_${ownerId}_${repoId}`;
                        if (!edges.find(e => e.data.id === ownerEdgeId)) {
                            edges.push({
                                data: {
                                    id: ownerEdgeId,
                                    source: ownerId,
                                    target: repoId,
                                    type: 'owns',
                                    line_style: 'solid',
                                    line_color: '#ec4899', // Pink for repository edges
                                    width: 2
                                }
                            });
                        }
                    }
                });
            }

            // 4b. Collaboration Repositories (Repos the user contributed to)
            if (profile.collaborations) {
                profile.collaborations.forEach((repo) => {
                    const repoId = `repo_${repo.name}`;
                    
                    // Avoid duplicate nodes if repo is already in owned list
                    if (nodes.find(n => n.data.id === repoId)) return;

                    nodes.push({
                        data: { 
                            id: repoId, 
                            label: repo.name, 
                            type: 'collaboration_repo', // Distinct type
                            bg_color: '#a855f7', // Purple-ish for external collaborations
                            size: 40, 
                            url: repo.url 
                        }
                    });
                    
                    // Edge: Main User -> Contributed To -> Repo
                    edges.push({
                        data: { 
                            id: `edge_main_${repoId}`, // Explicit ID
                            source: 'main', 
                            target: repoId, 
                            type: repo.owner === mainUserName ? 'owns' : 'contributed_to', // Distinguish ownership
                            line_style: 'solid', 
                            line_color: '#ec4899' // Pink for repository edges
                        }
                    });

                    // NEW: Add Owner Node if available
                    if (repo.owner) {
                        const ownerName = repo.owner;
                        // CRITICAL: If owner is the main user, use 'main' ID to unify nodes
                        const ownerId = ownerName === mainUserName ? 'main' : `user_${ownerName}`;
                        const backendOwnerId = `github:${ownerName}`;
                        
                        // Treat owner as a collaborator type node for visuals, or distinct 'owner' type
                        const isSameCommunity = mainUserCommunity !== undefined && communityMap[backendOwnerId] === mainUserCommunity;

                        // Only create owner node if NOT the main user (main already exists)
                        if (ownerName !== mainUserName && !nodes.find(n => n.data.id === ownerId)) {
                             nodes.push({
                                data: { 
                                    id: ownerId, 
                                    label: ownerName, 
                                    type: 'repo_owner', 
                                    bg_color: '#6366f1', // Blue (same as collaborator)
                                    size: 35, 
                                    url: `https://github.com/${ownerName}`,
                                    border_width: 0, // Remove yellow/black borders
                                    border_color: 'transparent'
                                }
                            });
                        }

                        // Edge: Owner -> Owns -> Repo
                        if (ownerName !== mainUserName) {
                            edges.push({
                                data: {
                                    id: `edge_${ownerId}_${repoId}`,
                                    source: ownerId,
                                    target: repoId,
                                    type: 'owns',
                                    line_style: 'solid',
                                    line_color: '#ec4899', // Pink for repository edges
                                    width: 2
                                }
                            });
                        }
                    }

                    // Add other collaborators for these repos too
                    if (profile.collaborators && profile.collaborators[repo.full_name]) {
                        profile.collaborators[repo.full_name].forEach((collabObj) => {
                            const collabName = typeof collabObj === 'string' ? collabObj : collabObj.login;
                            const collabUrl = typeof collabObj === 'string' ? null : collabObj.url;
                            // CRITICAL: Use consistent ID format: user_${username}
                            const collabId = collabName === mainUserName ? 'main' : `user_${collabName}`;
                            
                            // Skip if this is the main user or if node already exists
                            if (collabName === mainUserName || nodes.find(n => n.data.id === collabId)) {
                                // Just add the edge if node already exists
                                edges.push({
                                    data: { 
                                        id: `edge_${collabId}_${repoId}`,
                                        source: collabId, 
                                        target: repoId, 
                                        type: 'contributes', 
                                        line_style: 'dashed', 
                                        line_color: '#3b82f6' // Blue for collaborator edges 
                                    }
                                });
                                return; // Skip node creation
                            }
                            
                            // Check if this person is also an owner of any repo
                            const isOwner = profile.repos?.some(r => r.owner === collabName) || 
                                          profile.collaborations?.some(r => r.owner === collabName);
                            
                            // Get community color for this user
                            const backendId = `github:${collabName}`;
                            const userCommunityId = communityMap[backendId];
                            const communityColor = getCommunityColor(userCommunityId);
                            const isSameCommunity = userCommunityId === mainUserCommunity && mainUserCommunity !== undefined;
                            
                            // Base color: Blue for both owner and collaborator
                            let baseColor = '#6366f1';
                            // If in same community as main user, use community color
                            if (isSameCommunity && communityColor) {
                                baseColor = communityColor;
                            }
                            
                            nodes.push({
                                data: { 
                                    id: collabId, 
                                    label: isSameCommunity ? `${collabName}\n(Community)` : collabName, // Mark same community users
                                    type: isOwner ? 'repo_owner' : 'collaborator', 
                                    bg_color: baseColor,
                                    size: 35, 
                                    url: collabUrl,
                                    border_width: isSameCommunity ? 3 : 0, // Highlight same community with border
                                    border_color: isSameCommunity ? '#10b981' : 'transparent' // Green border for same community
                                }
                            });
                            
                            // Edge: Collaborator -> Contributes -> Repo
                            edges.push({
                                data: { 
                                    id: `edge_${collabId}_${repoId}`, // Explicit unique ID: collab + repo pairing
                                    source: collabId, 
                                    target: repoId, 
                                    type: 'contributes', 
                                    line_style: 'dashed',
                                    line_color: '#3b82f6', // Blue for collaborator edges (same for all)
                                    width: 2
                                }
                            });
                        });
                    }
                    
                    // IMPORTANT: Also show the owner connection even if owner is not in collaborators list
                    // This ensures we see: repo → owner connection when viewing a collaborator's profile
                    if (repo.owner && repo.owner !== mainUserName) {
                        const ownerName = repo.owner;
                        const ownerId = `user_${ownerName}`;
                        const backendOwnerId = `github:${ownerName}`;
                        
                        // Check if owner node already exists (might have been added as collaborator)
                        const existingNode = nodes.find(n => n.data.id === ownerId);
                        
                        // Get community color for owner
                        const ownerCommunityId = communityMap[backendOwnerId];
                        const ownerCommunityColor = getCommunityColor(ownerCommunityId);
                        const isSameCommunity = ownerCommunityId === mainUserCommunity && mainUserCommunity !== undefined;
                        
                        // Use community color if in same community, otherwise blue (same as collaborator)
                        let ownerColor = '#6366f1'; // Default blue (same as collaborator)
                        if (isSameCommunity && ownerCommunityColor) {
                            ownerColor = ownerCommunityColor;
                        }
                        
                        if (!existingNode) {
                            // Create new owner node
                            nodes.push({
                                data: { 
                                    id: ownerId, 
                                    label: isSameCommunity ? `${ownerName}\n(Community)` : ownerName, // Mark same community users
                                    type: 'repo_owner', 
                                    bg_color: ownerColor,
                                    size: 35, 
                                    url: `https://github.com/${ownerName}`,
                                    border_width: isSameCommunity ? 3 : 0, // Highlight same community with border
                                    border_color: isSameCommunity ? '#10b981' : 'transparent' // Green border for same community
                                }
                            });
                        } else {
                            // Update existing node to show it's also an owner
                            existingNode.data.type = 'repo_owner';
                            existingNode.data.bg_color = ownerColor;
                            // Update label if same community
                            if (isSameCommunity) {
                                existingNode.data.label = `${ownerName}\n(Community)`;
                            }
                            existingNode.data.border_width = isSameCommunity ? 3 : 0;
                            existingNode.data.border_color = isSameCommunity ? '#10b981' : 'transparent';
                        }
                        
                        // Add owner → repo connection if it doesn't exist
                        const ownerEdgeId = `edge_${ownerId}_${repoId}`;
                        if (!edges.find(e => e.data.id === ownerEdgeId)) {
                            edges.push({
                                data: {
                                    id: ownerEdgeId,
                                    source: ownerId,
                                    target: repoId,
                                    type: 'owns',
                                    line_style: 'solid',
                                    line_color: '#ec4899', // Pink for repository edges
                                    width: 2
                                }
                            });
                        }
                    }
                });
            }

            // 5. StackOverflow Nodes
            if (profile.so_stats && profile.so_stats.reputation) {
                const soId = 'so_profile';
                nodes.push({
                    data: { 
                        id: soId, 
                        label: 'StackOverflow', 
                        type: 'so_user', 
                        bg_color: '#f97316', 
                        size: 50,
                        url: profile.so_stats.link // Add link here 
                    }
                });
                edges.push({
                    data: { 
                        source: 'main', 
                        target: soId, 
                        type: 'has_profile', 
                        line_style: 'solid', 
                        line_color: '#f97316', // Orange color
                        width: 2 // Thinner line
                    }
                });
                if (profile.top_so_tags) {
                    profile.top_so_tags.forEach(([tag, score]) => {
                        const tagId = `tag_${tag}`;
                        nodes.push({
                            data: { id: tagId, label: tag, type: 'tag', bg_color: '#fbbf24', size: 30 }
                        });
                        edges.push({
                            data: { 
                                source: soId, 
                                target: tagId, 
                                type: 'has_tag', 
                                line_style: 'dashed', 
                                line_color: '#f97316', // Orange color
                                width: 2 // Thinner line
                            }
                        });
                    });
                }
            }

            // Update Cytoscape Elements safely
            try {
                 cyRef.current.elements().remove();
                 cyRef.current.add([...nodes, ...edges]);
            } catch(e) {
                 console.warn("Error updating graph elements:", e);
            }

            // Run Layout (Initial layout for new data)
            try {
                // Stop any previous layout/animation first
                cyRef.current.stop();
                
                const layout = cyRef.current.layout({
                    name: activeLayout,
                    animate: false, // Disable animation on data load to prevent crash
                    fit: true,
                    padding: 30,
                    nodeOverlap: 20,
                    componentSpacing: 100,
                    nodeRepulsion: 400000,
                    edgeElasticity: 100,
                    nestingFactor: 5,
                });
                layout.run();
            } catch(e) { console.warn("Layout run failed", e); }
        });
        
        return () => cancelAnimationFrame(rafId);

    }, [profile, recommendations, showRecommendations, metrics, prediction, activeLayout]); 

    // 3. Handle Layout Updates Only
    useEffect(() => {
        if (!cyRef.current || cyRef.current.destroyed()) return;

        try {
            const layout = cyRef.current.layout({
                name: activeLayout,
                animate: true,
                animationDuration: 500,
                idealEdgeLength: 100,
                nodeOverlap: 20,
                refresh: 20,
                fit: true,
                padding: 30,
                componentSpacing: 100,
                nodeRepulsion: 400000,
                edgeElasticity: 100,
                nestingFactor: 5,
            });
            layout.run();
        } catch (e) {
            console.warn("Layout update failed:", e);
        }
    }, [activeLayout]);

    // 4. Handle External Focus (e.g. from Recommendation Click)
    useEffect(() => {
        if (!cyRef.current || cyRef.current.destroyed() || !focusedNodeId) return;

        try {
            const node = cyRef.current.getElementById(focusedNodeId);
            
            if (node.length > 0) {
                // Remove previous selection/lighting
                cyRef.current.elements().removeClass('highlighted');
                cyRef.current.nodes().unselect();

                // Select and animate to new node
                node.select();
                node.addClass('highlighted');

                cyRef.current.animate({
                    fit: {
                        eles: node,
                        padding: 50
                    },
                    duration: 500
                });
            }
        } catch (e) {
            console.warn("Focus animation failed:", e);
        }
    }, [focusedNodeId]);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', position: 'relative', minHeight: '500px', ...style }}>
            <div className="graph-controls" style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '8px' }}>
                <span style={{ fontSize: '0.9rem', color: '#64748b' }}>Graph Layout:</span>
                <select 
                    value={activeLayout} 
                    onChange={(e) => setActiveLayout(e.target.value)}
                    style={{
                        padding: '6px 12px',
                        borderRadius: '6px',
                        border: '1px solid #cbd5e1',
                        fontSize: '0.9rem',
                        cursor: 'pointer',
                        backgroundColor: '#ffffff',
                        color: '#000000'
                    }}
                >
                    <option value="cose">Force Directed</option>
                    <option value="circle">Circle</option>
                    <option value="grid">Grid</option>
                    <option value="concentric">Concentric</option>
                    <option value="breadthfirst">Breadthfirst (Tree)</option>
                    <option value="random">Random</option>
                </select>
            </div>
            
            <div className="graph-container" style={{ flex: 1, border: '1px solid #eee', borderRadius: '8px', overflow: 'hidden', position: 'relative' }}>
                <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
                
                {/* Node Type Legend */}
                <div 
                    style={{
                        position: 'absolute',
                        top: '10px',
                        left: '10px',
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        padding: '10px 12px',
                        borderRadius: '6px',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                        border: '1px solid #e2e8f0',
                        zIndex: 10,
                        fontSize: '0.85rem',
                        minWidth: '200px'
                    }}
                >
                    <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: '8px', fontSize: '0.9rem' }}>
                        Node Types
                    </div>
                    
                    {/* Main User */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                        <div 
                            style={{ 
                                width: '20px', 
                                height: '20px', 
                                borderRadius: '50%', 
                                backgroundColor: '#3b82f6',
                                border: '3px solid #fbbf24',
                                flexShrink: 0
                            }} 
                        />
                        <span style={{ color: '#64748b', fontSize: '0.8rem' }}>
                            Main User
                        </span>
                    </div>
                    
                    {/* Repository */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                        <div 
                            style={{ 
                                width: '18px', 
                                height: '18px', 
                                borderRadius: '50%', 
                                backgroundColor: '#ec4899',
                                flexShrink: 0
                            }} 
                        />
                        <span style={{ color: '#64748b', fontSize: '0.8rem' }}>
                            Repository
                        </span>
                    </div>
                    
                    {/* Collaborator */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                        <div 
                            style={{ 
                                width: '14px', 
                                height: '14px', 
                                borderRadius: '50%', 
                                backgroundColor: '#6366f1',
                                flexShrink: 0
                            }} 
                        />
                        <span style={{ color: '#64748b', fontSize: '0.8rem' }}>
                            Collaborator
                        </span>
                    </div>
                </div>
                
                {/* Hover Popup */}
                {hoverInfo && (
                    <div 
                        style={{
                            position: 'absolute',
                            left: hoverInfo.x + 15,
                            top: hoverInfo.y - 15,
                            backgroundColor: 'rgba(255, 255, 255, 0.95)',
                            padding: '8px 12px',
                            borderRadius: '6px',
                            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                            border: '1px solid #e2e8f0',
                            zIndex: 10,
                            pointerEvents: 'none', // Prevent interference with mouse
                            fontSize: '0.85rem',
                            minWidth: '120px'
                        }}
                    >
                        <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: '2px' }}>{hoverInfo.label}</div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'capitalize' }}>Type: {hoverInfo.type.replace('_', ' ')}</div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default GraphView;
