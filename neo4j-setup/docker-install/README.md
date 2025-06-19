# Docker Installation for Neo4j

This folder contains the Docker-based installation for Neo4j, which is the **recommended approach** for most users.

## Prerequisites

- Docker installed on your system
- Docker daemon running
- At least 8GB of available RAM (4GB for Neo4j + system overhead)

## Quick Installation

1. **Navigate to this directory**:
   ```bash
   cd docker-install
   ```

2. **Make the script executable**:
   ```bash
   chmod +x neo4j-install-docker.sh
   ```

3. **Run the installation script**:
   ```bash
   ./neo4j-install-docker.sh
   ```

The script will:
- Stop and remove any existing Neo4j container
- Create necessary directories (`conf`, `data`, `logs`, `import`)
- Configure Neo4j with optimized settings for PersonaTrace
- Start the Neo4j container
- Set up firewall rules (optional)
- Verify the installation

## What Gets Created

The script creates the following directory structure in the current folder:

```
./
├── conf/           # Neo4j configuration files
├── data/           # Database files (persistent)
├── logs/           # Neo4j logs
├── import/         # Import directory for data files
└── neo4j-install-docker.sh
```

## Configuration

The default configuration includes:
- **Memory**: 4GB initial heap, 6GB max heap, 2GB page cache
- **Ports**: 7474 (HTTP), 7687 (Bolt)
- **Authentication**: neo4j/personatrace
- **Network**: Accessible from any IP (0.0.0.0)

## Accessing Neo4j

- **Neo4j Browser**: http://localhost:7474
- **Bolt Connection**: bolt://localhost:7687
- **Credentials**: neo4j / personatrace

## Management Commands

### View Logs
```bash
docker logs -f personatrace-neo4j
```

### Stop Neo4j
```bash
docker stop personatrace-neo4j
```

### Start Neo4j
```bash
docker start personatrace-neo4j
```

### Remove Container (keeps data)
```bash
docker rm personatrace-neo4j
```

### Remove Container and Data
```bash
docker stop personatrace-neo4j
docker rm personatrace-neo4j
rm -rf data logs conf import
```

### Check Status
```bash
docker ps -a | grep personatrace-neo4j
```

## Troubleshooting

### Container Won't Start
```bash
# Check Docker logs
docker logs personatrace-neo4j

# Check if ports are in use
netstat -tulpn | grep -E '7474|7687'

# Restart Docker daemon if needed
sudo systemctl restart docker
```

### Can't Connect to Neo4j
```bash
# Check if container is running
docker ps | grep personatrace-neo4j

# Test connection from inside container
docker exec -it personatrace-neo4j cypher-shell -u neo4j -p personatrace "RETURN 1"

# Check firewall settings
sudo ufw status
```

### Performance Issues
- Increase memory allocation in `conf/neo4j.conf`
- Check available system memory: `free -h`
- Monitor container resource usage: `docker stats personatrace-neo4j`

### Data Persistence
- Data is stored in the `./data` directory
- To backup: `cp -r data/ backup-data/`
- To restore: `cp -r backup-data/ data/`

## Customization

### Change Memory Settings
Edit `conf/neo4j.conf`:
```bash
# Increase heap size for larger datasets
dbms.memory.heap.initial_size=8g
dbms.memory.heap.max_size=12g
dbms.memory.pagecache.size=4g
```

### Change Password
```bash
# Stop container
docker stop personatrace-neo4j

# Remove container
docker rm personatrace-neo4j

# Edit script to change NEO4J_PASSWORD variable
# Re-run installation script
./neo4j-install-docker.sh
```

### Add Plugins
1. Create a `plugins` directory
2. Add plugin JAR files
3. Mount the directory in the Docker run command
4. Update Neo4j configuration

## Security Notes

- Default credentials are for development only
- For production: change password and restrict network access
- Consider using Docker secrets for credential management
- Regularly update Neo4j version for security patches

## Next Steps

Once Neo4j is running:
1. Load data using the [dataloader](../../dataloader/README.md)
2. Start the [PersonaTrace application](../../app/README.md)
3. Explore data in the Neo4j Browser 