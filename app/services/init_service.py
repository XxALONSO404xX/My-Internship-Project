"""Initialization service for system setup"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.device import Device
from app.models.firmware import Firmware

logger = logging.getLogger(__name__)

async def init_system(db: AsyncSession) -> None:
    """Initialize the system with required accounts and data"""
    # Check if any devices exist; if not, seed sample data
    try:
        result = await db.execute(select(Device))
        existing_devices = result.scalars().first()
        if existing_devices is None:
            sample_devices = [
                {
                    "name": "Smart Light 1",
                    "ip_address": "192.168.1.10",
                    "device_type": "light",
                    "manufacturer": "Philips",
                    "model": "Hue White",
                    "supports_http": True,
                    "supports_mqtt": True,
                    "device_metadata": {"state": {"power": False, "brightness": 0}},
                },
                {
                    "name": "Smart Thermostat",
                    "ip_address": "192.168.1.11",
                    "device_type": "thermostat",
                    "manufacturer": "Nest",
                    "model": "T3007ES",
                    "supports_http": True,
                    "supports_mqtt": False,
                    "device_metadata": {"state": {"power": True, "temperature": 22}},
                },
                {
                    "name": "Security Camera",
                    "ip_address": "192.168.1.12",
                    "device_type": "camera",
                    "manufacturer": "Arlo",
                    "model": "Pro 3",
                    "supports_http": True,
                    "supports_mqtt": False,
                    "device_metadata": {"state": {"power": True, "recording": False}},
                },
                {
                    "name": "Smart Lock",
                    "ip_address": "192.168.1.13",
                    "device_type": "lock",
                    "manufacturer": "August",
                    "model": "Smart Lock Pro",
                    "supports_http": False,
                    "supports_mqtt": True,
                    "device_metadata": {"state": {"power": True, "locked": True}},
                },
                {
                    "name": "Smart Plug",
                    "ip_address": "192.168.1.14",
                    "device_type": "plug",
                    "manufacturer": "TP-Link",
                    "model": "HS110",
                    "supports_http": True,
                    "supports_mqtt": True,
                    "device_metadata": {"state": {"power": False}},
                },
            ]
            for device_data in sample_devices:
                db.add(Device(**device_data))
            await db.commit()
            logger.info(f"Seeded {len(sample_devices)} sample devices")
        else:
            logger.info("Devices already exist; skipping seeding")
    except Exception as e:
        logger.error(f"Error during system initialization: {e}", exc_info=True)
    # Seed firmware records if none exist
    try:
        result_fw = await db.execute(select(Firmware))
        existing_fw = result_fw.scalars().first()
        if existing_fw is None:
            sample_fw = [
                {"device_type": "light",      "version": "1.0.0", "name": "Hue White FW 1.0.0", "is_critical": False},
                {"device_type": "thermostat", "version": "2.1.0", "name": "Nest Thermostat FW 2.1.0", "is_critical": False},
                {"device_type": "camera",     "version": "3.2.1", "name": "Arlo Pro FW 3.2.1", "is_critical": True},
                {"device_type": "lock",       "version": "1.5.0", "name": "August Lock FW 1.5.0", "is_critical": True},
                {"device_type": "plug",       "version": "1.0.5", "name": "TP-Link HS110 FW 1.0.5", "is_critical": False},
            ]
            for fw in sample_fw:
                db.add(Firmware(**fw))
            await db.commit()
            logger.info(f"Seeded {len(sample_fw)} sample firmware records")
        else:
            logger.info("Firmware records exist; skipping firmware seeding")
    except Exception as e:
        logger.error(f"Error during firmware seeding: {e}", exc_info=True)
    finally:
        logger.info("System initialization completed")