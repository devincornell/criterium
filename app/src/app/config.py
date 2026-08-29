import functools

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr

class Settings(BaseSettings):
    gemini_api_key: SecretStr
    firecrawl_api_key: SecretStr
    db_url: str = "sqlite:///./criterium.db"
    research_worker_poll_seconds: float = 0.5
    research_worker_concurrency: int = Field(default=3, ge=1, le=16)

    # This tells pydantic-settings to look for a .env file in the root
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore other environment variables not defined here
    )

@functools.lru_cache
def get_settings() -> Settings:
    return Settings()
