#!/bin/bash
# Production deployment script for To The Moon with monitoring

set -e

echo "🚀 Deploying To The Moon with System Stability Monitoring..."

# Check if running as root for systemd operations
if [[ $EUID -eq 0 ]]; then
   echo "⚠️  Running as root - systemd operations enabled"
   SYSTEMD_ENABLED=true
else
   echo "ℹ️  Running as user - systemd operations disabled"
   SYSTEMD_ENABLED=false
fi

# Environment setup
export APP_ENV=prod
export LOG_LEVEL=INFO
export SCHEDULER_ENABLED=true

# Install dependencies
echo "📦 Installing Python dependencies..."
python3 -m pip install -r requirements.txt

# Database migrations
echo "🗄️  Running database migrations..."
python3 -m alembic upgrade head

# Build frontend
echo "🎨 Building frontend..."
cd frontend && npm install && npm run build && cd -

# Test monitoring endpoints
echo "🔍 Testing monitoring endpoints..."
python3 -c "
import sys
sys.path.append(.)
try:
    from src.monitoring.health_monitor import get_health_monitor
    from src.monitoring.metrics import get_performance_tracker, get_performance_degradation_detector
    from src.monitoring.alert_manager import get_alert_manager, get_intelligent_alerting_engine
    from src.scheduler.monitoring import get_priority_processor, get_config_hot_reloader
    print(✅ All monitoring modules imported successfully)
except Exception as e:
    print(f❌ Monitoring module import failed: {e})
    sys.exit(1)
"

# Create systemd service file if running as root
if [ "$SYSTEMD_ENABLED" = true ]; then
    echo "📋 Creating systemd service..."
    cat > /etc/systemd/system/to-the-moon.service << EOF
[Unit]
Description=To The Moon - Solana Token Scoring System
After=network.target
Wants=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
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
MemoryMax=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable to-the-moon.service
    echo "✅ Systemd service created and enabled"
fi

# Start the application
echo "🚀 Starting To The Moon application..."

if [ "$SYSTEMD_ENABLED" = true ]; then
    systemctl start to-the-moon.service
    echo "✅ Application started via systemd"
    
    # Show status
    sleep 3
    systemctl status to-the-moon.service --no-pager
else
    echo "Starting application in background..."
    nohup python3 -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
    APP_PID=$!
    echo "✅ Application started with PID: $APP_PID"
    echo "📋 Logs: tail -f app.log"
fi

# Wait for application to start
echo "⏳ Waiting for application to start..."
sleep 5

# Test health endpoints
echo "🏥 Testing health endpoints..."
curl -f http://localhost:8000/health/scheduler || echo "❌ Scheduler health check failed"
curl -f http://localhost:8000/health/resources || echo "❌ Resources health check failed"
curl -f http://localhost:8000/health/performance || echo "❌ Performance health check failed"
curl -f http://localhost:8000/health/priority || echo "❌ Priority health check failed"

echo ""
echo "🎉 Deployment completed!"
echo ""
echo "📊 Monitoring endpoints:"
echo "  - Health: http://localhost:8000/health/scheduler"
echo "  - Resources: http://localhost:8000/health/resources"
echo "  - Performance: http://localhost:8000/health/performance"
echo "  - Priority: http://localhost:8000/health/priority"
echo ""
echo "📋 Management commands:"
if [ "$SYSTEMD_ENABLED" = true ]; then
    echo "  - Status: systemctl status to-the-moon"
    echo "  - Logs: journalctl -u to-the-moon -f"
    echo "  - Restart: systemctl restart to-the-moon"
    echo "  - Stop: systemctl stop to-the-moon"
else
    echo "  - Logs: tail -f app.log"
    echo "  - Stop: kill $APP_PID"
fi
echo ""

