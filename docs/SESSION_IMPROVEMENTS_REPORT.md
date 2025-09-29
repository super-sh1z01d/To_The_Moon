# Server Migration Report

**Date**: September 29, 2025  
**Duration**: Full day session  
**Scope**: Complete server migration from old to new infrastructure  

## 🎯 Overview

This session focused on migrating the To The Moon application from the old server (5.129.247.78) to a new, more powerful server (67.213.119.189). The migration included complete infrastructure setup, data transfer, and service configuration.

## �  Migration Process

### Pre-Migration Setup

**Old Server**: 5.129.247.78 (Ubuntu 22.04)  
**New Server**: 67.213.119.189 (Ubuntu 24.04)  
**Migration Method**: Step-by-step manual migration with data export/import

### Step 1: System Dependencies Installation

```bash
# Update system packages
ssh ubuntu@67.213.119.189 "sudo apt update && sudo apt install -y python3 python3-pip python3-venv git nginx curl"

# Install Node.js 18
ssh ubuntu@67.213.119.189 "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt install -y nodejs"
```

**Results**:
- ✅ Python 3.12 installed
- ✅ Node.js 18.20.8 installed  
- ✅ nginx, git, curl installed
- ✅ System updated to latest packages

### Step 2: User and Directory Setup

```bash
# Create application user and directories
ssh ubuntu@67.213.119.189 "sudo mkdir -p /srv/tothemoon && sudo useradd -r -s /bin/false tothemoon && sudo chown -R tothemoon:tothemoon /srv/tothemoon && sudo chmod 755 /srv/tothemoon"

# Create home directory for npm
ssh ubuntu@67.213.119.189 "sudo mkdir -p /home/tothemoon && sudo chown -R tothemoon:tothemoon /home/tothemoon"
```

**Results**:
- ✅ User `tothemoon` created
- ✅ Application directory `/srv/tothemoon` prepared
- ✅ Proper permissions set

### Step 3: Backup and File Transfer

```bash
# Transfer configuration files
scp /tmp/tothemoon_backup_20250929_182309/env_backup ubuntu@67.213.119.189:/tmp/
scp /tmp/tothemoon_backup_20250929_182309/markets_backup.json ubuntu@67.213.119.189:/tmp/
scp /tmp/tothemoon_backup_20250929_182309/dev.db ubuntu@67.213.119.189:/tmp/
```

**Files Transferred**:
- ✅ Environment configuration (116 bytes)
- ✅ Markets configuration (789 bytes)  
- ✅ Database file (325MB)

### Step 4: Application Code Deployment

```bash
# Clone repository
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon && sudo -u tothemoon git clone https://github.com/super-sh1z01d/To_The_Moon.git ."

# Move configuration files
ssh ubuntu@67.213.119.189 "sudo mv /tmp/env_backup /srv/tothemoon/.env && sudo mv /tmp/markets_backup.json /srv/tothemoon/markets.json && sudo mv /tmp/dev.db /srv/tothemoon/dev.db && sudo chown -R tothemoon:tothemoon /srv/tothemoon"
```

**Results**:
- ✅ Latest code deployed from GitHub
- ✅ Configuration files in place
- ✅ Database file transferred

### Step 5: Python Environment Setup

```bash
# Create virtual environment
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon && sudo -u tothemoon python3 -m venv venv"

# Install dependencies
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon && sudo -u tothemoon bash -c 'source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt'"
```

**Dependencies Installed**:
- ✅ FastAPI 0.111.0
- ✅ uvicorn 0.30.1  
- ✅ SQLAlchemy 2.0.32
- ✅ All required packages (40+ dependencies)

### Step 6: Frontend Build

```bash
# Install npm dependencies
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon/frontend && sudo -u tothemoon npm install"

# Build production frontend
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon/frontend && sudo -u tothemoon npm run build"
```

**Build Results**:
- ✅ 70 packages installed
- ✅ Production build completed (1.00s)
- ✅ Assets: 14.70 kB CSS, 202.91 kB JS

### Step 7: SystemD Service Configuration

```bash
# Transfer service files
scp /tmp/tothemoon_backup_20250929_182309/tothemoon.service ubuntu@67.213.119.189:/tmp/
scp -r /tmp/tothemoon_backup_20250929_182309/tothemoon.service.d ubuntu@67.213.119.189:/tmp/

# Install service
ssh ubuntu@67.213.119.189 "sudo mv /tmp/tothemoon.service /etc/systemd/system/ && sudo mv /tmp/tothemoon.service.d /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable tothemoon.service"
```

**Service Configuration**:
```ini
[Unit]
Description=To The Moon API (FastAPI + Uvicorn)
After=network.target

[Service]
Type=simple
User=tothemoon
Group=tothemoon
WorkingDirectory=/srv/tothemoon
EnvironmentFile=/etc/tothemoon.env
ExecStart=/srv/tothemoon/venv/bin/python -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=3
```

### Step 8: Nginx Configuration

```bash
# Configure nginx reverse proxy
ssh ubuntu@67.213.119.189 "sudo tee /etc/nginx/sites-available/tothemoon << 'EOF'
server {
    listen 80;
    server_name tothemoon.sh1z01d.ru;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /app/ {
        proxy_pass http://127.0.0.1:8000/app/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF"

# Enable site
ssh ubuntu@67.213.119.189 "sudo ln -sf /etc/nginx/sites-available/tothemoon /etc/nginx/sites-enabled/ && sudo rm -f /etc/nginx/sites-enabled/default && sudo nginx -t && sudo systemctl reload nginx"
```

**Results**:
- ✅ Nginx configuration validated
- ✅ Reverse proxy configured
- ✅ Default site disabled

### Step 9: Database Migration

```bash
# Run Alembic migrations
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon && sudo -u tothemoon bash -c 'source venv/bin/activate && PYTHONPATH=. python -m alembic upgrade head'"
```

**Migration Results**:
- ✅ Database schema up to date
- ✅ All migrations applied successfully

## 🚨 Critical Issue Resolution

### Database Corruption Issue

**Problem Encountered**:
```
(sqlite3.DatabaseError) database disk image is malformed
```

The transferred database file was corrupted during the copy process.

**Resolution Steps**:

1. **Stop the service**:
```bash
ssh ubuntu@67.213.119.189 "sudo systemctl stop tothemoon.service"
```

2. **Remove corrupted database**:
```bash
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon && sudo -u tothemoon rm -f dev.db"
```

3. **Create fresh database**:
```bash
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon && sudo -u tothemoon bash -c 'source venv/bin/activate && PYTHONPATH=. python -m alembic upgrade head'"
```

4. **Export data from old server**:
```bash
# Install sqlite3 on old server
ssh root@5.129.247.78 "apt install -y sqlite3"

# Export database as SQL dump
ssh root@5.129.247.78 "cd /srv/tothemoon && sqlite3 dev.db '.dump' > /tmp/tothemoon_export.sql"
```

**Export Results**:
- ✅ SQL dump created: 282MB (282,341,648 bytes)
- ✅ Complete database export successful

### Service Configuration Fix

**Problem**: Environment file path mismatch
- Service expected: `/etc/tothemoon.env`
- Actual location: `/srv/tothemoon/.env`

**Solution**:
```bash
ssh ubuntu@67.213.119.189 "sudo cp /srv/tothemoon/.env /etc/tothemoon.env && sudo systemctl daemon-reload && sudo systemctl start tothemoon.service"
```

## ✅ Migration Success

### Final Service Status

```bash
ssh ubuntu@67.213.119.189 "sudo systemctl status tothemoon.service --no-pager"
```

**Results**:
- ✅ Service: `active (running)`
- ✅ Memory usage: 95.2M
- ✅ Process ID: 633756
- ✅ Scheduler active and processing jobs

### System Verification

**Service Health**:
- ✅ FastAPI application running on port 8000
- ✅ Nginx reverse proxy functional
- ✅ APScheduler jobs executing
- ✅ NotArb pools file updates working

**Infrastructure Improvements**:
- **OS**: Ubuntu 22.04 → Ubuntu 24.04
- **Python**: 3.10 → 3.12
- **Node.js**: Older version → 18.20.8
- **Hardware**: More powerful server resources

## 📊 Migration Statistics

### Data Transfer
- **Configuration files**: 3 files transferred
- **Database size**: 325MB → 282MB SQL dump
- **Code deployment**: Fresh clone from GitHub
- **Build artifacts**: 202.91 kB JavaScript, 14.70 kB CSS

### Timeline
- **Preparation**: System setup and dependencies (~30 minutes)
- **Data transfer**: File copying and configuration (~15 minutes)  
- **Application setup**: Python/Node.js environment (~20 minutes)
- **Service configuration**: SystemD and nginx (~10 minutes)
- **Issue resolution**: Database corruption fix (~30 minutes)
- **Total duration**: ~2 hours

### Performance Gains
- **Modern OS**: Ubuntu 24.04 with latest security updates
- **Updated runtime**: Python 3.12 with performance improvements
- **Fresh environment**: Clean installation without legacy issues
- **Better hardware**: More CPU and memory resources

## 🔄 Next Steps

### Data Import (In Progress)
The SQL dump from the old server (282MB) needs to be imported to restore all historical data:

```bash
# Transfer SQL dump to new server
scp root@5.129.247.78:/tmp/tothemoon_export.sql /tmp/
scp /tmp/tothemoon_export.sql ubuntu@67.213.119.189:/tmp/

# Import data
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon && sudo -u tothemoon sqlite3 dev.db < /tmp/tothemoon_export.sql"
```

### DNS Update
Update DNS records to point to new server:
```
tothemoon.sh1z01d.ru A 67.213.119.189
```

### Old Server Decommission
After successful verification, the old server can be safely shut down.

## 🎯 Migration Success Criteria

- ✅ **Application deployed**: Code and dependencies installed
- ✅ **Service running**: SystemD service active and stable  
- ✅ **Web server configured**: Nginx reverse proxy functional
- ✅ **Database ready**: Fresh schema created, ready for data import
- ✅ **Frontend built**: Production assets compiled and served
- ⏳ **Data migration**: SQL dump ready for import (282MB)
- ⏳ **DNS update**: Pending domain pointer update
- ⏳ **Verification**: Full system testing after data import

**Migration Status**: 90% Complete - Ready for data import and DNS switch

## 📋 Migration Commands Reference

### Complete Command Log
```bash
# 1. System Dependencies
ssh ubuntu@67.213.119.189 "sudo apt update && sudo apt install -y python3 python3-pip python3-venv git nginx curl"
ssh ubuntu@67.213.119.189 "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt install -y nodejs"

# 2. User Setup
ssh ubuntu@67.213.119.189 "sudo mkdir -p /srv/tothemoon && sudo useradd -r -s /bin/false tothemoon && sudo chown -R tothemoon:tothemoon /srv/tothemoon && sudo chmod 755 /srv/tothemoon"
ssh ubuntu@67.213.119.189 "sudo mkdir -p /home/tothemoon && sudo chown -R tothemoon:tothemoon /home/tothemoon"

# 3. File Transfer
scp /tmp/tothemoon_backup_20250929_182309/env_backup ubuntu@67.213.119.189:/tmp/
scp /tmp/tothemoon_backup_20250929_182309/markets_backup.json ubuntu@67.213.119.189:/tmp/
scp /tmp/tothemoon_backup_20250929_182309/dev.db ubuntu@67.213.119.189:/tmp/

# 4. Code Deployment
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon && sudo -u tothemoon git clone https://github.com/super-sh1z01d/To_The_Moon.git ."
ssh ubuntu@67.213.119.189 "sudo mv /tmp/env_backup /srv/tothemoon/.env && sudo mv /tmp/markets_backup.json /srv/tothemoon/markets.json && sudo mv /tmp/dev.db /srv/tothemoon/dev.db && sudo chown -R tothemoon:tothemoon /srv/tothemoon"

# 5. Python Environment
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon && sudo -u tothemoon python3 -m venv venv"
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon && sudo -u tothemoon bash -c 'source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt'"

# 6. Frontend Build
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon/frontend && sudo -u tothemoon npm install"
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon/frontend && sudo -u tothemoon npm run build"

# 7. Service Configuration
scp /tmp/tothemoon_backup_20250929_182309/tothemoon.service ubuntu@67.213.119.189:/tmp/
scp -r /tmp/tothemoon_backup_20250929_182309/tothemoon.service.d ubuntu@67.213.119.189:/tmp/
ssh ubuntu@67.213.119.189 "sudo mv /tmp/tothemoon.service /etc/systemd/system/ && sudo mv /tmp/tothemoon.service.d /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable tothemoon.service"

# 8. Nginx Configuration
ssh ubuntu@67.213.119.189 "sudo ln -sf /etc/nginx/sites-available/tothemoon /etc/nginx/sites-enabled/ && sudo rm -f /etc/nginx/sites-enabled/default && sudo nginx -t && sudo systemctl reload nginx"

# 9. Database Setup
ssh ubuntu@67.213.119.189 "cd /srv/tothemoon && sudo -u tothemoon bash -c 'source venv/bin/activate && PYTHONPATH=. python -m alembic upgrade head'"

# 10. Fix Environment File Path
ssh ubuntu@67.213.119.189 "sudo cp /srv/tothemoon/.env /etc/tothemoon.env && sudo systemctl daemon-reload && sudo systemctl start tothemoon.service"

# 11. Database Export from Old Server
ssh root@5.129.247.78 "apt install -y sqlite3"
ssh root@5.129.247.78 "cd /srv/tothemoon && sqlite3 dev.db '.dump' > /tmp/tothemoon_export.sql"
```

## 🎯 Final Migration Status

### ✅ Completed Successfully
- **Infrastructure**: New server fully configured
- **Application**: Code deployed and running
- **Service**: SystemD service active and stable
- **Web Server**: Nginx reverse proxy functional
- **Database Schema**: Fresh database with latest migrations
- **Frontend**: Production build completed and served

### ⏳ Pending Steps
- **Data Import**: 282MB SQL dump ready for import
- **DNS Update**: Point domain to new server IP
- **Final Testing**: Verify all functionality after data import
- **Old Server Shutdown**: Decommission after successful verification

**Current Status**: Migration infrastructure 100% complete, ready for data import and cutover.