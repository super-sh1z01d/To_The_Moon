#!/usr/bin/env python3
"""
Test script for scheduler optimization performance.
Compares original vs optimized scheduler performance.
"""

import asyncio
import time
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.adapters.db.deps import get_db
from src.adapters.repositories.tokens_repo import TokensRepository as TokenRepository
from src.domain.scoring.scoring_service import ScoringService
from src.scheduler.service import _process_group as original_process_group
from src.scheduler.service_optimized import process_group_optimized
from src.core.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


async def benchmark_scheduler_performance():
    """Benchmark original vs optimized scheduler performance."""
    
    log.info("Starting scheduler optimization benchmark")
    
    # Get database session
    db = next(get_db())
    repo = TokenRepository(db)
    scoring_service = ScoringService()
    
    # Test parameters
    test_groups = ["hot", "cold"]
    test_runs = 3
    
    results = {
        "original": {},
        "optimized": {}
    }
    
    for group in test_groups:
        log.info(f"Testing {group} group processing")
        
        # Test original scheduler
        original_times = []
        original_processed = []
        original_updated = []
        
        for run in range(test_runs):
            log.info(f"Original scheduler - {group} group - Run {run + 1}/{test_runs}")
            
            start_time = time.time()
            try:
                processed, updated = await original_process_group(
                    repo, scoring_service, group
                )
                end_time = time.time()
                
                processing_time = end_time - start_time
                original_times.append(processing_time)
                original_processed.append(processed)
                original_updated.append(updated)
                
                log.info(f"Original - Processed: {processed}, Updated: {updated}, Time: {processing_time:.2f}s")
                
            except Exception as e:
                log.error(f"Original scheduler failed: {e}")
                continue
            
            # Wait between runs
            await asyncio.sleep(2)
        
        # Test optimized scheduler
        optimized_times = []
        optimized_processed = []
        optimized_updated = []
        
        for run in range(test_runs):
            log.info(f"Optimized scheduler - {group} group - Run {run + 1}/{test_runs}")
            
            start_time = time.time()
            try:
                processed, updated = await process_group_optimized(
                    repo, scoring_service, group
                )
                end_time = time.time()
                
                processing_time = end_time - start_time
                optimized_times.append(processing_time)
                optimized_processed.append(processed)
                optimized_updated.append(updated)
                
                log.info(f"Optimized - Processed: {processed}, Updated: {updated}, Time: {processing_time:.2f}s")
                
            except Exception as e:
                log.error(f"Optimized scheduler failed: {e}")
                continue
            
            # Wait between runs
            await asyncio.sleep(2)
        
        # Calculate averages
        if original_times and optimized_times:
            avg_original_time = sum(original_times) / len(original_times)
            avg_optimized_time = sum(optimized_times) / len(optimized_times)
            avg_original_processed = sum(original_processed) / len(original_processed)
            avg_optimized_processed = sum(optimized_processed) / len(optimized_processed)
            
            speedup = avg_original_time / avg_optimized_time if avg_optimized_time > 0 else 0
            
            results["original"][group] = {
                "avg_time": avg_original_time,
                "avg_processed": avg_original_processed,
                "tokens_per_second": avg_original_processed / avg_original_time if avg_original_time > 0 else 0
            }
            
            results["optimized"][group] = {
                "avg_time": avg_optimized_time,
                "avg_processed": avg_optimized_processed,
                "tokens_per_second": avg_optimized_processed / avg_optimized_time if avg_optimized_time > 0 else 0,
                "speedup": speedup
            }
    
    # Print results
    print("\n" + "="*80)
    print("SCHEDULER OPTIMIZATION BENCHMARK RESULTS")
    print("="*80)
    
    for group in test_groups:
        if group in results["original"] and group in results["optimized"]:
            orig = results["original"][group]
            opt = results["optimized"][group]
            
            print(f"\n{group.upper()} GROUP:")
            print(f"  Original Scheduler:")
            print(f"    Average Time: {orig['avg_time']:.2f}s")
            print(f"    Average Processed: {orig['avg_processed']:.1f} tokens")
            print(f"    Tokens/Second: {orig['tokens_per_second']:.2f}")
            
            print(f"  Optimized Scheduler:")
            print(f"    Average Time: {opt['avg_time']:.2f}s")
            print(f"    Average Processed: {opt['avg_processed']:.1f} tokens")
            print(f"    Tokens/Second: {opt['tokens_per_second']:.2f}")
            print(f"    Speedup: {opt['speedup']:.2f}x")
            
            if opt['speedup'] > 1.0:
                improvement = (opt['speedup'] - 1.0) * 100
                print(f"    Performance Improvement: +{improvement:.1f}%")
            else:
                degradation = (1.0 - opt['speedup']) * 100
                print(f"    Performance Change: -{degradation:.1f}%")
    
    print("\n" + "="*80)
    
    # Overall summary
    total_original_time = sum(results["original"][g]["avg_time"] for g in test_groups if g in results["original"])
    total_optimized_time = sum(results["optimized"][g]["avg_time"] for g in test_groups if g in results["optimized"])
    
    if total_original_time > 0 and total_optimized_time > 0:
        overall_speedup = total_original_time / total_optimized_time
        print(f"OVERALL SPEEDUP: {overall_speedup:.2f}x")
        
        if overall_speedup > 1.0:
            improvement = (overall_speedup - 1.0) * 100
            print(f"OVERALL IMPROVEMENT: +{improvement:.1f}%")
        
        # Recommendations
        print(f"\nRECOMMENDATIONS:")
        if overall_speedup > 1.5:
            print("✅ Optimized scheduler shows significant improvement - RECOMMENDED for production")
        elif overall_speedup > 1.1:
            print("✅ Optimized scheduler shows moderate improvement - RECOMMENDED for production")
        elif overall_speedup > 0.9:
            print("⚠️  Optimized scheduler shows similar performance - Consider testing under higher load")
        else:
            print("❌ Optimized scheduler shows degradation - Investigate configuration")
    
    db.close()
    return results


async def test_system_resources():
    """Test system resource utilization during processing."""
    import psutil
    
    log.info("Testing system resource utilization")
    
    # Get initial system stats
    initial_cpu = psutil.cpu_percent(interval=1)
    initial_memory = psutil.virtual_memory().percent
    
    print(f"\nSYSTEM RESOURCES:")
    print(f"CPU Cores: {psutil.cpu_count()}")
    print(f"Total Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    print(f"Initial CPU Usage: {initial_cpu:.1f}%")
    print(f"Initial Memory Usage: {initial_memory:.1f}%")
    
    # Test under load
    db = next(get_db())
    repo = TokenRepository(db)
    scoring_service = ScoringService()
    
    log.info("Running optimized scheduler under load monitoring")
    
    # Monitor resources during processing
    start_time = time.time()
    cpu_samples = []
    memory_samples = []
    
    async def monitor_resources():
        while time.time() - start_time < 30:  # Monitor for 30 seconds
            cpu_samples.append(psutil.cpu_percent())
            memory_samples.append(psutil.virtual_memory().percent)
            await asyncio.sleep(1)
    
    async def run_processing():
        for _ in range(3):  # Run multiple cycles
            await process_group_optimized(repo, scoring_service, "hot")
            await process_group_optimized(repo, scoring_service, "cold")
            await asyncio.sleep(2)
    
    # Run both tasks concurrently
    await asyncio.gather(
        monitor_resources(),
        run_processing()
    )
    
    # Calculate resource usage stats
    if cpu_samples and memory_samples:
        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        max_cpu = max(cpu_samples)
        avg_memory = sum(memory_samples) / len(memory_samples)
        max_memory = max(memory_samples)
        
        print(f"\nRESOURCE UTILIZATION DURING PROCESSING:")
        print(f"Average CPU Usage: {avg_cpu:.1f}%")
        print(f"Peak CPU Usage: {max_cpu:.1f}%")
        print(f"Average Memory Usage: {avg_memory:.1f}%")
        print(f"Peak Memory Usage: {max_memory:.1f}%")
        
        # Resource efficiency assessment
        if max_cpu < 70 and max_memory < 80:
            print("✅ System resources well utilized - room for more aggressive optimization")
        elif max_cpu < 85 and max_memory < 90:
            print("✅ System resources efficiently utilized")
        else:
            print("⚠️  System resources highly utilized - consider reducing concurrency")
    
    db.close()


async def main():
    """Main test function."""
    print("Scheduler Optimization Test Suite")
    print("=" * 50)
    
    try:
        # Test system resources first
        await test_system_resources()
        
        # Run performance benchmark
        await benchmark_scheduler_performance()
        
    except Exception as e:
        log.error(f"Test failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)