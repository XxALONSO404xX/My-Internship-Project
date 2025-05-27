"""Activity tracking service for the IoT Platform"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import desc
from sqlalchemy.orm import aliased
from collections import defaultdict

from app.models.activity import Activity
from app.models.device import Device

logger = logging.getLogger(__name__)

class ActivityService:
    """Service for tracking and querying user and system activities"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_activity(self, 
                           activity_type: str,
                           action: str,
                           description: str = None,
                           user_id: Optional[int] = None,
                           user_ip: Optional[str] = None,
                           target_type: Optional[str] = None,
                           target_id: Optional[int] = None,
                           target_name: Optional[str] = None,
                           previous_state: Optional[Dict[str, Any]] = None,
                           new_state: Optional[Dict[str, Any]] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> Activity:
        """
        Log a new activity
        
        Args:
            activity_type: Type of activity (user_action, system_event, state_change, alert)
            action: Action performed (turn_on, turn_off, update_settings, etc.)
            description: Human-readable description of the activity
            user_id: ID of the user who performed the action (None for system events)
            user_ip: IP address of the user
            target_type: Type of target affected (device, group, system)
            target_id: ID of the affected entity
            target_name: Name of the affected entity
            previous_state: State before the action
            new_state: State after the action
            metadata: Any additional context data
            
        Returns:
            Newly created Activity instance
        """
        activity = Activity(
            activity_type=activity_type,
            action=action,
            description=description,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            user_ip=user_ip,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            previous_state=previous_state,
            new_state=new_state,
            metadata=metadata or {}
        )
        
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)
        
        logger.info(f"Activity logged: {activity_type}:{action} on {target_type}:{target_name}")
        return activity
    
    async def log_device_state_change(self,
                                     device_id: int,
                                     device_name: str,
                                     action: str,
                                     previous_state: Dict[str, Any],
                                     new_state: Dict[str, Any],
                                     user_id: Optional[int] = None,
                                     user_ip: Optional[str] = None,
                                     description: Optional[str] = None) -> Activity:
        """
        Log a device state change activity
        
        Args:
            device_id: ID of the device
            device_name: Name of the device
            action: Action performed (turn_on, turn_off, update_settings, etc.)
            previous_state: State before the action
            new_state: State after the action
            user_id: ID of the user who performed the action (None for system events)
            user_ip: IP address of the user
            description: Human-readable description of the activity
            
        Returns:
            Newly created Activity instance
        """
        # Generate description if not provided
        if not description:
            if action == "turn_on":
                description = f"Device {device_name} was turned on"
            elif action == "turn_off":
                description = f"Device {device_name} was turned off"
            elif action == "update_settings":
                description = f"Settings updated for device {device_name}"
            else:
                description = f"Device {device_name} state changed: {action}"
        
        return await self.log_activity(
            activity_type="state_change",
            action=action,
            description=description,
            user_id=user_id,
            user_ip=user_ip,
            target_type="device",
            target_id=device_id,
            target_name=device_name,
            previous_state=previous_state,
            new_state=new_state
        )
    
    async def log_user_action(self,
                             user_id: int,
                             user_ip: str,
                             action: str,
                             description: str,
                             target_type: Optional[str] = None,
                             target_id: Optional[int] = None,
                             target_name: Optional[str] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> Activity:
        """
        Log a user action activity
        
        Args:
            user_id: ID of the user
            user_ip: IP address of the user
            action: Action performed
            description: Human-readable description of the activity
            target_type: Type of target affected
            target_id: ID of the affected entity
            target_name: Name of the affected entity
            metadata: Any additional context data
            
        Returns:
            Newly created Activity instance
        """
        return await self.log_activity(
            activity_type="user_action",
            action=action,
            description=description,
            user_id=user_id,
            user_ip=user_ip,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            metadata=metadata
        )
    
    async def log_system_event(self,
                              action: str,
                              description: str,
                              target_type: Optional[str] = None,
                              target_id: Optional[int] = None,
                              target_name: Optional[str] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> Activity:
        """
        Log a system event activity
        
        Args:
            action: Action performed
            description: Human-readable description of the activity
            target_type: Type of target affected
            target_id: ID of the affected entity
            target_name: Name of the affected entity
            metadata: Any additional context data
            
        Returns:
            Newly created Activity instance
        """
        return await self.log_activity(
            activity_type="system_event",
            action=action,
            description=description,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            metadata=metadata
        )
    
    async def log_alert(self,
                       action: str,
                       description: str,
                       severity: str,
                       target_type: Optional[str] = None,
                       target_id: Optional[int] = None,
                       target_name: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> Activity:
        """
        Log an alert activity
        
        Args:
            action: Alert type
            description: Human-readable description of the alert
            severity: Alert severity (low, medium, high, critical)
            target_type: Type of target affected
            target_id: ID of the affected entity
            target_name: Name of the affected entity
            metadata: Any additional context data
            
        Returns:
            Newly created Activity instance
        """
        metadata = metadata or {}
        metadata["severity"] = severity
        
        return await self.log_activity(
            activity_type="alert",
            action=action,
            description=description,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            metadata=metadata
        )
    
    async def get_recent_activities(self, limit: int = 100, skip: int = 0) -> List[Activity]:
        """Get most recent activities"""
        query = select(Activity).order_by(desc(Activity.timestamp)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_activities_by_type(self, activity_type: str, limit: int = 100, skip: int = 0) -> List[Activity]:
        """Get activities by type"""
        query = select(Activity).where(Activity.activity_type == activity_type).order_by(desc(Activity.timestamp)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_activities_by_target(self, target_type: str, target_id: int, limit: int = 100, skip: int = 0) -> List[Activity]:
        """Get activities for a specific target"""
        query = select(Activity).where(
            and_(
                Activity.target_type == target_type,
                Activity.target_id == target_id
            )
        ).order_by(desc(Activity.timestamp)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_activities_by_time_range(self, start_time: datetime, end_time: datetime, limit: int = 100, skip: int = 0) -> List[Activity]:
        """Get activities within a time range"""
        query = select(Activity).where(
            and_(
                Activity.timestamp >= start_time,
                Activity.timestamp <= end_time
            )
        ).order_by(desc(Activity.timestamp)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def search_activities(self,
                              activity_type: Optional[str] = None,
                              action: Optional[str] = None,
                              target_type: Optional[str] = None,
                              target_id: Optional[int] = None,
                              user_id: Optional[int] = None,
                              start_time: Optional[datetime] = None,
                              end_time: Optional[datetime] = None,
                              limit: int = 100,
                              skip: int = 0) -> List[Activity]:
        """
        Search activities with filtering
        
        Args:
            activity_type: Filter by activity type
            action: Filter by action
            target_type: Filter by target type
            target_id: Filter by target ID
            user_id: Filter by user ID
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of results
            skip: Number of results to skip
            
        Returns:
            List of matching Activity instances
        """
        conditions = []
        
        if activity_type:
            conditions.append(Activity.activity_type == activity_type)
        
        if action:
            conditions.append(Activity.action == action)
        
        if target_type:
            conditions.append(Activity.target_type == target_type)
        
        if target_id:
            conditions.append(Activity.target_id == target_id)
        
        if user_id:
            conditions.append(Activity.user_id == user_id)
        
        if start_time:
            conditions.append(Activity.timestamp >= start_time)
        
        if end_time:
            conditions.append(Activity.timestamp <= end_time)
        
        if conditions:
            query = select(Activity).where(and_(*conditions))
        else:
            query = select(Activity)
        
        query = query.order_by(desc(Activity.timestamp)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all() 