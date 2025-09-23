# Monitoring Guide

## Quick Start

### Health Check Commands

```bash
# Check overall system health
curl http://localhost:8000/health

# Check specific components
curl http://localhost:8000/health/scheduler
curl http://localhost:8000/health/resources
curl http://localhost:8000/health/performance
curl http://localhost:8000/health/priority
```

### Service Management

```bash
# Check service status
systemctl status tothemoon.service

# View logs
journalctl -u tothemoon.service -f

# Restart service
systemctl restart tothemoon.service
```

## Monitoring Dashboards

### System Health Dashboard

Access the built-in monitoring dashboard at:
```
http://your-server:8000/monitoring/dashboard
```

### Key Metrics to Monitor

#### 1. System Resources
- **CPU Usage**: Should stay below 80%
- **Memory Usage**: Should stay below 85%
- **Disk Usage**: Should stay below 90%

#### 2. Application Performance
- **API Response Time**: Should be < 500ms
- **Token Processing Rate**: Tokens/minute
- **Error Rate**: Should be < 1%

#### 3. External Dependencies
- **DexScreener API**: Response time and availability
- **Database**: Query performance and connections
- **Cache**: Hit rate and memory usage

## Alert Configuration

### Alert Levels

| Level | Description | Response Time | Action Required |
|-------|-------------|---------------|-----------------|
| INFO | Normal operations | None | Monitor |
| WARNING | Potential issues | 15 minutes | Investigate |
| ERROR | Service degradation | 5 minutes | Immediate action |
| CRITICAL | System failure | Immediate | Emergency response |

### Setting Up Alerts

#### Email Alerts
```json
{
  "alert_manager": {
    "email": {
      "enabled": true,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "alerts@yourdomain.com",
      "recipients": ["admin@yourdomain.com"]
    }
  }
}
```

#### Webhook Alerts
```json
{
  "alert_manager": {
    "webhook": {
      "enabled": true,
      "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
      "timeout": 10
    }
  }
}
```

## Performance Monitoring

### Key Performance Indicators (KPIs)

#### System KPIs
- **Uptime**: Target 99.9%
- **Response Time**: P95 < 500ms
- **Throughput**: Requests per second
- **Error Rate**: < 0.1%

#### Business KPIs
- **Token Processing Rate**: Tokens processed per minute
- **Scoring Accuracy**: Percentage of accurate scores
- **Data Freshness**: Age of latest data
- **API Success Rate**: Successful external API calls

### Performance Optimization

#### Automatic Optimizations
The system automatically adjusts:
- Batch sizes based on CPU usage
- Parallelism based on memory usage
- Cache sizes based on hit rates
- Request timeouts based on response times

#### Manual Optimizations
```bash
# Adjust batch size
curl -X POST http://localhost:8000/admin/config \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 50}'

# Clear caches
curl -X POST http://localhost:8000/admin/cache/clear

# Force garbage collection
curl -X POST http://localhost:8000/admin/gc
```

## Troubleshooting Guide

### Common Issues

#### 1. High CPU Usage
**Symptoms**: CPU > 80%, slow response times
**Causes**: Large batch sizes, inefficient queries
**Solutions**:
```bash
# Check current batch size
curl http://localhost:8000/admin/config | jq '.batch_size'

# Reduce batch size
curl -X POST http://localhost:8000/admin/config \
  -d '{"batch_size": 25}'
```

#### 2. High Memory Usage
**Symptoms**: Memory > 85%, potential OOM
**Causes**: Memory leaks, large caches
**Solutions**:
```bash
# Check memory usage
curl http://localhost:8000/health/resources | jq '.memory'

# Clear caches
curl -X POST http://localhost:8000/admin/cache/clear

# Force garbage collection
curl -X POST http://localhost:8000/admin/gc
```

#### 3. API Timeouts
**Symptoms**: Circuit breaker open, fallback mode
**Causes**: External API issues, network problems
**Solutions**:
```bash
# Check circuit breaker status
curl http://localhost:8000/health/performance | jq '.circuit_breakers'

# Check fallback status
curl http://localhost:8000/admin/fallback/status

# Reset circuit breaker (if appropriate)
curl -X POST http://localhost:8000/admin/circuit-breaker/reset
```

#### 4. Database Issues
**Symptoms**: Slow queries, connection errors
**Causes**: Lock contention, connection pool exhaustion
**Solutions**:
```bash
# Check database health
curl http://localhost:8000/health/database

# View active connections
curl http://localhost:8000/admin/database/connections

# Check slow queries
journalctl -u tothemoon.service | grep "slow_query"
```

### Log Analysis

#### Structured Log Format
```json
{
  "ts": "2025-09-23T16:30:28.641517+00:00",
  "level": "ERROR",
  "logger": "api_client",
  "msg": "DexScreener API timeout",
  "module": "resilient_dexscreener_client",
  "func": "get_token_data",
  "line": 234,
  "error": "Request timeout after 30s",
  "token_address": "ABC123...",
  "retry_count": 3,
  "circuit_breaker_state": "HALF_OPEN"
}
```

#### Log Analysis Commands
```bash
# Find errors in last hour
journalctl -u tothemoon.service --since "1 hour ago" | grep ERROR

# Monitor specific component
journalctl -u tothemoon.service -f | grep "health_monitor"

# Count errors by type
journalctl -u tothemoon.service --since "1 day ago" | \
  grep ERROR | jq -r '.error' | sort | uniq -c

# Performance metrics
journalctl -u tothemoon.service --since "1 hour ago" | \
  grep "response_time" | jq -r '.response_time' | \
  awk '{sum+=$1; count++} END {print "Avg:", sum/count "ms"}'
```

## Maintenance Procedures

### Daily Checks
```bash
#!/bin/bash
# daily_health_check.sh

echo "=== Daily Health Check ==="
echo "Date: $(date)"
echo

# System health
echo "System Health:"
curl -s http://localhost:8000/health | jq '.status'

# Resource usage
echo "Resource Usage:"
curl -s http://localhost:8000/health/resources | jq '{cpu, memory, disk}'

# Performance metrics
echo "Performance:"
curl -s http://localhost:8000/health/performance | jq '{avg_response_time, error_rate}'

# Alert summary
echo "Recent Alerts:"
journalctl -u tothemoon.service --since "24 hours ago" | \
  grep -E "WARNING|ERROR|CRITICAL" | wc -l
```

### Weekly Maintenance
```bash
#!/bin/bash
# weekly_maintenance.sh

echo "=== Weekly Maintenance ==="

# Clear old logs
journalctl --vacuum-time=7d

# Update performance baselines
curl -X POST http://localhost:8000/admin/performance/update-baseline

# Generate performance report
curl -s http://localhost:8000/admin/reports/weekly > weekly_report.json

# Check for configuration drift
curl -s http://localhost:8000/admin/config/validate
```

### Monthly Reviews
- Review alert patterns and adjust thresholds
- Analyze performance trends
- Update monitoring configurations
- Review and update documentation

## Integration Examples

### Prometheus Metrics
```python
# Custom metrics endpoint
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests')
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active database connections')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Grafana Dashboard
```json
{
  "dashboard": {
    "title": "To The Moon Monitoring",
    "panels": [
      {
        "title": "System Health",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"to-the-moon\"}",
            "legendFormat": "Uptime"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "http_request_duration_seconds",
            "legendFormat": "Response Time"
          }
        ]
      }
    ]
  }
}
```

### ELK Stack Configuration
```yaml
# logstash.conf
input {
  journald {
    path => "/var/log/journal"
    filter => {
      "_SYSTEMD_UNIT" => "tothemoon.service"
    }
  }
}

filter {
  if [MESSAGE] =~ /^{.*}$/ {
    json {
      source => "MESSAGE"
    }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "to-the-moon-%{+YYYY.MM.dd}"
  }
}
```

## Security Monitoring

### Security Metrics
- Failed authentication attempts
- Unusual API access patterns
- Resource exhaustion attacks
- Configuration changes

### Security Alerts
```json
{
  "security_alerts": {
    "failed_auth_threshold": 10,
    "unusual_traffic_multiplier": 3.0,
    "resource_exhaustion_threshold": 95.0,
    "config_change_notification": true
  }
}
```

### Audit Logging
```python
# Security audit log
{
  "ts": "2025-09-23T16:30:28.641517+00:00",
  "event_type": "config_change",
  "user": "admin",
  "ip_address": "192.168.1.100",
  "resource": "/admin/config",
  "action": "UPDATE",
  "changes": {
    "batch_size": {"old": 100, "new": 50}
  }
}
```

## Best Practices

### 1. Monitoring Strategy
- Monitor what matters to users
- Set meaningful alert thresholds
- Avoid alert fatigue
- Regular review and tuning

### 2. Performance Optimization
- Baseline performance metrics
- Continuous performance testing
- Proactive capacity planning
- Regular performance reviews

### 3. Incident Response
- Clear escalation procedures
- Documented troubleshooting steps
- Post-incident reviews
- Continuous improvement

### 4. Documentation
- Keep monitoring docs updated
- Document all configuration changes
- Maintain runbooks for common issues
- Share knowledge across team