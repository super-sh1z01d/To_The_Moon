#!/bin/bash

# Production deployment script
# Run this locally to deploy to production server

set -euo pipefail

echo "🚀 Deploying To The Moon to production..."
echo "📅 Started at: $(date)"

# Server configuration
SERVER_HOST=${SERVER_HOST:-"your-production-server.com"}
SERVER_USER=${SERVER_USER:-"root"}
APP_DIR=${APP_DIR:-"/opt/To_The_Moon"}

echo "🔗 Connecting to server: $SERVER_USER@$SERVER_HOST"
echo "📁 App directory: $APP_DIR"

# SSH into server and run deployment
ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" << 'EOF'
set -euo pipefail

echo "🏠 Connected to production server"
echo "📍 Current directory: $(pwd)"

# Navigate to app directory
cd /opt/To_The_Moon || {
    echo "❌ App directory not found at /opt/To_The_Moon"
    echo "📋 Available directories:"
    ls -la /opt/ || true
    exit 1
}

echo "📂 In app directory: $(pwd)"

# Check git status
echo "🔍 Checking git status..."
git status --porcelain || {
    echo "❌ Git status check failed"
    exit 1
}

# Run the deployment script
echo "🚀 Running deployment script..."
bash scripts/deploy.sh

echo "✅ Deployment completed successfully!"
echo "📊 Final system status:"
systemctl status tothemoon.service --no-pager -l || true
systemctl status tothemoon-ws.service --no-pager -l || true

EOF

echo ""
echo "🎉 Production deployment completed!"
echo "📋 Next steps:"
echo "   - Check logs: ssh $SERVER_USER@$SERVER_HOST 'journalctl -u tothemoon.service -f'"
echo "   - Monitor health: curl http://$SERVER_HOST:8000/health"
echo "   - Check monitoring: curl http://$SERVER_HOST:8000/health/detailed"