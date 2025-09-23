# Quick Monitoring Reference

## 🚀 Essential Health Checks

### One-Line System Status
```bash
curl -s http://localhost:8000/health | jq -r '.status'
```

### Complete Health Overview
```bash
echo "=== System Health Overview ==="
echo "Main: $(curl -s http://localhost:8000/health | jq -r '.status')"
echo "Scheduler: $(curl -s http://localhost:8000/health/scheduler | jq -r '.status // "error"')"
echo "Resources: $(curl -s http://localhost:8000/health/resources | jq -r '.status')"
echo "Performance: $(curl -s http://localhost:8000/health/performance | jq -r '.status // "ok"')"
echo "Priority: $(curl -s http://localhost:8000/health/priority | jq -r '.status')"
```

## 🔧 Service Management

```bash
# Check service status
systemctl status tothemoon.service

# View real-time logs
journalctl -u tothemoon.service -f

# Restart if needed
systemctl restart tothemoon.service

# Check resource usage
curl -s http://localhost:8000/health/resources | jq '{cpu, memory, disk}'
```

## 🚨 Emergency Commands

### If System is Unresponsive
```bash
# Check if process is running
ps aux | grep uvicorn

# Check system resources
top -p $(pgrep -f uvicorn)

# Force restart
systemctl restart tothemoon.service

# Check logs for errors
journalctl -u tothemoon.service --since "10 minutes ago" | grep ERROR
```

### If High Resource Usage
```bash
# Check current usage
curl -s http://localhost:8000/health/resources

# Clear caches (if endpoint available)
curl -X POST http://localhost:8000/admin/cache/clear

# Reduce batch size (if endpoint available)
curl -X POST http://localhost:8000/admin/config -d '{"batch_size": 25}'
```

## 📊 Key Metrics to Watch

| Metric | Healthy Range | Action if Exceeded |
|--------|---------------|-------------------|
| CPU Usage | < 80% | Check for runaway processes |
| Memory Usage | < 85% | Clear caches, restart if needed |
| Disk Usage | < 90% | Clean logs, check database size |
| Response Time | < 500ms | Check performance endpoint |
| Error Rate | < 1% | Check logs for patterns |

## 🔍 Troubleshooting Quick Reference

### Common Issues

**Service Won't Start**
```bash
# Check configuration
journalctl -u tothemoon.service | tail -20

# Verify database
python3 -c "from src.adapters.db.deps import get_db; print('DB OK')"

# Check port availability
netstat -tlnp | grep :8000
```

**High Memory Usage**
```bash
# Check memory details
curl -s http://localhost:8000/health/resources | jq '.memory'

# Monitor memory over time
watch -n 5 'curl -s http://localhost:8000/health/resources | jq .memory.percent'
```

**API Timeouts**
```bash
# Check circuit breaker status
curl -s http://localhost:8000/health/performance | jq '.circuit_breakers'

# Check external API health
curl -s "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112"
```

## 📈 Performance Monitoring

### Response Time Monitoring
```bash
# Test API response time
time curl -s http://localhost:8000/health > /dev/null

# Monitor over time
for i in {1..10}; do
  time curl -s http://localhost:8000/tokens?limit=1 > /dev/null
  sleep 1
done
```

### Resource Monitoring
```bash
# Continuous resource monitoring
watch -n 10 'curl -s http://localhost:8000/health/resources | jq "{cpu: .cpu.percent, memory: .memory.percent, disk: .disk.percent}"'
```

## 🚨 Alert Thresholds

### Critical Alerts (Immediate Action)
- Service down (health check fails)
- Memory usage > 95%
- Disk usage > 95%
- Error rate > 10%

### Warning Alerts (Monitor Closely)
- CPU usage > 80%
- Memory usage > 85%
- Response time > 1000ms
- Error rate > 1%

### Info Alerts (Awareness)
- Performance degradation detected
- Circuit breaker activated
- Fallback mode engaged

## 📞 Emergency Contacts

When system issues occur:

1. **Check this guide first**
2. **Review logs**: `journalctl -u tothemoon.service -f`
3. **Try basic restart**: `systemctl restart tothemoon.service`
4. **Check external dependencies** (DexScreener API)
5. **Escalate if needed**

## 🔗 Useful Links

- **Full Monitoring Guide**: [docs/MONITORING_GUIDE.md](MONITORING_GUIDE.md)
- **System Stability**: [docs/SYSTEM_STABILITY.md](SYSTEM_STABILITY.md)
- **API Reference**: [docs/API_REFERENCE.md](API_REFERENCE.md)
- **Deployment Guide**: [docs/DEPLOYMENT.md](DEPLOYMENT.md)