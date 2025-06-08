from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.database import Base

class Activity(Base):
    """Model for storing all system and user activities"""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    
    # Activity type categorization
    activity_type = Column(String(50), index=True)  # user_action, system_event, state_change, alert
    
    # What happened
    action = Column(String(100), index=True)  # turn_on, turn_off, update_settings, etc.
    description = Column(Text)
    
    # When it happened
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Who did it (if user action)
    user_id = Column(Integer, nullable=True, index=True)  # Can be null for system events
    user_ip = Column(String(50), nullable=True)
    
    # What it affected
    target_type = Column(String(50), index=True)  # device, group, system
    target_id = Column(String(64), nullable=True, index=True)  # ID of the affected entity (device hash_id)
    target_name = Column(String(255), nullable=True)  # Name of the affected entity
    
    # Before/after state
    previous_state = Column(JSON, nullable=True)  # State before the action
    new_state = Column(JSON, nullable=True)  # State after the action
    
    # Additional metadata
    activity_metadata = Column(JSON, default=dict)  # Any additional context data
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Activity {self.activity_type}:{self.action} on {self.target_type}:{self.target_name}>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert activity to dictionary for API responses"""
        return {
            "id": self.id,
            "activity_type": self.activity_type,
            "action": self.action,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "user_ip": self.user_ip,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "metadata": self.activity_metadata,
            "created_at": self.created_at.isoformat()
        } 