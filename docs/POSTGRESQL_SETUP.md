# PostgreSQL Setup Guide

This guide covers the installation and configuration of PostgreSQL for the To The Moon application.

## Prerequisites

- Ubuntu 20.04+ server
- sudo access
- At least 5GB free disk space

## 1. Install PostgreSQL 14+

```bash
# Update package list
sudo apt update

# Install PostgreSQL and contrib packages
sudo apt install -y postgresql postgresql-contrib

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify installation
sudo -u postgres psql --version
```

## 2. Create Database and User

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL prompt:
CREATE DATABASE tothemoon_prod;
CREATE USER tothemoon WITH ENCRYPTED PASSWORD 'CHANGE_THIS_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE tothemoon_prod TO tothemoon;

# Grant schema privileges
\c tothemoon_prod
GRANT ALL ON SCHEMA public TO tothemoon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO tothemoon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO tothemoon;

# Exit
\q
```

## 3. Configure PostgreSQL for Production

### Update postgresql.conf

```bash
sudo nano /etc/postgresql/14/main/postgresql.conf
```

Add/update these settings:

```ini
# Memory Configuration
shared_buffers = 256MB              # 25% of RAM for dedicated server
effective_cache_size = 1GB          # 50-75% of RAM
work_mem = 16MB                     # Per operation memory
maintenance_work_mem = 128MB        # For VACUUM, CREATE INDEX

# Connection Settings
max_connections = 100               # Adjust based on load
superuser_reserved_connections = 3

# Query Planning
random_page_cost = 1.1              # For SSD storage
effective_io_concurrency = 200      # For SSD storage

# Write Ahead Log
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_min_duration_statement = 1000   # Log queries > 1 second

# Performance Monitoring
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all
```

### Update pg_hba.conf

```bash
sudo nano /etc/postgresql/14/main/pg_hba.conf
```

Add this line for local application access:

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   tothemoon_prod  tothemoon                               md5
host    tothemoon_prod  tothemoon       127.0.0.1/32            md5
host    tothemoon_prod  tothemoon       ::1/128                 md5
```

### Restart PostgreSQL

```bash
sudo systemctl restart postgresql
```

## 4. Test Connection

```bash
# Test connection
psql -h localhost -U tothemoon -d tothemoon_prod

# Should prompt for password, then connect
# Exit with \q
```

## 5. Enable pg_stat_statements

```bash
sudo -u postgres psql -d tothemoon_prod

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

# Verify
\dx

# Exit
\q
```

## 6. Set Up Automated Backups

Create backup script:

```bash
sudo nano /usr/local/bin/backup-postgres.sh
```

Add content:

```bash
#!/bin/bash
BACKUP_DIR="/srv/tothemoon/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=7

# Create backup directory
mkdir -p $BACKUP_DIR

# Run backup
pg_dump -h localhost -U tothemoon -d tothemoon_prod -F c -f $BACKUP_DIR/tothemoon_$DATE.dump

# Compress
gzip $BACKUP_DIR/tothemoon_$DATE.dump

# Delete old backups
find $BACKUP_DIR -name "tothemoon_*.dump.gz" -mtime +$KEEP_DAYS -delete

echo "Backup completed: tothemoon_$DATE.dump.gz"
```

Make executable:

```bash
sudo chmod +x /usr/local/bin/backup-postgres.sh
```

Add to crontab:

```bash
sudo crontab -e

# Add this line for daily backup at 2 AM
0 2 * * * /usr/local/bin/backup-postgres.sh >> /var/log/postgres-backup.log 2>&1
```

## 7. Environment Variables

Update `/srv/tothemoon/.env`:

```bash
# PostgreSQL Configuration
DATABASE_URL=postgresql://tothemoon:YOUR_PASSWORD@localhost:5432/tothemoon_prod

# Keep SQLite as fallback
SQLITE_DATABASE_URL=sqlite:///./dev.db
```

## Verification Checklist

- [ ] PostgreSQL 14+ installed and running
- [ ] Database `tothemoon_prod` created
- [ ] User `tothemoon` created with proper permissions
- [ ] postgresql.conf configured for production
- [ ] pg_hba.conf allows local connections
- [ ] pg_stat_statements extension enabled
- [ ] Backup script created and scheduled
- [ ] Can connect with: `psql -h localhost -U tothemoon -d tothemoon_prod`

## Troubleshooting

### Connection refused
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### Authentication failed
```bash
# Reset password
sudo -u postgres psql
ALTER USER tothemoon WITH PASSWORD 'new_password';
```

### Permission denied
```bash
# Grant all privileges again
sudo -u postgres psql -d tothemoon_prod
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tothemoon;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tothemoon;
```

## Next Steps

After completing this setup:
1. Run Alembic migrations to create schema
2. Execute data migration scripts
3. Update application configuration
4. Test application connectivity
