# Scheduler Optimization Guide

## 🎯 Overview

This document describes the comprehensive scheduler optimization implemented to leverage the new powerful server and dramatically improve token processing performance.

## 🚀 Key Optimizations

### 1. Parallel API Processing
- **Before**: Sequential API calls (1 token at a time)
- **After**: Parallel API calls (8-16 concurrent requests)
- **Expected Improvement**: 3-5x faster API processing

### 2. Adaptive Batch Sizing
- **Before**: Fixed batch sizes (35/70 tokens)
- **After**: Dynamic sizing based on system load and performance
- **Range**: 10-150 tokens per batch
- **Expected Improvement**: Better resource utilization

### 3. Dynamic Timeouts
- **Before**: Fixed 5-second timeouts
- **After**: Adaptive timeouts based on API performance
- **Range**: 1.5-5.0 seconds
- **Expected Improvement**: Reduced timeout issues

### 4. Async HTTP Client
- **Before**: Sync HTTP client with thread pool
- **After**: Native async HTTP client
- **Expected Improvement**: Lower overhead, better concurrency

### 5. Performance Monitoring
- **Before**: Basic processing metrics
- **After**: Comprehensive performance tracking
- **Features**: Tokens/second, resource usage, API response times

## 📊 Performance Profiles

### High Performance (New Server)
- **CPU Cores**: 4+
- **Memory**: 8GB+
- **Hot Concurrency**: 12
- **Cold Concurrency**: 16
- **Max Batch Size**: 150

### Medium Performance
- **CPU Cores**: 2-4
- **Memory**: 4-8GB
- **Hot Concurrency**: 8
- **Cold Concurrency**: 12
- **Max Batch Size**: 100

### Low Performance
- **CPU Cores**: 1-2
- **Memory**: 2-4GB
- **Hot Concurrency**: 4
- **Cold Concurrency**: 6
- **Max Batch Size**: 50

## ⚙️ Configuration

### Environment Variables

```bash
# Enable optimizations
ENABLE_SCHEDULER_OPTIMIZATION=true
ENABLE_PARALLEL_PROCESSING=true
ENABLE_ADAPTIVE_BATCHING=true
ENABLE_DYNAMIC_TIMEOUTS=true

# Concurrency settings
MAX_CONCURRENT_HOT=12
MAX_CONCURRENT_COLD=16
MAX_CONCURRENT_UNDER_LOAD=4

# Timeout settings
TIMEOUT_HOT=3.0
TIMEOUT_COLD=2.0
TIMEOUT_UNDER_LOAD=1.5

# Batch sizing
MIN_BATCH_SIZE=10
MAX_BATCH_SIZE=150

# Performance thresholds
HIGH_CPU_THRESHOLD=80.0
MEDIUM_CPU_THRESHOLD=60.0
LOW_CPU_THRESHOLD=30.0

HIGH_MEMORY_THRESHOLD=85.0
MEDIUM_MEMORY_THRESHOLD=70.0
LOW_MEMORY_THRESHOLD=50.0

# Cache settings
CACHE_TTL_HOT=15
CACHE_TTL_COLD=30
```

### Runtime Configuration

```python
from src.scheduler.optimization_config import update_optimization_config

# Update concurrency at runtime
update_optimization_config({
    "max_concurrent_hot": 16,
    "max_concurrent_cold": 20,
    "enable_adaptive_batching": True
})
```

## 🧪 Testing

### Performance Benchmark

```bash
# Run performance comparison
cd /srv/tothemoon
sudo -u tothemoon bash -c 'source venv/bin/activate && PYTHONPATH=. python scripts/test_scheduler_optimization.py'
```

### Load Testing

```bash
# Monitor system resources during processing
htop
# or
watch -n 1 'ps aux | grep python | head -10'
```

### API Performance

```bash
# Monitor API response times
curl -w "@curl-format.txt" -s "http://localhost:8000/tokens?limit=50"
```

## 📈 Expected Results

### Processing Speed
- **Hot Group**: 2-4x faster processing
- **Cold Group**: 3-5x faster processing
- **Overall**: 2-4x improvement in tokens/second

### Resource Utilization
- **CPU**: Better multi-core utilization
- **Memory**: More efficient memory usage
- **Network**: Reduced connection overhead

### Reliability
- **Timeouts**: 50-70% reduction in timeout errors
- **Failures**: Better error handling and recovery
- **Consistency**: More predictable performance

## 🔍 Monitoring

### Key Metrics

```bash
# Monitor optimization performance
journalctl -u tothemoon.service -f | grep -E "(optimized_group_processing|parallel_batch|tokens_per_second)"

# Monitor system resources
journalctl -u tothemoon.service -f | grep -E "(cpu_usage|memory_usage|processing_time)"

# Monitor API performance
journalctl -u tothemoon.service -f | grep -E "(api_call|timeout|circuit_breaker)"
```

### Performance Dashboard

```bash
# Get current performance stats
curl "http://localhost:8000/health/scheduler" | jq '.performance'

# Get system metrics
curl "http://localhost:8000/health/system" | jq '.resources'
```

## 🚨 Troubleshooting

### High CPU Usage
```bash
# Reduce concurrency
export MAX_CONCURRENT_HOT=6
export MAX_CONCURRENT_COLD=8
sudo systemctl restart tothemoon.service
```

### High Memory Usage
```bash
# Reduce batch sizes
export MAX_BATCH_SIZE=50
export MIN_BATCH_SIZE=5
sudo systemctl restart tothemoon.service
```

### API Timeouts
```bash
# Increase timeouts
export TIMEOUT_HOT=5.0
export TIMEOUT_COLD=4.0
sudo systemctl restart tothemoon.service
```

### Poor Performance
```bash
# Disable optimizations temporarily
export ENABLE_SCHEDULER_OPTIMIZATION=false
sudo systemctl restart tothemoon.service

# Check logs for errors
journalctl -u tothemoon.service -n 100 | grep -i error
```

## 🔄 Rollback Procedure

### Quick Rollback
```bash
cd /srv/tothemoon
git checkout main
sudo systemctl restart tothemoon.service
```

### Disable Optimizations Only
```bash
# Set environment variable
echo 'ENABLE_SCHEDULER_OPTIMIZATION=false' | sudo tee -a /etc/tothemoon.env
sudo systemctl restart tothemoon.service
```

### Gradual Rollback
```bash
# Disable parallel processing only
export ENABLE_PARALLEL_PROCESSING=false
sudo systemctl restart tothemoon.service

# If stable, disable other optimizations
export ENABLE_ADAPTIVE_BATCHING=false
export ENABLE_DYNAMIC_TIMEOUTS=false
sudo systemctl restart tothemoon.service
```

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] Backup current system state
- [ ] Test optimizations in development
- [ ] Review system resources
- [ ] Plan rollback procedure

### Deployment
- [ ] Deploy optimization code
- [ ] Configure environment variables
- [ ] Restart service
- [ ] Verify health endpoints
- [ ] Monitor initial performance

### Post-Deployment
- [ ] Monitor performance for 24 hours
- [ ] Check error rates
- [ ] Validate processing speeds
- [ ] Adjust configuration if needed

### Success Criteria
- [ ] 2x+ improvement in processing speed
- [ ] No increase in error rates
- [ ] Stable system resource usage
- [ ] All API endpoints responding

## 🎉 Benefits

### Performance
- **3-5x faster** token processing
- **Better resource utilization** on new server
- **Reduced API timeouts** and failures
- **Adaptive performance** under varying loads

### Scalability
- **Higher token capacity** (5000+ tokens)
- **Better handling** of traffic spikes
- **Efficient resource usage** during low activity
- **Future-proof architecture** for growth

### Reliability
- **Comprehensive error handling**
- **Circuit breaker protection**
- **Graceful degradation** under load
- **Detailed monitoring** and alerting

### Maintainability
- **Configurable parameters**
- **Runtime adjustments**
- **Comprehensive testing**
- **Clear rollback procedures**