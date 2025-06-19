# Neo4j Setup

This directory contains instructions and configuration for setting up a local Neo4j instance for PersonaTrace testing and development. Neo4j serves as the graph database backend for storing identity observations and their relationships, which are then visualized in the PersonaTrace web application.

## ⚠️ Security Notice

**Default credentials are for development purposes only.**
- **Username**: `neo4j`
- **Password**: `personatrace`

For production use, change to a strong, unique password and use proper secret management.

## Installation Options

### 🐳 Docker Installation (Recommended)

**Prerequisites**: Docker installed on your system

**Note**: The folder you run the script from will store persistent db and config data. So, you may want to move it out of the docker-install folder

**Installation Script**: [docker-install/neo4j-install-docker.sh](docker-install/neo4j-install-docker.sh)

**Quick Start**:
```bash
cd docker-install
chmod +x neo4j-install-docker.sh
./neo4j-install-docker.sh
```

**Management Commands**:
```bash
# View logs
docker logs -f personatrace-neo4j

# Stop container
docker stop personatrace-neo4j

# Start container
docker start personatrace-neo4j

# Remove container
docker rm personatrace-neo4j

# Check status
docker ps -a | grep personatrace-neo4j
```

### 🐧 Ubuntu Installation

**Prerequisites**: Ubuntu/Debian-based system with sudo privileges

**Installation Script**: [ubuntu-install/neo4j-install-ubuntu.sh](ubuntu-install/neo4j-install-ubuntu.sh)

**Quick Start**:
```bash
cd ubuntu-install
chmod +x neo4j-install-ubuntu.sh
sudo ./neo4j-install-ubuntu.sh
```

**Management Commands**:
```bash
# Start Neo4j service
sudo systemctl start neo4j

# Stop Neo4j service
sudo systemctl stop neo4j

# Restart Neo4j service
sudo systemctl restart neo4j

# Check status
sudo systemctl status neo4j

# View logs
sudo journalctl -u neo4j -f

# Enable auto-start on boot
sudo systemctl enable neo4j
```

## Accessing Neo4j

Once installed, access Neo4j Browser at: [http://localhost:7474](http://localhost:7474)
- **Bolt Connection**: bolt://localhost:7687

## Integration with PersonaTrace

Once Neo4j is running, you can:

1. **Load Data**: Use the [dataloader](../dataloader/README.md) to populate the database with identity observations
2. **Visualize Data**: Run the [PersonaTrace web application](../app/README.md) to explore the graph data interactively
3. **Query Data**: Use the Neo4j Browser to run Cypher queries and explore the data structure directly

## Configuration

Both installation methods include optimized configurations for PersonaTrace:
- Memory settings tuned for graph operations
- Network access configured for local development
- Performance optimizations for bulk data loading

For custom configurations, see the respective installation folder documentation.

