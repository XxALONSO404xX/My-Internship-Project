"""Firmware models for IoT Platform"""
from datetime import datetime
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, Text, Float
from sqlalchemy.orm import relationship

from app.models.database import Base

def generate_uuid():
    """Generate a unique UUID for firmware records"""
    return str(uuid.uuid4())

class Firmware(Base):
    """Firmware model for storing firmware versions"""
    __tablename__ = "firmware"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    version = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    device_type = Column(String(100), nullable=False, index=True)
    release_date = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer)  # Size in bytes
    download_url = Column(String(255))
    changelog = Column(Text)
    is_critical = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(50), ForeignKey("clients.id"), nullable=True)
    
    # Relationships
    updates = relationship("FirmwareUpdate", back_populates="firmware")
    batch_updates = relationship("FirmwareBatchUpdate", back_populates="firmware")
    devices = relationship("Device", back_populates="current_firmware")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "device_type": self.device_type,
            "release_date": self.release_date,
            "file_size": self.file_size,
            "download_url": self.download_url,
            "changelog": self.changelog,
            "is_critical": self.is_critical,
            "created_at": self.created_at
        }


class FirmwareUpdate(Base):
    """FirmwareUpdate model for tracking individual device updates"""
    __tablename__ = "firmware_updates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    device_id = Column(String(64), ForeignKey("devices.hash_id", ondelete="CASCADE"), nullable=False, index=True)
    firmware_id = Column(String(36), ForeignKey("firmware.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, downloading, installing, rebooting, completed, failed
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    progress = Column(Integer, default=0)  # 0-100%
    speed_kbps = Column(Integer)  # Simulated download speed
    estimated_time_remaining = Column(Integer)  # Seconds remaining
    error_message = Column(Text)
    error_code = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    batch_id = Column(String(36), ForeignKey("firmware_batch_updates.id", ondelete="SET NULL"), nullable=True)
    
    # Security-related fields for secure transmission
    secure_channel = Column(Boolean, default=True)  # Whether update is transmitted over secure channel
    encryption_method = Column(String(50))  # E.g., AES-256-GCM, ChaCha20-Poly1305
    signature_verified = Column(Boolean)  # Whether firmware signature was verified
    
    # Relationships
    device = relationship("Device", back_populates="firmware_updates")
    firmware = relationship("Firmware", back_populates="updates")
    batch = relationship("FirmwareBatchUpdate", back_populates="updates")
    history_entries = relationship("DeviceFirmwareHistory", back_populates="update")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "firmware_id": self.firmware_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": self.progress,
            "speed_kbps": self.speed_kbps,
            "estimated_time_remaining": self.estimated_time_remaining,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "batch_id": self.batch_id
        }


class FirmwareBatchUpdate(Base):
    """FirmwareBatchUpdate model for tracking bulk firmware updates"""
    __tablename__ = "firmware_batch_updates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    firmware_id = Column(String(36), ForeignKey("firmware.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100))
    status = Column(String(20), nullable=False, default="pending")  # pending, in_progress, completed, partial, failed
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    total_devices = Column(Integer, default=0)
    successful_devices = Column(Integer, default=0)
    failed_devices = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(50), ForeignKey("clients.id"), nullable=True)
    notes = Column(Text)
    
    # Relationships
    firmware = relationship("Firmware", back_populates="batch_updates")
    updates = relationship("FirmwareUpdate", back_populates="batch")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "firmware_id": self.firmware_id,
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_devices": self.total_devices,
            "successful_devices": self.successful_devices,
            "failed_devices": self.failed_devices,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "notes": self.notes
        }


class DeviceFirmwareHistory(Base):
    """DeviceFirmwareHistory model for tracking firmware changes on devices"""
    __tablename__ = "device_firmware_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("devices.hash_id", ondelete="CASCADE"), nullable=False, index=True)
    firmware_id = Column(String(36), ForeignKey("firmware.id", ondelete="CASCADE"), nullable=False)
    previous_version = Column(String(50))
    updated_at = Column(DateTime, default=datetime.utcnow)
    update_id = Column(String(36), ForeignKey("firmware_updates.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    device = relationship("Device", back_populates="firmware_history")
    firmware = relationship("Firmware")
    update = relationship("FirmwareUpdate", back_populates="history_entries")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "firmware_id": self.firmware_id,
            "previous_version": self.previous_version,
            "updated_at": self.updated_at,
            "update_id": self.update_id
        }
