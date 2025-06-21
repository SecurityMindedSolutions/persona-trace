#! /usr/bin/env python3
from lib.constants import DELETION_BATCH_SIZE, logger, console
import time


def delete_graph(driver):
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        
        with driver.session() as session:
            # Drop all constraints
            with console.status("[bold red]Dropping constraints...", spinner="dots") as status:
                result = session.run("SHOW CONSTRAINTS")
                constraints = list(result)
                for record in constraints:
                    name = record["name"]
                    session.run(f"DROP CONSTRAINT {name}")

            # Drop all indexes
            with console.status("[bold red]Dropping indexes...", spinner="dots") as status:
                result = session.run("SHOW INDEXES")
                indexes = list(result)
                for record in indexes:
                    name = record["name"]
                    session.run(f"DROP INDEX {name}")

            # Delete all relationships first, then nodes in batches
            # Delete relationships
            rel_total_deleted = 0
            rel_batch_number = 0
            rel_start_time = time.time()
            
            # Calculate total relationship batches upfront
            initial_rel_count_result = session.run("MATCH ()-[r]->() RETURN count(r) as total")
            initial_rel_count = initial_rel_count_result.single()['total']
            total_rel_batches = (initial_rel_count + DELETION_BATCH_SIZE - 1) // DELETION_BATCH_SIZE if initial_rel_count > 0 else 0
            
            while True:
                # Check if there are any relationships remaining
                rel_count_result = session.run("MATCH ()-[r]->() RETURN count(r) as total")
                remaining_rels = rel_count_result.single()['total']
                
                if remaining_rels == 0:
                    break  # No more relationships to delete
                
                rel_batch_number += 1
                rel_batch_start_time = time.time()
                
                # Calculate batch size for relationships
                current_rel_batch_size = min(DELETION_BATCH_SIZE, remaining_rels)
                
                # Show spinner for current relationship batch
                with console.status(f"[bold red]Deleting relationship batch {rel_batch_number} of {total_rel_batches}...", spinner="dots") as status:
                    # Delete a batch of relationships
                    result = session.run("""
                        MATCH ()-[r]->()
                        WITH r LIMIT $batch_size 
                        DELETE r
                        RETURN count(r) as deleted
                    """, batch_size=current_rel_batch_size)
                    
                    deleted_count = result.single()['deleted']
                    rel_total_deleted += deleted_count
                    
                    # Calculate progress and timing
                    batch_time = time.time() - rel_batch_start_time
                    rels_per_second = deleted_count / batch_time if batch_time > 0 else 0
                                
            rel_total_time = time.time() - rel_start_time
            avg_rels_per_second = rel_total_deleted / rel_total_time if rel_total_time > 0 else 0

            # Delete nodes
            total_deleted = 0
            batch_number = 0
            start_time = time.time()
            
            # Calculate total node batches upfront
            initial_node_count_result = session.run("MATCH (n) RETURN count(n) as total")
            initial_node_count = initial_node_count_result.single()['total']
            total_node_batches = (initial_node_count + DELETION_BATCH_SIZE - 1) // DELETION_BATCH_SIZE if initial_node_count > 0 else 0
            
            while True:
                # Check if there are any nodes remaining
                count_result = session.run("MATCH (n) RETURN count(n) as total")
                remaining_nodes = count_result.single()['total']
                
                if remaining_nodes == 0:
                    break  # No more nodes to delete
                
                batch_number += 1
                batch_start_time = time.time()
                
                # Calculate batch size (use smaller batch if remaining nodes is less than batch size)
                current_batch_size = min(DELETION_BATCH_SIZE, remaining_nodes)
                
                # Show spinner for current node batch
                with console.status(f"[bold red]Deleting node batch {batch_number} of {total_node_batches}...", spinner="dots") as status:
                    # Delete a batch of nodes
                    result = session.run("""
                        MATCH (n) 
                        WITH n LIMIT $batch_size 
                        DELETE n
                        RETURN count(n) as deleted
                    """, batch_size=current_batch_size)
                    
                    deleted_count = result.single()['deleted']
                    total_deleted += deleted_count
                    
                    # Calculate progress and timing
                    batch_time = time.time() - batch_start_time
                    nodes_per_second = deleted_count / batch_time if batch_time > 0 else 0
            
            total_time = time.time() - start_time
            avg_nodes_per_second = total_deleted / total_time if total_time > 0 else 0

        # Check if deletion was complete
        with console.status("[bold green]Checking deletion status...", spinner="dots") as status:
            with driver.session() as session:
                # Check remaining constraints
                remaining_constraints_result = session.run("SHOW CONSTRAINTS")
                remaining_constraints = len(list(remaining_constraints_result))
                
                # Check remaining indexes
                remaining_indexes_result = session.run("SHOW INDEXES")
                remaining_indexes = len(list(remaining_indexes_result))
                
                # Check remaining nodes
                remaining_nodes_result = session.run("MATCH (n) RETURN count(n) as count")
                remaining_nodes = remaining_nodes_result.single()['count']
                
                # Check remaining relationships
                remaining_rels_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                remaining_rels = remaining_rels_result.single()['count']
                
                # If everything is deleted, we're done
                if remaining_constraints == 0 and remaining_indexes == 0 and remaining_nodes == 0 and remaining_rels == 0:
                    logger.info("Graph cleared successfully - all data, constraints, and indexes removed.")
                    return
                
                # If this was the last attempt, throw an error
                if attempt >= max_attempts:
                    logger.error(f"Deletion failed after {max_attempts} attempts!")
                    logger.error(f"Final state: {remaining_constraints} constraints, {remaining_indexes} indexes, "
                               f"{remaining_nodes} nodes, {remaining_rels} relationships")
                    raise Exception(f"Graph not fully cleared after {max_attempts} attempts. "
                                  f"Remaining: {remaining_constraints} constraints, {remaining_indexes} indexes, "
                                  f"{remaining_nodes} nodes, {remaining_rels} relationships")
                
                # Otherwise, continue to next attempt
                logger.warning(f"Deletion incomplete, retrying... (attempt {attempt + 1}/{max_attempts})")
