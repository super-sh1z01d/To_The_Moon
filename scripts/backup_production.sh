#!/bin/bash

# Production Backup Script for Server Migration
# Backs up database, configuration, and essential files

set -e

OLD_SERVER="5.129.247.78"
BACKUP_DIR="/tmp/tothemoon_backup_$(date +%Y%m%d_%H%M%S)"
DB_BACKUP_FILE="tothemoon_db_backup.sql"

echo "🔄 Starting production backup from $OLD_SERVER..."

# Create backup directory
mkdir -p "$BACKUP_DIR"
cd "$BACKUP_DIR"

echo "📦 Backing up database..."
# Check if PostgreSQL or SQLite is used
ssh root@$OLD_SERVER "cd /srv/tothemoon && ls -la *.db dev.db 2>/dev/null || echo 'No SQLite DB found'"
ssh root@$OLD_SERVER "cd /srv/tothemoon && ls -la" | grep -E "\.(db|sqlite)" || echo "Checking for PostgreSQL..."

# Try SQLite backup first
if ssh root@$OLD_SERVER "cd /srv/tothemoon && test -f dev.db"; then
    echo "Found SQLite database, backing up..."
    scp root@$OLD_SERVER:/srv/tothemoon/dev.db ./dev.db
    echo "SQLite database backed up as dev.db"
else
    echo "Trying PostgreSQL backup..."
    ssh root@$OLD_SERVER "which pg_dump || (apt update && apt install -y postgresql-client)"
    ssh root@$OLD_SERVER "cd /srv/tothemoon && pg_dump -h localhost -U tothemoon -d tothemoon --no-password > /tmp/$DB_BACKUP_FILE" || echo "PostgreSQL backup failed"
    scp root@$OLD_SERVER:/tmp/$DB_BACKUP_FILE ./ || echo "No PostgreSQL backup to copy"
fi

echo "📁 Backing up configuration files..."
scp root@$OLD_SERVER:/srv/tothemoon/.env ./env_backup
scp root@$OLD_SERVER:/srv/tothemoon/markets.json ./markets_backup.json || echo "markets.json not found, skipping"

echo "🔧 Backing up systemd service..."
scp root@$OLD_SERVER:/etc/systemd/system/tothemoon.service ./tothemoon.service
scp -r root@$OLD_SERVER:/etc/systemd/system/tothemoon.service.d/ ./tothemoon.service.d/ || echo "service.d not found, skipping"

echo "📊 Backing up nginx configuration..."
scp root@$OLD_SERVER:/etc/nginx/sites-available/tothemoon ./nginx_tothemoon || echo "nginx config not found, skipping"

echo "✅ Backup completed in: $BACKUP_DIR"
echo "📋 Backup contents:"
ls -la "$BACKUP_DIR"

echo ""
echo "🎯 Next steps:"
echo "1. Run: ./scripts/setup_new_server.sh $BACKUP_DIR"
echo "2. Update DNS to point to 67.213.119.189"
echo "3. Test the new server"
echo "4. Shutdown old server"