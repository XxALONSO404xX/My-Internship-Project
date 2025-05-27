"""Device API endpoints"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.models.device import Device
from app.models.sensor_reading import SensorReading
from app.models.client import Client
from app.services.device_service import DeviceService
from app.api.deps import get_db, get_current_client
from app.core.logging import logger
from app.api.schemas import (
    DeviceCreate, DeviceUpdate, DeviceInDB,
    DeviceControlResponse, DeviceStatusResponse,
    SensorReadingResponse, SensorSummaryResponse
)

router = APIRouter()

# Device Management Endpoints
@router.get("/", response_model=List[DeviceInDB])
async def list_devices(
    skip: int = 0, 
    limit: int = 100,
    device_type: Optional[str] = None,
    is_online: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Client = Depends(get_current_client)
):
    """List all devices with optional filtering"""
    try:
        device_service = DeviceService(db)
        devices = await device_service.get_all_devices()
        
        # Apply filters
        if device_type:
            devices = [d for d in devices if d.device_type == device_type]
        if is_online is not None:
            devices = [d for d in devices if d.is_online == is_online]
            
        return devices[skip:skip + limit]
    except Exception as e:
        logger.error(f"Error listing devices: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/", response_model=DeviceInDB)
async def create_device(
    device: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Client = Depends(get_current_client)
):
    """Create a new device"""
    try:
        device_service = DeviceService(db)
        return await device_service.create_device(device.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{device_id}", response_model=DeviceInDB)
async def get_device(device_id: str, db: AsyncSession = Depends(get_db), current_user: Client = Depends(get_current_client)):
    """Get a specific device"""
    try:
        device_service = DeviceService(db)
        device = await device_service.get_device_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        return device
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{device_id}", response_model=DeviceInDB)
async def update_device(device_id: str, device: DeviceUpdate, db: AsyncSession = Depends(get_db), current_user: Client = Depends(get_current_client)):
    """Update a device"""
    try:
        device_service = DeviceService(db)
        updated_device = await device_service.update_device(
            device_id,
            device.dict(exclude_unset=True),
            user_id=current_user.id,
            user_ip=current_user.last_ip
        )
        if not updated_device:
            raise HTTPException(status_code=404, detail="Device not found")
        return updated_device
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{device_id}")
async def delete_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Client = Depends(get_current_client)
):
    """Delete a device"""
    try:
        device_service = DeviceService(db)
        success = await device_service.delete_device(
            device_id,
            user_id=current_user.id,
            user_ip=current_user.last_ip
        )
        if not success:
            raise HTTPException(status_code=404, detail="Device not found")
        return {"status": "success", "message": "Device deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Device Control Endpoints
@router.post("/{device_id}/control", response_model=DeviceControlResponse)
async def control_device(device_id: str, action: str, parameters: Optional[Dict[str, Any]] = None, db: AsyncSession = Depends(get_db), current_user: Client = Depends(get_current_client)):
    """Control a device (virtual simulation)"""
    try:
        device_service = DeviceService(db)
        result = await device_service.control_device(
            device_id,
            action,
            parameters,
            user_id=current_user.id,
            user_ip=current_user.last_ip
        )
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Control failed")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error controlling device: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{device_id}/status", response_model=DeviceStatusResponse)
async def get_device_status(device_id: str, db: AsyncSession = Depends(get_db), current_user: Client = Depends(get_current_client)):
    """Get device status (virtual simulation)"""
    try:
        device_service = DeviceService(db)
        status = await device_service.get_device_status(device_id)
        if not status.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=status.get("error", "Device not found")
            )
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device status: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/{device_id}/status")
async def set_device_status(
    device_id: str,
    is_online: bool,
    db: AsyncSession = Depends(get_db),
    current_user: Client = Depends(get_current_client)
):
    """Set device online status (virtual simulation)"""
    try:
        device_service = DeviceService(db)
        device = await device_service.update_device_status(
            device_id,
            is_online,
            user_id=current_user.id,
            user_ip=current_user.last_ip
        )
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        return {"status": "success", "is_online": is_online}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting device status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{device_id}/simulate")
async def simulate_device_action(
    device_id: str,
    action: str,
    parameters: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Client = Depends(get_current_client)
):
    """Simulate a device action (for testing)"""
    try:
        device_service = DeviceService(db)
        result = await device_service.simulate_device_action(
            device_id,
            action,
            parameters,
            user_id=current_user.id,
            user_ip=current_user.last_ip
        )
        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "Simulation failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error simulating device action: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Sensor Readings Endpoints
@router.get("/{device_id}/readings", response_model=List[SensorReadingResponse])
async def get_device_readings(
    device_id: str,
    sensor_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Client = Depends(get_current_client)
):
    """Get sensor readings for a device"""
    try:
        # Build query
        query = select(SensorReading).where(SensorReading.device_id == device_id)
        
        if sensor_type:
            query = query.where(SensorReading.sensor_type == sensor_type)
        if start_time:
            query = query.where(SensorReading.timestamp >= start_time)
        if end_time:
            query = query.where(SensorReading.timestamp <= end_time)
        
        # Order and paginate
        query = query.order_by(desc(SensorReading.timestamp)).limit(limit).offset(offset)
        
        # Execute query
        result = await db.execute(query)
        readings = result.scalars().all()
        
        return [reading.to_dict() for reading in readings]
    except Exception as e:
        logger.error(f"Error getting sensor readings: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/sensors/summary", response_model=SensorSummaryResponse)
async def get_sensors_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Client = Depends(get_current_client)
):
    """Get summary of all sensor readings in the system"""
    try:
        # Get count of readings by device and sensor type
        query = (
            select(
                SensorReading.device_id,
                SensorReading.sensor_type,
                func.count(SensorReading.id).label("count"),
                func.min(SensorReading.timestamp).label("first_reading"),
                func.max(SensorReading.timestamp).label("last_reading")
            )
            .group_by(SensorReading.device_id, SensorReading.sensor_type)
        )
        result = await db.execute(query)
        rows = result.all()
        
        # Organize by device
        summary = {}
        for row in rows:
            device_id = row.device_id
            if device_id not in summary:
                summary[device_id] = {"sensors": {}}
            
            summary[device_id]["sensors"][row.sensor_type] = {
                "count": row.count,
                "first_reading": row.first_reading.isoformat() if row.first_reading else None,
                "last_reading": row.last_reading.isoformat() if row.last_reading else None
            }
        
        # Get device names
        for device_id in summary:
            device = await db.get(Device, device_id)
            if device:
                summary[device_id]["name"] = device.name
        
        return {"summary": summary}
    except Exception as e:
        logger.error(f"Error getting sensor summary: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{device_id}/history")
async def get_device_history(
    device_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: Client = Depends(get_current_client)
):
    """Get device activity history"""
    try:
        device_service = DeviceService(db)
        history = await device_service.get_device_history(device_id, limit)
        return history
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{device_id}/activities", response_model=None)
async def get_device_activities(
    device_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Get activity history for a device
    """
    try:
        # Check if device exists
        device_service = DeviceService(db)
        device = await device_service.get_device_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device with ID {device_id} not found")
        
        # Get activities
        from app.services.activity_service import ActivityService
        activity_service = ActivityService(db)
        
        activities = await activity_service.get_activities_by_target(
            target_type="device",
            target_id=device_id,
            limit=limit
        )
        
        # Convert to API response
        activity_list = [activity.to_dict() for activity in activities]
        
        return {
            "device_id": device_id,
            "device_name": device.name,
            "activities": activity_list,
            "total": len(activity_list)
        }
        
    except Exception as e:
        logger.error(f"Error getting activities for device {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{device_id}/snapshot", response_model=None)
async def simulate_device_snapshot(
    device_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Simulate taking a snapshot from a camera device
    Returns mock image data for demonstration purposes
    """
    try:
        # Get user info (mock for now)
        user_id = None
        user_ip = request.client.host
        
        device_service = DeviceService(db)
        
        # Check if device exists and is a camera
        device = await device_service.get_device_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device with ID {device_id} not found")
            
        if device.device_type != "CAMERA":
            raise HTTPException(status_code=400, detail=f"Device with ID {device_id} is not a camera")
            
        if not device.is_online:
            raise HTTPException(status_code=400, detail=f"Camera is offline")
        
        # Generate timestamp
        timestamp = datetime.utcnow()
        
        # Log activity
        await device_service.control_device(
            device_id=device_id,
            action="take_snapshot",
            user_id=user_id,
            user_ip=user_ip
        )
        
        # Return mock snapshot data
        return {
            "success": True,
            "device_id": device_id,
            "timestamp": timestamp.isoformat(),
            "snapshot_id": f"{int(timestamp.timestamp())}",
            "image_url": f"/api/devices/{device_id}/snapshots/{int(timestamp.timestamp())}",
            "resolution": device.device_metadata.get("resolution", "1080p"),
            "format": "jpeg"
        }
        
    except Exception as e:
        logger.error(f"Error taking snapshot from device {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulate/status-update")
async def simulate_device_status_update(
    device_id: int,
    status: str = Query(..., enum=["online", "offline", "error"]),
    db: AsyncSession = Depends(get_db)
):
    """
    Simulate a device status update
    
    This endpoint is used for testing and simulation purposes to update device status
    """
    try:
        device_service = DeviceService(db)
        device = await device_service.get_device_by_id(device_id)
        
        if not device:
            raise HTTPException(status_code=404, detail=f"Device with ID {device_id} not found")
            
        # Update device status
        await device_service.update_device(
            device_id=device_id,
            device_data={"status": status, "last_seen": datetime.utcnow()}
        )
        
        return {
            "success": True,
            "device_id": device_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error simulating device status update: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulate/metrics")
async def simulate_device_metrics(
    device_id: int,
    metrics: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Simulate device metrics update
    
    This endpoint is used for testing and simulation purposes to update device metrics
    """
    try:
        device_service = DeviceService(db)
        device = await device_service.get_device_by_id(device_id)
        
        if not device:
            raise HTTPException(status_code=404, detail=f"Device with ID {device_id} not found")
            
        # Update device metrics
        await device_service.update_device_metrics(
            device_id=device_id,
            metrics=metrics
        )
        
        return {
            "success": True,
            "device_id": device_id,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error simulating device metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{device_id}/sensors/latest", response_model=Dict[str, Any])
async def get_latest_device_readings(
    device_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get latest readings for each sensor type"""
    try:
        # Get distinct sensor types
        query = select(SensorReading.sensor_type).distinct().where(SensorReading.device_id == device_id)
        result = await db.execute(query)
        sensor_types = result.scalars().all()
        
        latest_readings = {}
        for sensor_type in sensor_types:
            query = (
                select(SensorReading)
                .where(
                    SensorReading.device_id == device_id,
                    SensorReading.sensor_type == sensor_type
                )
                .order_by(desc(SensorReading.timestamp))
                .limit(1)
            )
            result = await db.execute(query)
            reading = result.scalar_one_or_none()
            
            if reading:
                latest_readings[sensor_type] = reading.to_dict()
        
        return {"device_id": device_id, "readings": latest_readings}
    except Exception as e:
        logger.error(f"Error getting latest readings: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") 