"""GET /imports/{id}/pnl integration tests — Phase C3.

These tests are intentionally RED. The GET /imports/{id}/pnl endpoint does not
exist yet. Every request will return 404 or 405 (Method Not Allowed) from the
router until the endpoint is implemented. That is the correct RED state.

Contract being tested:
  GET /imports/{id}/pnl
    200  success: flat rows from pnl_summaries, 7 rows for sample fixture
    404  import not found (id never existed)
    404  import soft-deleted
    404  import exists but status is 'pending' (no file uploaded)
    422  malformed UUID in path

Response shape (flat — no phases, no grouping):
  {
    "import_id": "<uuid>",
    "rows": [
      {
        "line_item": "deliveries",
        "budget": null,
        "current": "9.0000",
        "delta": null
      },
      ...
    ]
  }

Sample fixture specifics (sample_import.xlsx):
  - 7 rows total: one per line_item
  - Line items: deliveries, revenue, cogs, gross_profit,
                sales_and_marketing, direct_costs, net_profit
  - budget=null (no budget import uploaded) → delta=null
  - current has non-null values for all rows
  - No delta_pct column in pnl_summaries
  - No rate fields (current_rate, budget_rate) stored in DB

Do not mock the DB session. These are real integration tests against the
Docker PostgreSQL instance. Each test that creates an import cleans up after
itself via try/finally.

This test must fail before we proceed. It is our way.

— Birdperson
"""

import uuid
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.domain.enums import ImportStatus, Phase, SourceType, VersionType
from app.domain.models import Import
from app.main import app

# ---------------------------------------------------------------------------
# Fixture file path
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent / "fixtures"
XLSX_PATH = FIXTURES / "sample_import.xlsx"

# ---------------------------------------------------------------------------
# Test DB helpers — NullPool to avoid cross-loop connection reuse
# ---------------------------------------------------------------------------


def _make_test_session() -> async_sessionmaker[AsyncSession]:
    """Create a fresh async_sessionmaker with NullPool for test helpers."""
    test_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        echo=False,
        future=True,
    )
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def _cleanup_by_id(import_id: uuid.UUID) -> None:
    """Hard-delete an Import row (cascades to child rows via FK ON DELETE CASCADE)."""
    Session = _make_test_session()
    async with Session() as session:
        await session.execute(delete(Import).where(Import.id == import_id))
        await session.commit()


async def _cleanup_by_name(name: str) -> None:
    """Hard-delete all Import rows with the given name."""
    Session = _make_test_session()
    async with Session() as session:
        await session.execute(delete(Import).where(Import.name == name))
        await session.commit()


async def _create_import(name: str) -> str:
    """POST /imports and return the created import id as a string."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/imports",
            json={
                "name": name,
                "version_type": VersionType.current.value,
                "source_type": SourceType.excel.value,
            },
        )
    assert resp.status_code == 201, f"Setup failed: {resp.text}"
    return resp.json()["id"]


def _xlsx_upload_files():
    """Return an httpx-compatible files dict for the sample xlsx."""
    return {
        "file": (
            "sample_import.xlsx",
            XLSX_PATH.read_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


async def _create_complete_import(name: str) -> str:
    """Create an import and upload the sample xlsx, returning the import id."""
    import_id = await _create_import(name)
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.patch(
            f"/imports/{import_id}/file",
            files=_xlsx_upload_files(),
        )
    assert resp.status_code == 200, (
        f"Setup: file upload must succeed, got {resp.status_code}: {resp.text}"
    )
    return import_id


# ---------------------------------------------------------------------------
# GET /imports/{id}/pnl — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_pnl_returns_200():
    """GET /imports/{id}/pnl must return HTTP 200 on a complete import."""
    name = "c3-test-pnl-returns-200"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/pnl")
        assert response.status_code == 200, (
            f"Expected 200 from GET /imports/{{id}}/pnl, "
            f"got {response.status_code}: {response.text}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_pnl_response_shape():
    """GET /imports/{id}/pnl response must have 'import_id' and 'rows' keys; import_id matches."""
    name = "c3-test-pnl-response-shape"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/pnl")
        assert response.status_code == 200
        data = response.json()
        assert "import_id" in data, "'import_id' key missing from pnl response"
        assert "rows" in data, "'rows' key missing from pnl response"
        assert isinstance(data["import_id"], str), (
            f"'import_id' must be a string (UUID), got {type(data['import_id'])}"
        )
        assert isinstance(data["rows"], list), (
            f"'rows' must be a list, got {type(data['rows'])}"
        )
        assert data["import_id"] == import_id, (
            f"Response import_id '{data['import_id']}' does not match "
            f"requested import '{import_id}'"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_pnl_row_count():
    """GET /imports/{id}/pnl must return exactly 7 rows for the sample fixture.

    7 = one flat row per P&L line_item (deliveries, revenue, cogs,
    gross_profit, sales_and_marketing, direct_costs, net_profit).
    """
    name = "c3-test-pnl-row-count"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/pnl")
        assert response.status_code == 200
        data = response.json()
        row_count = len(data["rows"])
        assert row_count == 7, (
            f"Expected exactly 7 rows (one per P&L line_item), got {row_count}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_pnl_row_fields_present():
    """Every row must have 'line_item', 'budget', 'current', and 'delta' fields."""
    name = "c3-test-pnl-row-fields"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/pnl")
        assert response.status_code == 200
        data = response.json()
        assert len(data["rows"]) > 0, "'rows' must not be empty"
        required_fields = {"line_item", "budget", "current", "delta"}
        for row in data["rows"]:
            missing = required_fields - set(row.keys())
            assert not missing, (
                f"Row for line_item={row.get('line_item')!r} is missing fields: {missing}"
            )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_pnl_budget_null_for_sample_fixture():
    """All 'budget' values must be null — the sample fixture has no budget import."""
    name = "c3-test-pnl-budget-null"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/pnl")
        assert response.status_code == 200
        data = response.json()
        for row in data["rows"]:
            assert row["budget"] is None, (
                f"Expected budget=null for line_item={row.get('line_item')!r}, "
                f"got {row['budget']!r}"
            )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_pnl_delta_null_when_budget_null():
    """All 'delta' values must be null when budget is null.

    PostgreSQL GENERATED ALWAYS AS column computes NULL when budget is NULL.
    """
    name = "c3-test-pnl-delta-null"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/pnl")
        assert response.status_code == 200
        data = response.json()
        for row in data["rows"]:
            assert row["delta"] is None, (
                f"Expected delta=null (budget is null) for "
                f"line_item={row.get('line_item')!r}, got {row['delta']!r}"
            )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_pnl_current_not_null_for_revenue():
    """The 'revenue' row must have a non-null 'current' value.

    revenue is the primary income line — the sample fixture always has a
    non-zero current value for this line item.
    """
    name = "c3-test-pnl-current-not-null"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/pnl")
        assert response.status_code == 200
        data = response.json()
        revenue_rows = [r for r in data["rows"] if r.get("line_item") == "revenue"]
        assert len(revenue_rows) == 1, (
            f"Expected exactly 1 revenue row, got {len(revenue_rows)}"
        )
        assert revenue_rows[0]["current"] is not None, (
            "Expected non-null current for 'revenue' row"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_pnl_no_internal_ids_exposed():
    """Individual rows must NOT expose internal DB ids ('id' and 'import_id' absent from rows).

    The flat P&L shape has no individually-addressable rows, so internal DB
    UUIDs must not leak into the consumer contract.
    """
    name = "c3-test-pnl-no-internal-ids"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/pnl")
        assert response.status_code == 200
        data = response.json()
        for row in data["rows"]:
            assert "id" not in row, (
                f"'id' must not appear on row line_item={row.get('line_item')!r}"
            )
            assert "import_id" not in row, (
                f"'import_id' must not appear on row line_item={row.get('line_item')!r}"
            )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_pnl_all_seven_line_items_present():
    """All seven expected P&L line items must appear in the response rows."""
    name = "c3-test-pnl-all-line-items"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/pnl")
        assert response.status_code == 200
        data = response.json()
        returned_line_items = {row["line_item"] for row in data["rows"]}
        expected_line_items = {
            "deliveries",
            "revenue",
            "cogs",
            "gross_profit",
            "sales_and_marketing",
            "direct_costs",
            "net_profit",
        }
        assert expected_line_items.issubset(returned_line_items), (
            f"Missing line items: {expected_line_items - returned_line_items}. "
            f"Got: {returned_line_items}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_pnl_no_delta_pct_field():
    """'delta_pct' must NOT appear in any row — pnl_summaries has no such column."""
    name = "c3-test-pnl-no-delta-pct"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/pnl")
        assert response.status_code == 200
        data = response.json()
        for row in data["rows"]:
            assert "delta_pct" not in row, (
                f"'delta_pct' must not appear on row line_item={row.get('line_item')!r} "
                f"(no such column in pnl_summaries)"
            )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_pnl_rows_in_canonical_order():
    """Rows must be returned in canonical P&L order: deliveries, revenue, cogs,
    gross_profit, sales_and_marketing, direct_costs, net_profit."""
    name = "c3-test-pnl-canonical-order"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/pnl")
        assert response.status_code == 200
        data = response.json()
        returned_order = [row["line_item"] for row in data["rows"]]
        expected_order = [
            "deliveries",
            "revenue",
            "cogs",
            "gross_profit",
            "sales_and_marketing",
            "direct_costs",
            "net_profit",
        ]
        assert returned_order == expected_order, (
            f"Expected canonical P&L order {expected_order}, got {returned_order}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_pnl_no_rate_fields_exposed():
    """'current_rate' and 'budget_rate' must NOT appear in any row.

    Rate fields are not stored in the pnl_summaries table. They would need to
    be recomputed from totals / delivery_counts at the API layer — that is
    deferred to a future phase.
    """
    name = "c3-test-pnl-no-rate-fields"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/pnl")
        assert response.status_code == 200
        data = response.json()
        for row in data["rows"]:
            assert "current_rate" not in row, (
                f"'current_rate' must not appear on row "
                f"line_item={row.get('line_item')!r} (rate fields not stored)"
            )
            assert "budget_rate" not in row, (
                f"'budget_rate' must not appear on row "
                f"line_item={row.get('line_item')!r} (rate fields not stored)"
            )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


# ---------------------------------------------------------------------------
# GET /imports/{id}/pnl — error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_pnl_404_nonexistent_import():
    """GET /imports/{id}/pnl must return 404 when the import id has never existed."""
    nonexistent_id = uuid.uuid4()
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/imports/{nonexistent_id}/pnl")
    assert response.status_code == 404, (
        f"Expected 404 for nonexistent import id, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_get_pnl_404_soft_deleted_import():
    """GET /imports/{id}/pnl must return 404 when the import is soft-deleted."""
    name = "c3-test-pnl-404-soft-deleted"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        # Soft-delete via DELETE endpoint
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            delete_resp = await client.delete(f"/imports/{import_id}")
        assert delete_resp.status_code == 204, (
            f"Setup: soft-delete must return 204, got {delete_resp.status_code}"
        )

        # P&L request on soft-deleted import must 404
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/pnl")
        assert response.status_code == 404, (
            f"Expected 404 for soft-deleted import, got {response.status_code}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_get_pnl_404_pending_import():
    """GET /imports/{id}/pnl must return 404 when the import status is 'pending'.

    A pending import has no file uploaded and therefore no pnl_summaries rows.
    The endpoint must not return an empty rows list — it must 404.
    """
    name = "c3-test-pnl-404-pending"
    await _cleanup_by_name(name)
    # Create the import but do NOT upload a file — status remains 'pending'
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/pnl")
        assert response.status_code == 404, (
            f"Expected 404 for pending import (no data uploaded), "
            f"got {response.status_code}: {response.text}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_get_pnl_422_malformed_uuid():
    """GET /imports/{id}/pnl must return 422 when the id is not a valid UUID."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/imports/not-a-uuid/pnl")
    assert response.status_code == 422, (
        f"Expected 422 for malformed UUID path param, got {response.status_code}"
    )
