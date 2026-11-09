from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database - Use SQLite for local development
    DATABASE_URL: str = "sqlite:///./proposalcreator.db"
    # Apply Alembic migrations on startup (see app/core/migrations.py)
    AUTO_MIGRATE: bool = True

    # Security
    SECRET_KEY: str = "supersecretkeychangeinproduction"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Private deployments set this to false and create accounts with
    # `python -m app.cli create-user` instead of the public sign-up page.
    ALLOW_REGISTRATION: bool = True
    # Comma-separated browser origins allowed to call the API. Not needed when
    # the frontend and API share one origin behind the deploy/ reverse proxy.
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # AI Providers
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    # Default provider for app.services.llm: "claude" or "gemini"
    LLM_PROVIDER: str = "claude"
    CLAUDE_MODEL: str = "claude-opus-4-7"
    GEMINI_MODEL: str = "gemini-3.8-flash"

    # n8n orchestration
    # Base URL of n8n's production webhooks; workflow names are appended.
    N8N_WEBHOOK_BASE_URL: str = "http://localhost:5678/webhook"
    # Shared secret sent to n8n and required from n8n on /internal routes.
    # Empty disables the internal API entirely.
    N8N_SHARED_SECRET: str = ""
    # Base URL n8n uses to reach this backend (http://backend:8000 in docker).
    BACKEND_INTERNAL_URL: str = "http://localhost:8000"
    # A PENDING/RUNNING run with no callback for this long is marked FAILED
    # (e.g. n8n crashed or its first callback never arrived).
    WORKFLOW_RUN_TIMEOUT_MINUTES: int = 30

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
