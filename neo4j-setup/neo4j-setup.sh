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
mkdir -p conf data logs import plugins
chmod -R 755 conf data logs import plugins

# === DOWNLOAD APOC ===
echo "[+] Downloading verified APOC plugin for Neo4j $NEO4J_VERSION..."
rm -f plugins/apoc.jar
curl -L -o plugins/apoc.jar "https://github.com/neo4j/apoc/releases/download/${NEO4J_VERSION}/apoc-${NEO4J_VERSION}-core.jar"

# Confirm it's a valid JAR
if ! file plugins/apoc.jar | grep -qE "Java archive|Zip archive"; then
    echo "[!] ERROR: plugins/apoc.jar is not a valid JAR file. Download may have failed."
    exit 1
fi

# === NEO4J CONFIGURATION ===
echo "[+] Writing conf/neo4j.conf..."
cat > conf/neo4j.conf <<EOF
# APOC config
dbms.security.procedures.unrestricted=apoc.*
dbms.security.procedures.allowlist=apoc.*
server.http.listen_address=:7474
server.bolt.listen_address=:7687
server.jvm.additional=-Dapoc.import.file.enabled=true
server.jvm.additional=-Dapoc.export.file.enabled=true

# Performance tuning
dbms.memory.heap.initial_size=4g
dbms.memory.heap.max_size=6g
dbms.memory.pagecache.size=2g
EOF

# === FIX FILE OWNERSHIP FOR DOCKER ===
echo "[+] Setting permissions for Docker access..."
sudo chown -R 1000:1000 data logs import plugins conf || true

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
  -v "$(pwd)/plugins:/plugins" \
  -e NEO4J_PLUGINS='["apoc"]' \
  -e NEO4J_dbms_security_procedures_unrestricted=apoc.* \
  -e NEO4J_dbms_security_procedures_allowlist=apoc.* \
  -e NEO4J_apoc_import_file_enabled=true \
  -e NEO4J_apoc_export_file_enabled=true \
  -e NEO4J_AUTH=neo4j/"$NEO4J_PASSWORD" \
  neo4j:"$NEO4J_VERSION"

# === WAIT AND VERIFY ===
echo "[+] Waiting for Neo4j to initialize..."
sleep 12

echo "[+] Verifying APOC availability..."
if docker exec -it "$CONTAINER_NAME" cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "RETURN apoc.version()" 2>/dev/null; then
    echo "[✓] APOC is installed and ready!"
    echo "[✓] Access Neo4j at http://localhost:7474 (neo4j / $NEO4J_PASSWORD)"
else
    echo "[!] APOC verification failed. Check Docker logs with: docker logs $CONTAINER_NAME"
    exit 1
fi