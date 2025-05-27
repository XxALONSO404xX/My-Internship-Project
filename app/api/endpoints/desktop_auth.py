"""Desktop application authentication endpoints for IoT platform"""
import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from app.models.database import get_db
from app.models.client import Client
from app.services.auth_service import AuthService
from app.services.refresh_token_service import create_refresh_token_service, RefreshTokenService
from app.api.schemas import ClientLogin, TokenResponse, RefreshTokenRequest, Token
from app.api.deps import get_current_client
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/desktop/login", response_model=TokenResponse)
async def desktop_login(
    login_data: ClientLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Desktop application login with extended session support
    Returns both access token and refresh token
    """
    auth_service = AuthService(db)
    refresh_token_service = create_refresh_token_service(db)
    
    # Authenticate client
    client = await auth_service.authenticate_client(login_data.username, login_data.password)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": client.id},
        expires_delta=access_token_expires
    )
    
    # Create refresh token if remember_me is enabled
    refresh_token = None
    refresh_token_expires_at = None
    
    if login_data.remember_me:
        # Longer expiry for desktop app (30 days by default)
        refresh_token_expires = timedelta(days=30)
        refresh_token_obj = await refresh_token_service.create_refresh_token(
            client=client,
            expires_delta=refresh_token_expires,
            device_info=login_data.device_info
        )
        refresh_token = refresh_token_obj.token
        refresh_token_expires_at = refresh_token_obj.expires_at
    
    # Return token and user info
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token if refresh_token else "",
        expires_at=refresh_token_expires_at if refresh_token_expires_at else None,
        client={
            "id": client.id,
            "username": client.username,
            "email": client.email,
            "is_active": client.is_active,
            "preferences": client.preferences
        }
    )

@router.post("/desktop/refresh", response_model=Token)
async def refresh_access_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Use a refresh token to get a new access token when the old one expires
    """
    refresh_token_service = create_refresh_token_service(db)
    auth_service = AuthService(db)
    
    # Validate the refresh token
    is_valid, client, error_message = await refresh_token_service.validate_refresh_token(
        refresh_request.refresh_token
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_message or "Invalid refresh token"
        )
    
    # Create a new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": client.id},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")

@router.post("/desktop/logout", response_model=Dict[str, Any])
async def desktop_logout(
    refresh_request: RefreshTokenRequest,
    current_client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout from the desktop application
    Revokes the refresh token so it can't be used again
    """
    refresh_token_service = create_refresh_token_service(db)
    
    # Revoke the refresh token if provided
    if refresh_request.refresh_token:
        await refresh_token_service.revoke_token(refresh_request.refresh_token)
    
    return {
        "status": "success",
        "message": "Successfully logged out"
    }

@router.post("/desktop/logout-all-devices", response_model=Dict[str, Any])
async def logout_all_devices(
    current_client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout from all devices
    Revokes all refresh tokens for the client
    """
    refresh_token_service = create_refresh_token_service(db)
    
    # Revoke all refresh tokens for the client
    tokens_revoked = await refresh_token_service.revoke_all_tokens_for_client(current_client.id)
    
    return {
        "status": "success",
        "message": f"Successfully logged out from all devices",
        "tokens_revoked": tokens_revoked
    }
