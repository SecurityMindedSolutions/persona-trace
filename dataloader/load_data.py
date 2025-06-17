#! /usr/bin/env python3
'''
Used to load example data into the Neo4j graph.

To make new example data tell GPT to

Remove all data from the current file.
Given the examples in @schema_examples create 5 observations with random data in them using the given @observation_of_identity.json example.
The output should be new line delimited json objects with one observation per line.
2 of the observations should share an IP address.

'''

from neo4j import GraphDatabase
import json
from pathlib import Path

# Import internal libs
from lib.constants import (
    # Internal vars
    args,
    logger,
    console,
    # Data sources
    EXAMPLE_DATA_FOLDER,
    LIVE_DATA_FOLDER,
    # Database targets
    NEO4J_ENDPOINT,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
    # Vertex schemas
    VERTEX_SCHEMAS,
    # Batch configuration
    BATCH_SIZE,
)
from lib.graph_print import print_graph_summary
from lib.json_operations import deep_flatten
from lib.file_operations import get_all_files


def process_batch(driver, batch):
    """Process a batch of observations, creating vertices and edges"""
    try:
        with driver.session() as session:
            for observation in batch:
                ############################################################################################
                # Required field validation
                ############################################################################################
                # Check that the observation has all required fields
                required_fields = ['vertex_type', 'id', 'source', 'observation_date']
                for field in required_fields:
                    if field not in observation:
                        logger.error(f"Observation missing required field: {field}")
                        raise Exception(f"Observation missing required field: {field}")
                    

                ############################################################################################
                # Process observation vertex
                ############################################################################################
                # Create observation vertex with all properties
                obs_properties = {
                    'id': observation['id'],
                    'source': observation['source'],
                    'observation_date': observation['observation_date'],
                    'value': observation['id']  # Use ID as the value for observations
                }
                
                # Add all properties from the observation to the vertex
                for key, value in observation.items():
                    if isinstance(value, (str, int, float, bool)):
                        obs_properties[key] = value
                    elif isinstance(value, dict):
                        flat_dict = deep_flatten(value, parent_key=key)
                        obs_properties.update(flat_dict)
                    elif isinstance(value, list):
                        obs_properties[key] = json.dumps(value)
                
                # Add all metadata properties to the observation vertex
                if 'metadata' in observation:
                    flat_metadata = deep_flatten(observation['metadata'], parent_key='metadata')
                    obs_properties.update(flat_metadata)
                    logger.debug(f"Added metadata properties to observation vertex")
                
                # Create the observation vertex
                create_obs_query = f"""
                CREATE (o:{observation['vertex_type']} $properties)
                RETURN o
                """
                result = session.run(create_obs_query, properties=obs_properties)
                observation_vertex = result.single()['o']
                logger.debug(f"Created observation vertex: {observation_vertex['id']}")

                ############################################################################################
                # Create source vertex from observation's source field
                ############################################################################################
                # Create source vertex
                source_value = observation['source']
                source_properties = {'value': source_value}
                
                # Merge source vertex (create if doesn't exist)
                merge_source_query = """
                MERGE (s:source {value: $value})
                SET s += $properties
                RETURN s
                """
                session.run(merge_source_query, value=source_value, properties=source_properties)
                
                # Create edge FROM source TO observation
                create_source_edge_query = """
                MATCH (s:source {value: $source_value})
                MATCH (o:observation_of_identity {id: $obs_id})
                MERGE (s)-[r:has_observation]->(o)
                RETURN r
                """
                session.run(create_source_edge_query, source_value=source_value, obs_id=observation['id'])
                logger.debug(f"Created source vertex and edge: {source_value} -> {observation['id']}")

                ############################################################################################
                # Process other vertices and edges
                ############################################################################################
                for vertex_type, config in VERTEX_SCHEMAS.items():
                    # Skip source vertices as they're handled above
                    if vertex_type == 'source':
                        continue
                        
                    # Only process vertices that are in the observation
                    if vertex_type in observation['vertices']:
                        for vertex in observation['vertices'][vertex_type]:
                            # Handle different vertex types
                            if vertex_type == 'names':
                                # Names are just strings, not objects
                                value = vertex  # vertex is the string value
                                vertex_properties = {'value': value}
                                actual_vertex_type = config['vertex_type']
                                actual_edge_type = config['edge_type']
                            else:
                                # Other vertex types are objects with properties
                                value = vertex[config['value_field']]
                                vertex_properties = {}
                                for prop in config['properties']:
                                    if prop in vertex:
                                        vertex_properties[prop] = vertex[prop]
                                    elif prop == config['value_field']:
                                        vertex_properties[prop] = value
                                
                                # Handle dynamic vertex types
                                if config['vertex_type'] == 'dynamic':
                                    actual_vertex_type = vertex['type']
                                    actual_edge_type = f"has_{vertex['type']}"
                                else:
                                    actual_vertex_type = config['vertex_type']
                                    actual_edge_type = config['edge_type']
                            
                            # Merge vertex (create if doesn't exist)
                            merge_vertex_query = f"""
                            MERGE (v:{actual_vertex_type} {{ {config['value_field']}: $value }})
                            SET v += $properties
                            RETURN v
                            """
                            session.run(merge_vertex_query, value=value, properties=vertex_properties)
                            
                            # Create edge FROM observation TO vertex
                            create_edge_query = f"""
                            MATCH (o:{observation['vertex_type']} {{id: $obs_id}})
                            MATCH (v:{actual_vertex_type} {{ {config['value_field']}: $value }})
                            MERGE (o)-[r:{actual_edge_type}]->(v)
                            RETURN r
                            """
                            session.run(create_edge_query, obs_id=observation['id'], value=value)
                
            logger.info(f"Successfully processed batch of {len(batch)} observations")
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        raise


def main():
    ################################################################################################
    # Connect to Neo4j
    ################################################################################################
    try:
        driver = GraphDatabase.driver(NEO4J_ENDPOINT, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        # Test the connection
        with driver.session() as session:
            session.run("RETURN 1")
        logger.info("Connected to Neo4j successfully!")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {str(e)}")
        logger.error(f"Endpoint: {NEO4J_ENDPOINT}, Username: {NEO4J_USERNAME}")
        raise

    ################################################################################################
    # Get files to process
    ################################################################################################
    if args.example_data:
        logger.info(f"Loading example data from {EXAMPLE_DATA_FOLDER}")
        files = get_all_files(EXAMPLE_DATA_FOLDER)
    elif args.live_data:
        logger.info(f"Loading live data from {LIVE_DATA_FOLDER}")
        files = get_all_files(LIVE_DATA_FOLDER)
    else:
        logger.error("No data source specified")
        return
    logger.info(f"Found {len(files)} file(s) to process")
    if not files:
        logger.error("No files found to process")
        return

    ################################################################################################
    # Clear the graph
    ################################################################################################
    try:
        with console.status("[bold green]Clearing existing graph data...", spinner="dots") as status:
            with driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
        logger.info("Graph cleared successfully")
    except Exception as e:
        logger.error(f"Error clearing graph data: {str(e)}")
        raise

    # Process each file
    for observations_file in files:
        logger.info(f"Processing file: {observations_file}")
    
        try:
            # Process observations in batches
            current_batch = []
            batch_counter = 0
            with open(observations_file, 'r') as f:
                # Count the number of lines in the file
                num_lines = sum(1 for _ in f)
                f.seek(0)  # Reset file pointer to the beginning
                # Calculate total number of batches (ceiling division)
                total_batches = (num_lines + BATCH_SIZE - 1) // BATCH_SIZE

                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    
                    try:
                        observation = json.loads(line.strip())
                        current_batch.append(observation)
                        
                        if len(current_batch) >= BATCH_SIZE:
                            batch_counter += 1
                            start_obs = (batch_counter - 1) * BATCH_SIZE + 1
                            end_obs = min(batch_counter * BATCH_SIZE, num_lines)
                            logger.info(f"Processing batch {batch_counter}/{total_batches} (observations {start_obs}-{end_obs} of {num_lines})...")
                            process_batch(driver, current_batch)
                            current_batch = []
                            
                    except json.JSONDecodeError as je:
                        logger.error(f"JSON decode error on line {line_num}: {str(je)}")
                        logger.error(f"Line content: {repr(line)}")
                        raise
                    except Exception as e:
                        logger.error(f"Error processing line {line_num}: {str(e)}")
                        raise
                
                # Process any remaining observations
                if current_batch:
                    batch_counter += 1
                    start_obs = (batch_counter - 1) * BATCH_SIZE + 1
                    end_obs = num_lines
                    logger.info(f"Processing final batch {batch_counter}/{total_batches} (observations {start_obs}-{end_obs} of {num_lines})...")
                    process_batch(driver, current_batch)
            
            # Print summary
            logger.info("Final Graph State:")
            print_graph_summary(driver)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(traceback.format_exc())

    ################################################################################################
    # Close the connection to Neo4j
    ################################################################################################
    if 'driver' in locals():
        driver.close()
        logger.info("Disconnected from Neo4j successfully!")


if __name__ == "__main__":
    main() 