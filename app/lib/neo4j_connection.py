from neo4j import GraphDatabase
from lib.constants import NEO4J_ENDPOINT, NEO4J_USERNAME, NEO4J_PASSWORD, logger

def get_neo4j_connection():
    """
    Get a Neo4j database connection using the configured credentials.
    
    Returns:
        GraphDatabase.driver: Neo4j driver instance
    """
    try:
        driver = GraphDatabase.driver(NEO4J_ENDPOINT, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        # Test the connection
        with driver.session() as session:
            session.run("RETURN 1")
        logger.info("Connected to Neo4j successfully!")
        return driver
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {str(e)}")
        logger.error(f"Endpoint: {NEO4J_ENDPOINT}, Username: {NEO4J_USERNAME}")
        raise 