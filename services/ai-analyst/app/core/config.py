from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from dotenv import load_dotenv

load_dotenv(dotenv_path="/home/dan/workspace/mtf-trading-system/services/ai-analyst/.env")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_ignore_empty=True, 
        extra="ignore"
    )

    # Gemini
    # Gemini
    GOOGLE_API_KEY: str
    GEMINI_MODEL_ID: str = "gemini-2.5-flash"
    
    # Google Search
    GOOGLE_CSE_ID: Optional[str] = None
    GOOGLE_SEARCH_API_KEY: Optional[str] = None

    # NewsAPI
    NEWS_API_KEY: Optional[str] = None

    # Service URLs
    STRATEGY_CORE_URL: str = "http://strategy-core:8000"
    EXECUTION_SERVICE_URL: str = "http://execution:8000"
    API_GATEWAY_URL: str = "http://api-gateway:8000"

    # Qdrant
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_URL: Optional[str] = None # Alternative if full URL provided
    QDRANT_GRPC_HTTPS: bool = False # Whether to use HTTPS for Qdrant client connection

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    @property
    def qdrant_location(self) -> str:
        if self.QDRANT_URL:
            return self.QDRANT_URL
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

settings = Settings()
