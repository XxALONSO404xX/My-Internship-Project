"""Network Security Simulation API for IoT platform dashboard"""
import random
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel

from app.models.database import get_db
from app.models.device import Device
from app.api.deps import get_current_client
from app.utils.notification_helper import NotificationHelper

router = APIRouter()
logger = logging.getLogger(__name__)

# Simulated attack types with descriptions
ATTACK_TYPES = {
    "port_scan": {
        "name": "Port Scanning", 
        "description": "Detected port scanning activity",
        "risk_level": "medium",
        "remediation": "Review firewall rules and block suspicious IPs"
    },
    "dos_attempt": {
        "name": "DoS Attempt", 
        "description": "Potential denial of service attempt",
        "risk_level": "high",
        "remediation": "Implement rate limiting and review traffic patterns"
    },
    "suspicious_traffic": {
        "name": "Suspicious Traffic Pattern", 
        "description": "Unusual traffic pattern detected",
        "risk_level": "low",
        "remediation": "Monitor device behavior for continued anomalies"
    },
    "unauthorized_access": {
        "name": "Unauthorized Access Attempt", 
        "description": "Attempt to access restricted resources",
        "risk_level": "high",
        "remediation": "Review authentication logs and strengthen access controls"
    },
    "malformed_packets": {
        "name": "Malformed Packets", 
        "description": "Detected malformed network packets",
        "risk_level": "medium",
        "remediation": "Update firmware and check for device compromise"
    }
}

# Simulated protocols
PROTOCOLS = ["HTTP", "MQTT", "CoAP", "TCP", "UDP", "AMQP", "BLE"]

@router.get("/traffic-stats")
async def get_network_traffic_stats(
    time_period: str = Query("1h", description="Time period for statistics (1h, 24h, 7d)"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """
    Get simulated network traffic statistics
    
    Returns packet counts, protocol distribution, and bandwidth usage
    """
    # Get all devices to generate realistic device IDs
    devices_query = await db.execute(
        text("SELECT hash_id, name, device_type FROM devices LIMIT 50")
    )
    devices = devices_query.fetchall()
    
    # If no devices, generate random data
    if not devices:
        devices = [
            {"hash_id": f"sim_{i}", "name": f"Simulated Device {i}", "device_type": random.choice(["sensor", "gateway", "controller"])}
            for i in range(1, 10)
        ]
    
    # Generate simulated traffic statistics
    total_packets = random.randint(10000, 1000000)
    incoming_packets = int(total_packets * random.uniform(0.4, 0.6))
    outgoing_packets = total_packets - incoming_packets
    
    # Protocol distribution based on device capabilities in DB
    http_count = (await db.execute(text("SELECT COUNT(*) FROM devices WHERE supports_http = true"))).scalar() or 0
    mqtt_count = (await db.execute(text("SELECT COUNT(*) FROM devices WHERE supports_mqtt = true"))).scalar() or 0
    coap_count = (await db.execute(text("SELECT COUNT(*) FROM devices WHERE supports_coap = true"))).scalar() or 0
    ws_count = (await db.execute(text("SELECT COUNT(*) FROM devices WHERE supports_websocket = true"))).scalar() or 0
    total_supported = http_count + mqtt_count + coap_count + ws_count
    protocol_distribution = {}
    if total_supported > 0:
        protocol_distribution['HTTP'] = round(http_count / total_supported * 100, 2)
        protocol_distribution['MQTT'] = round(mqtt_count / total_supported * 100, 2)
        protocol_distribution['CoAP'] = round(coap_count / total_supported * 100, 2)
        protocol_distribution['WebSocket'] = round(ws_count / total_supported * 100, 2)
    else:
        protocol_distribution = {'HTTP': 0, 'MQTT': 0, 'CoAP': 0, 'WebSocket': 0}
    
    # Generate time-series data
    time_points = 24  # 24 data points
    if time_period == "24h":
        interval = "hourly"
    elif time_period == "7d":
        interval = "daily"
        time_points = 7
    else:  # 1h default
        interval = "5-minute"
        time_points = 12
    
    traffic_series = []
    current_time = datetime.utcnow()
    
    for i in range(time_points):
        if interval == "hourly":
            point_time = current_time - timedelta(hours=time_points-i-1)
        elif interval == "daily":
            point_time = current_time - timedelta(days=time_points-i-1)
        else:
            point_time = current_time - timedelta(minutes=(time_points-i-1)*5)
            
        # Generate random traffic with some pattern (higher during work hours)
        hour = point_time.hour
        time_factor = 1.0
        if 9 <= hour <= 17:  # Higher traffic during work hours
            time_factor = 1.5
        elif 0 <= hour <= 5:  # Lower traffic at night
            time_factor = 0.3
            
        volume = int(random.normalvariate(5000, 1000) * time_factor)
        volume = max(100, volume)  # Ensure positive values
        
        traffic_series.append({
            "timestamp": point_time.isoformat(),
            "volume": volume,
            "packets": int(volume * random.uniform(0.8, 1.2))
        })
    
    # Top talkers (devices with most traffic)
    top_talkers = []
    random.shuffle(devices)
    for i, device in enumerate(devices[:5]):
        # Result rows from raw SQL are returned as tuples; simulated entries are dicts
        if isinstance(device, (list, tuple)):
            device_id, device_name = device[0], device[1]
        elif isinstance(device, dict):
            device_id, device_name = device.get("hash_id"), device.get("name")
        else:
            # Fallback – attempt attribute access
            device_id = getattr(device, "hash_id", None)
            device_name = getattr(device, "name", str(device))
        
        top_talkers.append({
            "device_id": device_id,
            "device_name": device_name,
            "packets_sent": random.randint(1000, 50000),
            "packets_received": random.randint(1000, 50000),
            "bandwidth_usage": f"{random.uniform(0.1, 10):.2f} MB"
        })
    
    return {
        "total_packets": total_packets,
        "incoming_packets": incoming_packets,
        "outgoing_packets": outgoing_packets,
        "bandwidth_usage": f"{random.uniform(10, 100):.2f} MB",
        "protocol_distribution": protocol_distribution,
        "traffic_series": traffic_series,
        "top_talkers": top_talkers,
        "analyzed_period": time_period,
        "analysis_timestamp": datetime.utcnow().isoformat()
    }

@router.get("/security-events")
async def get_security_events(
    time_period: str = Query("24h", description="Time period for events (1h, 24h, 7d)"),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high)"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """
    Get simulated network security events
    
    Returns detected anomalies, potential attacks, and security alerts
    """
    # Get some real device IDs if available
    devices_query = await db.execute(
        text("SELECT hash_id, name, device_type FROM devices LIMIT 50")
    )
    devices = devices_query.fetchall()
    
    if not devices:
        devices = [
            {"hash_id": f"sim_{i}", "name": f"Simulated Device {i}", "device_type": random.choice(["sensor", "gateway", "controller"])}
            for i in range(1, 10)
        ]
    
    # Determine time range based on period
    if time_period == "7d":
        start_time = datetime.utcnow() - timedelta(days=7)
        event_count = random.randint(5, 30)
    elif time_period == "24h":
        start_time = datetime.utcnow() - timedelta(days=1)
        event_count = random.randint(3, 15)
    else:  # 1h
        start_time = datetime.utcnow() - timedelta(hours=1)
        event_count = random.randint(0, 5)
    
    # Generate security events
    security_events = []
    notification_triggered = False  # Track if we've already sent a notification this session
    
    for _ in range(min(event_count, limit)):
        # Random timestamp within the period
        event_time = start_time + timedelta(
            seconds=random.randint(0, int((datetime.utcnow() - start_time).total_seconds()))
        )
        
        # Select random attack type
        attack_key = random.choice(list(ATTACK_TYPES.keys()))
        attack = ATTACK_TYPES[attack_key]
        
        # Skip if filtering by severity and doesn't match
        if severity and attack["risk_level"] != severity:
            continue
            
        # Select random source and target
        source_idx = random.randint(0, len(devices)-1)
        target_idx = random.randint(0, len(devices)-1)
        while target_idx == source_idx:
            target_idx = random.randint(0, len(devices)-1)
            
        source = devices[source_idx]
        target = devices[target_idx]
        
        source_id = source[0] if isinstance(source, tuple) else source["hash_id"]
        source_name = source[1] if isinstance(source, tuple) else source["name"]
        target_id = target[0] if isinstance(target, tuple) else target["hash_id"]
        target_name = target[1] if isinstance(target, tuple) else target["name"]
        
        # Generate random source IP (sometimes external, sometimes internal)
        if random.random() < 0.3:  # 30% chance of external IP
            source_ip = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
            source_id = None
            source_name = "External Actor"
        else:
            source_ip = f"192.168.{random.randint(0, 5)}.{random.randint(1, 254)}"
            
        target_ip = f"192.168.{random.randint(0, 5)}.{random.randint(1, 254)}"
        
        security_events.append({
            "id": f"SEC-{random.randint(10000, 99999)}",
            "timestamp": event_time.isoformat(),
            "event_type": attack_key,
            "name": attack["name"],
            "description": attack["description"],
            "severity": attack["risk_level"],
            "source": {
                "device_id": source_id,
                "device_name": source_name,
                "ip": source_ip,
                "port": random.randint(1024, 65535)
            },
            "target": {
                "device_id": target_id,
                "device_name": target_name,
                "ip": target_ip,
                "port": random.randint(1, 1024) if random.random() < 0.7 else random.randint(1024, 65535)
            },
            "protocol": random.choice(PROTOCOLS),
            "packet_count": random.randint(10, 1000),
            "action_taken": random.choice(["blocked", "logged", "alerted"]),
            "remediation": attack["remediation"]
        })
    
    # Sort by timestamp (newest first)
    security_events.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # Trigger notifications for high severity events - only one per API call to avoid flooding
    if not notification_triggered:
        high_severity_events = [event for event in security_events if event['severity'] == 'high']
        if high_severity_events and random.random() < 0.7:  # 70% chance to send notification for demo purposes
            try:
                # Select the most recent high severity event
                event = high_severity_events[0]
                # Only send notification for events that appear to be happening "now" (in the last hour)
                event_time = datetime.fromisoformat(event['timestamp'])
                if (datetime.utcnow() - event_time) < timedelta(hours=1):
                    await NotificationHelper.notify_security_event(
                        db=db,
                        event_type=event['name'],
                        source_ip=event['source']['ip'],
                        target_ip=event['target']['ip'],
                        severity='high'
                    )
                    notification_triggered = True
                    logger.info(f"Triggered notification for security event: {event['id']}")
            except Exception as e:
                logger.error(f"Error sending security event notification: {str(e)}")
    
    return {
        "total_events": event_count,
        "events": security_events[:limit],
        "time_period": time_period,
        "analysis_timestamp": datetime.utcnow().isoformat()
    }

@router.get("/network-topology")
async def get_network_topology(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """
    Get simulated network topology data
    
    Returns nodes (devices) and edges (connections) for visualization
    """
    # Get devices from database
    devices_query = await db.execute(
        text("SELECT hash_id, name, device_type FROM devices")
    )
    devices = devices_query.fetchall()
    
    if not devices:
        # Generate dummy devices if none exist
        devices = [
            {"hash_id": f"sim_{i}", "name": f"Simulated Device {i}", "device_type": random.choice(["sensor", "gateway", "controller"])}
            for i in range(1, 20)
        ]
    
    # Create nodes
    nodes = []
    for device in devices:
        if isinstance(device, dict):
            # Dummy or JSON-derived device
            device_id = device["hash_id"]
            device_name = device["name"]
            device_type = device["device_type"]
        else:
            # SQLAlchemy Row result
            device_id = getattr(device, "hash_id", None)
            device_name = getattr(device, "name", None)
            device_type = getattr(device, "device_type", None)
        
        # Determine node type based on device type
        node_type = "device"
        if "gateway" in device_type.lower():
            node_type = "gateway"
        elif "controller" in device_type.lower():
            node_type = "controller"
        elif "sensor" in device_type.lower():
            node_type = "sensor"
        
        nodes.append({
            "id": device_id,
            "name": device_name,
            "type": node_type,
            "status": random.choice(["online", "online", "online", "offline"]),  # 75% chance of being online
            "ip_address": f"192.168.{random.randint(0, 5)}.{random.randint(1, 254)}"
        })
    
    # Add router and internet nodes
    nodes.append({
        "id": "router_1",
        "name": "Main Router",
        "type": "router",
        "status": "online",
        "ip_address": "192.168.0.1"
    })
    
    nodes.append({
        "id": "internet",
        "name": "Internet",
        "type": "cloud",
        "status": "online",
        "ip_address": "external"
    })
    
    # Create edges (connections)
    edges = []
    
    # Connect devices based on type
    gateways = [node for node in nodes if node["type"] == "gateway"]
    controllers = [node for node in nodes if node["type"] == "controller"]
    sensors = [node for node in nodes if node["type"] == "sensor"]
    devices = [node for node in nodes if node["type"] == "device"]
    
    # Connect router to internet
    edges.append({
        "source": "router_1",
        "target": "internet",
        "type": "wan",
        "status": "active",
        "bandwidth": f"{random.randint(50, 100)} Mbps",
        "protocol": "TCP/IP"
    })
    
    # Connect gateways to router
    for gateway in gateways:
        edges.append({
            "source": gateway["id"],
            "target": "router_1",
            "type": "lan",
            "status": "active" if gateway["status"] == "online" else "inactive",
            "bandwidth": f"{random.randint(10, 100)} Mbps",
            "protocol": random.choice(["Ethernet", "WiFi", "Ethernet"])
        })
    
    # Connect controllers to router or gateways
    for controller in controllers:
        if gateways and random.random() < 0.7:  # 70% connect to gateway
            target = random.choice(gateways)
            edge_type = "local"
        else:
            target = {"id": "router_1"}
            edge_type = "lan"
            
        edges.append({
            "source": controller["id"],
            "target": target["id"],
            "type": edge_type,
            "status": "active" if controller["status"] == "online" else "inactive",
            "bandwidth": f"{random.randint(1, 10)} Mbps",
            "protocol": random.choice(["WiFi", "Ethernet", "Zigbee"])
        })
    
    # Connect sensors to controllers or gateways
    for sensor in sensors:
        if controllers and random.random() < 0.6:  # 60% connect to controller
            targets = controllers
            protocol = random.choice(["Zigbee", "Z-Wave", "BLE"])
        elif gateways:
            targets = gateways
            protocol = random.choice(["WiFi", "Zigbee", "Z-Wave"])
        else:
            targets = [{"id": "router_1"}]
            protocol = "WiFi"
            
        target = random.choice(targets)
        edges.append({
            "source": sensor["id"],
            "target": target["id"],
            "type": "sensor",
            "status": "active" if sensor["status"] == "online" else "inactive",
            "bandwidth": f"{random.randint(100, 1000)} Kbps",
            "protocol": protocol
        })
    
    # Connect other devices
    for device in devices:
        if random.random() < 0.3 and gateways:  # 30% to gateway
            target = random.choice(gateways)
            protocol = random.choice(["WiFi", "Ethernet"])
        else:
            target = {"id": "router_1"}
            protocol = random.choice(["WiFi", "Ethernet"])
            
        edges.append({
            "source": device["id"],
            "target": target["id"],
            "type": "device",
            "status": "active" if device["status"] == "online" else "inactive",
            "bandwidth": f"{random.randint(1, 50)} Mbps",
            "protocol": protocol
        })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "last_updated": datetime.utcnow().isoformat()
    }

@router.get("/summary")
async def get_network_security_summary(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """
    Get an overall network security summary
    
    Combines traffic statistics, security events, and assessment scores
    """
    # Get count of online devices
    device_count_query = await db.execute(
        text("SELECT COUNT(*) FROM devices")
    )
    device_count = device_count_query.scalar() or random.randint(5, 50)
    
    # Generate security score (0-100)
    security_score = random.randint(70, 95)
    
    # Determine security status based on score
    if security_score >= 90:
        security_status = "excellent"
    elif security_score >= 80:
        security_status = "good"
    elif security_score >= 70:
        security_status = "fair"
    else:
        security_status = "needs attention"
    
    # Generate events summary
    events_summary = {
        "total_last_24h": random.randint(0, 20),
        "high_severity": random.randint(0, 3),
        "medium_severity": random.randint(0, 5),
        "low_severity": random.randint(0, 12),
        "blocked_events": random.randint(0, 15)
    }
    
    # Generate traffic summary
    traffic_summary = {
        "total_gb_last_24h": round(random.uniform(1, 50), 2),
        "peak_mbps": round(random.uniform(10, 100), 2),
        "average_mbps": round(random.uniform(5, 50), 2),
        "anomalous_traffic_percent": round(random.uniform(0, 5), 2)
    }
    
    # Generate vulnerability stats
    vulnerability_summary = {
        "total_vulnerabilities": random.randint(0, device_count * 2),
        "critical": random.randint(0, 5),
        "high": random.randint(0, 10),
        "medium": random.randint(0, 15),
        "low": random.randint(0, 20),
        "remediated_last_7d": random.randint(0, 10)
    }
    
    # Firewall summary
    firewall_summary = {
        "total_rules": random.randint(10, 50),
        "active_rules": random.randint(10, 50),
        "blocked_ips_24h": random.randint(0, 20),
        "permitted_connections_24h": random.randint(1000, 10000),
        "denied_connections_24h": random.randint(10, 500)
    }
    
    return {
        "security_score": security_score,
        "security_status": security_status,
        "device_count": device_count,
        "monitored_protocols": len(PROTOCOLS),
        "events_summary": events_summary,
        "traffic_summary": traffic_summary,
        "vulnerability_summary": vulnerability_summary,
        "firewall_summary": firewall_summary,
        "last_updated": datetime.utcnow().isoformat(),
        "recommendations": [
            {
                "id": "REC001",
                "title": "Update firmware on vulnerable devices",
                "description": "Several devices have outdated firmware with known security vulnerabilities",
                "priority": "high" if vulnerability_summary["critical"] > 0 else "medium"
            },
            {
                "id": "REC002",
                "title": "Review firewall rules",
                "description": "Some firewall rules may be outdated or too permissive",
                "priority": "medium"
            },
            {
                "id": "REC003",
                "title": "Implement network segmentation",
                "description": "Separate IoT devices from critical infrastructure",
                "priority": "medium"
            }
        ]
    }
