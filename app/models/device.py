from datetime import datetime
import hashlib
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.database import Base

def generate_hash_id():
    """Generate a unique hashed ID for devices"""
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]

class Device(Base):
    __tablename__ = "devices"

    # Use hash_id as the only identifier and primary key - character varying type
    hash_id = Column(String(64), primary_key=True, default=generate_hash_id, index=True)
    name = Column(String(255), index=True)
    ip_address = Column(String(50), index=True)
    mac_address = Column(String(50), unique=True, index=True)
    device_type = Column(String(100))
    manufacturer = Column(String(255))
    model = Column(String(255))
    firmware_version = Column(String(100))
    
    # Network properties
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_online = Column(Boolean, default=True)
    ports = Column(JSON, default=dict)  # Open ports and services
    
    # Protocol support
    supports_http = Column(Boolean, default=False)
    supports_mqtt = Column(Boolean, default=False)
    supports_coap = Column(Boolean, default=False)
    supports_websocket = Column(Boolean, default=False)
    
    # Security capabilities
    supports_tls = Column(Boolean, default=True)  # Whether device supports TLS
    tls_version = Column(String(20), default="TLS 1.2")  # TLS version supported
    cert_expiry = Column(DateTime)  # Certificate expiration date
    cert_issued_by = Column(String(255))  # Certificate issuer
    cert_strength = Column(Integer, default=2048)  # Certificate strength (bits)
    
    # Firmware check timestamp
    last_firmware_check = Column(DateTime)  # When firmware was last verified
    
    # Discovery method
    discovery_method = Column(String(50))  # zeroconf, nmap, mqtt, manual
    discovery_info = Column(JSON, default=dict)  # Additional discovery info
    
    # Authentication
    auth_type = Column(String(50))  # none, basic, token, oauth, etc.
    auth_data = Column(JSON, default=dict)  # Encrypted credentials
    
    # Additional data
    device_metadata = Column(JSON, default=dict)
    description = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Simplified firmware-related fields
    firmware_version = Column(String(100))  # String representation of firmware version
    current_firmware_id = Column(String(36), ForeignKey("firmware.id", ondelete="SET NULL"), nullable=True)  # Reference to firmware record if available
    
    # Relationships
    groups = relationship("Group", secondary="device_groups", back_populates="devices")
    sensor_readings = relationship("SensorReading", back_populates="device", cascade="all, delete-orphan")
    firmware_updates = relationship("FirmwareUpdate", back_populates="device", cascade="all, delete-orphan")
    current_firmware = relationship("Firmware", foreign_keys=[current_firmware_id])
    
    def __repr__(self):
        return f"<Device {self.name} ({self.ip_address})>"
    
    @property
    def id(self) -> str:
        """Alias for hash_id"""
        return self.hash_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert device to dictionary for API responses"""
        return {
            "id": self.hash_id,
            "name": self.name,
            "ip_address": self.ip_address,
            "mac_address": self.mac_address,
            "device_type": self.device_type,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "firmware_version": self.firmware_version,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "is_online": self.is_online,
            "ports": self.ports,
            "supports_http": self.supports_http,
            "supports_mqtt": self.supports_mqtt,
            "supports_coap": self.supports_coap,
            "supports_websocket": self.supports_websocket,
            "discovery_method": self.discovery_method,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            # Don't include group_ids to avoid async loading issues
            "group_ids": []
        }
    
    def to_dict_with_groups(self) -> Dict[str, Any]:
        """Convert device to dictionary including group information"""
        device_dict = self.to_dict()
        device_dict["groups"] = [{"id": group.id, "name": group.name, "group_type": group.group_type} 
                                for group in self.groups] if self.groups else []
        return device_dict
    
    @classmethod
    def from_discovery(cls, 
                      ip_address: str, 
                      mac_address: Optional[str], 
                      discovery_method: str,
                      discovery_info: Dict[str, Any],
                      name: Optional[str] = None) -> "Device":
        """Create a device instance from discovery data"""
        device = cls(
            ip_address=ip_address,
            mac_address=mac_address,
            discovery_method=discovery_method,
            discovery_info=discovery_info,
            name=name or f"Device_{mac_address[-6:] if mac_address else ip_address}"
        )
        return device 