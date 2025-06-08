"""
Notification helper utility for standardized notification creation across the platform.
Provides consistent patterns for generating notifications from different system components.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from config import settings
from app.services.messaging_service import NotificationService

logger = logging.getLogger(__name__)

class NotificationHelper:
    """Helper class for creating notifications from different platform features"""
    
    def __init__(self, db):
        """Initialize helper with a DB session so instance methods can use it.

        Args:
            db: Async SQLAlchemy session used for writing notifications.
        """
        self.db = db

    @staticmethod
    async def trigger_notification(
        db,
        title: str,
        content: str,
        notification_type: str = "info",
        source: str = "system",
        source_id: Optional[int] = None,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        target_name: Optional[str] = None,
        priority: int = 3,
        channels: List[str] = None,
        metadata: Dict[str, Any] = None,
        recipients: List[str] = None,
    ):
        """
        Standardized method to trigger notifications from any system component
        
        Args:
            db: Database session
            title: Notification title
            content: Notification content/message
            notification_type: Type of notification (info, warning, error, success)
            source: Source of the notification (vulnerability_scanner, network_monitor, etc.)
            source_id: ID of the source object
            target_type: Type of target (device, group, system)
            target_id: ID of the target
            target_name: Name of the target
            priority: Priority level (1-5, where 5 is highest)
            channels: Delivery channels (in_app, websocket, email, sms, etc.)
            metadata: Additional context data
            recipients: List of email recipients
        """
        # Default channels include both in_app (for persistence) and websocket (for real-time)
        if channels is None:
            channels = ["in_app", "websocket"]
        
        # Ensure email & SMS channels are always included
        if "email" not in channels:
            channels.append("email")
        if "sms" not in channels:
            channels.append("sms")
            
        if metadata is None:
            metadata = {}
        
        # Initialise recipients list
        if recipients is None:
            recipients = []

        # Append default recipients from env if missing
        default_email = getattr(settings, "DEFAULT_NOTIFICATION_EMAIL", None)
        if default_email and default_email not in recipients:
            recipients.append(default_email)

        default_phone = getattr(settings, "DEFAULT_NOTIFICATION_PHONE", None)
        if default_phone and default_phone not in recipients:
            recipients.append(default_phone)
        
        # Add timestamp to metadata
        metadata["triggered_at"] = datetime.utcnow().isoformat()
        
        # Always include websocket for real-time delivery
        if "websocket" not in channels:
            channels.append("websocket")
        
        try:
            notification_service = NotificationService(db)
            await notification_service.create_notification(
                title=title,
                content=content,
                notification_type=notification_type,
                source=source,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                target_name=target_name,
                priority=priority,
                recipients=recipients,
                channels=channels,
                metadata=metadata
            )
            logger.info(f"Notification triggered: {title} (priority: {priority}, type: {notification_type})")
        except Exception as e:
            logger.error(f"Failed to create notification: {str(e)}", exc_info=True)
    
    # Specialized methods for common notification types
    
    @classmethod
    async def notify_vulnerability_detected(cls, db, vulnerability, device, severity="medium"):
        """Notify when a vulnerability is detected on a device"""
        severity_map = {
            "critical": 5,
            "high": 4,
            "medium": 3,
            "low": 2,
            "info": 1
        }
        
        # Determine channels based on severity
        channels = ["in_app", "websocket"]
        if severity in ["critical", "high"]:
            channels.append("email")
        
        notification_type = "warning" if severity in ["critical", "high"] else "info"
        
        await cls.trigger_notification(
            db=db,
            title=f"New {severity.upper()} vulnerability detected",
            content=f"Vulnerability '{vulnerability.name}' detected on device {device.name}.",
            notification_type=notification_type,
            source="vulnerability_scanner",
            source_id=vulnerability.id if hasattr(vulnerability, "id") else None,
            target_type="device",
            target_id=device.id if hasattr(device, "id") else None,
            target_name=device.name,
            priority=severity_map.get(severity, 3),
            channels=channels,
            metadata={
                "vulnerability_type": getattr(vulnerability, "type", "unknown"),
                "cve_id": getattr(vulnerability, "cve_id", None),
                "remediation_available": getattr(vulnerability, "has_remediation", False)
            }
        )
    
    @classmethod
    async def notify_security_event(cls, db, event_type, source_ip, target_ip, severity="medium"):
        """Notify about a detected security event"""
        priority_map = {"critical": 5, "high": 4, "medium": 3, "low": 2}
        priority = priority_map.get(severity, 3)
        
        # Determine channels based on severity
        channels = ["in_app"]
        if severity in ["critical", "high"]:
            channels.append("email")
            if severity == "critical":
                channels.append("sms")
        
        await cls.trigger_notification(
            db=db,
            title=f"{severity.title()} security event detected",
            content=f"{event_type} attack detected from {source_ip} targeting {target_ip}",
            notification_type="error" if severity in ["critical", "high"] else "warning",
            source="network_monitor",
            target_type="network",
            priority=priority,
            channels=channels,
            metadata={
                "event_type": event_type,
                "source_ip": source_ip,
                "target_ip": target_ip,
                "detection_time": datetime.utcnow().isoformat()
            }
        )
    
    @classmethod
    async def notify_firmware_update(cls, db, device, firmware, is_critical=False):
        """Notify about available firmware updates"""
        priority = 4 if is_critical else 3
        channels = ["in_app"]
        if is_critical:
            channels.append("email")
        
        await cls.trigger_notification(
            db=db,
            title=f"{'Critical' if is_critical else 'New'} firmware update available",
            content=f"Firmware update {firmware.version} is available for {device.name}",
            notification_type="warning" if is_critical else "info",
            source="firmware_manager",
            source_id=firmware.id if hasattr(firmware, "id") else None,
            target_type="device",
            target_id=device.id if hasattr(device, "id") else None,
            target_name=device.name,
            priority=priority,
            channels=channels,
            metadata={
                "current_version": getattr(device, "firmware_version", "unknown"),
                "new_version": getattr(firmware, "version", "unknown"),
                "is_critical": is_critical,
                "release_notes": getattr(firmware, "changelog", None)
            }
        )
    
    @classmethod
    async def notify_device_status_change(cls, db, device, previous_status, new_status):
        """Notify about important device status changes"""
        # Only notify for significant changes
        if previous_status == new_status:
            return
            
        # Determine if this is a concerning change
        is_concerning = (previous_status == "online" and new_status == "offline")
        
        await cls.trigger_notification(
            db=db,
            title=f"Device {new_status.title()}" if not is_concerning else "Device Unexpectedly Offline",
            content=f"Device {device.name} changed from {previous_status} to {new_status}",
            notification_type="warning" if is_concerning else "info",
            source="device_monitor",
            target_type="device",
            target_id=device.id if hasattr(device, "id") else None,
            target_name=device.name,
            priority=4 if is_concerning else 2,
            channels=["in_app"] if not is_concerning else ["in_app", "email"],
            metadata={
                "device_type": getattr(device, "device_type", "unknown"),
                "previous_status": previous_status,
                "new_status": new_status,
                "last_seen": device.last_seen.isoformat() if hasattr(device, "last_seen") and device.last_seen else None
            }
        )
    
    @classmethod
    async def notify_group_security_event(cls, db, group, event_type, affected_devices):
        """Notify about security events affecting a group of devices"""
        # Calculate the percentage of affected devices in the group
        device_count = getattr(group, "device_count", 0) or len(affected_devices)
        impact_percentage = (len(affected_devices) / device_count) * 100 if device_count > 0 else 0
        
        # Determine severity based on impact
        priority = 3
        if impact_percentage > 75:
            priority = 5
        elif impact_percentage > 50:
            priority = 4
        
        await cls.trigger_notification(
            db=db,
            title=f"Group Security Event: {event_type}",
            content=f"Security event affecting {len(affected_devices)} devices in group {group.name}",
            notification_type="warning",
            source="group_security",
            source_id=group.id if hasattr(group, "id") else None,
            target_type="group",
            target_id=group.id if hasattr(group, "id") else None,
            target_name=group.name,
            priority=priority,
            channels=["in_app", "email"] if priority >= 4 else ["in_app"],
            metadata={
                "event_type": event_type,
                "affected_device_count": len(affected_devices),
                "impact_percentage": round(impact_percentage, 1),
                "affected_device_ids": [getattr(d, "id", i) for i, d in enumerate(affected_devices[:10])]  # Limit to first 10
            }
        )

    # Convenience wrapper for vulnerability scan summary notifications
    async def create_vulnerability_notification(
        self,
        device_id: str,
        vulnerability_count: int,
        risk_score: float,
        critical_count: int = 0,
        vulnerabilities: Optional[List[Dict[str, Any]]] = None,
    ):
        """Send aggregated notification after a vulnerability scan.

        Args:
            device_id: Device hash_id or identifier.
            vulnerability_count: Total vulnerabilities discovered.
            risk_score: Calculated risk score.
            critical_count: Number of critical-severity vulnerabilities.
            vulnerabilities: List of vulnerability details.
        """
        # Default empty list for vulnerabilities details
        if vulnerabilities is None:
            vulnerabilities = []
        # Determine priority and channels
        priority = 4 if critical_count > 0 else 3
        channels: List[str] = ["in_app", "websocket"]
        if critical_count > 0:
            channels.append("email")

        notification_type = "warning" if vulnerability_count > 0 else "success"

        # Build detailed content
        content_lines = [
            f"Vulnerability scan completed for device {device_id}.",
            f"Total vulnerabilities: {vulnerability_count} (Critical: {critical_count}).",
            f"Risk score: {risk_score:.1f}",
        ]
        if vulnerabilities:
            content_lines.append("Details:")
            for v in vulnerabilities:
                title = v.get('title', v.get('id', 'Unknown'))
                severity = v.get('severity', 'unknown').capitalize()
                cvss = v.get('cvss_score', '')
                content_lines.append(f"- {title} (Severity: {severity}, CVSS: {cvss})")
        else:
            content_lines.append("No vulnerabilities detected.")
        content = "\n".join(content_lines)

        await NotificationHelper.trigger_notification(
            db=self.db,
            title=f"Vulnerability Scan Completed for {device_id}",
            content=content,
            notification_type=notification_type,
            source="vulnerability_scanner",
            target_type="device",
            target_id=None,
            target_name=None,
            priority=priority,
            channels=channels,
            metadata={
                "device_id": device_id,
                "vulnerability_count": vulnerability_count,
                "risk_score": risk_score,
                "critical_count": critical_count,
                "vulnerabilities": vulnerabilities,
            },
        )
