# Neo4j Setup

This directory contains instructions and configuration for setting up a local Neo4j instance for PersonaTrace testing and development. Neo4j serves as the graph database backend for storing identity observations and their relationships, which are then visualized in the PersonaTrace web application.

## Quick Start

**Important**: PersonaTrace requires the APOC plugin for bulk insertions. Use the provided setup script to ensure proper installation. There are heap configurations in the conf file insertion that you may want to change depending on the machine you are using.

1. From the folder you want your Neo4j data and configurations stored, run the Neo4j setup script:
```bash
chmod +x neo4j-setup.sh
sudo ./neo4j-setup.sh
```

This script will:
- Create the necessary directories
- Start Neo4j with the required APOC plugin installed
- Configure the database for optimal performance with PersonaTrace

2. Access Neo4j Browser: [http://localhost:7474](http://localhost:7474)
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

