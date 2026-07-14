from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "AI Hospital Voice Receptionist"
    app_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:3000"
    hospital_timezone: str = "Asia/Karachi"

    database_url: str = "sqlite:///./hospital_voice_receptionist.db"
    app_secret_key: str = "dev-secret-change-me"
    pii_encryption_key: str = "dev-pii-key-change-me"
    vapi_tool_secret: str = "replace-with-long-random-vapi-secret"
    admin_api_token: str = "replace-with-long-random-admin-token"

    admin_bootstrap_email: str = "admin@example.com"
    admin_bootstrap_password: str = "change-this-password"

    sentry_dsn: str | None = None
    log_level: str = "INFO"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
