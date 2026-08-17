"""Guards the API route mount points registered in app/main.py.

api_router is intentionally mounted at BOTH the bare root and under /api:

- The /api mount exists because frontend/src/api/client.ts defaults to
  calling every endpoint under an /api prefix whenever VITE_API_BASE_URL
  isn't set at build time - a deployment relying on that default was
  404ing when api_router had no prefix at all.
- The bare-root mount exists because the live Render deployment's actual
  frontend build calls the paths directly with no /api segment - confirmed
  by GET /companies and the dashboard-summary endpoint both 404ing in
  production on a commit that only had the /api mount. Its
  VITE_API_BASE_URL is evidently configured to resolve without an /api
  segment, so the bare mount is what actually fixes that deployment.

These tests exercise the real ASGI app (not just the router in isolation)
so a regression here - either mount silently disappearing, or a route
getting registered outside `api_router` - is caught the same way it would
manifest in production: an HTTP 404 the frontend would actually hit.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    async def setup_schema():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(setup_schema())

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


# --- Regression test: the exact production symptom -------------------------
# GET /companies?limit=10 and the dashboard-summary endpoint 404ing on the
# live Render deployment. Both must resolve (non-404) at the bare path.


def test_companies_list_resolves_at_bare_path(client):
    response = client.get("/companies", params={"limit": 10})
    assert response.status_code != 404
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_dashboard_summary_resolves_at_bare_path(client):
    response = client.get("/dashboard/summary")
    assert response.status_code != 404
    assert response.status_code == 200


# --- Same two routes must also resolve under /api, for the other consumer -


def test_companies_list_resolves_under_api_prefix(client):
    response = client.get("/api/companies", params={"limit": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_dashboard_summary_resolves_under_api_prefix(client):
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200


# --- Every other api_router route, at both mount points, for completeness -


def test_jobs_status_route_resolves_at_both_mount_points(client):
    for prefix in ("", "/api"):
        response = client.get(f"{prefix}/jobs/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404  # job not found - but the route itself resolved
        assert response.json()["detail"] != "Not Found"


def test_company_detail_route_resolves_at_both_mount_points(client):
    for prefix in ("", "/api"):
        response = client.get(f"{prefix}/company/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        assert response.json()["detail"] == "Company not found"  # app-level 404, not routing 404


# --- /health stays unprefixed only - infra liveness checks hit it directly,
# and the frontend never calls it. ------------------------------------------


def test_health_resolves_unprefixed(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_does_not_also_resolve_under_api_prefix(client):
    response = client.get("/api/health")
    assert response.status_code == 404
