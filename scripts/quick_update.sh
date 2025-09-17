#!/bin/bash

# Quick update script for Parameter Cleanup
# For running applications - minimal downtime

set -e

echo "⚡ Quick Update: Parameter Cleanup"
echo "Estimated downtime: < 30 seconds"
echo

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Detect sudo
if [[ $EUID -eq 0 ]]; then
    SUDO=""
else
    SUDO="sudo"
fi

# Quick backup (just the critical files)
print_status "Creating quick backup..."
BACKUP_DIR="/tmp/to_the_moon_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r src/ "$BACKUP_DIR/" 2>/dev/null || true
cp -r frontend/src/ "$BACKUP_DIR/frontend_src/" 2>/dev/null || true

# Update code
print_status "Pulling latest changes..."
git pull origin main

# Build frontend quickly
print_status "Building frontend..."
cd frontend
npm run build --silent
cd ..

# Restart services with minimal downtime
print_status "Restarting services..."

# Check what's running
MAIN_RUNNING=$($SUDO systemctl is-active to-the-moon 2>/dev/null || echo "inactive")
WORKER_RUNNING=$($SUDO systemctl is-active to-the-moon-worker 2>/dev/null || echo "inactive")

# Restart main service
if [ "$MAIN_RUNNING" = "active" ]; then
    $SUDO systemctl restart to-the-moon
    print_success "Main service restarted"
fi

# Restart worker
if [ "$WORKER_RUNNING" = "active" ]; then
    $SUDO systemctl restart to-the-moon-worker
    print_success "Worker service restarted"
fi

# Quick health check
sleep 2
if [ "$MAIN_RUNNING" = "active" ]; then
    if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Health check passed"
    else
        echo "⚠️  Health check failed - check logs"
    fi
fi

echo
echo "✅ Quick update completed!"
echo "🔍 Check: Settings UI should no longer have 'Максимальное изменение цены' field"
echo "📊 Monitor: sudo journalctl -u to-the-moon -f"
echo
echo "🚨 Rollback if needed:"
echo "  cp -r $BACKUP_DIR/src/* src/"
echo "  cp -r $BACKUP_DIR/frontend_src/* frontend/src/"
echo "  cd frontend && npm run build && cd .."
echo "  sudo systemctl restart to-the-moon"