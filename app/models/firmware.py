"""Simplified Firmware models for IoT Platform"""
from datetime import datetime
import uuid
from typing import Dict, Any
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.database import Base

def generate_uuid():
    """Generate a unique UUID for firmware records"""
    return str(uuid.uuid4())

class Firmware(Base):
    """Simplified firmware model for storing firmware versions"""
    __tablename__ = "firmware"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    version = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    device_type = Column(String(100), nullable=False, index=True)  # To match with device types
    release_date = Column(DateTime, default=datetime.utcnow)
    is_critical = Column(Boolean, default=False)  # Flag for critical updates
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    devices = relationship("Device", back_populates="current_firmware")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "version": self.version,
            "name": self.name,
            "device_type": self.device_type,
            "release_date": self.release_date.isoformat() if self.release_date else None,
            "is_critical": self.is_critical,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class FirmwareUpdate(Base):
    """Simplified model for tracking firmware updates"""
    __tablename__ = "firmware_updates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    device_id = Column(String(64), ForeignKey("devices.hash_id", ondelete="CASCADE"), nullable=False, index=True)
    firmware_id = Column(String(36), ForeignKey("firmware.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, completed, failed
    completed_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    job_id = Column(String(36))  # Reference to a job if part of bulk operation
    
    # Relationships
    device = relationship("Device", back_populates="firmware_updates")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "firmware_id": self.firmware_id,
            "status": self.status,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "job_id": self.job_id
        }
