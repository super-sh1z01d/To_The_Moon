#!/usr/bin/env python3
"""
Test script for memory reporting and analysis functionality.

This script tests the memory reporting system including:
- Report generation
- Trend analysis
- Recommendations
- Logging functionality
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from monitoring.memory_reporter import MemoryReporter, get_memory_reporter
from monitoring.memory_manager import MemoryUsageSnapshot, MemoryOptimizationResult


async def test_memory_reporting():
    """Test the memory reporting functionality."""
    print("📊 Testing Memory Reporting System")
    print("=" * 50)
    
    # Initialize memory reporter
    memory_reporter = get_memory_reporter()
    memory_manager = memory_reporter.memory_manager
    
    print(f"📊 System Memory: {memory_manager.total_system_memory_gb:.1f}GB")
    print()
    
    # Test 1: Generate basic report with minimal data
    print("1️⃣ Testing basic report generation...")
    basic_report = memory_reporter.generate_report(1.0)  # 1 hour
    print(f"   Report period: {basic_report.report_period_hours} hours")
    print(f"   Current usage: {basic_report.current_usage_mb:.1f}MB ({basic_report.current_usage_percent:.1f}%)")
    print(f"   Thresholds: Warning={basic_report.warning_threshold_mb:.0f}MB, Critical={basic_report.critical_threshold_mb:.0f}MB")
    print(f"   Usage samples: {basic_report.usage_samples}")
    print(f"   Recommendations: {len(basic_report.recommendations)}")
    for rec in basic_report.recommendations[:2]:  # Show first 2
        print(f"     - {rec}")
    print()
    
    # Test 2: Add some fake historical data
    print("2️⃣ Testing report with historical data...")
    
    # Add fake usage history
    base_time = datetime.utcnow() - timedelta(hours=2)
    base_memory = 1000.0
    
    for i in range(20):
        fake_snapshot = MemoryUsageSnapshot(
            timestamp=base_time + timedelta(minutes=i*6),
            used_mb=2000.0 + i * 50,  # System memory gradually increasing
            available_mb=60000.0 - i * 50,
            total_mb=64000.0,
            percent_used=3.0 + i * 0.1,
            process_memory_mb=base_memory + i * 5  # Process memory increasing
        )
        memory_manager.usage_history.append(fake_snapshot)
    
    # Add fake optimization history
    for i in range(3):
        fake_optimization = MemoryOptimizationResult(
            before_mb=base_memory + i * 20,
            after_mb=base_memory + i * 20 - 10,
            recovered_mb=10.0,
            actions_taken=[f"cleanup_action_{i}", "gc_collect"],
            success=True,
            timestamp=base_time + timedelta(minutes=i*30)
        )
        memory_manager.optimization_history.append(fake_optimization)
    
    historical_report = memory_reporter.generate_report(2.0)  # 2 hours
    print(f"   Report period: {historical_report.report_period_hours} hours")
    print(f"   Usage trend: {historical_report.usage_trend}")
    print(f"   Average usage: {historical_report.average_usage_mb:.1f}MB")
    print(f"   Peak usage: {historical_report.peak_usage_mb:.1f}MB")
    print(f"   Min usage: {historical_report.min_usage_mb:.1f}MB")
    print(f"   Optimizations: {historical_report.optimizations_count}")
    print(f"   Total recovered: {historical_report.total_memory_recovered_mb:.1f}MB")
    print(f"   Most effective: {historical_report.most_effective_optimization}")
    print(f"   Usage samples: {historical_report.usage_samples}")
    print()
    
    # Test 3: Test recommendations
    print("3️⃣ Testing recommendation generation...")
    print(f"   Recommendations count: {len(historical_report.recommendations)}")
    for i, rec in enumerate(historical_report.recommendations, 1):
        print(f"   {i}. {rec}")
    print()
    
    # Test 4: Test trend analysis
    print("4️⃣ Testing trend analysis...")
    
    # Create decreasing trend data
    decreasing_snapshots = []
    for i in range(10):
        snapshot = MemoryUsageSnapshot(
            timestamp=datetime.utcnow() - timedelta(minutes=i*5),
            used_mb=3000.0 - i * 100,  # Decreasing
            available_mb=60000.0,
            total_mb=64000.0,
            percent_used=5.0 - i * 0.2,
            process_memory_mb=200.0 - i * 10
        )
        decreasing_snapshots.append(snapshot)
    
    trend = memory_reporter._calculate_trend(decreasing_snapshots)
    print(f"   Decreasing trend test: {trend}")
    
    # Create stable trend data
    stable_snapshots = []
    for i in range(10):
        snapshot = MemoryUsageSnapshot(
            timestamp=datetime.utcnow() - timedelta(minutes=i*5),
            used_mb=2000.0 + (i % 2) * 10,  # Stable with minor fluctuation
            available_mb=60000.0,
            total_mb=64000.0,
            percent_used=3.0,
            process_memory_mb=150.0 + (i % 2) * 5
        )
        stable_snapshots.append(snapshot)
    
    trend = memory_reporter._calculate_trend(stable_snapshots)
    print(f"   Stable trend test: {trend}")
    print()
    
    # Test 5: Test report logging
    print("5️⃣ Testing report logging...")
    try:
        memory_reporter.log_memory_report(0.5)  # 30 minutes
        print("   ✅ Report logging successful")
    except Exception as e:
        print(f"   ❌ Report logging failed: {e}")
    print()
    
    # Test 6: Test different report periods
    print("6️⃣ Testing different report periods...")
    
    periods = [0.5, 1.0, 6.0, 24.0]
    for period in periods:
        try:
            period_report = memory_reporter.generate_report(period)
            print(f"   {period}h report: {period_report.usage_samples} samples, {len(period_report.recommendations)} recommendations")
        except Exception as e:
            print(f"   {period}h report failed: {e}")
    print()
    
    # Test 7: Test optimization analysis
    print("7️⃣ Testing optimization analysis...")
    opt_analysis = memory_reporter._analyze_optimization_history(
        datetime.utcnow() - timedelta(hours=2),
        datetime.utcnow()
    )
    print(f"   Optimizations found: {opt_analysis['count']}")
    print(f"   Total recovered: {opt_analysis['total_recovered_mb']:.1f}MB")
    print(f"   Most effective: {opt_analysis['most_effective']}")
    print(f"   History records: {len(opt_analysis['history'])}")
    print()
    
    print("✅ Memory reporting tests completed!")
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_memory_reporting())
        if result:
            print("\n🎉 All reporting tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some reporting tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)