import logging
import random
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.utils.simulation import simulate_network_delay, simulate_failures
from app.models.scan import Scan
from app.models.device import Device
from app.core.logging import logger

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
            
            # Add task to a global task registry for proper cleanup
            if not hasattr(self, '_scan_tasks'):
                self._scan_tasks = set()
            self._scan_tasks.add(task)
            task.add_done_callback(self._scan_tasks.discard)
            
            return scan_id
    
    # Not needed - this functionality is now handled directly by the API endpoint through database queries
    
    async def _run_scan(self, scan_id: str, scan_type: str, network_range: Optional[str] = None):
        """Run the actual scan operation"""
        # First, update status to running with proper transaction
        async with self._scan_lock:
            try:
                # Mark scan as running in a separate transaction
                await self.db.execute(
                    update(Scan)
                    .where(Scan.id == scan_id)
                    .where(Scan.status == "pending")  # Only update if still in pending state
                    .values(status="running")
                )
                await self.db.commit()
            except Exception as e:
                logger.error(f"Failed to mark scan {scan_id} as running: {str(e)}")
                await self.db.rollback()
                # Update scan status to failed
                await self._mark_scan_failed(scan_id, f"Failed to start scan: {str(e)}")
                return

        # Run the actual scan operation
        try:
            # Perform the appropriate scan based on type
            if scan_type == "discovery":
                results = await self._run_discovery_scan(network_range)
            elif scan_type == "vulnerability":
                results = await self._run_vulnerability_scan()
            else:
                raise ValueError(f"Unknown scan type: {scan_type}")
            
            # Update scan record with results in a new transaction
            try:
                await self.db.execute(
                    update(Scan)
                    .where(Scan.id == scan_id)
                    .values(
                        status="completed",
                        end_time=datetime.utcnow(),
                        results=results
                    )
                )
                await self.db.commit()
                logger.info(f"Scan {scan_id} completed successfully")
            except Exception as e:
                logger.error(f"Failed to update scan {scan_id} results: {str(e)}")
                await self.db.rollback()
                await self._mark_scan_failed(scan_id, f"Failed to save scan results: {str(e)}")
            
        except Exception as e:
            logger.error(f"Scan {scan_id} execution failed: {str(e)}")
            await self._mark_scan_failed(scan_id, str(e))

    async def _mark_scan_failed(self, scan_id: str, error_message: str):
        """Helper to mark a scan as failed with proper error handling"""
        try:
            await self.db.execute(
                update(Scan)
                .where(Scan.id == scan_id)
                .values(
                    status="failed",
                    end_time=datetime.utcnow(),
                    error=error_message
                )
            )
            await self.db.commit()
            logger.info(f"Marked scan {scan_id} as failed")
        except Exception as e:
            logger.error(f"Could not mark scan {scan_id} as failed: {str(e)}")
            await self.db.rollback()
    
    def _validate_network_range(self, network_range: str) -> bool:
        """Validate that a network range is properly formatted and allowed"""
        # Basic validation for CIDR notation (e.g., 192.168.1.0/24)
        if not network_range or not isinstance(network_range, str):
            return False
            
        # Check format
        parts = network_range.split('/')
        if len(parts) != 2:
            return False
            
        ip_part, cidr_part = parts
        
        # Validate IP address format
        ip_octets = ip_part.split('.')
        if len(ip_octets) != 4:
            return False
            
        for octet in ip_octets:
            try:
                o = int(octet)
                if o < 0 or o > 255:
                    return False
            except ValueError:
                return False
                
        # Validate CIDR prefix
        try:
            cidr = int(cidr_part)
            # Only allow scanning of class C networks or smaller for security (24 or higher)
            # This prevents scanning large network ranges
            if cidr < 24 or cidr > 32:
                logger.warning(f"Network range {network_range} not allowed - must be /24 or smaller")
                return False
        except ValueError:
            return False
            
        # Validate against allowed networks (typically private ranges)
        allowed_prefixes = [
            "10.", 
            "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.",
            "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
            "192.168."
        ]
        
        if not any(ip_part.startswith(prefix) for prefix in allowed_prefixes):
            logger.warning(f"Network range {network_range} not allowed - must be in private IP space")
            return False
            
        return True
    
    async def _run_discovery_scan(self, network_range: Optional[str] = None) -> List[Dict]:
        """Run a discovery scan to find devices with proper validation"""
        # Validate network range first
        if network_range and not self._validate_network_range(network_range):
            raise ValueError(f"Invalid or disallowed network range: {network_range}")
            
        # For this example, we're still using simulated devices
        # But with better structure and validation
        await simulate_network_delay(1, 3)
        
        # Create simulated scan results
        discovered_devices = []
        
        # In a real implementation, this would ping devices in the network range
        # and collect information about them
        if network_range:
            # Parse network range to determine IP generation
            base_ip = network_range.split('/')[0].rsplit('.', 1)[0]
            
            # Generate random devices for simulation
            device_count = random.randint(5, 15)  # Random number of devices
            for i in range(device_count):
                # Generate device details
                ip_suffix = random.randint(1, 254)
                ip_address = f"{base_ip}.{ip_suffix}"
                mac_address = ":16:".join([""]+[f"{random.randint(0, 255):02x}" for _ in range(5)])
                
                device = {
                    "ip_address": ip_address,
                    "mac_address": mac_address,
                    "hostname": f"device-{ip_suffix}",
                    "device_type": random.choice(["router", "camera", "thermostat", "light", "speaker", "sensor"]),
                    "manufacturer": random.choice(["Cisco", "Netgear", "TP-Link", "D-Link", "Linksys", "ASUS"]),
                    "status": random.choice(["online", "online", "online", "offline"]),  # 75% chance of being online
                    "last_seen": datetime.utcnow().isoformat(),
                    "scan_method": "discovery"
                }
                
                discovered_devices.append(device)
                
        # Also check database for existing devices to include in results
        try:
            result = await self.db.execute(select(Device))
            existing_devices = result.scalars().all()
            
            # Include existing devices from database
            for device in existing_devices:
                # Create device info dict
                device_info = {
                    "id": device.id,
                    "ip_address": device.ip_address,
                    "mac_address": device.mac_address,
                    "hostname": device.name,
                    "device_type": device.device_type,
                    "manufacturer": device.manufacturer,
                    "status": "online" if device.is_online else "offline",
                    "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                    "scan_method": "database"
                }
                
                # Check if this device is already in discovered_devices (by MAC address)
                if not any(d["mac_address"] == device.mac_address for d in discovered_devices):
                    discovered_devices.append(device_info)
                    
        except Exception as e:
            logger.error(f"Error retrieving existing devices: {str(e)}")
            
        return discovered_devices
    
    async def _run_vulnerability_scan(self) -> List[Dict]:
        """Run a vulnerability scan on known devices"""
        # Get all active devices
        devices = await self.db.execute(
            select(Device).where(Device.status == "active")
        )
        devices = devices.scalars().all()
        
        results = []
        for device in devices:
            # Implementation of vulnerability scan per device
            # This should be updated to use actual vulnerability scanning
            # For now, return mock data
            results.append({
                "device_id": device.id,
                "ip": device.ip_address,
                "vulnerabilities": [
                    {
                        "name": "Test Vulnerability",
                        "severity": "high",
                        "description": "Test vulnerability description"
                    }
                ]
            })
        
        return results
    
    async def _get_devices_from_db(self) -> List[Dict[str, Any]]:
        """Get devices from database and enhance with virtual properties"""
        if not self.db:
            return []
            
        try:
            # Fetch devices
            query = select(Device)
            result = await self.db.execute(query)
            db_devices = result.scalars().all()
            
            # Convert to dictionaries with virtual properties
            devices = []
            for device in db_devices:
                # Add random device failures using shared utility
                if simulate_failures():
                    logger.info(f"Device {device.name} ({device.ip_address}) not responding to scan")
                    continue
                    
                # Use existing ports data or generate fake data
                ports_dict = device.ports or {}
                if not ports_dict:
                    # Generate based on device type
                    ports_dict = self._generate_virtual_ports(device.device_type)
                
                # Add common information
                device_dict = {
                    "id": device.id,
                    "ip_address": device.ip_address,
                    "mac_address": device.mac_address,
                    "hostname": device.name,
                    "vendor": device.manufacturer,
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

# Create a DeviceScanner factory function instead of a global instance
def create_device_scanner(db: AsyncSession):
    """Create a new device scanner instance with the given database session"""
    return DeviceScanner(db) 