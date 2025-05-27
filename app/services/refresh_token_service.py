"""Refresh token service for desktop application support"""
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.models.client import Client

logger = logging.getLogger(__name__)

class RefreshTokenService:
    """Service for handling refresh tokens for desktop applications"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_refresh_token(
        self, 
        client: Client, 
        expires_delta: Optional[timedelta] = None,
        device_info: Optional[str] = None
    ) -> RefreshToken:
        """
        Create a refresh token for a client
        
        Args:
            client: Client to create token for
            expires_delta: Optional expiration time delta
            device_info: Optional device information
            
        Returns:
            RefreshToken: Created token
        """
        # Create new token
        token = RefreshToken.generate_token(
            client_id=client.id,
            expires_delta=expires_delta,
            device_info=device_info
        )
        
        # Save token to database
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)
        
        logger.info(f"Created refresh token for client {client.id}")
        return token
    
    async def validate_refresh_token(self, token_value: str) -> Tuple[bool, Optional[Client], Optional[str]]:
        """
        Validate a refresh token and return the associated client
        
        Args:
            token_value: Token value to verify
            
        Returns:
            Tuple containing:
            - Boolean indicating if token is valid
            - Associated Client object or None if invalid
            - Error message or None if valid
        """
        # Find token
        query = select(RefreshToken).where(RefreshToken.token == token_value)
        result = await self.db.execute(query)
        token = result.scalars().first()
        
        # Check if token exists
        if not token:
            return False, None, "Refresh token not found"
        
        # Check if token is expired
        if token.is_expired():
            await self.revoke_token(token.token)
            return False, None, "Refresh token expired"
        
        # Check if token is revoked
        if token.revoked:
            return False, None, "Refresh token revoked"
        
        # Get associated client
        client_query = select(Client).where(Client.id == token.client_id)
        client_result = await self.db.execute(client_query)
        client = client_result.scalars().first()
        
        # Check if client exists
        if not client:
            await self.revoke_token(token.token)
            return False, None, "Associated client not found"
        
        # Check if client is active
        if not client.is_active:
            await self.revoke_token(token.token)
            return False, None, "Client account is inactive"
        
        return True, client, None
    
    async def revoke_token(self, token_value: str) -> bool:
        """
        Revoke a refresh token
        
        Args:
            token_value: Token value to revoke
            
        Returns:
            Boolean indicating if token was successfully revoked
        """
        query = update(RefreshToken).where(
            RefreshToken.token == token_value
        ).values(
            revoked=True
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        
        if result.rowcount > 0:
            logger.info(f"Revoked refresh token {token_value}")
            return True
        
        return False
    
    async def revoke_all_tokens_for_client(self, client_id: str) -> int:
        """
        Revoke all refresh tokens for a client
        
        Args:
            client_id: Client ID to revoke tokens for
            
        Returns:
            Number of tokens revoked
        """
        query = update(RefreshToken).where(
            RefreshToken.client_id == client_id,
            RefreshToken.revoked == False
        ).values(
            revoked=True
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        
        logger.info(f"Revoked {result.rowcount} refresh tokens for client {client_id}")
        return result.rowcount
    
    async def purge_expired_tokens(self) -> int:
        """
        Delete expired and revoked tokens from the database
        
        Returns:
            Number of tokens deleted
        """
        query = delete(RefreshToken).where(
            (RefreshToken.expires_at < datetime.utcnow()) |
            (RefreshToken.revoked == True)
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        
        logger.info(f"Purged {result.rowcount} expired or revoked refresh tokens")
        return result.rowcount


def create_refresh_token_service(db: AsyncSession) -> RefreshTokenService:
    """Factory function to create a refresh token service instance"""
    return RefreshTokenService(db)
