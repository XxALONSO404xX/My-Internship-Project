"""Token service for handling email verification and password reset tokens"""
import logging
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token import Token
from app.models.client import Client

logger = logging.getLogger(__name__)

class TokenService:
    """Service for handling verification and reset tokens"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_verification_token(self, client: Client) -> Token:
        """
        Create a verification token for a client
        
        Args:
            client: Client to create token for
            
        Returns:
            Token: Created token
        """
        # Check for existing verification tokens and invalidate them
        await self._invalidate_existing_tokens(client.id, "verification")
        
        # Create new token
        token = Token.generate_verification_token(client_id=client.id)
        
        # Save token to database
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)
        
        logger.info(f"Created verification token for client {client.id}")
        return token
    
    async def create_reset_token(self, client: Client) -> Token:
        """
        Create a password reset token for a client
        
        Args:
            client: Client to create token for
            
        Returns:
            Token: Created token
        """
        # Check for existing reset tokens and invalidate them
        await self._invalidate_existing_tokens(client.id, "reset")
        
        # Create new token
        token = Token.generate_reset_token(client_id=client.id)
        
        # Save token to database
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)
        
        logger.info(f"Created password reset token for client {client.id}")
        return token
    
    async def verify_token(self, token_value: str, token_type: str) -> Tuple[bool, Optional[Client], Optional[str]]:
        """
        Verify a token and return the associated client
        
        Args:
            token_value: Token value to verify
            token_type: Type of token (verification or reset)
            
        Returns:
            Tuple containing:
            - Boolean indicating if token is valid
            - Associated Client object or None if invalid
            - Error message or None if valid
        """
        # Find token
        query = select(Token).where(Token.token == token_value, Token.token_type == token_type)
        result = await self.db.execute(query)
        token = result.scalars().first()
        
        # Check if token exists
        if not token:
            return False, None, "Token not found"
        
        # Check if token is expired
        if token.is_expired():
            return False, None, "Token expired"
        
        # Check if token is already used
        if token.is_used:
            return False, None, "Token already used"
        
        # Get associated client
        client_query = select(Client).where(Client.id == token.client_id)
        client_result = await self.db.execute(client_query)
        client = client_result.scalars().first()
        
        if not client:
            return False, None, "Associated client not found"
        
        return True, client, None
    
    async def mark_token_used(self, token_value: str) -> bool:
        """
        Mark a token as used
        
        Args:
            token_value: Token to mark as used
            
        Returns:
            Boolean indicating success
        """
        query = update(Token).where(Token.token == token_value).values(is_used=True)
        await self.db.execute(query)
        await self.db.commit()
        return True
    
    async def mark_client_verified(self, client_id: str) -> bool:
        """
        Mark a client as verified
        
        Args:
            client_id: ID of client to verify
            
        Returns:
            Boolean indicating success
        """
        query = update(Client).where(Client.id == client_id).values(
            is_verified=True,
            verification_date=datetime.utcnow()
        )
        await self.db.execute(query)
        await self.db.commit()
        logger.info(f"Marked client {client_id} as verified")
        return True
    
    async def _invalidate_existing_tokens(self, client_id: str, token_type: str) -> None:
        """
        Invalidate existing tokens for a client
        
        Args:
            client_id: Client ID
            token_type: Type of token to invalidate
        """
        # Mark existing tokens as used
        query = update(Token).where(
            Token.client_id == client_id,
            Token.token_type == token_type,
            Token.is_used == False
        ).values(is_used=True)
        
        await self.db.execute(query)
        await self.db.commit()
        
    async def clean_expired_tokens(self) -> int:
        """
        Clean expired tokens from database
        
        Returns:
            Number of tokens deleted
        """
        now = datetime.utcnow()
        query = delete(Token).where(Token.expires_at < now)
        result = await self.db.execute(query)
        await self.db.commit()
        
        count = result.rowcount
        if count > 0:
            logger.info(f"Cleaned {count} expired tokens")
        return count 