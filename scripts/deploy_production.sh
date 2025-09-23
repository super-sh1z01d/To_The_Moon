#!/bin/bash
# Production deployment script for To The Moon with System Stability Monitoring

set -e

echo "🚀 Deploying To The Moon with System Stability Monitoring..."
echo "📅 Deployment started at: $(date)"
echo "🖥️  Server: $(hostname -I | awk '{print $1}' || echo 'localhost')"

# Check if running as root for systemd operations
if [[ $EUID -eq 0 ]]; then
   echo "⚠️  Running as root - systemd operations enabled"
   SYSTEMD_ENABLED=true
   USER_NAME=${SUDO_USER:-ubuntu}
else
   echo "ℹ️  Running as user - systemd operations disabled"
   SYSTEMD_ENABLED=false
   USER_NAME=$(whoami)
fi

# Environment setup
export APP_ENV=prod
export LOG_LEVEL=INFO
export SCHEDULER_ENABLED=true
export PYTHONPATH=$(pwd)

echo "🔧 Environment configured:"
echo "   APP_ENV: $APP_ENV"
echo "   LOG_LEVEL: $LOG_LEVEL"
echo "   SCHEDULER_ENABLED: $SCHEDULER_ENABLED"
echo "   USER: $USER_NAME"

# Update system packages (if root)
if [ "$SYSTEMD_ENABLED" = true ]; then
    echo "📦 Updating system packages..."
    apt-get update -qq
    apt-get install -y python3-pip python3-venv nodejs npm curl jq htop
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt --user
else
    python3 -m pip install -r requirements.txt --user
fi

# Install additional monitoring dependencies
echo "📊 Installing monitoring dependencies..."
pip3 install psutil --user || python3 -m pip install psutil --user

# Database setup
echo "🗄️  Setting up database..."
if [ ! -f "prod.db" ]; then
    echo "Creating new production database..."
fi

# Run database migrations
echo "🔄 Running database migrations..."
python3 -m alembic upgrade head

# Build frontend
echo "🎨 Building frontend..."
if [ -d "frontend" ]; then
    cd frontend
    if command -v npm &> /dev/null; then
        npm install --production
        npm run build
    else
        echo "⚠️  npm not found, skipping frontend build"
    fi
    cd -
else
    echo "⚠️  Frontend directory not found, skipping build"
fi

# Test monitoring components
echo "🔍 Testing monitoring components..."
python3 -c "
import sys
sys.path.append('.')
try:
    from src.monitoring.health_monitor import get_health_monitor
    from src.monitoring.metrics import get_performance_tracker
    from src.monitoring.alert_manager import get_alert_manager
    from src.scheduler.monitoring import get_priority_processor
    print('✅ All monitoring modules imported successfully')
except Exception as e:
    print(f'❌ Monitoring module import failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

# Create production environment file
echo "📝 Creating production environment..."
cat > .env.prod << EOF
APP_ENV=prod
LOG_LEVEL=INFO
SCHEDULER_ENABLED=true
DATABASE_URL=sqlite:///./prod.db
FRONTEND_DIST_PATH=frontend/dist
EOF

# Create systemd service file if running as root
if [ "$SYSTEMD_ENABLED" = true ]; then
    echo "📋 Creating systemd service..."
    cat > /etc/systemd/system/to-the-moon.service << EOF
[Unit]
Description=To The Moon - Solana Token Scoring System with Monitoring
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$(pwd)
Environment=PYTHONPATH=$(pwd)
Environment=APP_ENV=prod
Environment=LOG_LEVEL=INFO
Environment=SCHEDULER_ENABLED=true
ExecStart=/usr/bin/python3 -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=to-the-moon

# Watchdog configuration
WatchdogSec=30
NotifyAccess=main

# Resource limits
LimitNOFILE=65536
MemoryMax=4G
CPUQuota=300%

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable to-the-moon.service
    echo "✅ Systemd service created and enabled"
    
    # Stop existing service if running
    systemctl stop to-the-moon.service 2>/dev/null || true
fi

# Start the application
echo "🚀 Starting To The Moon application..."

if [ "$SYSTEMD_ENABLED" = true ]; then
    systemctl start to-the-moon.service
    echo "✅ Application started via systemd"
    
    # Show status
    sleep 5
    systemctl status to-the-moon.service --no-pager
else
    echo "Starting application in background..."
    # Kill existing process
    pkill -f "uvicorn src.app.main:app" 2>/dev/null || true
    sleep 2
    
    nohup python3 -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000 > to-the-moon.log 2>&1 &
    APP_PID=$!
    echo "✅ Application started with PID: $APP_PID"
    echo "📋 Logs: tail -f to-the-moon.log"
fi

# Wait for application to start
echo "⏳ Waiting for application to start..."
sleep 10

# Test health endpoints
echo "🏥 Testing health endpoints..."
for i in {1..5}; do
    if curl -f -s http://localhost:8000/health/scheduler >/dev/null 2>&1; then
        echo "✅ Scheduler health check: OK"
        break
    else
        echo "⏳ Attempt $i/5: Waiting for scheduler..."
        sleep 5
    fi
done

curl -f -s http://localhost:8000/health/resources >/dev/null && echo "✅ Resources health check: OK" || echo "❌ Resources health check: FAILED"
curl -f -s http://localhost:8000/health/performance >/dev/null && echo "✅ Performance health check: OK" || echo "❌ Performance health check: FAILED"
curl -f -s http://localhost:8000/health/priority >/dev/null && echo "✅ Priority health check: OK" || echo "❌ Priority health check: FAILED"

echo ""
echo "🎉 Deployment completed!"
echo ""
echo "📊 Monitoring endpoints:"
echo "  - Health: http://$(hostname -I | awk '{print $1}' || echo 'localhost'):8000/health/scheduler"
echo "  - Resources: http://$(hostname -I | awk '{print $1}' || echo 'localhost'):8000/health/resources"
echo "  - Performance: http://$(hostname -I | awk '{print $1}' || echo 'localhost'):8000/health/performance"
echo "  - Priority: http://$(hostname -I | awk '{print $1}' || echo 'localhost'):8000/health/priority"
echo ""
echo "📋 Management commands:"
if [ "$SYSTEMD_ENABLED" = true ]; then
    echo "  - Status: systemctl status to-the-moon"
    echo "  - Logs: journalctl -u to-the-moon -f"
    echo "  - Restart: systemctl restart to-the-moon"
    echo "  - Stop: systemctl stop to-the-moon"
else
    echo "  - Logs: tail -f to-the-moon.log"
    echo "  - Stop: pkill -f 'uvicorn src.app.main:app'"
fi
echo ""
echo "🚀 System Stability Monitoring is LIVE!"