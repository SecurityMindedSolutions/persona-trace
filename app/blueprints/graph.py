from flask import Blueprint, render_template, current_app, jsonify, request
from neo4j import GraphDatabase
import random

import logging
from lib.constants import NODE_COLORS, RELATIONSHIP_COLORS_OPTIONS, logger, FIND_PATHS_MAX_DEPTH
from lib.neo4j_connection import get_neo4j_connection
from modules.neo4j_get_initial_nodes import get_initial_nodes
from modules.fake_data import make_fake_graph_data
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
        #########################################################################################
        # Get search parameters from the request
        #########################################################################################
        # Get search parameters from the request
        search_type = request.args.get('searchType')
        # Node value search
        show_overlaps = request.args.get('showOverlaps') == "true"
        node_type = request.args.get('nodeType')
        search_operator = request.args.get('searchOperator', 'equals')
        search_value = request.args.get('searchValue')
        num_hops_node_search = request.args.get('numHopsNodeSearch', '1')
        show_nodes_only_search = request.args.get('showNodesOnlySearch', 'false').lower() == 'true'
        search_source_select = request.args.get('searchSourceSelect', '')
        case_sensitive_search = request.args.get('caseSensitiveSearch', 'false').lower() == 'true'
        # Show all overlaps
        num_connections_show_all_overlaps = request.args.get('numConnectionsShowAllOverlaps', '1')
        num_hops_show_all_overlaps = request.args.get('numHopsShowAllOverlaps', '1')
        # Fake data parameter
        fake_data = request.args.get('fake_data', 'false').lower() == 'true'
        print(f"Fake data: {fake_data}")
        # Convert num_hops to integer with default value of 2
        try:
            num_hops_node_search = int(num_hops_node_search)
        except (ValueError, TypeError):
            num_hops_node_search = 1
        try:
            num_connections_show_all_overlaps = int(num_connections_show_all_overlaps)
        except (ValueError, TypeError):
            num_connections_show_all_overlaps = 1
        try:
            num_hops_show_all_overlaps = int(num_hops_show_all_overlaps)
        except (ValueError, TypeError):
            num_hops_show_all_overlaps = 1


        #########################################################################################
        # If fake_data is true, return fake data
        #########################################################################################
        if fake_data:
            logger.info("Returning fake data...")
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
                'nodes': fake_data['nodes'],
                'relationships': fake_data['relationships'],
                'metadata': {
                    'nodeCount': len(fake_data['relationships']),
                    'relationshipCount': len(fake_data['relationships']),
                    'relationshipColors': fake_data['metadata']['relationshipColors']
                }
            })


        #########################################################################################
        # Real Data
        #########################################################################################
        # Establish Neo4j connection
        driver = get_neo4j_connection()

        # Fetch initial nodes from Neo4j based on the search parameters
        logger.info(f"Fetching initial nodes from Neo4j... (show_overlaps={show_overlaps}, search_value={search_value}, search_operator={search_operator}, node_type={node_type})")
        initial_nodes = get_initial_nodes(
            driver=driver,
            search_type=search_type,
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


        # Fetch the rest of the graph data given the initial nodes, e.g. connected nodes and relationships
        logger.info(f"Fetching graph data given the initial nodes")
        data = get_graph_data(
            driver=driver,
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
            labels = [record["label"] for record in result if record["label"] not in ["observation_of_identity", "source", "online_identifiers", "location_identifiers", "identity_documents"]]
            
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


def get_graph_data(driver, initial_nodes, num_hops, show_nodes_only_search):
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
                MATCH (start)-[*0..{num_hops}]-(connected)
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
                    tooltip = '\n'.join(f"{k}: {v}" if not k.endswith('_identifiers') else f"{k}:\n{v}" for k, v in sorted(flat.items()))
                else:
                    value = v.get('value', v_id)

                name = v.get('name', value)
                # Use dynamic color assignment
                color = get_node_color(raw_label)

                # Check if this is an initial search node (is in the initial_nodes list)
                is_initial_search_node = any(str(init_node.get('elementId', init_node)) == v_id for init_node in initial_nodes)

                # Apply bolded color and larger border width for initial search nodes
                if is_initial_search_node:
                    color = {
                        'background': '#FFD700',  # Gold background
                        'border': '#FF4500'       # OrangeRed border
                    }
                    border_width = 4  # Larger border width for initial search nodes
                else:
                    border_width = 1  # Default border width

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
                    'properties': {**v, 'num_observations': num_observations},
                    'borderWidth': border_width
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
        final_relationship_colors = {}
        
        # Add dynamically assigned colors
        for relationship_type, color in RELATIONSHIP_COLOR_ASSIGNMENTS.items():
            final_relationship_colors[relationship_type] = color

        result = {
            'nodes': nodes,
            'relationships': formatted_relationships,
            'metadata': {
                'nodeCount': len(nodes),
                'relationshipCount': len(formatted_relationships),
                'relationshipColors': final_relationship_colors
            }
        }

        return result
    except Exception as e:
        logger.error(f"Error getting graph data: {str(e)}")
        raise Exception(f"Node query failed: {str(e)}")
    


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