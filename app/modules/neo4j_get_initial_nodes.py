from lib.constants import logger



def get_initial_nodes(driver, search_type, search_value, search_operator, node_type, num_connections_show_all_overlaps, case_sensitive_search):
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