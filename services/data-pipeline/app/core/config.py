from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_ignore_empty=True, 
        extra="ignore"
    )

    DATABASE_URL: str = "postgresql://trader:trader@localhost:5432/mtf_db"
    
    # Oanda
    OANDA_API_KEY: str
    OANDA_ACCOUNT_ID: str
    OANDA_ENV: str = "practice" # or 'live'
    
    REDIS_URL: str = "redis://redis:6379/0"
    NEWS_API_KEY: Optional[str] = None

settings = Settings()
