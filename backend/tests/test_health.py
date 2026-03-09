"""Health endpoint tests — Phase A1 scaffold + B1 real DB ping."""

import pytest
import httpx
from httpx import ASGITransport
from unittest.mock import patch, AsyncMock

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


@pytest.mark.asyncio
async def test_health_returns_db_error_when_database_is_unavailable():
    """GET /health must return {"db": "error"} when the DB connection fails."""
    from unittest.mock import MagicMock, AsyncMock
    from sqlalchemy.exc import OperationalError

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=OperationalError("refused", None, None))
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_cm

    with patch("app.main.engine", mock_engine):
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

    data = response.json()
    assert response.status_code == 503, (
        f"Expected 503 when DB unreachable, got: {response.status_code}"
    )
    assert data.get("db") == "error", (
        f"Expected db='error' when DB unreachable, got: {data.get('db')}"
    )
