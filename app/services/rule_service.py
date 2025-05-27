"""Rule Service for IoT Management Platform"""
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, desc

from app.services.device_service import DeviceService
from app.services.notification_service import NotificationService
from app.models.rule import Rule
from app.models.sensor_reading import SensorReading

logger = logging.getLogger(__name__)

class RuleService:
    """Service for managing device rules"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.device_service = DeviceService(db)
        self.notification_service = NotificationService(db)
        # Track active rule executions for cancellation
        self.active_executions = {}
        
    async def create_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new rule
        
        Args:
            rule_data: Rule configuration
            
        Returns:
            Created rule with ID
        """
        try:
            # Validate rule
            validation_result = self._validate_rule(rule_data)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["message"]
                }
            
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
                "success": True,
                "rule": rule.to_dict()
            }
        except Exception as e:
            logger.error(f"Error creating rule: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to create rule: {str(e)}"
            }
        
    async def get_rule(self, rule_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a rule by ID
        
        Args:
            rule_id: ID of the rule
            
        Returns:
            Rule configuration or None if not found
        """
        rule = await self.db.get(Rule, rule_id)
        return rule.to_dict() if rule else None
        
    async def update_rule(self, rule_id: int, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a rule
        
        Args:
            rule_id: ID of the rule to update
            rule_data: Rule configuration
            
        Returns:
            Updated rule
        """
        try:
            # Get existing rule
            rule = await self.db.get(Rule, rule_id)
            if not rule:
                return {
                    "success": False,
                    "error": f"Rule {rule_id} not found"
                }
            
            # Validate rule data if complete update
            if "conditions" in rule_data or "actions" in rule_data:
                validation_data = {
                    "name": rule_data.get("name", rule.name),
                    "conditions": rule_data.get("conditions", rule.conditions),
                    "actions": rule_data.get("actions", rule.actions)
                }
                validation_result = self._validate_rule(validation_data)
                if not validation_result["valid"]:
                    return {
                        "success": False,
                        "error": validation_result["message"]
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
                
            if "is_enabled" in rule_data:
                rule.is_enabled = rule_data["is_enabled"]
                
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
            
            # Save changes
            await self.db.commit()
            await self.db.refresh(rule)
            
            return {
                "success": True,
                "rule": rule.to_dict()
            }
        except Exception as e:
            logger.error(f"Error updating rule {rule_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to update rule: {str(e)}"
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
                    "success": False,
                    "error": f"Rule {rule_id} not found"
                }
            
            # Cancel any active execution
            execution_id = f"rule_{rule_id}"
            if execution_id in self.active_executions:
                self.active_executions[execution_id]["cancelled"] = True
            
            # Delete from database
            await self.db.delete(rule)
            await self.db.commit()
            
            return {
                "success": True,
                "message": f"Rule {rule_id} deleted"
            }
        except Exception as e:
            logger.error(f"Error deleting rule {rule_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to delete rule: {str(e)}"
            }
        
    async def list_rules(self) -> List[Dict[str, Any]]:
        """
        List all rules
        
        Returns:
            List of rules
        """
        try:
            query = select(Rule)
            result = await self.db.execute(query)
            rules = result.scalars().all()
            return [rule.to_dict() for rule in rules]
        except Exception as e:
            logger.error(f"Error listing rules: {str(e)}")
            return []
        
    async def enable_rule(self, rule_id: int) -> Dict[str, Any]:
        """
        Enable a rule
        
        Args:
            rule_id: ID of the rule to enable
            
        Returns:
            Result of operation
        """
        try:
            # Get rule
            rule = await self.db.get(Rule, rule_id)
            if not rule:
                return {
                    "success": False,
                    "error": f"Rule {rule_id} not found"
                }
            
            # Enable rule
            rule.is_enabled = True
            await self.db.commit()
            
            return {
                "success": True,
                "message": f"Rule {rule_id} enabled",
                "rule": rule.to_dict()
            }
        except Exception as e:
            logger.error(f"Error enabling rule {rule_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to enable rule: {str(e)}"
            }
        
    async def disable_rule(self, rule_id: int) -> Dict[str, Any]:
        """
        Disable a rule
        
        Args:
            rule_id: ID of the rule to disable
            
        Returns:
            Result of operation
        """
        try:
            # Get rule
            rule = await self.db.get(Rule, rule_id)
            if not rule:
                return {
                    "success": False,
                    "error": f"Rule {rule_id} not found"
                }
            
            # Disable rule
            rule.is_enabled = False
            await self.db.commit()
            
            # Cancel any active execution
            execution_id = f"rule_{rule_id}"
            if execution_id in self.active_executions:
                self.active_executions[execution_id]["cancelled"] = True
            
            return {
                "success": True,
                "message": f"Rule {rule_id} disabled",
                "rule": rule.to_dict()
            }
        except Exception as e:
            logger.error(f"Error disabling rule {rule_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to disable rule: {str(e)}"
            }
        
    async def apply_rules_to_device(self, device_id: int) -> Dict[str, Any]:
        """
        Apply all enabled rules to a specific device
        
        Args:
            device_id: ID of the device to apply rules to
            
        Returns:
            Result of rule application
        """
        try:
            device = await self.device_service.get_device_by_id(device_id)
            if not device:
                return {
                    "success": False,
                    "error": f"Device {device_id} not found"
                }
            
            # Get enabled rules
            query = select(Rule).where(Rule.is_enabled == True)
            result = await self.db.execute(query)
            enabled_rules = result.scalars().all()
            
            # Track applied rules
            applied_rules = []
            rule_actions = []
            
            # Create execution context for cancellation
            execution_id = f"device_{device_id}_{datetime.utcnow().timestamp()}"
            self.active_executions[execution_id] = {
                "start_time": datetime.utcnow(),
                "cancelled": False,
                "device_id": device_id
            }
            
            try:
                # Process each rule
                for rule in enabled_rules:
                    # Check for cancellation
                    if self.active_executions[execution_id]["cancelled"]:
                        logger.info(f"Rule execution for device {device_id} was cancelled")
                        break
                    
                    # Check if rule applies to this device
                    if await self._rule_applies_to_device(rule, device):
                        # Apply rule actions
                        action_result = await self._apply_rule_actions(rule, device)
                        if action_result["success"]:
                            # Update rule last triggered time
                            rule.last_triggered = datetime.utcnow()
                            rule.status = "success"
                            await self.db.commit()
                            
                            applied_rules.append(rule.id)
                            rule_actions.extend(action_result.get("actions", []))
            finally:
                # Clean up execution context
                if execution_id in self.active_executions:
                    del self.active_executions[execution_id]
            
            return {
                "success": True,
                "device_id": device_id,
                "device_name": device.name,
                "rules_applied": len(applied_rules),
                "rule_ids": applied_rules,
                "actions": rule_actions
            }
        except Exception as e:
            logger.error(f"Error applying rules to device {device_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to apply rules: {str(e)}"
            }
        
    async def apply_all_rules(self) -> Dict[str, Any]:
        """
        Apply all enabled rules to all applicable devices
        
        Returns:
            Result of rule application
        """
        try:
            # Get all devices
            devices = await self.device_service.get_all_devices()
            
            # Get enabled rules
            query = select(Rule).where(Rule.is_enabled == True)
            result = await self.db.execute(query)
            enabled_rules = result.scalars().all()
            
            # Create execution context for cancellation
            execution_id = f"all_rules_{datetime.utcnow().timestamp()}"
            self.active_executions[execution_id] = {
                "start_time": datetime.utcnow(),
                "cancelled": False
            }
            
            # Track results
            results = []
            total_actions = 0
            
            try:
                # Process each device
                for device in devices:
                    # Check for cancellation
                    if self.active_executions[execution_id]["cancelled"]:
                        logger.info("Rule execution for all devices was cancelled")
                        break
                    
                    device_actions = []
                    applied_rules = []
                    
                    # Apply each rule to device
                    for rule in enabled_rules:
                        if await self._rule_applies_to_device(rule, device):
                            # Apply rule actions
                            action_result = await self._apply_rule_actions(rule, device)
                            if action_result["success"]:
                                # Update rule last triggered time
                                rule.last_triggered = datetime.utcnow()
                                rule.status = "success"
                                await self.db.commit()
                                
                                applied_rules.append(rule.id)
                                device_actions.extend(action_result.get("actions", []))
                    
                    if applied_rules:
                        results.append({
                            "device_id": device.id,
                            "device_name": device.name,
                            "rules_applied": len(applied_rules),
                            "rule_ids": applied_rules,
                            "actions": device_actions
                        })
                        total_actions += len(device_actions)
            finally:
                # Clean up execution context
                if execution_id in self.active_executions:
                    del self.active_executions[execution_id]
            
            return {
                "success": True,
                "devices_processed": len(devices),
                "devices_affected": len(results),
                "total_actions": total_actions,
                "results": results
            }
        except Exception as e:
            logger.error(f"Error applying all rules: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to apply rules: {str(e)}"
            }
    
    async def cancel_execution(self, execution_id: str = None) -> Dict[str, Any]:
        """
        Cancel an active rule execution
        
        Args:
            execution_id: ID of execution to cancel (if None, cancels all)
            
        Returns:
            Result of cancellation
        """
        if execution_id and execution_id in self.active_executions:
            # Cancel specific execution
            self.active_executions[execution_id]["cancelled"] = True
            return {
                "success": True,
                "message": f"Execution {execution_id} cancelled"
            }
        elif not execution_id:
            # Cancel all executions
            cancel_count = 0
            for exec_id in self.active_executions:
                self.active_executions[exec_id]["cancelled"] = True
                cancel_count += 1
            
            return {
                "success": True,
                "message": f"{cancel_count} executions cancelled"
            }
        else:
            return {
                "success": False,
                "error": f"No active execution with ID {execution_id}"
            }
    
    async def get_active_executions(self) -> Dict[str, Any]:
        """
        Get information about active rule executions
        
        Returns:
            List of active executions
        """
        # Clean up old executions (older than 10 minutes)
        cutoff_time = datetime.utcnow() - timedelta(minutes=10)
        exec_ids_to_remove = []
        
        for exec_id, exec_data in self.active_executions.items():
            if exec_data["start_time"] < cutoff_time:
                exec_ids_to_remove.append(exec_id)
        
        for exec_id in exec_ids_to_remove:
            del self.active_executions[exec_id]
        
        # Return active executions
        return {
            "success": True,
            "active_executions": self.active_executions
        }
    
    async def _rule_applies_to_device(self, rule: Rule, device: Any) -> bool:
        """Check if a rule applies to a device based on conditions"""
        # Check if this rule targets specific devices
        if rule.target_device_ids and device.id not in rule.target_device_ids:
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
        """Apply rule actions to a device"""
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
                channels = parameters.get("channels", ["in_app"])
                
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
                            "triggered_at": datetime.utcnow().isoformat()
                        }
                    )
                    
                    results.append({
                        "rule_id": rule.id,
                        "action": "notification",
                        "notification_id": notification.id if notification else None,
                        "channels": channels,
                        "recipients": recipients
                    })
        
        return {
            "success": True,
            "actions": results
        }
    
    def _get_nested_value(self, data: Dict[str, Any], path: List[str]) -> Any:
        """Get a nested value from a dictionary using a path"""
        value = data
        for key in path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def _compare_values(self, actual_value: Any, expected_value: Any, operator: str) -> bool:
        """Compare values using the specified operator"""
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
        """Validate a rule configuration"""
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