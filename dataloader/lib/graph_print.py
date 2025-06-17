#! /usr/bin/env python3

import json

# Import internal libs
from lib.constants import logger


def print_graph_summary(driver):
    """Print a summary of the graph data"""
    try:
        with driver.session() as session:
            # Get vertex count
            vertex_count_result = session.run("MATCH (n) RETURN count(n) as count")
            vertex_count = vertex_count_result.single()['count']
            
            # Get edge count
            edge_count_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            edge_count = edge_count_result.single()['count']
            
            # Get vertex types and counts
            vertex_types_result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY count DESC
            """)
            vertex_types = {record['label']: record['count'] for record in vertex_types_result}
            
            # Get edge types and counts
            edge_types_result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """)
            edge_types = {record['type']: record['count'] for record in edge_types_result}
            
            summary = f"""Graph Summary
Vertices: {vertex_count}
Edges: {edge_count}

Vertex Types:
{json.dumps(vertex_types, indent=2)}

Edge Types:
{json.dumps(edge_types, indent=2)}
"""
            logger.info(summary)
    except Exception as e:
        logger.error(f"Error getting graph summary: {str(e)}")