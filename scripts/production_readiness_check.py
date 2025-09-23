#!/usr/bin/env python3
"""
Production readiness check for To The Moon.
Verifies all systems are ready for production deployment.
"""

import sys
import json
import time
import requests
from datetime import datetime

def check_environment():
    """Check environment configuration."""
    print("🌍 Checking environment configuration...")
    
    try:
        from src.core.config import get_config
        config = get_config()
        
        checks = {
            "app_env": config.app_env == "prod",
            "log_level": config.log_level in ["INFO", "WARNING", "ERROR"],
            "scheduler_enabled": getattr(config, "scheduler_enabled", True),
            "database_url": bool(getattr(config, "database_url", None))
        }
        
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {check}: {status}")
        
        return all(checks.values())
        
    except Exception as e:
        print(f"  ❌ Environment check failed: {e}")
        return False

def check_database():
    """Check database connectivity and migrations."""
    print("🗄️  Checking database...")
    
    try:
        from src.adapters.db.base import SessionLocal
        from sqlalchemy import text
        
        with SessionLocal() as session:
            # Test basic connectivity
            result = session.execute(text("SELECT 1")).scalar()
            print("  ✅ Database connectivity: OK")
            
            # Check if tables exist
            tables_result = session.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = public AND table_name IN (tokens, app_settings)
            """)).fetchall()
            
            if len(tables_result) >= 2:
                print("  ✅ Required tables exist: OK")
                return True
            else:
                print("  ❌ Required tables missing")
                return False
                
    except Exception as e:
        print(f"  ❌ Database check failed: {e}")
        return False

def check_monitoring_systems():
    """Check all monitoring systems are functional."""
    print("�� Checking monitoring systems...")
    
    try:
        # Import all monitoring components
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
        
        # Test each component
        components = {
            "health_monitor": get_health_monitor(),
            "performance_tracker": get_performance_tracker(),
            "degradation_detector": get_performance_degradation_detector(),
            "structured_logger": get_structured_logger(),
            "alert_manager": get_alert_manager(),
            "intelligent_alerting": get_intelligent_alerting_engine(),
            "priority_processor": get_priority_processor(),
            "config_reloader": get_config_hot_reloader()
        }
        
        for name, component in components.items():
            if component:
                print(f"  ✅ {name}: OK")
            else:
                print(f"  ❌ {name}: FAILED")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Monitoring systems check failed: {e}")
        return False

def check_resilient_client():
    """Check resilient client configuration."""
    print("🔄 Checking resilient client...")
    
    try:
        from src.adapters.services.resilient_dexscreener_client import ResilientDexScreenerClient
        from src.monitoring.circuit_breaker import CircuitBreaker
        from src.monitoring.retry_manager import RetryManager
        
        # Test circuit breaker
        circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception_types=[Exception]
        )
        print("  ✅ Circuit breaker: OK")
        
        # Test retry manager
        retry_manager = RetryManager(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0
        )
        print("  ✅ Retry manager: OK")
        
        # Test resilient client
        client = ResilientDexScreenerClient(timeout=5.0)
        print("  ✅ Resilient client: OK")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Resilient client check failed: {e}")
        return False

def check_configuration_files():
    """Check required configuration files exist."""
    print("📋 Checking configuration files...")
    
    import os
    
    required_files = [
        ".env",
        "config/monitoring.json",
        "config/production.json"
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}: EXISTS")
        else:
            print(f"  ❌ {file_path}: MISSING")
            all_exist = False
    
    return all_exist

def check_external_dependencies():
    """Check external API dependencies."""
    print("🌐 Checking external dependencies...")
    
    # Test DexScreener API (with timeout)
    try:
        response = requests.get(
            "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112",
            timeout=10
        )
        if response.status_code == 200:
            print("  ✅ DexScreener API: OK")
            return True
        else:
            print(f"  ⚠️  DexScreener API: HTTP {response.status_code}")
            return True  # Not critical for startup
    except Exception as e:
        print(f"  ⚠️  DexScreener API: {e} (will use fallback)")
        return True  # Not critical for startup

def run_production_readiness_check():
    """Run complete production readiness check."""
    print("🚀 PRODUCTION READINESS CHECK")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    checks = {
        "Environment": check_environment(),
        "Database": check_database(),
        "Monitoring Systems": check_monitoring_systems(),
        "Resilient Client": check_resilient_client(),
        "Configuration Files": check_configuration_files(),
        "External Dependencies": check_external_dependencies()
    }
    
    print()
    print("=" * 50)
    print("📋 READINESS SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check_name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 PRODUCTION READY!")
        print("All systems are operational and ready for deployment.")
        print()
        print("Next steps:")
        print("1. Run: ./scripts/deploy_monitoring.sh")
        print("2. Monitor: ./scripts/smoke_test_monitoring.py")
        print("3. Check logs: journalctl -u to-the-moon -f")
    else:
        print("❌ NOT READY FOR PRODUCTION")
        print("Please fix the failing checks before deployment.")
        print()
        print("Common fixes:")
        print("- Check .env file configuration")
        print("- Run database migrations: alembic upgrade head")
        print("- Install missing dependencies: pip install -r requirements.txt")
        print("- Create missing config files")
    
    print("=" * 50)
    return all_passed

if __name__ == "__main__":
    success = run_production_readiness_check()
    sys.exit(0 if success else 1)

