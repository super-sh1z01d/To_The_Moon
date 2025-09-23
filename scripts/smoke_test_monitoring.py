#!/usr/bin/env python3
"""
Smoke test for To The Moon monitoring systems.
Tests all monitoring components in production environment.
"""

import sys
import time
import requests
import json
from datetime import datetime

def test_health_endpoints():
    """Test all health monitoring endpoints."""
    endpoints = [
        "/health/scheduler",
        "/health/resources", 
        "/health/apis",
        "/health/performance",
        "/health/priority"
    ]
    
    base_url = "http://localhost:8000"
    results = {}
    
    print("🏥 Testing health endpoints...")
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                results[endpoint] = {
                    "status": "✅ PASS",
                    "response_time": response.elapsed.total_seconds(),
                    "data": data
                }
                print(f"  {endpoint}: ✅ OK ({response.elapsed.total_seconds():.2f}s)")
            else:
                results[endpoint] = {
                    "status": "❌ FAIL",
                    "error": f"HTTP {response.status_code}"
                }
                print(f"  {endpoint}: ❌ FAIL (HTTP {response.status_code})")
        except Exception as e:
            results[endpoint] = {
                "status": "❌ ERROR", 
                "error": str(e)
            }
            print(f"  {endpoint}: ❌ ERROR ({e})")
    
    return results

def test_monitoring_components():
    """Test monitoring components initialization."""
    print("🔧 Testing monitoring components...")
    
    try:
        # Test imports
        from src.monitoring.health_monitor import get_health_monitor
        from src.monitoring.metrics import (
            get_performance_tracker, 
            get_performance_degradation_detector,
            get_structured_logger
        )
        from src.monitoring.alert_manager import (
            get_alert_manager, 
            get_intelligent_alerting_engine
        )
        from src.scheduler.monitoring import (
            get_priority_processor,
            get_config_hot_reloader
        )
        
        print("  ✅ All monitoring modules imported successfully")
        
        # Test component initialization
        health_monitor = get_health_monitor()
        performance_tracker = get_performance_tracker()
        degradation_detector = get_performance_degradation_detector()
        structured_logger = get_structured_logger()
        alert_manager = get_alert_manager()
        intelligent_alerting = get_intelligent_alerting_engine()
        priority_processor = get_priority_processor()
        config_reloader = get_config_hot_reloader()
        
        print("  ✅ All monitoring components initialized successfully")
        
        # Test basic functionality
        structured_logger.info("Smoke test message", test_type="smoke_test")
        print("  ✅ Structured logging working")
        
        stats = priority_processor.get_priority_statistics()
        print(f"  ✅ Priority processor working (stats: {len(stats)} keys)")
        
        alert_stats = alert_manager.get_alert_statistics()
        print(f"  ✅ Alert manager working (rules: {alert_stats.get(total_rules, 0)})")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Component test failed: {e}")
        return False

def test_performance_simulation():
    """Simulate some load and test performance monitoring."""
    print("⚡ Testing performance monitoring...")
    
    try:
        from src.monitoring.metrics import get_performance_degradation_detector
        degradation_detector = get_performance_degradation_detector()
        
        # Simulate some metrics
        test_metrics = [
            {"cpu_usage": 45.0, "memory_usage": 60.0, "response_time": 1.2},
            {"cpu_usage": 55.0, "memory_usage": 65.0, "response_time": 1.5},
            {"cpu_usage": 65.0, "memory_usage": 70.0, "response_time": 2.1},
            {"cpu_usage": 75.0, "memory_usage": 75.0, "response_time": 2.8},
            {"cpu_usage": 85.0, "memory_usage": 80.0, "response_time": 3.5},
        ]
        
        for i, metrics in enumerate(test_metrics):
            degradation_detector.record_performance_metric("smoke_test", metrics)
            time.sleep(0.1)  # Small delay
        
        # Get health status
        health_status = degradation_detector.get_performance_health_status("smoke_test")
        print(f"  ✅ Performance monitoring working (status: {health_status[status]})")
        
        # Get predictive alerts
        alerts = degradation_detector.get_predictive_alerts("smoke_test", forecast_minutes=15)
        print(f"  ✅ Predictive alerting working ({len(alerts)} alerts)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Performance simulation failed: {e}")
        return False

def test_intelligent_alerting():
    """Test intelligent alerting system."""
    print("🧠 Testing intelligent alerting...")
    
    try:
        from src.monitoring.alert_manager import get_intelligent_alerting_engine
        from src.monitoring.models import HealthAlert, AlertLevel
        
        intelligent_alerting = get_intelligent_alerting_engine()
        
        # Record some metrics to trigger threshold rules
        intelligent_alerting.record_metric("smoke_test", "cpu_usage", 85.0)
        intelligent_alerting.record_metric("smoke_test", "memory_usage", 90.0)
        intelligent_alerting.record_metric("smoke_test", "response_time", 6.0)
        
        print("  ✅ Metrics recorded for intelligent alerting")
        
        # Get statistics
        stats = intelligent_alerting.get_intelligent_alerting_statistics()
        print(f"  ✅ Intelligent alerting stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Intelligent alerting test failed: {e}")
        return False

def generate_report(health_results, component_test, performance_test, alerting_test):
    """Generate smoke test report."""
    print("\n" + "="*60)
    print("🎯 SMOKE TEST REPORT")
    print("="*60)
    
    # Overall status
    all_health_passed = all(r["status"] == "✅ PASS" for r in health_results.values())
    overall_status = all_health_passed and component_test and performance_test and alerting_test
    
    print(f"Overall Status: {✅ PASS if overall_status else ❌ FAIL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Health endpoints summary
    print("Health Endpoints:")
    for endpoint, result in health_results.items():
        status = result["status"]
        if "response_time" in result:
            print(f"  {endpoint}: {status} ({result[response_time]:.2f}s)")
        else:
            print(f"  {endpoint}: {status}")
    print()
    
    # Component tests summary
    print("Component Tests:")
    print(f"  Monitoring Components: {✅ PASS if component_test else ❌ FAIL}")
    print(f"  Performance Monitoring: {✅ PASS if performance_test else ❌ FAIL}")
    print(f"  Intelligent Alerting: {✅ PASS if alerting_test else ❌ FAIL}")
    print()
    
    # Recommendations
    if not overall_status:
        print("❌ ISSUES DETECTED:")
        if not all_health_passed:
            print("  - Some health endpoints are failing")
        if not component_test:
            print("  - Monitoring components have issues")
        if not performance_test:
            print("  - Performance monitoring not working")
        if not alerting_test:
            print("  - Intelligent alerting has problems")
        print()
        print("🔧 RECOMMENDED ACTIONS:")
        print("  1. Check application logs: journalctl -u to-the-moon -f")
        print("  2. Verify all dependencies are installed")
        print("  3. Check database connectivity")
        print("  4. Restart the service: systemctl restart to-the-moon")
    else:
        print("🎉 ALL SYSTEMS OPERATIONAL!")
        print("  - All health endpoints responding")
        print("  - Monitoring systems active")
        print("  - Performance tracking enabled")
        print("  - Intelligent alerting configured")
    
    print("="*60)
    
    return overall_status

def main():
    """Run complete smoke test suite."""
    print("🚀 Starting To The Moon Monitoring Smoke Test")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Wait for application to be ready
    print("⏳ Waiting for application to be ready...")
    time.sleep(3)
    
    # Run tests
    health_results = test_health_endpoints()
    component_test = test_monitoring_components()
    performance_test = test_performance_simulation()
    alerting_test = test_intelligent_alerting()
    
    # Generate report
    success = generate_report(health_results, component_test, performance_test, alerting_test)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

