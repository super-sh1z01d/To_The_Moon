"""
Scheduler tasks for NotArb bot integration
"""

import logging
from datetime import datetime

from src.integrations.notarb_pools import NotArbPoolsGenerator
from src.core.config import get_config

logger = logging.getLogger(__name__)


def update_notarb_pools_file():
    """
    Scheduled task to update NotArb pools file
    """
    try:
        logger.info("Starting NotArb pools file update")
        
        # Configuration parameters
        config = get_config()
        output_path = getattr(config, 'notarb_config_path', 'markets.json')
        
        # Generate and export pools
        generator = NotArbPoolsGenerator(output_path)
        success = generator.export_pools_config()
        
        if success:
            logger.info(f"✅ NotArb pools file updated successfully: {output_path}")
        else:
            logger.error("❌ Failed to update NotArb pools file")
            
    except Exception as e:
        logger.error(f"Error in NotArb pools update task: {e}", exc_info=True)


