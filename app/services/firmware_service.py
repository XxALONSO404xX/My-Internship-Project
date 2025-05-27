"""Firmware service for IoT Platform"""
import logging
import random
import asyncio
import uuid
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Set, Tuple
from sqlalchemy import select, update, delete, desc, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.device import Device
from app.models.firmware import Firmware, FirmwareUpdate, FirmwareBatchUpdate, DeviceFirmwareHistory
from app.services.notification_service import NotificationService
from app.core.logging import logger
from app.utils.simulation import simulate_network_delay, simulate_failures

class FirmwareService:
    """Service for managing device firmware updates"""
    
    # Common encryption methods for simulating secure updates
    ENCRYPTION_METHODS = [
        "AES-256-GCM",
        "ChaCha20-Poly1305", 
        "AES-128-CBC",
        "AES-256-CBC",
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-ECDSA-AES256-GCM-SHA384"
    ]
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._update_tasks = set()
        
    async def get_all_firmware(self, skip: int = 0, limit: int = 100) -> List[Firmware]:
        """Get all firmware versions with pagination"""
        query = select(Firmware).order_by(desc(Firmware.release_date)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_firmware_by_id(self, firmware_id: str) -> Optional[Firmware]:
        """Get firmware by ID"""
        query = select(Firmware).where(Firmware.id == firmware_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_device_compatible_firmware(self, device_id: str) -> List[Firmware]:
        """Get compatible firmware versions for a device"""
        # Get device details
        device_query = select(Device).where(Device.hash_id == device_id)
        device_result = await self.db.execute(device_query)
        device = device_result.scalars().first()
        
        if not device:
            return []
        
        # Get firmware for device type
        query = select(Firmware).where(
            Firmware.device_type == device.device_type
        ).order_by(desc(Firmware.release_date))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_firmware(self, 
                             version: str,
                             name: str,
                             device_type: str,
                             description: Optional[str] = None,
                             file_size: Optional[int] = None,
                             changelog: Optional[str] = None,
                             is_critical: bool = False,
                             created_by: Optional[int] = None) -> Firmware:
        """Create a new firmware entry"""
        firmware = Firmware(
            id=str(uuid.uuid4()),
            version=version,
            name=name,
            description=description,
            device_type=device_type,
            release_date=datetime.utcnow(),
            file_size=file_size or random.randint(500000, 5000000),  # Default random size if not provided
            changelog=changelog,
            is_critical=is_critical,
            created_by=created_by
        )
        
        self.db.add(firmware)
        await self.db.commit()
        await self.db.refresh(firmware)
        
        return firmware
    
    async def start_update(self, device_id: str, firmware_id: str) -> FirmwareUpdate:
        """Start firmware update for a single device"""
        # Verify device exists
        device_query = select(Device).where(Device.hash_id == device_id)
        device_result = await self.db.execute(device_query)
        device = device_result.scalars().first()
        
        if not device:
            raise ValueError(f"Device with ID {device_id} not found")
        
        if not device.firmware_update_support:
            raise ValueError(f"Device {device.name} does not support firmware updates")
        
        if not device.is_online:
            raise ValueError(f"Device {device.name} is offline and cannot be updated")
        
        # Verify firmware exists
        firmware_query = select(Firmware).where(Firmware.id == firmware_id)
        firmware_result = await self.db.execute(firmware_query)
        firmware = firmware_result.scalars().first()
        
        if not firmware:
            raise ValueError(f"Firmware with ID {firmware_id} not found")
        
        # Check if device type matches
        if firmware.device_type != device.device_type:
            raise ValueError(f"Firmware is not compatible with device type {device.device_type}")
        
        # Check if already on this version
        if device.current_firmware_id == firmware_id:
            raise ValueError(f"Device {device.name} is already on firmware version {firmware.version}")
        
        # Check if there's already an update in progress
        existing_query = select(FirmwareUpdate).where(
            and_(
                FirmwareUpdate.device_id == device_id,
                FirmwareUpdate.status.in_(["pending", "downloading", "installing", "rebooting"])
            )
        )
        existing_result = await self.db.execute(existing_query)
        existing_update = existing_result.scalars().first()
        
        if existing_update:
            raise ValueError(f"There is already an update in progress for device {device.name}")
        
        # Create update record
        update = FirmwareUpdate(
            id=str(uuid.uuid4()),
            device_id=device_id,
            firmware_id=firmware_id,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        self.db.add(update)
        await self.db.commit()
        await self.db.refresh(update)
        
        # Start update simulation in background
        task = asyncio.create_task(self._simulate_update(update.id))
        self._update_tasks.add(task)
        task.add_done_callback(self._update_tasks.discard)
        
        return update
    
    async def start_batch_update(self, 
                               firmware_id: str, 
                               device_ids: Optional[List[str]] = None,
                               device_type: Optional[str] = None,
                               name: Optional[str] = None,
                               created_by: Optional[int] = None) -> FirmwareBatchUpdate:
        """Start a batch firmware update for multiple devices"""
        # Verify firmware exists
        firmware_query = select(Firmware).where(Firmware.id == firmware_id)
        firmware_result = await self.db.execute(firmware_query)
        firmware = firmware_result.scalars().first()
        
        if not firmware:
            raise ValueError(f"Firmware with ID {firmware_id} not found")
        
        # If device_type is provided, use that to find devices
        if device_type and not device_ids:
            devices_query = select(Device).where(
                and_(
                    Device.device_type == device_type,
                    Device.is_online == True,
                    Device.firmware_update_support == True
                )
            )
            devices_result = await self.db.execute(devices_query)
            devices = devices_result.scalars().all()
            device_ids = [device.hash_id for device in devices]
        
        if not device_ids:
            raise ValueError("No devices specified for batch update")
        
        # Create batch update record
        batch = FirmwareBatchUpdate(
            id=str(uuid.uuid4()),
            firmware_id=firmware_id,
            name=name or f"Batch update to {firmware.version}",
            status="pending",
            total_devices=len(device_ids),
            created_at=datetime.utcnow(),
            created_by=created_by
        )
        
        self.db.add(batch)
        await self.db.commit()
        await self.db.refresh(batch)
        
        # Start update for each device
        for device_id in device_ids:
            try:
                # Verify device exists and is compatible
                device_query = select(Device).where(Device.hash_id == device_id)
                device_result = await self.db.execute(device_query)
                device = device_result.scalars().first()
                
                if not device:
                    logger.warning(f"Device with ID {device_id} not found for batch update")
                    continue
                
                if not device.firmware_update_support:
                    logger.warning(f"Device {device.name} does not support firmware updates")
                    continue
                
                if not device.is_online:
                    logger.warning(f"Device {device.name} is offline and cannot be updated")
                    continue
                
                if firmware.device_type != device.device_type:
                    logger.warning(f"Firmware is not compatible with device {device.name}")
                    continue
                
                if device.current_firmware_id == firmware_id:
                    logger.info(f"Device {device.name} is already on firmware version {firmware.version}")
                    continue
                
                # Check if there's already an update in progress
                existing_query = select(FirmwareUpdate).where(
                    and_(
                        FirmwareUpdate.device_id == device_id,
                        FirmwareUpdate.status.in_(["pending", "downloading", "installing", "rebooting"])
                    )
                )
                existing_result = await self.db.execute(existing_query)
                existing_update = existing_result.scalars().first()
                
                if existing_update:
                    logger.warning(f"There is already an update in progress for device {device.name}")
                    continue
                
                # Create update record for this device in the batch
                update = FirmwareUpdate(
                    id=str(uuid.uuid4()),
                    device_id=device_id,
                    firmware_id=firmware_id,
                    status="pending",
                    batch_id=batch.id,
                    created_at=datetime.utcnow()
                )
                
                self.db.add(update)
                
            except Exception as e:
                logger.error(f"Error preparing update for device {device_id}: {str(e)}")
        
        # Commit all updates at once
        await self.db.commit()
        
        # Start batch update simulation
        task = asyncio.create_task(self._simulate_batch_update(batch.id))
        self._update_tasks.add(task)
        task.add_done_callback(self._update_tasks.discard)
        
        return batch
    
    async def get_update_by_id(self, update_id: str) -> Optional[FirmwareUpdate]:
        """Get update by ID with relationships loaded"""
        query = select(FirmwareUpdate).where(FirmwareUpdate.id == update_id)\
            .options(selectinload(FirmwareUpdate.device), selectinload(FirmwareUpdate.firmware))
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_batch_by_id(self, batch_id: str) -> Optional[FirmwareBatchUpdate]:
        """Get batch update by ID with relationships loaded"""
        query = select(FirmwareBatchUpdate).where(FirmwareBatchUpdate.id == batch_id)\
            .options(selectinload(FirmwareBatchUpdate.firmware))
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_device_updates(self, device_id: str, limit: int = 10) -> List[FirmwareUpdate]:
        """Get firmware update history for a device"""
        query = select(FirmwareUpdate).where(FirmwareUpdate.device_id == device_id)\
            .options(selectinload(FirmwareUpdate.firmware))\
            .order_by(desc(FirmwareUpdate.created_at)).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_device_firmware_history(self, device_id: str, limit: int = 10) -> List[DeviceFirmwareHistory]:
        """Get firmware version history for a device"""
        query = select(DeviceFirmwareHistory).where(DeviceFirmwareHistory.device_id == device_id)\
            .options(selectinload(DeviceFirmwareHistory.firmware))\
            .order_by(desc(DeviceFirmwareHistory.updated_at)).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
        
    async def simulate_tls_handshake(self, device: Device) -> Tuple[bool, Optional[str], Optional[str]]:
        """Simulate TLS handshake with a device
        
        Args:
            device: Device to handshake with
            
        Returns:
            Tuple containing (success, tls_version, encryption_method)
        """
        # Check if device supports TLS
        if not device.supports_tls:
            logger.warning(f"Device {device.name} does not support TLS")
            return (False, None, None)
            
        # Check certificate expiry
        if device.cert_expiry and device.cert_expiry < datetime.utcnow():
            logger.error(f"Device {device.name} has expired certificate")
            return (False, None, None)
            
        # Simulate TLS handshake success probability
        # Higher cert strength and newer TLS versions have better success rates
        base_success_rate = 0.95  # 95% success by default
        
        # Adjust for TLS version
        if device.tls_version == "TLS 1.3":
            version_factor = 0.04  # 4% bonus for TLS 1.3
        elif device.tls_version == "TLS 1.2":
            version_factor = 0.0   # Neutral for TLS 1.2
        else:
            version_factor = -0.1  # 10% penalty for older or unknown versions
            
        # Adjust for certificate strength
        if device.cert_strength and device.cert_strength >= 4096:
            strength_factor = 0.03  # 3% bonus for 4096-bit certs
        elif device.cert_strength and device.cert_strength >= 3072:
            strength_factor = 0.01  # 1% bonus for 3072-bit certs
        elif device.cert_strength and device.cert_strength >= 2048:
            strength_factor = 0.0   # Neutral for 2048-bit certs
        else:
            strength_factor = -0.05  # 5% penalty for weaker certs
            
        success_rate = min(0.999, base_success_rate + version_factor + strength_factor)
        
        # Simulate handshake success
        success = random.random() < success_rate
        
        if not success:
            logger.warning(f"TLS handshake failed with device {device.name}")
            return (False, None, None)
            
        # Choose encryption method based on TLS version
        if device.tls_version == "TLS 1.3":
            # TLS 1.3 has a fixed set of more secure cipher suites
            encryption_methods = [
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256",
                "TLS_AES_128_GCM_SHA256"
            ]
            encryption_method = random.choice(encryption_methods)
        else:  # TLS 1.2 or older
            encryption_method = random.choice(self.ENCRYPTION_METHODS)
            
        logger.info(f"Successful TLS handshake with device {device.name} using {device.tls_version}, {encryption_method}")
        return (True, device.tls_version, encryption_method)
        
    async def verify_firmware_signature(self, firmware: Firmware) -> bool:
        """Simulate verification of firmware signature
        
        Args:
            firmware: Firmware to verify
            
        Returns:
            Whether signature verification succeeded
        """
        # Simulate signature verification with 98% success rate for normal updates
        # and 100% success rate for critical updates (assuming these are more carefully verified)
        success_rate = 1.0 if firmware.is_critical else 0.98
        
        # Use firmware data to create a deterministic but random-looking result
        # This ensures the same firmware will consistently pass or fail verification
        hash_input = f"{firmware.id}:{firmware.version}:{firmware.name}"
        hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16) % 100
        
        # Simulate a verification based on hash and success rate
        success = (hash_value / 100) < success_rate
        
        if not success:
            logger.warning(f"Firmware signature verification failed for {firmware.name} v{firmware.version}")
        
        return success
    
    async def _simulate_update(self, update_id: str) -> None:
        """Simulate firmware update process for a single device"""
        try:
            # Get update record with relationships
            async with self.db.begin():
                query = select(FirmwareUpdate).where(FirmwareUpdate.id == update_id)\
                    .options(selectinload(FirmwareUpdate.device), selectinload(FirmwareUpdate.firmware))
                result = await self.db.execute(query)
                update = result.scalars().first()
                
                if not update:
                    logger.error(f"Update {update_id} not found")
                    return
                
                # Get device and firmware
                device = update.device
                firmware = update.firmware
                
                # Perform TLS handshake if device supports it
                secure_channel, tls_version, encryption_method = await self.simulate_tls_handshake(device)
                update.secure_channel = secure_channel
                update.tls_version = tls_version
                update.encryption_method = encryption_method
                
                # Verify firmware signature
                update.signature_verified = await self.verify_firmware_signature(firmware)
                
                # If security checks fail, abort the update
                if not secure_channel and device.supports_tls:
                    update.status = "failed"
                    update.error_message = "Failed to establish secure channel with device"
                    update.error_code = "TLS_HANDSHAKE_ERROR"
                    return
                
                if not update.signature_verified:
                    update.status = "failed"
                    update.error_message = "Firmware signature verification failed"
                    update.error_code = "SIGNATURE_VERIFICATION_ERROR"
                    return
                
                # Update status to downloading
                update.status = "downloading"
                update.started_at = datetime.utcnow()
                
                # Simulate speed differences based on encryption method
                # More secure encryption might be slightly slower
                base_speed = random.randint(100, 5000)  # Base speed between 100 Kbps and 5 Mbps
                if secure_channel:
                    if "AES-256" in str(encryption_method) or "TLS_AES_256" in str(encryption_method):
                        speed_factor = random.uniform(0.85, 0.95)  # 5-15% slower for stronger encryption
                    elif "CHACHA20" in str(encryption_method) or "TLS_CHACHA20" in str(encryption_method):
                        speed_factor = random.uniform(0.88, 0.98)  # 2-12% slower
                    else:
                        speed_factor = random.uniform(0.9, 1.0)  # 0-10% slower
                else:
                    speed_factor = 1.0  # No encryption overhead
                    
                update.speed_kbps = int(base_speed * speed_factor)
                update.estimated_time_remaining = int(firmware.file_size / (update.speed_kbps * 1024))
            
            # Notify user that update has started
            notification_service = NotificationService(self.db)
            await notification_service.create_notification(
                title="Firmware Update Started",
                content=f"Update to {firmware.version} started for device {device.name}",
                notification_type="info",
                priority="medium",
                source="firmware",
                source_id=update.id,
                target_type="device",
                target_id=device.hash_id,
                target_name=device.name,
                # Add the soft green color theme to the notification
                metadata={
                    "ui": {
                        "theme": "green",
                        "colors": {
                            "primary": "#4ade80",
                            "primaryDark": "#16a34a",
                            "primaryLight": "#dcfce7",
                            "background": "#f0fdf4"
                        }
                    }
                }
            )
            
            # Simulate download progress (0-50%)
            for progress in range(0, 51, 5):
                # Calculate variable delay based on simulated speed
                delay = firmware.file_size / (update.speed_kbps * 1024) / 10  # Total time / 10 steps
                max_delay = min(3, delay)  # Cap at 3 seconds per step for UX
                await asyncio.sleep(random.uniform(0.5, max_delay))  # Random delay for realism
                
                # Network fluctuations
                if random.random() < 0.3:  # 30% chance of speed change
                    speed_change = random.uniform(0.7, 1.3)  # 30% slower to 30% faster
                    update.speed_kbps = int(update.speed_kbps * speed_change)
                
                # Update progress
                async with self.db.begin():
                    query = select(FirmwareUpdate).where(FirmwareUpdate.id == update_id)
                    result = await self.db.execute(query)
                    update = result.scalars().first()
                    
                    if not update:
                        logger.error(f"Update {update_id} not found during progress update")
                        return
                    
                    # Update progress
                    update.progress = progress
                    update.estimated_time_remaining = int((firmware.file_size * (100 - progress) / 100) / (update.speed_kbps * 1024))
                    
                    # Small chance of failure during download (7%)
                    if progress > 10 and random.random() < 0.07:
                        update.status = "failed"
                        update.error_message = "Connection lost during download"
                        update.error_code = "CONNECTION_ERROR"
                        
                        # Create notification
                        await notification_service.create_notification(
                            title="Firmware Update Failed",
                            content=f"Update to {firmware.version} failed for device {device.name} - Connection lost",
                            notification_type="alert",
                            priority="high",
                            source="firmware",
                            source_id=update.id,
                            target_type="device",
                            target_id=device.hash_id,
                            target_name=device.name,
                            metadata={
                                "ui": {
                                    "theme": "green",
                                    "colors": {
                                        "primary": "#4ade80",
                                        "primaryDark": "#16a34a",
                                        "primaryLight": "#dcfce7",
                                        "background": "#f0fdf4"
                                    }
                                }
                            }
                        )
                        return
            
            # Update status to installing
            async with self.db.begin():
                query = select(FirmwareUpdate).where(FirmwareUpdate.id == update_id)
                result = await self.db.execute(query)
                update = result.scalars().first()
                
                if not update or update.status == "failed":
                    return
                
                update.status = "installing"
                update.progress = 50
            
            # Simulate installation progress (50-80%)
            for progress in range(55, 81, 5):
                await asyncio.sleep(random.uniform(1, 3))  # Random delay for installation steps
                
                async with self.db.begin():
                    query = select(FirmwareUpdate).where(FirmwareUpdate.id == update_id)
                    result = await self.db.execute(query)
                    update = result.scalars().first()
                    
                    if not update or update.status == "failed":
                        return
                    
                    # Update progress
                    update.progress = progress
                    update.estimated_time_remaining = int((20 + (80 - progress)) / 5)  # Rough estimate
                    
                    # Small chance of failure during installation (5%)
                    if random.random() < 0.05:
                        update.status = "failed"
                        update.error_message = "Error during installation"
                        update.error_code = "INSTALL_ERROR"
                        
                        # Create notification
                        await notification_service.create_notification(
                            title="Firmware Update Failed",
                            content=f"Update to {firmware.version} failed for device {device.name} - Installation error",
                            notification_type="alert",
                            priority="high",
                            source="firmware",
                            source_id=update.id,
                            target_type="device",
                            target_id=device.hash_id,
                            target_name=device.name,
                            metadata={
                                "ui": {
                                    "theme": "green",
                                    "colors": {
                                        "primary": "#4ade80",
                                        "primaryDark": "#16a34a",
                                        "primaryLight": "#dcfce7",
                                        "background": "#f0fdf4"
                                    }
                                }
                            }
                        )
                        return
            
            # Update status to rebooting
            async with self.db.begin():
                query = select(FirmwareUpdate).where(FirmwareUpdate.id == update_id)
                result = await self.db.execute(query)
                update = result.scalars().first()
                
                if not update or update.status == "failed":
                    return
                
                update.status = "rebooting"
                update.progress = 85
            
            # Simulate reboot
            await asyncio.sleep(random.uniform(3, 7))  # Random delay for reboot
            
            # Update device firmware and record history
            async with self.db.begin():
                # Get update with fresh data
                query = select(FirmwareUpdate).where(FirmwareUpdate.id == update_id)\
                    .options(selectinload(FirmwareUpdate.device), selectinload(FirmwareUpdate.firmware))
                result = await self.db.execute(query)
                update = result.scalars().first()
                
                if not update or update.status == "failed":
                    return
                
                device = update.device
                firmware = update.firmware
                
                # Create history record
                history = DeviceFirmwareHistory(
                    device_id=device.hash_id,
                    firmware_id=firmware.id,
                    previous_version=device.firmware_version,
                    updated_at=datetime.utcnow(),
                    update_id=update.id
                )
                self.db.add(history)
                
                # Update device firmware version
                previous_firmware_id = device.current_firmware_id
                device.firmware_version = firmware.version
                device.current_firmware_id = firmware.id
                device.last_firmware_check = datetime.utcnow()
                
                # Mark update as completed
                update.status = "completed"
                update.progress = 100
                update.completed_at = datetime.utcnow()
                update.estimated_time_remaining = 0
            
            # Create success notification
            await notification_service.create_notification(
                title="Firmware Update Completed",
                content=f"Update to {firmware.version} completed for device {device.name}",
                notification_type="success",
                priority="medium",
                source="firmware",
                source_id=update.id,
                target_type="device",
                target_id=device.hash_id,
                target_name=device.name,
                metadata={
                    "ui": {
                        "theme": "green",
                        "colors": {
                            "primary": "#4ade80",
                            "primaryDark": "#16a34a",
                            "primaryLight": "#dcfce7",
                            "background": "#f0fdf4"
                        }
                    }
                }
            )
        
        except Exception as e:
            logger.error(f"Error during firmware update simulation: {str(e)}")
            
            # Try to mark as failed
            try:
                async with self.db.begin():
                    query = select(FirmwareUpdate).where(FirmwareUpdate.id == update_id)\
                        .options(selectinload(FirmwareUpdate.device), selectinload(FirmwareUpdate.firmware))
                    result = await self.db.execute(query)
                    update = result.scalars().first()
                    
                    if update:
                        update.status = "failed"
                        update.error_message = f"System error: {str(e)}"
                        update.error_code = "SYSTEM_ERROR"
                        
                        # Create notification
                        notification_service = NotificationService(self.db)
                        await notification_service.create_notification(
                            title="Firmware Update Failed",
                            content=f"Update failed for device {update.device.name} - System error",
                            notification_type="alert",
                            priority="high",
                            source="firmware",
                            source_id=update.id,
                            target_type="device",
                            target_id=update.device_id,
                            target_name=update.device.name if update.device else "Unknown",
                            metadata={
                                "ui": {
                                    "theme": "green",
                                    "colors": {
                                        "primary": "#4ade80",
                                        "primaryDark": "#16a34a",
                                        "primaryLight": "#dcfce7",
                                        "background": "#f0fdf4"
                                    }
                                }
                            }
                        )
            except Exception as inner_e:
                logger.error(f"Failed to mark update as failed: {str(inner_e)}")
    
    async def _simulate_batch_update(self, batch_id: str) -> None:
        """Simulate batch firmware update process"""
        try:
            # Get batch record
            async with self.db.begin():
                query = select(FirmwareBatchUpdate).where(FirmwareBatchUpdate.id == batch_id)\
                    .options(selectinload(FirmwareBatchUpdate.firmware))
                result = await self.db.execute(query)
                batch = result.scalars().first()
                
                if not batch:
                    logger.error(f"Batch {batch_id} not found")
                    return
                
                # Update status to in_progress
                batch.status = "in_progress"
                batch.started_at = datetime.utcnow()
            
            # Get all updates in this batch
            query = select(FirmwareUpdate).where(FirmwareUpdate.batch_id == batch_id)
            result = await self.db.execute(query)
            updates = result.scalars().all()
            
            # Start updates with slight delays between them (parallel but staggered)
            tasks = []
            for i, update in enumerate(updates):
                # Stagger updates to prevent overwhelming the system
                await asyncio.sleep(random.uniform(0.5, 2))
                
                # Start update simulation
                task = asyncio.create_task(self._simulate_update(update.id))
                self._update_tasks.add(task)
                task.add_done_callback(self._update_tasks.discard)
                tasks.append(task)
            
            # Wait for all updates to complete
            await asyncio.gather(*tasks)
            
            # Update batch status and metrics
            async with self.db.begin():
                # Get fresh batch data
                query = select(FirmwareBatchUpdate).where(FirmwareBatchUpdate.id == batch_id)
                result = await self.db.execute(query)
                batch = result.scalars().first()
                
                if not batch:
                    return
                
                # Count successful and failed updates
                success_query = select(func.count()).where(
                    and_(
                        FirmwareUpdate.batch_id == batch_id,
                        FirmwareUpdate.status == "completed"
                    )
                )
                success_result = await self.db.execute(success_query)
                successful_devices = success_result.scalar()
                
                failed_query = select(func.count()).where(
                    and_(
                        FirmwareUpdate.batch_id == batch_id,
                        FirmwareUpdate.status == "failed"
                    )
                )
                failed_result = await self.db.execute(failed_query)
                failed_devices = failed_result.scalar()
                
                # Update batch metrics
                batch.successful_devices = successful_devices
                batch.failed_devices = failed_devices
                batch.completed_at = datetime.utcnow()
                
                # Determine final status
                if failed_devices == 0 and successful_devices > 0:
                    batch.status = "completed"
                elif successful_devices == 0:
                    batch.status = "failed"
                else:
                    batch.status = "partial"
            
            # Send notification about batch completion
            notification_service = NotificationService(self.db)
            if batch.status == "completed":
                await notification_service.create_notification(
                    title="Batch Firmware Update Completed",
                    content=f"Batch update '{batch.name}' completed successfully for all {batch.successful_devices} devices",
                    notification_type="success",
                    priority="medium",
                    source="firmware",
                    source_id=batch.id,
                    metadata={
                        "ui": {
                            "theme": "green",
                            "colors": {
                                "primary": "#4ade80",
                                "primaryDark": "#16a34a",
                                "primaryLight": "#dcfce7",
                                "background": "#f0fdf4"
                            }
                        }
                    }
                )
            elif batch.status == "partial":
                await notification_service.create_notification(
                    title="Batch Firmware Update Partially Completed",
                    content=f"Batch update '{batch.name}' completed with {batch.successful_devices} successful and {batch.failed_devices} failed devices",
                    notification_type="warning",
                    priority="medium",
                    source="firmware",
                    source_id=batch.id,
                    metadata={
                        "ui": {
                            "theme": "green",
                            "colors": {
                                "primary": "#4ade80",
                                "primaryDark": "#16a34a",
                                "primaryLight": "#dcfce7",
                                "background": "#f0fdf4"
                            }
                        }
                    }
                )
            else:  # failed
                await notification_service.create_notification(
                    title="Batch Firmware Update Failed",
                    content=f"Batch update '{batch.name}' failed for all devices",
                    notification_type="alert",
                    priority="high",
                    source="firmware",
                    source_id=batch.id,
                    metadata={
                        "ui": {
                            "theme": "green",
                            "colors": {
                                "primary": "#4ade80",
                                "primaryDark": "#16a34a",
                                "primaryLight": "#dcfce7",
                                "background": "#f0fdf4"
                            }
                        }
                    }
                )
        
        except Exception as e:
            logger.error(f"Error during batch firmware update simulation: {str(e)}")
            
            # Try to mark batch as failed
            try:
                async with self.db.begin():
                    query = select(FirmwareBatchUpdate).where(FirmwareBatchUpdate.id == batch_id)
                    result = await self.db.execute(query)
                    batch = result.scalars().first()
                    
                    if batch:
                        batch.status = "failed"
                        batch.completed_at = datetime.utcnow()
            except Exception as inner_e:
                logger.error(f"Failed to mark batch as failed: {str(inner_e)}")
