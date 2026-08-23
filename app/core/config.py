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

    anthropic_api_key: str | None = None
    anthropic_model: str = Field(default="claude-3-5-sonnet-20241022")

    gemini_api_key: str | None = None
    gemini_model: str = Field(default="gemini-2.5-flash")

    tavily_api_key: str | None = None
    google_news_rss_base: str = Field(default="https://news.google.com/rss/search")

    github_token: str | None = Field(
        default=None, description="Optional - raises the unauthenticated 60 req/hr GitHub API rate limit"
    )
    github_api_base: str = Field(default="https://api.github.com")

    crawl4ai_headless: bool = True
    crawl4ai_timeout_seconds: int = 30

    # Company & Technology Intelligence. Company profile/jobs providers
    # below are free/unauthenticated public sources with no key setting.
    # Technology Intelligence uses BuiltWith as the primary, keyed provider
    # (BUILTWITH_API_KEY, server-side only - never returned by any API
    # response) with the existing Python (Wappalyzer) detector as an
    # unauthenticated fallback when BuiltWith is unconfigured, rate
    # limited, or erroring - see app/collectors/tech_collector.py.
    company_profile_timeout_seconds: int = 15
    wikidata_api_base: str = Field(default="https://www.wikidata.org/w/api.php")

    builtwith_api_key: str | None = None

    # Jobs (Greenhouse / Lever) - both are free, unauthenticated public
    # job-board APIs; no key setting exists for the same reason as above.
    jobs_timeout_seconds: int = 15
    greenhouse_api_base: str = Field(default="https://boards-api.greenhouse.io/v1/boards")
    lever_api_base: str = Field(default="https://api.lever.co/v0/postings")

    # Feature flags let every collector/agent run in "stub mode" until real
    # credentials are supplied, per the current no-live-API-calls workflow.
    enable_live_search: bool = False
    enable_live_crawl: bool = False
    enable_live_tech_detection: bool = False
    enable_live_llm: bool = False
    enable_live_github: bool = False
    enable_live_company_profile: bool = False
    enable_live_jobs: bool = False

    # Dev-only: run Celery tasks eagerly (inline) without a broker/worker.
    # Set CELERY_TASK_ALWAYS_EAGER=true in .env to use without Redis.
    celery_task_always_eager: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
