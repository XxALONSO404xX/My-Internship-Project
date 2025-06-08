from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, IPvAnyAddress, EmailStr, validator

# Device schemas
class DeviceBase(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    device_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    description: Optional[str] = None

class DeviceCreate(DeviceBase):
    name: str
    ip_address: str

class DeviceUpdate(DeviceBase):
    is_online: Optional[bool] = None
    ports: Optional[Dict[str, Any]] = None
    device_metadata: Optional[Dict[str, Any]] = None

class DeviceInDB(DeviceBase):
    hash_id: str  # Using hashed ID for security
    is_online: bool
    last_seen: Optional[datetime]
    ports: Dict[str, Any]
    supports_http: bool
    supports_mqtt: bool
    supports_coap: bool
    supports_websocket: bool
    supports_tls: bool = True
    tls_version: Optional[str] = None
    cert_expiry: Optional[datetime] = None
    cert_issued_by: Optional[str] = None
    cert_strength: Optional[int] = None
    discovery_method: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Network scanning schemas
class NetworkInterface(BaseModel):
    name: str
    ip: str
    netmask: Optional[str] = None
    broadcast: Optional[str] = None

# Unused network scanning schemas - kept for reference or future implementation
'''
class NetworkScanRequest(BaseModel):
    network_range: Optional[str] = None
    ports: Optional[List[int]] = None
    timeout: Optional[int] = Field(default=10, ge=1, le=60)
    include_routers: Optional[bool] = Field(default=True, description="Whether to include routers in IoT device results")

class NetworkScanResponse(BaseModel):
    scan_id: str
    started_at: datetime
    status: str = "in_progress"
    devices_found: Optional[int] = None

class ScanResultDevice(BaseModel):
    ip_address: str
    mac_address: Optional[str] = None
    hostname: Optional[str] = None
    vendor: Optional[str] = None
    ports: Dict[str, Dict[str, str]] = {}
    discovery_method: str
    supports_http: bool = False
    supports_mqtt: bool = False

class ScanResults(BaseModel):
    scan_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    devices: List[ScanResultDevice] = []
'''
    
# System schemas
class SystemInfo(BaseModel):
    version: str
    uptime: float
    hostname: str
    network_interfaces: List[NetworkInterface]

# Activity schemas
class ActivityBase(BaseModel):
    activity_type: str = Field(..., description="Type of activity (user_action, system_event, state_change, alert)")
    action: str = Field(..., description="Action performed (turn_on, turn_off, update_settings, etc.)")
    description: Optional[str] = Field(None, description="Human-readable description of the activity")
    target_type: Optional[str] = Field(None, description="Type of target affected (device, group, system)")
    target_id: Optional[str] = Field(None, description="ID of the affected entity - hash_id for devices")
    target_name: Optional[str] = Field(None, description="Name of the affected entity")
    previous_state: Optional[Dict[str, Any]] = Field(None, description="State before the action")
    new_state: Optional[Dict[str, Any]] = Field(None, description="State after the action")
    metadata: Optional[Dict[str, Any]] = Field(None, alias="activity_metadata", description="Any additional context data")
    
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        populate_by_name = True  # allows alias usage
        from_attributes = True

class ActivityCreate(ActivityBase):
    user_id: Optional[int] = Field(None, description="ID of the user who performed the action")
    user_ip: Optional[str] = Field(None, description="IP address of the user")

class ActivityResponse(ActivityBase):
    id: int
    timestamp: datetime
    user_id: Optional[int] = None
    user_ip: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ActivityFilter(BaseModel):
    activity_type: Optional[str] = None
    action: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    user_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(100, ge=1, le=1000)
    skip: int = Field(0, ge=0)

# Scan schemas
class ScanRequest(BaseModel):
    scan_type: str = Field(..., description="Type of scan: 'discovery' or 'vulnerability'")
    network_range: Optional[str] = Field(None, description="Network range to scan in CIDR format, e.g. '192.168.1.0/24'")
    device_ids: Optional[List[str]] = Field(None, description="List of device hash_ids to scan for vulnerabilities")
    include_offline: bool = Field(False, description="Whether to include offline devices in vulnerability scan")
    scan_options: Optional[Dict[str, Any]] = Field(None, description="Additional scan options")
    
    class Config:
        json_schema_extra = {
            "example": {
                "scan_type": "discovery",
                "network_range": "192.168.1.0/24",
                "include_offline": False
            }
        }

class ScanResponse(BaseModel):
    scan_id: str
    status: str
    type: str
    start_time: Optional[str] = None

class ScanStatusResponse(BaseModel):
    scan_id: str
    status: str
    type: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    network_range: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ScanListResponse(BaseModel):
    scans: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int

class ScanResultsResponse(BaseModel):
    scan_id: str
    type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    network_range: Optional[str] = None
    results: Dict[str, Any] = Field(default_factory=dict)
    result_count: int = 0

# Pagination schema
class PaginationParams(BaseModel):
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)

# Response models
class Response(BaseModel):
    status: str = "success"
    message: str

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str

class ResponseModel(BaseModel):
    """Standard response model for API endpoints"""
    status: str = "success"
    message: str
    data: Optional[Any] = None

# Group schemas
class GroupBase(BaseModel):
    name: str = Field(..., description="Name of the group")
    description: Optional[str] = Field(None, description="Description of the group")
    group_type: str = Field("room", description="Type of group (room, location, category, etc.)")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Additional attributes for the group")
    icon: Optional[str] = Field(None, description="Icon for the group")
    color: Optional[str] = Field(None, description="Color code for the group")
    is_active: Optional[bool] = Field(True, description="Whether the group is active")

class GroupCreate(GroupBase):
    pass

class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Name of the group")
    description: Optional[str] = Field(None, description="Description of the group")
    group_type: Optional[str] = Field(None, description="Type of group (room, location, category, etc.)")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Additional attributes for the group")
    icon: Optional[str] = Field(None, description="Icon for the group")
    color: Optional[str] = Field(None, description="Color code for the group")
    is_active: Optional[bool] = Field(None, description="Whether the group is active")

class GroupResponse(GroupBase):
    id: int
    created_at: datetime
    updated_at: datetime
    device_count: int
    
    class Config:
        from_attributes = True

class GroupWithDevices(GroupResponse):
    devices: List[Dict[str, Any]] = Field([], description="Devices in the group")

# Sensor reading schemas
class SensorReadingBase(BaseModel):
    device_id: int = Field(..., description="ID of the device")
    sensor_type: str = Field(..., description="Type of sensor (temperature, humidity, etc.)")
    value: float = Field(..., description="Sensor reading value")
    unit: str = Field(..., description="Unit of measurement")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the reading")
    status: Optional[str] = Field("normal", description="Status of the reading (normal, warning, critical)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class SensorReadingCreate(BaseModel):
    device_id: int = Field(..., description="ID of the device")
    sensor_type: str = Field(..., description="Type of sensor (temperature, humidity, etc.)")
    value: float = Field(..., description="Sensor reading value")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    timestamp: Optional[datetime] = Field(None, description="Timestamp of the reading")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class SensorReadingResponse(BaseModel):
    """Schema for sensor reading responses"""
    id: int
    device_id: int
    timestamp: datetime
    sensor_type: str
    value: float
    unit: str
    status: str
    metadata: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "id": 1,
                "device_id": 2,
                "timestamp": "2023-09-01T12:34:56",
                "sensor_type": "temperature",
                "value": 22.5,
                "unit": "°C",
                "status": "normal",
                "metadata": {"target": 23.0, "mode": "heat"}
            }
        }

# Unused sensor data request schemas - kept for reference or future implementation
'''
class SensorTimeSeriesRequest(BaseModel):
    device_id: int = Field(..., description="ID of the device")
    sensor_type: str = Field(..., description="Type of sensor (temperature, humidity, etc.)")
    start_time: datetime = Field(..., description="Start time for data")
    end_time: datetime = Field(..., description="End time for data")
    limit: Optional[int] = Field(1000, description="Maximum number of readings to return")

class HistoricalDataRequest(BaseModel):
    device_id: int = Field(..., description="ID of the device")
    sensor_type: str = Field(..., description="Type of sensor (temperature, humidity, etc.)")
    start_time: datetime = Field(..., description="Start time for data generation")
    end_time: datetime = Field(..., description="End time for data generation")
    interval_minutes: Optional[int] = Field(5, description="Interval between readings in minutes")
'''

class AggregatedReadingResponse(BaseModel):
    period: str = Field(..., description="Time period for aggregation")
    sensor_type: str = Field(..., description="Type of sensor (temperature, humidity, etc.)")
    min_value: float = Field(..., description="Minimum reading value")
    max_value: float = Field(..., description="Maximum reading value")
    avg_value: float = Field(..., description="Average reading value")
    reading_count: int = Field(..., description="Number of readings in period")

# Group schemas
class GroupBase(BaseModel):
    name: str = Field(..., description="Name of the group")
    description: Optional[str] = Field(None, description="Description of the group")
    group_type: str = Field("room", description="Type of group (room, location, category, etc.)")
    icon: Optional[str] = Field(None, description="Icon identifier for UI display")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional attributes for the group")
    is_active: bool = Field(True, description="Whether the group is active")

class GroupCreate(GroupBase):
    device_ids: Optional[List[str]] = Field(None, description="List of device hash IDs to add to the group")

class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Name of the group")
    description: Optional[str] = Field(None, description="Description of the group")
    group_type: Optional[str] = Field(None, description="Type of group (room, location, category, etc.)")
    icon: Optional[str] = Field(None, description="Icon identifier for UI display")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Additional attributes for the group")
    is_active: Optional[bool] = Field(None, description="Whether the group is active")

class GroupResponse(GroupBase):
    id: int
    created_at: datetime
    updated_at: datetime
    device_count: Optional[int] = None

class GroupWithDevices(GroupResponse):
    devices: List[DeviceInDB] = []

# Rule schemas
class RuleCondition(BaseModel):
    operator: Optional[str] = Field("AND", description="Operator for combining conditions (AND, OR)")
    conditions: Optional[List[Dict[str, Any]]] = Field(None, description="List of conditions or condition groups")
    type: Optional[str] = Field(None, description="Condition type for single conditions (sensor, device_status, time, group)")
    device_id: Optional[int] = Field(None, description="Device ID for sensor/device conditions")
    sensor_type: Optional[str] = Field(None, description="Sensor type for sensor conditions")
    property: Optional[str] = Field(None, description="Property name for device_status conditions")
    value: Optional[Any] = Field(None, description="Value to compare against")
    time_window: Optional[int] = Field(None, description="Time window in minutes for sensor conditions")
    
    @validator('operator')
    def validate_operator(cls, v):
        if v not in ["AND", "OR"]:
            raise ValueError("Operator must be either 'AND' or 'OR'")
        return v

class RuleAction(BaseModel):
    type: str = Field(..., description="Action type (device_control, notification, group_control)")
    device_id: Optional[int] = Field(None, description="Device ID for device_control actions")
    group_id: Optional[int] = Field(None, description="Group ID for group_control actions")
    action: Optional[str] = Field(None, description="Control action to perform")
    parameters: Optional[Dict[str, Any]] = Field({}, description="Additional parameters for the action")
    title: Optional[str] = Field(None, description="Title for notification actions")
    content: Optional[str] = Field(None, description="Content for notification actions")
    notification_type: Optional[str] = Field(None, description="Type for notification actions")
    priority: Optional[int] = Field(None, description="Priority for notification actions")
    recipients: Optional[List[str]] = Field(None, description="Recipients for notification actions")
    channels: Optional[List[str]] = Field(None, description="Channels for notification actions")
    
    @validator('type')
    def validate_type(cls, v):
        valid_types = ["control_device", "set_status", "notification", "group_control"]
        if v not in valid_types:
            raise ValueError(f"Type must be one of: {', '.join(valid_types)}")
        return v
        
    @validator('parameters')
    def validate_parameters(cls, v, values):
        if 'type' not in values:
            return v
            
        if values['type'] == 'control_device' and v and 'action' not in v:
            raise ValueError("control_device action must have an action parameter")
            
        if values['type'] == 'notification':
            if not v.get('recipients'):
                raise ValueError("Notification action must have recipients")
            if not v.get('channels'):
                raise ValueError("Notification action must have channels")
        return v

class RuleBase(BaseModel):
    name: str = Field(..., description="Name of the rule")
    description: Optional[str] = Field(None, description="Description of the rule")
    rule_type: str = Field(..., description="Type of rule (threshold, schedule, state_change)")
    is_enabled: bool = Field(True, description="Whether the rule is enabled")
    schedule: Optional[str] = Field(None, description="Cron expression for scheduled rules")
    priority: Optional[int] = Field(1, description="Priority of the rule (higher = higher priority)")
    target_device_ids: Optional[List[str]] = Field(None, description="List of device hash IDs this rule applies to (null means all)")

class RuleCreate(RuleBase):
    conditions: Optional[Dict[str, Any]] = Field(None, description="Conditions that trigger the rule")
    actions: List[Dict[str, Any]] = Field(..., description="Actions to take when conditions are met")
    
    @validator('conditions')
    def validate_conditions(cls, v):
        if v is None:
            return v
        if "operator" not in v:
            raise ValueError("Conditions must have an operator (AND/OR)")
        
        if v["operator"] not in ["AND", "OR"]:
            raise ValueError(f"Invalid operator: {v['operator']}. Must be 'AND' or 'OR'")
            
        if "conditions" in v and not v["conditions"]:
            raise ValueError("Conditions must have at least one condition or be omitted")
         
        return v
        
    @validator('actions')
    def validate_actions(cls, v):
        if not v:
            raise ValueError("Rule must have at least one action")
        
        for action in v:
            if "type" not in action:
                raise ValueError("Action must have a type")
                
            valid_types = ["control_device", "set_status", "notification"]
            if action["type"] not in valid_types:
                raise ValueError(f"Invalid action type: {action['type']}. Must be one of: {', '.join(valid_types)}")
                
            # If control_device, validate action parameter
            if action["type"] == "control_device":
                parameters = action.get("parameters", {})
                if "action" not in parameters:
                    raise ValueError("control_device action must have an action parameter")
                    
            # If notification, validate recipients and channels
            if action["type"] == "notification":
                parameters = action.get("parameters", {})
                if not parameters.get("recipients"):
                    raise ValueError("Notification action must have recipients")
                if not parameters.get("channels"):
                    raise ValueError("Notification action must have channels")
                    
        return v

class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Name of the rule")
    description: Optional[str] = Field(None, description="Description of the rule")
    is_enabled: Optional[bool] = Field(None, description="Whether the rule is enabled")
    schedule: Optional[str] = Field(None, description="Cron expression for scheduled rules")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Conditions that trigger the rule")
    actions: Optional[List[Dict[str, Any]]] = Field(None, description="Actions to take when conditions are met")
    priority: Optional[int] = Field(None, description="Priority of the rule (higher = higher priority)")
    target_device_ids: Optional[List[str]] = Field(None, description="List of device hash IDs this rule applies to (null means all)")

class RuleData(RuleBase):
    id: int
    conditions: Optional[Dict[str, Any]] = None
    actions: List[Dict[str, Any]]
    last_triggered: Optional[datetime] = None
    status: str
    status_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class StandardResponse(BaseModel):
    """Standardized base response model for API operations"""
    status: str = Field("success", description="Response status: success or error")
    message: str = Field("", description="Human-readable response message")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="List of errors if any")

class RuleResponse(StandardResponse):
    """Standardized response model for rule operations"""
    data: Optional[Union[RuleData, List[RuleData], Dict[str, Any]]] = None

class RuleEvaluationResponse(BaseModel):
    rule_id: int
    rule_name: str
    triggered: bool
    success: bool
    actions_executed: Optional[int] = None
    action_results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# Notification schemas
class NotificationBase(BaseModel):
    title: str = Field(..., description="Notification title")
    content: str = Field(..., description="Notification content")
    notification_type: str = Field("info", description="Type of notification (info, warning, alert, error)")
    source: str = Field("system", description="Source of the notification (system, rule, user)")
    source_id: Optional[int] = Field(None, description="ID of the source (e.g., rule_id)")
    target_type: Optional[str] = Field(None, description="Type of target (device, group, system)")
    target_id: Optional[int] = Field(None, description="ID of the target")
    target_name: Optional[str] = Field(None, description="Name of the target")
    priority: int = Field(3, description="Priority level (1-5, where 5 is highest)")
    recipients: List[str] = Field([], description="List of recipient IDs or addresses")
    channels: List[str] = Field(["in_app"], description="List of delivery channels")
    notification_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id: int
    status: str
    status_message: Optional[str] = None
    delivery_attempts: int
    last_attempt: Optional[datetime] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class NotificationFilter(BaseModel):
    notification_type: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[int] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    priority: Optional[int] = None
    
# Firmware schemas
class FirmwareBase(BaseModel):
    version: str = Field(..., description="Firmware version")
    name: str = Field(..., description="Firmware name")
    device_type: str = Field(..., description="Device type this firmware is for")
    description: Optional[str] = Field(None, description="Firmware description")
    file_size: Optional[int] = Field(None, description="Size of firmware file in bytes")
    changelog: Optional[str] = Field(None, description="List of changes in this version")
    is_critical: bool = Field(False, description="Whether this is a critical update")

class FirmwareCreate(FirmwareBase):
    download_url: Optional[str] = Field(None, description="URL to download firmware")
    created_by: Optional[int] = Field(None, description="User ID who created this firmware")

class FirmwareUpdate(BaseModel):
    version: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    changelog: Optional[str] = None
    is_critical: Optional[bool] = None
    download_url: Optional[str] = None

class FirmwareResponse(FirmwareBase):
    id: str
    release_date: datetime
    download_url: Optional[str] = None
    created_at: datetime
    created_by: Optional[int] = None
    
    class Config:
        from_attributes = True

# Firmware update schemas
class FirmwareUpdateBase(BaseModel):
    device_id: str = Field(..., description="Device hash_id to update")
    firmware_id: str = Field(..., description="Firmware ID to update to")

class FirmwareUpdateCreate(FirmwareUpdateBase):
    pass

class FirmwareUpdateResponse(BaseModel):
    id: str
    device_id: str
    firmware_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int
    speed_kbps: Optional[int] = None
    estimated_time_remaining: Optional[int] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    batch_id: Optional[str] = None
    
    # TLS/Security fields
    secure_channel: bool = True
    encryption_method: Optional[str] = None
    signature_verified: Optional[bool] = None
    tls_version: Optional[str] = None
    
    # Include related information
    device_name: Optional[str] = None
    firmware_version: Optional[str] = None
    firmware_name: Optional[str] = None
    
    class Config:
        from_attributes = True
        
    @validator('device_name', 'firmware_version', 'firmware_name', pre=True, always=True)
    def set_related_fields(cls, v, values, **kwargs):
        field_name = kwargs['field'].name
        if field_name == 'device_name' and 'device' in values and values.get('device'):
            return values.get('device').name
        elif field_name == 'firmware_version' and 'firmware' in values and values.get('firmware'):
            return values.get('firmware').version
        elif field_name == 'firmware_name' and 'firmware' in values and values.get('firmware'):
            return values.get('firmware').name
        return v

# Batch update schemas
class FirmwareBatchUpdateBase(BaseModel):
    firmware_id: str = Field(..., description="Firmware ID to update to")
    name: Optional[str] = Field(None, description="Name for this batch update")
    notes: Optional[str] = Field(None, description="Notes about this batch update")

# Device control and status schemas
class DeviceControlResponse(BaseModel):
    device_id: str
    action: str
    success: bool
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    result: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class DeviceStatusResponse(BaseModel):
    device_id: str
    name: str
    is_online: bool
    status: str
    last_seen: Optional[datetime] = None
    uptime: Optional[int] = None
    firmware_version: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Sensor summary schema
class SensorSummaryResponse(BaseModel):
    total_sensors: int
    sensor_types: Dict[str, int]
    reading_count: int
    latest_readings: Dict[str, List[Dict[str, Any]]]
    device_count: int

class FirmwareBatchCreate(FirmwareBatchUpdateBase):
    device_ids: Optional[List[str]] = Field(None, description="List of device hash_ids to update")
    device_type: Optional[str] = Field(None, description="Device type to update (alternative to device_ids)")
    
    @validator('device_ids', 'device_type')
    def validate_target_devices(cls, v, values, **kwargs):
        field_name = kwargs['field'].name
        # Either device_ids or device_type must be provided
        if field_name == 'device_type' and not v and not values.get('device_ids'):
            raise ValueError("Either device_ids or device_type must be provided")
        return v

class FirmwareBatchResponse(BaseModel):
    id: str
    firmware_id: str
    name: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_devices: int
    successful_devices: int
    failed_devices: int
    created_at: datetime
    created_by: Optional[int] = None
    notes: Optional[str] = None
    
    # Include related information
    firmware_version: Optional[str] = None
    firmware_name: Optional[str] = None
    
    class Config:
        from_attributes = True
        
    @validator('firmware_version', 'firmware_name', pre=True, always=True)
    def set_related_fields(cls, v, values, **kwargs):
        field_name = kwargs['field'].name
        if field_name == 'firmware_version' and 'firmware' in values and values.get('firmware'):
            return values.get('firmware').version
        elif field_name == 'firmware_name' and 'firmware' in values and values.get('firmware'):
            return values.get('firmware').name
        return v

# Device firmware history schemas
class DeviceFirmwareHistoryResponse(BaseModel):
    id: int
    device_id: str
    firmware_id: str
    previous_version: Optional[str] = None
    updated_at: datetime
    update_id: Optional[str] = None
    
    # Include related information
    firmware_version: Optional[str] = None
    firmware_name: Optional[str] = None
    
    class Config:
        from_attributes = True
        
    @validator('firmware_version', 'firmware_name', pre=True, always=True)
    def set_related_fields(cls, v, values, **kwargs):
        field_name = kwargs['field'].name
        if field_name == 'firmware_version' and 'firmware' in values and values.get('firmware'):
            return values.get('firmware').version
        elif field_name == 'firmware_name' and 'firmware' in values and values.get('firmware'):
            return values.get('firmware').name
        return v
    is_read: Optional[bool] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(100, ge=1, le=1000)
    skip: int = Field(0, ge=0)

class NotificationWithClientsCreate(BaseModel):
    """Schema for creating a notification with client relationships"""
    title: str
    content: str
    client_ids: List[str]
    notification_type: str = "info"
    source: str = "system"
    source_id: Optional[int] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    target_name: Optional[str] = None
    priority: int = 3
    channels: List[str] = ["in_app"]
    metadata: Dict[str, Any] = {}

# Client schemas
class ClientBase(BaseModel):
    """Base client model"""
    username: str
    email: str
    is_active: bool = True
    preferences: Dict[str, Any] = {}

class ClientCreate(ClientBase):
    """Client creation model"""
    password: str
    id: Optional[str] = None

class ClientUpdate(BaseModel):
    """Client update model"""
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    preferences: Optional[Dict[str, Any]] = None

class ClientInDB(ClientBase):
    """Client model as stored in the database"""
    id: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

# Authentication schemas
class Token(BaseModel):
    """Token model"""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Token data model"""
    client_id: Optional[str] = None

# Desktop application specific schemas
class RefreshToken(BaseModel):
    """Refresh token response model"""
    refresh_token: str
    expires_at: datetime

class AuthResponse(BaseModel):
    """Base class for all authentication-related responses"""
    status: str = "success"
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

class TokenResponse(AuthResponse):
    """Complete token response including access and refresh tokens"""
    data: Dict[str, Any] = {
        "access_token": "",
        "token_type": "bearer",
        "refresh_token": "",
        "expires_at": None,
        "client": {}
    }
    
    @classmethod
    def create(cls, access_token: str, token_type: str, refresh_token: str, 
             expires_at: datetime, client: Dict[str, Any]) -> 'TokenResponse':
        """Create a token response with the specified data"""
        return cls(
            status="success",
            message="Authentication successful",
            data={
                "access_token": access_token,
                "token_type": token_type,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "client": client
            }
        )

class RefreshTokenRequest(BaseModel):
    """Request to refresh an access token"""
    refresh_token: str
    device_info: Optional[str] = None

class ClientLogin(BaseModel):
    """Client login credentials"""
    username: str
    password: str
    # For desktop applications
    device_info: Optional[str] = None
    remember_me: Optional[bool] = False

class PasswordResetRequest(BaseModel):
    """Password reset request model"""
    email: EmailStr = Field(..., description="Email address for password reset")
    
class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., description="New password")
    
class EmailVerificationConfirm(BaseModel):
    """Email verification confirmation model"""
    token: str = Field(..., description="Email verification token")

# Support diagnostics schemas
class HealthCheck(BaseModel):
    """Health check model"""
    status: str
    checks: Dict[str, Any]
    timestamp: datetime
    response_time_ms: float

# Unused diagnostic schema - kept for reference or future implementation
'''
class DiagnosticReport(BaseModel):
    """Diagnostic report model"""
    report_id: str
    report_type: str
    generated_at: datetime
    status: str
    data: Dict[str, Any]
    device: Optional[Dict[str, Any]] = None
'''

class ClientIssue(BaseModel):
    """Client issue model"""
    client_id: str
    issue_type: str
    description: Optional[str] = None 