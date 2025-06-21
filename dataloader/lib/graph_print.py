#! /usr/bin/env python3

import json

# Import internal libs
from lib.constants import logger


def print_graph_summary(driver):
    """Print a summary of the graph data"""
    try:
        with driver.session() as session:
            # Get node count
            node_count_result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = node_count_result.single()['count']
            
            # Get relationship count
            relationship_count_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            relationship_count = relationship_count_result.single()['count']
            
            # Get node types and counts
            node_types_result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY label ASC
            """)
            node_types = {record['label']: record['count'] for record in node_types_result}
            
            # Get relationship types and counts
            relationship_types_result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY type ASC
            """)
            relationship_types = {record['type']: record['count'] for record in relationship_types_result}
            
            summary = f"""Graph Summary
Nodes: {node_count}
Relationships: {relationship_count}

Node Types:
{json.dumps(node_types, indent=2)}

Relationship Types:
{json.dumps(relationship_types, indent=2)}
"""
            logger.info(summary)
    except Exception as e:
        logger.error(f"Error getting graph summary: {str(e)}")