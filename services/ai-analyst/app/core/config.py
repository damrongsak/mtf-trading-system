from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv


class GeminiSettings(BaseModel):
    api_key: str
    model_id: str
    flash_model_id: str = "gemini-2.5-flash"
    flash_lite_model_id: str = "gemini-2.5-flash-lite"
    embedding_dim: int = 768

class QdrantSettings(BaseModel):
    host: str
    port: int
    api_key: Optional[str]
    url: Optional[str]
    grpc_https: bool

    @property
    def location(self) -> str:
        if self.url:
            return self.url
        return f"http://{self.host}:{self.port}"

class ServiceSettings(BaseModel):
    strategy_core_url: str
    execution_url: str
    api_gateway_url: str

class RedisSettings(BaseModel):
    url: str

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_ignore_empty=True, 
        extra="ignore"
    )

    # Raw Environment Variables
    GOOGLE_API_KEY: str
    GEMINI_MODEL_ID: str = "gemini-2.5-pro"
    GEMINI_FLASH_MODEL_ID: str = "gemini-2.5-flash"
    GEMINI_FLASH_LITE_MODEL_ID: str = "gemini-2.5-flash-lite"
    GEMINI_EMBEDDING_DIM: int = 3072
    SERPAPI_API_KEY: Optional[str] = None
    
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_URL: Optional[str] = None
    QDRANT_GRPC_HTTPS: bool = False
    
    STRATEGY_CORE_URL: str = "http://strategy-core:8000"
    EXECUTION_SERVICE_URL: str = "http://execution:8000"
    API_GATEWAY_URL: str = "http://api-gateway:8000"
    
    REDIS_URL: str = "redis://redis:6379/0"
    DATA_PIPELINE_URL: str = "http://data-pipeline:8000"
    OLYMPUS_PREDICTOR_URL: str = "http://olympus-predictor:8000"
    INTERNAL_API_KEY: str = "dev-internal-key"
    TELEGRAM_BOT_TOKEN: Optional[str] = None

    @property
    def gemini(self) -> GeminiSettings:
        return GeminiSettings(
            api_key=self.GOOGLE_API_KEY,
            model_id=self.GEMINI_MODEL_ID,
            flash_model_id=self.GEMINI_FLASH_MODEL_ID,
            flash_lite_model_id=self.GEMINI_FLASH_LITE_MODEL_ID,
            embedding_dim=self.GEMINI_EMBEDDING_DIM
        )

    @property
    def qdrant(self) -> QdrantSettings:
        return QdrantSettings(
            host=self.QDRANT_HOST,
            port=self.QDRANT_PORT,
            api_key=self.QDRANT_API_KEY,
            url=self.QDRANT_URL,
            grpc_https=self.QDRANT_GRPC_HTTPS
        )

    @property
    def services(self) -> ServiceSettings:
        return ServiceSettings(
            strategy_core_url=self.STRATEGY_CORE_URL,
            execution_url=self.EXECUTION_SERVICE_URL,
            api_gateway_url=self.API_GATEWAY_URL
        )

    @property
    def redis(self) -> RedisSettings:
        return RedisSettings(url=self.REDIS_URL)

settings = Settings()
