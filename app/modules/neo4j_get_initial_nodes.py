from lib.constants import logger


def _build_search_query(node_type=None, search_operator='equals', case_sensitive=True, search_source_select=''):
    """Build Cypher query based on search parameters."""
    # Define operator mappings
    operator_map = {
        'equals': '=',
        'contains': 'CONTAINS',
        'starts_with': 'STARTS WITH',
        'ends_with': 'ENDS WITH'
    }
    
    if search_operator not in operator_map:
        raise ValueError(f"Invalid search operator: {search_operator}")
    
    operator = operator_map[search_operator]
    
    # Build the WHERE clause for the node value
    if case_sensitive:
        where_clause = f"v.value {operator} $search_value"
    else:
        where_clause = f"toLower(v.value) {operator} toLower($search_value)"
    
    # Handle source filtering
    if search_source_select and search_source_select.strip():
        # Parse comma-separated sources
        sources = [s.strip() for s in search_source_select.split(',') if s.strip()]
        
        if len(sources) == 1:
            # Single source - use direct match
            if node_type:
                query = f"""
                MATCH (s:source {{value: "{sources[0]}"}})-[:has_observation]->(o:observation_of_identity)-[:has_{node_type}]->(v:{node_type})
                WHERE {where_clause}
                RETURN v, o, s
                """
            else:
                query = f"""
                MATCH (s:source {{value: "{sources[0]}"}})-[:has_observation]->(o:observation_of_identity)-[r]->(v)
                WHERE {where_clause}
                RETURN v, o, s
                """
        else:
            # Multiple sources - use IN clause
            source_list = '[' + ', '.join([f'"{s}"' for s in sources]) + ']'
            if node_type:
                query = f"""
                MATCH (s:source)-[:has_observation]->(o:observation_of_identity)-[:has_{node_type}]->(v:{node_type})
                WHERE s.value IN {source_list} AND {where_clause}
                RETURN DISTINCT v, o, s
                """
            else:
                query = f"""
                MATCH (s:source)-[:has_observation]->(o:observation_of_identity)-[r]->(v)
                WHERE s.value IN {source_list} AND {where_clause}
                RETURN DISTINCT v, o, s
                """
    else:
        # No source filtering - search all sources
        if node_type:
            query = f"MATCH (v:{node_type}) WHERE {where_clause} RETURN v"
        else:
            query = f"MATCH (v) WHERE {where_clause} RETURN v"
    
    return query


def _convert_neo4j_node_to_dict(node, additional_fields=None):
    """Convert Neo4j node to dictionary format."""
    node_dict = dict(node)
    node_dict['id'] = node.id
    node_dict['elementId'] = node.element_id
    node_dict['labels'] = list(node.labels)
    
    if additional_fields:
        node_dict.update(additional_fields)
    
    return node_dict


def get_initial_nodes(driver, search_type, search_value, search_operator, node_type, num_connections_show_all_overlaps, case_sensitive_search, search_source_select):
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
                
                # Check if the requested node type exists
                if node_type and node_type not in available_labels:
                    logger.warning(f"Requested node type '{node_type}' not found in database. Available types: {available_labels}")
                    return []
                
                # Build and execute query
                query = _build_search_query(node_type, search_operator, case_sensitive_search, search_source_select)
                result = session.run(query, search_value=search_value)
                
                # Convert Neo4j nodes to list of dictionaries
                nodes = []
                for record in result:
                    node = record["v"]
                    node_dict = _convert_neo4j_node_to_dict(node)
                    
                    # If source filtering was used, we also have observation and source data
                    if search_source_select and search_source_select.strip():
                        if "o" in record and "s" in record:
                            obs = record["o"]
                            source = record["s"]
                            # Add source information to the node for display purposes
                            node_dict['source'] = source.get('value', 'Unknown')
                            node_dict['observation'] = obs.get('value', 'Unknown')
                            
                            # Also add the observation and source nodes to the results
                            obs_dict = _convert_neo4j_node_to_dict(obs)
                            source_dict = _convert_neo4j_node_to_dict(source)
                            nodes.extend([obs_dict, source_dict])
                    
                    nodes.append(node_dict)
                return nodes
                
            #########################################################################################
            # Show all overlaps
            #########################################################################################
            elif search_type == 'showAllOverlaps':
                logger.info("Finding identifiers with multiple observations...")
                
                # Get available labels
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
                
                # Convert results
                relationships = []
                for record in result:
                    node = record["identifier"]
                    additional_fields = {'observation_count': record["observation_count"]}
                    node_dict = _convert_neo4j_node_to_dict(node, additional_fields)
                    relationships.append(node_dict)
                
                logger.info(f"Found {len(relationships)} total shared identifiers")
                return relationships
            else:
                # Return empty graph if no search or show_overlaps is specified
                return []
    except Exception as e:
        logger.error(f"Error getting initial nodes: {str(e)}")
        raise Exception(f"Initial node query failed: {str(e)}")