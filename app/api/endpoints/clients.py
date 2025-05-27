"""API endpoints for client management"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from app.models.client import Client
from app.models.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/")
async def get_clients(
    db: AsyncSession = Depends(get_db)
):
    """Get all clients"""
    query = select(Client)
    result = await db.execute(query)
    clients = result.scalars().all()
    return [client.to_dict() for client in clients]

@router.post("/")
async def create_client(
    client_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Create a new client"""
    try:
        client = Client(
            id=client_data.get("id"),
            username=client_data.get("username"),
            email=client_data.get("email"),
            password_hash=client_data.get("password_hash", "dummy_hash"),
            is_active=client_data.get("is_active", True),
            preferences=client_data.get("preferences", {})
        )
        
        db.add(client)
        await db.commit()
        await db.refresh(client)
        
        return client.to_dict()
    except Exception as e:
        logger.error(f"Error creating client: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating client: {str(e)}")

@router.post("/test-clients")
async def create_test_clients(
    db: AsyncSession = Depends(get_db)
):
    """Create test clients for development purposes"""
    try:
        clients = []
        for i in range(1, 6):
            client_id = str(i)
            # Check if client already exists
            query = select(Client).where(Client.id == client_id)
            result = await db.execute(query)
            existing = result.scalar_one_or_none()
            
            if not existing:
                client = Client(
                    id=client_id,
                    username=f"test_user_{i}",
                    email=f"user{i}@example.com",
                    password_hash="dummy_hash",
                    is_active=True,
                    preferences={"theme": "light"}
                )
                db.add(client)
                clients.append(client)
        
        if clients:
            await db.commit()
            for client in clients:
                await db.refresh(client)
            
            return {"message": f"Created {len(clients)} test clients", "clients": [client.to_dict() for client in clients]}
        else:
            return {"message": "No new clients needed, test clients already exist"}
    
    except Exception as e:
        logger.error(f"Error creating test clients: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating test clients: {str(e)}") 