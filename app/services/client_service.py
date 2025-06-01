"""
Client management service for handling user/client operations
"""
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from app.models.client import Client
from app.services.activity_service import ActivityService

logger = logging.getLogger(__name__)

class ClientService:
    """Service for managing client accounts and operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.activity_service = ActivityService(db)
    
    async def get_all_clients(self, limit: int = 100, offset: int = 0) -> List[Client]:
        """
        Retrieve all clients with pagination
        
        Args:
            limit: Maximum number of clients to return
            offset: Number of clients to skip
            
        Returns:
            List of Client objects
        """
        query = select(Client).order_by(Client.username).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_client_by_id(self, client_id: str) -> Optional[Client]:
        """
        Get a client by ID
        
        Args:
            client_id: The client's unique identifier
            
        Returns:
            Client object if found, None otherwise
        """
        return await self.db.get(Client, client_id)
    
    async def get_client_by_username(self, username: str) -> Optional[Client]:
        """
        Get a client by username
        
        Args:
            username: The client's username
            
        Returns:
            Client object if found, None otherwise
        """
        query = select(Client).where(Client.username == username)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_client_by_email(self, email: str) -> Optional[Client]:
        """
        Get a client by email address
        
        Args:
            email: The client's email address
            
        Returns:
            Client object if found, None otherwise
        """
        query = select(Client).where(Client.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_client(self, 
                           username: str, 
                           email: str,
                           password_hash: str,
                           is_active: bool = True,
                           preferences: Dict[str, Any] = None,
                           client_id: Optional[str] = None) -> Client:
        """
        Create a new client
        
        Args:
            username: Client username
            email: Client email
            password_hash: Hashed password
            is_active: Whether the client is active
            preferences: Client preferences
            client_id: Optional client ID, generated if not provided
            
        Returns:
            Created Client object
        """
        # Generate ID if not provided
        if not client_id:
            client_id = str(uuid.uuid4())
            
        # Set default preferences if none
        if preferences is None:
            preferences = {"theme": "light"}
            
        # Create client object
        client = Client(
            id=client_id,
            username=username,
            email=email,
            password_hash=password_hash,
            is_active=is_active,
            preferences=preferences,
            created_at=datetime.utcnow()
        )
        
        # Add to database
        self.db.add(client)
        await self.db.commit()
        await self.db.refresh(client)
        
        # Log activity
        await self.activity_service.log_activity(
            activity_type="client_created",
            description=f"Client created: {username}",
            source="client_service",
            source_id=client_id,
            severity=2,
            metadata={
                "client_id": client_id,
                "email": email
            }
        )
        
        return client
    
    async def update_client(self, 
                           client_id: str,
                           username: Optional[str] = None,
                           email: Optional[str] = None,
                           password_hash: Optional[str] = None,
                           is_active: Optional[bool] = None,
                           preferences: Optional[Dict[str, Any]] = None) -> Optional[Client]:
        """
        Update an existing client
        
        Args:
            client_id: The client's ID
            username: New username
            email: New email
            password_hash: New password hash
            is_active: New active status
            preferences: New preferences
            
        Returns:
            Updated Client object if found, None otherwise
        """
        # Get client
        client = await self.get_client_by_id(client_id)
        if not client:
            return None
            
        # Update fields
        if username is not None:
            client.username = username
        if email is not None:
            client.email = email
        if password_hash is not None:
            client.password_hash = password_hash
        if is_active is not None:
            client.is_active = is_active
        if preferences is not None:
            client.preferences = preferences
            
        client.updated_at = datetime.utcnow()
        
        # Save changes
        await self.db.commit()
        await self.db.refresh(client)
        
        # Log activity
        await self.activity_service.log_activity(
            activity_type="client_updated",
            description=f"Client updated: {client.username}",
            source="client_service",
            source_id=client_id,
            severity=2,
            metadata={
                "client_id": client_id,
                "fields_updated": {
                    "username": username is not None,
                    "email": email is not None,
                    "password": password_hash is not None,
                    "is_active": is_active is not None,
                    "preferences": preferences is not None
                }
            }
        )
        
        return client
    
    async def delete_client(self, client_id: str) -> bool:
        """
        Delete a client
        
        Args:
            client_id: The client's ID
            
        Returns:
            True if client was deleted, False otherwise
        """
        client = await self.get_client_by_id(client_id)
        if not client:
            return False
            
        # Get client data for activity log
        client_username = client.username
        
        # Delete client
        await self.db.delete(client)
        await self.db.commit()
        
        # Log activity
        await self.activity_service.log_activity(
            activity_type="client_deleted",
            description=f"Client deleted: {client_username}",
            source="client_service",
            source_id=client_id,
            severity=3,
            metadata={
                "client_id": client_id,
                "username": client_username
            }
        )
        
        return True
    
    async def update_client_preferences(self, client_id: str, preferences: Dict[str, Any]) -> Optional[Client]:
        """
        Update client preferences
        
        Args:
            client_id: The client's ID
            preferences: New preferences to merge with existing
            
        Returns:
            Updated Client object if found, None otherwise
        """
        client = await self.get_client_by_id(client_id)
        if not client:
            return None
            
        # Merge preferences
        current_prefs = client.preferences or {}
        updated_prefs = {**current_prefs, **preferences}
        
        # Update client
        client.preferences = updated_prefs
        client.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(client)
        
        return client
    
    async def create_test_clients(self, count: int = 5) -> List[Client]:
        """
        Create test clients for development purposes
        
        Args:
            count: Number of test clients to create
            
        Returns:
            List of created Client objects
        """
        clients = []
        
        for i in range(1, count + 1):
            client_id = str(i)
            # Check if client already exists
            existing = await self.get_client_by_id(client_id)
            
            if not existing:
                client = await self.create_client(
                    client_id=client_id,
                    username=f"test_user_{i}",
                    email=f"user{i}@example.com",
                    password_hash="dummy_hash",
                    is_active=True,
                    preferences={"theme": "light"}
                )
                clients.append(client)
        
        return clients
        
    def format_client_response(self, client: Client) -> Dict[str, Any]:
        """
        Format a client object for API response
        
        Args:
            client: Client object to format
            
        Returns:
            Formatted client dictionary
        """
        return {
            "id": client.id,
            "username": client.username,
            "email": client.email,
            "is_active": client.is_active,
            "preferences": client.preferences,
            "created_at": client.created_at.isoformat() if client.created_at else None,
            "updated_at": client.updated_at.isoformat() if client.updated_at else None,
            # Don't include password_hash in response
        }
    
    def format_clients_response(self, clients: List[Client]) -> List[Dict[str, Any]]:
        """
        Format a list of client objects for API response
        
        Args:
            clients: List of Client objects to format
            
        Returns:
            List of formatted client dictionaries
        """
        return [self.format_client_response(client) for client in clients]


def create_client_service(db: AsyncSession) -> ClientService:
    """Factory function to create a client service instance"""
    return ClientService(db)
