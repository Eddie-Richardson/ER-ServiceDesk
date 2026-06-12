# ER-ServiceDesk/app/core/config.py
# Application settings loaded from environment variables.
#
# This module defines the Settings class, which loads environment variables
# using Pydantic Settings (v2). It provides strongly typed configuration
# values for the ER‑ServiceDesk application, including database connection
# details, Redis configuration, and security-related settings.
# These settings are imported throughout the application to ensure consistent,
# centralized access to environment-driven configuration.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration settings.

    Loads environment variables using Pydantic Settings (v2).
    Values defined here are automatically pulled from the .env file.
    """

    # Core application metadata
    PROJECT_NAME: str = "ER Service Desk"

    # Database and cache configuration
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"

    # Security configuration (loaded from .env, never hard-coded)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Pydantic v2 configuration
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }


# Instantiate settings for global use
settings = Settings()
