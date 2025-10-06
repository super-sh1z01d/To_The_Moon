#!/usr/bin/env python3
"""
Test script for spam monitoring task.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.scheduler.tasks import run_spam_monitor


def main():
    """Test spam monitoring task."""
    print("🔍 Testing spam monitoring task...")
    
    try:
        run_spam_monitor()
        print("✅ Spam monitoring completed successfully!")
        
    except Exception as e:
        print(f"❌ Spam monitoring failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()