#!/usr/bin/env bash
set -euo pipefail

#######################################
# Configuration
#######################################
NEO4J_PASSWORD="personatrace"
HEAP_INITIAL="4g"
HEAP_MAX="6g"
PAGECACHE="2g"

#######################################
# 1. Prerequisites
#######################################
echo "[1/9] Installing prerequisites..."
sudo apt update
sudo apt install -y wget curl apt-transport-https ca-certificates gnupg netcat-openbsd

#######################################
# 2. Add Neo4j APT repo
#######################################
echo "[2/9] Adding Neo4j APT repo..."
curl -fsSL https://debian.neo4j.com/neotechnology.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/neo4j.gpg
echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable 5" | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt update

#######################################
# 3. Install Neo4j
#######################################
echo "[3/9] Installing Neo4j..."
sudo apt install -y neo4j

#######################################
# 4. Configure Neo4j settings
#######################################
echo "[4/9] Configuring Neo4j settings..."
sudo tee -a /etc/neo4j/neo4j.conf > /dev/null <<EOF
server.memory.heap.initial_size=4g
server.memory.heap.max_size=6g
server.memory.pagecache.size=2g
server.default_listen_address=0.0.0.0

########################################################
# GDS plugin (if on enterprise/commercial edition)
# Uses GDS Enterprise JAR - https://neo4j.com/download-center/#graph-data-science
########################################################
# Enable GDS plugin
#dbms.security.procedures.unrestricted=gds.*
#dbms.security.procedures.allowlist=gds.*
# Allow GPU acceleration
#gds.graphanalytics.useCUDA=true
#gds.graphanalytics.cudaDevice=0  # Adjust if needed
EOF
# Make sure neo4j.conf is owned by neo4j
sudo chown neo4j:neo4j /etc/neo4j/neo4j.conf

#######################################
# 6. Enable and restart Neo4j
#######################################
echo "[6/9] Enabling and restarting Neo4j..."
sudo systemctl enable neo4j
sudo systemctl restart neo4j

#######################################
# 7. Wait for Neo4j
#######################################
echo "[7/9] Waiting for Neo4j to start..."
until nc -z localhost 7687; do sleep 1; done

#######################################
# 8. Set initial password
#######################################
echo "[8/9] Setting initial password..."
echo "${NEO4J_PASSWORD}" | sudo neo4j-admin dbms set-initial-password "${NEO4J_PASSWORD}"

#######################################
# 9. Restart Neo4j
#######################################
echo "[9/9] Restarting Neo4j..."
sudo systemctl restart neo4j

#######################################
# 10. Setup ufw
#######################################
echo "[10/10] Setting up ufw..."
# Check if you should install ufw from the user
read -p "Do you want to install ufw and allow incoming connections to Neo4j? (y/n) " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "[10/10] Installing ufw..."
    sudo apt install -y ufw
    sudo ufw allow 7474/tcp
    sudo ufw allow 7687/tcp
    sudo ufw enable
fi

#######################################
# 11. Done
#######################################
echo "[11/11] ✅ Installation complete!"
echo "➡  Web UI:  http://localhost:7474"
echo "➡  Bolt:    bolt://localhost:7687"
echo "➡  User:    neo4j"
echo "➡  Pass:    ${NEO4J_PASSWORD}"