"""Health endpoint tests — Phase A1 scaffold."""

import pytest
import httpx
from httpx import ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_200():
    """GET /health must return HTTP 200."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_body_contains_status_ok():
    """GET /health response body must contain {"status": "ok"}."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    data = response.json()
    assert data.get("status") == "ok"


@pytest.mark.asyncio
async def test_health_body_contains_version_key():
    """GET /health response body must contain a 'version' key."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    data = response.json()
    assert "version" in data


@pytest.mark.asyncio
async def test_health_body_contains_db_key():
    """GET /health response body must contain a 'db' key."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    data = response.json()
    assert "db" in data
