#!/bin/bash
# Backup SQLite database before PostgreSQL migration

set -e

BACKUP_DIR="/srv/tothemoon/backups/sqlite"
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="/srv/tothemoon/dev.db"

# Colors for output
GREEN='\033[0.32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== SQLite Backup Script ===${NC}"
echo "Date: $(date)"
echo "Database: $DB_PATH"
echo "Backup directory: $BACKUP_DIR"
echo ""

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}Error: Database file not found: $DB_PATH${NC}"
    exit 1
fi

# Create backup directory
mkdir -p $BACKUP_DIR

# Get database size
DB_SIZE=$(du -h $DB_PATH | cut -f1)
echo "Database size: $DB_SIZE"

# Check available disk space
AVAILABLE=$(df -h /srv/tothemoon | awk 'NR==2 {print $4}')
echo "Available disk space: $AVAILABLE"

# Backup database
echo -e "${YELLOW}Creating backup...${NC}"
cp $DB_PATH $BACKUP_DIR/dev_${DATE}.db

# Verify backup
if [ -f "$BACKUP_DIR/dev_${DATE}.db" ]; then
    BACKUP_SIZE=$(du -h $BACKUP_DIR/dev_${DATE}.db | cut -f1)
    echo -e "${GREEN}✓ Backup created successfully${NC}"
    echo "Backup file: dev_${DATE}.db"
    echo "Backup size: $BACKUP_SIZE"
    
    # Compress backup
    echo -e "${YELLOW}Compressing backup...${NC}"
    gzip $BACKUP_DIR/dev_${DATE}.db
    
    COMPRESSED_SIZE=$(du -h $BACKUP_DIR/dev_${DATE}.db.gz | cut -f1)
    echo -e "${GREEN}✓ Backup compressed${NC}"
    echo "Compressed size: $COMPRESSED_SIZE"
    
    # Verify integrity
    echo -e "${YELLOW}Verifying backup integrity...${NC}"
    gunzip -t $BACKUP_DIR/dev_${DATE}.db.gz
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Backup integrity verified${NC}"
    else
        echo -e "${RED}✗ Backup integrity check failed${NC}"
        exit 1
    fi
    
    # List recent backups
    echo ""
    echo "Recent backups:"
    ls -lh $BACKUP_DIR/dev_*.db.gz | tail -5
    
    echo ""
    echo -e "${GREEN}=== Backup completed successfully ===${NC}"
    echo "Backup location: $BACKUP_DIR/dev_${DATE}.db.gz"
    
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi

# Optional: Clean old backups (keep last 10)
BACKUP_COUNT=$(ls -1 $BACKUP_DIR/dev_*.db.gz 2>/dev/null | wc -l)
if [ $BACKUP_COUNT -gt 10 ]; then
    echo ""
    echo -e "${YELLOW}Cleaning old backups (keeping last 10)...${NC}"
    ls -t $BACKUP_DIR/dev_*.db.gz | tail -n +11 | xargs rm -f
    echo -e "${GREEN}✓ Old backups cleaned${NC}"
fi
