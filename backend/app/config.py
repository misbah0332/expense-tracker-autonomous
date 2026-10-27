"""Runtime configuration loaded from the environment and the project .env file."""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
_ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    jwt_expire_minutes: int = 60
    database_admin_url: str | None = None
    db_name: str = "expense_tracker"
    db_app_user: str = "expense_app"
    db_app_password: str | None = None
    app_username: str | None = None
    app_password: str | None = None
    api_base_url: str = "http://127.0.0.1:8000"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("jwt_secret")
    @classmethod
    def secret_length(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return value

    @field_validator("jwt_expire_minutes")
    @classmethod
    def expire_window(cls, value: int) -> int:
        if value < 1 or value > 10080:
            raise ValueError("JWT_EXPIRE_MINUTES must be between 1 and 10080")
        return value


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
