from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    line_channel_secret: str
    line_channel_access_token: str

    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"

    daily_cost_ceiling_usd: float = 5.0
    rate_limit_hour: int = 10
    rate_limit_day: int = 30
    history_turns: int = 20

    owner_line_user_id: str | None = None
    seller_line_id: str = ""
    rich_menu_id: str | None = None

    liff_id: str = ""

    admin_username: str = "admin"
    admin_password_hash: str = ""
    admin_jwt_secret: str = ""
    admin_base_url: str = "http://localhost:8000"

    database_url: str
    port: int = 8000

    @field_validator("database_url", mode="after")
    @classmethod
    def _ensure_psycopg_driver(cls, raw: str) -> str:
        if raw.startswith("postgres://"):
            return "postgresql+psycopg://" + raw[len("postgres://"):]
        if raw.startswith("postgresql://") and "+psycopg" not in raw:
            return "postgresql+psycopg://" + raw[len("postgresql://"):]
        return raw


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
