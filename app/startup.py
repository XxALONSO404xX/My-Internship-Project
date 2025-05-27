"""Startup initialization tasks"""
import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rule_checker import start_rule_checker
from app.services.sensor_generator import start_sensor_generator
from app.services.token_service import TokenService

logger = logging.getLogger(__name__)

async def clean_expired_tokens(db: AsyncSession, interval_seconds: int = 3600):
    """Clean expired tokens periodically"""
    while True:
        try:
            token_service = TokenService(db)
            count = await token_service.clean_expired_tokens()
            if count > 0:
                logger.info(f"Cleaned {count} expired tokens")
        except Exception as e:
            logger.error(f"Error cleaning expired tokens: {str(e)}")
        
        # Wait for next interval
        await asyncio.sleep(interval_seconds)

async def start_background_services(db: AsyncSession):
    """Start virtual background service tasks"""
    # Start the virtual rule evaluation service
    logger.info("Starting virtual rule evaluation service")
    start_rule_checker(5)
    
    # Start the virtual sensor reading generator
    logger.info("Starting virtual sensor data generator")
    start_sensor_generator(60)
    
    # Start token cleanup task
    logger.info("Starting authentication token cleanup service")
    asyncio.create_task(clean_expired_tokens(db, 3600))
    
    logger.info("All virtual background services started")

async def run_startup_tasks(db: AsyncSession):
    """Run all startup initialization tasks"""
    # Start background services
    await start_background_services(db) 