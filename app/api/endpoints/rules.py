"""Rule management API endpoints"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.rule_service import RuleService
from app.api.schemas import ResponseModel

router = APIRouter()

@router.get("/", response_model=ResponseModel)
async def list_rules(
    db: AsyncSession = Depends(get_db)
):
    """List all rules"""
    rule_service = RuleService(db)
    rules = await rule_service.list_rules()
    return ResponseModel(
        status="success",
        message="Rules retrieved",
        data={
            "total": len(rules),
            "rules": rules
        }
    )

@router.post("/", response_model=ResponseModel)
async def create_rule(
    rule_data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Create a new rule"""
    rule_service = RuleService(db)
    result = await rule_service.create_rule(rule_data)
    
    if not result.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to create rule")
        )
    
    return ResponseModel(
        status="success",
        message="Rule created",
        data=result.get("rule")
    )

@router.get("/{rule_id}", response_model=ResponseModel)
async def get_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a rule by ID"""
    rule_service = RuleService(db)
    rule = await rule_service.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    return ResponseModel(
        status="success",
        message="Rule details retrieved",
        data=rule
    )

@router.put("/{rule_id}", response_model=ResponseModel)
async def update_rule(
    rule_id: int,
    rule_data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Update a rule"""
    rule_service = RuleService(db)
    result = await rule_service.update_rule(rule_id, rule_data)
    
    if not result.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in result.get("error", "") else status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to update rule")
        )
    
    return ResponseModel(
        status="success",
        message="Rule updated",
        data=result.get("rule")
    )

@router.delete("/{rule_id}", response_model=ResponseModel)
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a rule"""
    rule_service = RuleService(db)
    result = await rule_service.delete_rule(rule_id)
    
    if not result.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", f"Rule {rule_id} not found")
        )
    
    return ResponseModel(
        status="success",
        message=f"Rule {rule_id} deleted",
        data=None
    )

@router.post("/{rule_id}/enable", response_model=ResponseModel)
async def enable_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Enable a rule"""
    rule_service = RuleService(db)
    result = await rule_service.enable_rule(rule_id)
    
    if not result.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", f"Rule {rule_id} not found")
        )
    
    return ResponseModel(
        status="success",
        message=f"Rule {rule_id} enabled",
        data=result.get("rule")
    )

@router.post("/{rule_id}/disable", response_model=ResponseModel)
async def disable_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Disable a rule"""
    rule_service = RuleService(db)
    result = await rule_service.disable_rule(rule_id)
    
    if not result.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", f"Rule {rule_id} not found")
        )
    
    return ResponseModel(
        status="success",
        message=f"Rule {rule_id} disabled",
        data=result.get("rule")
    )

@router.post("/apply", response_model=ResponseModel)
async def apply_all_rules(
    db: AsyncSession = Depends(get_db)
):
    """Apply all enabled rules to all applicable devices"""
    rule_service = RuleService(db)
    result = await rule_service.apply_all_rules()
    
    return ResponseModel(
        status="success",
        message="All rules applied",
        data=result
    )

@router.post("/device/{device_id}/apply", response_model=ResponseModel)
async def apply_rules_to_device(
    device_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Apply all enabled rules to a specific device"""
    rule_service = RuleService(db)
    result = await rule_service.apply_rules_to_device(device_id)
    
    if not result.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", f"Device {device_id} not found")
        )
    
    return ResponseModel(
        status="success",
        message=f"Rules applied to device {device_id}",
        data=result
    )

@router.post("/cancel", response_model=ResponseModel)
async def cancel_all_executions(
    db: AsyncSession = Depends(get_db)
):
    """Cancel all active rule executions"""
    rule_service = RuleService(db)
    result = await rule_service.cancel_execution()
    
    return ResponseModel(
        status="success",
        message="Rule executions cancelled",
        data=result
    )

@router.post("/cancel/{execution_id}", response_model=ResponseModel)
async def cancel_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Cancel a specific rule execution"""
    rule_service = RuleService(db)
    result = await rule_service.cancel_execution(execution_id)
    
    if not result.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", f"Execution {execution_id} not found")
        )
    
    return ResponseModel(
        status="success",
        message=f"Execution {execution_id} cancelled",
        data=None
    )

@router.get("/executions", response_model=ResponseModel)
async def get_active_executions(
    db: AsyncSession = Depends(get_db)
):
    """Get information about active rule executions"""
    rule_service = RuleService(db)
    result = await rule_service.get_active_executions()
    
    return ResponseModel(
        status="success",
        message="Active executions retrieved",
        data=result.get("active_executions", {})
    ) 