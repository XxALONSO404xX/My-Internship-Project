"""Service for generating simulated sensor readings for virtual devices"""
import logging
import asyncio
import random
from datetime import datetime, timedelta
import math
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.device import Device
from app.models.sensor_reading import SensorReading

logger = logging.getLogger(__name__)

class SensorGenerator:
    """Service for generating simulated sensor readings"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # Track last generated values to create realistic changes
        self.last_values = {}
    
    async def generate_readings_for_all_devices(self) -> int:
        """
        Generate sensor readings for all devices
        
        Returns:
            Number of readings generated
        """
        # Get all devices
        query = select(Device).where(Device.is_online == True)
        result = await self.db.execute(query)
        devices = result.scalars().all()
        
        count = 0
        for device in devices:
            readings = await self.generate_readings_for_device(device)
            count += len(readings)
            
        return count
    
    async def generate_readings_for_device(self, device: Device) -> List[SensorReading]:
        """
        Generate appropriate sensor readings based on device type
        
        Args:
            device: Device to generate readings for
            
        Returns:
            List of generated sensor readings
        """
        device_type = device.device_type
        device_id = device.hash_id  # Use hash_id which is the primary key for Device model
        readings = []
        
        # Get device metadata for context
        metadata = device.device_metadata or {}
        
        # Generate appropriate readings based on device type
        if device_type == "thermostat":
            readings.extend(await self.generate_thermostat_readings(device_id, metadata))
        elif device_type == "camera":
            readings.extend(await self.generate_camera_readings(device_id, metadata))
        elif device_type in ["light", "smart_light"]:
            readings.extend(await self.generate_light_readings(device_id, metadata))
        elif device_type in ["lock", "smart_lock"]:
            readings.extend(await self.generate_lock_readings(device_id, metadata))
        elif device_type in ["speaker", "smart_speaker"]:
            readings.extend(await self.generate_speaker_readings(device_id, metadata))
        elif device_type == "sensor":
            readings.extend(await self.generate_sensor_readings(device_id, metadata))
        else:
            # For any other device type, generate generic readings
            readings.extend(await self.generate_generic_readings(device_id, metadata))
        
        # Add all readings to database
        for reading in readings:
            self.db.add(reading)
        
        # Commit all readings at once
        if readings:
            await self.db.commit()
            
        return readings
    
    async def generate_thermostat_readings(self, device_id: str, metadata: Dict[str, Any]) -> List[SensorReading]:
        """Generate thermostat sensor readings"""
        readings = []
        now = datetime.utcnow()
        
        # Get current state from metadata
        state = metadata.get("state", {})
        current_temp = state.get("current_temperature", 21.0)
        target_temp = state.get("target_temperature", 21.0)
        mode = state.get("mode", "heat")
        power = state.get("power", "off")
        
        # Create device key for tracking last values
        device_key = f"thermostat_{device_id}"
        
        # Temperature varies gradually with some random fluctuation
        # Base the next temperature on the last generated value if available
        if device_key not in self.last_values:
            self.last_values[device_key] = {"temperature": current_temp, "humidity": 45}
        
        last_temp = self.last_values[device_key]["temperature"]
        last_humidity = self.last_values[device_key]["humidity"]
        
        # Calculate new temperature based on heating/cooling
        new_temp = last_temp
        if power == "on":
            if mode == "heat" and last_temp < target_temp:
                # Heating up - move toward target with some randomness
                new_temp = min(target_temp, last_temp + random.uniform(0.05, 0.2))
            elif mode == "cool" and last_temp > target_temp:
                # Cooling down - move toward target with some randomness
                new_temp = max(target_temp, last_temp - random.uniform(0.05, 0.2))
        
        # Add some random fluctuation
        new_temp += random.uniform(-0.1, 0.1)
        new_temp = round(new_temp * 10) / 10  # Round to 1 decimal place
        
        # Create temperature reading
        temp_reading = SensorReading(
            device_id=device_id,
            timestamp=now,
            sensor_type="temperature",
            value=new_temp,
            unit="°C",
            status=self._get_temperature_status(new_temp),
            reading_metadata={"target": target_temp, "mode": mode, "power": power}
        )
        readings.append(temp_reading)
        
        # Generate humidity reading with slight fluctuation
        new_humidity = last_humidity + random.uniform(-2, 2)
        new_humidity = max(20, min(80, new_humidity))  # Keep between 20-80%
        new_humidity = round(new_humidity)
        
        humidity_reading = SensorReading(
            device_id=device_id,
            timestamp=now,
            sensor_type="humidity",
            value=new_humidity,
            unit="%",
            status="normal",
            reading_metadata={}
        )
        readings.append(humidity_reading)
        
        # Update last values
        self.last_values[device_key] = {
            "temperature": new_temp,
            "humidity": new_humidity
        }
        
        return readings
    
    async def generate_camera_readings(self, device_id: str, metadata: Dict[str, Any]) -> List[SensorReading]:
        """Generate camera sensor readings"""
        readings = []
        now = datetime.utcnow()
        
        # Motion detection - occasional motion events
        if random.random() < 0.2:  # 20% chance of motion
            motion_value = 1
            motion_status = "alert"
        else:
            motion_value = 0
            motion_status = "normal"
            
        motion_reading = SensorReading(
            device_id=device_id,
            timestamp=now,
            sensor_type="motion",
            value=motion_value,
            unit="binary",
            status=motion_status,
            reading_metadata={"duration": random.randint(1, 10) if motion_value == 1 else 0}
        )
        readings.append(motion_reading)
        
        # Light level (simulates day/night)
        hour = datetime.now().hour
        # Day/Night cycle simulation
        if 7 <= hour <= 19:  # Daytime
            light_level = random.uniform(70, 100)
            light_status = "bright"
        elif hour < 6 or hour > 20:  # Night
            light_level = random.uniform(0, 15)
            light_status = "dark"
        else:  # Dawn/Dusk
            light_level = random.uniform(15, 70)
            light_status = "dim"
            
        light_reading = SensorReading(
            device_id=device_id,
            timestamp=now,
            sensor_type="light_level",
            value=light_level,
            unit="lux",
            status=light_status,
            reading_metadata={}
        )
        readings.append(light_reading)
        
        return readings
    
    async def generate_light_readings(self, device_id: str, metadata: Dict[str, Any]) -> List[SensorReading]:
        """Generate light sensor readings"""
        readings = []
        now = datetime.utcnow()
        
        # Get state from metadata
        state = metadata.get("state", {})
        power = state.get("power", "off")
        brightness = state.get("brightness", 0)
        
        # Power consumption based on brightness
        if power == "on":
            energy_value = 1 + (brightness * 0.05)  # 1W base + up to 5W at full brightness
        else:
            energy_value = 0.2  # Standby power
            
        # Add small random fluctuation
        energy_value += random.uniform(-0.1, 0.1)
        energy_value = max(0, round(energy_value * 10) / 10)  # Round to 1 decimal place
        
        energy_reading = SensorReading(
            device_id=device_id,
            timestamp=now,
            sensor_type="power_usage",
            value=energy_value,
            unit="W",
            status="normal",
            reading_metadata={"power_state": power, "brightness": brightness}
        )
        readings.append(energy_reading)
        
        return readings
    
    async def generate_lock_readings(self, device_id: str, metadata: Dict[str, Any]) -> List[SensorReading]:
        """Generate lock sensor readings"""
        readings = []
        now = datetime.utcnow()
        
        # Battery level - decreases slowly over time
        device_key = f"lock_{device_id}"
        if device_key not in self.last_values:
            self.last_values[device_key] = {"battery": metadata.get("battery_level", 85)}
            
        # Decrease battery by a small amount
        new_battery = self.last_values[device_key]["battery"] - random.uniform(0.01, 0.05)
        new_battery = max(0, round(new_battery * 10) / 10)  # Round to 1 decimal
        
        battery_status = "normal"
        if new_battery < 15:
            battery_status = "critical"
        elif new_battery < 30:
            battery_status = "warning"
            
        battery_reading = SensorReading(
            device_id=device_id,
            timestamp=now,
            sensor_type="battery_level",
            value=new_battery,
            unit="%",
            status=battery_status,
            reading_metadata={}
        )
        readings.append(battery_reading)
        
        # Update last values
        self.last_values[device_key]["battery"] = new_battery
        
        # Lock status sensor
        lock_status = metadata.get("lock_status", "locked")
        lock_reading = SensorReading(
            device_id=device_id,
            timestamp=now,
            sensor_type="lock_state",
            value=1 if lock_status == "locked" else 0,
            unit="binary",
            status="normal",
            reading_metadata={"state": lock_status}
        )
        readings.append(lock_reading)
        
        return readings
    
    async def generate_speaker_readings(self, device_id: str, metadata: Dict[str, Any]) -> List[SensorReading]:
        """Generate speaker sensor readings"""
        readings = []
        now = datetime.utcnow()
        
        # Get state from metadata
        playing_status = metadata.get("playing_status", "stopped")
        volume = metadata.get("volume", 0)
        
        # Power usage depends on volume and if playing
        if playing_status == "playing":
            # Power usage scales with volume
            power_usage = 2 + (volume * 0.08)  # 2W base + up to 8W at full volume
        elif playing_status == "paused":
            power_usage = 1.5  # Lower usage when paused
        else:
            power_usage = 0.8  # Standby power
            
        # Add small fluctuation
        power_usage += random.uniform(-0.2, 0.2)
        power_usage = max(0, round(power_usage * 10) / 10)
        
        power_reading = SensorReading(
            device_id=device_id,
            timestamp=now,
            sensor_type="power_usage",
            value=power_usage,
            unit="W",
            status="normal",
            reading_metadata={"playing_status": playing_status, "volume": volume}
        )
        readings.append(power_reading)
        
        return readings
    
    async def generate_sensor_readings(self, device_id: str, metadata: Dict[str, Any]) -> List[SensorReading]:
        """Generate dedicated sensor device readings based on sensor type"""
        readings = []
        now = datetime.utcnow()
        
        sensor_type = metadata.get("sensor_type", "multi")
        
        if sensor_type == "temperature":
            # Temperature sensor
            device_key = f"temp_sensor_{device_id}"
            if device_key not in self.last_values:
                self.last_values[device_key] = {"temperature": 21.0}
                
            # Get last temperature reading with some fluctuation
            new_temp = self.last_values[device_key]["temperature"] + random.uniform(-0.3, 0.3)
            new_temp = round(new_temp * 10) / 10
            
            temp_reading = SensorReading(
                device_id=device_id,
                timestamp=now,
                sensor_type="temperature",
                value=new_temp,
                unit="°C",
                status=self._get_temperature_status(new_temp),
                reading_metadata={}
            )
            readings.append(temp_reading)
            
            # Update last value
            self.last_values[device_key]["temperature"] = new_temp
            
        elif sensor_type == "motion":
            # Motion sensor - random motion events
            if random.random() < 0.1:  # 10% chance of motion
                motion_value = 1
                motion_status = "alert"
            else:
                motion_value = 0
                motion_status = "normal"
                
            motion_reading = SensorReading(
                device_id=device_id,
                timestamp=now,
                sensor_type="motion",
                value=motion_value,
                unit="binary",
                status=motion_status,
                reading_metadata={}
            )
            readings.append(motion_reading)
            
        elif sensor_type == "door":
            # Door sensor - mostly closed with occasional open
            if random.random() < 0.05:  # 5% chance of being open
                door_value = 1  # Open
                door_status = "alert"
            else:
                door_value = 0  # Closed
                door_status = "normal"
                
            door_reading = SensorReading(
                device_id=device_id,
                timestamp=now,
                sensor_type="door",
                value=door_value,
                unit="binary",
                status=door_status,
                reading_metadata={"state": "open" if door_value == 1 else "closed"}
            )
            readings.append(door_reading)
            
        elif sensor_type == "multi":
            # Multi-sensor - generate both temperature and humidity
            device_key = f"multi_sensor_{device_id}"
            if device_key not in self.last_values:
                self.last_values[device_key] = {"temperature": 21.0, "humidity": 45.0}
                
            # Temperature with fluctuation
            new_temp = self.last_values[device_key]["temperature"] + random.uniform(-0.2, 0.2)
            new_temp = round(new_temp * 10) / 10
            
            temp_reading = SensorReading(
                device_id=device_id,
                timestamp=now,
                sensor_type="temperature",
                value=new_temp,
                unit="°C",
                status=self._get_temperature_status(new_temp),
                reading_metadata={}
            )
            readings.append(temp_reading)
            
            # Humidity with fluctuation
            new_humidity = self.last_values[device_key]["humidity"] + random.uniform(-1, 1)
            new_humidity = max(20, min(80, new_humidity))  # Keep between 20-80%
            new_humidity = round(new_humidity)
            
            humidity_reading = SensorReading(
                device_id=device_id,
                timestamp=now,
                sensor_type="humidity",
                value=new_humidity,
                unit="%", 
                status="normal",
                reading_metadata={}
            )
            readings.append(humidity_reading)
            
            # Update last values
            self.last_values[device_key] = {
                "temperature": new_temp,
                "humidity": new_humidity
            }
            
        return readings
    
    async def generate_generic_readings(self, device_id: str, metadata: Dict[str, Any]) -> List[SensorReading]:
        """Generate generic readings for unknown device types"""
        readings = []
        now = datetime.utcnow()
        
        # Generate a generic status reading
        status_reading = SensorReading(
            device_id=device_id,
            timestamp=now,
            sensor_type="status",
            value=1,  # 1 = ok
            unit="status",
            status="normal",
            reading_metadata={}
        )
        readings.append(status_reading)
        
        return readings
    
    def _get_temperature_status(self, temperature: float) -> str:
        """Determine temperature status based on value"""
        if temperature < 10:
            return "cold"
        elif temperature > 30:
            return "hot"
        else:
            return "normal"

# Background task for sensor generation
async def generate_sensor_readings_task(interval_seconds: int = 60):
    """
    Background task for periodically generating sensor readings
    
    Args:
        interval_seconds: How often to generate readings (in seconds)
    """
    logger.info(f"Sensor reading generator started - generating readings every {interval_seconds} seconds")
    
    while True:
        try:
            # Get a new database session for each generation cycle
            from app.models.database import get_db
            
            # Use the session directly from get_db
            db_gen = get_db()
            db = await anext(db_gen.__aiter__())
            
            generator = SensorGenerator(db)
            count = await generator.generate_readings_for_all_devices()
            logger.debug(f"Generated {count} sensor readings")
            
            # Close the session properly
            await db.close()
                
        except Exception as e:
            logger.error(f"Error in sensor reading generator: {str(e)}", exc_info=True)
            
        # Wait before next generation
        await asyncio.sleep(interval_seconds)

def start_sensor_generator(interval_seconds: int = 60) -> asyncio.Task:
    """
    Start the sensor reading generator as a background task
    
    Args:
        interval_seconds: How often to generate readings (in seconds)
        
    Returns:
        The created asyncio task
    """
    task = asyncio.create_task(generate_sensor_readings_task(interval_seconds))
    logger.info(f"Sensor reading generator started (every {interval_seconds} seconds)")
    return task 