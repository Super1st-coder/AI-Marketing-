"""Application configuration"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
from core.logging import get_logger

logger = get_logger(__name__)

class Settings(BaseSettings):
    """Application settings"""
    
    # App
    APP_NAME: str = "Data Backend Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    API_V2_PREFIX: str = "/api/v2"
    
    DATABASE_HOST: Optional[str] = None
    DATABASE_PORT: Optional[int] = None
    DATABASE_USERNAME: Optional[str] = None
    DATABASE_PASSWORD: Optional[str] = None
    DATABASE_NAME_DEFAULT: Optional[str] = None
    
    @property
    def POSTGRES_CONNECTION_STRING(self) -> str:
        """Generate PostgreSQL connection string from environment variables"""
        if not all([self.DATABASE_USERNAME, self.DATABASE_PASSWORD, self.DATABASE_HOST, self.DATABASE_PORT, self.DATABASE_NAME_DEFAULT]):
            raise ValueError("PostgreSQL configuration is incomplete. Please set all required environment variables in .env file")
        return f"postgresql+psycopg://{self.DATABASE_USERNAME}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME_DEFAULT}"
    
    # Redis (Celery broker + result backend)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # Security — internal service auth
    FURY_INTERNAL_API_KEY: Optional[str] = None

    # Security — Google OIDC for Agent Engine endpoints
    OIDC_AUDIENCE: Optional[str] = None

    # CORS
    # In production set to explicit origins, e.g.:
    CORS_ORIGINS: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Create global settings instance
settings = get_settings()
