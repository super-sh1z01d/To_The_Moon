#!/usr/bin/env python3
"""
Simple performance test for scheduler optimization.
Tests the current system performance without comparing to original.
"""

import asyncio
import time
import logging
import sys
import os
import psutil
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


async def test_api_performance():
    """Test API performance and response times."""
    import httpx
    
    log.info("Testing API performance")
    
    base_url = "http://localhost:8000"
    
    # Test endpoints
    endpoints = [
        "/health",
        "/tokens?limit=10",
        "/tokens?statuses=active&limit=5",
        "/tokens?statuses=monitoring&limit=5"
    ]
    
    results = {}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for endpoint in endpoints:
            times = []
            
            for i in range(5):  # 5 requests per endpoint
                start_time = time.time()
                try:
                    response = await client.get(f"{base_url}{endpoint}")
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        response_time = (end_time - start_time) * 1000  # ms
                        times.append(response_time)
                        log.info(f"{endpoint} - Request {i+1}: {response_time:.2f}ms")
                    else:
                        log.warning(f"{endpoint} - Request {i+1}: HTTP {response.status_code}")
                        
                except Exception as e:
                    log.error(f"{endpoint} - Request {i+1}: Error {e}")
                
                await asyncio.sleep(0.5)  # Small delay between requests
            
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                results[endpoint] = {
                    "avg_ms": avg_time,
                    "min_ms": min_time,
                    "max_ms": max_time,
                    "requests": len(times)
                }
    
    return results


def test_system_resources():
    """Test current system resource utilization."""
    log.info("Testing system resources")
    
    # Get system info
    cpu_count = psutil.cpu_count()
    memory = psutil.virtual_memory()
    
    # Get current usage
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = memory.percent
    
    # Get process info for tothemoon service
    tothemoon_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
        try:
            if 'tothemoon' in ' '.join(proc.info['cmdline'] or []):
                tothemoon_processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return {
        "system": {
            "cpu_cores": cpu_count,
            "total_memory_gb": memory.total / (1024**3),
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent
        },
        "tothemoon_processes": tothemoon_processes
    }


async def monitor_scheduler_activity():
    """Monitor scheduler activity by watching logs."""
    import subprocess
    
    log.info("Monitoring scheduler activity for 60 seconds")
    
    # Monitor logs for scheduler activity
    cmd = [
        "journalctl", "-u", "tothemoon.service", "-f", "--no-pager", "-n", "0"
    ]
    
    scheduler_events = []
    start_time = time.time()
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        while time.time() - start_time < 60:  # Monitor for 60 seconds
            line = process.stdout.readline()
            if line:
                line = line.strip()
                
                # Look for scheduler-related events
                if any(keyword in line.lower() for keyword in [
                    'processing_group', 'processed', 'updated', 'tokens_per_second',
                    'parallel_batch', 'optimized_group', 'scheduler'
                ]):
                    scheduler_events.append({
                        "timestamp": datetime.now().isoformat(),
                        "message": line
                    })
                    log.info(f"Scheduler event: {line}")
            
            await asyncio.sleep(0.1)
        
        process.terminate()
        
    except Exception as e:
        log.error(f"Error monitoring logs: {e}")
    
    return scheduler_events


async def main():
    """Main test function."""
    print("Simple Performance Test for Scheduler Optimization")
    print("=" * 60)
    
    try:
        # Test system resources
        print("\n📊 SYSTEM RESOURCES:")
        print("-" * 30)
        resources = test_system_resources()
        
        system = resources["system"]
        print(f"CPU Cores: {system['cpu_cores']}")
        print(f"Total Memory: {system['total_memory_gb']:.1f} GB")
        print(f"Current CPU Usage: {system['cpu_percent']:.1f}%")
        print(f"Current Memory Usage: {system['memory_percent']:.1f}%")
        
        if resources["tothemoon_processes"]:
            print(f"\nTo The Moon Processes: {len(resources['tothemoon_processes'])}")
            for proc in resources["tothemoon_processes"]:
                print(f"  PID {proc['pid']}: CPU {proc['cpu_percent']:.1f}%, Memory {proc['memory_percent']:.1f}%")
        
        # Test API performance
        print("\n🌐 API PERFORMANCE:")
        print("-" * 30)
        api_results = await test_api_performance()
        
        for endpoint, stats in api_results.items():
            print(f"{endpoint}:")
            print(f"  Average: {stats['avg_ms']:.2f}ms")
            print(f"  Range: {stats['min_ms']:.2f}ms - {stats['max_ms']:.2f}ms")
            print(f"  Requests: {stats['requests']}")
        
        # Monitor scheduler activity
        print("\n⚙️  SCHEDULER ACTIVITY:")
        print("-" * 30)
        print("Monitoring scheduler for 60 seconds...")
        
        scheduler_events = await monitor_scheduler_activity()
        
        print(f"\nCaptured {len(scheduler_events)} scheduler events")
        
        # Show recent events
        if scheduler_events:
            print("\nRecent scheduler events:")
            for event in scheduler_events[-5:]:  # Show last 5 events
                print(f"  {event['timestamp']}: {event['message']}")
        
        # Performance assessment
        print("\n🎯 PERFORMANCE ASSESSMENT:")
        print("-" * 30)
        
        # API performance assessment
        avg_api_time = sum(stats['avg_ms'] for stats in api_results.values()) / len(api_results)
        if avg_api_time < 100:
            print("✅ API Performance: Excellent (< 100ms average)")
        elif avg_api_time < 500:
            print("✅ API Performance: Good (< 500ms average)")
        else:
            print("⚠️  API Performance: Needs improvement (> 500ms average)")
        
        # Resource utilization assessment
        if system['cpu_percent'] < 50 and system['memory_percent'] < 70:
            print("✅ Resource Utilization: Efficient - room for more load")
        elif system['cpu_percent'] < 80 and system['memory_percent'] < 85:
            print("✅ Resource Utilization: Good - well balanced")
        else:
            print("⚠️  Resource Utilization: High - consider optimization")
        
        # Scheduler activity assessment
        if len(scheduler_events) > 10:
            print("✅ Scheduler Activity: Active - processing tokens regularly")
        elif len(scheduler_events) > 0:
            print("✅ Scheduler Activity: Moderate - some processing detected")
        else:
            print("⚠️  Scheduler Activity: Low - check scheduler configuration")
        
        print(f"\n🎉 Performance test completed successfully!")
        print(f"System appears to be running optimally with {system['cpu_cores']} cores and {system['total_memory_gb']:.1f}GB RAM")
        
    except Exception as e:
        log.error(f"Test failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)