"""PATCH /imports/{id}/n12m/{line_item}/{month} integration tests — Phase C4.

These tests are intentionally RED. The endpoint
`PATCH /imports/{id}/n12m/{line_item}/{month}` does not exist yet. Every
request targeting this path will return 404 or 405 from FastAPI's router
until the endpoint is implemented. That is the correct RED state.

Contract being tested:
  PATCH /imports/{import_id}/n12m/{line_item}/{month}
  Body: {"value": <Decimal-compatible number>}

  204  No Content — cell updated, cascade recalculated, derived tables updated
  404  import not found (never existed, soft-deleted, or not complete)
  404  line_item not found in this import's n12m data
  422  malformed UUID path parameter
  422  month path parameter is not an integer

Post-204 guarantees:
  - n12m_line_items.value is updated in the DB for that (import_id, line_item, month)
  - GET /imports/{id}/forecast returns the updated value for that line_item + month
  - GET /imports/{id}/pnl returns updated current for the affected P&L row
    (e.g. editing gross_revenue in month 10 must change the 'revenue' pnl_summary row)
  - Derived tables (per_delivery_rows, ncf_series, pnl_summaries) reflect the
    re-cascaded values

Sample fixture specifics (sample_import.xlsx):
  - gross_revenue is line_item "gross_revenue", section=revenue, sort_order=1
  - Month 10 (October) is present in the rolling 12-month window
  - The sample fixture has no budget (budget=null), so delta/delta_pct remain null
    after the edit — do not assert on delta values

Do not mock the DB session. These are real integration tests against the
Docker PostgreSQL instance. Each test that creates an import cleans up after
itself via try/finally.

This test must fail before we proceed. It is our way.

— Birdperson
"""

import uuid
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.domain.enums import ImportStatus, SourceType, VersionType
from app.domain.models import Import, N12mLineItem, NcfSeries
from app.main import app

# ---------------------------------------------------------------------------
# Fixture file path
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent / "fixtures"
XLSX_PATH = FIXTURES / "sample_import.xlsx"

# Month used in happy-path tests — must exist in the sample fixture's 12-month window
EDIT_MONTH = 10  # October — calendar integer 1–12

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
# PATCH /imports/{id}/n12m/{line_item}/{month} — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_n12m_returns_204():
    """PATCH /imports/{id}/n12m/gross_revenue/10 must return HTTP 204 No Content.

    204 signals a successful update with no response body — the canonical REST
    contract for a single-resource mutation.
    """
    name = "c4-de-test-patch-n12m-returns-204"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/n12m/gross_revenue/{EDIT_MONTH}",
                json={"value": "75000.0000"},
            )
        assert response.status_code == 204, (
            f"Expected 204 from PATCH /imports/{{id}}/n12m/gross_revenue/{EDIT_MONTH}, "
            f"got {response.status_code}: {response.text}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_n12m_updates_value_in_db():
    """After PATCH returns 204, the n12m_line_items row must have the new value in the DB.

    The write must be durable — a direct DB query must confirm the update, not
    just rely on the response status code.
    """
    name = "c4-de-test-patch-n12m-updates-db"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)
    new_value = Decimal("87654.3210")
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/n12m/gross_revenue/{EDIT_MONTH}",
                json={"value": str(new_value)},
            )
        assert response.status_code == 204, (
            f"Expected 204, got {response.status_code}: {response.text}"
        )

        # Verify the DB row was updated
        Session = _make_test_session()
        async with Session() as session:
            result = await session.execute(
                select(N12mLineItem).where(
                    N12mLineItem.import_id == import_uuid,
                    N12mLineItem.line_item == "gross_revenue",
                    N12mLineItem.month == EDIT_MONTH,
                )
            )
            db_row = result.scalar_one_or_none()

        assert db_row is not None, (
            f"n12m_line_items row not found for import_id={import_id}, "
            f"line_item='gross_revenue', month={EDIT_MONTH}"
        )
        # Compare rounded to 4dp (NUMERIC(18,4) precision in DB)
        assert db_row.value == new_value, (
            f"Expected n12m_line_items.value={new_value!r} after PATCH, "
            f"got {db_row.value!r}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_n12m_forecast_reflects_update():
    """After PATCH, GET /imports/{id}/forecast must return the updated value for that cell.

    This tests the read-your-writes contract: the cascade must flush updated
    n12m data before the request returns, so the forecast endpoint sees the
    new value immediately.
    """
    name = "c4-de-test-patch-n12m-forecast-update"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)
    new_value = "99999.0000"
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            patch_resp = await client.patch(
                f"/imports/{import_id}/n12m/gross_revenue/{EDIT_MONTH}",
                json={"value": new_value},
            )
        assert patch_resp.status_code == 204, (
            f"PATCH must return 204 before we can check forecast, "
            f"got {patch_resp.status_code}: {patch_resp.text}"
        )

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            forecast_resp = await client.get(f"/imports/{import_id}/forecast")
        assert forecast_resp.status_code == 200, (
            f"GET /imports/{{id}}/forecast returned {forecast_resp.status_code}"
        )

        data = forecast_resp.json()
        gross_revenue_rows = [r for r in data["rows"] if r["line_item"] == "gross_revenue"]
        assert len(gross_revenue_rows) == 1, (
            f"Expected exactly 1 gross_revenue row in forecast, "
            f"got {len(gross_revenue_rows)}"
        )
        month_entries = {e["month"]: e["value"] for e in gross_revenue_rows[0]["entries"]}
        assert EDIT_MONTH in month_entries, (
            f"Month {EDIT_MONTH} not found in gross_revenue forecast entries. "
            f"Entries present: {list(month_entries.keys())}"
        )
        # Compare as Decimal to avoid string formatting differences
        assert Decimal(str(month_entries[EDIT_MONTH])) == Decimal(new_value), (
            f"Forecast entry for gross_revenue month={EDIT_MONTH} is "
            f"{month_entries[EDIT_MONTH]!r}, expected {new_value!r}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_n12m_pnl_reflects_cascade():
    """After editing gross_revenue month 10, GET /imports/{id}/pnl must show updated revenue.

    gross_revenue feeds the P&L 'revenue' summary row. Editing a single
    n12m cell must trigger a full cascade recalc that propagates the new
    value into pnl_summaries.current for the 'revenue' line_item.
    """
    name = "c4-de-test-patch-n12m-pnl-cascade"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        # Get the current pnl revenue current value before edit
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            pre_pnl_resp = await client.get(f"/imports/{import_id}/pnl")
        assert pre_pnl_resp.status_code == 200, (
            f"Pre-edit GET /pnl returned {pre_pnl_resp.status_code}"
        )
        pre_data = pre_pnl_resp.json()
        pre_revenue_rows = [r for r in pre_data["rows"] if r["line_item"] == "revenue"]
        assert len(pre_revenue_rows) == 1, (
            f"Expected 1 'revenue' row in pnl before edit, got {len(pre_revenue_rows)}"
        )
        pre_revenue_current = Decimal(str(pre_revenue_rows[0]["current"])) if pre_revenue_rows[0]["current"] is not None else None

        # Edit gross_revenue month 10 with a value that will change the pnl total
        # Use a distinctly different value so the delta is unambiguous
        new_value = "999999.0000"
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            patch_resp = await client.patch(
                f"/imports/{import_id}/n12m/gross_revenue/{EDIT_MONTH}",
                json={"value": new_value},
            )
        assert patch_resp.status_code == 204, (
            f"PATCH must return 204, got {patch_resp.status_code}: {patch_resp.text}"
        )

        # Check pnl after edit — revenue current must differ from pre-edit value
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            post_pnl_resp = await client.get(f"/imports/{import_id}/pnl")
        assert post_pnl_resp.status_code == 200, (
            f"Post-edit GET /pnl returned {post_pnl_resp.status_code}"
        )
        post_data = post_pnl_resp.json()
        post_revenue_rows = [r for r in post_data["rows"] if r["line_item"] == "revenue"]
        assert len(post_revenue_rows) == 1, (
            f"Expected 1 'revenue' row in pnl after edit, got {len(post_revenue_rows)}"
        )
        post_revenue_current = Decimal(str(post_revenue_rows[0]["current"])) if post_revenue_rows[0]["current"] is not None else None

        assert post_revenue_current != pre_revenue_current, (
            f"P&L 'revenue' current must change after editing gross_revenue month {EDIT_MONTH}. "
            f"Before: {pre_revenue_current}, After: {post_revenue_current}. "
            "The cascade recalc is not propagating to pnl_summaries."
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_n12m_no_response_body():
    """PATCH /imports/{id}/n12m/.../... must return a 204 with an empty body.

    204 No Content is a contract: callers must not parse a JSON body from this
    response. If a body is accidentally included, clients may break silently.
    """
    name = "c4-de-test-patch-n12m-no-body"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/n12m/gross_revenue/{EDIT_MONTH}",
                json={"value": "50000.0000"},
            )
        assert response.status_code == 204, (
            f"Expected 204, got {response.status_code}: {response.text}"
        )
        assert response.content == b"", (
            f"Expected empty response body for 204, got {response.content!r}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_n12m_idempotent():
    """Patching the same cell with the same value twice must both return 204.

    The endpoint is idempotent — repeated identical writes are safe and must
    not raise errors or return a different status.
    """
    name = "c4-de-test-patch-n12m-idempotent"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)
    patch_value = "60000.0000"
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first_resp = await client.patch(
                f"/imports/{import_id}/n12m/gross_revenue/{EDIT_MONTH}",
                json={"value": patch_value},
            )
        assert first_resp.status_code == 204, (
            f"First PATCH: expected 204, got {first_resp.status_code}: {first_resp.text}"
        )

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            second_resp = await client.patch(
                f"/imports/{import_id}/n12m/gross_revenue/{EDIT_MONTH}",
                json={"value": patch_value},
            )
        assert second_resp.status_code == 204, (
            f"Second (identical) PATCH: expected 204, got {second_resp.status_code}: "
            f"{second_resp.text}. Endpoint must be idempotent."
        )
    finally:
        await _cleanup_by_id(import_uuid)


# ---------------------------------------------------------------------------
# PATCH /imports/{id}/n12m/{line_item}/{month} — error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_n12m_404_nonexistent_import():
    """PATCH /imports/{id}/n12m/.../... must return 404 when the import id has never existed."""
    nonexistent_id = uuid.uuid4()
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.patch(
            f"/imports/{nonexistent_id}/n12m/gross_revenue/{EDIT_MONTH}",
            json={"value": "50000.0000"},
        )
    assert response.status_code == 404, (
        f"Expected 404 for nonexistent import id, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_patch_n12m_404_soft_deleted_import():
    """PATCH /imports/{id}/n12m/.../... must return 404 when the import is soft-deleted."""
    name = "c4-de-test-patch-n12m-404-soft-deleted"
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

        # PATCH on soft-deleted import must 404
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/n12m/gross_revenue/{EDIT_MONTH}",
                json={"value": "50000.0000"},
            )
        assert response.status_code == 404, (
            f"Expected 404 for soft-deleted import, got {response.status_code}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_n12m_404_pending_import():
    """PATCH /imports/{id}/n12m/.../... must return 404 when the import status is 'pending'.

    A pending import has no n12m data. The endpoint must not attempt a DB
    write — it must 404 before reaching the update logic.
    """
    name = "c4-de-test-patch-n12m-404-pending"
    await _cleanup_by_name(name)
    # Create the import but do NOT upload a file — status remains 'pending'
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/n12m/gross_revenue/{EDIT_MONTH}",
                json={"value": "50000.0000"},
            )
        assert response.status_code == 404, (
            f"Expected 404 for pending import (no data uploaded), "
            f"got {response.status_code}: {response.text}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_n12m_404_unknown_line_item():
    """PATCH /imports/{id}/n12m/{line_item}/{month} must return 404 when line_item is unknown.

    If `line_item` does not exist in this import's n12m data, the endpoint
    must return 404 — not silently insert a new row or raise an unhandled error.
    """
    name = "c4-de-test-patch-n12m-404-unknown-line-item"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/n12m/does_not_exist/{EDIT_MONTH}",
                json={"value": "50000.0000"},
            )
        assert response.status_code == 404, (
            f"Expected 404 for unknown line_item 'does_not_exist', "
            f"got {response.status_code}: {response.text}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_n12m_422_malformed_uuid():
    """PATCH /imports/{id}/n12m/.../... must return 422 when the id is not a valid UUID.

    FastAPI must reject path parameter validation failures with 422 before
    the handler executes.
    """
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.patch(
            f"/imports/not-a-uuid/n12m/gross_revenue/{EDIT_MONTH}",
            json={"value": "50000.0000"},
        )
    assert response.status_code == 422, (
        f"Expected 422 for malformed UUID path param, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_patch_n12m_422_invalid_month_string():
    """PATCH /imports/{id}/n12m/.../abc must return 422 when month is not an integer.

    The `month` path parameter is declared as `int` in the endpoint signature.
    FastAPI must reject non-integer values with 422 before the handler executes.
    """
    nonexistent_id = uuid.uuid4()  # UUID is valid; month validation fires first or simultaneously
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.patch(
            f"/imports/{nonexistent_id}/n12m/gross_revenue/abc",
            json={"value": "50000.0000"},
        )
    assert response.status_code == 422, (
        f"Expected 422 for non-integer month path param 'abc', "
        f"got {response.status_code}: {response.text}"
    )


@pytest.mark.asyncio
async def test_patch_n12m_404_calculated_line_item():
    """PATCH on a calculated (is_calculated=True) line item must return 404.

    Calculated rows (net_revenue, net_cash_flow, etc.) are derived and must not
    be directly editable. The endpoint filters is_calculated=False on lookup.
    """
    name = "c4-de-test-404-calculated"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/n12m/net_cash_flow/{EDIT_MONTH}",
                json={"value": "99999.00"},
            )
        assert response.status_code == 404, (
            f"Expected 404 for calculated line item 'net_cash_flow', "
            f"got {response.status_code}: {response.text}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_patch_n12m_ncf_series_repersisted():
    """After PATCH, ncf_series rows must still exist for this import.

    The cascade re-run deletes and re-inserts ncf_series. This test verifies
    the re-insert completes correctly (rows not accidentally left empty).
    The exact count is fixture-specific; the invariant is that PATCH must not
    leave the table empty.
    """
    name = "c4-de-test-ncf-repersist"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        # Record how many ncf_series rows exist after initial upload
        Session = _make_test_session()
        async with Session() as session:
            from sqlalchemy import select as _select
            pre_result = await session.execute(
                _select(NcfSeries).where(NcfSeries.import_id == import_uuid)
            )
            pre_count = len(list(pre_result.scalars().all()))
        assert pre_count > 0, "Setup: no ncf_series rows after initial upload."

        # Perform a PATCH
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/imports/{import_id}/n12m/gross_revenue/{EDIT_MONTH}",
                json={"value": "75000.00"},
            )
        assert resp.status_code == 204

        # Verify ncf_series rows still exist with the same count
        async with Session() as session:
            from sqlalchemy import select as _select
            result = await session.execute(
                _select(NcfSeries).where(NcfSeries.import_id == import_uuid)
            )
            ncf_rows = list(result.scalars().all())
        assert len(ncf_rows) > 0, (
            f"Expected ncf_series rows to exist after PATCH, got 0"
        )
        assert len(ncf_rows) == pre_count, (
            f"Expected {pre_count} ncf_series rows after PATCH (same as before), "
            f"got {len(ncf_rows)}"
        )
    finally:
        await _cleanup_by_id(import_uuid)
