from flask import Blueprint, render_template, current_app, jsonify, request
from neo4j import GraphDatabase
import random

import logging
from lib.constants import NODE_COLORS, RELATIONSHIP_COLORS_OPTIONS, logger, FIND_PATHS_MAX_DEPTH
from lib.neo4j_connection import get_neo4j_connection
import json

# Blueprint for the graph page
graph_bp = Blueprint('graph', __name__)

# Global dictionaries to maintain consistent color assignments across requests
NODE_COLOR_ASSIGNMENTS = {}
RELATIONSHIP_COLOR_ASSIGNMENTS = {}


@graph_bp.route('/')
def index():
    logger.info("Rendering graph visualization page...")
    fake_data = request.args.get('fake_data', 'false').lower() == 'true'
    return render_template('graph/index.html', fake_data=fake_data)


@graph_bp.route('/api/graph-data')
def api_graph_data():
    logger.info("API request received for graph data...")
    try:
        # Get search parameters from the request
        search_type = request.args.get('searchType')
        # Node value search
        show_overlaps = request.args.get('showOverlaps') == "true"
        node_type = request.args.get('nodeType')
        search_operator = request.args.get('searchOperator', 'equals')
        search_value = request.args.get('searchValue')
        num_hops_node_search = request.args.get('numHopsNodeSearch', '2')
        show_nodes_only_search = request.args.get('showNodesOnlySearch', 'false').lower() == 'true'
        search_source_select = request.args.get('searchSourceSelect', '')
        case_sensitive_search = request.args.get('caseSensitiveSearch', 'false').lower() == 'true'
        # Show all overlaps
        num_connections_show_all_overlaps = request.args.get('numConnectionsShowAllOverlaps', '2')
        num_hops_show_all_overlaps = request.args.get('numHopsShowAllOverlaps', '2')
        # Fake data parameter
        fake_data = request.args.get('fake_data', 'false').lower() == 'true'
        print(f"Fake data: {fake_data}")

        # If fake_data is true, return fake data
        if fake_data:
            logger.info("Returning fake data...")
            
            # Convert num_hops to integer with default value of 2
            try:
                num_hops_node_search = int(num_hops_node_search) if num_hops_node_search else 2
            except (ValueError, TypeError):
                num_hops_node_search = 2
            try:
                num_connections_show_all_overlaps = int(num_connections_show_all_overlaps) if num_connections_show_all_overlaps else 2
            except (ValueError, TypeError):
                num_connections_show_all_overlaps = 2
            try:
                num_hops_show_all_overlaps = int(num_hops_show_all_overlaps) if num_hops_show_all_overlaps else 2
            except (ValueError, TypeError):
                num_hops_show_all_overlaps = 2
            
            # Get fake data with proper search filtering and hop limiting
            fake_data = make_fake_graph_data(
                search_type=search_type,
                search_value=search_value,
                search_operator=search_operator,
                node_type=node_type,
                num_hops=num_hops_node_search if search_type == 'nodeValue' else num_hops_show_all_overlaps,
                num_connections_show_all_overlaps=num_connections_show_all_overlaps,
                show_nodes_only_search=show_nodes_only_search
            )
            
            # Return fake data
            return jsonify({
                'relationships': fake_data['relationships'],
                'relationships': fake_data['relationships'],
                'metadata': {
                    'nodeCount': len(fake_data['relationships']),
                    'relationshipCount': len(fake_data['relationships']),
                    'nodeColors': fake_data['metadata']['nodeColors'],
                    'relationshipColors': fake_data['metadata']['relationshipColors']
                }
            })

        # Convert num_hops to integer with default value of 2
        try:
            num_hops_node_search = int(num_hops_node_search) if num_hops_node_search else 2
        except (ValueError, TypeError):
            num_hops_node_search = 2
        try:
            num_connections_show_all_overlaps = int(num_connections_show_all_overlaps) if num_connections_show_all_overlaps else 2
        except (ValueError, TypeError):
            num_connections_show_all_overlaps = 2
        try:
            num_hops_show_all_overlaps = int(num_hops_show_all_overlaps) if num_hops_show_all_overlaps else 2
        except (ValueError, TypeError):
            num_hops_show_all_overlaps = 2

        # Establish Neo4j connection
        driver = get_neo4j_connection()

        # Fetch initial nodes from Neo4j based on the search parameters
        logger.info(f"Fetching initial nodes from Neo4j... (show_overlaps={show_overlaps}, search_value={search_value}, search_operator={search_operator}, node_type={node_type})")
        initial_nodes = get_initial_nodes(
            driver=driver,
            search_type=search_type,
            show_overlaps=show_overlaps,
            search_value=search_value,
            search_operator=search_operator,
            node_type=node_type,
            num_connections_show_all_overlaps=num_connections_show_all_overlaps,
            case_sensitive_search=case_sensitive_search
        )
        logger.info(f"Initial nodes {len(initial_nodes)}: {initial_nodes}")

        if not initial_nodes:
            return jsonify({
                'error': 'No initial nodes found',
                'traceback': '',
                'type': 'No initial nodes found'
            }), 200

        # Fetch graph data given the initial nodes
        logger.info(f"Fetching graph data given the initial nodes")
        data = get_graph_data(
            driver=driver,
            search_type=search_type,
            initial_nodes=initial_nodes,
            num_hops=num_hops_node_search if search_type == 'nodeValue' else num_hops_show_all_overlaps,
            show_nodes_only_search=show_nodes_only_search
        )

        logger.info(f"Final node count: {len(data['nodes'])}")
        logger.info(f"Final relationship count: {len(data['relationships'])}")

        # Close Neo4j connection
        driver.close()
    
        # Return the graph data
        logger.info("Successfully returned graph data via API")
        return jsonify(data)
    
    except Exception as e:
        # Close Neo4j connection
        if 'driver' in locals():
            driver.close()

        # Log the error and return a 500 error
        import traceback
        error_trace = traceback.format_exc()
        error_msg = f"Error: {str(e)}\nTraceback: {error_trace}"
        logger.error("API error:")
        logger.error(error_msg)
        return jsonify({
            'error': "An error occurred while fetching graph data",
            'traceback': "",
            'type': type(e).__name__
        }), 500


@graph_bp.route('/api/node-types')
def api_node_types():
    logger.info("API request received for node types...")
    try:
        # Establish Neo4j connection
        driver = get_neo4j_connection()
        
        with driver.session() as session:
            # Get all available labels from the database
            label_query = """
            CALL db.labels() YIELD label
            RETURN label
            ORDER BY label
            """
            result = session.run(label_query)
            labels = [record["label"] for record in result if record["label"] != "observation_of_identity"]
            
            logger.info(f"Found {len(labels)} node types: {labels}")
            
            # Close Neo4j connection
            driver.close()
            
            return jsonify({
                'node_types': labels
            })
            
    except Exception as e:
        # Close Neo4j connection
        if 'driver' in locals():
            driver.close()
            
        # Log the error and return a 500 error
        import traceback
        error_trace = traceback.format_exc()
        error_msg = f"Error: {str(e)}\nTraceback: {error_trace}"
        logger.error("API error:")
        logger.error(error_msg)
        return jsonify({
            'error': "An error occurred while fetching node types",
            'traceback': "",
            'type': type(e).__name__
        }), 500

@graph_bp.route('/api/source-types')
def api_source_types():
    logger.info("API request received for source types...")
    try:
        # Establish Neo4j connection
        driver = get_neo4j_connection()
        
        with driver.session() as session:
            # Get all available source types from the database
            label_query = """
            MATCH (n:source)
            RETURN DISTINCT n.value as source_type
            ORDER BY source_type
            """
            result = session.run(label_query)
            labels = [record["source_type"] for record in result if record["source_type"] is not None]

            logger.info(f"Found {len(labels)} source types: {labels}")

            # Close Neo4j connection
            driver.close()

            return jsonify({
                'source_types': labels
            })
            
    except Exception as e:
        # Close Neo4j connection
        if 'driver' in locals():
            driver.close()
            
        # Log the error and return a 500 error
        import traceback
        error_trace = traceback.format_exc()
        error_msg = f"Error: {str(e)}\nTraceback: {error_trace}"
        logger.error("API error:")
        logger.error(error_msg)
        return jsonify({
            'error': "An error occurred while fetching source types",
            'traceback': "",
            'type': type(e).__name__
        }), 500


def get_node_color(node_type):
    """Dynamically assign colors to node types, keeping source and observation fixed"""
    global NODE_COLOR_ASSIGNMENTS
    
    # Fixed colors for source and observation
    if node_type == 'source':
        return NODE_COLORS['source']
    elif node_type == 'observation_of_identity':
        return NODE_COLORS['observation_of_identity']
    
    # For other node types, assign colors dynamically
    if node_type not in NODE_COLOR_ASSIGNMENTS:
        # Get a random color from the options
        color_options = NODE_COLORS['node_color_options']
        assigned_color = random.choice(color_options)
        NODE_COLOR_ASSIGNMENTS[node_type] = assigned_color
    
    return NODE_COLOR_ASSIGNMENTS[node_type]

def get_relationship_color(relationship_type):
    """Dynamically assign colors to relationship types"""
    global RELATIONSHIP_COLOR_ASSIGNMENTS
    
    if relationship_type not in RELATIONSHIP_COLOR_ASSIGNMENTS:
        # Get a random color from the options
        assigned_color = random.choice(RELATIONSHIP_COLORS_OPTIONS)
        RELATIONSHIP_COLOR_ASSIGNMENTS[relationship_type] = assigned_color
    
    return RELATIONSHIP_COLOR_ASSIGNMENTS[relationship_type]

def get_initial_nodes(driver, search_type, show_overlaps, search_value, search_operator, node_type, num_connections_show_all_overlaps, case_sensitive_search):
    try:       
        with driver.session() as session:
            #########################################################################################
            # Search of a specific node
            #########################################################################################
            if search_type == 'nodeValue':
                # First, let's find out what labels actually exist
                label_query = """
                CALL db.labels() YIELD label
                RETURN label
                """
                label_result = session.run(label_query)
                available_labels = [record["label"] for record in label_result]
                logger.info(f"Available labels: {available_labels}")
                
                # Build Cypher query based on search parameters
                if node_type:
                    # Check if the requested node type exists
                    if node_type not in available_labels:
                        logger.warning(f"Requested node type '{node_type}' not found in database. Available types: {available_labels}")
                        return []
                    
                    # Filter by specific type
                    if search_operator == 'equals':
                        if case_sensitive_search:
                            query = f"MATCH (v:{node_type}) WHERE v.value = $search_value RETURN v"
                        else:
                            query = f"MATCH (v:{node_type}) WHERE toLower(v.value) = toLower($search_value) RETURN v"
                        result = session.run(query, search_value=search_value)
                    elif search_operator == 'contains':
                        if case_sensitive_search:
                            query = f"MATCH (v:{node_type}) WHERE v.value CONTAINS $search_value RETURN v"
                        else:
                            query = f"MATCH (v:{node_type}) WHERE toLower(v.value) CONTAINS toLower($search_value) RETURN v"
                        result = session.run(query, search_value=search_value)
                    elif search_operator == 'starts_with':
                        if case_sensitive_search:
                            query = f"MATCH (v:{node_type}) WHERE v.value STARTS WITH $search_value RETURN v"
                        else:
                            query = f"MATCH (v:{node_type}) WHERE toLower(v.value) STARTS WITH toLower($search_value) RETURN v"
                        result = session.run(query, search_value=search_value)
                    elif search_operator == 'ends_with':
                        if case_sensitive_search:
                            query = f"MATCH (v:{node_type}) WHERE v.value ENDS WITH $search_value RETURN v" 
                        else:
                            query = f"MATCH (v:{node_type}) WHERE toLower(v.value) ENDS WITH toLower($search_value) RETURN v"
                        result = session.run(query, search_value=search_value)
                    else:
                        raise ValueError(f"Invalid search operator: {search_operator}")
                else:
                    # Search across all node types
                    if search_operator == 'equals':
                        if case_sensitive_search:
                            query = """
                            MATCH (v)
                            WHERE v.value = $search_value
                            RETURN v
                            """
                        else:
                            query = """
                            MATCH (v)
                            WHERE toLower(v.value) = toLower($search_value)
                            RETURN v
                            """
                        result = session.run(query, search_value=search_value)
                    elif search_operator == 'contains':
                        if case_sensitive_search:
                            query = """
                            MATCH (v)
                            WHERE v.value CONTAINS $search_value
                            RETURN v
                            """
                        else:
                            query = """
                            MATCH (v)
                            WHERE toLower(v.value) CONTAINS toLower($search_value)
                            RETURN v
                            """
                        result = session.run(query, search_value=search_value)
                    elif search_operator == 'starts_with':
                        if case_sensitive_search:
                            query = """
                            MATCH (v)
                            WHERE v.value STARTS WITH $search_value
                            RETURN v
                            """
                        else:
                            query = """
                            MATCH (v)
                            WHERE toLower(v.value) STARTS WITH toLower($search_value)
                            RETURN v
                            """
                        result = session.run(query, search_value=search_value)
                    elif search_operator == 'ends_with':
                        if case_sensitive_search:
                            query = """
                            MATCH (v)
                            WHERE v.value ENDS WITH $search_value
                            RETURN v
                            """
                        else:
                            query = """
                            MATCH (v)
                            WHERE toLower(v.value) ENDS WITH toLower($search_value)
                            RETURN v
                            """
                        result = session.run(query, search_value=search_value)
                    else:
                        raise ValueError(f"Invalid search operator: {search_operator}")
                
                # Convert Neo4j nodes to list of dictionaries
                nodes = []
                for record in result:
                    node = record["v"]
                    # Convert Neo4j node to dictionary format
                    node_dict = dict(node)
                    node_dict['id'] = node.id
                    node_dict['elementId'] = node.element_id
                    node_dict['labels'] = list(node.labels)
                    nodes.append(node_dict)
                
                return nodes
                
            #########################################################################################
            # Show all overlaps
            #########################################################################################
            elif search_type == 'showAllOverlaps':
                logger.info("Finding identifiers with multiple observations...")
                
                # First, let's find out what relationship types actually exist
                relationship_query = """
                CALL db.relationshipTypes() YIELD relationshipType
                RETURN relationshipType
                """
                rel_result = session.run(relationship_query)
                relationship_types = [record["relationshipType"] for record in rel_result]
                logger.info(f"Available relationship types: {relationship_types}")
                
                # Also check what labels exist
                label_query = """
                CALL db.labels() YIELD label
                RETURN label
                """
                label_result = session.run(label_query)
                available_labels = [record["label"] for record in label_result]
                logger.info(f"Available labels: {available_labels}")
                
                # Filter identity labels to only include those that exist in the database
                identity_labels = [label for label in available_labels if label not in ['source', 'observation_of_identity']]
                if not identity_labels:
                    logger.warning(f"No identity labels found in database. Available: {available_labels}")
                    return []
                
                # Build Cypher query to find shared identifiers
                # Use a more generic approach that doesn't assume specific relationship names
                query = """
                MATCH (identifier)
                WHERE ANY(label IN labels(identifier) WHERE label IN $identity_labels)
                WITH identifier
                MATCH (obs:observation_of_identity)-[r]->(identifier)
                WITH identifier, count(DISTINCT obs) as observation_count
                WHERE observation_count >= $min_connections
                RETURN identifier, observation_count
                ORDER BY observation_count DESC
                """
                
                result = session.run(query, 
                                   identity_labels=identity_labels,
                                   min_connections=num_connections_show_all_overlaps)
                
                relationships = []
                for record in result:
                    node = record["identifier"]
                    node_dict = dict(node)
                    node_dict['id'] = node.id
                    node_dict['elementId'] = node.element_id
                    node_dict['labels'] = list(node.labels)
                    node_dict['observation_count'] = record["observation_count"]
                    relationships.append(node_dict)
                
                logger.info(f"Found {len(relationships)} total shared identifiers")
                return relationships
            else:
                # Return empty graph if no search or show_overlaps is specified
                return []
    except Exception as e:
        logger.error(f"Error getting initial nodes: {str(e)}")
        raise Exception(f"Initial node query failed: {str(e)}")


def flatten_properties(props, prefix=''):
    flat = {}
    for k, v in props.items():
        key = f'{prefix}{k}' if prefix else str(k)
        if isinstance(v, dict):
            flat.update(flatten_properties(v, key + '.'))
        elif isinstance(v, list):
            if v and all(isinstance(i, dict) for i in v):
                for idx, item in enumerate(v):
                    flat.update(flatten_properties(item, f'{key}[{idx}].'))
            else:
                flat[key] = ', '.join(str(i) for i in v)
        else:
            flat[key] = v
    return flat


def get_graph_data(driver, search_type, initial_nodes, num_hops, show_nodes_only_search=False):
    try:
        nodes = []
        seen_ids = set()

        # First, collect the initial node IDs
        initial_node_ids = []
        for v in initial_nodes:
            # Get the node elementId
            if isinstance(v, dict):
                v_id = str(v['elementId'])
            else:
                v_id = str(v)
            initial_node_ids.append(v_id)
            
        logger.info(f"Initial node IDs: {initial_node_ids}")

        # If show_nodes_only_search is True, only process the initial nodes
        if show_nodes_only_search:
            logger.info("Show nodes only search is enabled - only processing initial nodes")
            all_nodes = initial_nodes
        else:
            # Get all vertices within num_hops hops of our initial vertices
            logger.info(f"Getting nodes within {num_hops} hops of {len(initial_node_ids)} initial nodes")
            
            with driver.session() as session:
                # Get all connected nodes including the initial ones
                # Use Cypher to find all nodes within num_hops distance
                # Note: Neo4j doesn't allow parameters in variable-length path patterns, so we use string formatting
                query = f"""
                MATCH (start)
                WHERE elementId(start) IN $initial_ids
                WITH start
                MATCH (start)-[*1..{num_hops}]-(connected)
                RETURN DISTINCT connected
                """
                
                result = session.run(query, initial_ids=initial_node_ids)
                
                all_nodes = []
                for record in result:
                    node = record["connected"]
                    node_dict = dict(node)
                    node_dict['id'] = node.id
                    node_dict['elementId'] = node.element_id
                    node_dict['labels'] = list(node.labels)
                    all_nodes.append(node_dict)
                
                # Add initial vertices if not already included
                for v in initial_nodes:
                    if isinstance(v, dict):
                        v_id = str(v['elementId'])
                    else:
                        v_id = str(v)
                    if not any(str(node['elementId']) == v_id for node in all_nodes):
                        all_nodes.append(v)
            
            logger.info(f"Found {len(all_nodes)} total unique nodes")
        
        # Process all nodes - we need a session for this regardless of show_nodes_only_search
        with driver.session() as session:
            for v in all_nodes:
                v_id = str(v['elementId'])
                if v_id in seen_ids:
                    continue
                seen_ids.add(v_id)

                # This is the value to display in the node
                raw_label = v['labels'][0] if v['labels'] else 'default'
                tooltip = ''
                
                if raw_label.startswith('observation_of_'):
                    value = f"{v.get('source', 'Unknown')}: {v.get('value', v_id)}"
                    # Count observations for this node
                    num_observations = 1  # Default for observation nodes
                    flat = flatten_properties(v)
                    tooltip = '\n'.join(f"{k}: {v}" for k, v in sorted(flat.items()))
                else:
                    value = v.get('value', v_id)

                name = v.get('name', value)
                # Use dynamic color assignment
                color = get_node_color(raw_label)

                # For identifier vertices, count the number of observations
                # Only count for node types that are not source or observation_of_identity
                num_observations = 0
                if raw_label not in ['source', 'observation_of_identity']:
                    # Count observations connected to this identifier using Cypher
                    # Use a generic approach that doesn't assume specific relationship names
                    count_query = """
                    MATCH (obs:observation_of_identity)-[r]->(identifier)
                    WHERE elementId(identifier) = $node_id
                    RETURN count(DISTINCT obs) as count
                    """
                    count_result = session.run(count_query, node_id=v_id)
                    count_record = count_result.single()
                    num_observations = count_record["count"] if count_record else 0
                    
                    # Update the display label for vertices with multiple observations
                    if num_observations > 1:
                        value = f"{value}\n({num_observations} obs)"

                node = {
                    'id': v_id,
                    'label': value,
                    'title': tooltip or name,
                    'group': raw_label,
                    'color': color,
                    'num_observations': num_observations,
                    'is_shared': num_observations > 1,
                    'properties': {**v, 'num_observations': num_observations}
                }
                nodes.append(node)

            logger.info(f"Processed {len(nodes)} nodes")
            logger.info(f"Seen IDs: {seen_ids}")

            # Get ALL relationships between any vertices in our final set
            # Only get relationships if not in show_nodes_only_search mode
            if not show_nodes_only_search:
                logger.info("Getting relationships between vertices...")
                
                # Get relationships using Cypher
                relationship_query = """
                MATCH (from)-[r]->(to)
                WHERE elementId(from) IN $node_ids AND elementId(to) IN $node_ids
                RETURN from, r, to
                """
                
                relationship_result = session.run(relationship_query, node_ids=list(seen_ids))
                
                seen_relationship_ids = set()
                formatted_relationships = []
                relationship_counter = 0

                for record in relationship_result:
                    from_node = record["from"]
                    relationship = record["r"]
                    to_node = record["to"]
                    
                    relationship_id = str(relationship.element_id)
                    if relationship_id in seen_relationship_ids:
                        continue
                    seen_relationship_ids.add(relationship_id)

                    from_v = str(from_node.element_id)
                    to_v = str(to_node.element_id)
                    label = relationship.type
                    # Use dynamic color assignment for relationships
                    style = get_relationship_color(label)

                    formatted_relationships.append({
                        'id': f'e{relationship_counter}',
                        'from': from_v,
                        'to': to_v,
                        'label': label,
                        'title': label,
                        'color': style['color'],
                        'width': style['width'],
                        'dashes': style['dashes'],
                        'arrows': {'to': {'enabled': True, 'type': 'arrow'}}
                    })
                    relationship_counter += 1
            else:
                # No relationships when show_nodes_only_search is True
                formatted_relationships = []

        logger.info(f"Final counts - Nodes: {len(nodes)}, Relationships: {len(formatted_relationships)}")

        # Build the final color mappings for the frontend
        final_node_colors = {}
        final_relationship_colors = {}
        
        # Add fixed colors for source and observation
        final_node_colors['source'] = NODE_COLORS['source']
        final_node_colors['observation_of_identity'] = NODE_COLORS['observation_of_identity']
        
        # Add dynamically assigned colors
        for node_type, color in NODE_COLOR_ASSIGNMENTS.items():
            final_node_colors[node_type] = color
        
        for relationship_type, color in RELATIONSHIP_COLOR_ASSIGNMENTS.items():
            final_relationship_colors[relationship_type] = color

        result = {
            'nodes': nodes,
            'relationships': formatted_relationships,
            'metadata': {
                'nodeCount': len(nodes),
                'relationshipCount': len(formatted_relationships),
                'nodeColors': final_node_colors,
                'relationshipColors': final_relationship_colors
            }
        }

        return result
    except Exception as e:
        logger.error(f"Error getting graph data: {str(e)}")
        raise Exception(f"Node query failed: {str(e)}")
    

def make_fake_graph_data(search_type=None, search_value=None, search_operator=None, node_type=None, num_hops=2, num_connections_show_all_overlaps=2, show_nodes_only_search=False):
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
            'relationships': all_nodes,
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
            'relationships': [],
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
    
    logger.info(f"Final result: {len(final_nodes)} nodes, {len(final_relationships)} relationships")
    logger.info(f"Final nodes: {[v['id'] for v in final_nodes]}")
    
    return {
        'relationships': final_nodes,
        'relationships': final_relationships,
        'metadata': {
            'nodeCount': len(final_nodes),
            'relationshipCount': len(final_relationships),
            'nodeColors': fake_node_colors,
            'relationshipColors': fake_relationship_colors
        }
    }

@graph_bp.route('/api/find-paths')
def api_find_paths():
    logger.info("API request received for finding paths...")
    try:
        # Get parameters from the request
        from_node_id = request.args.get('fromNodeId')
        to_node_id = request.args.get('toNodeId')
        max_depth = request.args.get('maxDepth',FIND_PATHS_MAX_DEPTH)
        
        if not from_node_id or not to_node_id:
            return jsonify({
                'error': 'Both fromNodeId and toNodeId are required',
                'type': 'Missing parameters'
            }), 400
        
        try:
            max_depth = int(max_depth)
        except (ValueError, TypeError):
            max_depth = FIND_PATHS_MAX_DEPTH
        
        logger.info(f"Finding paths from {from_node_id} to {to_node_id} with max depth {max_depth}")
        
        # Establish Neo4j connection
        driver = get_neo4j_connection()
        
        with driver.session() as session:
            # First, find the shortest path length
            shortest_length_query = """
            MATCH (start), (end)
            WHERE elementId(start) = $from_node_id AND elementId(end) = $to_node_id
            MATCH p = shortestPath((start)-[*1..{max_depth}]-(end))
            RETURN length(p) as pathLength
            LIMIT 1
            """
            
            shortest_result = session.run(shortest_length_query.format(max_depth=max_depth), 
                                        from_node_id=from_node_id, to_node_id=to_node_id)
            shortest_record = shortest_result.single()
            
            if not shortest_record:
                # No path found
                return jsonify({
                    'paths': [],
                    'count': 0
                })
            
            shortest_length = shortest_record["pathLength"]
            logger.info(f"Shortest path length: {shortest_length}")
            
            # Now find all paths of the shortest length
            all_paths_query = f"""
            MATCH (start), (end)
            WHERE elementId(start) = $from_node_id AND elementId(end) = $to_node_id
            MATCH p = (start)-[*{shortest_length}]-(end)
            RETURN nodes(p) AS pathNodes, relationships(p) AS pathRelationsihps
            """
            
            result = session.run(all_paths_query, from_node_id=from_node_id, to_node_id=to_node_id)
            
            paths = []
            for record in result:
                path_nodes = record["pathNodes"]
                path_relationships = record["pathRelationsihps"]
                
                # Convert nodes to node IDs
                node_ids = [str(node.element_id) for node in path_nodes]
                
                # Convert relationships to relationship information
                relationship_info = []
                for relationship in path_relationships:
                    relationship_info.append({
                        'id': str(relationship.element_id),
                        'from': str(relationship.start_node.element_id),
                        'to': str(relationship.end_node.element_id),
                        'label': relationship.type
                    })
                
                paths.append({
                    'nodes': node_ids,
                    'relationships': relationship_info
                })
            
            logger.info(f"Found {len(paths)} paths between nodes")
            
            # Close Neo4j connection
            driver.close()
            
            return jsonify({
                'paths': paths,
                'count': len(paths)
            })
            
    except Exception as e:
        # Close Neo4j connection
        if 'driver' in locals():
            driver.close()
            
        # Log the error and return a 500 error
        import traceback
        error_trace = traceback.format_exc()
        error_msg = f"Error: {str(e)}\nTraceback: {error_trace}"
        logger.error("API error:")
        logger.error(error_msg)
        return jsonify({
            'error': "An error occurred while finding paths",
            'traceback': "",
            'type': type(e).__name__
        }), 500