"""Group Management Service for IoT Platform

This consolidated service module combines:
1. GroupService - Core group management functionality (CRUD, device assignment)
2. GroupVulnerabilityService - Group-level vulnerability scanning and analysis

The service handles all group-related operations including:
- Creating, reading, updating and deleting groups
- Adding/removing devices to/from groups
- Group-based vulnerability scanning
- Group vulnerability statistics and reporting
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy import select, update, delete, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.group import Group, device_groups
from app.models.device import Device
from app.services.security_service import VulnerabilityScanner

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
        
    def format_group_response(self, group: Group) -> Dict[str, Any]:
        """Format a group for API response with device count"""
        group_dict = group.to_dict()
        group_dict["device_count"] = len(group.devices) if group.devices else 0
        return group_dict
    
    def format_groups_response(self, groups: List[Group]) -> List[Dict[str, Any]]:
        """Format a list of groups for API response with device counts"""
        return [self.format_group_response(group) for group in groups]


class GroupVulnerabilityService:
    """Service for scanning groups of devices for vulnerabilities"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.vulnerability_scanner = VulnerabilityScanner(db)
        self.group_service = GroupService(db)
    
    async def scan_group(self, group_id: int) -> Dict[str, Any]:
        """Scan all devices in a group for vulnerabilities"""
        # Verify group exists
        group = await self.group_service.get_group_by_id(group_id)
        if not group:
            return {
                "status": "failed",
                "message": f"Group with ID {group_id} not found"
            }
        
        # Get all devices in the group
        devices = await self.group_service.get_devices_in_group(group_id)
        
        if not devices:
            return {
                "status": "info",
                "message": f"No devices found in group {group.name} (ID: {group_id})",
                "group_id": group_id,
                "group_name": group.name
            }
        
        # Extract device hash_ids
        device_ids = [device.hash_id for device in devices]
        
        # Start a vulnerability scan for these devices
        scan_result = await self.vulnerability_scanner.scan_multiple_devices(device_ids)
        
        # Add group information to the result
        scan_result["group_id"] = group_id
        scan_result["group_name"] = group.name
        scan_result["group_type"] = group.group_type
        
        return scan_result
    
    async def get_group_vulnerability_stats(self, group_id: int) -> Dict[str, Any]:
        """Get vulnerability statistics for a group"""
        # Verify group exists
        group = await self.group_service.get_group_by_id(group_id)
        if not group:
            return {
                "status": "failed",
                "message": f"Group with ID {group_id} not found"
            }
        
        # Get all devices in the group
        devices = await self.group_service.get_devices_in_group(group_id)
        
        if not devices:
            return {
                "status": "info",
                "message": f"No devices found in group {group.name} (ID: {group_id})",
                "group_id": group_id,
                "group_name": group.name,
                "device_count": 0,
                "vulnerability_stats": {}
            }
        
        # Calculate vulnerability statistics from each device's latest vulnerability scan
        total_devices = len(devices)
        devices_with_vulnerabilities = 0
        vulnerability_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        # Here we would normally query the database for actual vulnerability data
        # For now, we'll return mock statistics
        devices_with_vulnerabilities = total_devices // 2
        vulnerability_counts = {
            "critical": total_devices // 10,
            "high": total_devices // 5,
            "medium": total_devices // 3,
            "low": total_devices // 2
        }
        
        # Calculate risk score based on vulnerabilities
        risk_score = (
            (vulnerability_counts["critical"] * 10.0) +
            (vulnerability_counts["high"] * 7.5) +
            (vulnerability_counts["medium"] * 5.0) +
            (vulnerability_counts["low"] * 2.5)
        ) / max(1, total_devices)
        
        return {
            "status": "success",
            "group_id": group_id,
            "group_name": group.name,
            "group_type": group.group_type,
            "device_count": total_devices,
            "devices_with_vulnerabilities": devices_with_vulnerabilities,
            "vulnerability_counts": vulnerability_counts,
            "risk_score": min(10.0, risk_score),
            "last_scan_date": datetime.utcnow().isoformat()
        }
        
    async def get_vulnerability_dashboard(self, limit: int = 10) -> Dict[str, Any]:
        """Get vulnerability dashboard data organized by groups
        
        Args:
            limit: Number of highest risk groups to return
        
        Returns:
            Dashboard data with vulnerability statistics across groups
        """
        # Get all groups
        all_groups = await self.group_service.get_all_groups(limit=100)  # Reasonable upper limit
        
        if not all_groups:
            return {
                "status": "info",
                "message": "No groups found in the system",
                "groups_with_vulnerabilities": 0,
                "total_groups": 0,
                "highest_risk_groups": [],
                "vulnerability_distribution": {
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0
                }
            }
        
        # Get vulnerability stats for each group
        group_stats = []
        total_vulnerability_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        groups_with_vulnerabilities = 0
        
        for group in all_groups:
            # Get stats for this group
            stats = await self.get_group_vulnerability_stats(group.id)
            
            # Skip groups with errors or no devices
            if stats.get("status") != "success":
                continue
                
            # Get vulnerability counts and add to totals
            counts = stats.get("vulnerability_counts", {})
            has_vulnerabilities = False
            
            for severity, count in counts.items():
                if count > 0:
                    has_vulnerabilities = True
                    total_vulnerability_counts[severity] += count
            
            if has_vulnerabilities:
                groups_with_vulnerabilities += 1
                
            # Add to group stats if has vulnerabilities
            group_stats.append({
                "group_id": stats["group_id"],
                "group_name": stats["group_name"],
                "risk_score": stats.get("risk_score", 0),
                "vulnerability_count": sum(counts.values())
            })
        
        # Sort by risk score (descending)
        group_stats.sort(key=lambda x: x["risk_score"], reverse=True)
        
        # Limit to requested number
        highest_risk_groups = group_stats[:limit]
        
        return {
            "status": "success",
            "groups_with_vulnerabilities": groups_with_vulnerabilities,
            "total_groups": len(all_groups),
            "highest_risk_groups": highest_risk_groups,
            "vulnerability_distribution": total_vulnerability_counts
        }


#-----------------------------------------------------------------
# Factory functions to create service instances
#-----------------------------------------------------------------

def create_group_service(db: AsyncSession) -> GroupService:
    """Create a new group service instance with the given database session"""
    return GroupService(db)

def create_group_vulnerability_service(db: AsyncSession) -> GroupVulnerabilityService:
    """Create a group vulnerability service with the given database session"""
    return GroupVulnerabilityService(db)
