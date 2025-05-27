"""Group API endpoints for IoT platform"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.group_service import GroupService
from app.api.deps import get_current_client
from app.api.schemas import (
    GroupCreate, GroupUpdate, GroupResponse, GroupWithDevices
)

router = APIRouter()

@router.get("/", response_model=List[GroupResponse])
async def list_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    group_type: Optional[str] = Query(None, description="Filter by group type"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """List all groups with optional filtering by type"""
    group_service = GroupService(db)
    
    if group_type:
        groups = await group_service.get_groups_by_type(group_type)
    else:
        groups = await group_service.get_all_groups(skip=skip, limit=limit)
    
    # Add device count to each group
    result = []
    for group in groups:
        group_dict = group.to_dict()
        group_dict["device_count"] = len(group.devices) if group.devices else 0
        result.append(group_dict)
    
    return result

@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Create a new group"""
    group_service = GroupService(db)
    
    group = await group_service.create_group(
        name=group_data.name,
        description=group_data.description,
        group_type=group_data.group_type,
        icon=group_data.icon,
        attributes=group_data.attributes,
        device_ids=group_data.device_ids
    )
    
    group_dict = group.to_dict()
    group_dict["device_count"] = len(group.devices) if group.devices else 0
    return group_dict

@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Get a specific group by ID"""
    group_service = GroupService(db)
    
    group = await group_service.get_group_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail=f"Group with ID {group_id} not found")
    
    group_dict = group.to_dict()
    group_dict["device_count"] = len(group.devices) if group.devices else 0
    return group_dict

@router.get("/{group_id}/devices", response_model=GroupWithDevices)
async def get_group_with_devices(
    group_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Get a specific group with its devices"""
    group_service = GroupService(db)
    
    group = await group_service.get_group_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail=f"Group with ID {group_id} not found")
    
    # Return group with device information
    result = group.to_dict_with_devices()
    result["device_count"] = len(group.devices) if group.devices else 0
    return result

@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_data: GroupUpdate,
    group_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Update a group"""
    group_service = GroupService(db)
    
    updated_group = await group_service.update_group(
        group_id=group_id,
        name=group_data.name,
        description=group_data.description,
        group_type=group_data.group_type,
        icon=group_data.icon,
        attributes=group_data.attributes,
        is_active=group_data.is_active
    )
    
    if not updated_group:
        raise HTTPException(status_code=404, detail=f"Group with ID {group_id} not found")
    
    group_dict = updated_group.to_dict()
    group_dict["device_count"] = len(updated_group.devices) if updated_group.devices else 0
    return group_dict

@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Delete a group"""
    group_service = GroupService(db)
    
    success = await group_service.delete_group(group_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Group with ID {group_id} not found")

@router.post("/{group_id}/devices", response_model=GroupResponse)
async def add_devices_to_group(
    device_ids: List[str] = Body(..., description="List of device hash IDs to add to the group"),
    group_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Add devices to a group"""
    group_service = GroupService(db)
    
    success = await group_service.add_devices_to_group(group_id, device_ids)
    if not success:
        raise HTTPException(status_code=404, detail=f"Group with ID {group_id} not found")
    
    # Return updated group
    group = await group_service.get_group_by_id(group_id)
    group_dict = group.to_dict()
    group_dict["device_count"] = len(group.devices) if group.devices else 0
    return group_dict

@router.delete("/{group_id}/devices", response_model=GroupResponse)
async def remove_devices_from_group(
    device_ids: List[str] = Body(..., description="List of device hash IDs to remove from the group"),
    group_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Remove devices from a group"""
    group_service = GroupService(db)
    
    success = await group_service.remove_devices_from_group(group_id, device_ids)
    if not success:
        raise HTTPException(status_code=404, detail=f"Group with ID {group_id} not found")
    
    # Return updated group
    group = await group_service.get_group_by_id(group_id)
    group_dict = group.to_dict()
    group_dict["device_count"] = len(group.devices) if group.devices else 0
    return group_dict

@router.get("/device/{device_id}", response_model=List[GroupResponse])
async def get_device_groups(
    device_id: str = Path(..., description="Device hash ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Get all groups for a specific device"""
    group_service = GroupService(db)
    
    groups = await group_service.get_groups_for_device(device_id)
    
    # Add device count to each group
    result = []
    for group in groups:
        group_dict = group.to_dict()
        group_dict["device_count"] = len(group.devices) if group.devices else 0
        result.append(group_dict)
    
    return result
