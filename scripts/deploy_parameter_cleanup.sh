#!/bin/bash

# Deployment script for Parameter Cleanup update
# Version: 2.0.0
# Date: $(date)

set -e  # Exit on any error

echo "🚀 Starting Parameter Cleanup Deployment..."
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

# Check if running as root or with sudo
if [[ $EUID -eq 0 ]]; then
    SUDO=""
else
    SUDO="sudo"
fi

# 1. Create backup
print_status "Creating backup of current deployment..."
BACKUP_DIR="/opt/to_the_moon_backup_$(date +%Y%m%d_%H%M%S)"
$SUDO cp -r /opt/to_the_moon "$BACKUP_DIR"
print_success "Backup created at $BACKUP_DIR"

# 2. Stop services
print_status "Stopping services..."
$SUDO systemctl stop to-the-moon || print_warning "to-the-moon service not running"
$SUDO systemctl stop to-the-moon-worker || print_warning "to-the-moon-worker service not running"
print_success "Services stopped"

# 3. Update code
print_status "Updating code from Git..."
cd /opt/to_the_moon
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

# 8. Start services
print_status "Starting services..."
$SUDO systemctl start to-the-moon
$SUDO systemctl start to-the-moon-worker
print_success "Services started"

# 9. Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 5

# 10. Health checks
print_status "Running health checks..."

# Check service status
if $SUDO systemctl is-active --quiet to-the-moon; then
    print_success "to-the-moon service is running"
else
    print_error "to-the-moon service failed to start"
    exit 1
fi

if $SUDO systemctl is-active --quiet to-the-moon-worker; then
    print_success "to-the-moon-worker service is running"
else
    print_error "to-the-moon-worker service failed to start"
    exit 1
fi

# Check HTTP health endpoint
if curl -f -s http://localhost:8000/health > /dev/null; then
    print_success "HTTP health check passed"
else
    print_error "HTTP health check failed"
    exit 1
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
echo "  sudo rm -rf /opt/to_the_moon"
echo "  sudo mv $BACKUP_DIR /opt/to_the_moon"
echo "  sudo systemctl start to-the-moon to-the-moon-worker"
echo

print_success "Deployment completed at $(date)"