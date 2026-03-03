"""
SUPERNATURAL - Centralized Configuration
All settings loaded from environment variables via .env file
"""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

# Resolve .env from project root (SUPERNATURAL/.env)
# config.py is at SUPERNATURAL/backend/app/config.py → 3 parents up = SUPERNATURAL/
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    # ── App ────────────────────────────────────────────────────────────────
    APP_NAME: str = "SUPERNATURAL"
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    PORT: int = 8000

    # ── Database ───────────────────────────────────────────────────────────
    # Render provides DATABASE_URL automatically (PostgreSQL)
    # Falls back to SQLite for local development
    DATABASE_URL: str = "sqlite:///./supernatural.db"

    # ── Google OAuth / Meet ────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    GOOGLE_CALENDAR_CREDENTIALS_FILE: str = "credentials/google_credentials.json"
    GOOGLE_TOKEN_FILE: str = "credentials/token.json"

    # ── Gmail / Email ─────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    EMAIL_FROM_NAME: str = "SUPERNATURAL Platform"

    # ── OpenAI (for quiz generation & feedback) ────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # ── N8N Webhook Base URL ───────────────────────────────────────────────
    N8N_WEBHOOK_BASE_URL: str = "https://n8n-q7j7.onrender.com/webhook"
    N8N_API_KEY: str = ""

    # ── Google Credentials JSON (for Render / environments without the file) ─
    # Paste the entire contents of google_credentials.json as one line
    GOOGLE_CREDENTIALS_JSON: str = ""

    # ── Redis (for task queuing) ───────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    class Config:
        env_file = str(_ENV_FILE)
        extra = "ignore"


settings = Settings()
