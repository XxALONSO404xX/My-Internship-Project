"""Device Service for IoT Platform"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import random
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.services.device_scanner import create_device_scanner
from app.services.vulnerability_scanner import create_vulnerability_scanner
from app.services.activity_service import ActivityService
from app.utils.simulation import simulate_network_delay, simulate_failures

logger = logging.getLogger(__name__)

class DeviceService:
    """Service for managing IoT devices"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # Create scanner instances with DB session
        self.device_scanner = create_device_scanner(db)
        self.vulnerability_scanner = create_vulnerability_scanner(db)
        # Initialize activity service
        self.activity_service = ActivityService(db)
    
    async def get_all_devices(self) -> List[Device]:
        """Get all devices"""
        query = select(Device)
        result = await self.db.execute(query)
        return result.scalars().all()
        
    async def get_device_summary(self) -> Dict[str, Any]:
        """Get summary statistics for devices
        
        Returns a dictionary with counts of devices by status, type, etc.
        """
        # Get all devices for stats calculation
        devices = await self.get_all_devices()
        
        # Initialize counters
        total_count = len(devices)
        online_count = 0
        offline_count = 0
        type_counts = {}
        connection_type_counts = {}
        firmware_status = {
            "up_to_date": 0,
            "needs_update": 0,
            "unknown": 0
        }
        
        # Calculate counts
        for device in devices:
            # Online status
            if device.is_online:
                online_count += 1
            else:
                offline_count += 1
                
            # Device type counts
            device_type = device.device_type
            if device_type not in type_counts:
                type_counts[device_type] = 0
            type_counts[device_type] += 1
            
            # Connection type counts
            for conn_type in ["supports_http", "supports_mqtt", "supports_coap", "supports_websocket"]:
                if getattr(device, conn_type, False):
                    if conn_type not in connection_type_counts:
                        connection_type_counts[conn_type] = 0
                    connection_type_counts[conn_type] += 1
            
            # Firmware status (simplified example - would need actual firmware version comparison)
            if device.last_firmware_check:
                days_since_check = (datetime.utcnow() - device.last_firmware_check).days
                if days_since_check < 30:
                    firmware_status["up_to_date"] += 1
                else:
                    firmware_status["needs_update"] += 1
            else:
                firmware_status["unknown"] += 1
        
        return {
            "total": total_count,
            "online": online_count,
            "offline": offline_count,
            "by_type": type_counts,
            "by_connection": connection_type_counts,
            "firmware_status": firmware_status,
            "tls_enabled": sum(1 for device in devices if device.supports_tls),
            "tls_disabled": sum(1 for device in devices if not device.supports_tls),
        }
        
    async def get_device_status_distribution(self) -> Dict[str, Any]:
        """Get distribution of device statuses for dashboard charts"""
        devices = await self.get_all_devices()
        
        # Calculate device status distribution
        status_counts = {
            "online": 0,
            "offline": 0,
            "maintenance": 0,
            "warning": 0,
            "error": 0
        }
        
        for device in devices:
            if device.is_online:
                # Example status determination logic
                if device.firmware_version and "beta" in device.firmware_version:
                    status_counts["warning"] += 1
                elif getattr(device, "error_count", 0) > 0:
                    status_counts["error"] += 1
                elif getattr(device, "maintenance_mode", False):
                    status_counts["maintenance"] += 1
                else:
                    status_counts["online"] += 1
            else:
                status_counts["offline"] += 1
                
        return {
            "status_distribution": status_counts,
            "total_devices": len(devices)
        }
        
    async def get_recent_devices(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recently added devices"""
        query = select(Device).order_by(Device.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        devices = result.scalars().all()
        
        return [{
            "id": device.hash_id,
            "name": device.name,
            "type": device.device_type,
            "ip_address": device.ip_address,
            "created_at": device.created_at.isoformat() if device.created_at else None,
            "is_online": device.is_online
        } for device in devices]
        
    async def get_device_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of device metrics for dashboard display"""
        devices = await self.get_all_devices()
        
        # Example metrics collection
        temperature_devices = []
        energy_devices = []
        other_metrics = []
        
        for device in devices:
            if device.device_type in ["thermostat", "temperature_sensor"] and device.is_online:
                # Get temperature from device metadata or state
                if device.device_metadata and "state" in device.device_metadata:
                    state = device.device_metadata.get("state", {})
                    if "current_temperature" in state:
                        temperature_devices.append({
                            "id": device.hash_id,
                            "name": device.name,
                            "value": state["current_temperature"],
                            "unit": "°C"
                        })
            
            # Check for energy consumption metrics
            if device.device_type in ["smart_plug", "smart_switch"] and device.is_online:
                if device.device_metadata and "state" in device.device_metadata:
                    state = device.device_metadata.get("state", {})
                    if "power" in state and isinstance(state["power"], (int, float)):
                        energy_devices.append({
                            "id": device.hash_id,
                            "name": device.name,
                            "value": state["power"],
                            "unit": "W"
                        })
        
        return {
            "temperature_devices": temperature_devices[:5],  # Limit to 5 devices
            "energy_devices": energy_devices[:5],  # Limit to 5 devices
            "average_temperature": sum(d["value"] for d in temperature_devices) / len(temperature_devices) if temperature_devices else None,
            "total_energy": sum(d["value"] for d in energy_devices) if energy_devices else None,
            "metrics_count": len(temperature_devices) + len(energy_devices) + len(other_metrics)
        }
    
    async def get_device_by_id(self, device_id: str) -> Optional[Device]:
        """Get a device by hash_id"""
        query = select(Device).where(Device.hash_id == device_id)
        result = await self.db.execute(query)
        return result.scalars().first()
        
    async def get_device_by_legacy_id(self, legacy_id: int) -> Optional[Device]:
        """Get a device by legacy integer ID"""
        query = select(Device).where(Device.id == legacy_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_device_by_ip(self, ip_address: str) -> Optional[Device]:
        """Get a device by IP address"""
        result = await self.db.execute(select(Device).where(Device.ip_address == ip_address))
        return result.scalars().first()
    
    async def get_device_by_mac(self, mac_address: str) -> Optional[Device]:
        """Get a device by MAC address"""
        result = await self.db.execute(select(Device).where(Device.mac_address == mac_address))
        return result.scalars().first()
    
    async def create_device(self, device_data: Dict[str, Any]) -> Device:
        """Create a new device"""
        device = Device(**device_data)
        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)
        
        # Log device creation activity
        await self.activity_service.log_system_event(
            action="create_device",
            description=f"Device {device.name} created",
            target_type="device",
            target_id=device.id,
            target_name=device.name,
            metadata={
                "ip_address": device.ip_address,
                "mac_address": device.mac_address,
                "device_type": device.device_type
            }
        )
        
        return device
    
    async def update_device(self, device_id: int, device_data: Dict[str, Any], user_id: Optional[int] = None, user_ip: Optional[str] = None) -> Optional[Device]:
        """Update an existing device"""
        device = await self.get_device_by_id(device_id)
        if not device:
            return None
        
        # Store previous state for activity log
        previous_state = device.to_dict()
        
        for key, value in device_data.items():
            if hasattr(device, key):
                setattr(device, key, value)
        
        device.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(device)
        
        # Log device update activity
        await self.activity_service.log_device_state_change(
            device_id=device.id,
            device_name=device.name,
            action="update_device",
            previous_state=previous_state,
            new_state=device.to_dict(),
            user_id=user_id,
            user_ip=user_ip,
            description=f"Device {device.name} updated"
        )
        
        return device
    
    async def delete_device(self, device_id: int, user_id: Optional[int] = None, user_ip: Optional[str] = None) -> bool:
        """Delete a device"""
        device = await self.get_device_by_id(device_id)
        if not device:
            return False
        
        # Store device info for activity log
        device_info = device.to_dict()
        device_name = device.name
        
        await self.db.delete(device)
        await self.db.commit()
        
        # Log device deletion activity
        if user_id:
            await self.activity_service.log_user_action(
                user_id=user_id,
                user_ip=user_ip or "unknown",
                action="delete_device",
                description=f"Device {device_name} deleted",
                target_type="device",
                target_id=device_id,
                target_name=device_name,
                metadata=device_info
            )
        else:
            await self.activity_service.log_system_event(
                action="delete_device",
                description=f"Device {device_name} deleted",
                target_type="device",
                target_id=device_id,
                target_name=device_name,
                metadata=device_info
            )
        
        return True
    
    async def update_device_status(self, device_id: int, is_online: bool, user_id: Optional[int] = None, user_ip: Optional[str] = None) -> Optional[Device]:
        """Update a device's online status with proper transaction handling"""
        # Use a transaction to handle potential race conditions
        try:
            # Start transaction
            async with self.db.begin():
                # Get device with row-level locking to prevent race conditions
                result = await self.db.execute(
                    select(Device)
                    .where(Device.id == device_id)
                    .with_for_update()  # This locks the row until transaction completes
                )
                device = result.scalars().first()
                
                if not device:
                    return None
                
                # No change in status, just return the device
                if device.is_online == is_online:
                    return device
                
                # Store previous state for activity log
                previous_state = device.to_dict()
                
                # Update status with timestamp
                device.is_online = is_online
                device.last_seen = datetime.utcnow() if is_online else device.last_seen
                
                # The commit will happen automatically when the transaction block exits
                
            # Refresh device outside transaction
            await self.db.refresh(device)
            
        except Exception as e:
            # Log error but don't raise it to prevent API failures on status updates
            logger.error(f"Error updating device status for device {device_id}: {str(e)}")
            return None
        
        # Log device status change activity
        action = "device_online" if is_online else "device_offline"
        description = f"Device {device.name} is now {'online' if is_online else 'offline'}"
        
        await self.activity_service.log_device_state_change(
            device_id=device.id,
            device_name=device.name,
            action=action,
            previous_state=previous_state,
            new_state=device.to_dict(),
            user_id=user_id,
            user_ip=user_ip,
            description=description
        )
        
        return device
    
    async def control_device(self, 
                            device_id: int, 
                            action: str, 
                            parameters: Optional[Dict[str, Any]] = None,
                            user_id: Optional[int] = None,
                            user_ip: Optional[str] = None) -> Dict[str, Any]:
        """
        Control a device with various actions
        
        Args:
            device_id: ID of the device to control
            action: Action to perform (turn_on, turn_off, set_brightness, etc.)
            parameters: Additional parameters for the action
            user_id: ID of the user performing the action
            user_ip: IP address of the user
            
        Returns:
            Dict with result of the action
        """
        device = await self.get_device_by_id(device_id)
        if not device:
            return {"success": False, "error": "Device not found"}
        
        parameters = parameters or {}
        previous_state = device.to_dict()
        result = {"success": True, "device_id": device_id, "action": action}
        
        # Extract device metadata for manipulation
        metadata = device.device_metadata or {}
        
        # Handle common device actions based on device type
        if device.device_type == "light":
            result.update(await self._control_light(device, action, parameters, metadata))
        elif device.device_type == "thermostat":
            result.update(await self._control_thermostat(device, action, parameters, metadata))
        elif device.device_type == "camera":
            result.update(await self._control_camera(device, action, parameters, metadata))
        elif device.device_type == "speaker":
            result.update(await self._control_speaker(device, action, parameters, metadata))
        elif device.device_type == "lock":
            result.update(await self._control_lock(device, action, parameters, metadata))
        elif device.device_type == "switch":
            result.update(await self._control_switch(device, action, parameters, metadata))
        elif device.device_type == "sensor":
            result.update(await self._control_sensor(device, action, parameters, metadata))
        else:
            # Generic device control
            result.update(await self._control_generic(device, action, parameters, metadata))
        
        # Update device with new metadata
        device.device_metadata = metadata
        device.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(device)
        
        # Log device control activity
        await self.activity_service.log_device_control(
            device_id=device.id,
            device_name=device.name,
            action=action,
            parameters=parameters,
            previous_state=previous_state,
            new_state=device.to_dict(),
            user_id=user_id,
            user_ip=user_ip,
            result=result,
            description=f"Device {device.name} controlled with action: {action}"
        )
        
        # Return result
        return result
    
    async def _control_light(self, device: Device, action: str, parameters: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle light control actions"""
        result = {}
        
        # Initialize light state if not present
        if "state" not in metadata:
            metadata["state"] = {
                "power": "off",
                "brightness": 100,
                "color_temp": 2700,
                "color": {"r": 255, "g": 255, "b": 255},
                "effect": None,
                "last_updated": datetime.utcnow().isoformat()
            }
        
        # Handle light actions
        if action == "turn_on":
            metadata["state"]["power"] = "on"
            result["state"] = "on"
            
            # Handle brightness
            if "brightness" in parameters:
                brightness = max(1, min(100, int(parameters["brightness"])))
                metadata["state"]["brightness"] = brightness
                result["brightness"] = brightness
                
            # Handle color temperature
            if "color_temp" in parameters:
                color_temp = max(2000, min(6500, int(parameters["color_temp"])))
                metadata["state"]["color_temp"] = color_temp
                result["color_temp"] = color_temp
                
            # Handle color
            if "color" in parameters:
                color = parameters["color"]
                if isinstance(color, dict) and all(k in color for k in ["r", "g", "b"]):
                    metadata["state"]["color"] = {
                        "r": max(0, min(255, int(color["r"]))),
                        "g": max(0, min(255, int(color["g"]))),
                        "b": max(0, min(255, int(color["b"])))
                    }
                    result["color"] = metadata["state"]["color"]
        
        elif action == "turn_off":
            metadata["state"]["power"] = "off"
            result["state"] = "off"
        
        elif action == "toggle":
            new_state = "on" if metadata["state"]["power"] == "off" else "off"
            metadata["state"]["power"] = new_state
            result["state"] = new_state
            
        # Update last_updated timestamp
        metadata["state"]["last_updated"] = datetime.utcnow().isoformat()
        return result
    
    async def _control_thermostat(self, device: Device, action: str, parameters: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle thermostat control actions"""
        result = {}
        
        # Initialize thermostat state if not present
        if "state" not in metadata:
            metadata["state"] = {
                "power": "off",
                "mode": "heat",  # heat, cool, auto
                "target_temperature": 21.0,
                "current_temperature": 21.0,
                "humidity": 45,
                "fan_mode": "auto",  # auto, on
                "last_updated": datetime.utcnow().isoformat()
            }
        
        # Handle thermostat actions
        if action == "turn_on":
            metadata["state"]["power"] = "on"
            result["state"] = "on"
            
        elif action == "turn_off":
            metadata["state"]["power"] = "off"
            result["state"] = "off"
            
        elif action == "set_temperature":
            if "temperature" in parameters:
                temp = float(parameters["temperature"])
                metadata["state"]["target_temperature"] = temp
                result["target_temperature"] = temp
                
        elif action == "set_mode":
            if "mode" in parameters:
                mode = parameters["mode"]
                if mode in ["heat", "cool", "auto"]:
                    metadata["state"]["mode"] = mode
                    result["mode"] = mode
                    
        elif action == "set_fan_mode":
            if "fan_mode" in parameters:
                fan_mode = parameters["fan_mode"]
                if fan_mode in ["auto", "on"]:
                    metadata["state"]["fan_mode"] = fan_mode
                    result["fan_mode"] = fan_mode
        
        # Simulate temperature changes for realistic behavior
        current_temp = metadata["state"]["current_temperature"]
        target_temp = metadata["state"]["target_temperature"]
        
        # Update temperature based on target and mode
        if metadata["state"]["power"] == "on":
            if metadata["state"]["mode"] == "heat" and current_temp < target_temp:
                # Heating up
                metadata["state"]["current_temperature"] = min(
                    target_temp,
                    current_temp + 0.1
                )
            elif metadata["state"]["mode"] == "cool" and current_temp > target_temp:
                # Cooling down
                metadata["state"]["current_temperature"] = max(
                    target_temp,
                    current_temp - 0.1
                )
        
        # Add current state to result
        result["current_temperature"] = metadata["state"]["current_temperature"]
        result["mode"] = metadata["state"]["mode"]
        result["power"] = metadata["state"]["power"]
        
        # Update last_updated timestamp
        metadata["state"]["last_updated"] = datetime.utcnow().isoformat()
        return result
        
    async def _control_camera(self, device: Device, action: str, parameters: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle camera control actions"""
        result = {}
        
        # Initialize camera state if not present
        if "state" not in metadata:
            metadata["state"] = {
                "power": "off",
                "recording": False,
                "motion_detection": False,
                "night_mode": "auto",
                "resolution": "1080p",
                "rotation": 0,
                "zoom": 1.0,
                "last_updated": datetime.utcnow().isoformat()
            }
        
        # Handle camera actions
        if action == "turn_on":
            metadata["state"]["power"] = "on"
            result["state"] = "on"
            
        elif action == "turn_off":
            metadata["state"]["power"] = "off"
            metadata["state"]["recording"] = False
            result["state"] = "off"
            result["recording"] = False
            
        elif action == "start_recording":
            if metadata["state"]["power"] == "on":
                metadata["state"]["recording"] = True
                result["recording"] = True
            else:
                result["success"] = False
                result["error"] = "Camera is powered off"
                
        elif action == "stop_recording":
            metadata["state"]["recording"] = False
            result["recording"] = False
            
        elif action == "set_night_mode":
            if "mode" in parameters:
                mode = parameters["mode"]
                if mode in ["auto", "on", "off"]:
                    metadata["state"]["night_mode"] = mode
                    result["night_mode"] = mode
                    
        elif action == "set_motion_detection":
            if "enabled" in parameters:
                enabled = bool(parameters["enabled"])
                metadata["state"]["motion_detection"] = enabled
                result["motion_detection"] = enabled
                
        elif action == "set_resolution":
            if "resolution" in parameters:
                resolution = parameters["resolution"]
                if resolution in ["720p", "1080p", "2k", "4k"]:
                    metadata["state"]["resolution"] = resolution
                    result["resolution"] = resolution
                    
        elif action == "pan_tilt_zoom":
            if "zoom" in parameters:
                zoom = float(parameters["zoom"])
                if 1.0 <= zoom <= 10.0:
                    metadata["state"]["zoom"] = zoom
                    result["zoom"] = zoom
            
            if "rotation" in parameters:
                rotation = int(parameters["rotation"])
                if 0 <= rotation < 360:
                    metadata["state"]["rotation"] = rotation
                    result["rotation"] = rotation
        
        # Update last_updated timestamp
        metadata["state"]["last_updated"] = datetime.utcnow().isoformat()
        return result
    
    async def _control_speaker(self, device: Device, action: str, parameters: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle speaker control actions"""
        result = {}
        
        # Initialize speaker state if not present
        if "state" not in metadata:
            metadata["state"] = {
                "power": "off",
                "volume": 50,
                "muted": False,
                "playing": False,
                "source": "bluetooth",
                "track": None,
                "last_updated": datetime.utcnow().isoformat()
            }
        
        # Handle speaker actions
        if action == "turn_on":
            metadata["state"]["power"] = "on"
            result["state"] = "on"
            
        elif action == "turn_off":
            metadata["state"]["power"] = "off"
            metadata["state"]["playing"] = False
            result["state"] = "off"
            result["playing"] = False
            
        elif action == "set_volume":
            if "volume" in parameters:
                volume = max(0, min(100, int(parameters["volume"])))
                metadata["state"]["volume"] = volume
                result["volume"] = volume
                
        elif action == "mute":
            metadata["state"]["muted"] = True
            result["muted"] = True
            
        elif action == "unmute":
            metadata["state"]["muted"] = False
            result["muted"] = False
            
        elif action == "play":
            if metadata["state"]["power"] == "on":
                metadata["state"]["playing"] = True
                result["playing"] = True
                
                if "track" in parameters:
                    metadata["state"]["track"] = parameters["track"]
                    result["track"] = parameters["track"]
            else:
                result["success"] = False
                result["error"] = "Speaker is powered off"
                
        elif action == "pause":
            metadata["state"]["playing"] = False
            result["playing"] = False
            
        elif action == "next_track":
            result["track_changed"] = True
            
        elif action == "previous_track":
            result["track_changed"] = True
            
        elif action == "set_source":
            if "source" in parameters:
                source = parameters["source"]
                if source in ["bluetooth", "aux", "wifi", "optical"]:
                    metadata["state"]["source"] = source
                    result["source"] = source
        
        # Update last_updated timestamp
        metadata["state"]["last_updated"] = datetime.utcnow().isoformat()
        return result
    
    async def _control_lock(self, device: Device, action: str, parameters: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle smart lock control actions"""
        result = {}
        
        # Initialize lock state if not present
        if "state" not in metadata:
            metadata["state"] = {
                "locked": True,
                "battery": 100,
                "auto_lock_enabled": True,
                "auto_lock_delay": 30,  # seconds
                "last_user": None,
                "last_action": None,
                "last_updated": datetime.utcnow().isoformat()
            }
        
        # Handle lock actions
        if action == "lock":
            metadata["state"]["locked"] = True
            result["locked"] = True
            metadata["state"]["last_action"] = "lock"
            
            if user_id := parameters.get("user_id"):
                metadata["state"]["last_user"] = user_id
                result["user_id"] = user_id
                
        elif action == "unlock":
            metadata["state"]["locked"] = False
            result["locked"] = False
            metadata["state"]["last_action"] = "unlock"
            
            if user_id := parameters.get("user_id"):
                metadata["state"]["last_user"] = user_id
                result["user_id"] = user_id
                
        elif action == "set_auto_lock":
            if "enabled" in parameters:
                enabled = bool(parameters["enabled"])
                metadata["state"]["auto_lock_enabled"] = enabled
                result["auto_lock_enabled"] = enabled
                
            if "delay" in parameters:
                delay = max(5, min(300, int(parameters["delay"])))
                metadata["state"]["auto_lock_delay"] = delay
                result["auto_lock_delay"] = delay
        
        # Update battery level (simulate drain)
        metadata["state"]["battery"] = max(0, metadata["state"]["battery"] - random.uniform(0, 0.1))
        result["battery"] = metadata["state"]["battery"]
        
        # Update last_updated timestamp
        metadata["state"]["last_updated"] = datetime.utcnow().isoformat()
        return result
    
    async def _control_switch(self, device: Device, action: str, parameters: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle switch control actions"""
        result = {}
        
        # Initialize switch state if not present
        if "state" not in metadata:
            metadata["state"] = {
                "power": "off",
                "timer_active": False,
                "timer_duration": 0,
                "last_updated": datetime.utcnow().isoformat()
            }
        
        # Handle switch actions
        if action == "turn_on":
            metadata["state"]["power"] = "on"
            result["state"] = "on"
            
        elif action == "turn_off":
            metadata["state"]["power"] = "off"
            result["state"] = "off"
            
        elif action == "toggle":
            new_state = "on" if metadata["state"]["power"] == "off" else "off"
            metadata["state"]["power"] = new_state
            result["state"] = new_state
            
        elif action == "set_timer":
            if "duration" in parameters:
                duration = max(0, int(parameters["duration"]))
                if duration > 0:
                    metadata["state"]["timer_active"] = True
                    metadata["state"]["timer_duration"] = duration
                    result["timer_active"] = True
                    result["timer_duration"] = duration
                else:
                    metadata["state"]["timer_active"] = False
                    metadata["state"]["timer_duration"] = 0
                    result["timer_active"] = False
        
        # Update last_updated timestamp
        metadata["state"]["last_updated"] = datetime.utcnow().isoformat()
        return result
    
    async def _control_sensor(self, device: Device, action: str, parameters: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle sensor control actions"""
        result = {}
        
        # Initialize sensor state if not present
        sensor_type = device.model or "environmental"
        
        if "state" not in metadata:
            if sensor_type == "motion":
                metadata["state"] = {
                    "detected": False,
                    "sensitivity": 5,  # 1-10
                    "last_detected": None,
                    "battery": 100,
                    "last_updated": datetime.utcnow().isoformat()
                }
            elif sensor_type == "door":
                metadata["state"] = {
                    "open": False,
                    "battery": 100,
                    "last_changed": None,
                    "last_updated": datetime.utcnow().isoformat()
                }
            elif sensor_type == "temperature":
                metadata["state"] = {
                    "temperature": 21.0,
                    "humidity": 45,
                    "battery": 100,
                    "last_updated": datetime.utcnow().isoformat()
                }
            else:
                metadata["state"] = {
                    "value": 0,
                    "battery": 100,
                    "last_updated": datetime.utcnow().isoformat()
                }
        
        # Handle sensor actions
        if action == "set_sensitivity" and sensor_type == "motion":
            if "sensitivity" in parameters:
                sensitivity = max(1, min(10, int(parameters["sensitivity"])))
                metadata["state"]["sensitivity"] = sensitivity
                result["sensitivity"] = sensitivity
                
        elif action == "simulate_trigger":
            if sensor_type == "motion":
                metadata["state"]["detected"] = True
                metadata["state"]["last_detected"] = datetime.utcnow().isoformat()
                result["detected"] = True
                result["last_detected"] = metadata["state"]["last_detected"]
                
                # Auto-reset after a short time
                metadata["state"]["detected"] = False
                
            elif sensor_type == "door":
                metadata["state"]["open"] = not metadata["state"]["open"]
                metadata["state"]["last_changed"] = datetime.utcnow().isoformat()
                result["open"] = metadata["state"]["open"]
                result["last_changed"] = metadata["state"]["last_changed"]
                
            elif sensor_type == "temperature":
                if "temperature" in parameters:
                    metadata["state"]["temperature"] = float(parameters["temperature"])
                    result["temperature"] = metadata["state"]["temperature"]
                    
                if "humidity" in parameters:
                    metadata["state"]["humidity"] = float(parameters["humidity"])
                    result["humidity"] = metadata["state"]["humidity"]
                    
            else:
                if "value" in parameters:
                    metadata["state"]["value"] = parameters["value"]
                    result["value"] = metadata["state"]["value"]
        
        # Update battery level (simulate drain)
        metadata["state"]["battery"] = max(0, metadata["state"]["battery"] - random.uniform(0, 0.05))
        result["battery"] = metadata["state"]["battery"]
        
        # Update last_updated timestamp
        metadata["state"]["last_updated"] = datetime.utcnow().isoformat()
        return result
    
    async def _control_generic(self, device: Device, action: str, parameters: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generic device control actions"""
        result = {}
        
        # Initialize generic state if not present
        if "state" not in metadata:
            metadata["state"] = {
                "power": "off",
                "last_updated": datetime.utcnow().isoformat()
            }
        
        # Handle generic actions
        if action == "turn_on":
            metadata["state"]["power"] = "on"
            result["state"] = "on"
            
        elif action == "turn_off":
            metadata["state"]["power"] = "off"
            result["state"] = "off"
            
        elif action == "toggle":
            new_state = "on" if metadata["state"]["power"] == "off" else "off"
            metadata["state"]["power"] = new_state
            result["state"] = new_state
            
        elif action == "set_property":
            # Allow setting arbitrary properties
            for key, value in parameters.items():
                metadata["state"][key] = value
                result[key] = value
        
        # Update last_updated timestamp
        metadata["state"]["last_updated"] = datetime.utcnow().isoformat()
        return result
        
    async def scan_and_update_devices(self) -> List[Device]:
        """
        Simulate device discovery and update database
        
        Returns:
            Updated list of devices
        """
        # Simulate network delay
        await simulate_network_delay()
        
        # Get existing devices
        existing_devices = await self.get_all_devices()
        updated_devices = []
        
        # Simulate device discovery by randomly updating existing devices
        for device in existing_devices:
            # Simulate device going offline
            if simulate_failures(probability=0.1):  # 10% chance of device going offline
                update_data = {
                    "is_online": False,
                    "last_seen": datetime.utcnow()
                }
            else:
                # Simulate device staying online with updated properties
                update_data = {
                    "is_online": True,
                    "last_seen": datetime.utcnow(),
                    "device_metadata": {
                        "state": {
                            "battery": max(0, random.uniform(0, 100)),
                            "signal_strength": random.randint(1, 5),
                            "last_update": datetime.utcnow().isoformat()
                        }
                    }
                }
            
            # Update device
            updated_device = await self.update_device(device.id, update_data)
            if updated_device:
                updated_devices.append(updated_device)
        
        # Simulate discovering new devices (rare event)
        if random.random() < 0.05:  # 5% chance of discovering a new device
            new_device_data = {
                "name": f"Simulated_Device_{random.randint(1000, 9999)}",
                "ip_address": f"192.168.1.{random.randint(2, 254)}",
                "mac_address": f"00:11:22:33:44:{random.randint(10, 99):02x}",
                "device_type": random.choice(["router", "camera", "thermostat", "sensor"]),
                "manufacturer": random.choice(["Simulated", "Virtual", "Test"]),
                "is_online": True,
                "discovery_method": "simulation",
                "ports": self._generate_virtual_ports(),
                "discovery_info": {
                    "discovered_at": datetime.utcnow().isoformat(),
                    "simulated": True
                }
            }
            
            # Create new device
            new_device = await self.create_device(new_device_data)
            if new_device:
                updated_devices.append(new_device)
        
        return updated_devices
    
    def _generate_virtual_ports(self) -> Dict[str, str]:
        """Generate virtual port information"""
        ports = {
            "80": "http",
            "443": "https"
        }
        
        # Randomly add additional ports
        if random.choice([True, False]):
            ports["8080"] = "http-alt"
        if random.choice([True, False]):
            ports["1883"] = "mqtt"
        if random.choice([True, False]):
            ports["5683"] = "coap"
            
        return ports
    
    async def scan_network(self) -> Dict[str, Any]:
        """
        Simulate network scanning
        
        Returns:
            Dict with simulated scan results
        """
        try:
            # Simulate network delay
            await simulate_network_delay()
            
            # Update devices with simulated data
            updated_devices = await self.scan_and_update_devices()
            
            return {
                "status": "completed",
                "devices_found": len(updated_devices),
                "timestamp": datetime.utcnow().isoformat(),
                "simulated": True
            }
        except Exception as e:
            logger.error(f"Error in simulated network scan: {str(e)}")
            return {"error": str(e), "status": "failed", "simulated": True}
    
    async def get_scan_results(self, scan_id: str) -> Dict[str, Any]:
        """Get results of a previous scan"""
        if self.device_scanner.current_scan_id == scan_id:
            return self.device_scanner.scan_results
        
        return {"scan_id": scan_id, "status": "not_found", "message": "Scan results not found"}
    
    async def run_vulnerability_scan(self, device_ids: List[int] = None) -> Dict[str, Any]:
        """Run vulnerability scan on devices"""
        try:
            if device_ids:
                # Scan specific devices
                return await self.vulnerability_scanner.scan_multiple_devices(device_ids)
            else:
                # Get all devices
                devices = await self.get_all_devices()
                device_ids = [d.id for d in devices]
                
                # Run scan
                return await self.vulnerability_scanner.scan_multiple_devices(device_ids)
                
        except Exception as e:
            logger.error(f"Error running vulnerability scan: {str(e)}")
            return {"status": "error", "message": f"Error: {str(e)}"}
    
    async def apply_rules(self, device_id: int) -> Dict[str, Any]:
        """
        Apply configured rules to a device
        
        Args:
            device_id: ID of the device to apply rules to
            
        Returns:
            Dict with result of rule application
        """
        device = await self.get_device_by_id(device_id)
        if not device:
            return {"success": False, "error": "Device not found"}
        
        # Use rule service to apply rules
        try:
            from app.services.rule_service import RuleService
            rule_service = RuleService(self.db)
            result = await rule_service.apply_rules_to_device(device_id)
            return result
        except Exception as e:
            logger.error(f"Error applying rules to device {device_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Error applying rules: {str(e)}",
                "device_id": device_id
            }
    
    async def cleanup(self):
        """Clean up resources used by the service"""
        logger.info("Cleaning up device service resources")
        await self.device_scanner.cleanup()
        
    async def get_device_status(self, device_id: int) -> Dict[str, Any]:
        """
        Get detailed device status
        
        Args:
            device_id: ID of the device
            
        Returns:
            Dict with device status details
        """
        device = await self.get_device_by_id(device_id)
        if not device:
            return {"success": False, "error": "Device not found"}
        
        device_dict = device.to_dict()
        
        # Get device metadata for state info
        metadata = device.device_metadata or {}
        state = metadata.get("state", {})
        
        return {
            "device_id": device_id,
            "name": device.name,
            "ip_address": device.ip_address,
            "mac_address": device.mac_address,
            "device_type": device.device_type,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "firmware_version": device.firmware_version,
            "is_online": device.is_online,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "state": state,
            "success": True
        }
        
    async def get_device_history(self, device_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get device activity history
        
        Args:
            device_id: ID of the device
            limit: Maximum number of records to return
            
        Returns:
            List of device activity records
        """
        device = await self.get_device_by_id(device_id)
        if not device:
            return []
        
        # Get device activities
        activities = await self.activity_service.get_device_activities(device_id, limit)
        return activities 