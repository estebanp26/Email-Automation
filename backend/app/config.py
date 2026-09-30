import os
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Riwi HSE Email Automation Backend"
    VERSION: str = "3.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "*"
    ]
    
    # Ingestion & Validation
    MAX_ATTACHMENT_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    ALLOWED_ATTACHMENT_EXTENSIONS: List[str] = [".pdf", ".png", ".jpg", ".jpeg", ".webp"]
    FORMACION_EMAIL_OFFICIAL: str = "formacion.barranquilla@riwi.io"
    
    # Strata Core
    STRATA_CORE_URL: str = os.getenv("STRATA_CORE_URL", "http://localhost:8001")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/email_automation")

    # Plataforma Hermana (CONN-03 / EPIC-06)
    SISTER_PLATFORM_API_URL: str = os.getenv("SISTER_PLATFORM_API_URL", "https://api.plataforma-hermana.riwi.io/v1")
    SISTER_PLATFORM_API_KEY: str = os.getenv("SISTER_PLATFORM_API_KEY", "")
    SISTER_PLATFORM_USE_MOCK: bool = os.getenv("SISTER_PLATFORM_USE_MOCK", "true").lower() == "true"

    # Alertas Discord / Slack (CONN-EXT-01)
    HSE_DISCORD_WEBHOOK_URL: str = os.getenv("HSE_DISCORD_WEBHOOK_URL", "")

    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()
