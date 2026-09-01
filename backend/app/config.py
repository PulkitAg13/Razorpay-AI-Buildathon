"""
RECOVERX AI — Application Configuration
All settings loaded from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "RECOVERX AI"
    app_env: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # Database — SQLite default for local dev, PostgreSQL for production
    database_url: str = "sqlite+aiosqlite:///./recoverx.db"

    # LLM Provider
    llm_provider: str = "gemini"          # mock | gemini | openai
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.6-flash"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    # Event Bus
    event_bus: str = "memory"           # memory | redis
    redis_url: str = "redis://localhost:6379"

    # Recovery Policy Rules
    max_contact_attempts: int = 5
    max_recovery_cost_ratio: float = 0.05   # 5% of transaction value
    human_approval_threshold: float = 100000.0  # INR — above this, human approval recommended
    high_value_threshold: float = 50000.0
    min_confidence_for_auto: float = 0.60
    contact_hours_start: int = 9            # IST hour
    contact_hours_end: int = 21             # IST hour

    # Simulation
    simulation_seed: int = 42

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
