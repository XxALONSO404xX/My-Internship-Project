"""Token model for password reset and email verification"""
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, func

from app.models.database import Base

class Token(Base):
    """Token model for email verification and password reset"""
    __tablename__ = "tokens"
    
    token = Column(String(120), primary_key=True, index=True)
    client_id = Column(String(50), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    token_type = Column(String(20), index=True)  # "verification" or "reset"
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    token_metadata = Column(Text, nullable=True)  # For storing additional data as JSON
    
    def __repr__(self):
        return f"<Token {self.token[:10]}... ({self.token_type})>"
    
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary for API responses"""
        return {
            "token": self.token,
            "client_id": self.client_id,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat(),
            "is_used": self.is_used,
            "created_at": self.created_at.isoformat()
        }
    
    @staticmethod
    def generate_token(length: int = 64) -> str:
        """Generate a random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_verification_token(client_id: str, expires_in_hours: int = 24) -> "Token":
        """Generate a verification token for the given client"""
        token_value = Token.generate_token()
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        return Token(
            token=token_value,
            client_id=client_id,
            token_type="verification",
            expires_at=expires_at
        )
    
    @staticmethod
    def generate_reset_token(client_id: str, expires_in_hours: int = 1) -> "Token":
        """Generate a password reset token for the given client"""
        token_value = Token.generate_token()
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        return Token(
            token=token_value,
            client_id=client_id,
            token_type="reset",
            expires_at=expires_at
        ) 