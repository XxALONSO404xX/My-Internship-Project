from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Text, func
from sqlalchemy.orm import relationship

from app.models.database import Base

class Client(Base):
    """Model for client accounts in the system"""
    __tablename__ = "clients"

    id = Column(String(50), primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # Email verification status
    verification_date = Column(DateTime, nullable=True)  # When email was verified
    preferences = Column(JSON, server_default='{}')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    
    # Relationship to tokens - using string-based reference to avoid circular imports
    tokens = relationship("Token", backref="client", cascade="all, delete", lazy="selectin")
    
    # Relationship to refresh tokens for desktop app support
    refresh_tokens = relationship("RefreshToken", back_populates="client", cascade="all, delete", lazy="selectin")
    
    # Relationship to notifications through the junction table
    notifications = relationship("NotificationRecipient", back_populates="client", lazy="selectin")
    
    def __repr__(self):
        return f"<Client {self.id} ({self.username})>"
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert client to dictionary for API responses"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None
        } 