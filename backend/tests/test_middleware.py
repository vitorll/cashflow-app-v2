"""C5 — Request ID middleware tests.

RED PHASE: All tests in this file MUST FAIL before any middleware implementation.

Requirements under test:
1. Every HTTP response carries an X-Request-ID header.
2. X-Request-ID is a valid UUID4.
3. If the client sends X-Request-ID, the server echoes it back unchanged.
4. If the client does NOT send X-Request-ID, the server generates one.
5. Different requests without a client header produce different request IDs.
6. The request ID appears in structlog output for the duration of the request.
7. Structlog contextvars are cleared between requests (no leakage).

This test must fail before we proceed. It is our way.
"""

import uuid

import httpx
import pytest
import structlog
from httpx import ASGITransport

from app.main import app


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _is_valid_uuid(value: str) -> bool:
    """Return True if *value* is a well-formed UUID (any version)."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


# ---------------------------------------------------------------------------
# 1. Response always carries X-Request-ID
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_response_always_has_x_request_id_header():
    """Every response must include the X-Request-ID header."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert "x-request-id" in response.headers, (
        "Expected X-Request-ID header in response, but it was absent."
    )


# ---------------------------------------------------------------------------
# 2. X-Request-ID in response is a valid UUID
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_response_x_request_id_is_valid_uuid():
    """The server-generated (or echoed) X-Request-ID must be a valid UUID."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    request_id = response.headers.get("x-request-id", "")
    assert _is_valid_uuid(request_id), (
        f"X-Request-ID '{request_id}' is not a valid UUID."
    )


# ---------------------------------------------------------------------------
# 3. Server echoes client-provided X-Request-ID
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_server_echoes_client_provided_x_request_id():
    """When the client sends X-Request-ID, the server must return the same value."""
    client_request_id = str(uuid.uuid4())

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/health", headers={"X-Request-ID": client_request_id}
        )

    echoed = response.headers.get("x-request-id", "")
    assert echoed == client_request_id, (
        f"Expected server to echo '{client_request_id}', got '{echoed}'."
    )


# ---------------------------------------------------------------------------
# 4. Server generates X-Request-ID when client does not provide one
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_server_generates_x_request_id_when_not_provided_by_client():
    """When the client omits X-Request-ID, the server must generate a valid UUID."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Explicitly omit X-Request-ID (default httpx client sends none)
        response = await client.get("/health")

    request_id = response.headers.get("x-request-id", "")
    assert request_id, "Expected server to generate X-Request-ID, but header was empty."
    assert _is_valid_uuid(request_id), (
        f"Server-generated X-Request-ID '{request_id}' is not a valid UUID."
    )


# ---------------------------------------------------------------------------
# 5. Different requests produce different request IDs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_different_requests_produce_different_request_ids():
    """Two requests without a client-provided ID must yield different UUIDs."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r1 = await client.get("/health")
        r2 = await client.get("/health")

    id1 = r1.headers.get("x-request-id", "")
    id2 = r2.headers.get("x-request-id", "")

    assert id1 and id2, "Both responses must have X-Request-ID headers."
    assert id1 != id2, (
        f"Expected unique request IDs per request, but both were '{id1}'."
    )


# ---------------------------------------------------------------------------
# 6. Request ID appears in structlog output during the request
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_request_id_appears_in_structlog_output():
    """Every log line emitted during a request must carry request_id."""
    with structlog.testing.capture_logs() as captured:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

    expected_id = response.headers.get("x-request-id", "")
    assert expected_id, "Cannot verify log output — response had no X-Request-ID."

    # At least one log event must carry the request_id bound by middleware.
    request_ids_in_logs = [
        ev.get("request_id") for ev in captured if "request_id" in ev
    ]
    assert request_ids_in_logs, (
        "No log event carried a 'request_id' key. "
        "Middleware must bind request_id into structlog contextvars."
    )
    assert expected_id in request_ids_in_logs, (
        f"Expected request_id='{expected_id}' in logs, "
        f"but only found: {request_ids_in_logs}"
    )


# ---------------------------------------------------------------------------
# 7. Structlog contextvars are cleared between requests (no leakage)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_structlog_contextvars_cleared_between_requests():
    """request_id bound for request N must NOT appear in request N+1's logs."""
    # ---- First request ----
    with structlog.testing.capture_logs() as first_logs:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r1 = await client.get("/health")

    id_from_first_request = r1.headers.get("x-request-id", "")
    assert id_from_first_request, "First response must have X-Request-ID."

    # ---- Second request ----
    with structlog.testing.capture_logs() as second_logs:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.get("/health")

    # The first request's ID must not bleed into the second request's log output.
    leaked_ids = [
        ev.get("request_id")
        for ev in second_logs
        if ev.get("request_id") == id_from_first_request
    ]
    assert not leaked_ids, (
        f"request_id '{id_from_first_request}' from the first request leaked "
        f"into the second request's log events. Middleware must clear contextvars."
    )
