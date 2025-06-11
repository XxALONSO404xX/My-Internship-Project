"""
Firmware Management API for IoT Platform
-----------------------------------------
This module consolidates all firmware-related endpoints including:
- Firmware CRUD operations (create, read, update, delete)
- Firmware status checking and reporting
- Firmware update operations
- Vulnerability remediation through firmware updates
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.device import Device
from app.models.firmware import Firmware
from app.services.device_management_service import DeviceService
from app.services.firmware_service import FirmwareService
from app.services.security_service import VulnerabilityService
from app.utils.vulnerability_utils import vulnerability_manager
from app.api import schemas
from app.api.deps import get_current_client
from app.utils.notification_helper import NotificationHelper
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

#
# ===== FIRMWARE MANAGEMENT ENDPOINTS =====
#

@router.get("/", response_model=List[Dict[str, Any]])
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
    
    return [fw.to_dict() for fw in firmware_list]

@router.post("/", response_model=Dict[str, Any], status_code=201)
async def create_firmware(
    firmware: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_client: Dict[str, Any] = Depends(get_current_client)
):
    """Create new firmware
    
    Required fields:
    - version: Firmware version string
    - name: Firmware name
    - device_type: Type of device this firmware is for
    
    Optional fields:
    - is_critical: Whether this is a critical update (default: false)
    """
    firmware_service = FirmwareService(db)
    
    try:
        new_firmware = await firmware_service.create_firmware(
            version=firmware.get("version"),
            name=firmware.get("name"),
            device_type=firmware.get("device_type"),
            is_critical=firmware.get("is_critical", False)
        )
        
        return new_firmware.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{firmware_id}", response_model=Dict[str, Any])
async def get_firmware(
    firmware_id: str = Path(..., description="Firmware ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get specific firmware by ID"""
    firmware_service = FirmwareService(db)
    firmware = await firmware_service.get_firmware_by_id(firmware_id)
    
    if not firmware:
        raise HTTPException(status_code=404, detail="Firmware not found")
    
    return firmware.to_dict()

@router.get("/device/{device_id}/compatible", response_model=List[Dict[str, Any]])
async def get_device_compatible_firmware(
    device_id: str = Path(..., description="Device hash ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get compatible firmware for a specific device"""
    device_service = DeviceService(db)
    
    # Verify device exists
    device = await device_service.get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get firmware for the device type via ORM
    stmt = select(Firmware).where(Firmware.device_type == device.device_type)
    result = await db.execute(stmt)
    firmware_list = result.scalars().all()

    # Auto-seed firmware on-the-fly if none exist for this device type
    if not firmware_list:
        logger.warning(f"No firmware found for device_type {device.device_type}. Seeding baseline/critical automatically.")
        fw_service = FirmwareService(db)
        baseline = await fw_service.create_firmware(
            version="1.0.0",
            name=f"{device.device_type} Firmware v1.0.0",
            device_type=device.device_type
        )
        critical = await fw_service.create_firmware(
            version="1.1.0",
            name=f"{device.device_type} Firmware v1.1.0",
            device_type=device.device_type,
            is_critical=True
        )
        firmware_list = [baseline, critical]
    
    compatible = [fw for fw in firmware_list if fw.version != device.firmware_version]

    return [
        {
            "id": fw.id,
            "version": fw.version,
            "name": fw.name,
            "device_type": fw.device_type,
            "release_date": fw.release_date.isoformat() if fw.release_date else None,
            "is_critical": fw.is_critical,
            "is_compatible": True
        } for fw in compatible
    ]

@router.post("/update", response_model=Dict[str, Any])
async def start_firmware_update(
    update_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Start firmware update for a device
    
    Required fields:
    - device_id: ID of the device to update
    - firmware_version: Target firmware version
    
    Optional fields:
    - force_update: Whether to force update even if current version is same/newer (default: false)
    """
    device_id = update_data.get("device_id")
    firmware_version = update_data.get("firmware_version")
    force_update = update_data.get("force_update", False)
    
    if not device_id or not firmware_version:
        raise HTTPException(status_code=400, detail="device_id and firmware_version are required")
    
    # Check if device exists
    device_service = DeviceService(db)
    device = await device_service.get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Start firmware update (simplified)
    firmware_service = FirmwareService(db)
    update_id = await firmware_service.start_firmware_update(
        device_id=device_id,
        target_version=firmware_version,
        force_update=force_update
    )
    
    # Create notification for firmware update
    notification_helper = NotificationHelper(db)
    if hasattr(notification_helper, "create_firmware_update_notification"):
        background_tasks.add_task(
            notification_helper.create_firmware_update_notification,
            update_id,
            device_id,
            firmware_version,
        )
    
    return {
        "status": "started",
        "update_id": update_id,
        "device_id": device_id,
        "target_version": firmware_version
    }

@router.get("/update/{update_id}", response_model=Dict[str, Any])
async def get_update_status(
    update_id: str = Path(..., description="Update ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get firmware update status"""
    firmware_service = FirmwareService(db)
    status = await firmware_service.get_update_status(update_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Update not found")
    
    return status

#
# ===== FIRMWARE STATUS ENDPOINTS =====
#

@router.get("/status/device/{device_id}")
async def check_device_firmware_status(
    device_id: str,
    include_vulnerabilities: bool = Query(True, description="Include vulnerability information"),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if a specific device's firmware is up to date
    
    Returns firmware status information and update recommendations
    Also checks for vulnerabilities that could be fixed by firmware update
    """
    # Get device info
    device_service = DeviceService(db)
    device = await device_service.get_device_by_id(device_id)
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get latest firmware for device type
    firmware_service = FirmwareService(db)
    latest_firmware = await firmware_service.get_latest_firmware_for_device_type(device.device_type)
    
    if not latest_firmware:
        return {
            "status": "no_firmware",
            "message": f"No firmware found for device type {device.device_type}",
            "device": device.to_dict()
        }
    
    # Compare versions - simplified for demo
    current_version = device.firmware_version or "0.0.0"
    latest_version = latest_firmware.version
    
    # Basic version comparison (in production, would use proper semver)
    needs_update = current_version != latest_version
    
    result = {
        "device": device.to_dict(),
        "current_firmware": {
            "version": current_version,
            "last_updated": device.firmware_update_date.isoformat() if device.firmware_update_date else None
        },
        "latest_firmware": {
            "version": latest_version,
            "release_date": latest_firmware.release_date.isoformat() if latest_firmware.release_date else None,
            "is_critical": latest_firmware.is_critical
        },
        "status": "needs_update" if needs_update else "up_to_date",
        "update_recommended": needs_update
    }
    
    # Include vulnerability information if requested
    if include_vulnerabilities:
        # Get device vulnerabilities
        vulnerabilities = vulnerability_manager.get_device_vulnerabilities(device_id)
        
        # Get vulnerabilities that would be fixed by a firmware update
        fixable_vulnerabilities = []
        if vulnerabilities and needs_update:
            for vuln in vulnerabilities:
                # Simplified logic - in a real system, would check if specific vulnerability
                # is addressed by this firmware version
                if vuln.get("fix_available") == "firmware_update":
                    fixable_vulnerabilities.append(vuln)
        
        result["vulnerabilities"] = {
            "total_count": len(vulnerabilities) if vulnerabilities else 0,
            "fixable_by_update": len(fixable_vulnerabilities),
            "fixable_vulnerabilities": fixable_vulnerabilities
        }
    
    return result

@router.get("/status/all")
async def check_all_devices_firmware_status(
    device_type: str = Query(None, description="Filter by device type"),
    status: str = Query(None, description="Filter by status (needs_update, up_to_date, all)"),
    include_vulnerabilities: bool = Query(True, description="Include vulnerability information"),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """
    Check firmware status for all devices
    
    Returns a summary of devices that need updates and those that are up to date
    """
    # Get all devices
    query = select(Device)
    
    # Apply device type filter if provided
    if device_type:
        query = query.where(Device.device_type == device_type)
    
    result = await db.execute(query)
    devices = result.scalars().all()
    
    if not devices:
        return {
            "status": "no_devices",
            "message": "No devices found with the specified criteria",
            "devices": []
        }
    
    firmware_service = FirmwareService(db)
    
    # Get latest firmware versions for each device type
    device_types = set(d.device_type for d in devices)
    latest_firmware_by_type = {}
    
    for dt in device_types:
        latest = await firmware_service.get_latest_firmware_for_device_type(dt)
        if latest:
            latest_firmware_by_type[dt] = latest
    
    # Process each device
    devices_data = []
    needs_update_count = 0
    up_to_date_count = 0
    
    for device in devices:
        # Skip if no firmware exists for this device type
        if device.device_type not in latest_firmware_by_type:
            continue
        
        latest_firmware = latest_firmware_by_type[device.device_type]
        current_version = device.firmware_version or "0.0.0"
        latest_version = latest_firmware.version
        
        # Basic version comparison
        needs_update = current_version != latest_version
        
        if needs_update:
            needs_update_count += 1
        else:
            up_to_date_count += 1
        
        # Skip if filtered by status
        if status == "needs_update" and not needs_update:
            continue
        if status == "up_to_date" and needs_update:
            continue
        
        device_data = {
            "device": {
                "id": device.hash_id,
                "name": device.name,
                "device_type": device.device_type
            },
            "current_firmware": {
                "version": current_version,
                "last_updated": device.firmware_update_date.isoformat() if device.firmware_update_date else None
            },
            "latest_firmware": {
                "version": latest_version,
                "release_date": latest_firmware.release_date.isoformat() if latest_firmware.release_date else None,
                "is_critical": latest_firmware.is_critical
            },
            "status": "needs_update" if needs_update else "up_to_date",
            "update_recommended": needs_update
        }
        
        # Include vulnerability information if requested
        if include_vulnerabilities:
            vulnerabilities = vulnerability_manager.get_device_vulnerabilities(device.hash_id)
            
            # Get vulnerabilities that would be fixed by a firmware update
            fixable_vulnerabilities = []
            if vulnerabilities and needs_update:
                for vuln in vulnerabilities:
                    if vuln.get("fix_available") == "firmware_update":
                        fixable_vulnerabilities.append(vuln)
            
            device_data["vulnerabilities"] = {
                "total_count": len(vulnerabilities) if vulnerabilities else 0,
                "fixable_by_update": len(fixable_vulnerabilities)
            }
        
        devices_data.append(device_data)
        
        # Respect the limit
        if len(devices_data) >= limit:
            break
    
    return {
        "summary": {
            "total_devices": len(devices),
            "needs_update": needs_update_count,
            "up_to_date": up_to_date_count,
            "update_percentage": round(needs_update_count / len(devices) * 100, 1) if devices else 0
        },
        "devices": devices_data
    }

@router.get("/status/summary")
async def get_firmware_status_summary(
    include_vulnerabilities: bool = Query(True, description="Include vulnerability metrics"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a summary of firmware status across all devices
    
    Returns counts and percentages of devices needing updates
    """
    # Get device counts by type
    query = select(Device.device_type, func.count().label("count")).group_by(Device.device_type)
    result = await db.execute(query)
    device_counts = {row[0]: row[1] for row in result}
    
    # If no devices, return empty summary
    if not device_counts:
        return {
            "status": "no_devices",
            "message": "No devices found in system",
            "summary": {
                "total_devices": 0,
                "needs_update": 0,
                "up_to_date": 0,
                "update_percentage": 0
            }
        }
    
    # Get latest firmware for each device type
    firmware_service = FirmwareService(db)
    
    latest_firmware = {}
    for device_type in device_counts.keys():
        latest = await firmware_service.get_latest_firmware_for_device_type(device_type)
        if latest:
            latest_firmware[device_type] = latest.version
    
    # Count devices needing updates
    needs_update_count = 0
    critical_updates_count = 0
    
    # Get all devices
    query = select(Device)
    result = await db.execute(query)
    devices = result.scalars().all()
    
    for device in devices:
        if device.device_type not in latest_firmware:
            continue
            
        latest_version = latest_firmware[device.device_type]
        current_version = device.firmware_version or "0.0.0"
        
        if current_version != latest_version:
            needs_update_count += 1
            
            # Check if update is critical
            latest_fw = await firmware_service.get_latest_firmware_for_device_type(device.device_type)
            if latest_fw and latest_fw.is_critical:
                critical_updates_count += 1
    
    total_devices = len(devices)
    up_to_date_count = total_devices - needs_update_count
    
    # Prepare summary
    summary = {
        "total_devices": total_devices,
        "needs_update": needs_update_count,
        "up_to_date": up_to_date_count,
        "critical_updates": critical_updates_count,
        "update_percentage": round(needs_update_count / total_devices * 100, 1) if total_devices else 0,
        "by_device_type": {
            dt: {
                "total": count,
                "latest_firmware": latest_firmware.get(dt, "unknown")
            } for dt, count in device_counts.items()
        }
    }
    
    # Include vulnerability information if requested
    if include_vulnerabilities:
        # Count vulnerabilities fixable by firmware update
        fixable_vulnerabilities = 0
        vulnerability_service = VulnerabilityService(db)
        
        for device in devices:
            vulnerabilities = vulnerability_manager.get_device_vulnerabilities(device.hash_id)
            if not vulnerabilities:
                continue
                
            for vuln in vulnerabilities:
                if vuln.get("fix_available") == "firmware_update":
                    fixable_vulnerabilities += 1
        
        summary["vulnerability_metrics"] = {
            "fixable_by_firmware": fixable_vulnerabilities
        }
    
    return {
        "status": "success",
        "summary": summary,
        "timestamp": str(func.now())
    }

@router.get("/vulnerability-remediation")
async def get_firmware_vulnerability_remediation(
    db: AsyncSession = Depends(get_db),
    current_client = Depends(get_current_client)
):
    """
    Get mapping between firmware updates and vulnerability remediation
    
    Shows which vulnerabilities can be fixed by firmware updates and provides
    remediation recommendations for device fleet
    """
    # Get all devices
    query = select(Device)
    result = await db.execute(query)
    devices = result.scalars().all()
    
    if not devices:
        return {
            "status": "no_devices",
            "message": "No devices found in system",
            "remediation_plan": []
        }
    
    # Process each device
    remediation_plan = []
    
    for device in devices:
        # Get device vulnerabilities
        vulnerabilities = vulnerability_manager.get_device_vulnerabilities(device.hash_id)
        
        # Skip if no vulnerabilities
        if not vulnerabilities:
            continue
            
        # Check for firmware-fixable vulnerabilities
        firmware_fixable = [v for v in vulnerabilities if v.get("fix_available") == "firmware_update"]
        
        # Skip if no firmware-fixable vulnerabilities
        if not firmware_fixable:
            continue
            
        # Get latest firmware
        firmware_service = FirmwareService(db)
        latest_firmware = await firmware_service.get_latest_firmware_for_device_type(device.device_type)
        
        if not latest_firmware:
            continue
            
        # Check if device needs update
        current_version = device.firmware_version or "0.0.0"
        needs_update = current_version != latest_firmware.version
        
        # Skip if already up to date
        if not needs_update:
            continue
            
        # Add to remediation plan
        device_plan = {
            "device": {
                "id": device.hash_id,
                "name": device.name,
                "device_type": device.device_type,
                "current_firmware": current_version
            },
            "firmware_update": {
                "version": latest_firmware.version,
                "is_critical": latest_firmware.is_critical
            },
            "fixable_vulnerabilities": [
                {
                    "id": v.get("id"),
                    "title": v.get("title"),
                    "severity": v.get("severity")
                } for v in firmware_fixable
            ],
            "recommendation": "Update firmware to fix vulnerabilities"
        }
        
        remediation_plan.append(device_plan)
    
    # Sort by number of vulnerabilities (descending)
    remediation_plan.sort(key=lambda x: len(x["fixable_vulnerabilities"]), reverse=True)
    
    return {
        "status": "success",
        "total_devices_with_fixable_vulnerabilities": len(remediation_plan),
        "remediation_plan": remediation_plan
    }
