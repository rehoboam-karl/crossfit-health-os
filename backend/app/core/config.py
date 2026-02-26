"""
Application Settings and Configuration
Loads environment variables and provides typed settings
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment"""
    
    # Application
    APP_NAME: str = "CrossFit Health OS"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str
    
    # Database (fallback for local Postgres)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/crossfit"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://crossfit.leicbit.com"
    ]
    
    # Frontend URL (for email links)
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Integrations
    GOOGLE_CALENDAR_CLIENT_ID: str = ""
    GOOGLE_CALENDAR_CLIENT_SECRET: str = ""
    APPLE_TEAM_ID: str = ""
    TODOIST_API_TOKEN: str = ""
    
    # AI & OCR
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # Default timezone for calendar events
    DEFAULT_TIMEZONE: str = "America/Sao_Paulo"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
