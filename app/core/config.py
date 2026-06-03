# ER-ServiceDesk/app/core/config.py
# Application settings loaded from environment variables
#
# This module defines the Settings class, which loads and validates all
# environment‑based configuration for the ER‑ServiceDesk application.
# It centralizes project metadata, database connection details, and
# Redis configuration. The Settings instance is imported throughout the
# application to ensure consistent access to environment variables.

from pydantic import BaseSettings

class Settings(BaseSettings):
    """
    Application configuration settings.

    This class loads environment variables using Pydantic's BaseSettings.
    It provides strongly‑typed access to core configuration values such as
    the project name, database connection string, and Redis URL.
    """

    # Project name used for logging, metadata, and identification
    PROJECT_NAME: str = "ER Service Desk"

    # Database connection string (required for application startup)
    DATABASE_URL: str

    # Redis connection string (default points to docker-compose Redis service)
    REDIS_URL: str = "redis://redis:6379/0"

    class Config:
        # Specifies that environment variables should be loaded from a .env file
        env_file = ".env"


# Instantiate settings so the rest of the application can import a ready-to-use config object
settings = Settings()
