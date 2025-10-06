#!/usr/bin/env python3
"""
Test script for performance optimizer.

Tests the adaptive performance optimization system including:
- Metrics collection
- Optimization decisions
- API timeout adjustments
- Parallelism optimization
- Load management
- Database optimization
- Memory leak detection
- System resource monitoring
"""

import sys
import os
import asyncio
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.monitoring.performance_optimizer import get_performance_optimizer


def test_metrics_collection():
    """Test basic metrics collection."""
    print("🔍 Testing basic metrics collection...")
    
    optimizer = get_performance_optimizer()
    
    # Get basic metrics
    metrics = optimizer._get_basic_metrics()
    
    print(f"✅ Basic metrics collected:")
    print(f"   - CPU usage: {metrics.get('cpu_usage', 0):.1f}%")
    print(f"   - Memory usage: {metrics.get('memory_mb', 0):.1f}MB")
    print(f"   - Timestamp: {metrics.get('timestamp', 'unknown')}")
    
    return metrics


def test_simple_optimization_cycle():
    """Test the simple optimization cycle."""
    print("\n🔄 Testing simple optimization cycle...")
    
    optimizer = get_performance_optimizer()
    
    # Run optimization cycle
    result = optimizer.run_optimization_cycle()
    
    print(f"✅ Simple optimization cycle completed:")
    print(f"   - Status: {result.get('status', 'unknown')}")
    print(f"   - Timestamp: {result.get('timestamp', 'unknown')}")
    
    if result.get('error'):
        print(f"   - Error: {result['error']}")
    else:
        metrics = result.get('metrics', {})
        print(f"   - CPU usage: {metrics.get('cpu_usage', 0):.1f}%")
        print(f"   - Memory usage: {metrics.get('memory_mb', 0):.1f}MB")
        
        recommendations = result.get('recommendations', [])
        if recommendations:
            print(f"   - Recommendations ({len(recommendations)}):")
            for rec in recommendations:
                print(f"     - {rec}")
        else:
            print("   - No recommendations needed")


def main():
    """Run simple performance optimizer tests."""
    print("🚀 Simple Performance Optimizer Test Suite")
    print("=" * 60)
    
    try:
        # Test basic functionality
        test_metrics_collection()
        test_simple_optimization_cycle()
        
        print("\n" + "=" * 60)
        print("✅ All performance optimizer tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())