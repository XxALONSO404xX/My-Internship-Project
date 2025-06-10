"""Device API endpoints"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Path, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.api.deps import get_db, get_current_client
from app.api.schemas import (
    DeviceBase, DeviceCreate, DeviceUpdate, DeviceInDB, DeviceStatusResponse,
    DeviceControlResponse, SensorReadingResponse, SensorSummaryResponse
)
from app.models.client import Client
from app.models.device import Device
from app.models.sensor_reading import SensorReading
from app.services.device_management_service import DeviceService
from app.services.security_service import VulnerabilityService
from app.utils.vulnerability_utils import vulnerability_manager
from app.core.logging import logger

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
        # Use the service method to update the device
        device_service = DeviceService(db)
        update_data = device.dict(exclude_unset=True)
        updated_device = await device_service.update_device(device_id, update_data)
        
        if not updated_device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Return updated device
        return updated_device
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error updating device: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error updating device: {str(e)}\n{error_details}")

@router.delete("/{device_id}")
async def delete_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Client = Depends(get_current_client)
):
    """Delete a device"""
    try:
        # Use raw SQL to delete the device directly without loading relationships
        from sqlalchemy import text
        
        # First verify the device exists
        query = select(Device.hash_id).where(Device.hash_id == device_id)
        result = await db.execute(query)
        found_id = result.scalar_one_or_none()
        
        if not found_id:
            raise HTTPException(status_code=404, detail="Device not found")
            
        # Execute a raw SQL DELETE to bypass relationship loading
        sql = text("DELETE FROM devices WHERE hash_id = :hash_id")
        await db.execute(sql, {"hash_id": device_id})
        await db.commit()
        
        # Skip activity logging for now
        
        return {"status": "success", "message": "Device deleted"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error deleting device: {error_details}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting device: {str(e)}\n{error_details}")

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
            user_ip=current_user.email  # Use email instead of non-existent last_ip
        )
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Control failed")
            )
            
        # Format the response to match DeviceControlResponse schema
        formatted_response = {
            "device_id": device_id,
            "action": action,
            "success": result.get("success", False),
            "message": result.get("message", f"Successfully executed {action} on device"),
            "timestamp": datetime.utcnow(),
            "result": {
                "state": result.get("state", {}),
                **{k: v for k, v in result.items() if k not in ["success", "message", "state", "error"]}
            }
        }
        
        return formatted_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error controlling device: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{device_id}/status", response_model=DeviceStatusResponse)
async def get_device_status(device_id: str, db: AsyncSession = Depends(get_db), current_user: Client = Depends(get_current_client)):
    """Get device status (virtual simulation)"""
    try:
        # First, explicitly verify device exists to avoid confusing errors
        query = select(Device).where(Device.hash_id == device_id)
        result = await db.execute(query)
        device = result.scalars().first()
        
        if not device:
            logger.warning(f"Device with ID {device_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"detail": "Device not found"}
            )
            
        # Now get the status
        device_service = DeviceService(db)
        device_status = await device_service.get_device_status(device_id)
        return device_status
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
            user_ip=current_user.email  # Use email instead of non-existent last_ip
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
            user_ip=current_user.email  # Use email instead of non-existent last_ip
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
    device_id: str,
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
    device_id: str,
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
    device_id: str,
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
    device_id: str,
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
    device_id: str,
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

# Vulnerability Management Endpoints
@router.post("/{device_id}/vulnerability/scan", response_model=Dict[str, Any])
async def scan_device_vulnerabilities(
    device_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Scan a device for vulnerabilities
    
    This endpoint initiates a vulnerability scan for the specified device and returns a scan ID
    that can be used to retrieve the results.
    """
    logger.info(f"Starting vulnerability scan for device {device_id} by client {current_client.id}")
    
    # Get the device to ensure it exists
    device_service = DeviceService(db)
    device = await device_service.get_device_by_id(device_id)
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID {device_id} not found"
        )
    
    # Initialize vulnerability service
    vulnerability_service = VulnerabilityService(db)
    
    # Start the scan
    scan_result = await vulnerability_service.start_vulnerability_scan(
        device_id=device_id,
        user_id=current_client.id
    )
    
    if scan_result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=scan_result.get("error", "Unknown error during scan initialization")
        )
    
    # Add background task to simulate the scan
    scan_id = scan_result["scan_id"]
    background_tasks.add_task(
        vulnerability_service.simulate_vulnerability_scan,
        scan_id=scan_id
    )
    
    return scan_result

@router.get("/{device_id}/vulnerability/scan/{scan_id}", response_model=Dict[str, Any])
async def get_device_scan_results(
    device_id: str,
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Get the results of a vulnerability scan for a device
    """
    logger.info(f"Retrieving vulnerability scan results for device {device_id}, scan {scan_id}")
    
    # Get the device to ensure it exists
    device_service = DeviceService(db)
    device = await device_service.get_device_by_id(device_id)
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID {device_id} not found"
        )
    
    # Initialize vulnerability service
    vulnerability_service = VulnerabilityService(db)
    
    # Get scan results
    results = await vulnerability_service.get_scan_results(scan_id)
    
    if results.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=results.get("error", "Scan not found or results unavailable")
        )
    
    return results

@router.post("/{device_id}/vulnerability/{vulnerability_id}/remediate", response_model=Dict[str, Any])
async def remediate_device_vulnerability(
    device_id: str,
    vulnerability_id: str,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Remediate a specific vulnerability on a device
    """
    logger.info(f"Remediating vulnerability {vulnerability_id} on device {device_id}")
    
    # Get the device to ensure it exists
    device_service = DeviceService(db)
    device = await device_service.get_device_by_id(device_id)
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID {device_id} not found"
        )
    
    # Call the vulnerability manager to remediate with enhanced outcomes
    remediation_result = vulnerability_manager.remediate_vulnerability(device_id, vulnerability_id)
    
    # Handle different remediation outcomes
    if remediation_result["status"] == "error" and remediation_result.get("outcome") != "failed_fix":
        # This is a true error (vulnerability not found or system error)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=remediation_result["message"]
        )
    
    # For all other outcomes (success, partial, temporary, or even failed_fix), 
    # return the detailed result to the client
    # This allows the client to handle different remediation scenarios
    return remediation_result

@router.get("/{device_id}/vulnerabilities", response_model=Dict[str, Any])
async def get_device_vulnerabilities(
    device_id: str,
    include_risk_score: bool = Query(True, description="Include risk scoring information"),
    prioritize: bool = Query(False, description="Return vulnerabilities in priority order with remediation timeframes"),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Get current known vulnerabilities for a device without needing a new scan
    
    - **include_risk_score**: Whether to include risk scoring information
    - **prioritize**: Return vulnerabilities in priority order with remediation timeframes
    """
    logger.info(f"Getting current vulnerabilities for device {device_id}")
    
    # Get the device to ensure it exists
    device_service = DeviceService(db)
    device = await device_service.get_device_by_id(device_id)
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID {device_id} not found"
        )
    
    # Get current vulnerabilities from the vulnerability manager
    vulnerabilities = vulnerability_manager.get_device_vulnerabilities(device_id)
    
    # Import only when needed to avoid circular imports
    if include_risk_score or prioritize:
        from app.utils.risk_scoring import risk_scorer
    
    result = {
        "status": "success",
        "device_id": device_id,
        "count": len(vulnerabilities)
    }
    
    # Add risk scoring if requested
    if include_risk_score:
        risk_data = risk_scorer.calculate_device_risk_score(device, vulnerabilities)
        result["risk_score"] = risk_data["total_score"]
        result["risk_level"] = risk_data["risk_level"]
        
        # Include detailed risk data
        result["risk_details"] = {
            "component_scores": risk_data["component_scores"],
            "vulnerability_scores": risk_data["vulnerability_scores"]
        }
    
    # Prioritize vulnerabilities if requested
    if prioritize and vulnerabilities:
        result["vulnerabilities"] = risk_scorer.prioritize_vulnerabilities(device, vulnerabilities)
    else:
        result["vulnerabilities"] = vulnerabilities
    
    return result

@router.get("/{device_id}/sensors/latest", response_model=Dict[str, Any])
async def get_latest_device_readings(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get latest readings for each sensor type"""
    try:
        device_service = DeviceService(db)
        readings = await device_service.get_latest_device_readings(device_id)
        return readings
    except Exception as e:
        logger.error(f"Error getting latest readings: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") 