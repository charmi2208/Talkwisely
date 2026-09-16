"""
TalkWiseAI Backend Application Configuration.

Reads all settings from environment variables (.env file).
No secrets should ever be hardcoded here.
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # .env.local (git-ignored) holds real secrets and overrides the committed .env
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = "TalkWiseAI"
    app_env: Literal["development", "production", "test"] = "development"
    app_debug: bool = True
    app_secret_key: str = "dev-secret-change-in-production"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    # ---- Database ----
    database_url: str = "postgresql+asyncpg://talkwise:talkwise@localhost:5432/talkwiseai"
    database_sync_url: str = "postgresql://talkwise:talkwise@localhost:5432/talkwiseai"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ---- Redis ----
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ---- JWT ----
    jwt_secret_key: str = "dev-jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # ---- LLM Provider ----
    llm_provider: Literal["openai", "mock"] = "mock"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096
    llm_base_url: str = ""  # For OpenAI-compatible APIs (e.g. Groq: https://api.groq.com/openai/v1)
    llm_max_concurrency: int = 3  # Parallel LLM calls; keeps free-tier rate limits happy
    llm_reasoning_effort: str = ""  # low | medium | high — only for reasoning models (e.g. openai/gpt-oss-*)

    # ---- Embedding Provider ----
    # local = ONNX all-MiniLM-L6-v2 bundled with chromadb (no API key, runs on CPU)
    embedding_provider: Literal["openai", "local", "mock"] = "mock"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # ---- Speech-to-Text ----
    stt_provider: Literal["whisper_local", "whisper_api", "mock"] = "mock"
    whisper_model: str = "base"
    # whisper_api: any OpenAI-compatible transcription endpoint. Falls back to the LLM key/base URL.
    stt_api_key: str = ""
    stt_base_url: str = ""
    stt_api_model: str = "whisper-large-v3-turbo"
    stt_max_upload_mb: int = 25

    # ---- File Storage ----
    storage_provider: Literal["local", "s3"] = "local"
    storage_local_path: str = "./storage"
    storage_max_upload_size_mb: int = 500
    storage_allowed_audio_extensions: str = ".mp3,.wav,.m4a,.ogg,.flac"
    storage_allowed_video_extensions: str = ".mp4,.avi,.mov,.mkv,.webm"

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    aws_s3_bucket: str = ""

    # ---- Vector DB ----
    vector_db_provider: str = "chromadb"
    chroma_persist_dir: str = "./vector_store"

    # ---- CRM Integration ----
    crm_provider: Literal["mock", "hubspot", "salesforce", "zoho"] = "mock"
    hubspot_api_key: str = ""
    salesforce_client_id: str = ""
    salesforce_client_secret: str = ""

    # ---- Calendar Integration ----
    calendar_provider: Literal["mock", "google", "outlook"] = "mock"
    google_client_id: str = ""
    google_client_secret: str = ""

    # ---- Email Integration ----
    email_provider: Literal["mock", "sendgrid", "smtp"] = "mock"
    sendgrid_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@talkwiseai.com"

    # ---- TalkWisely Integration ----
    talkwisely_provider: Literal["mock", "talkwisely"] = "mock"
    talkwisely_api_base_url: str = ""
    talkwisely_api_key: str = ""
    talkwisely_account_id: str = ""

    # ---- Logging ----
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    # ---- CORS ----
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ---- Rate Limiting ----
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_period_seconds: int = 60

    # ---- Demo Mode ----
    demo_mode_enabled: bool = True
    demo_org_slug: str = "demo"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str) -> str:
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_audio_extensions(self) -> list[str]:
        return [e.strip() for e in self.storage_allowed_audio_extensions.split(",")]

    @property
    def allowed_video_extensions(self) -> list[str]:
        return [e.strip() for e in self.storage_allowed_video_extensions.split(",")]

    @property
    def allowed_media_extensions(self) -> list[str]:
        return self.allowed_audio_extensions + self.allowed_video_extensions

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()


# Convenience alias used throughout the app
settings = get_settings()
