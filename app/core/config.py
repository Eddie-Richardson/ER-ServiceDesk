# ER-ServiceDesk/app/core/config.py
# Application settings loaded from environment variables

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration settings.
    Loads environment variables using Pydantic Settings (v2).
    """

    PROJECT_NAME: str = "ER Service Desk"
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }


settings = Settings()
