"""Virtual rule checking service for simulated rule evaluation"""
import logging
import asyncio
from typing import Dict, Any

from app.models.database import get_db
from app.services.rule_service import RuleService

logger = logging.getLogger(__name__)

async def check_rules_periodically(interval_seconds: int = 5):
    """
    Virtually check all rules against all devices in the database periodically
    
    This simulates evaluating rules against virtual devices, with all data
    coming from the database. No actual network devices are affected.
    
    Args:
        interval_seconds: How often to check rules (in seconds)
    """
    logger.info(f"Virtual rule checker started - evaluating rules every {interval_seconds} seconds")
    
    while True:
        try:
            # Get a new database session for each check
            async for db in get_db():
                rule_service = RuleService(db)
                result = await rule_service.apply_all_rules()
                
                # Only log when rules are actually triggered
                if result.get("devices_affected", 0) > 0:
                    logger.info(f"Virtual rule evaluation: affected {result.get('devices_affected', 0)} devices with {result.get('total_actions', 0)} actions")
                
                break  # Only need one session iteration
                
        except Exception as e:
            logger.error(f"Error in virtual rule checker: {str(e)}", exc_info=True)
            
        # Wait before next check
        await asyncio.sleep(interval_seconds)

def start_rule_checker(interval_seconds: int = 5) -> asyncio.Task:
    """
    Start the virtual rule checker as a background task
    
    Args:
        interval_seconds: How often to check rules (in seconds)
        
    Returns:
        The created asyncio task
    """
    task = asyncio.create_task(check_rules_periodically(interval_seconds))
    logger.info(f"Virtual rule checker started (every {interval_seconds} seconds)")
    return task 