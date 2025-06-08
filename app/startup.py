"""Startup initialization tasks"""
"""Startup tasks for the application"""
import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rule_checker import start_rule_checker
from app.services.sensor_generator import start_sensor_generator
from app.services.token_service import TokenService
from app.utils.vulnerability_utils import vulnerability_manager
from app.models.device import Device
# Removed job service import to simplify platform

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
    # Job monitoring service removed to simplify platform
    
    # Start background services
    await start_background_services(db)
    
    # Initialize vulnerabilities for select devices
    from app.services.security_service import vulnerability_initializer
    logger.info("Starting vulnerability initialization...")
    asyncio.create_task(vulnerability_initializer())
    logger.info("Vulnerability initialization task scheduled")

    # Seed firmware table if empty
    try:
        from app.services.firmware_service import FirmwareService
        from app.models.device import Device
        from sqlalchemy import select
        firmware_service = FirmwareService(db)
        existing_fw = await firmware_service.get_all_firmware()
        if not existing_fw:
            # fetch distinct device types
            res = await db.execute(select(Device.device_type).distinct())
            types = [row[0] for row in res.all()]
            for dtype in types:
                # baseline firmware
                await firmware_service.create_firmware(
                    version="1.0.0",
                    name=f"{dtype} Firmware v1.0.0",
                    device_type=dtype
                )
                # critical update
                await firmware_service.create_firmware(
                    version="1.1.0",
                    name=f"{dtype} Firmware v1.1.0",
                    device_type=dtype,
                    is_critical=True
                )
            logger.info(f"Seeded firmware for types: {types}")
    except Exception as e:
        logger.error(f"Firmware seeding error: {e}")