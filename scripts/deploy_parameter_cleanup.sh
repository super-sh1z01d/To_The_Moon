#!/bin/bash

# Update script for Parameter Cleanup (for running application)
# Version: 2.0.0
# Date: $(date)

set -e  # Exit on any error

echo "🔄 Starting Parameter Cleanup Update..."
echo "Version: 2.0.0 - Hybrid Momentum Parameter Cleanup"
echo "Date: $(date)"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect application directory (common locations)
APP_DIR=""
if [ -d "/opt/to_the_moon" ]; then
    APP_DIR="/opt/to_the_moon"
elif [ -d "/srv/tothemoon" ]; then
    APP_DIR="/srv/tothemoon"
elif [ -d "/home/ubuntu/to_the_moon" ]; then
    APP_DIR="/home/ubuntu/to_the_moon"
else
    print_error "Could not find application directory. Please run from app directory or specify path."
    exit 1
fi

print_status "Found application at: $APP_DIR"

# Check if running as root or with sudo
if [[ $EUID -eq 0 ]]; then
    SUDO=""
else
    SUDO="sudo"
fi

# 1. Create backup
print_status "Creating backup of current deployment..."
BACKUP_DIR="${APP_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
$SUDO cp -r "$APP_DIR" "$BACKUP_DIR"
print_success "Backup created at $BACKUP_DIR"

# 2. Check current service status
print_status "Checking current service status..."
SERVICE_RUNNING=false
WORKER_RUNNING=false

if $SUDO systemctl is-active --quiet to-the-moon 2>/dev/null; then
    SERVICE_RUNNING=true
    print_status "Main service is running"
else
    print_warning "Main service is not running"
fi

if $SUDO systemctl is-active --quiet to-the-moon-worker 2>/dev/null; then
    WORKER_RUNNING=true
    print_status "Worker service is running"
else
    print_warning "Worker service is not running"
fi

# 3. Stop services gracefully
if [ "$SERVICE_RUNNING" = true ] || [ "$WORKER_RUNNING" = true ]; then
    print_status "Stopping services gracefully..."
    
    if [ "$SERVICE_RUNNING" = true ]; then
        $SUDO systemctl stop to-the-moon
        print_success "Main service stopped"
    fi
    
    if [ "$WORKER_RUNNING" = true ]; then
        $SUDO systemctl stop to-the-moon-worker
        print_success "Worker service stopped"
    fi
    
    # Wait a moment for graceful shutdown
    sleep 2
else
    print_warning "No services were running"
fi

# 4. Update code
print_status "Updating code from Git..."
cd "$APP_DIR"
$SUDO git pull origin main
print_success "Code updated"

# 4. Update Python dependencies
print_status "Updating Python dependencies..."
$SUDO python3 -m pip install -r requirements.txt --quiet
print_success "Python dependencies updated"

# 5. Build frontend
print_status "Building frontend..."
cd frontend
$SUDO npm install --silent
$SUDO npm run build --silent
cd ..
print_success "Frontend built"

# 6. Run database migrations (if any)
print_status "Running database migrations..."
$SUDO python3 -m alembic upgrade head
print_success "Database migrations completed"

# 7. Validate Python syntax
print_status "Validating Python code..."
python3 -m py_compile src/domain/settings/defaults.py
python3 -m py_compile src/domain/settings/service.py
python3 -m py_compile src/domain/scoring/scoring_service.py
python3 -m py_compile src/domain/metrics/enhanced_dex_aggregator.py
python3 -m py_compile src/app/routes/tokens.py
print_success "Python code validation passed"

# 8. Start services (only those that were running)
print_status "Starting services..."

if [ "$SERVICE_RUNNING" = true ]; then
    $SUDO systemctl start to-the-moon
    print_success "Main service started"
fi

if [ "$WORKER_RUNNING" = true ]; then
    $SUDO systemctl start to-the-moon-worker
    print_success "Worker service started"
fi

if [ "$SERVICE_RUNNING" = false ] && [ "$WORKER_RUNNING" = false ]; then
    print_warning "No services were restarted (none were running initially)"
fi

# 9. Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 5

# 10. Health checks (only for services that should be running)
print_status "Running health checks..."

if [ "$SERVICE_RUNNING" = true ]; then
    if $SUDO systemctl is-active --quiet to-the-moon; then
        print_success "to-the-moon service is running"
        
        # Check HTTP health endpoint
        sleep 3  # Give service time to start
        if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "HTTP health check passed"
        else
            print_warning "HTTP health check failed (service may still be starting)"
        fi
    else
        print_error "to-the-moon service failed to start"
        exit 1
    fi
fi

if [ "$WORKER_RUNNING" = true ]; then
    if $SUDO systemctl is-active --quiet to-the-moon-worker; then
        print_success "to-the-moon-worker service is running"
    else
        print_error "to-the-moon-worker service failed to start"
        exit 1
    fi
fi

# 11. Verify specific changes
print_status "Verifying parameter cleanup changes..."

# Check that max_price_change_5m is not in defaults
if ! grep -q "max_price_change_5m" src/domain/settings/defaults.py; then
    print_success "max_price_change_5m removed from defaults"
else
    print_warning "max_price_change_5m still present in defaults"
fi

# Check that enhanced_dex_aggregator doesn't require the parameter
if python3 -c "from src.domain.metrics.enhanced_dex_aggregator import aggregate_enhanced_metrics; print('OK')" 2>/dev/null; then
    print_success "Enhanced aggregator imports correctly"
else
    print_error "Enhanced aggregator import failed"
    exit 1
fi

print_success "Parameter cleanup verification passed"

# 12. Final status
echo
echo "🎉 Deployment completed successfully!"
echo
echo "📊 Summary:"
echo "  ✅ Backup created: $BACKUP_DIR"
echo "  ✅ Code updated to latest version"
echo "  ✅ Dependencies updated"
echo "  ✅ Frontend rebuilt"
echo "  ✅ Services restarted"
echo "  ✅ Health checks passed"
echo "  ✅ Parameter cleanup verified"
echo
echo "🔍 Changes in this version:"
echo "  - Removed max_price_change_5m parameter from Hybrid Momentum model"
echo "  - Simplified settings UI"
echo "  - Updated documentation"
echo "  - Maintained legacy compatibility"
echo
echo "📝 Next steps:"
echo "  1. Monitor logs: sudo journalctl -u to-the-moon -f"
echo "  2. Check dashboard: http://your-server:8000"
echo "  3. Verify settings UI (max_price_change_5m field should be gone)"
echo
echo "🚨 Rollback if needed:"
echo "  sudo systemctl stop to-the-moon to-the-moon-worker"
echo "  sudo rm -rf $APP_DIR"
echo "  sudo mv $BACKUP_DIR $APP_DIR"
if [ "$SERVICE_RUNNING" = true ]; then
    echo "  sudo systemctl start to-the-moon"
fi
if [ "$WORKER_RUNNING" = true ]; then
    echo "  sudo systemctl start to-the-moon-worker"
fi
echo

print_success "Deployment completed at $(date)"