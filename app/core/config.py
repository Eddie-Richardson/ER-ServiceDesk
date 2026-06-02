# ER-ServiceDesk/app/core/config.py
# Application settings loaded from environment variables

from pydantic import BaseSettings

class Settings(BaseSettings):
    # Project name for identification/logging
    PROJECT_NAME: str = "ER Service Desk"

    # Database connection string (required)
    DATABASE_URL: str

    # Redis connection string (default points to docker-compose service)
    REDIS_URL: str = "redis://redis:6379/0"

    class Config:
        # Load variables from .env file
        env_file = ".env"

# Instantiate settings so the rest of the app can import it
settings = Settings()
