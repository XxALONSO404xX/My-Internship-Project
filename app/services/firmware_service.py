"""Simplified Firmware service for IoT Platform"""
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.firmware import Firmware, FirmwareUpdate
from app.core.logging import logger
from app.services.job_service import job_service, JobStatus
from app.utils.notification_helper import NotificationHelper
from app.utils.vulnerability_utils import VulnerabilityManager

class FirmwareService:
    """Simplified service for managing device firmware updates"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all_firmware(self, skip: int = 0, limit: int = 100) -> List[Firmware]:
        """Get all firmware versions with pagination"""
        query = select(Firmware).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_firmware_by_id(self, firmware_id: str) -> Optional[Firmware]:
        """Get firmware by ID"""
        query = select(Firmware).where(Firmware.id == firmware_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_firmware_by_version(self, version: str, device_type: str) -> Optional[Firmware]:
        """Get firmware by version and device type"""
        query = select(Firmware).where(
            and_(Firmware.version == version, Firmware.device_type == device_type)
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def create_firmware(self, 
                             version: str,
                             name: str,
                             device_type: str,
                             is_critical: bool = False) -> Firmware:
        """Create a new firmware entry"""
        firmware = Firmware(
            id=str(uuid.uuid4()),
            version=version,
            name=name,
            device_type=device_type,
            release_date=datetime.utcnow(),
            is_critical=is_critical
        )
        
        self.db.add(firmware)
        await self.db.commit()
        await self.db.refresh(firmware)
        
        return firmware
    
    async def start_firmware_update(self, device_id: str, target_version: str, force_update: bool = False) -> str:
        """Start firmware update for a device
        
        Args:
            device_id: ID of the device to update
            target_version: Target firmware version
            force_update: Whether to force update even if current version is same/newer
            
        Returns:
            The ID of the created firmware update job
        """
        # Verify device exists
        device_query = select(Device).where(Device.hash_id == device_id)
        device_result = await self.db.execute(device_query)
        device = device_result.scalars().first()
        
        if not device:
            raise ValueError(f"Device with ID {device_id} not found")
        
        # Find target firmware
        firmware_query = select(Firmware).where(
            and_(
                Firmware.version == target_version,
                Firmware.device_type == device.device_type
            )
        )
        firmware_result = await self.db.execute(firmware_query)
        firmware = firmware_result.scalars().first()
        
        if not firmware:
            # Auto-create firmware entry on-the-fly to satisfy demo flows
            logger.warning(
                f"Firmware {target_version} for {device.device_type} missing; creating baseline record automatically."
            )
            firmware = await self.create_firmware(
                version=target_version,
                name=f"{device.device_type} Firmware v{target_version}",
                device_type=device.device_type,
                is_critical=False,
            )
        
        # Check if update is needed
        if not force_update and device.firmware_version == target_version:
            raise ValueError(f"Device already has firmware version {target_version}")
        
        # Create update record
        update_id = str(uuid.uuid4())
        firmware_update = FirmwareUpdate(
            id=update_id,
            device_id=device_id,
            firmware_id=firmware.id,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        self.db.add(firmware_update)
        await self.db.commit()
        
        # Create a job for this update
        job_id = await job_service.create_job(
            job_type="firmware_update",
            description=f"Update firmware to {target_version} on device {device.name}",
            metadata={
                "device_id": device_id,
                "firmware_id": firmware.id,
                "target_version": target_version,
                "update_id": update_id
            }
        )
        
        # Update the firmware update record with the job ID
        await self.db.execute(
            update(FirmwareUpdate)
            .where(FirmwareUpdate.id == update_id)
            .values(job_id=job_id)
        )
        await self.db.commit()
        
        # Start the firmware update job
        await self._process_firmware_update(job_id)
        
        return update_id
    
    async def get_update_status(self, update_id: str) -> Dict[str, Any]:
        """Get the status of a firmware update"""
        query = select(FirmwareUpdate).where(FirmwareUpdate.id == update_id)
        result = await self.db.execute(query)
        update = result.scalars().first()
        
        if not update:
            raise ValueError(f"Update with ID {update_id} not found")
        
        # Get job status if available
        job_status = None
        if update.job_id:
            job_status = await job_service.get_job_status(update.job_id)
        
        return {
            "id": update.id,
            "device_id": update.device_id,
            "status": update.status,
            "created_at": update.created_at.isoformat() if update.created_at else None,
            "completed_at": update.completed_at.isoformat() if update.completed_at else None,
            "job_id": update.job_id,
            "job_status": job_status.value if hasattr(job_status, "value") else job_status,
            "job_progress": await job_service.get_job_status(update.job_id) if hasattr(job_service, "get_job_status") else None
        }
    
    async def _process_firmware_update(self, job_id: str) -> None:
        """Process a firmware update job
        
        This simplified version just marks the update as completed after a short delay
        """
        # Get job details
        job = await job_service.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        # Get update details
        update_id = job.metadata.get("update_id")
        if not update_id:
            logger.error(f"Job {job_id} has no update_id in metadata")
            await job_service.update_job_status(job_id, JobStatus.FAILED)
            return
        
        # Mark job as running
        await job_service.update_job_status(job_id, JobStatus.RUNNING)

        # Simulate download with progress updates
        for pct in [0, 20, 40, 60, 80]:
            await job_service.update_job_progress(job_id, pct, f"Downloading firmware... {pct}%")
            await asyncio.sleep(1)
        
        # Finalize download
        await job_service.update_job_progress(job_id, 90, "Applying firmware")

        try:
            # In a real implementation, this would communicate with the device
            # to perform the actual firmware update. For simplicity, we just
            # mark it as completed after updating the device record.
            
            # Get device and firmware details
            device_id = job.metadata.get("device_id")
            firmware_id = job.metadata.get("firmware_id")
            target_version = job.metadata.get("target_version")
            
            # Update the device's firmware version
            await self.db.execute(
                update(Device)
                .where(Device.hash_id == device_id)
                .values(
                    firmware_version=target_version,
                    current_firmware_id=firmware_id
                )
            )
            
            # Update the firmware update status
            await self.db.execute(
                update(FirmwareUpdate)
                .where(FirmwareUpdate.id == update_id)
                .values(
                    status="completed",
                    completed_at=datetime.utcnow()
                )
            )
            
            await self.db.commit()
            
            # Remove firmware-fixable vulnerabilities from state
            vm = VulnerabilityManager()
            vulns = vm.get_device_vulnerabilities(device_id)
            remaining = [v for v in vulns if v.get("fix_available") != "firmware_update"]
            vm._update_device_vulnerabilities(device_id, remaining)
            vm.save_state()
            
            # Mark job as completed
            await job_service.update_job_progress(job_id, 100, "Completed")
            await job_service.update_job_status(job_id, JobStatus.COMPLETED)
            
        except Exception as e:
            logger.error(f"Error processing firmware update: {str(e)}")
            
            # Mark the update as failed
            try:
                await self.db.execute(
                    update(FirmwareUpdate)
                    .where(FirmwareUpdate.id == update_id)
                    .values(
                        status="failed",
                        error_message=str(e),
                        completed_at=datetime.utcnow()
                    )
                )
                await self.db.commit()
            except Exception as inner_e:
                logger.error(f"Failed to mark update as failed: {str(inner_e)}")
            
            # Mark job as failed
            await job_service.update_job_status(job_id, JobStatus.FAILED)
