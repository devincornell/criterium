from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    gemini_api_key: SecretStr
    firecrawl_api_key: SecretStr
    db_url: str|None = "sqlite:///:memory:"

    # This tells pydantic-settings to look for a .env file in the root
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore other environment variables not defined here
    )

# Instantiate the settings once to be imported anywhere in the app
settings = Settings()
