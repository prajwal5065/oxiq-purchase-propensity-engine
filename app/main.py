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
# The frontend's API client (frontend/src/api/client.ts) defaults to
# calling every endpoint under an /api prefix whenever VITE_API_BASE_URL
# isn't set at build time (the documented, expected default for a
# same-origin production deployment - see frontend/.env.example). The
# routes below previously had no prefix at all, so any deployed frontend
# relying on that default - e.g. its /companies and /dashboard/summary
# calls - would 404. /health stays unprefixed: it's a liveness/readiness
# endpoint conventionally polled directly by infra (Docker/k8s), and the
# frontend never calls it.
app.include_router(api_router, prefix="/api", tags=["propensity"])
