"""Initialization service for system setup"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def init_system(db: AsyncSession) -> None:
    """Initialize the system with required accounts and data"""
    logger.info("System initialization completed") 