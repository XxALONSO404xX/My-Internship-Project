import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.activity_service import ActivityService
from app.api.schemas import (
    ActivityResponse, ActivityCreate, ActivityFilter,
    Response, ErrorResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[ActivityResponse])
async def get_activities(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent activities
    
    Returns the most recent activities, sorted by timestamp (newest first)
    """
    activity_service = ActivityService(db)
    activities = await activity_service.get_recent_activities(limit=limit, skip=skip)
    return activities

@router.get("/types/{activity_type}", response_model=List[ActivityResponse])
async def get_activities_by_type(
    activity_type: str = Path(..., description="Type of activity to filter by"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get activities by type
    
    Returns activities filtered by the specified type (user_action, system_event, state_change, alert)
    """
    activity_service = ActivityService(db)
    activities = await activity_service.get_activities_by_type(activity_type, limit=limit, skip=skip)
    return activities

@router.get("/targets/{target_type}/{target_id}", response_model=List[ActivityResponse])
async def get_activities_by_target(
    target_type: str = Path(..., description="Type of target (device, group, system)"),
    target_id: int = Path(..., description="ID of the target"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get activities for a specific target
    
    Returns activities related to a specific target, such as a device, group, or system component
    """
    activity_service = ActivityService(db)
    activities = await activity_service.get_activities_by_target(target_type, target_id, limit=limit, skip=skip)
    return activities

@router.post("/search", response_model=List[ActivityResponse])
async def search_activities(
    filter_params: ActivityFilter,
    db: AsyncSession = Depends(get_db)
):
    """
    Search activities with filters
    
    Search for activities using various filter criteria
    """
    activity_service = ActivityService(db)
    activities = await activity_service.search_activities(
        activity_type=filter_params.activity_type,
        action=filter_params.action,
        target_type=filter_params.target_type,
        target_id=filter_params.target_id,
        user_id=filter_params.user_id,
        start_time=filter_params.start_time,
        end_time=filter_params.end_time,
        limit=filter_params.limit,
        skip=filter_params.skip
    )
    return activities

@router.get("/recent/{hours}", response_model=List[ActivityResponse])
async def get_recent_activities_by_hours(
    hours: int = Path(..., ge=1, le=720, description="Number of hours to look back"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get activities from the past N hours
    
    Returns activities that occurred within the specified number of hours from now
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    activity_service = ActivityService(db)
    activities = await activity_service.get_activities_by_time_range(
        start_time=start_time, 
        end_time=end_time,
        limit=limit,
        skip=skip
    )
    return activities

@router.get("/actions/{action}", response_model=List[ActivityResponse])
async def get_activities_by_action(
    action: str = Path(..., description="Action to filter by (e.g., turn_on, turn_off)"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get activities by action
    
    Returns activities filtered by the specified action
    """
    activity_service = ActivityService(db)
    activities = await activity_service.search_activities(action=action, limit=limit, skip=skip)
    return activities

@router.post("/", response_model=ActivityResponse)
async def create_activity(
    activity: ActivityCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new activity
    
    This endpoint is primarily for internal use. Most activities should be created through
    specific actions in the system, but this provides a way to manually create activities if needed.
    """
    activity_service = ActivityService(db)
    
    # Get client IP address from request
    client_ip = request.client.host if request.client else None
    
    # If no user_ip is provided, use the client IP
    if not activity.user_ip and client_ip:
        activity.user_ip = client_ip
    
    new_activity = await activity_service.log_activity(
        activity_type=activity.activity_type,
        action=activity.action,
        description=activity.description,
        user_id=activity.user_id,
        user_ip=activity.user_ip,
        target_type=activity.target_type,
        target_id=activity.target_id,
        target_name=activity.target_name,
        previous_state=activity.previous_state,
        new_state=activity.new_state,
        metadata=activity.metadata
    )
    
    return new_activity

@router.get("/summary", response_model=Dict)
async def get_activity_summary(
    hours: int = Query(24, ge=1, le=720, description="Number of hours to look back"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get activity summary statistics
    
    Returns summary statistics for activities in the specified time period
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    activity_service = ActivityService(db)
    activities = await activity_service.get_activities_by_time_range(
        start_time=start_time, 
        end_time=end_time,
        limit=1000  # Get a large sample for accurate stats
    )
    
    # Count activities by type
    activity_counts = {
        "user_action": 0,
        "system_event": 0,
        "state_change": 0,
        "alert": 0,
        "total": len(activities)
    }
    
    # Count activities by target type
    target_counts = {}
    
    # Count activities by action
    action_counts = {}
    
    for activity in activities:
        # Count by activity type
        activity_type = activity.activity_type
        activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1
        
        # Count by target type
        if activity.target_type:
            target_counts[activity.target_type] = target_counts.get(activity.target_type, 0) + 1
        
        # Count by action
        action_counts[activity.action] = action_counts.get(activity.action, 0) + 1
    
    return {
        "time_period": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "hours": hours
        },
        "counts": {
            "by_type": activity_counts,
            "by_target": target_counts,
            "by_action": action_counts
        },
        "total_activities": len(activities)
    } 