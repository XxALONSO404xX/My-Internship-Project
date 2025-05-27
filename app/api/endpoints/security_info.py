"""Security information API endpoints for IoT platform"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import random

from app.models.database import get_db
from app.models.device import Device
from app.services.device_service import DeviceService
from app.api import schemas
from app.api.deps import get_current_client

router = APIRouter()

@router.get("/devices/{device_id}/tls", response_model=Dict[str, Any])
async def get_device_tls_info(
    device_id: str = Path(..., description="Device hash ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get TLS/SSL security information for a specific device"""
    device_service = DeviceService(db)
    
    # Verify device exists
    device = await device_service.get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Compile TLS security information
    return {
        "device_id": device.hash_id,
        "device_name": device.name,
        "supports_tls": device.supports_tls,
        "tls_version": device.tls_version,
        "cert_expiry": device.cert_expiry,
        "cert_issued_by": device.cert_issued_by,
        "cert_strength": device.cert_strength,
        "cert_status": "expired" if (device.cert_expiry and device.cert_expiry < datetime.utcnow()) 
                       else "valid" if device.cert_expiry else "unknown",
        "security_rating": calculate_security_rating(device),
        "last_firmware_check": device.last_firmware_check,
        "firmware_auto_update": device.firmware_auto_update
    }

@router.get("/devices/{device_id}/update-history/secure", response_model=List[Dict[str, Any]])
async def get_device_secure_updates(
    device_id: str = Path(..., description="Device hash ID"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get firmware update security history for a device"""
    device_service = DeviceService(db)
    
    # Verify device exists
    device = await device_service.get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get updates with security information
    query = """
    SELECT 
        fu.id, fu.status, fu.started_at, fu.completed_at, 
        fu.secure_channel, fu.encryption_method, fu.signature_verified,
        f.version as firmware_version, f.name as firmware_name
    FROM firmware_updates fu
    JOIN firmware f ON fu.firmware_id = f.id
    WHERE fu.device_id = :device_id
    ORDER BY fu.created_at DESC
    LIMIT :limit
    """
    
    result = await db.execute(query, {"device_id": device_id, "limit": limit})
    rows = result.mappings().all()
    
    # Format the results
    return [dict(row) for row in rows]

@router.put("/devices/{device_id}/tls", response_model=Dict[str, Any])
async def update_device_tls_info(
    device_id: str = Path(..., description="Device hash ID"),
    supports_tls: Optional[bool] = Query(None, description="Whether device supports TLS"),
    tls_version: Optional[str] = Query(None, description="TLS version (TLS 1.2 or TLS 1.3)"),
    renew_cert: bool = Query(False, description="Whether to renew the device certificate"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_client)
):
    """Update TLS/SSL security information for a device (simulated)"""
    device_service = DeviceService(db)
    
    # Verify device exists
    device = await device_service.get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Update device TLS information
    updates = {}
    
    if supports_tls is not None:
        updates["supports_tls"] = supports_tls
    
    if tls_version is not None:
        if tls_version not in ["TLS 1.2", "TLS 1.3"]:
            raise HTTPException(status_code=400, detail="TLS version must be 'TLS 1.2' or 'TLS 1.3'")
        updates["tls_version"] = tls_version
    
    if renew_cert:
        # Simulate certificate renewal with a future expiry date (1-2 years)
        days = random.randint(365, 730)
        updates["cert_expiry"] = datetime.utcnow() + timedelta(days=days)
        
        # Simulate new certificate strength based on TLS version
        if tls_version == "TLS 1.3" or (tls_version is None and device.tls_version == "TLS 1.3"):
            updates["cert_strength"] = random.choice([3072, 4096])
        else:
            updates["cert_strength"] = random.choice([2048, 3072])
            
        # Set a certificate issuer
        issuers = [
            'IoT Security Authority', 
            'Global Device Trust', 
            'SecureThings CA',
            'IoT Platform Internal CA',
            'Trusted Device Authority'
        ]
        updates["cert_issued_by"] = random.choice(issuers)
    
    # Update the device if there are changes
    if updates:
        for key, value in updates.items():
            setattr(device, key, value)
        
        await db.commit()
        await db.refresh(device)
    
    # Return updated information
    return {
        "device_id": device.hash_id,
        "device_name": device.name,
        "supports_tls": device.supports_tls,
        "tls_version": device.tls_version,
        "cert_expiry": device.cert_expiry,
        "cert_issued_by": device.cert_issued_by,
        "cert_strength": device.cert_strength,
        "cert_status": "expired" if (device.cert_expiry and device.cert_expiry < datetime.utcnow()) 
                       else "valid" if device.cert_expiry else "unknown",
        "security_rating": calculate_security_rating(device),
        "updates": list(updates.keys())
    }

def calculate_security_rating(device: Device) -> int:
    """Calculate a security rating for the device based on TLS settings (1-10 scale)"""
    if not device.supports_tls:
        return 1  # No TLS = very poor rating
    
    base_score = 5  # Start with a moderate score
    
    # TLS version adds points
    if device.tls_version == "TLS 1.3":
        base_score += 2
    elif device.tls_version == "TLS 1.2":
        base_score += 1
    
    # Valid certificate adds points
    if device.cert_expiry and device.cert_expiry > datetime.utcnow():
        base_score += 1
    
    # Certificate strength adds points
    if device.cert_strength:
        if device.cert_strength >= 4096:
            base_score += 2
        elif device.cert_strength >= 3072:
            base_score += 1.5
        elif device.cert_strength >= 2048:
            base_score += 1
    
    # Cap the score at 10
    return min(10, base_score)
