"""Guards the API route mount points registered in app/main.py.

frontend/src/api/client.ts defaults to calling every endpoint under an
`/api` prefix whenever `VITE_API_BASE_URL` isn't set at build time - the
documented default for a same-origin production deployment (see
frontend/.env.example). Before this fix, `app.include_router(api_router,
...)` had no prefix at all, so any deployed frontend relying on that
default would 404 on every call, `/companies` and `/dashboard/summary`
included.

These tests exercise the real ASGI app (not just the router in isolation)
so a regression here - someone dropping the prefix again, or a route
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


# --- The two routes the reported production bug named directly -----------


def test_companies_list_resolves_under_api_prefix(client):
    response = client.get("/api/companies")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_dashboard_summary_resolves_under_api_prefix(client):
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200


# --- The old, pre-fix paths must no longer resolve ------------------------


def test_companies_list_no_longer_resolves_unprefixed(client):
    """Guards against silently re-adding the route at both mount points -
    the whole point of the fix is that the frontend's default /api-prefixed
    calls are what work, not a coincidental duplicate registration."""
    response = client.get("/companies")
    assert response.status_code == 404


def test_dashboard_summary_no_longer_resolves_unprefixed(client):
    response = client.get("/dashboard/summary")
    assert response.status_code == 404


# --- Every other api_router route the frontend calls, for completeness ----


def test_jobs_status_route_resolves_under_api_prefix(client):
    response = client.get("/api/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404  # job not found - but the route itself resolved
    assert response.json()["detail"] != "Not Found"


def test_company_detail_route_resolves_under_api_prefix(client):
    response = client.get("/api/company/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"  # app-level 404, not routing 404


# --- /health stays unprefixed on purpose - infra liveness checks hit it
# directly, and the frontend never calls it. -------------------------------


def test_health_still_resolves_unprefixed(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_does_not_also_resolve_under_api_prefix(client):
    response = client.get("/api/health")
    assert response.status_code == 404
