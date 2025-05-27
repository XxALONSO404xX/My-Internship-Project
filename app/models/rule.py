from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.database import Base

class Rule(Base):
    """Model for defining automated rules based on sensor readings and device states"""
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(Text)
    
    # Rule type (threshold, schedule, state_change, etc.)
    rule_type = Column(String(50), index=True)
    
    # Enabled status
    is_enabled = Column(Boolean, default=True)
    
    # Execution schedule (cron expression for scheduled rules)
    schedule = Column(String(100), nullable=True)
    
    # Target device IDs (null means apply to all matching devices)
    target_device_ids = Column(JSON, nullable=True, comment="List of specific device IDs this rule applies to")
    
    # Conditions (JSON structure defining when the rule should trigger)
    # Example:
    # {
    #   "operator": "AND",
    #   "conditions": [
    #     {"type": "sensor", "device_id": 1, "sensor_type": "temperature", "operator": ">", "value": 30},
    #     {"type": "device_status", "device_id": 1, "property": "is_online", "operator": "==", "value": true}
    #   ]
    # }
    conditions = Column(JSON, nullable=False)
    
    # Actions to perform when conditions are met (JSON structure)
    # Example:
    # [
    #   {"type": "device_control", "device_id": 2, "action": "turn_on", "parameters": {}},
    #   {"type": "notification", "channel": "email", "recipients": ["user@example.com"], "template": "alert", "parameters": {}}
    # ]
    actions = Column(JSON, nullable=False)
    
    # Priority (higher numbers = higher priority)
    priority = Column(Integer, default=1)
    
    # Last triggered timestamp
    last_triggered = Column(DateTime, nullable=True)
    
    # Rule state - success, error, waiting
    status = Column(String(50), default="waiting")
    status_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Rule {self.name} ({self.rule_type})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type,
            "is_enabled": self.is_enabled,
            "schedule": self.schedule,
            "target_device_ids": self.target_device_ids,
            "conditions": self.conditions,
            "actions": self.actions,
            "priority": self.priority,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "status": self.status,
            "status_message": self.status_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        } 