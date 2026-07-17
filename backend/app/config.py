"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API
    app_name: str = "Multi-Agent Research Assistant"
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # LLM
    google_api_key: str = ""
    llm_model: str = "gemini-2.0-flash"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4096

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MongoDB
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "research_assistant"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Guardrails
    max_output_length: int = 10000
    hallucination_threshold: float = 0.7

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
