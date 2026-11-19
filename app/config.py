from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://inboxguard:inboxguard@localhost:5434/inboxguard"
    token_encryption_key: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    telegram_bot_token: str = ""

    llm_provider: Literal["openai_compatible", "anthropic"] = "openai_compatible"
    llm_key: str = ""
    llm_model: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_json_mode: bool = True
    llm_price_input_per_m: float | None = None
    llm_price_output_per_m: float | None = None

    default_timezone: str = "Asia/Kolkata"

    # Urgency wait thresholds (hours). Used by later milestones.
    urgency_5_hours: int = 1
    urgency_4_hours: int = 2
    urgency_3_hours: int = 24
    urgency_2_hours: int = 48

    quiet_hours_start: int = 22
    quiet_hours_end: int = 8
    max_realtime_alerts_per_day: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
