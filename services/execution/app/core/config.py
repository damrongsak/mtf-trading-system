from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OANDA_API_KEY: str
    OANDA_ACCOUNT_ID: str
    OANDA_ENV: str = "practice"  # practice or live
    
    API_GATEWAY_URL: str = "http://api-gateway:8000/api/v1"
    REDIS_URL: str = "redis://redis:6379/0"
    INTERNAL_API_KEY: str = "dev_secret_key" # Should be set in .env

    class Config:
        env_file = ".env"

settings = Settings()
