"""Application configuration.

All secrets and endpoints are sourced exclusively from environment variables
(see .env.example). Nothing here is hardcoded, and no credentials are ever
committed to the repository.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    secret_key: str = Field(default="change-me")

    database_url: str = Field(default="postgresql+asyncpg://oxiq:oxiq@localhost:5432/oxiq")
    database_url_sync: str = Field(default="postgresql+psycopg2://oxiq:oxiq@localhost:5432/oxiq")

    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")

    gemini_api_key: str | None = None
    gemini_model: str = Field(default="gemini-1.5-pro")

    tavily_api_key: str | None = None
    google_news_rss_base: str = Field(default="https://news.google.com/rss/search")

    crawl4ai_headless: bool = True
    crawl4ai_timeout_seconds: int = 30

    # Feature flags let every collector/agent run in "stub mode" until real
    # credentials are supplied, per the current no-live-API-calls workflow.
    enable_live_search: bool = False
    enable_live_crawl: bool = False
    enable_live_tech_detection: bool = False
    enable_live_llm: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
