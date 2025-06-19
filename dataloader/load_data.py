#! /usr/bin/env python3
'''
Used to load example data into the Neo4j graph.

To make new example data tell GPT to

Remove all data from the current file.
Given the examples in @schema_examples create 5 observations with random data in them using the given @observation_of_identity.json example.
The output should be new line delimited json objects with one observation per line.
2 of the observations should share an IP address.

'''
from concurrent.futures import ThreadPoolExecutor
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


from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import time
import json


from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import time, json

# Global variable to track created indices for end_labels
created_end_label_indices = set()
created_source_nodes = set()
created_node_values_dict = defaultdict(set)

def process_batch(driver, batch):
    """Process a batch of observations, creating nodes and relationships in bulk
       with explicit USING INDEX hints for faster relationship insertion."""
    start_time = time.time()
    try:
        with driver.session() as session:
            all_nodes = []
            all_relationships = []
            batch_end_labels = set()  # Track end_labels for this batch

            # ────────────────────────── build node / rel lists ──────────────────────────
            for observation in batch:
                # ────────────────────────── validate observation ──────────────────────────
                required_fields = ['node_type', 'id', 'source', 'observation_date']
                for f in required_fields:
                    if f not in observation:
                        logger.error(f"Observation missing required field: {f}")
                        raise Exception(f"Observation missing required field: {f}")

                # ────────────────────────── build observation properties ──────────────────────────
                obs_props = {
                    'id':  observation['id'],
                    'source': observation['source'],
                    'observation_date': observation['observation_date'],
                    'value': observation['id']
                }
                for k, v in observation.items():
                    if isinstance(v, (str, int, float, bool)):
                        obs_props[k] = v
                    elif isinstance(v, dict):
                        obs_props.update(deep_flatten(v, parent_key=k))
                    elif isinstance(v, list):
                        obs_props[k] = json.dumps(v)
                if 'metadata' in observation:
                    obs_props.update(deep_flatten(observation['metadata'], parent_key='metadata'))

                # The observation will always need
                all_nodes.append({'labels': [observation['node_type']], 'properties': obs_props})

                #Only create the source node if it doesn't already exist
                source_val = observation['source']
                if source_val not in created_source_nodes:
                    created_source_nodes.add(source_val)
                    all_nodes.append({'labels': ['source'], 'properties': {'value': source_val}})

                # Add an edge from the source node to the observation node
                all_relationships.append({
                    'start_node': {'labels': ['source'], 'properties': {'value': source_val}},
                    'end_node':   {'labels': [observation['node_type']], 'properties': {'id': observation['id']}},
                    'type':       'has_observation'
                })

                # schema-driven nodes
                for node_type, cfg in NODE_SCHEMAS.items():
                    if node_type == 'source':
                        continue
                    for node in observation.get('nodes', {}).get(node_type, []):
                        if node_type == 'names':                       # simple list
                            value, label, rel_type = node, cfg['node_type'], cfg['relationship_type']
                            node_props = {'value': value}
                        else:                                         # dict-style nodes
                            value = node.get(cfg['value_field'])
                            node_props = {k: node.get(k) for k in cfg['properties'] if k in node}
                            if cfg['node_type'] == 'dynamic':
                                label, rel_type = node.get('type'), f"has_{node.get('type')}"
                            else:
                                label, rel_type = cfg['node_type'], cfg['relationship_type']

                        # Only create the node if it doesn't already exist
                        if value not in created_node_values_dict[label]:
                            created_node_values_dict[label].add(value)
                            all_nodes.append({'labels': [label],
                                              'properties': {cfg['value_field']: value, **node_props}})

                        # Still need to create the relationship
                        all_relationships.append({
                            'start_node': {'labels': [observation['node_type']], 'properties': {'id': observation['id']}},
                            'end_node':   {'labels': [label], 'properties': {cfg['value_field']: value}},
                            'type':       rel_type
                        })

            # ──────────────────────────── bulk node merge ─────────────────────────────
            nodes_by_label = defaultdict(list)
            for n in all_nodes:
                nodes_by_label[n['labels'][0]].append(n['properties'])

            for label, nodes in nodes_by_label.items():
                logger.debug(f"Creating {len(nodes)} nodes for label {label}")
                query = f"""
                    UNWIND $rows AS props
                    MERGE (n:`{label}` {{ value: props.value }})
                    SET n += props
                    RETURN count(n)
                """
                session.run(query, rows=nodes)
            logger.debug(f"Bulk created nodes for {len(nodes_by_label)} labels")

            # ───────────────────── split relationships by type ────────────────────────
            has_obs, other_rels = [], []
            for r in all_relationships:
                if r['type'] == 'has_observation':
                    has_obs.append({'start_val': r['start_node']['properties']['value'],
                                    'end_id':   r['end_node']['properties']['id']})
                else:
                    end_label = r['end_node']['labels'][0]
                    end_key, end_val = next(iter(r['end_node']['properties'].items()))
                    batch_end_labels.add(end_label)  # Track end_label for this batch
                    other_rels.append({
                        'type':      r['type'],
                        'start_id':  r['start_node']['properties']['id'],
                        'end_label': end_label,
                        'end_key':   end_key,
                        'end_val':   end_val,
                        'properties': r.get('properties', {})
                    })

            # ─── create indices for new end_labels ───
            new_end_labels = batch_end_labels - created_end_label_indices
            if new_end_labels:
                for end_label in new_end_labels:
                    if end_label not in created_end_label_indices:
                        create_indexes(driver, [end_label])
                        created_end_label_indices.add(end_label)

            # ── fast has_observation edges (with index hints) ──
            if has_obs:
                logger.debug(f"Creating {len(has_obs)} has_observation relationships")
                session.run("""
                    UNWIND $rels AS rel
                    MATCH (start:source {value: rel.start_val})
                    MATCH (end:observation_of_identity {id: rel.end_id})
                    CREATE (start)-[:has_observation]->(end)
                    RETURN count(*)
                """, rels=has_obs)
                logger.debug(f"Created {len(has_obs)} has_observation relationships")

            # ─── group remaining rels and insert in parallel ───
            grouped = defaultdict(list)
            for r in other_rels:
                grouped[(r['type'], r['end_label'], r['end_key'])].append(r)

            def create_rel_block(rel_type, end_label, end_key, rels):
                try:
                    logger.debug(f"Creating {len(rels)} {rel_type} → {end_label}.{end_key}")
                    cypher = f"""
                        UNWIND $rels AS rel
                        MATCH (start:observation_of_identity {{id: rel.start_id}})
                        MATCH (end:{end_label} {{{end_key}: rel.end_val}})
                        CREATE (start)-[r:{rel_type}]->(end)
                        SET r += rel.properties
                        RETURN count(*)
                    """
                    with driver.session() as s:
                        s.run(cypher, rels=rels)
                    logger.debug(f"Created {len(rels)} {rel_type} → {end_label}.{end_key}")
                except Exception as e:
                    logger.error(f"Error creating {rel_type} rels: {e}")

            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = [pool.submit(create_rel_block, rt, lbl, key, rels)
                           for (rt, lbl, key), rels in grouped.items()]
                for f in futures:
                    f.result()   # raise exceptions, if any

        return len(batch), time.time() - start_time

    except Exception as e:
        logger.error(f"Error processing batch: {e}")
        raise



def create_indexes(driver, node_types):
    # Create indexes for all node types
    with driver.session() as session:
        for node_type in node_types:
            session.run(f"CREATE INDEX IF NOT EXISTS FOR (n:{node_type}) ON (n.value)")
    logger.info(f"Indexes created for {node_types}")
    

def create_constraints(driver, node_types):
    # Create constraints for all node types
    logger.debug(f"Creating constraints for {node_types}")
    with driver.session() as session:
        for node_type in node_types:
            session.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{node_type}) REQUIRE n.value IS UNIQUE")
    logger.info(f"Constraints created for {node_types}")


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
    create_constraints(driver, ['observation_of_identity', 'source'])
    create_indexes(driver, NODE_SCHEMAS.keys())


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