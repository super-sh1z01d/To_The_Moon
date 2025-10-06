#!/usr/bin/env python3
"""
Test script for intelligent memory manager.

This script tests the memory management functionality including:
- Dynamic threshold calculation
- Memory optimization
- Threshold updates
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from monitoring.memory_manager import IntelligentMemoryManager
from monitoring.config import get_monitoring_config_manager


async def test_memory_manager():
    """Test the intelligent memory manager functionality."""
    print("🧠 Testing Intelligent Memory Manager")
    print("=" * 50)
    
    # Initialize memory manager
    memory_manager = IntelligentMemoryManager()
    
    print(f"📊 System Memory: {memory_manager.total_system_memory_gb:.1f}GB")
    print()
    
    # Test 1: Get current memory snapshot
    print("1️⃣ Testing memory snapshot...")
    snapshot = memory_manager.get_current_memory_snapshot()
    print(f"   Used: {snapshot.used_mb:.1f}MB ({snapshot.percent_used:.1f}%)")
    print(f"   Available: {snapshot.available_mb:.1f}MB")
    print(f"   Process: {snapshot.process_memory_mb:.1f}MB")
    print()
    
    # Test 2: Calculate dynamic thresholds
    print("2️⃣ Testing dynamic threshold calculation...")
    warning_mb, critical_mb = memory_manager.calculate_dynamic_thresholds()
    print(f"   Warning threshold: {warning_mb:.0f}MB ({(warning_mb/snapshot.total_mb)*100:.1f}%)")
    print(f"   Critical threshold: {critical_mb:.0f}MB ({(critical_mb/snapshot.total_mb)*100:.1f}%)")
    
    # Compare with current config
    config_manager = get_monitoring_config_manager()
    config = config_manager.get_monitoring_config()
    print(f"   Current config warning: {config.memory_warning_threshold:.0f}MB")
    print(f"   Current config critical: {config.memory_critical_threshold:.0f}MB")
    print()
    
    # Test 3: Memory optimization
    print("3️⃣ Testing memory optimization...")
    optimization_result = memory_manager.perform_garbage_collection()
    print(f"   Success: {optimization_result.success}")
    print(f"   Before: {optimization_result.before_mb:.1f}MB")
    print(f"   After: {optimization_result.after_mb:.1f}MB")
    print(f"   Recovered: {optimization_result.recovered_mb:.1f}MB")
    print(f"   Actions: {', '.join(optimization_result.actions_taken)}")
    print()
    
    # Test 4: Check memory and optimize
    print("4️⃣ Testing memory check and optimization...")
    needs_alert, alerts = memory_manager.check_memory_and_optimize()
    print(f"   Needs alert: {needs_alert}")
    print(f"   Alerts generated: {len(alerts)}")
    for alert in alerts:
        print(f"   - {alert.level.value.upper()}: {alert.message}")
    print()
    
    # Test 5: Memory statistics
    print("5️⃣ Testing memory statistics...")
    stats = memory_manager.get_memory_statistics()
    print(f"   Current usage: {stats['current_usage']['used_mb']:.1f}MB")
    print(f"   Warning threshold: {stats['thresholds']['warning_mb']:.0f}MB")
    print(f"   Critical threshold: {stats['thresholds']['critical_mb']:.0f}MB")
    print(f"   Optimization history: {len(stats['optimization_history'])} entries")
    
    if stats['leak_detection']:
        print(f"   Leak detection: {stats['leak_detection']}")
    else:
        print("   No memory leaks detected")
    print()
    
    # Test 6: Threshold update
    print("6️⃣ Testing threshold update...")
    # Force update by clearing last update time
    memory_manager._last_threshold_update = None
    updated = memory_manager.update_thresholds_if_needed()
    print(f"   Thresholds updated: {updated}")
    print()
    
    print("✅ Memory manager tests completed!")
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_memory_manager())
        if result:
            print("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)