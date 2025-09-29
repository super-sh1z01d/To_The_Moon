# Server Migration Guide

## Overview
Migration from old server (5.129.247.78) to new server (67.213.119.189) with full data preservation.

## Prerequisites
- SSH access to both servers
- PostgreSQL credentials
- Domain DNS control

## Migration Steps

### 1. Backup Old Server
```bash
./scripts/backup_production.sh
```

This will:
- Create timestamped backup directory
- Export PostgreSQL database
- Backup configuration files (.env, systemd service, nginx)
- Backup application data (markets.json)

### 2. Setup New Server
```bash
./scripts/setup_new_server.sh /tmp/tothemoon_backup_YYYYMMDD_HHMMSS
```

This will:
- Install system dependencies (Python, PostgreSQL, nginx)
- Create database and user
- Restore database from backup
- Clone application code
- Setup Python environment
- Install systemd service
- Configure nginx
- Build frontend
- Start services

### 3. Verify Migration
```bash
./scripts/verify_migration.sh
```

This will:
- Compare database record counts
- Test API endpoints on both servers
- Check service status
- Compare system resources

### 4. DNS Update
Update DNS record:
```
tothemoon.sh1z01d.ru A 67.213.119.189
```

### 5. Final Testing
```bash
# Test new server directly
curl http://67.213.119.189/health

# Test with domain (after DNS propagation)
curl https://tothemoon.sh1z01d.ru/health
```

### 6. Shutdown Old Server
```bash
ssh root@5.129.247.78 'shutdown -h now'
```

## Rollback Plan
If issues occur:
1. Revert DNS to old server: `tothemoon.sh1z01d.ru A 5.129.247.78`
2. Restart old server if needed
3. Debug new server issues

## New Server Specs
- **IP**: 67.213.119.189
- **OS**: Ubuntu 20.04+ 
- **Resources**: Higher CPU/RAM than old server
- **Services**: PostgreSQL, nginx, Python 3.10+

## Post-Migration Checklist
- [ ] Database data intact
- [ ] All API endpoints working
- [ ] Frontend accessible
- [ ] Scheduler running
- [ ] Token processing active
- [ ] Logs being generated
- [ ] SSL certificate (if needed)
- [ ] Monitoring alerts updated

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL status
systemctl status postgresql

# Test database connection
sudo -u postgres psql -d tothemoon -c "SELECT COUNT(*) FROM tokens;"
```

### Service Issues
```bash
# Check service logs
journalctl -u tothemoon.service -f

# Restart service
systemctl restart tothemoon.service
```

### Frontend Issues
```bash
# Rebuild frontend
cd /srv/tothemoon/frontend
npm run build
```

## Performance Monitoring
Monitor new server performance:
```bash
# CPU and memory usage
htop

# Disk usage
df -h

# Service resource usage
systemctl status tothemoon.service
```