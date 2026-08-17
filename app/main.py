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
# api_router is intentionally mounted at BOTH the bare root and under /api.
#
# frontend/src/api/client.ts defaults to calling every endpoint under an
# /api prefix whenever VITE_API_BASE_URL isn't set at build time - that's
# the /api mount below (added because a deployment relying on that default
# was 404ing).
#
# But the live Render deployment's actual frontend build calls the BARE
# paths directly (confirmed: GET /companies and the dashboard-summary
# endpoint 404'd in production on commit 9da859f, which only had the /api
# mount) - so VITE_API_BASE_URL is evidently set there to something that
# resolves without an /api segment. Mounting the same router at the bare
# root as well fixes that deployment immediately, without needing to know
# exactly how its VITE_API_BASE_URL is configured, and without touching or
# breaking whatever relies on the /api mount.
app.include_router(api_router, tags=["propensity"])
app.include_router(api_router, prefix="/api", tags=["propensity"])
