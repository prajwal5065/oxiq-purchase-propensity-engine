"""Guards the CORS configuration registered in app/main.py.

The deployed frontend (Vercel) and this API (Render) are different
origins, so every browser request between them is subject to the
browser's CORS check - independent of whether the route itself resolves
(see tests/unit/test_route_mount_points.py for that). Before this fix,
no CORSMiddleware was registered at all, so the browser silently blocked
every response - GET /dashboard/summary, /companies?limit=10, and
/companies?limit=50 included - even though the server had already
handled the request successfully.

These tests exercise the real ASGI app via TestClient so a regression -
the middleware disappearing, or the allowed origin drifting from the
actual deployed Vercel URL - is caught the same way it would manifest in
production: a response the browser would refuse to hand to the frontend.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app

PRODUCTION_ORIGIN = "https://oxiq-purchase-propensity-engine.vercel.app"


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


# --- The exact production symptom: actual GET requests from the Vercel
# origin must come back with an Access-Control-Allow-Origin header, or the
# browser discards the (otherwise successful) response. -------------------


@pytest.mark.parametrize("path", ["/dashboard/summary", "/companies?limit=10", "/companies?limit=50"])
def test_production_origin_receives_cors_header_on_the_reported_routes(client, path):
    response = client.get(path, headers={"Origin": PRODUCTION_ORIGIN})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == PRODUCTION_ORIGIN


def test_production_origin_receives_cors_header_under_api_prefix_too(client):
    response = client.get("/api/dashboard/summary", headers={"Origin": PRODUCTION_ORIGIN})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == PRODUCTION_ORIGIN


# --- Preflight: the browser sends this before the real GET/POST whenever
# it needs to check CORS eligibility. -----------------------------------


def test_preflight_from_production_origin_is_allowed(client):
    response = client.options(
        "/companies",
        headers={
            "Origin": PRODUCTION_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == PRODUCTION_ORIGIN
    assert "GET" in response.headers.get("access-control-allow-methods", "")


def test_preflight_allows_post_with_content_type_header_for_analyze(client):
    """The only POST the frontend makes (submitAnalysis) sends a JSON body
    with an explicit Content-Type header - both must be allowed."""
    response = client.options(
        "/analyze",
        headers={
            "Origin": PRODUCTION_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert "POST" in response.headers.get("access-control-allow-methods", "")
    assert "content-type" in response.headers.get("access-control-allow-headers", "").lower()


# --- A request from an origin that was never allowed must not get a
# matching Access-Control-Allow-Origin header - that's what makes the
# production origin allowance meaningful rather than a blanket "*". -------


def test_unrelated_origin_does_not_receive_a_matching_cors_header(client):
    response = client.get("/dashboard/summary", headers={"Origin": "https://evil.example.com"})
    assert response.status_code == 200  # the server still serves it...
    assert response.headers.get("access-control-allow-origin") != "https://evil.example.com"
    # ...but omits (or mismatches) the header, so the browser discards it.


def test_preflight_from_unrelated_origin_is_rejected(client):
    response = client.options(
        "/companies",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400


# --- A request with no Origin header at all (server-to-server, curl, the
# Vite dev proxy) must be entirely unaffected - CORS is a browser-enforced,
# browser-signaled mechanism only. -----------------------------------------


def test_request_without_origin_header_is_unaffected(client):
    response = client.get("/dashboard/summary")
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
