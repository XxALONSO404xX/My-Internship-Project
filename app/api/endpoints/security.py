from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.api.schemas import ResponseModel
from app.models.database import get_db
from app.services.vulnerability_scanner import create_vulnerability_scanner, VulnerabilityScanner
from app.services.device_service import DeviceService
from app.api.deps import get_current_client

router = APIRouter()

async def get_vulnerability_scanner(db_session: AsyncSession = Depends(get_db)):
    """Get a vulnerability scanner instance with DB session"""
    return create_vulnerability_scanner(db_session)

@router.post("/vulnerabilities/scan", response_model=ResponseModel)
async def start_vulnerability_scan(
    background_tasks: BackgroundTasks,
    scanner: VulnerabilityScanner = Depends(get_vulnerability_scanner)
):
    """
    Start a full vulnerability scan on all devices.
    
    This is an asynchronous operation. The response includes a scan_id
    that can be used to check scan status and retrieve results.
    """
    # Start the scan
    result = await scanner.scan_multiple_devices([])
    
    return ResponseModel(
        data=result,
        message="Vulnerability scan started"
    )

@router.post("/vulnerabilities/scan/{device_id}", response_model=ResponseModel)
async def start_device_vulnerability_scan(
    device_id: int,
    background_tasks: BackgroundTasks,
    scanner: VulnerabilityScanner = Depends(get_vulnerability_scanner)
):
    """
    Start a vulnerability scan on a specific device.
    
    This is an asynchronous operation. The response includes a scan_id
    that can be used to check scan status and retrieve results.
    """
    # Start the scan for the specific device
    result = await scanner.scan_device(device_id)
    
    return ResponseModel(
        data=result,
        message=f"Vulnerability scan started for device {device_id}"
    )

@router.get("/vulnerabilities/status/{scan_id}", response_model=ResponseModel)
async def get_vulnerability_scan_status(
    scan_id: str,
    scanner: VulnerabilityScanner = Depends(get_vulnerability_scanner)
):
    """
    Check the status of a vulnerability scan.
    
    Returns the current status and, if completed, the results of the scan.
    """
    # Get scan results
    result = await scanner.get_scan_results(scan_id)
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found"
        )
    
    return ResponseModel(
        data=result,
        message=f"Vulnerability scan status for {scan_id}"
    )

@router.post("/vulnerabilities/cancel/{scan_id}", response_model=ResponseModel)
async def cancel_vulnerability_scan(
    scan_id: str,
    scanner: VulnerabilityScanner = Depends(get_vulnerability_scanner)
):
    """
    Cancel an ongoing vulnerability scan.
    """
    # Clean up resources
    await scanner.cleanup()
    
    return ResponseModel(
        data={"scan_id": scan_id, "status": "cancelled"},
        message=f"Vulnerability scan {scan_id} has been cancelled"
    )

@router.get("/vulnerabilities/{device_id}")
async def scan_device_vulnerabilities(
    device_id: int = Path(..., description="ID of the device to scan"),
    scanner = Depends(get_vulnerability_scanner),
    current_user = Depends(get_current_client)
):
    """
    Scan a device for vulnerabilities
    """
    result = await scanner.scan_device(device_id)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "Device not found"))
        
    return result

@router.post("/vulnerabilities/batch")
async def scan_multiple_devices(
    device_ids: List[int],
    scanner = Depends(get_vulnerability_scanner),
    current_user = Depends(get_current_client)
):
    """
    Scan multiple devices for vulnerabilities
    """
    if not device_ids:
        raise HTTPException(status_code=400, detail="No device IDs provided")
        
    result = await scanner.scan_multiple_devices(device_ids)
    return result

@router.get("/vulnerabilities/results/{scan_id}")
async def get_vulnerability_scan_results(
    scan_id: str = Path(..., description="ID of the vulnerability scan"),
    scanner = Depends(get_vulnerability_scanner),
    current_user = Depends(get_current_client)
):
    """
    Get results of a vulnerability scan
    """
    results = await scanner.get_scan_results(scan_id)
    
    if not results:
        raise HTTPException(status_code=404, detail="Scan results not found")
        
    return results

@router.get("/vulnerabilities/dashboard")
async def get_vulnerability_dashboard(
    limit: int = Query(10, description="Number of results to return"),
    device_service: DeviceService = Depends(lambda db: DeviceService(db)),
    scanner = Depends(get_vulnerability_scanner),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """
    Get vulnerability dashboard data
    """
    # Get devices
    devices = await device_service.get_all_devices()
    device_ids = [d.id for d in devices[:limit]]
    
    # Run scan
    if device_ids:
        result = await scanner.scan_multiple_devices(device_ids)
        return result
    else:
        return {"message": "No devices found"} 
