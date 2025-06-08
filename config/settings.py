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
    SECRET_KEY: str = os.getenv('SECRET_KEY', '')
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 60 * 24 * 7))  # 7 days default
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 30))  # 30 days default
    ALGORITHM: str = os.getenv('ALGORITHM', 'HS256')  # JWT algorithm
    
    # Password validation settings
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False
    
    # PostgreSQL settings
    POSTGRES_SERVER: str = os.getenv('POSTGRES_SERVER', '')
    POSTGRES_USER: str = os.getenv('POSTGRES_USER', '')
    POSTGRES_PASSWORD: str = os.getenv('POSTGRES_PASSWORD', '')
    POSTGRES_DB: str = os.getenv('POSTGRES_DB', '')
    POSTGRES_PORT: str = os.getenv('POSTGRES_PORT', '5432')  # Default PostgreSQL port
    
    # Database URL
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    
    @validator('SQLALCHEMY_DATABASE_URI', pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        return f"postgresql://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_SERVER')}:{values.get('POSTGRES_PORT')}/{values.get('POSTGRES_DB')}"
    

    # WebSocket
    WS_MAX_CONNECTIONS: int = 100
    WS_PING_INTERVAL: int = 30  # seconds
    
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",        # React default
        "http://localhost:8080",        # Vue.js default
        "http://localhost:4200",        # Angular default
        "http://localhost:5174",        # Vite default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:4200",
        "http://127.0.0.1:5174",
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
    SMTP_SERVER: str = os.getenv('SMTP_SERVER', '')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME: str = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD: str = os.getenv('SMTP_PASSWORD', '')
    SMTP_USE_TLS: bool = True
    EMAIL_FROM_ADDRESS: str = os.getenv('EMAIL_FROM_ADDRESS', '')
    EMAIL_FROM_NAME: str = os.getenv('EMAIL_FROM_NAME', 'IoT Platform')
    FRONTEND_URL: str = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    # Twilio settings (no default values for security)
    TWILIO_ACCOUNT_SID: Optional[str] = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN: Optional[str] = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER: Optional[str] = os.getenv('TWILIO_PHONE_NUMBER', '')

    # Default notification recipients
    DEFAULT_NOTIFICATION_EMAIL: Optional[str] = os.getenv('DEFAULT_NOTIFICATION_EMAIL', '')
    DEFAULT_NOTIFICATION_PHONE: Optional[str] = os.getenv('DEFAULT_NOTIFICATION_PHONE', '')

    # Server settings
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: str = os.getenv('PORT', '8000')
    
    model_config = {
        'env_file': '.env',
        'case_sensitive': True,
        'extra': 'ignore'  # Allow extra fields
    }

settings = Settings() 