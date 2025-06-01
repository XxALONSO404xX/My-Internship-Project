"""Refresh token model for desktop application support"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.database import Base

logger = logging.getLogger(__name__)

class RefreshToken(Base):
    """Refresh token model for extended desktop application sessions"""
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    token = Column(String, unique=True, index=True, nullable=False)
    client_id = Column(String, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    device_info = Column(String, nullable=True)  # Store desktop device information
    
    # Relationship
    client = relationship("Client", back_populates="refresh_tokens")
    
    @classmethod
    def generate_token(cls, client_id: str, expires_delta: Optional[timedelta] = None, device_info: Optional[str] = None) -> "RefreshToken":
        """Generate a refresh token for a client"""
        if expires_delta is None:
            # Default to 30 days for refresh tokens
            expires_delta = timedelta(days=30)
        
        expires_at = datetime.utcnow() + expires_delta
        token_value = str(uuid.uuid4())
        
        return cls(
            id=str(uuid.uuid4()),
            token=token_value,
            client_id=client_id,
            expires_at=expires_at,
            device_info=device_info
        )
    
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)"""
        return not self.is_expired() and not self.revoked
    
    def revoke(self) -> None:
        """Revoke the token"""
        self.revoked = True
