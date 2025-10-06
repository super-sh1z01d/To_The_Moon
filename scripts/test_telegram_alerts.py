#!/usr/bin/env python3
"""
Test script for enhanced Telegram notification system.

This script tests the specialized Telegram notifications including:
- Memory alerts with rich formatting
- Performance alerts with metrics
- Token processing alerts
- System health summaries
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from monitoring.telegram_notifier import TelegramNotifier, get_telegram_notifier


async def test_telegram_notifications():
    """Test the enhanced Telegram notification system."""
    print("📱 Testing Enhanced Telegram Notifications")
    print("=" * 50)
    
    # Initialize Telegram notifier
    telegram_notifier = get_telegram_notifier()
    
    print(f"🔧 Telegram configured: {telegram_notifier.is_configured()}")
    
    if not telegram_notifier.is_configured():
        print("❌ Telegram not configured - set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        return False
    
    print()
    
    # Test 1: Memory alerts
    print("1️⃣ Testing memory alerts...")
    
    # Critical memory alert
    success = telegram_notifier.send_memory_alert(
        alert_type="critical",
        current_usage_mb=1800.0,
        threshold_mb=1600.0,
        total_memory_gb=62.7,
        recovered_mb=15.5,
        actions_taken=["gc_collect", "cache_clear", "malloc_trim"]
    )
    print(f"   Critical memory alert: {'✅' if success else '❌'}")
    
    # Memory optimization alert
    success = telegram_notifier.send_memory_alert(
        alert_type="optimized",
        current_usage_mb=1200.0,
        threshold_mb=1600.0,
        total_memory_gb=62.7,
        recovered_mb=45.2,
        actions_taken=["comprehensive_cleanup", "gc_collect", "history_trim"]
    )
    print(f"   Memory optimization alert: {'✅' if success else '❌'}")
    
    # Memory leak detection alert
    success = telegram_notifier.send_memory_alert(
        alert_type="leak_detected",
        current_usage_mb=1450.0,
        threshold_mb=1600.0,
        total_memory_gb=62.7,
        recovered_mb=8.3,
        actions_taken=["leak_cleanup", "targeted_gc"]
    )
    print(f"   Memory leak alert: {'✅' if success else '❌'}")
    print()
    
    # Test 2: Performance alerts
    print("2️⃣ Testing performance alerts...")
    
    # Performance degradation
    success = telegram_notifier.send_performance_alert(
        alert_type="degradation",
        component="dexscreener_api",
        metrics={
            "response_time": 3.2,
            "throughput": 25.5,
            "error_rate": 15.8,
            "cpu_usage": 85.2
        },
        recommendations=[
            "Increase API timeout settings",
            "Implement request caching",
            "Scale processing workers"
        ]
    )
    print(f"   Performance degradation alert: {'✅' if success else '❌'}")
    
    # Performance bottleneck
    success = telegram_notifier.send_performance_alert(
        alert_type="bottleneck",
        component="token_processing",
        metrics={
            "response_time": 5.8,
            "throughput": 8.2,
            "error_rate": 25.3
        },
        recommendations=[
            "Investigate database queries",
            "Optimize token validation logic"
        ]
    )
    print(f"   Performance bottleneck alert: {'✅' if success else '❌'}")
    print()
    
    # Test 3: Token processing alerts
    print("3️⃣ Testing token processing alerts...")
    
    # Stuck tokens alert
    success = telegram_notifier.send_token_processing_alert(
        alert_type="stuck_tokens",
        tokens_stuck=23,
        processing_rate=1.8,
        backlog_size=67,
        avg_activation_time=145.5
    )
    print(f"   Stuck tokens alert: {'✅' if success else '❌'}")
    
    # Slow processing alert
    success = telegram_notifier.send_token_processing_alert(
        alert_type="slow_processing",
        tokens_stuck=5,
        processing_rate=0.8,
        backlog_size=125,
        avg_activation_time=280.2
    )
    print(f"   Slow processing alert: {'✅' if success else '❌'}")
    
    # Growing backlog alert
    success = telegram_notifier.send_token_processing_alert(
        alert_type="backlog_growing",
        tokens_stuck=12,
        processing_rate=2.1,
        backlog_size=200,
        avg_activation_time=95.3
    )
    print(f"   Growing backlog alert: {'✅' if success else '❌'}")
    print()
    
    # Test 4: System health summary
    print("4️⃣ Testing system health summary...")
    
    # Healthy system summary
    success = telegram_notifier.send_system_health_summary(
        memory_status="healthy",
        cpu_usage=25.3,
        api_status="healthy",
        tokens_processed_last_hour=145,
        active_alerts=1
    )
    print(f"   Healthy system summary: {'✅' if success else '❌'}")
    
    # Critical system summary
    success = telegram_notifier.send_system_health_summary(
        memory_status="critical",
        cpu_usage=88.7,
        api_status="degraded",
        tokens_processed_last_hour=23,
        active_alerts=8
    )
    print(f"   Critical system summary: {'✅' if success else '❌'}")
    print()
    
    # Test 5: Configuration check
    print("5️⃣ Testing configuration...")
    print(f"   Bot token configured: {'✅' if telegram_notifier.bot_token else '❌'}")
    print(f"   Chat ID configured: {'✅' if telegram_notifier.chat_id else '❌'}")
    print(f"   Alert manager available: {'✅' if telegram_notifier.alert_manager else '❌'}")
    print()
    
    print("✅ Telegram notification tests completed!")
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_telegram_notifications())
        if result:
            print("\n🎉 All Telegram tests passed!")
            print("\n📱 Check your Telegram chat for the test messages!")
            sys.exit(0)
        else:
            print("\n❌ Some Telegram tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)