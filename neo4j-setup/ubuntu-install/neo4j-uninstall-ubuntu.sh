#!/usr/bin/env bash

echo "[!] Force purging Neo4j completely..."

sudo systemctl stop neo4j || true
sudo apt purge -y neo4j
sudo apt autoremove -y

sudo rm -rf /etc/neo4j /var/lib/neo4j /var/log/neo4j /var/run/neo4j
sudo rm -rf /var/lib/dpkg/info/neo4j.*
sudo rm -f /etc/apt/sources.list.d/neo4j.list
sudo rm -f /usr/share/keyrings/neo4j.gpg

sudo apt update

# Check if ufw is installed
if command -v ufw &> /dev/null; then
    # See if ufw is enabled
    if ufw status | grep -q "active"; then
        # See if ports 7474 and 7687 are allowed
        if ufw status | grep -q "7474/tcp" && ufw status | grep -q "7687/tcp"; then
            # Check if the user wants to delete the ufw rules
            read -p "Do you want to delete the ufw rules to allow incoming connections to Neo4j? (y/n) " -n 1 -r
            echo    # (optional) move to a new line
            if [[ $REPLY =~ ^[Yy]$ ]]
            then
                sudo ufw delete allow 7474/tcp
                sudo ufw delete allow 7687/tcp
                sudo ufw disable
            fi
        fi
    fi
fi
