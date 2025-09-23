# Health Monitoring Endpoints

This document describes the comprehensive health monitoring endpoints available in the To The Moon system.

## Overview

The health monitoring system provides detailed insights into system performance, resource usage, and component status. It includes circuit breaker monitoring, retry statistics, and comprehensive alerting.

## Endpoints

### Basic Health Check

**GET** `/health/`

Simple health check suitable for load balancers and uptime monitoring.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-09-23T10:30:00Z",
  "uptime_seconds": 3600.0,
  "message": "System operational"
}
```

### Detailed Health Status

**GET** `/health/detailed`

Comprehensive system health with detailed component information.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-09-23T10:30:00Z",
  "uptime_seconds": 3600.0,
  "message": "System healthy with 0 alerts",
  "components": {
    "scheduler": {
      "status": "healthy",
      "hot_group_last_run": "2023-09-23T10:29:00Z",
      "cold_group_last_run": "2023-09-23T10:25:00Z",
      "hot_group_processing_time": 30.0,
      "cold_group_processing_time": 120.0,
      "tokens_processed_per_minute": 5.0,
      "error_rate": 2.0,
      "active_jobs": 3,
      "failed_jobs_last_hour": 1
    },
    "resources": {
      "status": "healthy",
      "memory_usage_mb": 512.0,
      "memory_usage_percent": 50.0,
      "cpu_usage_percent": 25.0,
      "disk_usage_percent": 60.0,
      "database_connections": 5,
      "max_database_connections": 20,
      "open_file_descriptors": 100,
      "max_file_descriptors": 1024
    },
    "apis": {
      "dexscreener": {
        "status": "healthy",
        "average_response_time": 150.0,
        "p95_response_time": 300.0,
        "error_rate": 1.0,
        "circuit_breaker_state": "closed",
        "cache_hit_rate": 85.0,
        "requests_per_minute": 30.0,
        "last_successful_call": "2023-09-23T10:29:30Z",
        "consecutive_failures": 0
      }
    }
  },
  "alerts": [],
  "statistics": {
    "total_alerts": 0,
    "critical_alerts": 0,
    "uptime_seconds": 3600.0,
    "last_restart": null
  }
}
```

### Scheduler Health

**GET** `/health/scheduler`

Detailed scheduler performance and status information.

**Response:**
```json
{
  "status": "healthy",
  "hot_group": {
    "last_run": "2023-09-23T10:29:00Z",
    "processing_time": 30.0
  },
  "cold_group": {
    "last_run": "2023-09-23T10:25:00Z",
    "processing_time": 120.0
  },
  "performance": {
    "tokens_processed_per_minute": 5.0,
    "error_rate": 2.0,
    "active_jobs": 3,
    "failed_jobs_last_hour": 1
  },
  "alerts": [],
  "last_check": "2023-09-23T10:30:00Z"
}
```

### Resource Health

**GET** `/health/resources`

System resource usage information including CPU, memory, and disk.

**Response:**
```json
{
  "status": "healthy",
  "memory": {
    "usage_mb": 512.0,
    "usage_percent": 50.0
  },
  "cpu": {
    "usage_percent": 25.0
  },
  "disk": {
    "usage_percent": 60.0
  },
  "database": {
    "connections": 5,
    "max_connections": 20
  },
  "file_descriptors": {
    "open": 100,
    "max": 1024
  },
  "alerts": [],
  "last_check": "2023-09-23T10:30:00Z"
}
```

### API Health

**GET** `/health/apis`

External API performance and circuit breaker status.

**Response:**
```json
{
  "dexscreener": {
    "status": "healthy",
    "performance": {
      "average_response_time": 150.0,
      "p95_response_time": 300.0,
      "error_rate": 1.0,
      "requests_per_minute": 30.0
    },
    "circuit_breaker": {
      "state": "closed",
      "consecutive_failures": 0
    },
    "cache": {
      "hit_rate": 85.0
    },
    "last_successful_call": "2023-09-23T10:29:30Z",
    "client_stats": {
      "total_requests": 100,
      "success_rate": 99.0
    },
    "alerts": [],
    "last_check": "2023-09-23T10:30:00Z"
  }
}
```

### Circuit Breakers Status

**GET** `/health/circuit-breakers`

Status of all circuit breakers in the system.

**Response:**
```json
{
  "circuit_breakers": {
    "dexscreener": {
      "state": "closed",
      "is_healthy": true,
      "failure_rate": 2.0,
      "stats": {
        "total_calls": 100,
        "failures": 2
      }
    }
  },
  "summary": {
    "total_breakers": 1,
    "healthy_breakers": 1,
    "open_breakers": 0,
    "half_open_breakers": 0
  }
}
```

### Retry Managers Status

**GET** `/health/retry-managers`

Status and statistics of all retry managers.

**Response:**
```json
{
  "retry_managers": {
    "dexscreener": {
      "success_rate": 95.0,
      "average_attempts": 1.2,
      "stats": {
        "total_calls": 100,
        "total_retries": 20,
        "success_rate": 95.0,
        "average_attempts": 1.2
      }
    }
  },
  "summary": {
    "total_managers": 1,
    "total_calls": 100,
    "total_retries": 20,
    "overall_success_rate": 95.0
  }
}
```

### System Alerts

**GET** `/health/alerts`

Recent system alerts with optional filtering.

**Query Parameters:**
- `level` (optional): Filter by alert level (info, warning, error, critical)
- `component` (optional): Filter by component name
- `limit` (optional): Maximum number of alerts to return (default: 50)

**Response:**
```json
{
  "alerts": [
    {
      "level": "warning",
      "message": "High CPU usage detected",
      "component": "resources",
      "timestamp": "2023-09-23T10:25:00Z",
      "correlation_id": "alert-123",
      "context": {
        "cpu_percent": 85
      }
    }
  ],
  "summary": {
    "total_alerts": 1,
    "critical_alerts": 0,
    "error_alerts": 0,
    "warning_alerts": 1,
    "info_alerts": 0
  },
  "filters_applied": {
    "level": null,
    "component": null,
    "limit": 50
  }
}
```

### Health Status Summary

**GET** `/health/status`

Quick health status summary suitable for dashboards.

**Response:**
```json
{
  "overall_status": "healthy",
  "uptime_seconds": 3600.0,
  "components_status": {
    "scheduler": "healthy",
    "resources": "healthy",
    "apis": {
      "dexscreener": "healthy"
    }
  },
  "alert_counts": {
    "critical": 0,
    "error": 0,
    "warning": 1,
    "info": 0
  },
  "timestamp": "2023-09-23T10:30:00Z",
  "healthy_components": 3,
  "total_components": 3
}
```

### Reset Monitoring Statistics

**POST** `/health/reset`

Reset all monitoring statistics and counters.

**Response:**
```json
{
  "message": "Monitoring statistics reset successfully",
  "timestamp": "2023-09-23T10:30:00Z",
  "reset_components": [
    "circuit_breakers",
    "retry_managers",
    "resilient_client"
  ]
}
```

## Health Status Values

- **healthy**: All systems operating normally
- **degraded**: Some issues detected but system still functional
- **critical**: Serious issues that may affect system functionality

## Circuit Breaker States

- **closed**: Normal operation, requests allowed
- **open**: Circuit breaker triggered, requests blocked
- **half_open**: Testing if service has recovered

## Alert Levels

- **info**: Informational messages
- **warning**: Issues that should be monitored
- **error**: Errors that need attention
- **critical**: Critical issues requiring immediate action

## Usage Examples

### Basic Health Check for Load Balancer
```bash
curl http://localhost:8000/health/
```

### Get Detailed System Status
```bash
curl http://localhost:8000/health/detailed
```

### Monitor Critical Alerts Only
```bash
curl "http://localhost:8000/health/alerts?level=critical"
```

### Check API Performance
```bash
curl http://localhost:8000/health/apis
```

### Reset Statistics (Admin Only)
```bash
curl -X POST http://localhost:8000/health/reset
```

## Integration

These endpoints can be integrated with:
- Load balancers for health checks
- Monitoring systems like Prometheus
- Alerting systems like PagerDuty
- Dashboard applications
- Automated deployment systems

## Security Considerations

- The `/health/reset` endpoint should be restricted to admin users
- Consider rate limiting for health endpoints
- Sensitive information is not exposed in health responses
- All endpoints use structured logging for audit trails