"""Firmware API endpoints for IoT platform"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.firmware_service import FirmwareService
from app.services.device_service import DeviceService
from app.services.notification_service import NotificationService
from app.api import schemas
from app.api.deps import get_current_client

router = APIRouter()

@router.get("/", response_model=List[schemas.FirmwareResponse])
async def list_firmware(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    db: AsyncSession = Depends(get_db)
):
    """List all firmware with optional filtering by device type"""
    firmware_service = FirmwareService(db)
    firmware_list = await firmware_service.get_all_firmware(skip=skip, limit=limit)
    
    # Apply device type filter if provided
    if device_type and firmware_list:
        firmware_list = [fw for fw in firmware_list if fw.device_type == device_type]
    
    return firmware_list

@router.post("/", response_model=schemas.FirmwareResponse, status_code=201)
async def create_firmware(
    firmware: schemas.FirmwareCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_client)
):
    """Create new firmware"""
    firmware_service = FirmwareService(db)
    
    # Use current user ID if available
    created_by = current_user.get("id") if current_user else None
    
    new_firmware = await firmware_service.create_firmware(
        version=firmware.version,
        name=firmware.name,
        device_type=firmware.device_type,
        description=firmware.description,
        file_size=firmware.file_size,
        changelog=firmware.changelog,
        is_critical=firmware.is_critical,
        created_by=created_by
    )
    
    return new_firmware

@router.get("/{firmware_id}", response_model=schemas.FirmwareResponse)
async def get_firmware(
    firmware_id: str = Path(..., description="Firmware ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get specific firmware by ID"""
    firmware_service = FirmwareService(db)
    firmware = await firmware_service.get_firmware_by_id(firmware_id)
    
    if not firmware:
        raise HTTPException(status_code=404, detail="Firmware not found")
    
    return firmware

@router.get("/device/{device_id}/compatible", response_model=List[schemas.FirmwareResponse])
async def get_device_compatible_firmware(
    device_id: str = Path(..., description="Device hash ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get compatible firmware for a specific device"""
    firmware_service = FirmwareService(db)
    device_service = DeviceService(db)
    
    # Verify device exists
    device = await device_service.get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    firmware_list = await firmware_service.get_device_compatible_firmware(device_id)
    return firmware_list

@router.post("/updates", response_model=schemas.FirmwareUpdateResponse, status_code=201)
async def start_firmware_update(
    update: schemas.FirmwareUpdateCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Start firmware update for a device"""
    firmware_service = FirmwareService(db)
    device_service = DeviceService(db)
    
    # Verify device exists
    device = await device_service.get_device_by_id(update.device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    try:
        # Start the firmware update
        firmware_update = await firmware_service.start_update(
            device_id=update.device_id,
            firmware_id=update.firmware_id
        )
        
        return firmware_update
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting firmware update: {str(e)}")

@router.get("/updates/{update_id}", response_model=schemas.FirmwareUpdateResponse)
async def get_update_status(
    update_id: str = Path(..., description="Update ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get firmware update status"""
    firmware_service = FirmwareService(db)
    update = await firmware_service.get_update_by_id(update_id)
    
    if not update:
        raise HTTPException(status_code=404, detail="Update not found")
    
    return update

@router.get("/device/{device_id}/updates", response_model=List[schemas.FirmwareUpdateResponse])
async def get_device_updates(
    device_id: str = Path(..., description="Device hash ID"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get firmware update history for a device"""
    firmware_service = FirmwareService(db)
    device_service = DeviceService(db)
    
    # Verify device exists
    device = await device_service.get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    updates = await firmware_service.get_device_updates(device_id, limit)
    return updates

@router.post("/batch", response_model=schemas.FirmwareBatchResponse, status_code=201)
async def start_batch_update(
    batch_update: schemas.FirmwareBatchCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_client)
):
    """Start a batch firmware update for multiple devices"""
    firmware_service = FirmwareService(db)
    
    # Use current user ID if available
    created_by = current_user.get("id") if current_user else None
    
    try:
        # Start the batch update
        batch = await firmware_service.start_batch_update(
            firmware_id=batch_update.firmware_id,
            device_ids=batch_update.device_ids,
            device_type=batch_update.device_type,
            name=batch_update.name,
            created_by=created_by
        )
        
        return batch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting batch update: {str(e)}")

@router.get("/batch/{batch_id}", response_model=schemas.FirmwareBatchResponse)
async def get_batch_status(
    batch_id: str = Path(..., description="Batch update ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get batch update status"""
    firmware_service = FirmwareService(db)
    batch = await firmware_service.get_batch_by_id(batch_id)
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch update not found")
    
    return batch

@router.get("/device/{device_id}/history", response_model=List[schemas.DeviceFirmwareHistoryResponse])
async def get_device_firmware_history(
    device_id: str = Path(..., description="Device hash ID"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get firmware version history for a device"""
    firmware_service = FirmwareService(db)
    device_service = DeviceService(db)
    
    # Verify device exists
    device = await device_service.get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    history = await firmware_service.get_device_firmware_history(device_id, limit)
    return history
