"""
Security Service for IoT Platform
---------------------------------
This module consolidates all security-related services including:

1. Vulnerability Scanner - Scans devices for security vulnerabilities
2. Vulnerability Service - Manages vulnerability scan results and remediation
3. Vulnerability Initializer - Injects simulated vulnerabilities for testing

The security service handles the complete lifecycle of vulnerability management:
- Automatic vulnerability injection at startup (for simulation)
- Device vulnerability scanning
- Vulnerability detection and classification
- Scan result storage and retrieval
- Remediation workflows
"""
import logging
import random
import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.device import Device
from app.models.scan import Scan, VulnerabilityScan
from app.models.database import get_db
from app.services.device_management_service import create_device_scanner
from app.services.activity_service import ActivityService
# Import DeviceService at runtime to avoid circular imports
from app.core.logging import logger
from app.utils.simulation import calculate_risk_score, simulate_network_delay, simulate_failures
from app.utils.notification_helper import NotificationHelper
from app.utils.vulnerability_utils import vulnerability_manager


#
# ===== VULNERABILITY SCANNER =====
#

class VulnerabilityScanner:
    """Advanced vulnerability scanner for IoT devices"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._scan_lock = asyncio.Lock()
        self.cve_database = self._initialize_cve_database()
        # Create a device scanner to fetch device data
        self.device_scanner = create_device_scanner(db)
    
    def _initialize_cve_database(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize a database of common vulnerabilities by device type"""
        return {
            "router": [
                {
                    "id": "CVE-2020-1472",
                    "name": "Zerologon",
                    "description": "Critical vulnerability in Windows Server Netlogon Remote Protocol",
                    "severity": "CRITICAL",
                    "cvss_score": 10.0,
                    "affected_vendors": ["Microsoft", "All"],
                    "remediation": "Apply security patches from Microsoft"
                },
                {
                    "id": "CVE-2019-1653",
                    "name": "Cisco Router Information Disclosure",
                    "description": "Information disclosure vulnerability in Cisco routers",
                    "severity": "HIGH",
                    "cvss_score": 7.5,
                    "affected_vendors": ["Cisco"],
                    "remediation": "Update router firmware"
                },
                {
                    "id": "CVE-2021-44228",
                    "name": "Log4Shell",
                    "description": "Remote code execution vulnerability in Log4j",
                    "severity": "CRITICAL",
                    "cvss_score": 10.0,
                    "affected_vendors": ["Apache", "All"],
                    "remediation": "Update to Log4j 2.15.0 or later"
                }
            ],
            "camera": [
                {
                    "id": "CVE-2021-32934",
                    "name": "Camera Default Credentials",
                    "description": "IP camera uses default credentials that are easily guessed",
                    "severity": "HIGH",
                    "cvss_score": 8.0,
                    "affected_vendors": ["Generic", "All"],
                    "remediation": "Change default password"
                },
                {
                    "id": "CVE-2019-11068",
                    "name": "Unauthenticated Access",
                    "description": "IP camera allows unauthenticated access to video stream",
                    "severity": "CRITICAL",
                    "cvss_score": 9.1,
                    "affected_vendors": ["Generic", "All"],
                    "remediation": "Update firmware and enable authentication"
                }
            ],
            "thermostat": [
                {
                    "id": "CVE-2019-9569",
                    "name": "Temperature Spoofing",
                    "description": "Vulnerability allows attackers to spoof temperature readings",
                    "severity": "MEDIUM",
                    "cvss_score": 5.5,
                    "affected_vendors": ["Generic", "All"],
                    "remediation": "Update firmware to latest version"
                }
            ],
            "lock": [
                {
                    "id": "CVE-2020-8366",
                    "name": "Bluetooth Replay Attack",
                    "description": "Smart lock vulnerable to Bluetooth replay attacks",
                    "severity": "HIGH",
                    "cvss_score": 7.8,
                    "affected_vendors": ["Generic", "All"],
                    "remediation": "Update lock firmware and mobile app"
                }
            ]
        }
    
    async def scan_device(self, device: Device) -> List[Dict[str, Any]]:
        """
        Scan a device for vulnerabilities and return findings
        
        This scans a device based on its type, firmware version,
        and other attributes to detect potential vulnerabilities.
        """
        logger.info(f"Scanning device {device.hash_id} ({device.name}) for vulnerabilities")
        
        # Simulate network delay for realism
        await simulate_network_delay()
        
        # Check if device is online
        if not device.is_online:
            logger.warning(f"Cannot scan offline device: {device.hash_id}")
            return []
        
        # Get simulated vulnerabilities already attached to this device
        simulated_vulns = vulnerability_manager.get_device_vulnerabilities(device.hash_id)
        if simulated_vulns:
            return simulated_vulns
        
        # If no simulated vulnerabilities, check against CVE database based on device type
        device_type = device.device_type
        vulnerabilities = []
        
        # For each device type, check if any vulnerabilities apply
        if device_type in self.cve_database:
            # Get potential vulnerabilities for this device type
            potential_vulns = self.cve_database.get(device_type, [])
            
            # Randomly determine how many vulnerabilities to add (0-2)
            # This simulates that not all devices have vulnerabilities
            num_vulns = random.randint(0, 2)
            if num_vulns > 0 and potential_vulns:
                # Randomly select vulnerabilities
                selected_vulns = random.sample(potential_vulns, min(num_vulns, len(potential_vulns)))
                
                for vuln in selected_vulns:
                    # Copy the vulnerability and add device-specific details
                    vuln_copy = vuln.copy()
                    
                    # Determine if this vulnerability can be fixed with a firmware update
                    # For demo purposes, we'll say 70% of vulnerabilities can be fixed with firmware
                    if random.random() < 0.7:
                        vuln_copy["fix_available"] = "firmware_update"
                    else:
                        vuln_copy["fix_available"] = "configuration_change"
                    
                    # Add some device-specific context
                    vuln_copy["affected_device"] = device.hash_id
                    vuln_copy["device_name"] = device.name
                    vuln_copy["first_detected"] = datetime.now().isoformat()
                    
                    # Add the vulnerability
                    vulnerabilities.append(vuln_copy)
        
        return vulnerabilities
    
    async def bulk_scan(self, devices: List[Device]) -> Dict[str, Any]:
        """
        Perform a bulk vulnerability scan on multiple devices
        
        Returns:
            Dict with scan results and statistics
        """
        logger.info(f"Starting bulk vulnerability scan for {len(devices)} devices")
        
        results = {
            "total_devices": len(devices),
            "devices_scanned": 0,
            "devices_with_vulnerabilities": 0,
            "total_vulnerabilities": 0,
            "scan_results": {}
        }
        
        # Use a lock to prevent concurrent scans that might conflict
        async with self._scan_lock:
            for device in devices:
                # Skip offline devices
                if not device.is_online:
                    continue
                    
                # Simulate network delay for realism
                await simulate_network_delay(min_delay=0.1, max_delay=0.5)
                
                # Scan the device
                vulnerabilities = await self.scan_device(device)
                
                # Add results
                results["devices_scanned"] += 1
                
                if vulnerabilities:
                    results["devices_with_vulnerabilities"] += 1
                    results["total_vulnerabilities"] += len(vulnerabilities)
                    
                    # Store the scan results
                    results["scan_results"][device.hash_id] = {
                        "device_name": device.name,
                        "device_type": device.device_type,
                        "vulnerabilities": vulnerabilities
                    }
        
        return results


# Create a VulnerabilityScanner factory function
def create_vulnerability_scanner(db: AsyncSession) -> VulnerabilityScanner:
    """Create a new vulnerability scanner instance with the given database session"""
    return VulnerabilityScanner(db)


#
# ===== VULNERABILITY SERVICE =====
#

class VulnerabilityService:
    """Service for performing vulnerability scans on IoT devices"""

    def __init__(self, db: AsyncSession):
        from app.services.device_management_service import DeviceService
        self.db = db
        self.device_service = DeviceService(db)
        self.activity_service = ActivityService(db)
        self._scan_lock = asyncio.Lock()
        # Create an instance of VulnerabilityScanner for technical scanning
        self.vulnerability_scanner = create_vulnerability_scanner(db)
        
    async def start_vulnerability_scan(self, device_id: str, user_id: Optional[Union[int, str]] = None) -> Dict[str, Any]:
        """
        Start a vulnerability scan for a specific device
        """
        try:
            # Get device info
            device = await self.device_service.get_device_by_id(device_id)
            if not device:
                logger.error(f"Device with ID {device_id} not found")
                return {"status": "error", "error": "Device not found"}
            
            # Check if device is online
            if not device.is_online:
                logger.error(f"Device with ID {device_id} is offline and cannot be scanned")
                return {"status": "error", "error": "Device is offline"}
            
            # Create scan record
            scan_id = str(uuid.uuid4())
            scan = Scan(
                id=scan_id,
                device_id=device_id,
                scan_type="vulnerability",
                status="pending",
                created_by=user_id,
                start_time=datetime.now()
            )
            self.db.add(scan)
            await self.db.commit()
            
            # Log the activity
            await self.activity_service.log_device_state_change(
                device_id=device_id,
                action="vulnerability_scan_started",
                user_id=user_id,
                metadata={"scan_id": scan_id}
            )
            
            logger.info(f"Vulnerability scan {scan_id} initiated for device {device_id}")
            
            return {
                "status": "started",
                "scan_id": scan_id,
                "device_id": device_id,
                "device_name": device.name,
                "scan_type": "vulnerability",
                "start_time": scan.start_time.isoformat()
            }
        except Exception as e:
            logger.error(f"Error starting vulnerability scan: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    async def simulate_vulnerability_scan(self, scan_id: str) -> None:
        """
        Simulate a vulnerability scan running as a background task
        """
        try:
            # Get scan info
            query = select(Scan).where(Scan.id == scan_id)
            result = await self.db.execute(query)
            scan = result.scalar_one_or_none()
            
            if not scan:
                logger.error(f"Scan with ID {scan_id} not found")
                return
            
            # Get device info
            device = await self.device_service.get_device_by_id(scan.device_id)
            if not device:
                logger.error(f"Device with ID {scan.device_id} not found")
                
                # Update scan status
                scan.status = "error"
                scan.end_time = datetime.now()
                scan.results = {"error": "Device not found"}
                await self.db.commit()
                return
            
            # Update scan to in-progress
            scan.status = "in_progress"
            await self.db.commit()
            
            # Simulate scan duration
            await asyncio.sleep(random.uniform(2.0, 5.0))
            
            # Check if device is still online - if not, scan fails
            if not device.is_online and random.random() < 0.8:  # 80% chance to fail if offline
                scan.status = "error"
                scan.end_time = datetime.now()
                scan.results = {"error": "Device went offline during scan"}
                await self.db.commit()
                
                logger.warning(f"Vulnerability scan {scan_id} failed: device went offline")
                return
            
            # Perform the actual scan
            vulnerabilities = await self.vulnerability_scanner.scan_device(device)
            
            # Add vulnerability scan results
            for vuln in vulnerabilities:
                vuln_scan = VulnerabilityScan(
                    scan_id=scan_id,
                    vulnerability_id=vuln["id"],
                    title=vuln.get("name", "Unknown"),
                    description=vuln.get("description", ""),
                    severity=vuln.get("severity", "MEDIUM"),
                    cvss_score=vuln.get("cvss_score", 5.0),
                    affected_component=vuln.get("affected_component", ""),
                    fix_available=vuln.get("fix_available", "unknown"),
                    remediation=vuln.get("remediation", "")
                )
                self.db.add(vuln_scan)
            
            # Update scan status
            scan.status = "completed"
            scan.end_time = datetime.now()
            scan.results = {
                "vulnerabilities_found": len(vulnerabilities),
                "risk_score": calculate_risk_score(vulnerabilities),
                "scan_summary": f"Found {len(vulnerabilities)} vulnerabilities"
            }
            await self.db.commit()
            
            # Always send a vulnerability notification, even if zero findings
            notification_helper = NotificationHelper(self.db)
            await notification_helper.create_vulnerability_notification(
                device_id=device.hash_id,
                vulnerability_count=len(vulnerabilities),
                risk_score=scan.results["risk_score"],
                critical_count=sum(1 for v in vulnerabilities if v.get("severity") == "CRITICAL"),
                vulnerabilities=vulnerabilities
            )
            
            # Log alert activity for vulnerability scan completion
            critical_count = sum(1 for v in vulnerabilities if v.get("severity") == "CRITICAL")
            await self.activity_service.log_alert(
                action="vulnerability_scan_completed",
                description=f"Vulnerability scan completed for device {device.hash_id}: found {len(vulnerabilities)} vulnerabilities",
                severity="critical" if critical_count > 0 else ("warning" if vulnerabilities else "info"),
                target_type="device",
                target_id=device.hash_id,
                target_name=device.name,
                metadata={"scan_id": scan_id, "vulnerability_count": len(vulnerabilities), "critical_count": critical_count}
            )
            
            logger.info(f"Vulnerability scan {scan_id} completed with {len(vulnerabilities)} findings")
        except Exception as e:
            logger.error(f"Error during vulnerability scan simulation: {str(e)}", exc_info=True)
            
            # Try to update scan status
            try:
                query = select(Scan).where(Scan.id == scan_id)
                result = await self.db.execute(query)
                scan = result.scalar_one_or_none()
                
                if scan:
                    scan.status = "error"
                    scan.end_time = datetime.now()
                    scan.results = {"error": str(e)}
                    await self.db.commit()
            except Exception as update_err:
                logger.error(f"Failed to update scan status: {str(update_err)}")
    
    async def get_scan_results(self, scan_id: str) -> Dict[str, Any]:
        """
        Get the results of a vulnerability scan
        """
        # Get scan record
        query = select(Scan).options(selectinload(Scan.vulnerability_scans)).where(Scan.id == scan_id)
        result = await self.db.execute(query)
        scan = result.scalar_one_or_none()
        
        if not scan:
            return {"status": "error", "error": "Scan not found"}
        
        # Get device info
        device = await self.device_service.get_device_by_id(scan.device_id)
        device_info = device.to_dict() if device else {"id": scan.device_id, "not_found": True}
        
        # Format scan results
        scan_data = {
            "id": scan.id,
            "device": device_info,
            "scan_type": scan.scan_type,
            "status": scan.status,
            "start_time": scan.start_time.isoformat(),
            "end_time": scan.end_time.isoformat() if scan.end_time else None,
            "duration_seconds": (scan.end_time - scan.start_time).total_seconds() if scan.end_time else None,
            "result": scan.results,
            "vulnerabilities": []
        }
        
        # Add vulnerability details
        for vuln_scan in scan.vulnerability_scans:
            scan_data["vulnerabilities"].append({
                "id": vuln_scan.vulnerability_id,
                "title": vuln_scan.title,
                "description": vuln_scan.description,
                "severity": vuln_scan.severity,
                "cvss_score": vuln_scan.cvss_score,
                "affected_component": vuln_scan.affected_component,
                "fix_available": vuln_scan.fix_available,
                "detected_at": vuln_scan.timestamp.isoformat() if vuln_scan.timestamp else None,
                "remediation": vuln_scan.remediation
            })
        
        return {
            "status": "success",
            "scan": scan_data
        }


#
# ===== VULNERABILITY INITIALIZER =====
#

# Predefined vulnerabilities to inject
INJECTABLE_VULNERABILITIES = [
    {
        "id": "CVE-2023-1001",
        "name": "Hardcoded Backdoor Access",
        "severity": "CRITICAL",
        "cvss_score": 9.8,
        "description": "Device contains a hardcoded backdoor that allows unauthorized access",
        "affected_component": "Authentication System",
        "recommendation": "Update to latest firmware which removes backdoor",
        "remediation_complexity": "MEDIUM",
        "exploitability": "HIGH"
    },
    {
        "id": "CVE-2023-1002",
        "name": "Command Injection in Web Interface",
        "severity": "CRITICAL",
        "cvss_score": 9.6,
        "description": "Web management interface is vulnerable to command injection attacks",
        "affected_component": "Web Interface",
        "recommendation": "Apply security patch or update firmware",
        "remediation_complexity": "MEDIUM",
        "exploitability": "HIGH"
    },
    {
        "id": "CVE-2023-1003",
        "name": "Insecure Default Credentials",
        "severity": "HIGH",
        "cvss_score": 8.2,
        "description": "Device ships with default credentials that are easily guessable",
        "affected_component": "Authentication System",
        "recommendation": "Change default password immediately after installation",
        "remediation_complexity": "LOW",
        "exploitability": "HIGH"
    },
    {
        "id": "CVE-2023-1004",
        "name": "Unencrypted Data Transmission",
        "severity": "HIGH",
        "cvss_score": 7.5,
        "description": "Device transmits sensitive data without encryption",
        "affected_component": "Communication Protocol",
        "recommendation": "Update to firmware that implements TLS/HTTPS",
        "remediation_complexity": "MEDIUM",
        "exploitability": "MEDIUM"
    },
    {
        "id": "CVE-2023-1005",
        "name": "Outdated TLS Version",
        "severity": "MEDIUM",
        "cvss_score": 5.3,
        "description": "Device uses outdated TLS 1.0 which has known vulnerabilities",
        "affected_component": "Security Protocol",
        "recommendation": "Update firmware to support TLS 1.2 or higher",
        "remediation_complexity": "MEDIUM",
        "exploitability": "MEDIUM"
    },
    {
        "id": "CVE-2023-1006",
        "name": "Weak Encryption Algorithm",
        "severity": "MEDIUM",
        "cvss_score": 6.1,
        "description": "Device uses weak encryption algorithms like MD5 or DES",
        "affected_component": "Cryptographic Implementation",
        "recommendation": "Update firmware to use strong encryption algorithms",
        "remediation_complexity": "MEDIUM",
        "exploitability": "MEDIUM"
    },
    {
        "id": "CVE-2023-1007",
        "name": "Missing Authentication for Critical Function",
        "severity": "CRITICAL",
        "cvss_score": 9.0,
        "description": "Critical device functions can be accessed without authentication",
        "affected_component": "Access Control",
        "recommendation": "Update firmware to add authentication for all critical functions",
        "remediation_complexity": "HIGH",
        "exploitability": "HIGH"
    },
    {
        "id": "CVE-2023-1008",
        "name": "Buffer Overflow in Firmware",
        "severity": "HIGH",
        "cvss_score": 8.8,
        "description": "Buffer overflow vulnerability in device firmware allows code execution",
        "affected_component": "Firmware",
        "recommendation": "Update to latest firmware which fixes the vulnerability",
        "remediation_complexity": "MEDIUM",
        "exploitability": "MEDIUM"
    },
    {
        "id": "CVE-2023-1009",
        "name": "Cross-Site Scripting in Web Interface",
        "severity": "MEDIUM",
        "cvss_score": 6.5,
        "description": "Device web interface is vulnerable to cross-site scripting attacks",
        "affected_component": "Web Interface",
        "recommendation": "Update firmware with security patches",
        "remediation_complexity": "MEDIUM",
        "exploitability": "MEDIUM"
    },
    {
        "id": "CVE-2023-1010",
        "name": "Insecure Firmware Update Process",
        "severity": "HIGH",
        "cvss_score": 7.8,
        "description": "Firmware update process doesn't verify integrity of updates",
        "affected_component": "Update Mechanism",
        "recommendation": "Update to firmware that implements signed updates",
        "remediation_complexity": "HIGH",
        "exploitability": "MEDIUM"
    }
]

async def initialize_device_vulnerabilities(db: AsyncSession) -> None:
    """
    Automatically inject vulnerabilities into devices based on their properties.
    This creates a more realistic and deterministic vulnerability simulation.
    """
    try:
        # Get all devices
        query = select(Device)
        result = await db.execute(query)
        devices = result.scalars().all()
        
        if not devices:
            logger.warning("No devices found to initialize vulnerabilities")
            return
        
        # Check if vulnerability manager has already been initialized
        # If vulnerabilities exist, we don't need to reinitialize
        if vulnerability_manager.vulnerability_state.get("devices") and len(vulnerability_manager.vulnerability_state.get("devices", {})) > 0:
            logger.info("Vulnerabilities already initialized, skipping")
            return
        
        # Select 3-6 random devices to inject vulnerabilities into
        num_vulnerable_devices = random.randint(3, min(6, len(devices)))
        vulnerable_devices = random.sample(devices, num_vulnerable_devices)
        
        logger.info(f"Initializing vulnerabilities for {num_vulnerable_devices} random devices")
        
        # For each selected device, inject 1-3 vulnerabilities
        for device in vulnerable_devices:
            # Select 1-3 random vulnerabilities for this device
            num_vulnerabilities = random.randint(1, 3)
            selected_vulnerabilities = random.sample(INJECTABLE_VULNERABILITIES, num_vulnerabilities)
            
            # Add device-specific context to each vulnerability
            for vuln in selected_vulnerabilities:
                vuln_copy = vuln.copy()
                
                # Determine if this vulnerability can be fixed with a firmware update
                # For demo purposes, we'll say 70% of vulnerabilities can be fixed with firmware
                if random.random() < 0.7:
                    vuln_copy["fix_available"] = "firmware_update"
                else:
                    vuln_copy["fix_available"] = "configuration_change"
                
                # Add the vulnerability to the device
                vulnerability_manager.inject_vulnerability(device.hash_id, vuln_copy)
                
                logger.info(f"Injected vulnerability {vuln_copy['id']} ({vuln_copy['name']}) into device {device.name}")
        
        # Save the vulnerability state to persistent storage
        vulnerability_manager.save_state()
        
        logger.info("Vulnerability initialization completed successfully")
    except Exception as e:
        logger.error(f"Error initializing device vulnerabilities: {str(e)}", exc_info=True)

async def run_vulnerability_initializer() -> None:
    """Run the vulnerability initializer once at startup"""
    try:
        logger.info("Starting vulnerability initializer")
        
        # Get a database session
        async for db in get_db():
            await initialize_device_vulnerabilities(db)
            break  # Only need one iteration
            
        logger.info("Vulnerability initializer completed")
    except Exception as e:
        logger.error(f"Error running vulnerability initializer: {str(e)}", exc_info=True)

# Export the initializer for use at application startup
vulnerability_initializer = run_vulnerability_initializer
