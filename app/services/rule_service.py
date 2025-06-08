"""Rule Service for IoT Management Platform"""
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json
import random
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, desc

from app.services.device_management_service import DeviceService
from app.services.messaging_service import NotificationService
from app.services.websocket_service import publish_event
from app.models.rule import Rule
from app.models.sensor_reading import SensorReading
from app.api.schemas import RuleCreate, RuleUpdate, RuleAction, RuleCondition

logger = logging.getLogger(__name__)

class RuleService:
    """Service for managing device rules"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.device_service = DeviceService(db)
        self.notification_service = NotificationService(db)
        # Track active rule executions for cancellation
        self.active_executions = {}
        self.execution_id_prefix = "rule-exec-"
        
    async def create_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new rule
        
        Args:
            rule_data: Rule configuration
            
        Returns:
            Standardized response with created rule
        """
        try:
            # Create rule object
            rule = Rule(
                name=rule_data["name"],
                description=rule_data.get("description"),
                rule_type=rule_data.get("rule_type", "condition"),
                is_enabled=rule_data.get("enabled", True),
                schedule=rule_data.get("schedule"),
                target_device_ids=rule_data.get("target_device_ids"),
                conditions=rule_data.get("conditions", {}),
                actions=rule_data.get("actions", []),
                priority=rule_data.get("priority", 1)
            )
            
            # Add to database
            self.db.add(rule)
            await self.db.commit()
            await self.db.refresh(rule)
            
            return {
                "status": "success",
                "message": "Rule created successfully",
                "data": rule.to_dict(),
                "errors": None
            }
        except Exception as e:
            logger.error(f"Error creating rule: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to create rule",
                "data": None,
                "errors": [{"field": "rule_data", "detail": str(e)}]
            }
        
    async def get_rule(self, rule_id: int) -> Dict[str, Any]:
        """
        Get a rule by ID
        
        Args:
            rule_id: ID of the rule
            
        Returns:
            Standardized response with rule data or error
        """
        try:
            rule = await self.db.get(Rule, rule_id)
            if not rule:
                return {
                    "status": "error",
                    "message": f"Rule with ID {rule_id} not found",
                    "data": None,
                    "errors": [{"field": "rule_id", "detail": "Not found"}]
                }
            
            return {
                "status": "success",
                "message": "Rule retrieved successfully",
                "data": rule.to_dict(),
                "errors": None
            }
        except Exception as e:
            logger.error(f"Error retrieving rule {rule_id}: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to retrieve rule",
                "data": None,
                "errors": [{"field": "database", "detail": str(e)}]
            }
        
    async def update_rule(self, rule_id: int, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a rule
        
        Args:
            rule_id: ID of the rule to update
            rule_data: Rule configuration
            
        Returns:
            Standardized response with updated rule
        """
        try:
            # Get existing rule
            rule = await self.db.get(Rule, rule_id)
            if not rule:
                return {
                    "status": "error",
                    "message": f"Rule {rule_id} not found",
                    "data": None,
                    "errors": [{"field": "rule_id", "detail": "Not found"}]
                }
            
            # Update fields
            if "name" in rule_data:
                rule.name = rule_data["name"]
            if "description" in rule_data:
                rule.description = rule_data["description"]
            if "rule_type" in rule_data:
                rule.rule_type = rule_data["rule_type"]
            if "enabled" in rule_data:
                rule.is_enabled = rule_data["enabled"]
            if "schedule" in rule_data:
                rule.schedule = rule_data["schedule"]
            if "target_device_ids" in rule_data:
                rule.target_device_ids = rule_data["target_device_ids"]
            if "conditions" in rule_data:
                rule.conditions = rule_data["conditions"]
            if "actions" in rule_data:
                rule.actions = rule_data["actions"]
            if "priority" in rule_data:
                rule.priority = rule_data["priority"]
            
            # Update timestamp
            rule.updated_at = datetime.now()
            
            # Save changes
            await self.db.commit()
            await self.db.refresh(rule)
            
            return {
                "status": "success",
                "message": "Rule updated successfully",
                "data": rule.to_dict(),
                "errors": None
            }
        except Exception as e:
            logger.error(f"Error updating rule: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to update rule",
                "data": None,
                "errors": [{"field": "rule_data", "detail": str(e)}]
            }
        
    async def delete_rule(self, rule_id: int) -> Dict[str, Any]:
        """
        Delete a rule
        
        Args:
            rule_id: ID of the rule to delete
            
        Returns:
            Result of deletion
        """
        try:
            # Get rule
            rule = await self.db.get(Rule, rule_id)
            if not rule:
                return {
                    "status": "error",
                    "message": f"Rule {rule_id} not found",
                    "data": None,
                    "errors": [{"field": "rule_id", "detail": "Not found"}]
                }
            
            # Cancel any active execution
            execution_id = f"rule_{rule_id}"
            if execution_id in self.active_executions:
                self.active_executions[execution_id]["is_cancelled"] = True
            
            # Delete from database
            await self.db.delete(rule)
            await self.db.commit()
            
            return {
                "status": "success",
                "message": f"Rule {rule_id} deleted",
                "data": None,
                "errors": None
            }
        except Exception as e:
            logger.error(f"Error deleting rule {rule_id}: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to delete rule",
                "data": None,
                "errors": [{"field": "database", "detail": str(e)}]
            }
        
    async def list_rules(self) -> Dict[str, Any]:
        """
        List all rules
        
        Returns:
            Standardized response with list of rules
        """
        try:
            query = select(Rule).order_by(Rule.priority.desc())
            result = await self.db.execute(query)
            rules = result.scalars().all()
            
            rule_list = [rule.to_dict() for rule in rules]
            
            return {
                "status": "success",
                "message": f"{len(rule_list)} rules retrieved",
                "data": rule_list,
                "errors": None
            }
        except Exception as e:
            logger.error(f"Error listing rules: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to list rules",
                "data": None,
                "errors": [{"field": "database", "detail": str(e)}]
            }
        
    async def enable_rule(self, rule_id: int) -> Dict[str, Any]:
        """
        Enable a rule
        
        Args:
            rule_id: ID of the rule to enable
            
        Returns:
            Standardized response with result
        """
        try:
            # Get rule
            rule = await self.db.get(Rule, rule_id)
            if not rule:
                return {
                    "status": "error",
                    "message": f"Rule {rule_id} not found",
                    "data": None,
                    "errors": [{"field": "rule_id", "detail": "Not found"}]
                }
            
            # Enable rule
            rule.is_enabled = True
            await self.db.commit()
            
            return {
                "status": "success",
                "message": f"Rule {rule_id} enabled successfully",
                "data": rule.to_dict(),
                "errors": None
            }
        except Exception as e:
            logger.error(f"Error enabling rule {rule_id}: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to enable rule",
                "data": None,
                "errors": [{"field": "database", "detail": str(e)}]
            }
        
    async def disable_rule(self, rule_id: int) -> Dict[str, Any]:
        """
        Disable a rule
        
        Args:
            rule_id: ID of the rule to disable
            
        Returns:
            Standardized response with disabled rule
        """
        try:
            # Get rule
            rule = await self.db.get(Rule, rule_id)
            if not rule:
                return {
                    "status": "error",
                    "message": f"Rule {rule_id} not found",
                    "data": None,
                    "errors": [{"field": "rule_id", "detail": "Not found"}]
                }
            
            # Check if already disabled
            if not rule.is_enabled:
                return {
                    "status": "success",
                    "message": f"Rule {rule_id} is already disabled",
                    "data": rule.to_dict(),
                    "errors": None
                }
            
            # Update rule
            rule.is_enabled = False
            rule.updated_at = datetime.now()
            await self.db.commit()
            await self.db.refresh(rule)
            
            return {
                "status": "success",
                "message": f"Rule {rule_id} disabled successfully",
                "data": rule.to_dict(),
                "errors": None
            }
        except Exception as e:
            logger.error(f"Error disabling rule {rule_id}: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to disable rule",
                "data": None,
                "errors": [{"field": "database", "detail": str(e)}]
            }
        
    async def apply_rules_to_device(self, device_id: int) -> Dict[str, Any]:
        """
        Apply all enabled rules to a specific device
        
        Args:
            device_id: ID of the device to apply rules to
            
        Returns:
            Standardized response with rule application results
        """
        # Create a unique execution ID
        execution_id = f"{self.execution_id_prefix}{uuid.uuid4()}"
        
        try:
            # Get device
            device = await self.device_service.get_device_by_id(device_id)
            if not device:
                error_result = {
                    "status": "error",
                    "message": f"Device with ID {device_id} not found",
                    "data": None,
                    "errors": [{"field": "device_id", "detail": "Not found"}]
                }
                # Publish event for device not found
                await self._publish_rule_execution_status(
                    execution_id=execution_id,
                    status="failed", 
                    error=f"Device with ID {device_id} not found"
                )
                return error_result
            
            # Track execution
            self.active_executions[execution_id] = {
                "device_id": device_id,
                "started_at": datetime.now().isoformat(),
                "status": "running",
                "is_cancelled": False
            }
            
            # Publish event for execution start
            await self._publish_rule_execution_status(
                execution_id=execution_id,
                status="started",
                result={
                    "data": {
                        "devices_processed": 0,
                        "rules_applied_count": 0
                    }
                }
            )
            
            # Get all enabled rules
            query = select(Rule).where(Rule.is_enabled == True)
            result = await self.db.execute(query)
            rules = result.scalars().all()
            
            # Track rule application results
            rule_results = []
            rules_applied = 0
            rules_skipped = 0
            
            # Check for cancellation periodically
            for rule in rules:
                # Check if execution is cancelled
                if execution_id in self.active_executions and self.active_executions[execution_id].get("is_cancelled", False):
                    # Update execution status
                    self.active_executions[execution_id]["status"] = "cancelled"
                    self.active_executions[execution_id]["completed_at"] = datetime.now().isoformat()
                    
                    cancel_result = {
                        "status": "success",
                        "message": f"Rule execution cancelled after applying {rules_applied} rules",
                        "data": {
                            "execution_id": execution_id,
                            "device_id": device_id,
                            "rules_applied": rules_applied,
                            "rules_skipped": rules_skipped,
                            "results": rule_results
                        },
                        "errors": None
                    }
                    
                    # Publish event for cancellation
                    await self._publish_rule_execution_status(
                        execution_id=execution_id,
                        status="cancelled",
                        result=cancel_result
                    )
                    
                    return cancel_result
                
                # Schedule enforcement for scheduled rules
                if rule.rule_type == "schedule":
                    sched = rule.schedule or ""
                    if "T" in sched:
                        # support datetime-local strings without seconds
                        sched_str = sched
                        if len(sched_str.split('T')[1].split(':')) == 2:
                            sched_str = sched_str + ":00"
                        try:
                            sched_dt = datetime.fromisoformat(sched_str)
                        except ValueError:
                            rule_results.append({
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "applied": False,
                                "reason": "Invalid schedule format"
                            })
                            rules_skipped += 1
                            continue
                        now = datetime.now()
                        if now < sched_dt:
                            rule_results.append({
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "applied": False,
                                "reason": "Scheduled for future"
                            })
                            rules_skipped += 1
                            continue
                        if rule.last_triggered and rule.last_triggered >= sched_dt:
                            rule_results.append({
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "applied": False,
                                "reason": "Already executed"
                            })
                            rules_skipped += 1
                            continue
                
                # Check if rule applies to this device
                if await self._rule_applies_to_device(rule, device):
                    # Rule applies, execute actions
                    action_result = await self._apply_rule_actions(rule, device)
                    rule_results.append({
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "applied": True,
                        "actions": action_result.get("actions", [])
                    })
                    rules_applied += 1
                    
                    # Update last_triggered for one-time schedule rules
                    if rule.rule_type == "schedule" and rule.schedule and "T" in rule.schedule:
                        lt_str = rule.schedule
                        if len(lt_str.split('T')[1].split(':')) == 2:
                            lt_str = lt_str + ":00"
                        rule.last_triggered = datetime.fromisoformat(lt_str)
                        self.db.add(rule)
                        await self.db.commit()
                    
                    # Publish progress update every 5 rules applied
                    if rules_applied % 5 == 0:
                        await self._publish_rule_execution_status(
                            execution_id=execution_id,
                            status="in_progress",
                            result={
                                "data": {
                                    "devices_processed": 1,
                                    "rules_applied_count": rules_applied
                                }
                            }
                        )
                else:
                    # Rule doesn't apply to this device
                    rule_results.append({
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "applied": False,
                        "reason": "Conditions not met"
                    })
                    rules_skipped += 1
            
            # Update execution status
            self.active_executions[execution_id]["status"] = "completed"
            self.active_executions[execution_id]["completed_at"] = datetime.now().isoformat()
            self.active_executions[execution_id]["rules_applied"] = rules_applied
            self.active_executions[execution_id]["rules_skipped"] = rules_skipped
            
            result = {
                "status": "success",
                "message": f"Applied {rules_applied} rules to device {device_id}",
                "data": {
                    "execution_id": execution_id,
                    "device_id": device_id,
                    "rules_applied_count": rules_applied,
                    "rules_skipped_count": rules_skipped,
                    "results": rule_results
                },
                "errors": None
            }
            
            # Publish completion event
            await self._publish_rule_execution_status(
                execution_id=execution_id,
                status="completed",
                result=result
            )
            
            return result
            
        except Exception as e:
            # Update execution status on error
            if execution_id in self.active_executions:
                self.active_executions[execution_id]["status"] = "failed"
                self.active_executions[execution_id]["error"] = str(e)
                self.active_executions[execution_id]["completed_at"] = datetime.now().isoformat()
            
            logger.error(f"Error applying rules to device {device_id}: {str(e)}")
            error_result = {
                "status": "error",
                "message": f"Failed to apply rules to device {device_id}",
                "data": None,
                "errors": [{"field": "rule_execution", "detail": str(e)}]
            }
            
            # Publish error event
            await self._publish_rule_execution_status(
                execution_id=execution_id,
                status="failed",
                error=str(e)
            )
            
            return error_result
        
    async def apply_all_rules(self) -> Dict[str, Any]:
        """
        Apply all enabled rules to all applicable devices
        
        Returns:
            Standardized response with rule application results
        """
        # Create a unique execution ID
        execution_id = f"{self.execution_id_prefix}_all_rules_{uuid.uuid4().hex[:8]}"
        
        try:
            # Track execution
            self.active_executions[execution_id] = {
                "started_at": datetime.now().isoformat(),
                "status": "running",
                "cancelled": False
            }
            
            # Publish execution start event
            await self._publish_rule_execution_status(
                execution_id=execution_id,
                status="started",
                result={
                    "data": {
                        "devices_processed": 0,
                        "rules_applied_count": 0
                    }
                }
            )
            
            # Get all devices
            devices_result = await self.device_service.get_all_devices()
            devices = devices_result if isinstance(devices_result, list) else devices_result.get("data", [])
            
            # Get enabled rules
            query = select(Rule).where(Rule.is_enabled == True).order_by(Rule.priority.desc())
            result = await self.db.execute(query)
            enabled_rules = result.scalars().all()
            
            # Check if we have rules and devices
            if not enabled_rules:
                no_rules_result = {
                    "status": "success",
                    "message": "No enabled rules found",
                    "data": {
                        "execution_id": execution_id,
                        "devices_processed": 0,
                        "rules_applied_count": 0
                    },
                    "errors": None
                }
                
                # Update execution status
                self.active_executions[execution_id]["status"] = "completed"
                self.active_executions[execution_id]["completed_at"] = datetime.now().isoformat()
                
                # Publish completion event
                await self._publish_rule_execution_status(
                    execution_id=execution_id,
                    status="completed",
                    result=no_rules_result
                )
                
                return no_rules_result
            
            if not devices:
                no_devices_result = {
                    "status": "success",
                    "message": "No devices found to apply rules to",
                    "data": {
                        "execution_id": execution_id,
                        "devices_processed": 0,
                        "rules_applied_count": 0
                    },
                    "errors": None
                }
                
                # Update execution status
                self.active_executions[execution_id]["status"] = "completed"
                self.active_executions[execution_id]["completed_at"] = datetime.now().isoformat()
                
                # Publish completion event
                await self._publish_rule_execution_status(
                    execution_id=execution_id,
                    status="completed",
                    result=no_devices_result
                )
                
                return no_devices_result
            
            # Track applied rules per device
            results = []
            devices_processed = 0
            
            # Update execution with total devices
            self.active_executions[execution_id]["total_devices"] = len(devices)
            
            # Publish initial progress info
            await self._publish_rule_execution_status(
                execution_id=execution_id,
                status="in_progress",
                result={
                    "data": {
                        "devices_processed": 0,
                        "rules_applied_count": 0,
                        "total_devices": len(devices)
                    }
                }
            )
            
            try:
                # Process each device
                for i, device in enumerate(devices):
                    # Check for cancellation
                    if self.active_executions[execution_id]["cancelled"]:
                        logger.info("All rules execution was cancelled")
                        
                        cancel_result = {
                            "status": "success",
                            "message": f"Rule execution cancelled after processing {devices_processed} devices",
                            "data": {
                                "execution_id": execution_id,
                                "devices_processed": devices_processed,
                                "rules_applied_count": len(results),
                                "results": results
                            },
                            "errors": None
                        }
                        
                        # Publish cancellation event
                        await self._publish_rule_execution_status(
                            execution_id=execution_id,
                            status="cancelled",
                            result=cancel_result
                        )
                        
                        # Update execution status
                        self.active_executions[execution_id]["status"] = "cancelled"
                        self.active_executions[execution_id]["completed_at"] = datetime.now().isoformat()
                        
                        return cancel_result
                    
                    # Get device ID depending on device format
                    device_id = device["id"] if isinstance(device, dict) else device.id 
                    
                    # Apply rules to this device
                    device_result = await self.apply_rules_to_device(device_id)
                    if device_result["status"] == "success":
                        results.append(device_result["data"])
                    
                    devices_processed += 1
                    
                    # Publish progress updates every 5 devices or at the end
                    if devices_processed % 5 == 0 or devices_processed == len(devices):
                        await self._publish_rule_execution_status(
                            execution_id=execution_id,
                            status="in_progress",
                            result={
                                "data": {
                                    "devices_processed": devices_processed,
                                    "rules_applied_count": len(results),
                                    "total_devices": len(devices),
                                    "percentage_complete": round((devices_processed / len(devices)) * 100, 1)
                                }
                            }
                        )
                
                # Update execution status
                self.active_executions[execution_id]["status"] = "completed"
                self.active_executions[execution_id]["completed_at"] = datetime.now().isoformat()
                self.active_executions[execution_id]["devices_processed"] = devices_processed
                self.active_executions[execution_id]["rules_applied"] = len(results)
                
            except Exception as sub_e:
                # Mark execution as failed but continue
                logger.error(f"Error in sub-process during apply_all_rules: {str(sub_e)}")
                self.active_executions[execution_id]["status"] = "failed"
                self.active_executions[execution_id]["error"] = str(sub_e)
                
                # Publish failure event
                await self._publish_rule_execution_status(
                    execution_id=execution_id,
                    status="failed",
                    error=str(sub_e)
                )
            
            application_result = {
                "devices_processed": devices_processed,
                "rules_applied_count": len(results),
                "results": results
            }
            
            result = {
                "status": "success",
                "message": f"Rules applied to {len(results)} of {len(devices)} devices",
                "data": application_result,
                "errors": None
            }
            
            # Publish completion event
            await self._publish_rule_execution_status(
                execution_id=execution_id,
                status="completed",
                result=result
            )
            
            return result
        except Exception as e:
            logger.error(f"Error applying all rules: {str(e)}")
            
            # Update execution status if it exists
            if execution_id in self.active_executions:
                self.active_executions[execution_id]["status"] = "failed"
                self.active_executions[execution_id]["error"] = str(e)
                self.active_executions[execution_id]["completed_at"] = datetime.now().isoformat()
            
            error_result = {
                "status": "error",
                "message": "Failed to apply all rules",
                "data": None,
                "errors": [{"field": "execution", "detail": str(e)}]
            }
            
            # Publish error event
            await self._publish_rule_execution_status(
                execution_id=execution_id,
                status="failed",
                error=str(e)
            )
            
            return error_result
            
    async def get_active_executions(self) -> Dict[str, Any]:
        try:
            cutoff_time = datetime.now() - timedelta(minutes=10)
            exec_ids_to_remove = []
            
            for exec_id, exec_data in self.active_executions.items():
                started_at = exec_data.get("started_at")
                if started_at:
                    try:
                        started_time = datetime.fromisoformat(started_at)
                        if started_time < cutoff_time:
                            exec_ids_to_remove.append(exec_id)
                    except (ValueError, TypeError):
                        exec_ids_to_remove.append(exec_id)
            
            for exec_id in exec_ids_to_remove:
                self.active_executions.pop(exec_id, None)
            
            status_counts = {}
            for exec_data in self.active_executions.values():
                status = exec_data.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "status": "success",
                "message": f"Found {len(self.active_executions)} active executions",
                "data": {
                    "executions": self.active_executions,
                    "count": len(self.active_executions),
                    "status_summary": status_counts
                },
                "errors": None
            }
        except Exception as e:
            logger.error(f"Error getting active executions: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to get active executions",
                "data": None,
                "errors": [{"field": "execution", "detail": str(e)}]
            }
    
    async def _publish_rule_execution_status(self, execution_id: str, status: str, 
                                            result: Dict[str, Any] = None, 
                                            error: str = None) -> None:
        # Publish rule execution status updates to WebSocket clients
        # 
        # This method sends real-time updates about rule execution progress to connected
        # WebSocket clients, allowing frontends to display live execution status without polling.
        # 
        # Args:
        #    execution_id: Unique execution identifier
        #    status: Current status (started, in_progress, completed, failed, cancelled)
        #    result: Success result data (if any)
        #    error: Error message (if any)
        try:
            # Build event data
            event_data = {
                "event_type": "rule_execution",
                "execution_id": execution_id,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add result data if available
            if result and isinstance(result, dict):
                # Extract relevant information without duplicating everything
                event_data["data"] = {
                    "devices_processed": result.get("data", {}).get("devices_processed", 0),
                    "rules_applied_count": result.get("data", {}).get("rules_applied_count", 0),
                    "status_summary": result.get("data", {}).get("status_summary", {})
                }
            
            # Add error information if available
            if error:
                event_data["error"] = error
            
            # Determine if notification should be sent
            should_notify = True
            if not error:
                data_stats = event_data.get("data", {})
                devices_processed = data_stats.get("devices_processed", 0)
                rules_applied_count = data_stats.get("rules_applied_count", 0)
                if devices_processed == 0 and rules_applied_count == 0:
                    should_notify = False
            
            if should_notify:
                # Publish event to all connected clients
                await publish_event(event_data)
            else:
                logger.debug("Rule execution produced no changes – notification suppressed")
            
        except Exception as e:
            # Log but don't interrupt rule processing
            logger.warning(f"Failed to publish rule execution status: {str(e)}")
    
    async def _rule_applies_to_device(self, rule: Rule, device: Any) -> bool:
        # Check if a rule applies to a device based on conditions
        # Check if this rule targets specific devices
        if rule.target_device_ids:
            # Match by numeric ID or string hash_id
            if not any(
                (isinstance(tid, int) and tid == device.id)
                or (isinstance(tid, str) and (tid == device.hash_id or tid == str(device.id)))
                for tid in rule.target_device_ids
            ):
                return False  # This rule doesn't apply to this device
        
        conditions = rule.conditions
        
        # If no conditions, rule applies to all devices
        if not conditions:
            return True
        
        device_dict = device.to_dict()
        
        # Process each condition
        for condition in conditions:
            condition_type = condition.get("type", "device_property")
            
            # Handle different condition types
            if condition_type == "sensor":
                # Check sensor reading
                sensor_type = condition.get("sensor_type")
                operator = condition.get("operator", "equals")
                expected_value = condition.get("value")
                
                if not sensor_type:
                    continue
                    
                # Get the most recent sensor reading of this type
                query = (
                    select(SensorReading)
                    .where(
                        SensorReading.device_id == device.id,
                        SensorReading.sensor_type == sensor_type
                    )
                    .order_by(desc(SensorReading.timestamp))
                    .limit(1)
                )
                
                result = await self.db.execute(query)
                reading = result.scalar_one_or_none()
                
                if not reading:
                    return False  # No reading available, condition can't be met
                    
                # Compare reading value against expected value
                if not self._compare_values(reading.value, expected_value, operator):
                    return False
                    
            else:
                # Default: check device property
                property_path = condition.get("property", "").split(".")
                operator = condition.get("operator", "equals")
                expected_value = condition.get("value")
                
                # Extract property value
                actual_value = self._get_nested_value(device_dict, property_path)
                
                # Compare values
                if not self._compare_values(actual_value, expected_value, operator):
                    return False
        
        # All conditions passed
        return True
    
    async def _apply_rule_actions(self, rule: Rule, device: Any) -> Dict[str, Any]:
        # Apply rule actions to a device
        actions = rule.actions
        results = []
        
        for action in actions:
            action_type = action.get("type")
            parameters = action.get("parameters", {})
            
            if action_type == "control_device":
                # Execute device control
                control_action = parameters.get("action")
                control_params = parameters.get("parameters", {})
                
                if control_action:
                    result = await self.device_service.control_device(
                        device_id=device.id,
                        action=control_action,
                        parameters=control_params,
                        user_id=None  # System action
                    )
                    
                    results.append({
                        "rule_id": rule.id,
                        "device_id": device.id,
                        "action": control_action,
                        "result": result
                    })
            
            elif action_type == "set_status":
                # Set device status
                is_online = parameters.get("is_online", True)
                result = await self.device_service.update_device_status(
                    device_id=device.id,
                    is_online=is_online
                )
                
                results.append({
                    "rule_id": rule.id,
                    "device_id": device.id,
                    "action": "set_status",
                    "status": "online" if is_online else "offline",
                    "result": result is not None
                })
            
            elif action_type == "notification":
                # Send notification
                title = parameters.get("title", f"Alert from rule: {rule.name}")
                content = parameters.get("content", f"Rule {rule.name} was triggered by device {device.name}")
                recipients = parameters.get("recipients", [])
                # Include email and websocket by default in addition to in_app
                channels = parameters.get("channels", ["in_app", "email", "websocket"])
                
                if recipients and channels:
                    notification = await self.notification_service.create_notification(
                        title=title,
                        content=content,
                        notification_type=parameters.get("notification_type", "alert"),
                        source="rule",
                        source_id=rule.id,
                        target_type="device",
                        target_id=device.id,
                        target_name=device.name,
                        priority=parameters.get("priority", 3),
                        recipients=recipients,
                        channels=channels,
                        metadata={
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "device_id": device.id,
                            "device_name": device.name,
                            "triggered_at": datetime.now().isoformat()
                        }
                    )
                    
                    # Dispatch the notification via each channel
                    delivery_results = {}
                    for ch in channels:
                        try:
                            send_res = await self.notification_service.send_notification(notification.id, ch)
                            delivery_results[ch] = send_res
                        except Exception as e:
                            delivery_results[ch] = {"success": False, "error": str(e)}
                      
                    results.append({
                        "rule_id": rule.id,
                        "action": "notification",
                        "notification_id": notification.id if notification else None,
                        "channels": channels,
                        "recipients": recipients,
                        "delivery_results": delivery_results
                    })
        
        return {
            "success": True,
            "actions": results
        }
    
    def _get_nested_value(self, data: Dict[str, Any], path: List[str]) -> Any:
        # Get a nested value from a dictionary using a path
        value = data
        for key in path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def _compare_values(self, actual_value: Any, expected_value: Any, operator: str) -> bool:
        # Compare values using the specified operator
        if operator == "equals":
            return actual_value == expected_value
        elif operator == "not_equals":
            return actual_value != expected_value
        elif operator == "contains":
            if isinstance(actual_value, str) and isinstance(expected_value, str):
                return expected_value in actual_value
            elif isinstance(actual_value, (list, tuple)):
                return expected_value in actual_value
            return False
        elif operator == "greater_than":
            try:
                return float(actual_value) > float(expected_value)
            except (ValueError, TypeError):
                return False
        elif operator == "less_than":
            try:
                return float(actual_value) < float(expected_value)
            except (ValueError, TypeError):
                return False
        # Default: values don't match
        return False
    
    def _validate_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        # Check required fields
        if "name" not in rule_data:
            return {
                "valid": False,
                "message": "Rule name is required"
            }
        
        # Validate conditions
        if "conditions" in rule_data:
            conditions = rule_data["conditions"]
            if not isinstance(conditions, list) and not isinstance(conditions, dict):
                return {
                    "valid": False,
                    "message": "Conditions must be a list or object"
                }
            
            # If it's a list, validate each condition
            if isinstance(conditions, list):
                for condition in conditions:
                    if not isinstance(condition, dict):
                        return {
                            "valid": False,
                            "message": "Each condition must be an object"
                        }
                    
                    # Check condition type
                    condition_type = condition.get("type", "device_property")
                    
                    if condition_type == "sensor":
                        # Sensor condition requires sensor_type
                        if "sensor_type" not in condition:
                            return {
                                "valid": False,
                                "message": "Sensor condition must have a sensor_type"
                            }
                        
                        if "operator" in condition and condition["operator"] not in [
                            "equals", "not_equals", "contains", "greater_than", "less_than"
                        ]:
                            return {
                                "valid": False,
                                "message": f"Invalid operator: {condition['operator']}"
                            }
                        
                        if "value" not in condition:
                            return {
                                "valid": False,
                                "message": "Sensor condition must have a value"
                            }
                    
                    else:
                        # Device property condition
                        if "property" not in condition:
                            return {
                                "valid": False,
                                "message": "Device property condition must have a property"
                            }
                        
                        if "operator" in condition and condition["operator"] not in [
                            "equals", "not_equals", "contains", "greater_than", "less_than"
                        ]:
                            return {
                                "valid": False,
                                "message": f"Invalid operator: {condition['operator']}"
                            }
                        
                        if "value" not in condition:
                            return {
                                "valid": False,
                                "message": "Condition must have a value"
                            }
        
        # Validate actions
        if "actions" not in rule_data:
            return {
                "valid": False,
                "message": "Rule must have actions"
            }
        
        actions = rule_data["actions"]
        if not isinstance(actions, list):
            return {
                "valid": False,
                "message": "Actions must be a list"
            }
        
        if not actions:
            return {
                "valid": False,
                "message": "Rule must have at least one action"
            }
        
        for action in actions:
            if not isinstance(action, dict):
                return {
                    "valid": False,
                    "message": "Each action must be an object"
                }
            
            if "type" not in action:
                return {
                    "valid": False,
                    "message": "Action must have a type"
                }
            
            action_type = action["type"]
            valid_action_types = ["control_device", "set_status", "notification"]
            if action_type not in valid_action_types:
                return {
                    "valid": False,
                    "message": f"Invalid action type: {action_type}. Must be one of: {', '.join(valid_action_types)}"
                }
            
            # If control_device, validate action parameter
            if action_type == "control_device":
                parameters = action.get("parameters", {})
                if "action" not in parameters:
                    return {
                        "valid": False,
                        "message": "control_device action must have an action parameter"
                    }
                    
            # If notification, validate recipients and channels
            if action_type == "notification":
                parameters = action.get("parameters", {})
                if not parameters.get("recipients"):
                    return {
                        "valid": False,
                        "message": "Notification action must have recipients"
                    }
                if not parameters.get("channels"):
                    return {
                        "valid": False,
                        "message": "Notification action must have channels"
                    }
        
        return {
            "valid": True
        }
    
    async def cancel_execution(self, execution_id: str = None) -> Dict[str, Any]:
        try:
            if execution_id and execution_id in self.active_executions:
                if "is_cancelled" in self.active_executions[execution_id]:
                    self.active_executions[execution_id]["is_cancelled"] = True
                else:
                    self.active_executions[execution_id]["cancelled"] = True
                    
                self.active_executions[execution_id]["status"] = "cancelled"
                self.active_executions[execution_id]["cancelled_at"] = datetime.now().isoformat()
                
                result = {
                    "status": "success",
                    "message": f"Execution {execution_id} cancelled successfully",
                    "data": {
                        "execution_id": execution_id,
                        "status": self.active_executions[execution_id]
                    },
                    "errors": None
                }
                
                await self._publish_rule_execution_status(
                    execution_id=execution_id,
                    status="cancelled",
                    result=result
                )
                
                return result
                
            elif not execution_id:
                cancel_count = 0
                cancelled_executions = []
                
                for exec_id in list(self.active_executions.keys()):
                    if self.active_executions[exec_id]["status"] == "running":
                        if "is_cancelled" in self.active_executions[exec_id]:
                            self.active_executions[exec_id]["is_cancelled"] = True
                        else:
                            self.active_executions[exec_id]["cancelled"] = True
                            
                        self.active_executions[exec_id]["status"] = "cancelled"
                        self.active_executions[exec_id]["cancelled_at"] = datetime.now().isoformat()
                        cancelled_executions.append(exec_id)
                        cancel_count += 1
                        
                        await self._publish_rule_execution_status(
                            execution_id=exec_id,
                            status="cancelled",
                            result={
                                "data": {
                                    "execution_id": exec_id,
                                    "status": "cancelled"
                                }
                            }
                        )
                
                result = {
                    "status": "success",
                    "message": f"{cancel_count} executions cancelled successfully",
                    "data": {
                        "cancel_count": cancel_count,
                        "cancelled_executions": cancelled_executions
                    },
                    "errors": None
                }
                
                if cancel_count > 0:
                    await self._publish_rule_execution_status(
                        execution_id="all_executions",
                        status="cancelled",
                        result=result
                    )
                
                return result
            else:
                error_result = {
                    "status": "error",
                    "message": f"No active execution with ID {execution_id}",
                    "data": None,
                    "errors": [{"field": "execution_id", "detail": "Execution ID not found"}]
                }
                
                await self._publish_rule_execution_status(
                    execution_id=execution_id or "unknown_execution",
                    status="error",
                    error=f"No active execution with ID {execution_id}"
                )
                
                return error_result
                
        except Exception as e:
            logger.error(f"Error cancelling execution: {str(e)}")
            
            error_result = {
                "status": "error",
                "message": "Failed to cancel execution",
                "data": None,
                "errors": [{"field": "execution", "detail": str(e)}]
            }
            
            try:
                await self._publish_rule_execution_status(
                    execution_id=execution_id or "error_in_cancel",
                    status="error",
                    error=f"Failed to cancel execution: {str(e)}"
                )
            except Exception as pub_error:
                logger.error(f"Failed to publish cancellation error: {str(pub_error)}")
                
            return error_result
    
    async def get_active_executions(self) -> Dict[str, Any]:
        try:
            cutoff_time = datetime.now() - timedelta(minutes=10)
            exec_ids_to_remove = []
            
            for exec_id, exec_data in self.active_executions.items():
                started_at = exec_data.get("started_at")
                if started_at:
                    try:
                        started_time = datetime.fromisoformat(started_at)
                        if started_time < cutoff_time:
                            exec_ids_to_remove.append(exec_id)
                    except (ValueError, TypeError):
                        exec_ids_to_remove.append(exec_id)
            
            for exec_id in exec_ids_to_remove:
                self.active_executions.pop(exec_id, None)
            
            status_counts = {}
            for exec_data in self.active_executions.values():
                status = exec_data.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "status": "success",
                "message": f"Found {len(self.active_executions)} active executions",
                "data": {
                    "executions": self.active_executions,
                    "count": len(self.active_executions),
                    "status_summary": status_counts
                },
                "errors": None
            }
        except Exception as e:
            logger.error(f"Error getting active executions: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to get active executions",
                "data": None,
                "errors": [{"field": "execution", "detail": str(e)}]
            }