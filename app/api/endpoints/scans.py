"""Scan API endpoints for IoT Platform"""
import logging
import uuid
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.models.scan import Scan
from app.models.device import Device
from app.models.client import Client
from app.services.device_scanner import create_device_scanner
from app.services.vulnerability_scanner import create_vulnerability_scanner
from app.api.deps import get_db, get_current_client
from app.core.logging import logger
from sqlalchemy.exc import SQLAlchemyError
from app.api.schemas import (
    ScanRequest,
    ScanResponse, 
    ScanListResponse, 
    ScanStatusResponse,
    ScanResultsResponse,
    PaginationParams
)

router = APIRouter()

@router.post("/", response_model=ScanResponse)
async def create_scan(
    scan_request: ScanRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Client = Depends(get_current_client)
):
    """Create a new scan of specified type
    
    Types available:
    - discovery: Find devices on the network
    - vulnerability: Check devices for security vulnerabilities
    """
    # Validate input parameters
    if scan_request.scan_type not in ["discovery", "vulnerability"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scan type. Must be 'discovery' or 'vulnerability'"
        )
    
    # Type-specific validation
    if scan_request.scan_type == "discovery" and not scan_request.network_range:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Network range is required for discovery scans"
        )
    
    if scan_request.scan_type == "vulnerability" and not scan_request.device_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device IDs are required for vulnerability scans"
        )
    
    # Validate network range format for discovery scans
    if scan_request.scan_type == "discovery" and scan_request.network_range:
        scanner = create_device_scanner(db)
        if not scanner._validate_network_range(scan_request.network_range):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid network range format or not allowed. Use format like '192.168.1.0/24'"
            )
    
    try:
        # Create a scan ID and record upfront
        scan_id = str(uuid.uuid4())
        
        # Create a scan record with pending status
        scan = Scan(
            id=scan_id,
            status="pending",
            scan_type=scan_request.scan_type,
            start_time=datetime.utcnow(),
            network_range=scan_request.network_range if scan_request.scan_type == "discovery" else None
        )
        db.add(scan)
        await db.commit()
        
        # Log scan start activity
        logger.info(
            f"User {current_user.username} started {scan_request.scan_type} scan {scan_id}"
            + (f" for network {scan_request.network_range}" if scan_request.network_range else "")
            + (f" for devices {scan_request.device_ids}" if scan_request.device_ids else "")
        )
        
        # Schedule the actual scan as a background task
        async def run_scan_task():
            try:
                # Create appropriate scanner based on scan type
                if scan_request.scan_type == "discovery":
                    scanner = create_device_scanner(db)
                    await scanner._run_scan(scan_id, "discovery", scan_request.network_range)
                else:  # vulnerability scan
                    scanner = create_vulnerability_scanner(db)
                    await scanner.start_vulnerability_scan(scan_request.device_ids, scan_id=scan_id)
            except Exception as e:
                logger.error(f"Background scan task failed: {str(e)}", exc_info=True)
                # Update scan status to failed
                async with AsyncSession(db.bind) as session:
                    await session.execute(
                        update(Scan)
                        .where(Scan.id == scan_id)
                        .values(
                            status="failed",
                            end_time=datetime.utcnow(),
                            error=f"Scan failed: {str(e)}"
                        )
                    )
                    await session.commit()
        
        # Add the task to background tasks
        background_tasks.add_task(run_scan_task)
        
        return {
            "scan_id": scan_id, 
            "status": "pending", 
            "type": scan_request.scan_type,
            "start_time": datetime.utcnow().isoformat()
        }
    except RuntimeError as e:
        # Known error: scan already running
        logger.warning(f"Cannot start scan: {str(e)}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        # Bad parameter values
        logger.warning(f"Invalid scan parameters: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Unexpected error
        logger.error(f"Error starting scan: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to start scan. Please try again later."
        )

@router.get("/", response_model=ScanListResponse)
async def list_scans(
    scan_type: Optional[str] = None,
    status: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: Client = Depends(get_current_client)
):
    """List all scans with optional filtering"""
    try:
        # Build query
        query = select(Scan).order_by(Scan.start_time.desc())
        
        # Apply filters
        if scan_type:
            query = query.filter(Scan.scan_type == scan_type)
        if status:
            query = query.filter(Scan.status == status)
        
        # Get total count for pagination
        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total_count = count_result.scalar_one()
        
        # Apply pagination
        query = query.offset(pagination.skip).limit(pagination.limit)
        
        # Execute query
        result = await db.execute(query)
        scans = result.scalars().all()
        
        # Format response
        scan_list = [
            {
                "scan_id": scan.id,
                "type": scan.scan_type,
                "status": scan.status,
                "start_time": scan.start_time,
                "end_time": scan.end_time,
                "has_results": bool(scan.results),
                "error": scan.error
            }
            for scan in scans
        ]
        
        return {
            "scans": scan_list,
            "total": total_count,
            "page": pagination.skip // pagination.limit + 1 if pagination.limit > 0 else 1,
            "page_size": pagination.limit
        }
    except Exception as e:
        logger.error(f"Error listing scans: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to retrieve scan list"
        )

@router.get("/{scan_id}", response_model=ScanStatusResponse)
async def get_scan_status(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Client = Depends(get_current_client)
):
    """Get the status of a specific scan"""
    try:
        # Query scan directly from database
        result = await db.execute(
            select(Scan).where(Scan.id == scan_id)
        )
        scan = result.scalar_one_or_none()
        
        # Check if scan exists
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scan with ID {scan_id} not found"
            )
        
        # Return formatted scan status
        return {
            "scan_id": scan.id,
            "status": scan.status,
            "type": scan.scan_type,
            "start_time": scan.start_time,
            "end_time": scan.end_time,
            "network_range": scan.network_range,
            "results": scan.results or {},
            "error": scan.error
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving scan status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scan status"
        )

@router.get("/{scan_id}/results", response_model=ScanResultsResponse)
async def get_scan_results(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Client = Depends(get_current_client)
):
    """Get detailed results of a completed scan"""
    try:
        # Query scan directly from database
        result = await db.execute(
            select(Scan).where(Scan.id == scan_id)
        )
        scan = result.scalar_one_or_none()
        
        # Check if scan exists
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scan with ID {scan_id} not found"
            )
        
        # Check if scan is completed
        if scan.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scan {scan_id} is not completed (current status: {scan.status})"
            )
        
        # Return results
        return {
            "scan_id": scan.id,
            "type": scan.scan_type,
            "start_time": scan.start_time,
            "end_time": scan.end_time,
            "duration_seconds": (scan.end_time - scan.start_time).total_seconds() if scan.end_time else None,
            "network_range": scan.network_range,
            "results": scan.results or {},
            "result_count": len(scan.results) if scan.results else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving scan results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scan results"
        )
