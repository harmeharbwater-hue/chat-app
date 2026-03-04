import os
from functools import lru_cache
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Chat App Backend"
    environment: str = os.getenv("ENVIRONMENT", "development")

    # Security
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    encryption_key: str = os.getenv("ENCRYPTION_KEY", "dev-encryption-key-change-me")
    access_token_expire_minutes: int = 60 * 24  # 1 day
    algorithm: str = "HS256"

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./chat_app.db",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

