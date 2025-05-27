import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator

class Settings(BaseSettings):
    # API Settings
    API_V1_PREFIX: str = '/api/v1'
    PROJECT_NAME: str = 'IoT Management Platform'
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'THIS_SHOULD_BE_CHANGED_IN_PRODUCTION')
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = 'HS256'
    
    # PostgreSQL settings
    POSTGRES_SERVER: str = os.getenv('POSTGRES_SERVER', 'localhost')
    POSTGRES_USER: str = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD: str = os.getenv('POSTGRES_PASSWORD', '1234')
    POSTGRES_DB: str = os.getenv('POSTGRES_DB', 'ProjectBD')
    POSTGRES_PORT: str = os.getenv('POSTGRES_PORT', '5432')
    
    # Database URL
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    
    @validator('SQLALCHEMY_DATABASE_URI', pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        return f"postgresql://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_SERVER')}:{values.get('POSTGRES_PORT')}/{values.get('POSTGRES_DB')}"
    
    # Network Scanning - commented out since we're using virtual simulation
    # NETWORK_SCAN_INTERVAL: int = 300  # seconds
    # SCAN_TIMEOUT: int = 10  # seconds
    # DEFAULT_SCAN_PORTS: List[int] = [80, 443, 1883, 8883, 8080, 5683]  # Common IoT ports
    # NETWORK_RANGES: List[str] = ['192.168.1.0/24']  # Default network range to scan
    
    # MQTT - commented out since we're only doing virtual simulation
    # MQTT_BROKER_HOST: str = os.getenv('MQTT_BROKER_HOST', 'localhost')
    # MQTT_BROKER_PORT: int = int(os.getenv('MQTT_BROKER_PORT', '1883'))
    # MQTT_USERNAME: Optional[str] = os.getenv('MQTT_USERNAME')
    # MQTT_PASSWORD: Optional[str] = os.getenv('MQTT_PASSWORD')
    # MQTT_CLIENT_ID: str = os.getenv('MQTT_CLIENT_ID', 'iot_platform')
    
    # WebSocket
    WS_MAX_CONNECTIONS: int = 100
    WS_PING_INTERVAL: int = 30  # seconds
    
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",        # React default
        "http://localhost:8080",        # Vue.js default
        "http://localhost:4200",        # Angular default
        "http://localhost:5173",        # Vite default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:4200",
        "http://127.0.0.1:5173",
        "app://.",                     # Electron app protocol
        "file://",                    # Local file protocol for desktop apps
        "electron://altair"           # Electron specific protocol
    ]
    
    # For development mode, allow all origins for desktop app testing
    ALLOW_ALL_ORIGINS_FOR_DESKTOP: bool = os.getenv('ALLOW_ALL_ORIGINS_FOR_DESKTOP', 'True').lower() == 'true'
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    CORS_ALLOW_HEADERS: List[str] = ["Content-Type", "Authorization", "X-Requested-With"]
    
    # Email settings
    SMTP_SERVER: str = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME: str = os.getenv('SMTP_USERNAME', 'eduanouar@gmail.com')
    SMTP_PASSWORD: str = os.getenv('SMTP_PASSWORD', 'njsogkqauemargyy')
    SMTP_USE_TLS: bool = True
    EMAIL_FROM_ADDRESS: str = os.getenv('EMAIL_FROM_ADDRESS', 'eduanouar@gmail.com')
    EMAIL_FROM_NAME: str = os.getenv('EMAIL_FROM_NAME', 'IoT Platform')
    FRONTEND_URL: str = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    # Twilio settings (made optional with default empty strings)
    TWILIO_ACCOUNT_SID: Optional[str] = os.getenv('TWILIO_ACCOUNT_SID', 'AC45123be8fbe966fbc7837ae1ec99ca6b')
    TWILIO_AUTH_TOKEN: Optional[str] = os.getenv('TWILIO_AUTH_TOKEN', '09bd92abc5f39036d235a521306e3758')
    TWILIO_PHONE_NUMBER: Optional[str] = os.getenv('TWILIO_PHONE_NUMBER', '+212702174311')
    
    # Server settings
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: str = os.getenv('PORT', '8000')
    
    model_config = {
        'env_file': '.env',
        'case_sensitive': True,
        'extra': 'ignore'  # Allow extra fields
    }

settings = Settings() 