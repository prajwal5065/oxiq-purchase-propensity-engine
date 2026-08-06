"""FastAPI application entrypoint."""
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.routes import router as api_router
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="OxiQ Purchase Propensity Engine",
    description=(
        "Explainable B2B purchase propensity scoring from publicly available evidence. "
        "Not a chatbot, not a lead-gen tool, not a CRM."
    ),
    version="0.1.0",
)

app.include_router(health_router, tags=["health"])
app.include_router(api_router, tags=["propensity"])
