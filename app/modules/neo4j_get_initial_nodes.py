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


def get_initial_nodes(driver, search_type, search_value, search_operator, node_type, num_connections_show_all_overlaps, case_sensitive_search, search_source_select, overlap_source_select1='', overlap_source_select2=''):
    try:       
        logger.info(f"get_initial_nodes called with: search_type={search_type}, overlap_source_select1='{overlap_source_select1}', overlap_source_select2='{overlap_source_select2}'")
        
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
                
                # Build Cypher query to find shared identifiers with source filtering
                # Always enter source filtering logic if either parameter is provided (even if empty)
                # This allows us to handle empty arrays as "search all sources" properly
                if overlap_source_select1 is not None or overlap_source_select2 is not None:
                    logger.info(f"Source filtering is enabled: overlap_source_select1='{overlap_source_select1}', overlap_source_select2='{overlap_source_select2}'")
                    # Parse source lists
                    primary_sources = []
                    if overlap_source_select1 and overlap_source_select1.strip():
                        primary_sources = [s.strip() for s in overlap_source_select1.split(',') if s.strip()]
                    
                    compare_sources = []
                    if overlap_source_select2 and overlap_source_select2.strip():
                        compare_sources = [s.strip() for s in overlap_source_select2.split(',') if s.strip()]
                    
                    logger.info(f"Parsed sources: primary_sources={primary_sources}, compare_sources={compare_sources}")
                    
                    # Build query with source filtering
                    # Handle different combinations: both specified, only primary, only compare, or mixed (one empty, one specified)
                    # 
                    # Logic for empty arrays:
                    # - If primary_sources=[] and compare_sources=['source1'], it means:
                    #   * Search ALL sources for primary observations
                    #   * Search only 'source1' for compare observations
                    # - If primary_sources=['source1'] and compare_sources=[], it means:
                    #   * Search only 'source1' for primary observations  
                    #   * Search ALL sources for compare observations
                    # - If both are empty (primary_sources=[] and compare_sources=[]), it means:
                    #   * Search ALL sources for primary observations
                    #   * Search ALL sources for compare observations
                    #   * This is different from "no source filtering" because it still uses the source filtering structure
                    #
                    if primary_sources and compare_sources:
                        logger.info("Using query with both primary and compare sources specified")
                        # Both primary and compare sources specified
                        query = """
                        MATCH (identifier)
                        WHERE ANY(label IN labels(identifier) WHERE label IN $identity_labels)
                        WITH identifier
                        MATCH (s1:source)-[:has_observation]->(obs1:observation_of_identity)-[r1]->(identifier)
                        WHERE s1.value IN $primary_sources
                        WITH identifier, count(DISTINCT obs1) as primary_count
                        MATCH (s2:source)-[:has_observation]->(obs2:observation_of_identity)-[r2]->(identifier)
                        WHERE s2.value IN $compare_sources
                        WITH identifier, primary_count, count(DISTINCT obs2) as compare_count
                        WITH identifier, primary_count + compare_count as total_count
                        WHERE total_count >= $min_connections
                        RETURN identifier, total_count as observation_count
                        ORDER BY observation_count DESC
                        """
                        
                        result = session.run(query, 
                                           identity_labels=identity_labels,
                                           primary_sources=primary_sources,
                                           compare_sources=compare_sources,
                                           min_connections=num_connections_show_all_overlaps)
                    elif primary_sources and not compare_sources:
                        logger.info("Using query with only primary sources specified (compare_sources is empty - search all sources for comparison)")
                        # Only primary sources specified, compare against all sources
                        query = """
                        MATCH (identifier)
                        WHERE ANY(label IN labels(identifier) WHERE label IN $identity_labels)
                        WITH identifier
                        MATCH (s1:source)-[:has_observation]->(obs1:observation_of_identity)-[r1]->(identifier)
                        WHERE s1.value IN $primary_sources
                        WITH identifier, count(DISTINCT obs1) as primary_count
                        MATCH (s2:source)-[:has_observation]->(obs2:observation_of_identity)-[r2]->(identifier)
                        WITH identifier, primary_count, count(DISTINCT obs2) as compare_count
                        WITH identifier, primary_count + compare_count as total_count
                        WHERE total_count >= $min_connections
                        RETURN identifier, total_count as observation_count
                        ORDER BY observation_count DESC
                        """
                        
                        result = session.run(query, 
                                           identity_labels=identity_labels,
                                           primary_sources=primary_sources,
                                           min_connections=num_connections_show_all_overlaps)
                    elif compare_sources and not primary_sources:
                        logger.info("Using query with only compare sources specified (primary_sources is empty - search all sources for primary)")
                        # Only compare sources specified, search all sources for primary
                        query = """
                        MATCH (identifier)
                        WHERE ANY(label IN labels(identifier) WHERE label IN $identity_labels)
                        WITH identifier
                        MATCH (s1:source)-[:has_observation]->(obs1:observation_of_identity)-[r1]->(identifier)
                        WITH identifier, count(DISTINCT obs1) as primary_count
                        MATCH (s2:source)-[:has_observation]->(obs2:observation_of_identity)-[r2]->(identifier)
                        WHERE s2.value IN $compare_sources
                        WITH identifier, primary_count, count(DISTINCT obs2) as compare_count
                        WITH identifier, primary_count + compare_count as total_count
                        WHERE total_count >= $min_connections
                        RETURN identifier, total_count as observation_count
                        ORDER BY observation_count DESC
                        """
                        
                        result = session.run(query, 
                                           identity_labels=identity_labels,
                                           compare_sources=compare_sources,
                                           min_connections=num_connections_show_all_overlaps)
                    elif not primary_sources and not compare_sources:
                        logger.info("Using query with both sides empty - search all sources for both primary and compare")
                        # Both primary and compare sources are empty - search all sources on both sides
                        query = """
                        MATCH (identifier)
                        WHERE ANY(label IN labels(identifier) WHERE label IN $identity_labels)
                        WITH identifier
                        MATCH (s1:source)-[:has_observation]->(obs1:observation_of_identity)-[r1]->(identifier)
                        WITH identifier, count(DISTINCT obs1) as primary_count
                        MATCH (s2:source)-[:has_observation]->(obs2:observation_of_identity)-[r2]->(identifier)
                        WITH identifier, primary_count, count(DISTINCT obs2) as compare_count
                        WITH identifier, primary_count + compare_count as total_count
                        WHERE total_count >= $min_connections
                        RETURN identifier, total_count as observation_count
                        ORDER BY observation_count DESC
                        """
                        
                        result = session.run(query, 
                                           identity_labels=identity_labels,
                                           min_connections=num_connections_show_all_overlaps)
                    else:
                        # This shouldn't happen given our logic above, but just in case
                        logger.warning("Unexpected state: both primary_sources and compare_sources are empty")
                        # Fall back to no source filtering
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
                else:
                    logger.info("Using query with no source filtering (all sources)")
                    logger.info("Both overlap_source_select1 and overlap_source_select2 are empty or whitespace - searching ALL sources")
                    # No source filtering - use original query
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
                if overlap_source_select1 or overlap_source_select2:
                    logger.info(f"Query used source filtering with primary_sources={primary_sources if 'primary_sources' in locals() else 'N/A'} and compare_sources={compare_sources if 'compare_sources' in locals() else 'N/A'}")
                    if 'primary_sources' in locals() and 'compare_sources' in locals():
                        if primary_sources and compare_sources:
                            logger.info(f"Search pattern: Primary sources: {primary_sources} + Compare sources: {compare_sources}")
                        elif primary_sources and not compare_sources:
                            logger.info(f"Search pattern: Primary sources: {primary_sources} + Compare sources: ALL SOURCES")
                        elif compare_sources and not primary_sources:
                            logger.info(f"Search pattern: Primary sources: ALL SOURCES + Compare sources: {compare_sources}")
                        elif not primary_sources and not compare_sources:
                            logger.info("Search pattern: Primary sources: ALL SOURCES + Compare sources: ALL SOURCES")
                        else:
                            logger.info("Search pattern: Both sides use ALL SOURCES")
                else:
                    logger.info("Query used no source filtering (searched all sources)")
                return relationships
            else:
                # Return empty graph if no search or show_overlaps is specified
                return []
    except Exception as e:
        logger.error(f"Error getting initial nodes: {str(e)}")
        raise Exception(f"Initial node query failed: {str(e)}")