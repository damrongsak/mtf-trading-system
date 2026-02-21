from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    APP_NAME: str = "Olympus Predictor"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://trader:trader@mtf-postgres:5432/mtf_db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    MODEL_DIR: str = os.getenv("MODEL_DIR", "/app/models")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
