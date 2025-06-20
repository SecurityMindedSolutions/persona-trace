from lib.constants import logger, NODE_COLORS, RELATIONSHIP_COLORS_OPTIONS


def make_fake_graph_data(search_type, search_value, search_operator, node_type, num_hops, num_connections_show_all_overlaps, show_nodes_only_search):
    # Create fake node and relationship color assignments for consistency
    fake_node_colors = {
        'source': NODE_COLORS['source'],
        'observation_of_identity': NODE_COLORS['observation_of_identity'],
        'email_address': NODE_COLORS['node_color_options'][0],
        'ip_address': NODE_COLORS['node_color_options'][1], 
        'phone_number': NODE_COLORS['node_color_options'][2],
        'address': NODE_COLORS['node_color_options'][3],
        'name': NODE_COLORS['node_color_options'][4]
    }
    
    fake_relationship_colors = {
        'has_observation': RELATIONSHIP_COLORS_OPTIONS[5],
        'has_email': RELATIONSHIP_COLORS_OPTIONS[0],
        'has_ip': RELATIONSHIP_COLORS_OPTIONS[1],
        'has_phone': RELATIONSHIP_COLORS_OPTIONS[2], 
        'has_address': RELATIONSHIP_COLORS_OPTIONS[3],
        'has_name': RELATIONSHIP_COLORS_OPTIONS[4]
    }
    
    # Define the complete fake dataset
    all_nodes = [
        # Source nodes (observations)
        {
            'id': 'obs1',
            'label': 'Social Media Post 1',
            'group': 'source',
            'properties': {
                'source': 'social_media_platform',
                'observation_date': '2024-03-15'
            },
            'num_observations': 1
        },
        {
            'id': 'obs2',
            'label': 'Data Breach 1',
            'group': 'source',
            'properties': {
                'source': 'data_breach',
                'observation_date': '2024-03-10'
            },
            'num_observations': 1
        },
        {
            'id': 'obs3',
            'label': 'Forum Post 1',
            'group': 'source',
            'properties': {
                'source': 'forum_data',
                'observation_date': '2024-03-12'
            },
            'num_observations': 1
        },
        # Observation nodes
        {
            'id': 'obs_id1',
            'label': 'John Smith (obs1)',
            'group': 'observation_of_identity',
            'properties': {
                'names': ['John Smith'],
                'date_of_birth': '1985-03-22',
                'age': 39,
                'city': 'Portland',
                'state': 'OR'
            },
            'num_observations': 1
        },
        {
            'id': 'obs_id2',
            'label': 'John Smith (obs2)',
            'group': 'observation_of_identity',
            'properties': {
                'names': ['John Smith'],
                'date_of_birth': '1985-03-22',
                'age': 39,
                'city': 'Seattle',
                'state': 'WA'
            },
            'num_observations': 1
        },
        {
            'id': 'obs_id3',
            'label': 'Sarah Jones (obs3)',
            'group': 'observation_of_identity',
            'properties': {
                'names': ['Sarah Jones'],
                'date_of_birth': '1988-06-15',
                'age': 36,
                'city': 'Portland',
                'state': 'OR'
            },
            'num_observations': 1
        },
        # Identity nodes (with some overlaps)
        {
            'id': 'email1',
            'label': 'john.smith@email.com',
            'group': 'email_address',
            'properties': {'category': 'personal'},
            'num_observations': 2  # Used in both obs1 and obs2
        },
        {
            'id': 'email2',
            'label': 'sarah.jones@email.com',
            'group': 'email_address',
            'properties': {'category': 'personal'},
            'num_observations': 1
        },
        {
            'id': 'ip1',
            'label': '192.168.1.100',
            'group': 'ip_address',
            'properties': {'category': 'home'},
            'num_observations': 2  # Used in both obs1 and obs3
        },
        {
            'id': 'phone1',
            'label': '+15035551234',
            'group': 'phone_number',
            'properties': {'category': 'mobile'},
            'num_observations': 1
        },
        {
            'id': 'addr1',
            'label': '123 Main St, Portland, OR',
            'group': 'address',
            'properties': {'category': 'home'},
            'num_observations': 2  # Used in both obs1 and obs3
        },
        {
            'id': 'name1',
            'label': 'John Smith',
            'group': 'name',
            'properties': {},
            'num_observations': 2  # Used in both obs1 and obs2
        },
        {
            'id': 'name2',
            'label': 'Sarah Jones',
            'group': 'name',
            'properties': {},
            'num_observations': 1
        }
    ]
    
    all_relationships = [
        # Source to observation connections
        {'id': 'e1', 'from': 'obs1', 'to': 'obs_id1', 'label': 'has_observation'},
        {'id': 'e2', 'from': 'obs2', 'to': 'obs_id2', 'label': 'has_observation'},
        {'id': 'e3', 'from': 'obs3', 'to': 'obs_id3', 'label': 'has_observation'},
        # Observation to identity connections
        {'id': 'e4', 'from': 'obs_id1', 'to': 'email1', 'label': 'has_email'},
        {'id': 'e5', 'from': 'obs_id1', 'to': 'ip1', 'label': 'has_ip'},
        {'id': 'e6', 'from': 'obs_id1', 'to': 'phone1', 'label': 'has_phone'},
        {'id': 'e7', 'from': 'obs_id1', 'to': 'addr1', 'label': 'has_address'},
        {'id': 'e8', 'from': 'obs_id1', 'to': 'name1', 'label': 'has_name'},
        {'id': 'e9', 'from': 'obs_id2', 'to': 'email1', 'label': 'has_email'},
        {'id': 'e10', 'from': 'obs_id2', 'to': 'name1', 'label': 'has_name'},
        {'id': 'e11', 'from': 'obs_id3', 'to': 'email2', 'label': 'has_email'},
        {'id': 'e12', 'from': 'obs_id3', 'to': 'ip1', 'label': 'has_ip'},
        {'id': 'e13', 'from': 'obs_id3', 'to': 'addr1', 'label': 'has_address'},
        {'id': 'e14', 'from': 'obs_id3', 'to': 'name2', 'label': 'has_name'}
    ]
    
    # If no search parameters, return all data
    if not search_type:
        return {
            'nodes': all_nodes,
            'relationships': all_relationships,
            'metadata': {
                'nodeCount': len(all_nodes),
                'relationshipCount': len(all_relationships),
                'nodeColors': fake_node_colors,
                'relationshipColors': fake_relationship_colors
            }
        }
    
    # Filter nodes based on search parameters
    filtered_nodes = []
    if search_type == 'nodeValue':
        # Find nodes that match the search criteria
        for node in all_nodes:
            if node['group'] == node_type or not node_type:
                node_value = node.get('label', '')
                if search_operator == 'equals' and node_value.lower() == search_value.lower():
                    filtered_nodes.append(node)
                elif search_operator == 'contains' and search_value.lower() in node_value.lower():
                    filtered_nodes.append(node)
    
    elif search_type == 'showAllOverlaps':
        # Find nodes with multiple observations
        for node in all_nodes:
            if node['num_observations'] >= num_connections_show_all_overlaps:
                filtered_nodes.append(node)
    
    # Debug logging
    logger.info(f"Search parameters: type={search_type}, value={search_value}, operator={search_operator}, node_type={node_type}")
    logger.info(f"Filtered nodes found: {len(filtered_nodes)}")
    for v in filtered_nodes:
        logger.info(f"  - {v['id']} ({v['group']}): {v['label']}")
    
    # If no matching nodes found, return empty result
    if not filtered_nodes:
        return {
            'nodes': [],
            'relationships': [],
            'metadata': {
                'nodeCount': 0,
                'relationshipCount': 0,
                'nodeColors': fake_node_colors,
                'relationshipColors': fake_relationship_colors
            }
        }
    
    # Get nodes within num_hops of the filtered nodes
    included_nodes = set()
    included_relationships = []
    
    # Add the filtered nodes
    for node in filtered_nodes:
        included_nodes.add(node['id'])
    
    logger.info(f"Starting with {len(included_nodes)} filtered nodes: {included_nodes}")
    
    # If show_nodes_only_search is True, only return the filtered nodes
    if show_nodes_only_search:
        logger.info("Show nodes only search is enabled - only returning filtered nodes")
        final_nodes = filtered_nodes
        final_relationships = []
    else:
        # Add nodes within num_hops
        for hop in range(num_hops):
            new_nodes = set()
            for relationship in all_relationships:
                from_id = relationship['from']
                to_id = relationship['to']
                
                # If one end is included, add the other end and the relationship
                if from_id in included_nodes and to_id not in included_nodes:
                    new_nodes.add(to_id)
                    included_relationships.append(relationship)
                elif to_id in included_nodes and from_id not in included_nodes:
                    new_nodes.add(from_id)
                    included_relationships.append(relationship)
                elif from_id in included_nodes and to_id in included_nodes:
                    # Both nodes are included, add relationship if not already added
                    if relationship not in included_relationships:
                        included_relationships.append(relationship)
            
            included_nodes.update(new_nodes)
            logger.info(f"After hop {hop + 1}: {len(included_nodes)} nodes, {len(included_relationships)} relationships")
        
        # Special handling: Always include source nodes that are connected to any included observation nodes
        # This ensures that when we find identity nodes, we also show their source observations
        source_nodes = set()
        for node in all_nodes:
            if node['group'] == 'source':
                # Check if this source is connected to any included observation nodes
                for relationship in all_relationships:
                    if relationship['label'] == 'has_observation':
                        # In fake data: source -> observation (from: source, to: observation)
                        if relationship['from'] == node['id'] and relationship['to'] in included_nodes:
                            source_nodes.add(node['id'])
                            # Add the relationship connecting source to observation
                            if relationship not in included_relationships:
                                included_relationships.append(relationship)
                                logger.info(f"Added source node {node['id']} connected to observation {relationship['to']}")
                        # Also check reverse direction in case relationship direction is different
                        elif relationship['to'] == node['id'] and relationship['from'] in included_nodes:
                            source_nodes.add(node['id'])
                            # Add the relationship connecting observation to source
                            if relationship not in included_relationships:
                                included_relationships.append(relationship)
                                logger.info(f"Added source node {node['id']} connected from observation {relationship['from']}")
        
        logger.info(f"Found {len(source_nodes)} source nodes to include: {source_nodes}")
        
        # Add source nodes to included set
        included_nodes.update(source_nodes)
        
        # Get the final nodes and relationships
        final_nodes = [v for v in all_nodes if v['id'] in included_nodes]
        final_relationships = included_relationships
    
    # Recalculate num_observations for nodes based on actual connections in the final result
    # Only do this when not in show_nodes_only_search mode
    if not show_nodes_only_search:
        for node in final_nodes:
            if node['group'] not in ['source', 'observation_of_identity']:
                # Count how many observation nodes are connected to this node in the final result
                observation_count = 0
                for relationship in final_relationships:
                    if relationship['label'].startswith('has_') and relationship['to'] == node['id']:
                        # Check if the 'from' node is an observation
                        from_node = next((v for v in final_nodes if v['id'] == relationship['from']), None)
                        if from_node and from_node['group'] == 'observation_of_identity':
                            observation_count += 1
                
                # Update the node with the correct observation count
                node['num_observations'] = observation_count
                node['is_shared'] = observation_count > 1
                
                # Update the label to include observation count if multiple observations
                if observation_count > 1:
                    # Remove any existing observation count from the label
                    import re
                    base_label = re.sub(r'(\n| )?\(\d+ obs\)', '', node['label'])
                    node['label'] = f"{base_label}\n({observation_count} obs)"
    
    # Apply bolded colors to initial search nodes
    for node in final_nodes:
        # Check if this is an initial search node (is in the filtered_nodes list)
        is_initial_search_node = any(filtered_node['id'] == node['id'] for filtered_node in filtered_nodes)

        # Apply bolded color for initial search nodes
        if is_initial_search_node:
            node['color'] = {
                'background': '#FFD700',  # Gold background
                'border': '#FF4500'       # OrangeRed border
            }
            node['borderWidth'] = 4  # Larger border width for initial search nodes
        else:
            # Use normal color from fake_node_colors
            node['color'] = fake_node_colors.get(node['group'], {
                'background': '#D3D3D3',
                'border': '#808080'
            })
            node['borderWidth'] = 1  # Default border width
    
    logger.info(f"Final result: {len(final_nodes)} nodes, {len(final_relationships)} relationships")
    logger.info(f"Final nodes: {[v['id'] for v in final_nodes]}")
    
    return {
        'nodes': final_nodes,
        'relationships': final_relationships,
        'metadata': {
            'nodeCount': len(final_nodes),
            'relationshipCount': len(final_relationships),
            'relationshipColors': fake_relationship_colors
        }
    }