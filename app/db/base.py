"""Import all models for migrations"""

# This file is used to make all models accessible for Alembic
# Import all models here to ensure they're discovered during migrations

from app.db.base_class import Base

# Import all models below
from app.models.client import Client
from app.models.token import Token
from app.models.device import Device
from app.models.group import Group
from app.models.rule import Rule
from app.models.activity import Activity
from app.models.sensor_reading import SensorReading
from app.models.notification import Notification, NotificationRecipient 