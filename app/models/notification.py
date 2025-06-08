from datetime import datetime
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, Text, func
from sqlalchemy.orm import relationship

from app.models.database import Base

logger = logging.getLogger(__name__)

class Notification(Base):
    """
    Notification model for storing all notifications in the system
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    notification_type = Column(String(50), index=True)  # "alert", "warning", "info", "error", etc
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(50), index=True)  # "system", "rule", "device", "user", etc
    source_id = Column(Integer, nullable=True)  # ID of source if applicable
    
    # Target details (what the notification is about)
    target_type = Column(String(50), nullable=True, index=True)  # "device", "user", "group", etc
    target_id = Column(String(64), nullable=True)  # ID of target if applicable (e.g. device hash_id)
    target_name = Column(String(255), nullable=True)  # Human readable name of target
    
    # These fields are stored as JSON but managed through the application
    recipients = Column(JSON)  # List of recipients or recipient types
    channels = Column(JSON)  # List of delivery channels
    
    priority = Column(Integer, default=3, index=True)  # 1 (highest) to 5 (lowest)
    status = Column(String(50), default="pending", index=True)  # "pending", "delivered", "failed", etc
    status_message = Column(Text, nullable=True)
    delivery_attempts = Column(Integer, default=0)
    last_attempt = Column(DateTime, nullable=True)
    
    # Read status (aggregate from recipients)
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime, nullable=True)
    
    # Additional metadata
    notification_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship to recipients
    recipients_details = relationship("NotificationRecipient", back_populates="notification",
                                      cascade="all, delete-orphan")
    
    def __init__(self, **kwargs):
        # Initialize JSON fields as empty lists/dicts if not provided
        if 'recipients' not in kwargs:
            kwargs['recipients'] = []
        if 'channels' not in kwargs:
            kwargs['channels'] = []
        if 'notification_metadata' not in kwargs:
            kwargs['notification_metadata'] = {}
            
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Notification {self.id} ({self.notification_type})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary for API responses"""
        try:
            logger.info(f"Converting notification {self.id} to dict")
            
            # Handle potentially None values or invalid values
            if self.notification_metadata is None or self.notification_metadata == 0:
                metadata = {}
            elif isinstance(self.notification_metadata, (dict, list)):
                metadata = self.notification_metadata
            else:
                # Force conversion to dict for any other type
                logger.warning(f"Notification {self.id} has non-dict metadata: {type(self.notification_metadata)}")
                metadata = {}
            
            # Legacy recipients and channels (kept for backward compatibility)
            old_recipients = [] if self.recipients is None else self.recipients
            old_channels = [] if self.channels is None else self.channels
            
            # Ensure recipients and channels are lists
            if not isinstance(old_recipients, list):
                old_recipients = [old_recipients] if old_recipients else []
            
            if not isinstance(old_channels, list):
                old_channels = [old_channels] if old_channels else []
            
            # Don't try to access the relationship directly - this can cause async issues
            # We'll let the API endpoints load the relationships properly when needed
            client_recipients = []
            
            logger.debug(f"Notification {self.id} metadata: {metadata}")
            logger.debug(f"Notification {self.id} legacy recipients: {old_recipients}")
            
            result = {
                "id": self.id,
                "notification_type": self.notification_type,
                "title": self.title,
                "content": self.content,
                "source": self.source,
                "source_id": self.source_id,
                "target_type": self.target_type,
                "target_id": self.target_id,
                "target_name": self.target_name,
                "recipients": old_recipients,  # Legacy field
                "channels": old_channels,      # Legacy field
                "client_recipients": client_recipients,  # This will be populated by the API endpoint if needed
                "priority": self.priority,
                "status": self.status if hasattr(self, "status") else "pending",
                "status_message": self.status_message,
                "delivery_attempts": self.delivery_attempts if hasattr(self, "delivery_attempts") else 0,
                "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
                "is_read": self.is_read if hasattr(self, "is_read") else False,
                "read_at": self.read_at.isoformat() if hasattr(self, "read_at") and self.read_at else None,
                "notification_metadata": metadata,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat()
            }
            
            return result
        except Exception as e:
            logger.error(f"Error in to_dict for notification {self.id}: {str(e)}", exc_info=True)
            # Return a minimal dict that won't break things
            return {
                "id": self.id,
                "title": getattr(self, "title", "Unknown"),
                "content": getattr(self, "content", ""),
                "notification_type": getattr(self, "notification_type", "info"),
                "source": getattr(self, "source", "system"),
                "priority": getattr(self, "priority", 3),
                "status": getattr(self, "status", "pending"),
                "status_message": getattr(self, "status_message", ""),
                "delivery_attempts": getattr(self, "delivery_attempts", 0),
                "is_read": getattr(self, "is_read", False),
                "recipients": [],
                "channels": [],
                "client_recipients": [],
                "created_at": self.created_at.isoformat() if hasattr(self, "created_at") and self.created_at else datetime.utcnow().isoformat(),
                "updated_at": self.updated_at.isoformat() if hasattr(self, "updated_at") and self.updated_at else datetime.utcnow().isoformat(),
                "notification_metadata": {},
                "error": "Error serializing complete notification"
            }

class NotificationRecipient(Base):
    """Junction table linking notifications to client recipients"""
    __tablename__ = "notification_recipients"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id", ondelete="CASCADE"), index=True)
    client_id = Column(String(50), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    delivery_channel = Column(String(50), default="in_app")  # in_app, email, sms, etc.
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    is_delivered = Column(Boolean, default=False)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships - using string-based references to avoid circular imports
    notification = relationship("Notification", back_populates="recipients_details", lazy="selectin")
    client = relationship("Client", foreign_keys=[client_id], lazy="selectin")
    
    def __repr__(self):
        return f"<NotificationRecipient {self.id} (notification={self.notification_id}, client={self.client_id})>" 