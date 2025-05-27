from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.database import Base

class SensorReading(Base):
    """Model for storing time-series sensor data from IoT devices"""
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # Foreign key to the device using hash_id
    device_id = Column(String(64), ForeignKey("devices.hash_id", ondelete="CASCADE"), index=True)
    
    # Timestamp of the reading
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Sensor type (temperature, humidity, motion, etc.)
    sensor_type = Column(String(50), index=True)
    
    # Reading value
    value = Column(Float)
    
    # Unit of measurement (°C, %, lux, etc.)
    unit = Column(String(20))
    
    # Reading status (normal, warning, critical, etc.)
    status = Column(String(20), default="normal")
    
    # Additional data
    reading_metadata = Column(JSON, default=dict)
    
    # Relationship to device
    device = relationship("Device", back_populates="sensor_readings")
    
    def __repr__(self):
        return f"<SensorReading {self.sensor_type} {self.value}{self.unit} @ {self.timestamp}>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sensor reading to dictionary for API responses"""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "timestamp": self.timestamp.isoformat(),
            "sensor_type": self.sensor_type,
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            "metadata": self.reading_metadata
        } 