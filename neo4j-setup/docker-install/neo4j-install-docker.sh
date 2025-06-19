#!/bin/bash

set -euo pipefail

# === CONFIGURATION ===
NEO4J_VERSION="5.21.0"
CONTAINER_NAME="personatrace-neo4j"
NEO4J_PASSWORD="personatrace"

# === CLEAN START ===
echo "[+] Stopping and removing existing container (if any)..."
docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true

# === DIRECTORY SETUP ===
echo "[+] Creating directories..."
mkdir -p conf data logs import
chmod -R 755 conf data logs import

# === NEO4J CONFIGURATION ===
echo "[+] Writing conf/neo4j.conf..."
cat > conf/neo4j.conf <<EOF
server.directories.plugins=/var/lib/neo4j/plugins
server.memory.heap.initial_size=4g
server.memory.heap.max_size=6g
server.memory.pagecache.size=2g
server.default_listen_address=0.0.0.0
EOF

# === FIX FILE OWNERSHIP FOR DOCKER ===
echo "[+] Setting permissions for Docker access..."
sudo chown -R 1000:1000 data logs import conf || true

# === START NEO4J CONTAINER ===
echo "[+] Starting Neo4j container..."
docker run -d \
  --name "$CONTAINER_NAME" \
  -p 7474:7474 \
  -p 7687:7687 \
  -v "$(pwd)/data:/data" \
  -v "$(pwd)/logs:/logs" \
  -v "$(pwd)/conf:/conf" \
  -v "$(pwd)/import:/var/lib/neo4j/import" \
  -e NEO4J_AUTH=neo4j/"$NEO4J_PASSWORD" \
  neo4j:"$NEO4J_VERSION"

# === WAIT AND VERIFY ===
echo "[+] Waiting for Neo4j to initialize..."
sleep 12

# === Check if for ufw setup ===
read -p "Do you want to setup ufw to allow incoming connections to Neo4j? (y/n) " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Check if ufw is installed
    if ! command -v ufw &> /dev/null; then
        echo "ufw is not installed. Installing it now..."
        sudo apt-get update
        sudo apt-get install ufw
        sudo ufw enable
        echo "ufw is now installed and configured to allow incoming connections to Neo4j."
    fi
    # Allow incoming connections to Neo4j
    echo "Allowing incoming connections to Neo4j..."
    sudo ufw allow 7474/tcp
    sudo ufw allow 7687/tcp
fi

echo "[+] Verifying Neo4j connection..."
if docker exec -it "$CONTAINER_NAME" cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "RETURN 1" 2>/dev/null; then
    echo "[✓] Neo4j is ready!"
    echo "[✓] Access Neo4j at http://localhost:7474 (neo4j / $NEO4J_PASSWORD)"
    echo "[✓] Bolt connection: bolt://localhost:7687"
else
    echo "[!] Neo4j verification failed. Check Docker logs with: docker logs $CONTAINER_NAME"
    exit 1
fi