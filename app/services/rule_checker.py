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
                
                # Handle new standardized response format
                if result.get("status") == "success" and result.get("data"):
                    data = result.get("data", {})
                    devices_affected = data.get("devices_affected", 0)
                    total_actions = data.get("total_actions", 0)
                    
                    # Only log when rules are actually triggered
                    if devices_affected > 0:
                        logger.info(f"Virtual rule evaluation: affected {devices_affected} devices with {total_actions} actions")
                        
                        # Additional debugging for execution details
                        execution_id = data.get("execution_id")
                        if execution_id:
                            logger.debug(f"Rule execution ID: {execution_id}")
                elif result.get("status") == "error":
                    error_msg = result.get("message", "Unknown error in rule execution")
                    errors = result.get("errors", [])
                    error_details = ", ".join([f"{e.get('field')}: {e.get('detail')}" for e in errors]) if errors else "No details"
                    logger.error(f"Rule execution error: {error_msg} - {error_details}")
                
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