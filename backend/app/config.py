"""Application configuration loaded from environment / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "sqlite:///./salon.db"

    # Auth / JWT
    secret_key: str = "change-me-in-production-please-use-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # CORS (comma-separated origins)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Availability engine
    slot_interval_minutes: int = 15
    booking_buffer_minutes: int = 0

    # Salon local timezone (IANA name, e.g. "Asia/Kolkata", "America/New_York").
    # Working hours and the "hide past slots" cutoff are interpreted in this zone.
    salon_tz: str = "Asia/Kolkata"

    # Seed admin
    admin_email: str = "admin@salon.test"
    admin_password: str = "admin12345"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
