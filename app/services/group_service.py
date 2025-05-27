"""Group Service for IoT Platform"""
import logging
from typing import Dict, List, Optional, Any
from sqlalchemy import select, update, delete, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.group import Group, device_groups
from app.models.device import Device

logger = logging.getLogger(__name__)

class GroupService:
    """Service for managing device groups"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all_groups(self, skip: int = 0, limit: int = 100) -> List[Group]:
        """Get all groups with pagination"""
        query = select(Group).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_group_by_id(self, group_id: int) -> Optional[Group]:
        """Get a group by ID"""
        query = select(Group).where(Group.id == group_id).options(joinedload(Group.devices))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_groups_by_type(self, group_type: str) -> List[Group]:
        """Get groups by type"""
        query = select(Group).where(Group.group_type == group_type)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_group(self, 
                          name: str, 
                          description: Optional[str] = None, 
                          group_type: str = "room",
                          icon: Optional[str] = None,
                          attributes: Optional[Dict[str, Any]] = None,
                          device_ids: Optional[List[str]] = None) -> Group:
        """Create a new group"""
        # Create group
        group = Group(
            name=name,
            description=description,
            group_type=group_type,
            icon=icon,
            attributes=attributes or {},
            is_active=True
        )
        self.db.add(group)
        await self.db.flush()
        
        # Add devices to group if provided
        if device_ids:
            await self.add_devices_to_group(group.id, device_ids)
        
        await self.db.commit()
        await self.db.refresh(group)
        return group
    
    async def update_group(self, 
                          group_id: int, 
                          name: Optional[str] = None, 
                          description: Optional[str] = None,
                          group_type: Optional[str] = None,
                          icon: Optional[str] = None,
                          attributes: Optional[Dict[str, Any]] = None,
                          is_active: Optional[bool] = None) -> Optional[Group]:
        """Update a group"""
        group = await self.get_group_by_id(group_id)
        if not group:
            return None
        
        # Update fields if provided
        if name is not None:
            group.name = name
        if description is not None:
            group.description = description
        if group_type is not None:
            group.group_type = group_type
        if icon is not None:
            group.icon = icon
        if attributes is not None:
            group.attributes = attributes
        if is_active is not None:
            group.is_active = is_active
        
        await self.db.commit()
        await self.db.refresh(group)
        return group
    
    async def delete_group(self, group_id: int) -> bool:
        """Delete a group"""
        group = await self.get_group_by_id(group_id)
        if not group:
            return False
        
        await self.db.delete(group)
        await self.db.commit()
        return True
    
    async def add_devices_to_group(self, group_id: int, device_ids: List[str]) -> bool:
        """Add devices to a group"""
        group = await self.get_group_by_id(group_id)
        if not group:
            return False
        
        # Get devices by hash_id
        query = select(Device).where(Device.hash_id.in_(device_ids))
        result = await self.db.execute(query)
        devices = result.scalars().all()
        
        # Add devices to group
        for device in devices:
            if device not in group.devices:
                group.devices.append(device)
        
        await self.db.commit()
        return True
    
    async def remove_devices_from_group(self, group_id: int, device_ids: List[str]) -> bool:
        """Remove devices from a group"""
        group = await self.get_group_by_id(group_id)
        if not group:
            return False
        
        # Get devices by hash_id
        query = select(Device).where(Device.hash_id.in_(device_ids))
        result = await self.db.execute(query)
        devices = result.scalars().all()
        
        # Remove devices from group
        for device in devices:
            if device in group.devices:
                group.devices.remove(device)
        
        await self.db.commit()
        return True
    
    async def get_devices_in_group(self, group_id: int) -> List[Device]:
        """Get all devices in a group"""
        group = await self.get_group_by_id(group_id)
        if not group:
            return []
        
        return group.devices
    
    async def get_groups_for_device(self, device_hash_id: str) -> List[Group]:
        """Get all groups for a device"""
        query = select(Device).where(Device.hash_id == device_hash_id).options(joinedload(Device.groups))
        result = await self.db.execute(query)
        device = result.scalar_one_or_none()
        
        if not device:
            return []
            
        return device.groups
