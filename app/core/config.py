# ER-ServiceDesk/app/core/config.py
# Application settings loaded from environment variables.
"""
Strongly-typed application configuration, loaded from environment
variables (and .env locally) via Pydantic Settings.
"""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application configuration settings."""
    PROJECT_NAME: str = "ER Service Desk"
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

settings = Settings()