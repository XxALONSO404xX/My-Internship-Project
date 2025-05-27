from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, Text, Table
from sqlalchemy.orm import relationship

from app.models.database import Base

# Association table for many-to-many relationship between devices and groups
device_groups = Table(
    'device_groups',
    Base.metadata,
    Column('device_id', String(64), ForeignKey('devices.hash_id', ondelete='CASCADE'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True)
)

class Group(Base):
    """Model for organizing devices into groups or rooms"""
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(Text)
    
    # Group type (room, location, category, etc.)
    group_type = Column(String(50), index=True, default="room")
    
    # Group attributes (e.g., floor number, building name, etc.)
    attributes = Column(JSON, default=dict)
    
    # Icon to use for the group
    icon = Column(String(50))
    
    # Color code for UI display
    color = Column(String(20))
    
    # Whether the group is active
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    devices = relationship("Device", secondary=device_groups, back_populates="groups")
    
    def __repr__(self):
        return f"<Group {self.name} ({self.group_type})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert group to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "group_type": self.group_type,
            "attributes": self.attributes,
            "icon": self.icon,
            "color": self.color,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "device_count": len(self.devices) if self.devices else 0
        }
        
    def to_dict_with_devices(self) -> Dict[str, Any]:
        """Convert group to dictionary including device information"""
        group_dict = self.to_dict()
        group_dict["devices"] = [device.to_dict() for device in self.devices]
        return group_dict 