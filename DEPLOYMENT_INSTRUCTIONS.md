# 🚀 System Stability Monitoring Deployment Instructions

## Server: 5.129.247.78

### Quick Deployment (Recommended)

```bash
# Connect to server
ssh root@5.129.247.78

# Navigate to application directory
cd /srv/tothemoon

# Run deployment script (pulls latest code and restarts services)
bash scripts/deploy.sh
```

### First-Time Installation (if needed)

```bash
# Connect to server as root
ssh root@5.129.247.78

# Run one-time installation script
curl -fsSL https://raw.githubusercontent.com/super-sh1z01d/To_The_Moon/main/scripts/install.sh | bash
```

### Manual Deployment Steps

```bash
# 1. Connect to server
ssh root@5.129.247.78

# 2. Navigate to app directory
cd /srv/tothemoon

# 3. Pull latest code
sudo -u tothemoon git pull origin main

# 4. Install/update dependencies
sudo -u tothemoon ./venv/bin/python -m pip install -r requirements.txt
sudo -u tothemoon ./venv/bin/python -m pip install psutil

# 5. Run migrations
sudo -u tothemoon bash -c "source /etc/tothemoon.env && ./venv/bin/python -m alembic upgrade head"

# 6. Build frontend (if needed)
cd frontend && sudo -u tothemoon npm ci && sudo -u tothemoon npm run build && cd -

# 7. Restart services
systemctl restart tothemoon.service
systemctl restart tothemoon-ws.service

# 8. Check status
systemctl status tothemoon.service
```

## 🏥 Health Check Endpoints

After deployment, verify all monitoring systems are working:

```bash
# Main health check
curl http://127.0.0.1:8000/health

# Monitoring endpoints
curl http://127.0.0.1:8000/health/scheduler
curl http://127.0.0.1:8000/health/resources  
curl http://127.0.0.1:8000/health/performance
curl http://127.0.0.1:8000/health/priority
```

## 📊 System Stability Features Deployed

### ✅ Core Monitoring Systems
- **Structured Logging** with correlation IDs
- **Performance Degradation Detection** with predictive alerts
- **Intelligent Alerting** with hysteresis & escalation
- **Priority-based Token Processing** with load adaptation
- **Fallback Mechanisms** for external dependencies
- **Automatic Performance Optimization**
- **Configuration Hot-reloading**
- **Circuit Breaker Pattern** for API resilience

### ✅ Health Monitoring Endpoints
- `/health/scheduler` - Scheduler health and diagnostics
- `/health/resources` - System resource monitoring  
- `/health/performance` - Performance metrics and trends
- `/health/priority` - Priority processing statistics

### ✅ Self-Healing Capabilities
- Automatic scheduler restart on failures
- Circuit breaker for external API calls
- Load-based processing adjustment
- Memory cleanup and optimization
- Configuration hot-reload without downtime

## 📋 Management Commands

```bash
# Service status
systemctl status tothemoon.service

# View logs
journalctl -u tothemoon.service -f

# Restart service
systemctl restart tothemoon.service

# Stop service
systemctl stop tothemoon.service

# Start service
systemctl start tothemoon.service
```

## 🔧 Troubleshooting

### If deployment fails:
```bash
# Check service status
systemctl status tothemoon.service

# View recent logs
journalctl -u tothemoon.service -n 100

# Check disk space
df -h

# Check memory usage
free -h

# Test monitoring components manually
cd /srv/tothemoon
sudo -u tothemoon ./venv/bin/python -c "
from src.monitoring.health_monitor import get_health_monitor
from src.monitoring.metrics import get_performance_tracker
print('Monitoring components OK')
"
```

### If health checks fail:
```bash
# Check if service is running
systemctl is-active tothemoon.service

# Check port binding
netstat -tlnp | grep :8000

# Test local connection
curl -v http://127.0.0.1:8000/health
```

## 🎉 Expected Results

After successful deployment, you should see:

1. **Service Status**: `systemctl status tothemoon.service` shows "active (running)"
2. **Health Checks**: All `/health/*` endpoints return HTTP 200
3. **Monitoring Active**: Performance tracking, alerting, and priority processing operational
4. **Logs**: Structured JSON logs with correlation IDs in journalctl
5. **Self-Healing**: Automatic recovery from failures and load adaptation

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review service logs: `journalctl -u tothemoon.service -f`
3. Verify all monitoring endpoints are responding
4. Check system resources (CPU, memory, disk)

The system is now production-ready with comprehensive monitoring and self-healing capabilities! 🚀