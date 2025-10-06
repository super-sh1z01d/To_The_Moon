#!/usr/bin/env python3
"""
Daemon script for continuous spam monitoring.
Runs spam detection every 5 seconds for top tokens.
"""

import asyncio
import sys
import os
import time
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.scheduler.tasks import monitor_spam_once

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("spam_monitor_daemon")


async def spam_monitor_daemon():
    """Run spam monitoring continuously every 5 seconds."""
    logger.info("🚀 Starting spam monitoring daemon (5 second intervals)")
    
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            start_time = time.time()
            
            logger.info(f"📊 Starting spam monitoring cycle #{cycle_count}")
            
            # Run spam monitoring
            await monitor_spam_once()
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Cycle #{cycle_count} completed in {elapsed:.2f}s")
            
            # Wait for next cycle (5 seconds total)
            sleep_time = max(0, 5.0 - elapsed)
            if sleep_time > 0:
                logger.debug(f"💤 Sleeping for {sleep_time:.2f}s until next cycle")
                await asyncio.sleep(sleep_time)
            else:
                logger.warning(f"⚠️  Cycle took longer than 5s ({elapsed:.2f}s), starting next cycle immediately")
            
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal, shutting down...")
            break
            
        except Exception as e:
            logger.error(f"❌ Error in spam monitoring cycle #{cycle_count}: {e}")
            logger.exception("Full traceback:")
            
            # Wait before retrying
            await asyncio.sleep(5.0)


def main():
    """Main entry point."""
    try:
        asyncio.run(spam_monitor_daemon())
    except KeyboardInterrupt:
        logger.info("👋 Spam monitoring daemon stopped")
    except Exception as e:
        logger.error(f"💥 Daemon crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()