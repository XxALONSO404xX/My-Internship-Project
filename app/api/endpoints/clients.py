"""API endpoints for client management"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import schemas
from app.models.database import get_db
from app.services.client_service import ClientService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[Dict[str, Any]])
async def get_clients(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Get all clients with pagination"""
    try:
        client_service = ClientService(db)
        clients = await client_service.get_all_clients(limit=limit, offset=offset)
        return client_service.format_clients_response(clients)
    except Exception as e:
        logger.error(f"Error retrieving clients: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving clients: {str(e)}")

@router.post("/", response_model=Dict[str, Any])
async def create_client(
    client_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Create a new client"""
    try:
        client_service = ClientService(db)
        
        # Check for existing client with same username or email
        if "username" in client_data:
            existing_username = await client_service.get_client_by_username(client_data["username"])
            if existing_username:
                raise HTTPException(status_code=400, detail="Username already exists")
        
        if "email" in client_data:
            existing_email = await client_service.get_client_by_email(client_data["email"])
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already exists")
        
        # Create client
        client = await client_service.create_client(
            username=client_data.get("username"),
            email=client_data.get("email"),
            password_hash=client_data.get("password_hash", "dummy_hash"),
            is_active=client_data.get("is_active", True),
            preferences=client_data.get("preferences", {}),
            client_id=client_data.get("id")
        )
        
        return client_service.format_client_response(client)
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error creating client: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating client: {str(e)}")

@router.get("/{client_id}", response_model=Dict[str, Any])
async def get_client_by_id(
    client_id: str = Path(..., title="The Client ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific client by ID"""
    try:
        client_service = ClientService(db)
        client = await client_service.get_client_by_id(client_id)
        
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        return client_service.format_client_response(client)
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving client: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving client: {str(e)}")


@router.put("/{client_id}", response_model=Dict[str, Any])
async def update_client(
    client_data: Dict[str, Any],
    client_id: str = Path(..., title="The Client ID"),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing client"""
    try:
        client_service = ClientService(db)
        
        # Check if client exists
        existing_client = await client_service.get_client_by_id(client_id)
        if not existing_client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Update client
        updated_client = await client_service.update_client(
            client_id=client_id,
            username=client_data.get("username"),
            email=client_data.get("email"),
            password_hash=client_data.get("password_hash"),
            is_active=client_data.get("is_active"),
            preferences=client_data.get("preferences")
        )
        
        return client_service.format_client_response(updated_client)
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error updating client: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating client: {str(e)}")


@router.delete("/{client_id}", response_model=Dict[str, Any])
async def delete_client(
    client_id: str = Path(..., title="The Client ID"),
    db: AsyncSession = Depends(get_db)
):
    """Delete a client"""
    try:
        client_service = ClientService(db)
        
        # Delete client
        result = await client_service.delete_client(client_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Client not found")
        
        return {"success": True, "message": "Client deleted successfully"}
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error deleting client: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting client: {str(e)}")


@router.post("/test-clients", response_model=Dict[str, Any])
async def create_test_clients(
    count: int = Query(5, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Create test clients for development purposes"""
    try:
        client_service = ClientService(db)
        created_clients = await client_service.create_test_clients(count)
        
        if created_clients:
            return {
                "message": f"Created {len(created_clients)} test clients", 
                "clients": client_service.format_clients_response(created_clients)
            }
        else:
            return {"message": "No new clients needed, test clients already exist"}
    
    except Exception as e:
        logger.error(f"Error creating test clients: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating test clients: {str(e)}") 