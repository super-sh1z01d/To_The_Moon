#!/usr/bin/env python3
"""
Test script for spam detection functionality.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.monitoring.spam_detector import SpamDetector, test_spam_detection


async def test_specific_tokens():
    """Test spam detection on specific tokens."""
    
    test_tokens = [
        {
            "name": "Known Spammy Token",
            "mint": "J4UBm5kvMSHeUwbNgZW4ySpCHBvS7LXknZ7rqQR9pump",
            "expected": "high spam"
        },
        {
            "name": "WSOL (Should be clean)",
            "mint": "So11111111111111111111111111111111111111112",
            "expected": "clean"
        }
    ]
    
    print("🔍 TESTING SPAM DETECTOR")
    print("=" * 50)
    
    async with SpamDetector() as detector:
        for token_info in test_tokens:
            print(f"\n📊 Testing: {token_info['name']}")
            print(f"   Mint: {token_info['mint']}")
            print(f"   Expected: {token_info['expected']}")
            
            try:
                result = await detector.analyze_token_spam(token_info['mint'])
                
                if "error" in result:
                    print(f"   ❌ Error: {result['error']}")
                    continue
                
                metrics = result.get("spam_metrics", {})
                spam_pct = metrics.get("spam_percentage", 0)
                risk_level = metrics.get("risk_level", "unknown")
                total_instructions = metrics.get("total_instructions", 0)
                compute_budget_count = metrics.get("compute_budget_count", 0)
                
                print(f"   📈 Results:")
                print(f"      Spam Percentage: {spam_pct:.1f}%")
                print(f"      Risk Level: {risk_level}")
                print(f"      Total Instructions: {total_instructions}")
                print(f"      ComputeBudget Count: {compute_budget_count}")
                print(f"      Analysis Time: {result.get('analysis_time', 0):.2f}s")
                
                # Determine if result matches expectation
                if "high" in token_info['expected'] and risk_level in ["high", "medium"]:
                    print(f"   ✅ Result matches expectation!")
                elif "clean" in token_info['expected'] and risk_level in ["clean", "low"]:
                    print(f"   ✅ Result matches expectation!")
                else:
                    print(f"   ⚠️  Result differs from expectation")
                
            except Exception as e:
                print(f"   ❌ Test failed: {e}")


async def benchmark_performance():
    """Benchmark spam detection performance."""
    print(f"\n🚀 PERFORMANCE BENCHMARK")
    print("=" * 50)
    
    test_mint = "J4UBm5kvMSHeUwbNgZW4ySpCHBvS7LXknZ7rqQR9pump"
    
    async with SpamDetector() as detector:
        # Test multiple runs
        times = []
        
        for i in range(3):
            print(f"\n   Run {i+1}/3...")
            
            try:
                result = await detector.analyze_token_spam(test_mint)
                analysis_time = result.get("analysis_time", 0)
                times.append(analysis_time)
                
                metrics = result.get("spam_metrics", {})
                print(f"   Time: {analysis_time:.2f}s, Spam: {metrics.get('spam_percentage', 0):.1f}%")
                
            except Exception as e:
                print(f"   ❌ Run {i+1} failed: {e}")
        
        if times:
            avg_time = sum(times) / len(times)
            print(f"\n   📊 Average analysis time: {avg_time:.2f}s")
            print(f"   📊 Target: <2s per token (for 5s monitoring cycle)")
            
            if avg_time < 2.0:
                print(f"   ✅ Performance is acceptable!")
            else:
                print(f"   ⚠️  Performance may be too slow for real-time monitoring")


async def test_batch_analysis():
    """Test analyzing multiple tokens in batch."""
    print(f"\n📦 BATCH ANALYSIS TEST")
    print("=" * 50)
    
    # Test with multiple tokens
    test_tokens = [
        "J4UBm5kvMSHeUwbNgZW4ySpCHBvS7LXknZ7rqQR9pump",
        "So11111111111111111111111111111111111111112",
    ]
    
    async with SpamDetector() as detector:
        start_time = asyncio.get_event_loop().time()
        
        # Analyze tokens concurrently
        tasks = [detector.analyze_token_spam(mint) for mint in test_tokens]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = asyncio.get_event_loop().time() - start_time
        
        print(f"   📊 Analyzed {len(test_tokens)} tokens in {total_time:.2f}s")
        print(f"   📊 Average per token: {total_time/len(test_tokens):.2f}s")
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"   ❌ Token {i+1}: {result}")
            else:
                metrics = result.get("spam_metrics", {})
                spam_pct = metrics.get("spam_percentage", 0)
                risk_level = metrics.get("risk_level", "unknown")
                print(f"   📈 Token {i+1}: {spam_pct:.1f}% spam ({risk_level})")


async def main():
    """Run all tests."""
    try:
        await test_specific_tokens()
        await benchmark_performance()
        await test_batch_analysis()
        
        print(f"\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())