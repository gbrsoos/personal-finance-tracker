from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BANKS: dict = {
    "Erste Bank": "HU", 
    "Revolut": "HU"
    }

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    enable_banking_app_id: str = Field(..., description="Enable Banking API ID")
    enable_banking_key_path: str = Field(..., description="Path to personal secret")
    redirect_url: str = Field(..., description="URL of the redirection")
    ssl_cert_path: str = Field(..., description="Path to MKCert SSL Cert")
    ssl_key_path: str = Field(..., description="Path to MKCert SSL Key")
    sessions_info_path: str = Field(..., description="Path to the current Session info")
    database_url: str = Field(..., description="Route to the SQLAlchemy session")

settings = Settings()