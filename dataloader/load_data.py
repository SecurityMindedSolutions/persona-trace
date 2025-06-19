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
import time
from pathlib import Path
from collections import defaultdict

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
    # Node schemas
    NODE_SCHEMAS,
    # Batch configuration
    BATCH_SIZE,
)
from lib.graph_print import print_graph_summary
from lib.json_operations import deep_flatten
from lib.file_operations import get_all_files


def create_indexes(driver):
    # Create indexes for all node types
    with driver.session() as session:
        for node_type in NODE_SCHEMAS.keys():
            session.run(f"CREATE INDEX IF NOT EXISTS FOR (n:{node_type}) ON (n.value)")
    logger.info("Indexes created for all node types")

def process_batch(driver, batch):
    """Process a batch of observations, creating nodes and relationships in bulk"""
    start_time = time.time()
    try:
        with driver.session() as session:
            all_nodes = []
            all_relationships = []

            for observation in batch:
                # --- Validate required fields ---
                required_fields = ['node_type', 'id', 'source', 'observation_date']
                for field in required_fields:
                    if field not in observation:
                        logger.error(f"Observation missing required field: {field}")
                        raise Exception(f"Observation missing required field: {field}")

                # --- Build observation node ---
                obs_properties = {
                    'id': observation['id'],
                    'source': observation['source'],
                    'observation_date': observation['observation_date'],
                    'value': observation['id']
                }

                for key, value in observation.items():
                    if isinstance(value, (str, int, float, bool)):
                        obs_properties[key] = value
                    elif isinstance(value, dict):
                        obs_properties.update(deep_flatten(value, parent_key=key))
                    elif isinstance(value, list):
                        obs_properties[key] = json.dumps(value)

                if 'metadata' in observation:
                    obs_properties.update(deep_flatten(observation['metadata'], parent_key='metadata'))

                all_nodes.append({
                    'labels': [observation['node_type']],
                    'properties': obs_properties
                })

                # --- Source node and relationship ---
                source_val = observation['source']
                all_nodes.append({
                    'labels': ['source'],
                    'properties': {'value': source_val}
                })
                all_relationships.append({
                    'start_node': {'labels': ['source'], 'properties': {'value': source_val}},
                    'end_node': {'labels': [observation['node_type']], 'properties': {'id': observation['id']}},
                    'type': 'has_observation'
                })

                # --- Other node types from schema ---
                for node_type, config in NODE_SCHEMAS.items():
                    if node_type == 'source':
                        continue
                    values = observation.get('vertices', {}).get(node_type, [])
                    for node in values:
                        if node_type == 'names':
                            value = node
                            node_props = {'value': value}
                            label = config['node_type']
                            rel_type = config['relationship_type']
                        else:
                            value = node.get(config['value_field'])
                            node_props = {k: node.get(k) for k in config['properties'] if k in node}
                            if config['node_type'] == 'dynamic':
                                label = node.get('type')
                                rel_type = f"has_{label}"
                            else:
                                label = config['node_type']
                                rel_type = config['relationship_type']

                        all_nodes.append({
                            'labels': [label],
                            'properties': {config['value_field']: value, **node_props}
                        })
                        all_relationships.append({
                            'start_node': {'labels': [observation['node_type']], 'properties': {'id': observation['id']}},
                            'end_node': {'labels': [label], 'properties': {config['value_field']: value}},
                            'type': rel_type
                        })

            # --- Bulk node creation ---
            nodes_by_label = defaultdict(list)
            for node in all_nodes:
                label = node['labels'][0]
                nodes_by_label[label].append(node['properties'])

            bulk_node_data = [
                {"label": label, "props": props}
                for label, props_list in nodes_by_label.items()
                for props in props_list
            ]

            node_query = """
            UNWIND $data as row
            CALL apoc.merge.node([row.label], row.props) YIELD node
            SET node += row.props
            """
            session.run(node_query, data=bulk_node_data)
            logger.debug(f"Bulk created {len(bulk_node_data)} nodes total")

            # --- Bulk relationship creation ---
            has_obs_rels = []
            obs_to_entity_rels = []
            for rel in all_relationships:
                if rel['type'] == 'has_observation':
                    has_obs_rels.append({
                        'start_val': rel['start_node']['properties']['value'],
                        'end_id': rel['end_node']['properties']['id']
                    })
                else:
                    end_label = rel['end_node']['labels'][0]
                    end_key, end_val = list(rel['end_node']['properties'].items())[0]
                    obs_to_entity_rels.append({
                        'type': rel['type'],
                        'start_id': rel['start_node']['properties']['id'],
                        'end_label': end_label,
                        'end_key': end_key,
                        'end_val': end_val,
                        'properties': rel.get('properties', {})
                    })

            if has_obs_rels:
                rel_query = """
                UNWIND $rels as rel
                MATCH (start:source {value: rel.start_val})
                MATCH (end:observation_of_identity {id: rel.end_id})
                CREATE (start)-[:has_observation]->(end)
                """
                session.run(rel_query, rels=has_obs_rels)

            grouped = defaultdict(list)
            for rel in obs_to_entity_rels:
                key = (rel['type'], rel['end_label'], rel['end_key'])
                grouped[key].append(rel)

            for (rel_type, end_label, end_key), rels in grouped.items():
                rel_query = f"""
                UNWIND $rels as rel
                MATCH (start:observation_of_identity {{id: rel.start_id}})
                MATCH (end:{end_label} {{{end_key}: rel.end_val}})
                CREATE (start)-[r:{rel_type}]->(end)
                SET r += rel.properties
                """
                session.run(rel_query, rels=rels)

        processing_time = time.time() - start_time
        return len(batch), processing_time

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
        if args.clear_graph:
            confirmation = input("Are you sure you want to clear all graph data? This cannot be undone. (y/N): ")
            if confirmation.lower() == 'y':
                with console.status("[bold green]Clearing existing graph data...", spinner="dots") as status:
                    with driver.session() as session:
                        # Drop all constraints
                        result = session.run("SHOW CONSTRAINTS")
                        for record in result:
                            name = record["name"]
                            session.run(f"DROP CONSTRAINT {name}")

                        # Drop all indexes
                        result = session.run("SHOW INDEXES")
                        for record in result:
                            name = record["name"]
                            session.run(f"DROP INDEX {name}")

                        # Delete all nodes and relationships
                        session.run("MATCH (n) DETACH DELETE n")

                logger.info("Graph cleared successfully - all data, constraints, and indexes removed.")
            else:
                logger.info("Graph clearing cancelled by user.")
        else:
            logger.info("Skipping graph clearing")
    except Exception as e:
        logger.error(f"Error clearing graph data: {str(e)}")
        raise

    ################################################################################################
    # Create indexes
    ################################################################################################
    create_indexes(driver)

    ################################################################################################
    # Process each file 
    ################################################################################################
    for observations_file in files:
        logger.info(f"Processing file: {observations_file}")
    
        try:
            # Process observations in batches
            current_batch = []
            batch_counter = 0
            total_start_time = time.time()
            total_processed = 0
            
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
                            num_nodes, processing_time = process_batch(driver, current_batch)
                            total_processed += num_nodes
                            
                            # Calculate ETA
                            elapsed_time = time.time() - total_start_time
                            avg_time_per_observation = elapsed_time / total_processed
                            remaining_observations = num_lines - total_processed
                            eta_seconds = remaining_observations * avg_time_per_observation
                            
                            # Format ETA
                            if eta_seconds < 60:
                                eta_str = f"{eta_seconds:.1f}s"
                            elif eta_seconds < 3600:
                                eta_str = f"{eta_seconds/60:.1f}m"
                            else:
                                eta_str = f"{eta_seconds/3600:.1f}h"
                            
                            # Calculate average insertions per second
                            insertions_per_second = total_processed / elapsed_time
                            
                            logger.info(f"Successfully processed batch of {num_nodes} observations in {processing_time:.2f}s. "
                                      f"Avg: {insertions_per_second:.1f} obs/sec. ETA: {eta_str}")
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
                    num_nodes, processing_time = process_batch(driver, current_batch)
                    total_processed += num_nodes
                    
                    # Calculate final stats
                    elapsed_time = time.time() - total_start_time
                    insertions_per_second = total_processed / elapsed_time
                    
                    logger.info(f"Successfully processed final batch of {num_nodes} observations in {processing_time:.2f}s. "
                              f"Total: {total_processed} observations in {elapsed_time:.2f}s. "
                              f"Final avg: {insertions_per_second:.1f} obs/sec")
            
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