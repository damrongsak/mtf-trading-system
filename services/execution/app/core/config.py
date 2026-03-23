import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OANDA_API_KEY: str
    OANDA_ACCOUNT_ID: str
    OANDA_ENV: str = "practice"  # practice or live
    
    API_GATEWAY_URL: str = "http://api-gateway:8000/api/v1"
    AI_ANALYST_URL: str = "http://ai-analyst:8001/api/v1"
    REDIS_URL: str = "redis://redis:6379/0"
    INTERNAL_API_KEY: str = "dev_secret_key" # Should be set in .env
    
    SYSTEM_USER: str = os.getenv("SYSTEM_USER", "execution_service")
    SYSTEM_PASSWORD: str = os.getenv("SYSTEM_PASSWORD", "servicepassword123")
    
    PORTFOLIO_REBALANCE_INTERVAL: int = 21600 # 6 hours in seconds

    class Config:
        env_file = ".env"

settings = Settings()
