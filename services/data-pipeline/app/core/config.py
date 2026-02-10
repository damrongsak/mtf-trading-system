from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from typing import Optional, List
from pydantic import BaseModel


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

class CalendarSettings(BaseModel):
    source_url: str = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    cache_ttl: int = 21600 # 6 hours
    currencies: List[str] = ["USD"]
    redis_key: str = "calendar:{currency}"
    sync_interval_minutes: int = 60
    fetch_timeout: float = 30.0

settings = Settings()
calendar_settings = CalendarSettings()

