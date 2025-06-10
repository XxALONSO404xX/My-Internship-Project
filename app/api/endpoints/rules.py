"""Rule management API endpoints"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.models.database import get_db
from app.services.rule_service import RuleService
from app.services.messaging_service import NotificationService
from app.api.schemas import RuleCreate, RuleUpdate, RuleResponse, RuleEvaluationResponse, RuleData
from app.api.deps import get_current_client

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=RuleResponse)
async def list_rules(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """List all rules"""
    rule_service = RuleService(db)
    result = await rule_service.list_rules()
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )
    
    return RuleResponse(
        status=result["status"],
        message=result["message"],
        data=result["data"],
        errors=result["errors"]
    )

@router.post("/", response_model=RuleResponse)
async def create_rule(
    rule_data: RuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Create a new rule"""
    rule_service = RuleService(db)
    result = await rule_service.create_rule(rule_data.dict())
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    # Dispatch creation notifications via WebSocket and Email
    try:
        notif = NotificationService(db)
        await notif.create_notification(
            title=f"Rule '{result['data']['name']}' Created",
            content=result['message'],
            notification_type='info',
            source='rule',
            source_id=result['data']['id'],
            target_type='rule',
            target_id=result['data']['id'],
            target_name=result['data']['name'],
            channels=['websocket','email'],
            recipients=[current_user.email]
        )
    except Exception as e:
        logger.error(f"Failed to send creation notification: {str(e)}")
    
    return RuleResponse(
        status=result["status"],
        message=result["message"],
        data=result["data"],
        errors=result["errors"]
    )

@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Get a rule by ID"""
    rule_service = RuleService(db)
    result = await rule_service.get_rule(rule_id)
    
    if result["status"] == "error":
        status_code = status.HTTP_404_NOT_FOUND if "not found" in result["message"].lower() else status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail=result["message"]
        )
    
    return RuleResponse(
        status=result["status"],
        message=result["message"],
        data=result["data"],
        errors=result["errors"]
    )

@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int,
    rule_data: RuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Update a rule"""
    rule_service = RuleService(db)
    result = await rule_service.update_rule(rule_id, rule_data.dict(exclude_unset=True))
    
    if result["status"] == "error":
        status_code = status.HTTP_404_NOT_FOUND if "not found" in result["message"].lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=result["message"]
        )
    
    return RuleResponse(
        status=result["status"],
        message=result["message"],
        data=result["data"],
        errors=result["errors"]
    )

@router.delete("/{rule_id}", response_model=RuleResponse)
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Delete a rule"""
    rule_service = RuleService(db)
    result = await rule_service.delete_rule(rule_id)
    
    if result["status"] == "error":
        status_code = status.HTTP_404_NOT_FOUND if "not found" in result["message"].lower() else status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail=result["message"]
        )
    
    return RuleResponse(
        status=result["status"],
        message=result["message"],
        data=result["data"],
        errors=result["errors"]
    )

@router.post("/{rule_id}/enable", response_model=RuleResponse)
async def enable_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Enable a rule"""
    rule_service = RuleService(db)
    result = await rule_service.enable_rule(rule_id)
    
    if result["status"] == "error":
        status_code = status.HTTP_404_NOT_FOUND if "not found" in result["message"].lower() else status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail=result["message"]
        )
    
    return RuleResponse(
        status=result["status"],
        message=result["message"],
        data=result["data"],
        errors=result["errors"]
    )

@router.post("/{rule_id}/disable", response_model=RuleResponse)
async def disable_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Disable a rule"""
    rule_service = RuleService(db)
    result = await rule_service.disable_rule(rule_id)
    
    if result["status"] == "error":
        status_code = status.HTTP_404_NOT_FOUND if "not found" in result["message"].lower() else status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail=result["message"]
        )
    
    return RuleResponse(
        status=result["status"],
        message=result["message"],
        data=result["data"],
        errors=result["errors"]
    )

@router.post("/apply", response_model=RuleResponse)
async def apply_all_rules(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Apply all enabled rules to all applicable devices"""
    rule_service = RuleService(db)
    result = await rule_service.apply_all_rules()
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )
    
    return RuleResponse(
        status=result["status"],
        message=result["message"],
        data=result["data"],
        errors=result["errors"]
    )

@router.post("/device/{device_id}/apply", response_model=RuleResponse)
async def apply_rules_to_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Apply all enabled rules to a specific device"""
    rule_service = RuleService(db)
    result = await rule_service.apply_rules_to_device(device_id)
    
    if result["status"] == "error":
        status_code = status.HTTP_404_NOT_FOUND if "not found" in result["message"].lower() else status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail=result["message"]
        )
    
    return RuleResponse(
        status=result["status"],
        message=result["message"],
        data=result["data"],
        errors=result["errors"]
    )

@router.post("/cancel", response_model=RuleResponse)
async def cancel_all_executions(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Cancel all active rule executions"""
    rule_service = RuleService(db)
    result = await rule_service.cancel_execution()
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )
    
    return RuleResponse(
        status=result["status"],
        message=result["message"],
        data=result["data"],
        errors=result["errors"]
    )

@router.post("/cancel/{execution_id}", response_model=RuleResponse)
async def cancel_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Cancel a specific rule execution"""
    rule_service = RuleService(db)
    result = await rule_service.cancel_execution(execution_id)
    
    if result["status"] == "error":
        status_code = status.HTTP_404_NOT_FOUND if "not found" in result["message"].lower() else status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail=result["message"]
        )
    
    return RuleResponse(
        status=result["status"],
        message=result["message"],
        data=result["data"],
        errors=result["errors"]
    )

@router.get("/executions", response_model=RuleResponse)
async def get_active_executions(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """Get information about active rule executions"""
    rule_service = RuleService(db)
    result = await rule_service.get_active_executions()
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )
    
    return RuleResponse(
        status=result["status"],
        message=result["message"],
        data=result["data"],
        errors=result["errors"]
    ) 