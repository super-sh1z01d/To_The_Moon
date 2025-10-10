#!/bin/bash
# Master script for PostgreSQL migration
# Run this script to perform the complete migration

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}PostgreSQL Migration Script${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run with sudo${NC}"
    exit 1
fi

# Step 1: Backup SQLite
echo -e "${YELLOW}Step 1: Backing up SQLite database...${NC}"
bash /srv/tothemoon/scripts/backup_sqlite.sh
if [ $? -ne 0 ]; then
    echo -e "${RED}Backup failed!${NC}"
    exit 1
fi
echo ""

# Step 2: Stop scheduler
echo -e "${YELLOW}Step 2: Stopping scheduler...${NC}"
systemctl stop tothemoon
echo -e "${GREEN}✓ Scheduler stopped${NC}"
echo ""

# Step 3: Export data from SQLite
echo -e "${YELLOW}Step 3: Exporting data from SQLite...${NC}"
python3 /srv/tothemoon/scripts/export_sqlite_data.py
if [ $? -ne 0 ]; then
    echo -e "${RED}Export failed!${NC}"
    systemctl start tothemoon
    exit 1
fi
echo ""

# Step 4: Run Alembic migrations
echo -e "${YELLOW}Step 4: Running database migrations...${NC}"
cd /srv/tothemoon
python3 -m alembic upgrade head
if [ $? -ne 0 ]; then
    echo -e "${RED}Migration failed!${NC}"
    systemctl start tothemoon
    exit 1
fi
echo -e "${GREEN}✓ Migrations applied${NC}"
echo ""

# Step 5: Run PostgreSQL optimizations
echo -e "${YELLOW}Step 5: Applying PostgreSQL optimizations...${NC}"
sudo -u postgres psql -d tothemoon_prod -f /srv/tothemoon/scripts/postgresql_optimizations.sql
if [ $? -ne 0 ]; then
    echo -e "${RED}Optimizations failed!${NC}"
    systemctl start tothemoon
    exit 1
fi
echo -e "${GREEN}✓ Optimizations applied${NC}"
echo ""

# Step 6: Import data to PostgreSQL
echo -e "${YELLOW}Step 6: Importing data to PostgreSQL...${NC}"
python3 /srv/tothemoon/scripts/import_postgresql_data.py
if [ $? -ne 0 ]; then
    echo -e "${RED}Import failed!${NC}"
    systemctl start tothemoon
    exit 1
fi
echo ""

# Step 7: Validate migration
echo -e "${YELLOW}Step 7: Validating migration...${NC}"
python3 /srv/tothemoon/scripts/validate_migration.py
if [ $? -ne 0 ]; then
    echo -e "${RED}Validation failed!${NC}"
    echo -e "${YELLOW}Review errors above. You may need to rollback.${NC}"
    exit 1
fi
echo ""

# Step 8: Update environment
echo -e "${YELLOW}Step 8: Updating environment configuration...${NC}"
# Backup current .env
cp /srv/tothemoon/.env /srv/tothemoon/.env.backup
echo -e "${GREEN}✓ Backed up .env${NC}"

# Update DATABASE_URL (user needs to set password)
echo -e "${YELLOW}Please update DATABASE_URL in /srv/tothemoon/.env${NC}"
echo -e "${YELLOW}Set: DATABASE_URL=postgresql://tothemoon:YOUR_PASSWORD@localhost:5432/tothemoon_prod${NC}"
echo ""
read -p "Press Enter after updating .env file..."

# Step 9: Restart application
echo -e "${YELLOW}Step 9: Restarting application...${NC}"
systemctl start tothemoon
sleep 5

# Check if service started
if systemctl is-active --quiet tothemoon; then
    echo -e "${GREEN}✓ Application started successfully${NC}"
else
    echo -e "${RED}❌ Application failed to start${NC}"
    echo -e "${YELLOW}Check logs: journalctl -u tothemoon -n 50${NC}"
    exit 1
fi
echo ""

# Step 10: Final checks
echo -e "${YELLOW}Step 10: Running final checks...${NC}"
sleep 5
curl -s http://localhost:8000/health > /dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
    exit 1
fi

# Test API endpoint
response_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/tokens?status=active&limit=10)
echo -e "${GREEN}✓ API response time: ${response_time}s${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Migration completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Next steps:"
echo -e "1. Monitor application logs: journalctl -u tothemoon -f"
echo -e "2. Check API performance: curl http://localhost:8000/tokens?status=active"
echo -e "3. SQLite backup location: /srv/tothemoon/backups/sqlite/"
echo -e "4. Keep SQLite backup for 7 days before deleting"
echo ""
