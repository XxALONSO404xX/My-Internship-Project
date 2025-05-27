"""Group Security API endpoints for IoT platform"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Any, Optional

from app.api.schemas import ResponseModel
from app.models.database import get_db
from app.services.group_vulnerability_service import create_group_vulnerability_service, GroupVulnerabilityService
from app.api.deps import get_current_client

router = APIRouter()

async def get_group_vulnerability_service(db_session: AsyncSession = Depends(get_db)):
    """Get a group vulnerability service instance with DB session"""
    return create_group_vulnerability_service(db_session)

@router.post("/groups/{group_id}/scan", response_model=ResponseModel)
async def start_group_vulnerability_scan(
    group_id: int = Path(..., gt=0, description="ID of the group to scan"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    service: GroupVulnerabilityService = Depends(get_group_vulnerability_service),
    current_user = Depends(get_current_client)
):
    """
    Start a vulnerability scan on all devices in a group.
    
    This is an asynchronous operation. The response includes a scan_id
    that can be used to check scan status and retrieve results.
    """
    # Start the group scan
    result = await service.scan_group(group_id)
    
    if result.get("status") == "failed":
        raise HTTPException(status_code=404, detail=result.get("message"))
    
    return {
        "status": "success",
        "data": result,
        "message": f"Group vulnerability scan started for {result.get('group_name', f'group {group_id}')}"
    }

@router.get("/groups/{group_id}/vulnerabilities", response_model=ResponseModel)
async def get_group_vulnerability_stats(
    group_id: int = Path(..., gt=0, description="ID of the group"),
    service: GroupVulnerabilityService = Depends(get_group_vulnerability_service),
    current_user = Depends(get_current_client)
):
    """
    Get vulnerability statistics for a group of devices.
    
    Returns aggregated vulnerability information for all devices in the group.
    """
    result = await service.get_group_vulnerability_stats(group_id)
    
    if result.get("status") == "failed":
        raise HTTPException(status_code=404, detail=result.get("message"))
    
    return {
        "status": "success",
        "data": result,
        "message": f"Vulnerability statistics for group {result.get('group_name', f'group {group_id}')}"
    }

@router.get("/groups/vulnerability-dashboard", response_model=ResponseModel)
async def get_group_vulnerability_dashboard(
    limit: int = Query(10, ge=1, le=100, description="Number of highest risk groups to return"),
    service: GroupVulnerabilityService = Depends(get_group_vulnerability_service),
    current_user = Depends(get_current_client)
):
    """
    Get vulnerability dashboard data organized by groups.
    
    Returns an overview of vulnerability statistics for all groups,
    sorted by risk score (highest risk first).
    """
    # This would be implemented to fetch vulnerability data for all groups
    # For now, returning a placeholder
    return {
        "status": "success",
        "data": {
            "groups_with_vulnerabilities": 3,
            "total_groups": 10,
            "highest_risk_groups": [
                {
                    "group_id": 1,
                    "group_name": "Living Room",
                    "risk_score": 8.5,
                    "vulnerability_count": 12
                },
                {
                    "group_id": 3,
                    "group_name": "Security Cameras",
                    "risk_score": 7.2,
                    "vulnerability_count": 8
                }
            ],
            "vulnerability_distribution": {
                "critical": 5,
                "high": 15,
                "medium": 23,
                "low": 42
            }
        },
        "message": "Group vulnerability dashboard data"
    }
