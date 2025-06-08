"""
Security Management API for IoT Platform
-----------------------------------------
This module consolidates all security-related endpoints including:
- Vulnerability scanning and management
- Vulnerability remediation
- Security status reporting
- Simulated vulnerability injection for testing
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.client import Client
from app.api.deps import get_current_client, get_client_ip
from app.services.security_service import VulnerabilityService, create_vulnerability_scanner
from app.services.activity_service import ActivityService
from app.utils.vulnerability_utils import vulnerability_manager
from app.core.logging import logger

router = APIRouter()



@router.post("/vulnerability/{device_id}/scan", response_model=Dict[str, Any])
async def start_vulnerability_scan(
    device_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
    client_ip: str = Depends(get_client_ip)
) -> Dict[str, Any]:
    """
    Start a vulnerability scan for a specific device
    """
    logger.info(f"Starting vulnerability scan for device {device_id} by client {current_client.id}")
    vulnerability_service = VulnerabilityService(db)
    
    # Start the scan
    scan_result = await vulnerability_service.start_vulnerability_scan(
        device_id=device_id,
        user_id=current_client.id
    )
    
    if scan_result["status"] == "error":
        raise HTTPException(status_code=400, detail=scan_result["error"])
    
    # Add background task to simulate the scan
    scan_id = scan_result["scan_id"]
    background_tasks.add_task(
        vulnerability_service.simulate_vulnerability_scan,
        scan_id=scan_id
    )
    
    return scan_result

@router.get("/vulnerability/scan/{scan_id}", response_model=Dict[str, Any])
async def get_vulnerability_scan_results(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Get the results of a vulnerability scan
    """
    logger.info(f"Retrieving vulnerability scan results for scan {scan_id}")
    vulnerability_service = VulnerabilityService(db)
    
    # Get scan results
    results = await vulnerability_service.get_scan_results(scan_id)
    
    if results["status"] == "error":
        raise HTTPException(status_code=404, detail=results["error"])
    
    return results

@router.get("/vulnerability/device/{device_id}/history", response_model=Dict[str, Any])
async def get_device_vulnerability_history(
    device_id: str,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Get vulnerability scan history for a specific device
    """
    logger.info(f"Retrieving vulnerability scan history for device {device_id}")
    
    # This endpoint would query the database for all vulnerability scans
    # related to the specified device and return them
    # For now, we'll return a placeholder
    
    return {
        "status": "success",
        "message": "This endpoint will be implemented to show vulnerability scan history"
    }

#
# ===== VULNERABILITY REMEDIATION ENDPOINTS =====
#

@router.post("/remediation/vulnerability/{device_id}/{vulnerability_id}", response_model=Dict[str, Any])
async def remediate_vulnerability(
    device_id: str,
    vulnerability_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Simulate remediation of a specific vulnerability on a device.
    This is part of the simulated environment to demonstrate security workflow.
    """
    logger.info(f"Remediating vulnerability {vulnerability_id} on device {device_id}")
    
    # Log the remediation activity
    activity_service = ActivityService(db)
    await activity_service.log_device_state_change(
        device_id=device_id,
        action="vulnerability_remediated",
        user_id=current_client.id,
        metadata={"vulnerability_id": vulnerability_id}
    )
    
    # Perform remediation via vulnerability manager
    result = vulnerability_manager.remediate_vulnerability(device_id, vulnerability_id)
    
    # If remediation failed, raise HTTP error with reason
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Remediation failed"))
    
    # Log successful remediation / partial etc.
    await activity_service.log_device_state_change(
        device_id=device_id,
        action="vulnerability_remediation_performed",
        user_id=current_client.id,
        metadata={
            "vulnerability_id": vulnerability_id,
            "remediation_status": result.get("status"),
            "outcome": result.get("outcome")
        }
    )
    
    # Include remaining vulnerabilities count
    result["remaining_vulnerabilities"] = len(vulnerability_manager.get_device_vulnerabilities(device_id))
    return result

@router.post("/remediation/bulk", response_model=Dict[str, Any])
async def bulk_remediate_vulnerabilities(
    remediation_data: Dict[str, List[str]] = Body(..., description="Map of device_id to list of vulnerability_ids"),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Simulate bulk remediation of vulnerabilities across multiple devices.
    This is part of the simulated environment to demonstrate security workflow.
    """
    logger.info(f"Performing bulk remediation for {len(remediation_data)} devices")
    
    # Log the bulk remediation activity
    activity_service = ActivityService(db)
    total_vulns = sum(len(vuln_ids) for vuln_ids in remediation_data.values())
    await activity_service.log_activity(
        activity_type="user_action",
        action="bulk_vulnerability_remediation",
        description=f"Bulk remediation of {total_vulns} vulnerabilities across {len(remediation_data)} devices",
        user_id=current_client.id,
        metadata={
            "devices_count": len(remediation_data),
            "vulnerabilities_count": total_vulns
        }
    )
    
    # Perform the bulk remediation
    results = vulnerability_manager.bulk_remediate_vulnerabilities(remediation_data)
    
    return {
        "status": "success",
        "message": f"Completed bulk remediation of {results['vulnerabilities_fixed']} vulnerabilities across {results['total_devices']} devices",
        "results": results
    }

@router.post("/vulnerability/inject/{device_id}", response_model=Dict[str, Any])
async def inject_vulnerability(
    device_id: str,
    vulnerability: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Inject a simulated vulnerability into a device.
    This is useful for testing the security workflow.
    Requires admin privileges.
    """
    # Check if user has admin role
    if current_client.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can inject vulnerabilities"
        )
    
    logger.info(f"Injecting vulnerability into device {device_id}")
    
    # Ensure the vulnerability has required fields
    required_fields = ["id", "name", "severity", "description"]
    for field in required_fields:
        if field not in vulnerability:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field '{field}' in vulnerability data"
            )
    
    # Inject the vulnerability
    success = vulnerability_manager.inject_vulnerability(device_id, vulnerability)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to inject vulnerability"
        )
    
    # Log the activity
    activity_service = ActivityService(db)
    await activity_service.log_device_state_change(
        device_id=device_id,
        action="vulnerability_injected",
        user_id=current_client.id,
        metadata={"vulnerability_id": vulnerability["id"]}
    )
    
    return {
        "status": "success",
        "message": f"Vulnerability {vulnerability['id']} has been injected into device {device_id}",
        "device_id": device_id,
        "vulnerability": vulnerability
    }
