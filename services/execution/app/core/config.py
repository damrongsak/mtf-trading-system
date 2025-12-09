from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OANDA_API_KEY: str
    OANDA_ACCOUNT_ID: str
    OANDA_ENV: str = "practice"  # practice or live

    class Config:
        env_file = ".env"

settings = Settings()
