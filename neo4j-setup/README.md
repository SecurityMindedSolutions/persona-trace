# Neo4j Setup

This directory contains instructions and configuration for setting up a local Neo4j instance for PersonaTrace testing and development. Neo4j serves as the graph database backend for storing identity observations and their relationships, which are then visualized in the PersonaTrace web application.

## Quick Start

1. Create directories:
```bash
mkdir -p data logs conf import plugins
```

2. Start Neo4j:
### Start with no saved state
```bash
docker run -d \
  --name personatrace-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/personatrace \
  neo4j:latest
```

### Start with saved state
```bash
docker run -d \
  --name personatrace-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -v "$(pwd)/data:/data" \
  -v "$(pwd)/logs:/logs" \
  -v "$(pwd)/conf:/conf" \
  -v "$(pwd)/import:/var/lib/neo4j/import" \
  -v "$(pwd)/plugins:/plugins" \
  -e NEO4J_AUTH=neo4j/personatrace \
  neo4j:latest
```

3. Access Neo4j Browser: [http://localhost:7474](http://localhost:7474)
   - Username: `neo4j`
   - Password: `personatrace`

**Security Note**: The username `neo4j` and password `personatrace` is used as an example for development purposes only. For production use, you should change this to a strong, unique password and use a secret management system to retrieve and use it.

## Basic Docker Commands

```bash
# View logs
docker logs -f personatrace-neo4j

# Stop container
docker stop personatrace-neo4j

# Remove container
docker rm personatrace-neo4j

# Check status
docker ps -a | grep personatrace-neo4j
```

## Integration with PersonaTrace

Once Neo4j is running, you can:

1. **Load Data**: Use the [dataloader](../dataloader/README.md) to populate the database with identity observations
2. **Visualize Data**: Run the [PersonaTrace web application](../app/README.md) to explore the graph data interactively
3. **Query Data**: Use the Neo4j Browser to run Cypher queries and explore the data structure directly

