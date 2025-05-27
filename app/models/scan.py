from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.models.database import Base

class Scan(Base):
    """Model for storing scan operations"""
    __tablename__ = "scans"

    id = Column(String(50), primary_key=True, index=True)
    status = Column(String(20), index=True)  # running, completed, failed
    scan_type = Column(String(50), index=True)  # discovery, vulnerability, exploit
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    network_range = Column(String(100), nullable=True)
    results = Column(JSON, nullable=True)
    error = Column(String(500), nullable=True)
    
    # Relationships
    vulnerability_scans = relationship("VulnerabilityScan", back_populates="scan", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Scan {self.id} ({self.scan_type})>"

class VulnerabilityScan(Base):
    """Model for storing vulnerability scan results"""
    __tablename__ = "vulnerability_scans"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(String(50), ForeignKey("scans.id"), index=True)
    device_id = Column(String(64), ForeignKey("devices.hash_id"), index=True)
    status = Column(String(20), index=True)  # completed, error
    vulnerabilities = Column(JSON, nullable=True)
    risk_score = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    error = Column(String(500), nullable=True)
    
    # Relationships
    scan = relationship("Scan", back_populates="vulnerability_scans")
    device = relationship("Device", backref="vulnerability_scans")
    
    def __repr__(self):
        return f"<VulnerabilityScan {self.id} for device {self.device_id}>" 