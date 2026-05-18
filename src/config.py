from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    enable_banking_app_id: str = Field(description="Enable Banking API ID")
    enable_banking_key_path: str = Field(description="Path to personal secret")
    redirect_url: str = Field(description="URL of the redirection")

settings = Settings()