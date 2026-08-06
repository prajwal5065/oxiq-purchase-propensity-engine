"""Celery application factory.

Task definitions (e.g. `run_full_analysis`) land in phase 6+ once the Rule
Engine and Purchase Aggregator exist to give a worker something complete to
run end-to-end. For now this wires up the app so `docker compose` brings up
a working worker process.
"""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "oxiq",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
