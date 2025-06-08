"""Device Management Service for IoT Platform
This module consolidates device services including:
- Device CRUD operations
- Device scanning and discovery
- Device control functions
- Device metrics and status tracking
"""
import logging
import random
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.device import Device
from app.models.scan import Scan
from app.services.activity_service import ActivityService
# Import create_vulnerability_scanner at runtime to avoid circular imports
from app.utils.simulation import simulate_network_delay, simulate_failures
from app.utils.notification_helper import NotificationHelper

logger = logging.getLogger(__name__)

#-----------------------------------------------------------------
# Device Scanner - Handles device discovery and scanning operations
#-----------------------------------------------------------------
class DeviceScanner:
    """Virtual device simulator that fetches and enhances database devices with simulated properties"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._scan_lock = asyncio.Lock()
        self.current_scan_id = None
        self.scan_results = {}
        self.scan_status = {}
        self._scan_tasks = set()
        # Setup periodic cleanup task
        self._setup_cleanup_task()
    
    def _setup_cleanup_task(self):
        """Set up periodic cleanup task for completed scan tasks"""
        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(self._periodic_scan_cleanup())
        except RuntimeError:
            logger.warning("Could not setup scan task cleanup - no event loop available")
    
    async def _periodic_scan_cleanup(self):
        """Periodically check and clean up completed scan tasks"""
        while True:
            try:
                # Run cleanup every 15 minutes
                await asyncio.sleep(900)
                # Log active tasks count
                active_count = len(self._scan_tasks)
                if active_count > 0:
                    logger.info(f"Current active scan tasks: {active_count}")
                    # Any tasks in _scan_tasks should be automatically removed when done
                    # via the done_callback, but we check for any abandoned tasks
                    
                    # Check for tasks that completed but weren't removed
                    for task in list(self._scan_tasks):
                        if task.done():
                            logger.warning(f"Found completed task that wasn't removed: {task}")
                            self._scan_tasks.discard(task)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scan task cleanup: {str(e)}")
                await asyncio.sleep(60)
                
    async def cleanup(self):
        """Clean up any resources"""
        logger.info("Cleaning up device simulator resources")
        # Cancel the cleanup task if it exists
        if hasattr(self, '_cleanup_task') and self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clear data structures
        self.scan_results.clear()
        self._scan_tasks.clear()
    
    async def start_scan(self, scan_type: str, network_range: Optional[str] = None) -> str:
        """Start a new scan and return its ID"""
        async with self._scan_lock:
            # Check for any running scans
            running_scan = await self.db.execute(
                select(Scan).where(Scan.status == "running")
            )
            if running_scan.scalar_one_or_none():
                raise RuntimeError("A scan is already running")
            
            # Create new scan record with pending status first
            scan_id = str(uuid.uuid4())
            scan = Scan(
                id=scan_id,
                status="pending",  # Start as pending until background task picks it up
                scan_type=scan_type,
                start_time=datetime.utcnow(),
                network_range=network_range
            )
            self.db.add(scan)
            await self.db.commit()
            
            # Start scan in background and return immediately
            # This prevents race condition between db commit and task creation
            task = asyncio.create_task(self._run_scan(scan_id, scan_type, network_range))
            
            # Add done callback to clean up task when finished
            def _done_callback(completed_task):
                self._scan_tasks.discard(completed_task)
                # We don't access result here to avoid exceptions if task failed
                
            task.add_done_callback(_done_callback)
            self._scan_tasks.add(task)
            
            return scan_id
    
    async def _run_scan(self, scan_id: str, scan_type: str, network_range: Optional[str] = None):
        """Run the actual scan operation"""
        try:
            # Update scan to running status
            await self.db.execute(
                update(Scan).where(Scan.id == scan_id).values(
                    status="running",
                )
            )
            await self.db.commit()
            
            logger.info(f"Starting {scan_type} scan with ID {scan_id}")
            
            # Simulate network delay
            await simulate_network_delay()
            
            # Run appropriate scan type
            if scan_type == "discovery":
                devices = await self._run_discovery_scan(network_range)
                result = {"devices_found": len(devices), "devices": devices}
            elif scan_type == "vulnerability":
                result = await self._run_vulnerability_scan()
            else:
                raise ValueError(f"Unknown scan type: {scan_type}")
                
            # Update scan record with success
            await self.db.execute(
                update(Scan).where(Scan.id == scan_id).values(
                    status="completed",
                    end_time=datetime.utcnow(),
                    result=result
                )
            )
            await self.db.commit()
            
            # Store results in memory too
            self.scan_results[scan_id] = result
            self.scan_status[scan_id] = "completed"
            
            logger.info(f"Completed {scan_type} scan with ID {scan_id}")
            return result
            
        except Exception as e:
            logger.error(f"Scan {scan_id} failed: {str(e)}")
            await self._mark_scan_failed(scan_id, str(e))
            raise
    
    async def _mark_scan_failed(self, scan_id: str, error_message: str):
        """Helper to mark a scan as failed with proper error handling"""
        try:
            await self.db.execute(
                update(Scan).where(Scan.id == scan_id).values(
                    status="failed",
                    end_time=datetime.utcnow(),
                    result={"error": error_message}
                )
            )
            await self.db.commit()
            
            # Update in-memory status too
            self.scan_status[scan_id] = "failed"
            self.scan_results[scan_id] = {"error": error_message}
        except Exception as db_error:
            logger.error(f"Error marking scan as failed: {str(db_error)}")
    
    def _validate_network_range(self, network_range: str) -> bool:
        """Validate that a network range is properly formatted and allowed"""
        import re
        import ipaddress
        
        # Check if it's a single IP
        ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        if re.match(ip_pattern, network_range):
            try:
                ip = ipaddress.ip_address(network_range)
                # Check if it's a private IP
                if not ip.is_private:
                    logger.warning(f"Scanning public IP addresses is not allowed: {network_range}")
                    return False
                return True
            except ValueError:
                logger.warning(f"Invalid IP address format: {network_range}")
                return False
                
        # Check if it's a CIDR range
        cidr_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$"
        if re.match(cidr_pattern, network_range):
            try:
                network = ipaddress.ip_network(network_range, strict=False)
                # Check if it's a private network
                if not network.is_private:
                    logger.warning(f"Scanning public networks is not allowed: {network_range}")
                    return False
                # Check if network is too large (more than /16)
                if network.prefixlen < 16:
                    logger.warning(f"Network range too large: {network_range}")
                    return False
                return True
            except ValueError:
                logger.warning(f"Invalid CIDR format: {network_range}")
                return False
                
        # Check if it's a range (e.g., 192.168.1.1-192.168.1.254)
        range_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}-\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        if re.match(range_pattern, network_range):
            try:
                start_ip, end_ip = network_range.split('-')
                start = ipaddress.ip_address(start_ip)
                end = ipaddress.ip_address(end_ip)
                
                # Check if IPs are private
                if not start.is_private or not end.is_private:
                    logger.warning(f"Scanning public IP ranges is not allowed: {network_range}")
                    return False
                
                # Check if range is too large (more than 254 IPs)
                if int(end) - int(start) > 254:
                    logger.warning(f"IP range too large: {network_range}")
                    return False
                
                return True
            except ValueError:
                logger.warning(f"Invalid IP range format: {network_range}")
                return False
        
        logger.warning(f"Unsupported network range format: {network_range}")
        return False
    
    async def _run_discovery_scan(self, network_range: Optional[str] = None) -> List[Dict[str, Any]]:
        """Run a discovery scan to find devices with proper validation"""
        if network_range and not self._validate_network_range(network_range):
            raise ValueError(f"Invalid or disallowed network range: {network_range}")
            
        # In a real system, we'd scan the network here.
        # For this simulation, we'll just return devices from the database
        # with some randomized properties to simulate discovery
        
        # Simulate failures occasionally
        if simulate_failures(0.05):  # 5% chance of failure
            raise RuntimeError("Network scan failed due to connection timeout")
            
        # Simulate a network delay
        await asyncio.sleep(random.uniform(1.5, 3.5))
        
        # Get devices from database
        devices = await self._get_devices_from_db()
        
        # Simulate discovering some new devices that aren't in DB yet
        # (In a real implementation, we'd add these to the database)
        if random.random() < 0.3:  # 30% chance to find a "new" device
            # Generate a fake new device
            fake_new_device = {
                "ip_address": f"192.168.1.{random.randint(100, 250)}",
                "mac_address": ":".join([f"{random.randint(0, 255):02x}" for _ in range(6)]),
                "name": f"Unknown Device {random.randint(1000, 9999)}",
                "manufacturer": random.choice(["Unknown", "Generic", "OEM"]),
                "model": f"Model-{random.randint(100, 999)}",
                "device_type": random.choice(["sensor", "switch", "light", "generic"]),
                "ports": self._generate_default_ports(),
                "is_online": True,
                "last_seen": datetime.utcnow().isoformat(),
                "response_time_ms": random.randint(2, 150),
                "os_info": "Unknown OS",
                "new_device": True  # Flag to indicate this is a new device not in DB
            }
            devices.append(fake_new_device)
            
        # Apply any network range filtering if provided
        if network_range:
            # In a real implementation, we'd filter by the network range
            # For this simulation, we'll just take a random subset of devices
            # to simulate that only some devices are in the given range
            devices = random.sample(devices, max(1, len(devices) // 2))
        
        return devices
    
    async def _run_vulnerability_scan(self) -> Dict[str, Any]:
        """Run a vulnerability scan on known devices"""
        # In a real implementation, we'd integrate with a vulnerability scanner
        # For this simulation, we'll just return a simulated result
        
        # Simulate network delay
        await asyncio.sleep(random.uniform(2.0, 5.0))
        
        # Get devices from database
        devices = await self._get_devices_from_db()
        
        # Simulate vulnerability scan results
        results = {
            "scan_time": datetime.utcnow().isoformat(),
            "devices_scanned": len(devices),
            "vulnerabilities_found": random.randint(0, len(devices) * 2),
            "details": []
        }
        
        # Generate detailed results for each device
        for device in devices:
            device_id = device.get("id", "unknown")
            if random.random() < 0.3:  # 30% chance of finding vulnerabilities
                vuln_count = random.randint(1, 3)
                device_result = {
                    "device_id": device_id,
                    "device_name": device.get("name", "Unknown Device"),
                    "ip_address": device.get("ip_address", "unknown"),
                    "vulnerabilities_found": vuln_count,
                    "risk_level": random.choice(["low", "medium", "high"])
                }
                results["details"].append(device_result)
                
        return results
    
    async def _get_devices_from_db(self) -> List[Dict[str, Any]]:
        """Get devices from database and enhance with virtual properties"""
        try:
            # Get all devices from database
            query = select(Device)
            result = await self.db.execute(query)
            db_devices = result.scalars().all()
            
            # Convert to dictionaries and add virtual properties
            devices = []
            for device in db_devices:
                # Generate virtual ports based on device type
                ports_dict = self._generate_virtual_ports(device.device_type)
                
                # Create device dictionary with actual and simulated properties
                device_dict = {
                    "id": device.hash_id,
                    "legacy_id": device.id,
                    "name": device.name,
                    "ip_address": device.ip_address,
                    "mac_address": device.mac_address,
                    "manufacturer": device.manufacturer,
                    "model": device.model,
                    "device_type": device.device_type,
                    "ports": ports_dict,
                    "is_online": device.is_online,
                    "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                    "response_time_ms": random.randint(2, 150),
                    "os_info": self._get_virtual_os_info(device.device_type, device.manufacturer),
                }
                devices.append(device_dict)
            
            return devices
            
        except Exception as e:
            logger.error(f"Error fetching devices: {str(e)}")
            return []
    
    def _get_virtual_os_info(self, device_type: str, manufacturer: str) -> str:
        """Generate virtual OS info based on device type and manufacturer"""
        os_map = {
            "router": {
                "Cisco": "Cisco IOS",
                "Ubiquiti": "EdgeOS",
                "TP-Link": "TP-Link OS",
                "NETGEAR": "NETGEAR OS",
                "default": "Router OS"
            },
            "camera": {
                "Hikvision": "Hikvision Firmware",
                "Dahua": "Dahua Firmware",
                "Amcrest": "Amcrest Firmware",
                "default": "Camera Firmware"
            },
            "thermostat": {
                "Nest": "Nest OS",
                "Ecobee": "Ecobee Firmware",
                "Honeywell": "Honeywell Firmware",
                "default": "Thermostat Firmware"
            },
            "default": "IoT Firmware"
        }
        
        device_map = os_map.get(device_type, os_map["default"])
        if isinstance(device_map, dict):
            return device_map.get(manufacturer, device_map["default"])
        return device_map
    
    def _generate_virtual_ports(self, device_type: str) -> Dict[str, str]:
        """Generate virtual port information based on device type"""
        if device_type == "router":
            return self._generate_router_ports()
        elif device_type == "camera":
            return self._generate_camera_ports()
        elif device_type == "thermostat":
            return self._generate_thermostat_ports()
        else:
            return self._generate_default_ports()
    
    def _generate_router_ports(self) -> Dict[str, str]:
        """Generate virtual router ports"""
        ports = {
            "80": "http",
            "443": "https"
        }
        
        # Randomly add additional ports
        if random.choice([True, False]):
            ports["22"] = "ssh"
        if random.choice([True, False]):
            ports["23"] = "telnet"
        if random.choice([True, False]):
            ports["53"] = "domain"
        
        return ports
    
    def _generate_camera_ports(self) -> Dict[str, str]:
        """Generate virtual camera ports"""
        ports = {
            "80": "http",
            "554": "rtsp"
        }
        
        # Randomly add additional ports
        if random.choice([True, False]):
            ports["443"] = "https"
        if random.choice([True, True, False]):  # More likely
            ports["8080"] = "http-alt"
        
        return ports
    
    def _generate_thermostat_ports(self) -> Dict[str, str]:
        """Generate virtual thermostat ports"""
        ports = {
            "80": "http",
        }
        
        # Randomly add additional ports
        if random.choice([True, False]):
            ports["443"] = "https"
            
        return ports
    
    def _generate_default_ports(self) -> Dict[str, str]:
        """Generate default virtual ports"""
        ports = {}
        
        if random.choice([True, True, False]):  # 2/3 chance
            ports["80"] = "http"
        if random.choice([True, False]):  # 1/2 chance
            ports["443"] = "https"
            
        return ports
#-----------------------------------------------------------------
# Device Service - Handles device CRUD operations and control functions
#-----------------------------------------------------------------
# Factory function to create a DeviceScanner instance
def create_device_scanner(db: AsyncSession) -> DeviceScanner:
    """Create and return a DeviceScanner instance"""
    return DeviceScanner(db)

class DeviceService:
    """Service for managing IoT devices"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # Create scanner instances with DB session
        self.device_scanner = create_device_scanner(db)
        # Lazy import to avoid circular dependency
        from app.services.security_service import create_vulnerability_scanner
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
            if not device.is_online:
                status_counts["offline"] += 1
                continue
                
            # For online devices, determine status
            if getattr(device, "maintenance_mode", False):
                status_counts["maintenance"] += 1
            elif getattr(device, "error_state", False):
                status_counts["error"] += 1
            elif device.firmware_version and "beta" in device.firmware_version.lower():
                status_counts["warning"] += 1
            else:
                status_counts["online"] += 1
                
        return {
            "status_distribution": status_counts,
            "total_devices": len(devices)
        }
    
    async def get_recent_devices(self, limit: int = 5) -> List[Device]:
        """Get recently added devices"""
        query = select(Device).order_by(Device.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_device_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of device metrics for dashboard display"""
        devices = await self.get_all_devices()
        
        # Calculate device metrics by type
        device_types = {}
        manufacturers = {}
        connection_protocols = {
            "http": 0,
            "mqtt": 0,
            "coap": 0,
            "websocket": 0
        }
        
        total_devices = len(devices)
        for device in devices:
            # Count by device type
            device_type = device.device_type
            if device_type not in device_types:
                device_types[device_type] = 0
            device_types[device_type] += 1
            
            # Count by manufacturer
            manufacturer = device.manufacturer
            if manufacturer not in manufacturers:
                manufacturers[manufacturer] = 0
            manufacturers[manufacturer] += 1
            
            # Count connection protocols
            if device.supports_http:
                connection_protocols["http"] += 1
            if device.supports_mqtt:
                connection_protocols["mqtt"] += 1
            if device.supports_coap:
                connection_protocols["coap"] += 1
            if device.supports_websocket:
                connection_protocols["websocket"] += 1
        
        # Calculate percentages for pie charts
        device_type_percentages = {
            device_type: (count / total_devices) * 100 
            for device_type, count in device_types.items()
        }
        
        # Get top manufacturers (limited to top 5)
        top_manufacturers = sorted(
            manufacturers.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        return {
            "device_types": device_types,
            "device_type_percentages": device_type_percentages,
            "top_manufacturers": dict(top_manufacturers),
            "connection_protocols": connection_protocols,
            "total_devices": total_devices
        }
    
    async def get_device_by_id(self, device_id: str) -> Optional[Device]:
        """Get a device by hash_id"""
        query = select(Device).where(Device.hash_id == device_id)
        result = await self.db.execute(query)
        device = result.scalar_one_or_none()
        
        # Critical: ensure is_online status and device metadata power state are in sync
        if device and device.device_metadata:
            # Handle device_metadata properly whether it's a string or dict
            metadata = device.device_metadata
            if isinstance(metadata, str):
                try:
                    import json
                    metadata = json.loads(metadata)
                except:
                    # If can't parse as JSON, skip sync check
                    return device
                    
            # Now safely access nested state
            if isinstance(metadata, dict) and 'state' in metadata:
                device_state = metadata.get('state', {})
                # If device metadata indicates it's powered off, ensure is_online reflects that
                if isinstance(device_state, dict) and device_state.get('power') is False and device.is_online:
                    logger.warning(f"Device {device_id} has inconsistent state: metadata shows powered off but is_online=True. Fixing...")
                    device.is_online = False
                    await self.db.commit()
        
        return device
    
    async def get_device_by_legacy_id(self, legacy_id: int) -> Optional[Device]:
        """Get a device by legacy integer ID"""
        query = select(Device).where(Device.id == legacy_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_device_by_ip(self, ip_address: str) -> Optional[Device]:
        """Get a device by IP address"""
        query = select(Device).where(Device.ip_address == ip_address)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_device_by_mac(self, mac_address: str) -> Optional[Device]:
        """Get a device by MAC address"""
        query = select(Device).where(Device.mac_address == mac_address)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_device(self, device_data: Dict[str, Any]) -> Device:
        """Create a new device"""
        # Generate a hash ID if not provided
        if "hash_id" not in device_data:
            device_data["hash_id"] = str(uuid.uuid4())
            
        # Set created timestamp
        device_data["created_at"] = datetime.utcnow()
        device_data["updated_at"] = datetime.utcnow()
        
        # Create device object
        device = Device(**device_data)
        self.db.add(device)
        
        try:
            await self.db.commit()
            await self.db.refresh(device)
            
            # Log activity
            await self.activity_service.log_activity(
                activity_type="user_action",
                action="device_created",
                description=f"Device {device.name} was created",
                target_type="device",
                target_id=device.hash_id,
                target_name=device.name,
                metadata={"device": device.name, "manufacturer": device.manufacturer}
            )
            
            return device
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating device: {str(e)}")
            raise
    
    async def update_device(self, device_id: str, device_data: Dict[str, Any], 
                          user_id: Optional[int] = None, 
                          user_ip: Optional[str] = None) -> Optional[Device]:
        """Update an existing device"""
        # Get device
        device = await self.get_device_by_id(device_id)
        if not device:
            return None
            
        # Save original values for activity log
        original_values = {
            "name": device.name,
            "is_online": device.is_online,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "firmware_version": device.firmware_version
        }
        
        # Update timestamp
        device_data["updated_at"] = datetime.utcnow()
        
        # Update device
        for key, value in device_data.items():
            # Skip hash_id as that shouldn't be updated
            if key != "hash_id" and hasattr(device, key):
                setattr(device, key, value)
        
        try:
            await self.db.commit()
            await self.db.refresh(device)
            
            # Log activity with changed fields
            changed_fields = {
                key: device_data[key]
                for key in device_data.keys()
                if key in original_values and original_values[key] != device_data[key]
            }
            
            if changed_fields:
                await self.activity_service.log_activity(
                    activity_type="user_action",
                    action="device_updated",
                    description=f"Device {device.name} was updated",
                    target_type="device",
                    target_id=device.hash_id,
                    target_name=device.name,
                    user_id=user_id,
                    user_ip=user_ip,
                    metadata={
                        "device": device.name,
                        "changes": changed_fields,
                        "original_values": {k: original_values[k] for k in changed_fields}
                    }
                )
            
            # If device name or status changed, send notification
            if ("name" in changed_fields or "is_online" in changed_fields):
                notification_helper = NotificationHelper()
                await notification_helper.notify_device_update(
                    device.hash_id, 
                    device.name, 
                    changed_fields
                )
            
            return device
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating device {device_id}: {str(e)}")
            raise
    
    async def delete_device(self, device_id: str, 
                          user_id: Optional[int] = None, 
                          user_ip: Optional[str] = None) -> bool:
        """Delete a device"""
        # Get device
        device = await self.get_device_by_id(device_id)
        if not device:
            return False
            
        # Save device info for activity log
        device_info = {
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "ip_address": device.ip_address,
            "mac_address": device.mac_address
        }
        
        try:
            # Delete the device
            await self.db.delete(device)
            await self.db.commit()
            
            # Log activity
            await self.activity_service.log_activity(
                activity_type="user_action",
                action="device_deleted",
                description=f"Device {device_info.get('name', 'unknown')} was deleted",
                target_type="device",
                target_id=device_id,  # Use the ID even though device is deleted
                target_name=device_info.get('name', 'unknown'),
                user_id=user_id,
                user_ip=user_ip,
                metadata={"device": device_info}
            )
            
            # Send notification about device deletion
            notification_helper = NotificationHelper()
            await notification_helper.notify_device_deletion(
                device_id, 
                device_info["name"]
            )
            
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting device {device_id}: {str(e)}")
            raise
    
    async def update_device_status(self, device_id: int, is_online: bool,
                                user_id: Optional[int] = None,
                                user_ip: Optional[str] = None) -> Optional[Device]:
        """Update a device's online status with proper transaction handling"""
        # Get device
        device = await self.get_device_by_legacy_id(device_id)
        if not device:
            return None
            
        # Check if status actually changed
        if device.is_online == is_online:
            return device  # No change needed
            
        # Save original status
        original_status = device.is_online
        
        # Update status
        device.is_online = is_online
        device.last_seen = datetime.utcnow() if is_online else device.last_seen
        device.updated_at = datetime.utcnow()
        
        try:
            await self.db.commit()
            await self.db.refresh(device)
            
            # Log activity
            status_text = "online" if is_online else "offline"
            await self.activity_service.log_activity(
                activity_type="system_event",
                action="device_status_changed",
                description=f"Device {device.name} changed status to {status_text}",
                target_type="device",
                target_id=device.hash_id,
                target_name=device.name,
                user_id=user_id,
                user_ip=user_ip,
                metadata={
                    "device": device.name,
                    "new_status": status_text,
                    "previous_status": "online" if original_status else "offline"
                }
            )
            
            # Send notification about status change
            notification_helper = NotificationHelper()
            await notification_helper.notify_device_status_change(
                device.hash_id,
                device.name,
                is_online
            )
            
            return device
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating device status for {device_id}: {str(e)}")
            raise
    
    async def control_device(self, device_id: str, 
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
            user_id: Optional ID of the user performing the action
            user_ip: Optional IP address of the user
            
        Returns:
            Dictionary with result of the action
        """
        # Get device
        device = await self.get_device_by_id(device_id)
        if not device:
            return {"success": False, "error": "Device not found"}
        
        # Sanitize device_metadata early to avoid type errors later
        if device.device_metadata and not isinstance(device.device_metadata, dict):
            try:
                import json
                device.device_metadata = json.loads(device.device_metadata)
            except Exception:
                # Fallback to empty dict if parsing fails
                device.device_metadata = {}
                logger.warning(
                    "device_metadata for %s was non-dict and could not be parsed; reset to empty dict", device_id
                )
        
        # Log device status for debugging
        logger.info(
            f"Device control request: device_id={device_id}, is_online={device.is_online}, action={action}, device_type={device.device_type}"
        )
        
        # Special handling for power actions
        action_lower = action.lower()
        
        # Skip online check for turn_on/turn_off actions
        if action_lower not in ["turn_on", "turn_off"] and not device.is_online:
            return {"success": False, "error": "Device is offline"}
            
        # Initialize parameters dict if not provided
        if parameters is None:
            parameters = {}
            
        # Prepare metadata for action log
        metadata = {
            "user_id": user_id,
            "ip_address": user_ip,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Simulate network delay
        await simulate_network_delay()
        
        # Route to appropriate control method based on device type
        result = None
        try:
            device_type = device.device_type.lower()
            
            if device_type == "light":
                result = await self._control_light(device, action, parameters, metadata)
            elif device_type == "thermostat":
                result = await self._control_thermostat(device, action, parameters, metadata)
            elif device_type == "camera":
                result = await self._control_camera(device, action, parameters, metadata)
            elif device_type == "speaker":
                result = await self._control_speaker(device, action, parameters, metadata)
            elif device_type == "lock":
                result = await self._control_lock(device, action, parameters, metadata)
            elif device_type == "switch":
                result = await self._control_switch(device, action, parameters, metadata)
            elif device_type == "sensor" or ("sensor" in device_type):
                # Handle specific sensor sub-types like contact_sensor, motion_sensor, etc.
                result = await self._control_sensor(device, action, parameters, metadata)
            else:
                # Generic device control
                result = await self._control_generic(device, action, parameters, metadata)
            
            # Update device online status based on power actions
            if result and result.get("success", False):
                action_lower = action.lower()
                if action_lower == "turn_on":
                    device.is_online = True
                    await self.db.commit()
                elif action_lower == "turn_off":
                    device.is_online = False
                    await self.db.commit()
            
            # Log activity
            if result and result.get("success", False):
                await self.activity_service.log_activity(
                    activity_type="user_action",
                    action="device_control",
                    description=f"Device {device.name} was controlled with action: {action}",
                    target_type="device",
                    target_id=device.hash_id,
                    target_name=device.name,
                    user_id=user_id,
                    user_ip=user_ip,
                    metadata={
                        "device": device.name,
                        "action": action,
                        "parameters": parameters,
                        "result": "success"
                    }
                )
                
            return result
        except Exception as e:
            logger.error(f"Error controlling device {device_id}: {str(e)}")
            # Log error activity
            await self.activity_service.log_activity(
                activity_type="system_event",
                action="device_control_error",
                description=f"Error controlling device {device.name}: {str(e)}",
                target_type="device",
                target_id=device.hash_id,
                target_name=device.name,
                user_id=user_id,
                user_ip=user_ip,
                metadata={
                    "device": device.name,
                    "action": action,
                    "parameters": parameters,
                    "error": str(e)
                }
            )
            return {"success": False, "error": f"Control error: {str(e)}"}
        
    async def _control_generic(self, device: Device, action: str, parameters: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generic device control method that can handle any device type
        
        Args:
            device: The device to control
            action: The action to perform (turn_on, turn_off, etc.)
            parameters: Additional parameters for the action
            metadata: Metadata about the action
            
        Returns:
            Dictionary with the result of the action
        """
        # Process common actions that apply to most devices
        action = action.lower()
        
        if action == "turn_on":
            # Simulate turning device on
            return {
                "success": True,
                "state": {"power": True},
                "message": f"Device {device.name} turned on"
            }
            
        elif action == "turn_off":
            # Simulate turning device off
            return {
                "success": True,
                "state": {"power": False},
                "message": f"Device {device.name} turned off"
            }
            
        elif action == "restart":
            # Simulate restarting device
            return {
                "success": True,
                "state": {"power": True, "restarted": True},
                "message": f"Device {device.name} restarted"
            }
            
        elif action == "status":
            # Return device status
            return {
                "success": True,
                "state": {"power": True, "online": device.is_online},
                "message": f"Device {device.name} status retrieved"
            }
        
        else:
            # Unknown action
            return {
                "success": False,
                "error": f"Unsupported action '{action}' for device type '{device.device_type}'"
            }
    
    async def _control_light(self, device: Device, action: str, 
                           parameters: Dict[str, Any], 
                           metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle light control actions"""
        # Get current device metadata and state, ensure both are dicts
        raw_metadata = device.device_metadata or {}
        device_metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
        
        raw_state = device_metadata.get("state", {})
        current_state = raw_state if isinstance(raw_state, dict) else {}
        
        # Ensure nested dict fields have proper types
        if not isinstance(current_state.get("color"), dict):
            current_state["color"] = {"r": 255, "g": 255, "b": 255}
        
        # Initialize with defaults if not present
        if "power" not in current_state:
            current_state["power"] = False
        if "brightness" not in current_state:
            current_state["brightness"] = 100
        
        # Process action
        if action == "turn_on":
            current_state["power"] = True
            result = {"success": True, "state": current_state}
        elif action == "turn_off":
            current_state["power"] = False
            result = {"success": True, "state": current_state}
        elif action == "toggle":
            current_state["power"] = not current_state["power"]
            result = {"success": True, "state": current_state}
        elif action == "set_brightness":
            # Validate brightness parameter
            if "brightness" not in parameters:
                return {"success": False, "error": "Missing brightness parameter"}
                
            try:
                brightness = int(parameters["brightness"])
                if not (0 <= brightness <= 100):
                    return {"success": False, "error": "Brightness must be between 0 and 100"}
                    
                current_state["brightness"] = brightness
                # If we're setting brightness > 0, also turn on the light
                if brightness > 0:
                    current_state["power"] = True
                
                result = {"success": True, "state": current_state}
            except ValueError:
                return {"success": False, "error": "Invalid brightness value"}
        elif action == "set_color":
            # Validate color parameters
            color_error = False
            for channel in ["r", "g", "b"]:
                if channel not in parameters:
                    color_error = True
                    break
                try:
                    value = int(parameters[channel])
                    if not (0 <= value <= 255):
                        color_error = True
                        break
                    current_state["color"][channel] = value
                except ValueError:
                    color_error = True
                    break
                    
            if color_error:
                return {"success": False, "error": "Invalid color parameters (r,g,b required, 0-255)"}
                
            result = {"success": True, "state": current_state}
        else:
            return {"success": False, "error": f"Unknown action for light: {action}"}
            
        # Update device metadata with new state
        device_metadata["state"] = current_state
        device.device_metadata = device_metadata
        await self.db.commit()
        
        return result
    
    async def _control_thermostat(self, device: Device, action: str, 
                                parameters: Dict[str, Any], 
                                metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle thermostat control actions"""
        # Get current device state
        device_metadata = device.device_metadata or {}
        current_state = device_metadata.get("state", {})
        
        # Initialize with defaults if not present
        if "power" not in current_state:
            current_state["power"] = False
        if "target_temperature" not in current_state:
            current_state["target_temperature"] = 21.0  # Default 21°C
        if "current_temperature" not in current_state:
            current_state["current_temperature"] = 21.0
        if "mode" not in current_state:
            current_state["mode"] = "heat"  # Options: heat, cool, auto, off
        if "fan" not in current_state:
            current_state["fan"] = "auto"  # Options: auto, on
        if "humidity" not in current_state:
            current_state["humidity"] = 45  # Default 45%
            
        # Process action
        if action == "turn_on":
            current_state["power"] = True
            result = {"success": True, "state": current_state}
        elif action == "turn_off":
            current_state["power"] = False
            result = {"success": True, "state": current_state}
        elif action == "set_temperature":
            # Validate temperature parameter
            if "temperature" not in parameters:
                return {"success": False, "error": "Missing temperature parameter"}
                
            try:
                temp = float(parameters["temperature"])
                # Allow temperature in reasonable range (10-35°C)
                if not (10 <= temp <= 35):
                    return {"success": False, "error": "Temperature must be between 10°C and 35°C"}
                    
                current_state["target_temperature"] = temp
                # If we're setting temperature, also turn on the thermostat
                current_state["power"] = True
                
                result = {"success": True, "state": current_state}
            except ValueError:
                return {"success": False, "error": "Invalid temperature value"}
        elif action == "set_mode":
            # Validate mode parameter
            if "mode" not in parameters:
                return {"success": False, "error": "Missing mode parameter"}
                
            mode = parameters["mode"].lower()
            valid_modes = ["heat", "cool", "auto", "off"]
            
            if mode not in valid_modes:
                return {"success": False, "error": f"Invalid mode. Must be one of: {', '.join(valid_modes)}"}
                
            current_state["mode"] = mode
            # If mode is off, power off the thermostat
            if mode == "off":
                current_state["power"] = False
            else:
                current_state["power"] = True
                
            result = {"success": True, "state": current_state}
        elif action == "set_fan":
            # Validate fan parameter
            if "fan" not in parameters:
                return {"success": False, "error": "Missing fan parameter"}
                
            fan = parameters["fan"].lower()
            valid_fan_modes = ["auto", "on"]
            
            if fan not in valid_fan_modes:
                return {"success": False, "error": f"Invalid fan mode. Must be one of: {', '.join(valid_fan_modes)}"}
                
            current_state["fan"] = fan
            result = {"success": True, "state": current_state}
        else:
            return {"success": False, "error": f"Unknown action for thermostat: {action}"}
            
        # Update device metadata with new state
        device_metadata["state"] = current_state
        device.device_metadata = device_metadata
        await self.db.commit()
        
        return result
    
    async def _control_camera(self, device: Device, action: str, 
                                parameters: Dict[str, Any], 
                                metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle camera control actions"""
        # Get current device state
        device_metadata = device.device_metadata or {}
        current_state = device_metadata.get("state", {})
        
        # Initialize with defaults if not present
        if "power" not in current_state:
            current_state["power"] = False
        if "recording" not in current_state:
            current_state["recording"] = False
        if "motion_detection" not in current_state:
            current_state["motion_detection"] = False
        if "zoom" not in current_state:
            current_state["zoom"] = 1.0  # 1.0 = no zoom
        if "pan" not in current_state:
            current_state["pan"] = 0  # -100 to 100
        if "tilt" not in current_state:
            current_state["tilt"] = 0  # -100 to 100
        if "night_mode" not in current_state:
            current_state["night_mode"] = False
        if "resolution" not in current_state:
            current_state["resolution"] = "1080p"
            
        # Process action
        if action == "turn_on":
            current_state["power"] = True
            result = {"success": True, "state": current_state}
        elif action == "turn_off":
            current_state["power"] = False
            current_state["recording"] = False
            result = {"success": True, "state": current_state}
        elif action == "start_recording":
            if not current_state["power"]:
                return {"success": False, "error": "Camera is powered off"}
                
            current_state["recording"] = True
            result = {"success": True, "state": current_state}
        elif action == "stop_recording":
            current_state["recording"] = False
            result = {"success": True, "state": current_state}
        elif action == "set_motion_detection":
            # Validate motion detection parameter
            if "enabled" not in parameters:
                return {"success": False, "error": "Missing 'enabled' parameter"}
                
            try:
                enabled = bool(parameters["enabled"])
                current_state["motion_detection"] = enabled
                result = {"success": True, "state": current_state}
            except ValueError:
                return {"success": False, "error": "Invalid 'enabled' value"}
        elif action == "set_zoom":
            # Validate zoom parameter
            if "zoom" not in parameters:
                return {"success": False, "error": "Missing zoom parameter"}
                
            try:
                zoom = float(parameters["zoom"])
                # Allow zoom in reasonable range (1.0-10.0)
                if not (1.0 <= zoom <= 10.0):
                    return {"success": False, "error": "Zoom must be between 1.0 and 10.0"}
                    
                current_state["zoom"] = zoom
                result = {"success": True, "state": current_state}
            except ValueError:
                return {"success": False, "error": "Invalid zoom value"}
        elif action == "set_position":
            # Validate pan and tilt parameters
            pan_error = False
            tilt_error = False
            
            if "pan" in parameters:
                try:
                    pan = int(parameters["pan"])
                    if not (-100 <= pan <= 100):
                        pan_error = True
                    else:
                        current_state["pan"] = pan
                except ValueError:
                    pan_error = True
            
            if "tilt" in parameters:
                try:
                    tilt = int(parameters["tilt"])
                    if not (-100 <= tilt <= 100):
                        tilt_error = True
                    else:
                        current_state["tilt"] = tilt
                except ValueError:
                    tilt_error = True
                    
            if pan_error or tilt_error:
                return {"success": False, "error": "Invalid pan/tilt values (must be -100 to 100)"}
                
            result = {"success": True, "state": current_state}
        elif action == "toggle_night_mode":
            current_state["night_mode"] = not current_state["night_mode"]
            result = {"success": True, "state": current_state}
        else:
            # For unsupported actions, fall back to generic control
            return await self._control_generic(device, action, parameters, metadata)
            
        # Update device metadata with new state
        device_metadata["state"] = current_state
        device.device_metadata = device_metadata
        
        # Return success result
        return result
    async def _control_speaker(self, device: Device, action: str, 
                             parameters: Dict[str, Any], 
                             metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle speaker control actions"""
        # Get current device state
        device_metadata = device.device_metadata or {}
        current_state = device_metadata.get("state", {})
        
        # Initialize with defaults if not present
        if "power" not in current_state:
            current_state["power"] = False
        if "volume" not in current_state:
            current_state["volume"] = 50  # 0-100 scale
        if "muted" not in current_state:
            current_state["muted"] = False
        if "playing" not in current_state:
            current_state["playing"] = False
            
        # Process action
        if action == "turn_on":
            current_state["power"] = True
            result = {"success": True, "state": current_state}
        elif action == "turn_off":
            current_state["power"] = False
            current_state["playing"] = False
            result = {"success": True, "state": current_state}
        elif action == "set_volume":
            # Validate volume parameter
            if "volume" not in parameters:
                return {"success": False, "error": "Missing volume parameter"}
                
            try:
                volume = int(parameters["volume"])
                if not (0 <= volume <= 100):
                    return {"success": False, "error": "Volume must be between 0 and 100"}
                    
                current_state["volume"] = volume
                # If volume > 0, unmute the speaker
                if volume > 0:
                    current_state["muted"] = False
                    
                result = {"success": True, "state": current_state}
            except ValueError:
                return {"success": False, "error": "Invalid volume value"}
        elif action == "mute":
            current_state["muted"] = True
            result = {"success": True, "state": current_state}
        elif action == "unmute":
            current_state["muted"] = False
            result = {"success": True, "state": current_state}
        elif action == "play":
            if not current_state["power"]:
                return {"success": False, "error": "Speaker is powered off"}
                
            media_uri = parameters.get("media_uri")
            if not media_uri:
                return {"success": False, "error": "Missing media_uri parameter"}
                
            current_state["playing"] = True
            current_state["media_uri"] = media_uri
            result = {"success": True, "state": current_state}
        elif action == "stop":
            current_state["playing"] = False
            result = {"success": True, "state": current_state}
        else:
            # For unsupported actions, fall back to generic control
            return await self._control_generic(device, action, parameters, metadata)
            
        # Update device metadata with new state
        device_metadata["state"] = current_state
        device.device_metadata = device_metadata
        
        # Return success result
        return result
    async def _control_lock(self, device: Device, action: str, 
                          parameters: Dict[str, Any], 
                          metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle smart lock control actions"""
        # Get current device state
        device_metadata = device.device_metadata or {}
        current_state = device_metadata.get("state", {})
        
        # Initialize with defaults if not present
        if "power" not in current_state:
            current_state["power"] = True  # Locks are typically always powered
        if "locked" not in current_state:
            current_state["locked"] = True  # Default to locked for safety
        if "battery" not in current_state:
            current_state["battery"] = 100  # Battery level 0-100
            
        # Process action
        if action == "lock":
            current_state["locked"] = True
            result = {"success": True, "state": current_state}
        elif action == "unlock":
            # Validate authentication if provided
            pin = parameters.get("pin")
            if pin and pin != "1234":  # Simulated PIN validation
                return {"success": False, "error": "Invalid PIN code"}
                
            current_state["locked"] = False
            result = {"success": True, "state": current_state}
        elif action == "get_status":
            result = {
                "success": True, 
                "state": current_state,
                "last_activity": datetime.utcnow().isoformat()
            }
        else:
            # For unsupported actions, fall back to generic control
            return await self._control_generic(device, action, parameters, metadata)
            
        # Update device metadata with new state
        device_metadata["state"] = current_state
        device.device_metadata = device_metadata
        
        # Return success result
        return result
    async def _control_switch(self, device: Device, action: str, 
                             parameters: Dict[str, Any], 
                             metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle switch control actions"""
        # Get current device metadata and state, ensure both are dicts
        raw_metadata = device.device_metadata or {}
        device_metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
        
        raw_state = device_metadata.get("state", {})
        current_state = raw_state if isinstance(raw_state, dict) else {}
        
        # Ensure nested outlets field is a dict
        if not isinstance(current_state.get("outlets"), dict):
            current_state["outlets"] = {}
        
        # Initialize with defaults if not present
        if "power" not in current_state:
            current_state["power"] = False
        if "outlets" not in current_state or not current_state["outlets"]:
            # Default to a single outlet switch
            current_state["outlets"] = {"main": False}
            
        # Process action
        if action == "turn_on":
            current_state["power"] = True
            # Turn on all outlets
            for outlet in current_state["outlets"]:
                current_state["outlets"][outlet] = True
            result = {"success": True, "state": current_state}
        elif action == "turn_off":
            current_state["power"] = False
            # Turn off all outlets
            for outlet in current_state["outlets"]:
                current_state["outlets"][outlet] = False
            result = {"success": True, "state": current_state}
        elif action == "toggle":
            # Toggle main power and all outlets
            current_state["power"] = not current_state["power"]
            for outlet in current_state["outlets"]:
                current_state["outlets"][outlet] = current_state["power"]
            result = {"success": True, "state": current_state}
        elif action == "control_outlet":
            # Validate outlet parameter
            if "outlet" not in parameters:
                return {"success": False, "error": "Missing outlet parameter"}
            if "state" not in parameters:
                return {"success": False, "error": "Missing state parameter for outlet"}
                
            outlet = parameters["outlet"]
            if outlet not in current_state["outlets"]:
                return {"success": False, "error": f"Outlet '{outlet}' not found on this device"}
                
            # Update the specific outlet
            try:
                outlet_state = bool(parameters["state"])
                current_state["outlets"][outlet] = outlet_state
                
                # Update main power status based on any active outlets
                current_state["power"] = any(current_state["outlets"].values())
                result = {"success": True, "state": current_state}
            except ValueError:
                return {"success": False, "error": "Invalid outlet state value"}
        else:
            # For unsupported actions, fall back to generic control
            return await self._control_generic(device, action, parameters, metadata)
            
        # Update device metadata with new state
        device_metadata["state"] = current_state
        device.device_metadata = device_metadata
        await self.db.commit()
        
        # Return success result
        return result
    async def _control_sensor(self, device: Device, action: str, 
                            parameters: Dict[str, Any], 
                            metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle sensor control actions"""
        # Get current device metadata and state, ensure both are dicts
        raw_metadata = device.device_metadata or {}
        device_metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
        
        raw_state = device_metadata.get("state", {})
        current_state = raw_state if isinstance(raw_state, dict) else {}
        
        # Ensure nested dict fields are properly initialized/typed
        if not isinstance(current_state.get("readings"), dict):
            current_state["readings"] = {}
        if not isinstance(current_state.get("alert_thresholds"), dict):
            current_state["alert_thresholds"] = {}
        
        # Initialize with defaults if not present
        if "power" not in current_state:
            current_state["power"] = True  # Most sensors are always on
        if "battery" not in current_state:
            current_state["battery"] = 100  # Percentage
        if "alerting_enabled" not in current_state:
            current_state["alerting_enabled"] = True
        if "sampling_rate" not in current_state:
            current_state["sampling_rate"] = 60  # seconds
            
        # Process action
        if action == "turn_on":
            current_state["power"] = True
            result = {"success": True, "state": current_state}
        elif action == "turn_off":
            current_state["power"] = False
            result = {"success": True, "state": current_state}
        elif action == "get_reading":
            # Simulate getting a fresh reading
            if not current_state["power"]:
                return {"success": False, "error": "Sensor is powered off"}
                
            # Get reading type if specified
            reading_type = parameters.get("type", None)
            
            # Based on device sub-type, generate appropriate simulated readings
            # This is a simulation - in reality, we'd query the actual sensor
            from random import uniform
            
            if "temperature" in device.device_type.lower():
                reading = round(uniform(18.0, 24.0), 1)  # Celsius
                current_state["readings"]["temperature"] = reading
            elif "humidity" in device.device_type.lower():
                reading = round(uniform(30.0, 60.0), 1)  # Percentage
                current_state["readings"]["humidity"] = reading
            elif "motion" in device.device_type.lower():
                reading = random.choice([True, False])  # Motion detected or not
                current_state["readings"]["motion"] = reading
            elif "light" in device.device_type.lower():
                reading = round(uniform(0, 1000), 0)  # Lux
                current_state["readings"]["light_level"] = reading
            elif "air" in device.device_type.lower():
                # Air quality sensor
                current_state["readings"]["pm25"] = round(uniform(0, 50), 1)  # μg/m³
                current_state["readings"]["co2"] = round(uniform(400, 1500), 0)  # ppm
                current_state["readings"]["tvoc"] = round(uniform(0, 500), 0)  # ppb
            elif "water" in device.device_type.lower():
                # Water leak sensor
                current_state["readings"]["leak_detected"] = random.choice([True, False])
            elif "door" in device.device_type.lower() or "window" in device.device_type.lower():
                # Door/window sensor
                current_state["readings"]["contact"] = random.choice(["open", "closed"])
            else:
                # Generic sensor
                current_state["readings"]["value"] = round(uniform(0, 100), 1)
                
            # If a specific reading type was requested, filter to just that
            if reading_type and reading_type in current_state["readings"]:
                result = {
                    "success": True, 
                    "reading": {
                        reading_type: current_state["readings"][reading_type]
                    }
                }
            else:
                result = {
                    "success": True, 
                    "reading": current_state["readings"]
                }
        elif action == "set_alert_threshold":
            # Validate parameters
            if "type" not in parameters:
                return {"success": False, "error": "Missing type parameter"}
                
            if "min" not in parameters and "max" not in parameters:
                return {"success": False, "error": "Missing min or max parameter"}
                
            sensor_type = parameters["type"]
            
            # Initialize threshold for this type if it doesn't exist
            if sensor_type not in current_state["alert_thresholds"]:
                current_state["alert_thresholds"][sensor_type] = {}
                
            # Update min threshold if provided
            if "min" in parameters:
                try:
                    min_val = float(parameters["min"])
                    current_state["alert_thresholds"][sensor_type]["min"] = min_val
                except ValueError:
                    return {"success": False, "error": "Invalid min value"}
                    
            # Update max threshold if provided
            if "max" in parameters:
                try:
                    max_val = float(parameters["max"])
                    current_state["alert_thresholds"][sensor_type]["max"] = max_val
                except ValueError:
                    return {"success": False, "error": "Invalid max value"}
                    
            result = {"success": True, "state": {"alert_thresholds": current_state["alert_thresholds"]}}
        elif action == "set_sampling_rate":
            # Validate sampling_rate parameter
            if "rate" not in parameters:
                return {"success": False, "error": "Missing rate parameter"}
                
            try:
                rate = int(parameters["rate"])
                if not (1 <= rate <= 3600):  # 1 second to 1 hour
                    return {"success": False, "error": "Sampling rate must be between 1 and 3600 seconds"}
                    
                current_state["sampling_rate"] = rate
                result = {"success": True, "state": {"sampling_rate": rate}}
            except ValueError:
                return {"success": False, "error": "Invalid rate value"}
        elif action == "toggle_alerting":
            current_state["alerting_enabled"] = not current_state["alerting_enabled"]
            result = {"success": True, "state": {"alerting_enabled": current_state["alerting_enabled"]}}
        else:
            return {"success": False, "error": f"Unknown action for sensor: {action}"}
            
        # Update device metadata with new state
        device_metadata["state"] = current_state
        device.device_metadata = device_metadata
        await self.db.commit()
        
        return result
    
    async def _control_generic(self, device: Device, action: str, 
                              parameters: Dict[str, Any], 
                              metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generic device control actions"""
        # Get current device state
        device_metadata = device.device_metadata or {}
        current_state = device_metadata.get("state", {})
        
        # Initialize with defaults if not present
        if "power" not in current_state:
            current_state["power"] = False
            
        # Process action
        if action == "turn_on":
            current_state["power"] = True
            result = {"success": True, "state": current_state}
        elif action == "turn_off":
            current_state["power"] = False
            result = {"success": True, "state": current_state}
        elif action == "toggle":
            current_state["power"] = not current_state["power"]
            result = {"success": True, "state": current_state}
        elif action == "set_property":
            # Validate parameters
            if "property" not in parameters:
                return {"success": False, "error": "Missing property parameter"}
                
            if "value" not in parameters:
                return {"success": False, "error": "Missing value parameter"}
                
            # Set the property
            property_name = parameters["property"]
            property_value = parameters["value"]
            
            # Don't allow overriding power with this generic method
            if property_name == "power":
                return {"success": False, "error": "Use turn_on/turn_off to control power state"}
                
            current_state[property_name] = property_value
            result = {"success": True, "state": {property_name: property_value}}
        elif action == "get_property":
            # Validate parameters
            if "property" not in parameters:
                return {"success": False, "error": "Missing property parameter"}
                
            property_name = parameters["property"]
            
            # Check if property exists
            if property_name not in current_state:
                return {"success": False, "error": f"Property {property_name} not found"}
                
            result = {"success": True, "state": {property_name: current_state[property_name]}}
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
            
        # Update device metadata with new state
        device_metadata["state"] = current_state
        device.device_metadata = device_metadata
        await self.db.commit()
        
        return result
    
    async def scan_and_update_devices(self) -> Dict[str, Any]:
        """
        Simulate device discovery and update database
        
        Returns:
            Updated list of devices
        """
        logger.info("Starting device scan and update process")
        
        try:
            # Use device scanner to do discovery
            scan_id = await self.device_scanner.start_scan("discovery")
            
            # Simulate scan completion delay
            await asyncio.sleep(2)
            
            # Get scan results from database
            scan_query = select(Scan).where(Scan.id == scan_id)
            scan_result = await self.db.execute(scan_query)
            scan = scan_result.scalar_one_or_none()
            
            if not scan or scan.status != "completed":
                return {"success": False, "error": "Scan failed or still running"}
                
            # Process discovered devices
            devices_found = scan.result.get("devices_found", 0)
            devices = scan.result.get("devices", [])
            
            # Update existing devices and add new ones
            updated_count = 0
            new_count = 0
            
            for device_data in devices:
                # Check if this is a new device
                if device_data.get("new_device", False):
                    # Create new device
                    new_device_data = {
                        "name": device_data.get("name", "Unknown Device"),
                        "ip_address": device_data.get("ip_address", ""),
                        "mac_address": device_data.get("mac_address", ""),
                        "manufacturer": device_data.get("manufacturer", "Unknown"),
                        "model": device_data.get("model", "Unknown"),
                        "device_type": device_data.get("device_type", "generic"),
                        "is_online": True,
                        "last_seen": datetime.utcnow(),
                        "firmware_version": "1.0.0"
                    }
                    
                    await self.create_device(new_device_data)
                    new_count += 1
                else:
                    # Update existing device
                    device_id = device_data.get("id")
                    if device_id:
                        device = await self.get_device_by_id(device_id)
                        if device:
                            # Only update online status and last_seen
                            update_data = {
                                "is_online": True,
                                "last_seen": datetime.utcnow()
                            }
                            
                            await self.update_device(device_id, update_data)
                            updated_count += 1
            
            return {
                "success": True,
                "devices_found": devices_found,
                "updated_count": updated_count,
                "new_count": new_count,
                "scan_id": scan_id
            }
                
        except Exception as e:
            logger.error(f"Error in scan_and_update_devices: {str(e)}")
            return {"success": False, "error": f"Error: {str(e)}"}
    
    async def run_vulnerability_scan(self, device_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run a vulnerability scan on specified devices or all devices
        
        Args:
            device_ids: Optional list of device IDs to scan. If None, all devices are scanned.
            
        Returns:
            Dict with result of vulnerability scan
        """
        try:
            # If specific devices requested, validate they exist
            if device_ids:
                valid_devices = []
                for device_id in device_ids:
                    device = await self.get_device_by_id(device_id)
                    if device:
                        valid_devices.append(device_id)
                    else:
                        logger.warning(f"Device not found for vulnerability scan: {device_id}")
                
                if not valid_devices:
                    return {"success": False, "error": "No valid devices found to scan"}
                    
                device_ids = valid_devices
                
            # Run the vulnerability scan using the vulnerability scanner
            if device_ids:
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
    
    async def update_device(self, device_id: str, update_data: Dict[str, Any]) -> Optional[Device]:
        """
        Update a device with the provided data
        
        Args:
            device_id: ID of the device to update
            update_data: Dictionary of fields to update
            
        Returns:
            Updated device object or None if device not found
        """
        # First get the device
        query = select(Device).where(Device.hash_id == device_id)
        result = await self.db.execute(query)
        device = result.scalars().first()
        
        if not device:
            return None
            
        # Update device fields directly
        for key, value in update_data.items():
            if hasattr(device, key):
                setattr(device, key, value)
        
        # Update timestamp
        device.updated_at = datetime.utcnow()
        
        # Save changes
        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)
        
        # Log the activity
        await self.activity_service.log_activity(
            activity_type="user_action",
            action="device_updated",
            description=f"Device {device.name} was updated",
            target_type="device",
            target_id=device_id,
            target_name=device.name,
            metadata={"updated_fields": list(update_data.keys())}
        )
        
        return device
        
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """
        Get the current status of a device
        
        Args:
            device_id: ID of the device
            
        Returns:
            Dict with device status details
        """
        from sqlalchemy import select
        from app.models.device import Device
        
        # Simple query without loading relationships
        query = select(Device).where(Device.hash_id == device_id)
        result = await self.db.execute(query)
        device = result.scalars().first()
        
        if not device:
            return {"success": False, "error": "Device not found"}
        
        # Get device metadata for state info
        metadata = device.device_metadata or {}
        state = metadata.get("state", {})
        
        # Determine status based on device properties
        status = "online" if device.is_online else "offline"
        if device.is_online:
            if device.firmware_version and "beta" in device.firmware_version.lower():
                status = "warning"
            if getattr(device, "maintenance_mode", False):
                status = "maintenance"
        
        # Include required fields for DeviceStatusResponse
        return {
            "device_id": device_id,
            "name": device.name,
            "is_online": device.is_online,
            "status": status,  # Required field
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "firmware_version": device.firmware_version,
            "metadata": {
                "ip_address": device.ip_address,
                "mac_address": device.mac_address,
                "device_type": device.device_type,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "state": state
            },
            "uptime": getattr(device, "uptime", None)  # Optional field
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
        
    async def get_latest_device_readings(self, device_id: int) -> Dict[str, Any]:
        """
        Get latest readings for each sensor type associated with a device
        
        Args:
            device_id: ID of the device
            
        Returns:
            Dict containing device_id and latest readings for each sensor type
        """
        from app.models.sensor_reading import SensorReading
        from sqlalchemy import desc
        
        try:
            # Get distinct sensor types
            query = select(SensorReading.sensor_type).distinct().where(SensorReading.device_id == device_id)
            result = await self.db.execute(query)
            sensor_types = result.scalars().all()
            
            latest_readings = {}
            for sensor_type in sensor_types:
                query = (
                    select(SensorReading)
                    .where(
                        SensorReading.device_id == device_id,
                        SensorReading.sensor_type == sensor_type
                    )
                    .order_by(desc(SensorReading.timestamp))
                    .limit(1)
                )
                result = await self.db.execute(query)
                reading = result.scalar_one_or_none()
                
                if reading:
                    latest_readings[sensor_type] = reading.to_dict()
            
            return {"device_id": device_id, "readings": latest_readings}
        except Exception as e:
            logger.error(f"Error getting latest readings: {str(e)}")
            return {"device_id": device_id, "readings": {}, "error": str(e)}
#-----------------------------------------------------------------
# Factory functions to create service instances
#-----------------------------------------------------------------

def create_device_scanner(db: AsyncSession) -> DeviceScanner:
    """Create a new device scanner instance with the given database session"""
    return DeviceScanner(db)

def create_device_service(db: AsyncSession) -> DeviceService:
    """Create a new device service instance with the given database session"""
    return DeviceService(db)
