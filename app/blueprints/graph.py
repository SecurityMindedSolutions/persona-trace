from flask import Blueprint, render_template, current_app, jsonify, request
from neo4j import GraphDatabase
import random

import logging
from lib.constants import VERTEX_COLORS, EDGE_COLORS_OPTIONS, logger, FIND_PATHS_MAX_DEPTH
from lib.neo4j_connection import get_neo4j_connection
import json

# Blueprint for the graph page
graph_bp = Blueprint('graph', __name__)

# Global dictionaries to maintain consistent color assignments across requests
VERTEX_COLOR_ASSIGNMENTS = {}
EDGE_COLOR_ASSIGNMENTS = {}


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
        # Vertex value search
        show_overlaps = request.args.get('showOverlaps') == "true"
        vertex_type = request.args.get('vertexType')
        search_operator = request.args.get('searchOperator', 'equals')
        search_value = request.args.get('searchValue')
        num_hops_vertex_search = request.args.get('numHopsVertexSearch', '2')
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
                num_hops_vertex_search = int(num_hops_vertex_search) if num_hops_vertex_search else 2
            except (ValueError, TypeError):
                num_hops_vertex_search = 2
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
                vertex_type=vertex_type,
                num_hops=num_hops_vertex_search if search_type == 'vertexValue' else num_hops_show_all_overlaps,
                num_connections_show_all_overlaps=num_connections_show_all_overlaps
            )
            
            # Return fake data
            return jsonify({
                'vertices': fake_data['vertices'],
                'edges': fake_data['edges'],
                'metadata': {
                    'vertexCount': len(fake_data['vertices']),
                    'edgeCount': len(fake_data['edges']),
                    'vertexColors': fake_data['metadata']['vertexColors'],
                    'edgeColors': fake_data['metadata']['edgeColors']
                }
            })

        # Convert num_hops to integer with default value of 2
        try:
            num_hops_vertex_search = int(num_hops_vertex_search) if num_hops_vertex_search else 2
        except (ValueError, TypeError):
            num_hops_vertex_search = 2
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

        # Fetch initial vertices from Neo4j based on the search parameters
        logger.info(f"Fetching initial vertices from Neo4j... (show_overlaps={show_overlaps}, search_value={search_value}, search_operator={search_operator}, vertex_type={vertex_type})")
        initial_vertices = get_initial_nodes(
            driver=driver,
            search_type=search_type,
            show_overlaps=show_overlaps,
            search_value=search_value,
            search_operator=search_operator,
            vertex_type=vertex_type,
            num_connections_show_all_overlaps=num_connections_show_all_overlaps
        )
        logger.info(f"Initial vertices {len(initial_vertices)}: {initial_vertices}")

        if not initial_vertices:
            return jsonify({
                'error': 'No initial vertices found',
                'traceback': '',
                'type': 'No initial vertices found'
            }), 200

        # Fetch graph data given the initial vertices
        logger.info(f"Fetching graph data given the initial vertices")
        data = get_graph_data(
            driver=driver,
            search_type=search_type,
            initial_vertices=initial_vertices,
            num_hops=num_hops_vertex_search if search_type == 'vertexValue' else num_hops_show_all_overlaps
        )

        logger.info(f"Final vertex count: {len(data['vertices'])}")
        logger.info(f"Final edge count: {len(data['edges'])}")

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


@graph_bp.route('/api/vertex-types')
def api_vertex_types():
    logger.info("API request received for vertex types...")
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
            
            logger.info(f"Found {len(labels)} vertex types: {labels}")
            
            # Close Neo4j connection
            driver.close()
            
            return jsonify({
                'vertex_types': labels
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
            'error': "An error occurred while fetching vertex types",
            'traceback': "",
            'type': type(e).__name__
        }), 500


def get_vertex_color(vertex_type):
    """Dynamically assign colors to vertex types, keeping source and observation fixed"""
    global VERTEX_COLOR_ASSIGNMENTS
    
    # Fixed colors for source and observation
    if vertex_type == 'source':
        return VERTEX_COLORS['source']
    elif vertex_type == 'observation_of_identity':
        return VERTEX_COLORS['observation_of_identity']
    
    # For other vertex types, assign colors dynamically
    if vertex_type not in VERTEX_COLOR_ASSIGNMENTS:
        # Get a random color from the options
        color_options = VERTEX_COLORS['vertex_color_options']
        assigned_color = random.choice(color_options)
        VERTEX_COLOR_ASSIGNMENTS[vertex_type] = assigned_color
    
    return VERTEX_COLOR_ASSIGNMENTS[vertex_type]

def get_edge_color(edge_type):
    """Dynamically assign colors to edge types"""
    global EDGE_COLOR_ASSIGNMENTS
    
    if edge_type not in EDGE_COLOR_ASSIGNMENTS:
        # Get a random color from the options
        assigned_color = random.choice(EDGE_COLORS_OPTIONS)
        EDGE_COLOR_ASSIGNMENTS[edge_type] = assigned_color
    
    return EDGE_COLOR_ASSIGNMENTS[edge_type]

def get_initial_nodes(driver, search_type, show_overlaps, search_value, search_operator, vertex_type, num_connections_show_all_overlaps):
    try:       
        with driver.session() as session:
            #########################################################################################
            # Search of a specific vertex
            #########################################################################################
            if search_type == 'vertexValue':
                # First, let's find out what labels actually exist
                label_query = """
                CALL db.labels() YIELD label
                RETURN label
                """
                label_result = session.run(label_query)
                available_labels = [record["label"] for record in label_result]
                logger.info(f"Available labels: {available_labels}")
                
                # Build Cypher query based on search parameters
                if vertex_type:
                    # Check if the requested vertex type exists
                    if vertex_type not in available_labels:
                        logger.warning(f"Requested vertex type '{vertex_type}' not found in database. Available types: {available_labels}")
                        return []
                    
                    # Filter by specific type
                    if search_operator == 'equals':
                        query = f"MATCH (v:{vertex_type}) WHERE toLower(v.value) = toLower($search_value) RETURN v"
                        result = session.run(query, search_value=search_value)
                    elif search_operator == 'contains':
                        query = f"MATCH (v:{vertex_type}) WHERE toLower(v.value) CONTAINS toLower($search_value) RETURN v"
                        result = session.run(query, search_value=search_value)
                    else:
                        raise ValueError(f"Invalid search operator: {search_operator}")
                else:
                    # Search across all vertex types
                    if search_operator == 'equals':
                        query = """
                        MATCH (v)
                        WHERE toLower(v.value) = toLower($search_value)
                        RETURN v
                        """
                        result = session.run(query, search_value=search_value)
                    elif search_operator == 'contains':
                        query = """
                        MATCH (v)
                        WHERE toLower(v.value) CONTAINS toLower($search_value)
                        RETURN v
                        """
                        result = session.run(query, search_value=search_value)
                    else:
                        raise ValueError(f"Invalid search operator: {search_operator}")
                
                # Convert Neo4j nodes to list of dictionaries
                vertices = []
                for record in result:
                    node = record["v"]
                    # Convert Neo4j node to dictionary format
                    vertex_dict = dict(node)
                    vertex_dict['id'] = node.id
                    vertex_dict['elementId'] = node.element_id
                    vertex_dict['labels'] = list(node.labels)
                    vertices.append(vertex_dict)
                
                return vertices
                
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
                
                vertices = []
                for record in result:
                    node = record["identifier"]
                    vertex_dict = dict(node)
                    vertex_dict['id'] = node.id
                    vertex_dict['elementId'] = node.element_id
                    vertex_dict['labels'] = list(node.labels)
                    vertex_dict['observation_count'] = record["observation_count"]
                    vertices.append(vertex_dict)
                
                logger.info(f"Found {len(vertices)} total shared identifiers")
                return vertices
            else:
                # Return empty graph if no search or show_overlaps is specified
                return []
    except Exception as e:
        logger.error(f"Error getting initial vertices: {str(e)}")
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


def get_graph_data(driver, search_type, initial_vertices, num_hops):
    try:
        vertices = []
        seen_ids = set()

        # First, collect the initial vertex IDs
        initial_vertex_ids = []
        for v in initial_vertices:
            # Get the vertex elementId
            if isinstance(v, dict):
                v_id = str(v['elementId'])
            else:
                v_id = str(v)
            initial_vertex_ids.append(v_id)
            
        logger.info(f"Initial vertex IDs: {initial_vertex_ids}")

        # Get all vertices within num_hops hops of our initial vertices
        logger.info(f"Getting vertices within {num_hops} hops of {len(initial_vertex_ids)} initial vertices")
        
        with driver.session() as session:
            # Get all connected vertices including the initial ones
            # Use Cypher to find all nodes within num_hops distance
            # Note: Neo4j doesn't allow parameters in variable-length path patterns, so we use string formatting
            query = f"""
            MATCH (start)
            WHERE elementId(start) IN $initial_ids
            WITH start
            MATCH (start)-[*1..{num_hops}]-(connected)
            RETURN DISTINCT connected
            """
            
            result = session.run(query, initial_ids=initial_vertex_ids)
            
            all_vertices = []
            for record in result:
                node = record["connected"]
                vertex_dict = dict(node)
                vertex_dict['id'] = node.id
                vertex_dict['elementId'] = node.element_id
                vertex_dict['labels'] = list(node.labels)
                all_vertices.append(vertex_dict)
            
            # Add initial vertices if not already included
            for v in initial_vertices:
                if isinstance(v, dict):
                    v_id = str(v['elementId'])
                else:
                    v_id = str(v)
                if not any(str(vertex['elementId']) == v_id for vertex in all_vertices):
                    all_vertices.append(v)
            
            logger.info(f"Found {len(all_vertices)} total unique vertices")
            
            # Process all vertices
            for v in all_vertices:
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
                color = get_vertex_color(raw_label)

                # For identifier vertices, count the number of observations
                # Only count for vertex types that are not source or observation_of_identity
                num_observations = 0
                if raw_label not in ['source', 'observation_of_identity']:
                    # Count observations connected to this identifier using Cypher
                    # Use a generic approach that doesn't assume specific relationship names
                    count_query = """
                    MATCH (obs:observation_of_identity)-[r]->(identifier)
                    WHERE elementId(identifier) = $vertex_id
                    RETURN count(DISTINCT obs) as count
                    """
                    count_result = session.run(count_query, vertex_id=v_id)
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
                vertices.append(node)

            logger.info(f"Processed {len(vertices)} vertices")
            logger.info(f"Seen IDs: {seen_ids}")

            # Get ALL edges between any vertices in our final set
            logger.info("Getting edges between vertices...")
            
            # Get edges using Cypher
            edge_query = """
            MATCH (from)-[r]->(to)
            WHERE elementId(from) IN $vertex_ids AND elementId(to) IN $vertex_ids
            RETURN from, r, to
            """
            
            edge_result = session.run(edge_query, vertex_ids=list(seen_ids))
            
            seen_edge_ids = set()
            formatted_edges = []
            edge_counter = 0

            for record in edge_result:
                from_node = record["from"]
                relationship = record["r"]
                to_node = record["to"]
                
                edge_id = str(relationship.element_id)
                if edge_id in seen_edge_ids:
                    continue
                seen_edge_ids.add(edge_id)

                from_v = str(from_node.element_id)
                to_v = str(to_node.element_id)
                label = relationship.type
                # Use dynamic color assignment for edges
                style = get_edge_color(label)

                formatted_edges.append({
                    'id': f'e{edge_counter}',
                    'from': from_v,
                    'to': to_v,
                    'label': label,
                    'title': label,
                    'color': style['color'],
                    'width': style['width'],
                    'dashes': style['dashes'],
                    'arrows': {'to': {'enabled': True, 'type': 'arrow'}}
                })
                edge_counter += 1

        logger.info(f"Final counts - Vertices: {len(vertices)}, Edges: {len(formatted_edges)}")

        # Build the final color mappings for the frontend
        final_vertex_colors = {}
        final_edge_colors = {}
        
        # Add fixed colors for source and observation
        final_vertex_colors['source'] = VERTEX_COLORS['source']
        final_vertex_colors['observation_of_identity'] = VERTEX_COLORS['observation_of_identity']
        
        # Add dynamically assigned colors
        for vertex_type, color in VERTEX_COLOR_ASSIGNMENTS.items():
            final_vertex_colors[vertex_type] = color
        
        for edge_type, color in EDGE_COLOR_ASSIGNMENTS.items():
            final_edge_colors[edge_type] = color

        result = {
            'vertices': vertices,
            'edges': formatted_edges,
            'metadata': {
                'vertexCount': len(vertices),
                'edgeCount': len(formatted_edges),
                'vertexColors': final_vertex_colors,
                'edgeColors': final_edge_colors
            }
        }

        return result
    except Exception as e:
        logger.error(f"Error getting graph data: {str(e)}")
        raise Exception(f"Vertex query failed: {str(e)}")
    

def make_fake_graph_data(search_type=None, search_value=None, search_operator=None, vertex_type=None, num_hops=2, num_connections_show_all_overlaps=2):
    # Create fake vertex and edge color assignments for consistency
    fake_vertex_colors = {
        'source': VERTEX_COLORS['source'],
        'observation_of_identity': VERTEX_COLORS['observation_of_identity'],
        'email_address': VERTEX_COLORS['vertex_color_options'][0],
        'ip_address': VERTEX_COLORS['vertex_color_options'][1], 
        'phone_number': VERTEX_COLORS['vertex_color_options'][2],
        'address': VERTEX_COLORS['vertex_color_options'][3],
        'name': VERTEX_COLORS['vertex_color_options'][4]
    }
    
    fake_edge_colors = {
        'has_observation': EDGE_COLORS_OPTIONS[5],
        'has_email': EDGE_COLORS_OPTIONS[0],
        'has_ip': EDGE_COLORS_OPTIONS[1],
        'has_phone': EDGE_COLORS_OPTIONS[2], 
        'has_address': EDGE_COLORS_OPTIONS[3],
        'has_name': EDGE_COLORS_OPTIONS[4]
    }
    
    # Define the complete fake dataset
    all_vertices = [
        # Source vertices (observations)
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
        # Observation vertices
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
        # Identity vertices (with some overlaps)
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
    
    all_edges = [
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
            'vertices': all_vertices,
            'edges': all_edges,
            'metadata': {
                'vertexCount': len(all_vertices),
                'edgeCount': len(all_edges),
                'vertexColors': fake_vertex_colors,
                'edgeColors': fake_edge_colors
            }
        }
    
    # Filter vertices based on search parameters
    filtered_vertices = []
    if search_type == 'vertexValue':
        # Find vertices that match the search criteria
        for vertex in all_vertices:
            if vertex['group'] == vertex_type or not vertex_type:
                vertex_value = vertex.get('label', '')
                if search_operator == 'equals' and vertex_value.lower() == search_value.lower():
                    filtered_vertices.append(vertex)
                elif search_operator == 'contains' and search_value.lower() in vertex_value.lower():
                    filtered_vertices.append(vertex)
    
    elif search_type == 'showAllOverlaps':
        # Find vertices with multiple observations
        for vertex in all_vertices:
            if vertex['num_observations'] >= num_connections_show_all_overlaps:
                filtered_vertices.append(vertex)
    
    # Debug logging
    logger.info(f"Search parameters: type={search_type}, value={search_value}, operator={search_operator}, vertex_type={vertex_type}")
    logger.info(f"Filtered vertices found: {len(filtered_vertices)}")
    for v in filtered_vertices:
        logger.info(f"  - {v['id']} ({v['group']}): {v['label']}")
    
    # If no matching vertices found, return empty result
    if not filtered_vertices:
        return {
            'vertices': [],
            'edges': [],
            'metadata': {
                'vertexCount': 0,
                'edgeCount': 0,
                'vertexColors': fake_vertex_colors,
                'edgeColors': fake_edge_colors
            }
        }
    
    # Get vertices within num_hops of the filtered vertices
    included_vertices = set()
    included_edges = []
    
    # Add the filtered vertices
    for vertex in filtered_vertices:
        included_vertices.add(vertex['id'])
    
    logger.info(f"Starting with {len(included_vertices)} filtered vertices: {included_vertices}")
    
    # Add vertices within num_hops
    for hop in range(num_hops):
        new_vertices = set()
        for edge in all_edges:
            from_id = edge['from']
            to_id = edge['to']
            
            # If one end is included, add the other end and the edge
            if from_id in included_vertices and to_id not in included_vertices:
                new_vertices.add(to_id)
                included_edges.append(edge)
            elif to_id in included_vertices and from_id not in included_vertices:
                new_vertices.add(from_id)
                included_edges.append(edge)
            elif from_id in included_vertices and to_id in included_vertices:
                # Both vertices are included, add edge if not already added
                if edge not in included_edges:
                    included_edges.append(edge)
        
        included_vertices.update(new_vertices)
        logger.info(f"After hop {hop + 1}: {len(included_vertices)} vertices, {len(included_edges)} edges")
    
    # Special handling: Always include source nodes that are connected to any included observation nodes
    # This ensures that when we find identity nodes, we also show their source observations
    source_vertices = set()
    for vertex in all_vertices:
        if vertex['group'] == 'source':
            # Check if this source is connected to any included observation nodes
            for edge in all_edges:
                if edge['label'] == 'has_observation':
                    # In fake data: source -> observation (from: source, to: observation)
                    if edge['from'] == vertex['id'] and edge['to'] in included_vertices:
                        source_vertices.add(vertex['id'])
                        # Add the edge connecting source to observation
                        if edge not in included_edges:
                            included_edges.append(edge)
                            logger.info(f"Added source vertex {vertex['id']} connected to observation {edge['to']}")
                    # Also check reverse direction in case edge direction is different
                    elif edge['to'] == vertex['id'] and edge['from'] in included_vertices:
                        source_vertices.add(vertex['id'])
                        # Add the edge connecting observation to source
                        if edge not in included_edges:
                            included_edges.append(edge)
                            logger.info(f"Added source vertex {vertex['id']} connected from observation {edge['from']}")
    
    logger.info(f"Found {len(source_vertices)} source vertices to include: {source_vertices}")
    
    # Add source vertices to included set
    included_vertices.update(source_vertices)
    
    # Get the final vertices and edges
    final_vertices = [v for v in all_vertices if v['id'] in included_vertices]
    final_edges = included_edges
    
    # Recalculate num_observations for vertices based on actual connections in the final result
    for vertex in final_vertices:
        if vertex['group'] not in ['source', 'observation_of_identity']:
            # Count how many observation vertices are connected to this vertex in the final result
            observation_count = 0
            for edge in final_edges:
                if edge['label'].startswith('has_') and edge['to'] == vertex['id']:
                    # Check if the 'from' vertex is an observation
                    from_vertex = next((v for v in final_vertices if v['id'] == edge['from']), None)
                    if from_vertex and from_vertex['group'] == 'observation_of_identity':
                        observation_count += 1
            
            # Update the vertex with the correct observation count
            vertex['num_observations'] = observation_count
            vertex['is_shared'] = observation_count > 1
            
            # Update the label to include observation count if multiple observations
            if observation_count > 1:
                # Remove any existing observation count from the label
                import re
                base_label = re.sub(r'(\n| )?\(\d+ obs\)', '', vertex['label'])
                vertex['label'] = f"{base_label}\n({observation_count} obs)"
    
    logger.info(f"Final result: {len(final_vertices)} vertices, {len(final_edges)} edges")
    logger.info(f"Final vertices: {[v['id'] for v in final_vertices]}")
    
    return {
        'vertices': final_vertices,
        'edges': final_edges,
        'metadata': {
            'vertexCount': len(final_vertices),
            'edgeCount': len(final_edges),
            'vertexColors': fake_vertex_colors,
            'edgeColors': fake_edge_colors
        }
    }

@graph_bp.route('/api/find-paths')
def api_find_paths():
    logger.info("API request received for finding paths...")
    try:
        # Get parameters from the request
        from_vertex_id = request.args.get('fromVertexId')
        to_vertex_id = request.args.get('toVertexId')
        max_depth = request.args.get('maxDepth',FIND_PATHS_MAX_DEPTH)
        
        if not from_vertex_id or not to_vertex_id:
            return jsonify({
                'error': 'Both fromVertexId and toVertexId are required',
                'type': 'Missing parameters'
            }), 400
        
        try:
            max_depth = int(max_depth)
        except (ValueError, TypeError):
            max_depth = FIND_PATHS_MAX_DEPTH
        
        logger.info(f"Finding paths from {from_vertex_id} to {to_vertex_id} with max depth {max_depth}")
        
        # Establish Neo4j connection
        driver = get_neo4j_connection()
        
        with driver.session() as session:
            # First, find the shortest path length
            shortest_length_query = """
            MATCH (start), (end)
            WHERE elementId(start) = $from_vertex_id AND elementId(end) = $to_vertex_id
            MATCH p = shortestPath((start)-[*1..{max_depth}]-(end))
            RETURN length(p) as pathLength
            LIMIT 1
            """
            
            shortest_result = session.run(shortest_length_query.format(max_depth=max_depth), 
                                        from_vertex_id=from_vertex_id, to_vertex_id=to_vertex_id)
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
            WHERE elementId(start) = $from_vertex_id AND elementId(end) = $to_vertex_id
            MATCH p = (start)-[*{shortest_length}]-(end)
            RETURN nodes(p) AS pathNodes, relationships(p) AS pathEdges
            """
            
            result = session.run(all_paths_query, from_vertex_id=from_vertex_id, to_vertex_id=to_vertex_id)
            
            paths = []
            for record in result:
                path_nodes = record["pathNodes"]
                path_edges = record["pathEdges"]
                
                # Convert nodes to vertex IDs
                node_ids = [str(node.element_id) for node in path_nodes]
                
                # Convert edges to edge information
                edge_info = []
                for edge in path_edges:
                    edge_info.append({
                        'id': str(edge.element_id),
                        'from': str(edge.start_node.element_id),
                        'to': str(edge.end_node.element_id),
                        'label': edge.type
                    })
                
                paths.append({
                    'nodes': node_ids,
                    'edges': edge_info
                })
            
            logger.info(f"Found {len(paths)} paths between vertices")
            
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