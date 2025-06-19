# Ubuntu Installation for Neo4j

This folder contains the native Ubuntu/Debian installation for Neo4j, suitable for users who prefer system-level installation or need production deployments.

## Prerequisites

- Ubuntu 18.04+ or Debian 9+
- At least 8GB of available RAM
- Sudo privileges
- Internet connection for package downloads

## Quick Installation

1. **Navigate to this directory**:
   ```bash
   cd ubuntu-install
   ```

2. **Make the script executable**:
   ```bash
   chmod +x neo4j-install-ubuntu.sh
   ```

3. **Run the installation script**:
   ```bash
   sudo ./neo4j-install-ubuntu.sh
   ```

The script will:
- Add the official Neo4j repository
- Install Neo4j and dependencies
- Configure Neo4j with optimized settings for PersonaTrace
- Set up systemd service
- Start Neo4j service
- Configure firewall rules (optional)
- Verify the installation

## What Gets Installed

- **Neo4j Database**: Official Neo4j Community Edition
- **Java Runtime**: OpenJDK 11 (required by Neo4j)
- **System Service**: Neo4j runs as a systemd service
- **Configuration**: Optimized settings in `/etc/neo4j/neo4j.conf`

## Configuration

The default configuration includes:
- **Memory**: 4GB initial heap, 6GB max heap, 2GB page cache
- **Ports**: 7474 (HTTP), 7687 (Bolt)
- **Authentication**: neo4j/personatrace
- **Network**: Accessible from any IP (0.0.0.0)
- **Service**: Auto-starts on boot

## Accessing Neo4j

- **Neo4j Browser**: http://localhost:7474
- **Bolt Connection**: bolt://localhost:7687
- **Credentials**: neo4j / personatrace

## Management Commands

### Service Management
```bash
# Start Neo4j
sudo systemctl start neo4j

# Stop Neo4j
sudo systemctl stop neo4j

# Restart Neo4j
sudo systemctl restart neo4j

# Check status
sudo systemctl status neo4j

# Enable auto-start on boot
sudo systemctl enable neo4j

# Disable auto-start on boot
sudo systemctl disable neo4j
```

### View Logs
```bash
# View service logs
sudo journalctl -u neo4j -f

# View Neo4j logs directly
sudo tail -f /var/log/neo4j/neo4j.log

# View debug logs
sudo tail -f /var/log/neo4j/debug.log
```

### Configuration
```bash
# Edit configuration
sudo nano /etc/neo4j/neo4j.conf

# View configuration
sudo cat /etc/neo4j/neo4j.conf

# Test configuration
sudo neo4j validate-config
```

### Data Management
```bash
# View data directory
ls -la /var/lib/neo4j/data/

# Backup data
sudo cp -r /var/lib/neo4j/data/ /backup/neo4j-data/

# Restore data
sudo cp -r /backup/neo4j-data/ /var/lib/neo4j/data/
sudo chown -R neo4j:neo4j /var/lib/neo4j/data/
```

## Troubleshooting

### Service Won't Start
```bash
# Check service status
sudo systemctl status neo4j

# Check logs
sudo journalctl -u neo4j -n 50

# Check configuration
sudo neo4j validate-config

# Check permissions
sudo chown -R neo4j:neo4j /var/lib/neo4j/
sudo chown -R neo4j:neo4j /var/log/neo4j/
```

### Can't Connect to Neo4j
```bash
# Check if service is running
sudo systemctl status neo4j

# Check if ports are listening
sudo netstat -tulpn | grep -E '7474|7687'

# Test connection locally
cypher-shell -u neo4j -p personatrace "RETURN 1"

# Check firewall
sudo ufw status
```

### Performance Issues
```bash
# Check memory usage
free -h

# Check Neo4j memory settings
grep -E "heap|pagecache" /etc/neo4j/neo4j.conf

# Monitor system resources
htop
```

### Permission Issues
```bash
# Fix ownership
sudo chown -R neo4j:neo4j /var/lib/neo4j/
sudo chown -R neo4j:neo4j /var/log/neo4j/
sudo chown -R neo4j:neo4j /etc/neo4j/

# Fix permissions
sudo chmod -R 755 /var/lib/neo4j/
sudo chmod -R 755 /var/log/neo4j/
```

## Customization

### Change Memory Settings
Edit `/etc/neo4j/neo4j.conf`:
```bash
# Increase heap size for larger datasets
dbms.memory.heap.initial_size=8g
dbms.memory.heap.max_size=12g
dbms.memory.pagecache.size=4g
```

### Change Password
```bash
# Stop Neo4j
sudo systemctl stop neo4j

# Change password using cypher-shell
cypher-shell -u neo4j -p personatrace "ALTER CURRENT USER SET PASSWORD FROM 'personatrace' TO 'newpassword'"

# Or use Neo4j Browser at http://localhost:7474
```

### Network Configuration
Edit `/etc/neo4j/neo4j.conf`:
```bash
# Restrict to localhost only
server.default_listen_address=127.0.0.1

# Or allow specific IPs
server.default_listen_address=0.0.0.0
```

## Uninstallation

To completely remove Neo4j:

1. **Run the uninstall script**:
   ```bash
   sudo ./neo4j-uninstall-ubuntu.sh
   ```

2. **Or manually remove**:
   ```bash
   # Stop and disable service
   sudo systemctl stop neo4j
   sudo systemctl disable neo4j

   # Remove packages
   sudo apt remove neo4j
   sudo apt autoremove

   # Remove data and logs (WARNING: This deletes all data!)
   sudo rm -rf /var/lib/neo4j/
   sudo rm -rf /var/log/neo4j/
   sudo rm -rf /etc/neo4j/
   ```

## Security Notes

- Default credentials are for development only
- For production: change password and restrict network access
- Consider using systemd secrets for credential management
- Regularly update Neo4j version for security patches
- Configure firewall rules appropriately

## Performance Tuning

### Memory Optimization
```bash
# For systems with 16GB+ RAM
dbms.memory.heap.initial_size=8g
dbms.memory.heap.max_size=12g
dbms.memory.pagecache.size=4g

# For systems with 32GB+ RAM
dbms.memory.heap.initial_size=16g
dbms.memory.heap.max_size=24g
dbms.memory.pagecache.size=8g
```

### Disk I/O Optimization
```bash
# Use SSD storage when possible
# Consider RAID configurations for production
# Monitor I/O performance with iostat
```

## Next Steps

Once Neo4j is running:
1. Load data using the [dataloader](../../dataloader/README.md)
2. Start the [PersonaTrace application](../../app/README.md)
3. Explore data in the Neo4j Browser
4. Set up monitoring and backup procedures for production use 