#!/bin/bash

# New Server Setup Script
# Sets up the new server with backed up data

set -e

NEW_SERVER="67.213.119.189"
NEW_USER="ubuntu"
BACKUP_DIR="$1"

if [ -z "$BACKUP_DIR" ]; then
    echo "❌ Usage: $0 <backup_directory>"
    exit 1
fi

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "🚀 Setting up new server: $NEW_SERVER"
echo "📦 Using backup from: $BACKUP_DIR"

# Test connection
echo "🔗 Testing connection to new server..."
ssh $NEW_USER@$NEW_SERVER "echo 'Connection successful'"

echo "📋 Installing system dependencies..."
ssh $NEW_USER@$NEW_SERVER "
    sudo apt update && sudo apt upgrade -y
    sudo apt install -y python3 python3-pip python3-venv git nginx curl nodejs npm
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
"

echo "🗄️ Setting up database..."
# Check if we have SQLite or PostgreSQL backup
if [ -f "$BACKUP_DIR/dev.db" ]; then
    echo "Found SQLite backup, will use SQLite on new server"
    DB_TYPE="sqlite"
else
    echo "Found PostgreSQL backup, setting up PostgreSQL..."
    DB_TYPE="postgresql"
    ssh $NEW_USER@$NEW_SERVER "
        sudo apt install -y postgresql postgresql-contrib
        sudo systemctl enable postgresql
        sudo systemctl start postgresql
        sudo -u postgres createuser -s tothemoon || echo 'User already exists'
        sudo -u postgres createdb tothemoon -O tothemoon || echo 'Database already exists'
        sudo -u postgres psql -c \"ALTER USER tothemoon PASSWORD 'tothemoon_secure_password';\"
    "
fi

echo "📁 Creating application directory..."
ssh $NEW_USER@$NEW_SERVER "
    sudo mkdir -p /srv/tothemoon
    sudo useradd -r -s /bin/false tothemoon || echo 'User already exists'
    sudo chown -R tothemoon:tothemoon /srv/tothemoon
    sudo chmod 755 /srv/tothemoon
"

echo "📤 Uploading backup files..."
if [ -f "$BACKUP_DIR/tothemoon_db_backup.sql" ]; then
    scp "$BACKUP_DIR/tothemoon_db_backup.sql" $NEW_USER@$NEW_SERVER:/tmp/
fi
scp "$BACKUP_DIR/env_backup" $NEW_USER@$NEW_SERVER:/tmp/env_backup
scp "$BACKUP_DIR/markets_backup.json" $NEW_USER@$NEW_SERVER:/tmp/markets_backup.json || echo "No markets.json to restore"

echo "🔄 Restoring database..."
if [ "$DB_TYPE" = "sqlite" ]; then
    echo "Restoring SQLite database..."
    scp "$BACKUP_DIR/dev.db" $NEW_USER@$NEW_SERVER:/tmp/dev.db
    ssh $NEW_USER@$NEW_SERVER "
        sudo mv /tmp/dev.db /srv/tothemoon/dev.db
        sudo chown tothemoon:tothemoon /srv/tothemoon/dev.db
    "
else
    echo "Restoring PostgreSQL database..."
    ssh $NEW_USER@$NEW_SERVER "
        sudo -u postgres psql -d tothemoon < /tmp/tothemoon_db_backup.sql
        rm /tmp/tothemoon_db_backup.sql
    "
fi

echo "📥 Cloning application code..."
ssh $NEW_USER@$NEW_SERVER "
    sudo -u tothemoon git clone https://github.com/super-sh1z01d/To_The_Moon.git /srv/tothemoon/app
    sudo mv /srv/tothemoon/app/* /srv/tothemoon/
    sudo mv /srv/tothemoon/app/.* /srv/tothemoon/ 2>/dev/null || true
    sudo rmdir /srv/tothemoon/app
    sudo mv /tmp/env_backup /srv/tothemoon/.env
    sudo mv /tmp/markets_backup.json /srv/tothemoon/markets.json 2>/dev/null || true
    sudo chown -R tothemoon:tothemoon /srv/tothemoon
"

echo "🐍 Setting up Python environment..."
ssh $NEW_USER@$NEW_SERVER "
    cd /srv/tothemoon
    sudo -u tothemoon python3 -m venv venv
    sudo -u tothemoon bash -c 'source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt'
"

echo "🔧 Installing systemd service..."
scp "$BACKUP_DIR/tothemoon.service" $NEW_USER@$NEW_SERVER:/tmp/
if [ -d "$BACKUP_DIR/tothemoon.service.d" ]; then
    scp -r "$BACKUP_DIR/tothemoon.service.d" $NEW_USER@$NEW_SERVER:/tmp/
fi

ssh $NEW_USER@$NEW_SERVER "
    sudo mv /tmp/tothemoon.service /etc/systemd/system/
    if [ -d /tmp/tothemoon.service.d ]; then
        sudo mv /tmp/tothemoon.service.d /etc/systemd/system/
    fi
    sudo systemctl daemon-reload
    sudo systemctl enable tothemoon.service
"

echo "🌐 Setting up nginx..."
if [ -f "$BACKUP_DIR/nginx_tothemoon" ]; then
    scp "$BACKUP_DIR/nginx_tothemoon" $NEW_USER@$NEW_SERVER:/tmp/nginx_tothemoon
    ssh $NEW_USER@$NEW_SERVER "
        sudo mv /tmp/nginx_tothemoon /etc/nginx/sites-available/tothemoon
        sudo ln -sf /etc/nginx/sites-available/tothemoon /etc/nginx/sites-enabled/
        sudo rm -f /etc/nginx/sites-enabled/default
        sudo nginx -t && sudo systemctl reload nginx
    "
else
    echo "⚠️ No nginx config found, setting up basic config..."
    ssh $NEW_USER@$NEW_SERVER "sudo tee /etc/nginx/sites-available/tothemoon << 'EOF'
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
EOF
        sudo ln -sf /etc/nginx/sites-available/tothemoon /etc/nginx/sites-enabled/
        sudo rm -f /etc/nginx/sites-enabled/default
        sudo nginx -t && sudo systemctl reload nginx
    "
fi

echo "🔄 Running database migrations..."
ssh $NEW_USER@$NEW_SERVER "
    cd /srv/tothemoon
    sudo -u tothemoon bash -c 'source venv/bin/activate && PYTHONPATH=. python -m alembic upgrade head'
"

echo "🏗️ Building frontend..."
ssh $NEW_USER@$NEW_SERVER "
    cd /srv/tothemoon/frontend
    sudo -u tothemoon npm install
    sudo -u tothemoon npm run build
"

echo "🚀 Starting services..."
ssh $NEW_USER@$NEW_SERVER "
    sudo systemctl start tothemoon.service
    sudo systemctl status tothemoon.service --no-pager
"

echo "✅ Migration completed!"
echo ""
echo "🎯 Next steps:"
echo "1. Test the new server: http://$NEW_SERVER"
echo "2. Update DNS: tothemoon.sh1z01d.ru -> $NEW_SERVER"
echo "3. Test with domain: https://tothemoon.sh1z01d.ru"
echo "4. If everything works, shutdown old server"
echo ""
echo "🔍 Health check:"
echo "curl http://$NEW_SERVER/health"