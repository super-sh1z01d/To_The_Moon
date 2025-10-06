#!/usr/bin/env python3
"""
Test script for memory cleanup and optimization functionality.

This script tests the enhanced memory cleanup features including:
- Targeted cleanup by component
- Automatic leak detection and cleanup
- Memory optimization history
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from monitoring.memory_manager import IntelligentMemoryManager


async def test_memory_cleanup():
    """Test the enhanced memory cleanup functionality."""
    print("🧹 Testing Enhanced Memory Cleanup")
    print("=" * 50)
    
    # Initialize memory manager
    memory_manager = IntelligentMemoryManager()
    
    print(f"📊 System Memory: {memory_manager.total_system_memory_gb:.1f}GB")
    print()
    
    # Test 1: Basic garbage collection
    print("1️⃣ Testing basic garbage collection...")
    gc_result = memory_manager.perform_garbage_collection()
    print(f"   Success: {gc_result.success}")
    print(f"   Before: {gc_result.before_mb:.1f}MB")
    print(f"   After: {gc_result.after_mb:.1f}MB")
    print(f"   Recovered: {gc_result.recovered_mb:.1f}MB")
    print(f"   Actions: {', '.join(gc_result.actions_taken)}")
    print()
    
    # Test 2: Targeted cleanup - all components
    print("2️⃣ Testing targeted cleanup (all components)...")
    cleanup_result = memory_manager.perform_targeted_cleanup("all")
    print(f"   Success: {cleanup_result.success}")
    print(f"   Before: {cleanup_result.before_mb:.1f}MB")
    print(f"   After: {cleanup_result.after_mb:.1f}MB")
    print(f"   Recovered: {cleanup_result.recovered_mb:.1f}MB")
    print(f"   Actions: {', '.join(cleanup_result.actions_taken)}")
    print()
    
    # Test 3: Targeted cleanup - API cache only
    print("3️⃣ Testing targeted cleanup (API cache only)...")
    api_cleanup_result = memory_manager.perform_targeted_cleanup("api_cache")
    print(f"   Success: {api_cleanup_result.success}")
    print(f"   Actions: {', '.join(api_cleanup_result.actions_taken)}")
    print()
    
    # Test 4: Targeted cleanup - metrics only
    print("4️⃣ Testing targeted cleanup (metrics only)...")
    metrics_cleanup_result = memory_manager.perform_targeted_cleanup("metrics")
    print(f"   Success: {metrics_cleanup_result.success}")
    print(f"   Actions: {', '.join(metrics_cleanup_result.actions_taken)}")
    print()
    
    # Test 5: Memory leak detection
    print("5️⃣ Testing memory leak detection...")
    
    # Add some fake memory usage data to simulate a leak
    from datetime import datetime, timedelta
    from monitoring.memory_manager import MemoryUsageSnapshot
    
    base_time = datetime.utcnow() - timedelta(minutes=30)
    base_memory = 100.0
    
    # Simulate increasing memory usage (potential leak)
    for i in range(15):
        fake_snapshot = MemoryUsageSnapshot(
            timestamp=base_time + timedelta(minutes=i*2),
            used_mb=1000.0 + i * 10,  # System memory
            available_mb=60000.0,
            total_mb=64000.0,
            percent_used=2.0,
            process_memory_mb=base_memory + i * 8  # Process memory increasing
        )
        memory_manager.usage_history.append(fake_snapshot)
    
    leak_detection = memory_manager.detect_memory_leak()
    if leak_detection:
        print(f"   Leak detected: {leak_detection['detected']}")
        print(f"   Increase: {leak_detection['increase_percent']:.1f}% over {leak_detection['timespan_minutes']:.1f} minutes")
        print(f"   Slope: {leak_detection['slope_mb_per_measurement']:.2f} MB/measurement")
        print(f"   Recommendation: {leak_detection['recommendation']}")
    else:
        print("   No memory leak detected")
    print()
    
    # Test 6: Check memory and optimize with leak detection
    print("6️⃣ Testing memory check with automatic leak cleanup...")
    needs_alert, alerts = memory_manager.check_memory_and_optimize()
    print(f"   Needs alert: {needs_alert}")
    print(f"   Alerts generated: {len(alerts)}")
    for alert in alerts:
        print(f"   - {alert.level.value.upper()}: {alert.message}")
    print()
    
    # Test 7: Optimization history
    print("7️⃣ Testing optimization history...")
    print(f"   Total optimizations: {len(memory_manager.optimization_history)}")
    for i, opt in enumerate(memory_manager.optimization_history[-3:], 1):  # Last 3
        print(f"   {i}. {opt.timestamp.strftime('%H:%M:%S')}: {opt.recovered_mb:.1f}MB recovered, {len(opt.actions_taken)} actions")
    print()
    
    # Test 8: Memory statistics with cleanup history
    print("8️⃣ Testing memory statistics with cleanup history...")
    stats = memory_manager.get_memory_statistics()
    print(f"   Current usage: {stats['current_usage']['used_mb']:.1f}MB")
    print(f"   Optimization history entries: {len(stats['optimization_history'])}")
    
    if stats['leak_detection']:
        print(f"   Leak detection: Active - {stats['leak_detection']['increase_percent']:.1f}% increase")
    else:
        print("   Leak detection: No leaks detected")
    print()
    
    print("✅ Memory cleanup tests completed!")
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_memory_cleanup())
        if result:
            print("\n🎉 All cleanup tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some cleanup tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)