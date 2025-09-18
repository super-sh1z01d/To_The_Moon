# Deployment Guide

Complete guide for deploying and maintaining To The Moon in production environments.

## 🚀 Quick Deployment

### Automated Installation (Recommended)
```bash
# One-command installation on fresh Ubuntu/Debian server
sudo bash scripts/install.sh

# Or with custom settings
REPO_URL="https://github.com/your-fork/To_The_Moon.git" sudo bash scripts/install.sh
```

**What this does:**
- ✅ Installs system dependencies (Python, Node.js, PostgreSQL)
- ✅ Creates application user and directories
- ✅ Clones repository and sets up virtual environment
- ✅ Configures database and runs migrations
- ✅ Builds frontend application
- ✅ Sets up systemd services
- ✅ Configures nginx (optional)
- ✅ Sets up SSL with Let's Encrypt (optional)
- ✅ Performs health checks

### Manual Installation
For custom setups or when you need more control:

```bash
# 1. System dependencies
sudo apt update && sudo apt install -y python3.10 python3.10-venv python3-pip nodejs npm postgresql postgresql-contrib nginx

# 2. Create application user
sudo useradd -m -s /bin/bash tothemoon
sudo mkdir -p /srv/tothemoon
sudo chown tothemoon:tothemoon /srv/tothemoon

# 3. Clone and setup
sudo -u tothemoon git clone https://github.com/super-sh1z01d/To_The_Moon.git /srv/tothemoon
cd /srv/tothemoon
sudo -u tothemoon python3 -m venv venv
sudo -u tothemoon ./venv/bin/pip install -r requirements.txt

# 4. Configure environment
sudo -u tothemoon cp .env.example .env
# Edit .env with your settings

# 5. Database setup
sudo -u postgres createdb tothemoon
sudo -u postgres createuser tothemoon
sudo -u tothemoon ./venv/bin/python -m alembic upgrade head

# 6. Build frontend
cd frontend && npm install && npm run build && cd -

# 7. Setup systemd services (see systemd section below)
```

## ⚙️ Configuration

### Environment Variables (.env)
```bash
# Application
APP_ENV=prod
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=postgresql+psycopg2://tothemoon:password@localhost:5432/tothemoon

# Features
SCHEDULER_ENABLED=true
FRONTEND_DIST_PATH=frontend/dist

# Security (optional)
SECRET_KEY=your-secret-key-here
```

### Database Configuration
```bash
# PostgreSQL setup
sudo -u postgres psql
CREATE DATABASE tothemoon;
CREATE USER tothemoon WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE tothemoon TO tothemoon;
\q

# Update .env with connection string
DATABASE_URL=postgresql+psycopg2://tothemoon:secure_password@localhost:5432/tothemoon
```

### Runtime Settings
Configure via `/settings` API or web interface:
- **Scoring Model**: `hybrid_momentum` (recommended)
- **Update Intervals**: Hot (30s), Cold (2min)
- **Quality Thresholds**: Data validation parameters
- **Component Weights**: Scoring component weights

## 🔧 Systemd Services

### Main Application Service
Create `/etc/systemd/system/tothemoon.service`:
```ini
[Unit]
Description=To The Moon API (FastAPI + Uvicorn)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=tothemoon
Group=tothemoon
WorkingDirectory=/srv/tothemoon
Environment=PATH=/srv/tothemoon/venv/bin
ExecStart=/srv/tothemoon/venv/bin/python -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### WebSocket Worker Service
Create `/etc/systemd/system/tothemoon-worker.service`:
```ini
[Unit]
Description=To The Moon WebSocket Worker
After=network.target
Requires=tothemoon.service

[Service]
Type=simple
User=tothemoon
Group=tothemoon
WorkingDirectory=/srv/tothemoon
Environment=PATH=/srv/tothemoon/venv/bin
Environment=PYTHONPATH=/srv/tothemoon
Environment=PUMPFUN_RUN_SECONDS=300
ExecStart=/srv/tothemoon/venv/bin/python -m src.workers.pumpfun_ws
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Enable and Start Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable tothemoon tothemoon-worker
sudo systemctl start tothemoon tothemoon-worker

# Check status
sudo systemctl status tothemoon
sudo systemctl status tothemoon-worker
```

## 🌐 Nginx Configuration

### Basic Configuration
Create `/etc/nginx/sites-available/tothemoon`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files (optional optimization)
    location /static/ {
        alias /srv/tothemoon/frontend/dist/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/tothemoon /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL with Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 🔄 Updates and Maintenance

### Quick Updates (Recommended)
For regular updates without downtime:
```bash
cd /srv/tothemoon
sudo -u tothemoon bash scripts/quick_update.sh
```

**What it does:**
- ✅ Git pull latest changes
- ✅ Install new dependencies (if any)
- ✅ Run database migrations
- ✅ Rebuild frontend
- ✅ Restart services
- ✅ Health check
- ⚡ **Downtime: <30 seconds**

### Manual Updates
For more control over the update process:
```bash
# 1. Backup (optional but recommended)
sudo -u tothemoon cp .env .env.backup
sudo -u postgres pg_dump tothemoon > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Update code
sudo -u tothemoon git pull origin main

# 3. Update dependencies
sudo -u tothemoon ./venv/bin/pip install -r requirements.txt

# 4. Run migrations
sudo -u tothemoon ./venv/bin/python -m alembic upgrade head

# 5. Rebuild frontend
cd frontend && npm install && npm run build && cd -

# 6. Restart services
sudo systemctl restart tothemoon tothemoon-worker

# 7. Verify
curl -f http://localhost:8000/health
```

### Database Migrations
```bash
# Check current migration status
sudo -u tothemoon ./venv/bin/python -m alembic current

# Apply pending migrations
sudo -u tothemoon ./venv/bin/python -m alembic upgrade head

# Create new migration (development)
sudo -u tothemoon ./venv/bin/python -m alembic revision -m "description" --autogenerate
```

## 📊 Monitoring and Health Checks

### Health Check Endpoints
```bash
# Basic health check
curl http://localhost:8000/health

# Scheduler health (detailed)
curl http://localhost:8000/health/scheduler

# System version
curl http://localhost:8000/version
```

### Log Monitoring
```bash
# Application logs
sudo journalctl -u tothemoon -f

# Worker logs
sudo journalctl -u tothemoon-worker -f

# Combined logs
sudo journalctl -u tothemoon -u tothemoon-worker -f

# Error logs only
sudo journalctl -u tothemoon -p err -f
```

### System Metrics
```bash
# Service status
sudo systemctl status tothemoon tothemoon-worker

# Resource usage
htop
df -h
free -h

# Database connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='tothemoon';"
```

### Performance Monitoring
- **Response Time**: Monitor `/health` endpoint response time
- **Database Performance**: Monitor query execution times
- **Memory Usage**: Watch for memory leaks in long-running processes
- **Disk Space**: Monitor database and log file growth

## 🔒 Security Considerations

### Firewall Configuration
```bash
# Basic firewall setup
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable

# Restrict database access (if external)
sudo ufw allow from trusted_ip to any port 5432
```

### Application Security
- **Environment Variables**: Never commit secrets to git
- **Database**: Use strong passwords and restrict network access
- **API Access**: Consider rate limiting for public APIs
- **Updates**: Keep system packages and dependencies updated

### Backup Strategy
```bash
# Database backup script
#!/bin/bash
BACKUP_DIR="/srv/backups/tothemoon"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Database backup
sudo -u postgres pg_dump tothemoon | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Configuration backup
cp /srv/tothemoon/.env $BACKUP_DIR/env_$DATE

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
```

## 🚨 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check service status
sudo systemctl status tothemoon

# Check logs for errors
sudo journalctl -u tothemoon -n 50

# Common fixes
sudo systemctl daemon-reload
sudo systemctl restart tothemoon
```

#### Database Connection Issues
```bash
# Test database connection
sudo -u tothemoon ./venv/bin/python -c "
from src.adapters.db.base import engine
try:
    with engine.connect() as conn:
        print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
"

# Check PostgreSQL status
sudo systemctl status postgresql
```

#### High Memory Usage
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head

# Restart services if needed
sudo systemctl restart tothemoon tothemoon-worker
```

#### Frontend Not Loading
```bash
# Rebuild frontend
cd /srv/tothemoon/frontend
npm install
npm run build

# Check nginx configuration
sudo nginx -t
sudo systemctl reload nginx
```

### Performance Issues
- **Slow API responses**: Check database query performance
- **High CPU usage**: Monitor scheduler frequency settings
- **Memory leaks**: Restart services periodically if needed
- **Database locks**: Monitor long-running queries

### Getting Help
- **Logs**: Always check application and system logs first
- **Health Checks**: Use `/health/scheduler` for system diagnostics
- **Documentation**: Refer to this guide and [Development Guide](DEVELOPMENT.md) for detailed troubleshooting
- **Issues**: Report bugs on GitHub with logs and system information

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] Server meets minimum requirements (Python 3.10+, PostgreSQL 14+)
- [ ] Domain name configured (if using)
- [ ] SSL certificate ready (if using HTTPS)
- [ ] Backup strategy planned

### Deployment
- [ ] System dependencies installed
- [ ] Application deployed and configured
- [ ] Database created and migrated
- [ ] Services configured and started
- [ ] Nginx configured (if using)
- [ ] SSL configured (if using)

### Post-Deployment
- [ ] Health checks passing
- [ ] Services running and enabled
- [ ] Logs showing no errors
- [ ] Frontend accessible
- [ ] API endpoints responding
- [ ] Monitoring configured
- [ ] Backup system tested

### Production Readiness
- [ ] Performance tested under load
- [ ] Security hardening completed
- [ ] Monitoring and alerting configured
- [ ] Documentation updated
- [ ] Team trained on operations
- [ ] Incident response plan ready

## 🔗 Related Documentation

- **[Architecture Guide](ARCHITECTURE.md)** - System design and components
- **[API Reference](API_REFERENCE.md)** - Complete API documentation
- **[Development Guide](DEVELOPMENT.md)** - Development setup and guidelines
- **[Development Guide](DEVELOPMENT.md)** - Debugging and troubleshooting