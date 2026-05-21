from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database - Use SQLite for local development
    DATABASE_URL: str = "sqlite:///./proposalcreator.db"

    # Security
    SECRET_KEY: str = "supersecretkeychangeinproduction"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Providers
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()