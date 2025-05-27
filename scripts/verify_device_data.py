"""
Script to verify device data is properly aligned with the IoT platform functionalities
"""
import psycopg2
import json
from datetime import datetime
from tabulate import tabulate

def get_connection_params():
    """Get database connection parameters with correct credentials."""
    return {
        "user": "postgres",
        "password": "1234",
        "host": "localhost",
        "port": "5432",
        "dbname": "ProjectBD"
    }

def verify_device_data():
    """Verify device data aligns with IoT platform functionalities."""
    # Connect to the database
    params = get_connection_params()
    print(f"Connecting to PostgreSQL database at {params['host']}:{params['port']}...")
    conn = psycopg2.connect(**params)
    cur = conn.cursor()
    
    try:
        # Check database schema
        print("\n1. DATABASE SCHEMA")
        tables_to_check = [
            "devices", "firmware", "firmware_updates", "groups", "device_groups", 
            "clients", "notifications"
        ]
        
        missing_tables = []
        for table in tables_to_check:
            cur.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
            exists = cur.fetchone()[0]
            if not exists:
                missing_tables.append(table)
        
        if missing_tables:
            print(f"✗ Missing tables: {', '.join(missing_tables)}")
        else:
            print("✓ All required tables exist")
        
        # Table counts
        print("\n2. DATA SUMMARY")
        table_counts = {}
        for table in tables_to_check:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                table_counts[table] = count
            except:
                table_counts[table] = "ERROR"
        
        for table, count in table_counts.items():
            print(f"{table}: {count} records")
            
        # Device types summary
        print("\n3. DEVICE TYPES SUMMARY")
        cur.execute("SELECT device_type, COUNT(*) FROM devices GROUP BY device_type")
        device_types = cur.fetchall()
        for device_type, count in device_types:
            print(f"{device_type}: {count}")
        
        # Verify key relationships
        print("\n4. DATA INTEGRITY CHECK")
        
        # Run all integrity checks
        integrity_checks = [
            # Check 1: Devices with invalid firmware references
            {
                "query": """
                SELECT COUNT(*) FROM devices d 
                LEFT JOIN firmware f ON d.current_firmware_id = f.id
                WHERE d.current_firmware_id IS NOT NULL AND f.id IS NULL
                """,
                "label": "Devices with invalid firmware reference"
            },
            # Check 2: Firmware updates with invalid device references
            {
                "query": """
                SELECT COUNT(*) FROM firmware_updates fu 
                LEFT JOIN devices d ON fu.device_id = d.hash_id
                WHERE d.hash_id IS NULL
                """,
                "label": "Firmware updates with invalid device reference"
            },
            # Check 3: Firmware updates with invalid firmware references
            {
                "query": """
                SELECT COUNT(*) FROM firmware_updates fu 
                LEFT JOIN firmware f ON fu.firmware_id = f.id
                WHERE f.id IS NULL
                """,
                "label": "Firmware updates with invalid firmware reference"
            },
            # Check 4: Device groups with invalid device references
            {
                "query": """
                SELECT COUNT(*) FROM device_groups dg 
                LEFT JOIN devices d ON dg.device_id = d.hash_id
                WHERE d.hash_id IS NULL
                """,
                "label": "Device-group associations with invalid device reference"
            },
            # Check 5: Device groups with invalid group references
            {
                "query": """
                SELECT COUNT(*) FROM device_groups dg 
                LEFT JOIN groups g ON dg.group_id = g.id
                WHERE g.id IS NULL
                """,
                "label": "Device-group associations with invalid group reference"
            },
            # Check 6: Devices with TLS but missing certificate info
            {
                "query": """
                SELECT COUNT(*) FROM devices 
                WHERE supports_tls = TRUE AND (cert_expiry IS NULL OR cert_issued_by IS NULL OR cert_strength IS NULL)
                """,
                "label": "Devices with incomplete TLS configuration"
            }
        ]
        
        issues_found = 0
        for check in integrity_checks:
            cur.execute(check["query"])
            count = cur.fetchone()[0]
            if count > 0:
                issues_found += count
                print(f"✗ {check['label']}: {count}")
        
        if issues_found == 0:
            print("✓ All data integrity checks passed")
        
        # Metadata validity check (simplified)
        print("\n5. METADATA CHECK")
        cur.execute("SELECT COUNT(*) FROM devices WHERE device_metadata IS NULL OR device_metadata = '{}'")
        empty_metadata_count = cur.fetchone()[0]
        if empty_metadata_count > 0:
            print(f"✗ {empty_metadata_count} devices have empty metadata")
        else:
            print("✓ All devices have metadata")
            
        # Check for device-specific capabilities
        print("\n6. FUNCTIONALITY ALIGNMENT")
        functionality_checks = [
            # Security devices should have TLS support
            {
                "query": """
                SELECT COUNT(*) FROM devices 
                WHERE device_type LIKE 'security%' AND supports_tls = FALSE
                """,
                "label": "Security devices without TLS support"
            },
            # Sensor devices should have MQTT support
            {
                "query": """
                SELECT COUNT(*) FROM devices 
                WHERE device_type LIKE '%sensor' AND supports_mqtt = FALSE
                """,
                "label": "Sensor devices without MQTT support"
            },
            # Cameras should have websocket support
            {
                "query": """
                SELECT COUNT(*) FROM devices 
                WHERE device_type = 'security_camera' AND supports_websocket = FALSE
                """,
                "label": "Cameras without websocket support"
            }
        ]
        
        functionality_issues = 0
        for check in functionality_checks:
            cur.execute(check["query"])
            count = cur.fetchone()[0]
            if count > 0:
                functionality_issues += count
                print(f"✗ {check['label']}: {count}")
        
        if functionality_issues == 0:
            print("✓ All devices have appropriate protocol support for their type")
        
        # Overall assessment
        print("\n7. OVERALL ASSESSMENT")
        total_issues = issues_found + functionality_issues + (1 if empty_metadata_count > 0 else 0) + len(missing_tables)
        
        if total_issues == 0:
            print("✓ All device data is properly aligned with IoT platform functionalities!")
            print("✓ No data integrity issues were detected.")
        else:
            print(f"✗ Found {total_issues} potential issues that need to be addressed.")
        
    except Exception as e:
        print(f"Error during verification: {str(e)}")
    finally:
        cur.close()
        conn.close()

def get_expected_metadata_fields(device_type):
    """Return expected metadata fields based on device type."""
    # Define expected metadata fields for each device type
    type_to_fields = {
        "temperature_sensor": ["temperature", "unit", "accuracy", "battery_level"],
        "combined_sensor": ["temperature", "humidity", "pressure", "battery_level"],
        "thermostat": ["current_temp", "target_temp", "mode", "humidity"],
        "security_lock": ["lock_type", "battery_level", "access_log_size"],
        "smart_light": ["brightness", "color", "supports_rgb"],
        "motion_sensor": ["sensitivity", "detection_range", "battery_level"],
        "security_camera": ["resolution", "night_vision", "storage"],
        "contact_sensor": ["state", "battery_level", "alert_delay"],
        "water_sensor": ["sensitivity", "battery_level", "last_alert"],
        "air_quality": ["pm25", "voc", "co2", "aqi"],
        "energy_meter": ["current_usage_watts", "daily_kwh", "billing_cycle_days_left"],
        "energy_controller": ["current_production_watts", "daily_kwh", "panels_active"],
        "air_purifier": ["filter_life_remaining", "mode", "fan_speed"],
        "health_device": ["last_measurement", "battery_level"]
    }
    
    # Return expected fields for the given device type, or an empty list if type is unknown
    return type_to_fields.get(device_type, [])

if __name__ == "__main__":
    try:
        verify_device_data()
    except Exception as e:
        print(f"Verification failed: {str(e)}")
