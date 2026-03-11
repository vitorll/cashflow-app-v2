"""GET /imports/{id}/forecast integration tests — Phase C1.

These tests are intentionally RED. The GET /imports/{id}/forecast endpoint
does not exist yet. Every request will return 404 or 405 (Method Not Allowed)
from the router until the endpoint is implemented. That is the correct RED
state.

Contract being tested:
  GET /imports/{id}/forecast
    200  success: grouped N12M rows, 22 rows × N months per import
    404  import not found (id never existed)
    404  import soft-deleted
    404  import exists but status is 'pending' (no file uploaded)
    422  malformed UUID in path

Response shape:
  {
    "import_id": "<uuid>",
    "rows": [
      {
        "section": "revenue",
        "line_item": "gross_revenue",
        "entries": [
          {"month": 10, "value": "60000.0000"},
          ...
        ]
      }
    ]
  }

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
from app.domain.enums import ImportStatus, SourceType, VersionType
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
# GET /imports/{id}/forecast — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_forecast_returns_200():
    """GET /imports/{id}/forecast must return HTTP 200 on a complete import."""
    name = "c1-test-forecast-returns-200"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/forecast")
        assert response.status_code == 200, (
            f"Expected 200 from GET /imports/{{id}}/forecast, "
            f"got {response.status_code}: {response.text}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_forecast_response_shape():
    """GET /imports/{id}/forecast response must have 'import_id' and 'rows' keys."""
    name = "c1-test-forecast-response-shape"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/forecast")
        assert response.status_code == 200
        data = response.json()
        assert "import_id" in data, "'import_id' key missing from forecast response"
        assert "rows" in data, "'rows' key missing from forecast response"
        assert isinstance(data["import_id"], str), (
            f"'import_id' must be a string (UUID), got {type(data['import_id'])}"
        )
        assert isinstance(data["rows"], list), (
            f"'rows' must be a list, got {type(data['rows'])}"
        )
        # import_id in response must match the requested import
        assert data["import_id"] == import_id, (
            f"Response import_id '{data['import_id']}' does not match "
            f"requested import '{import_id}'"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_forecast_rows_are_grouped():
    """Each row in the forecast response must have 'section', 'line_item', and 'entries'."""
    name = "c1-test-forecast-rows-grouped"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/forecast")
        assert response.status_code == 200
        data = response.json()
        assert len(data["rows"]) > 0, "Forecast 'rows' must not be empty"
        first_row = data["rows"][0]
        assert "section" in first_row, "'section' key missing from forecast row"
        assert "line_item" in first_row, "'line_item' key missing from forecast row"
        assert "entries" in first_row, "'entries' key missing from forecast row"
        assert isinstance(first_row["entries"], list), (
            f"'entries' must be a list, got {type(first_row['entries'])}"
        )
        assert len(first_row["entries"]) > 0, "'entries' list must not be empty"
        first_entry = first_row["entries"][0]
        assert "month" in first_entry, "'month' key missing from forecast entry"
        assert "value" in first_entry, "'value' key missing from forecast entry"
        # section must be one of the known section values
        valid_sections = {"revenue", "direct_costs", "overheads", "capex", "contingency"}
        assert first_row["section"] in valid_sections, (
            f"'section' value '{first_row['section']}' is not one of {valid_sections}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_forecast_row_count():
    """GET /imports/{id}/forecast must return exactly 22 rows for the sample fixture.

    22 = 16 input line items + 6 calculated line items.
    The sample fixture has 3 months in the rolling window.
    """
    name = "c1-test-forecast-row-count"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/forecast")
        assert response.status_code == 200
        data = response.json()
        row_count = len(data["rows"])
        assert row_count == 22, (
            f"Expected exactly 22 forecast rows (16 input + 6 calculated), got {row_count}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_forecast_entries_are_integers():
    """'month' values in forecast entries must be integers (not strings).

    The sample fixture has 3 months, so every row must have 3 entries with
    integer month values in range 1–12.
    """
    name = "c1-test-forecast-entries-integers"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/forecast")
        assert response.status_code == 200
        data = response.json()
        for row in data["rows"]:
            section = row["section"]
            line_item = row["line_item"]
            assert len(row["entries"]) == 3, (
                f"Expected 3 entries (Oct/Nov/Dec) for {section}/{line_item}, "
                f"got {len(row['entries'])}"
            )
            for entry in row["entries"]:
                month = entry["month"]
                assert isinstance(month, int), (
                    f"Expected integer month in {section}/{line_item}, "
                    f"got {type(month).__name__}: {month!r}"
                )
                assert 1 <= month <= 12, (
                    f"Month {month} in {section}/{line_item} is out of range 1–12"
                )
                value = entry["value"]
                assert isinstance(value, str), (
                    f"Expected string value in {section}/{line_item} month {month}, "
                    f"got {type(value).__name__}: {value!r}"
                )
                assert "." in value and len(value.split(".")[1]) == 4, (
                    f"Expected 4dp string value in {section}/{line_item} month {month}, "
                    f"got {value!r}"
                )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


# ---------------------------------------------------------------------------
# GET /imports/{id}/forecast — error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_forecast_404_nonexistent_import():
    """GET /imports/{id}/forecast must return 404 when the import id has never existed."""
    nonexistent_id = uuid.uuid4()
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/imports/{nonexistent_id}/forecast")
    assert response.status_code == 404, (
        f"Expected 404 for nonexistent import id, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_get_forecast_404_soft_deleted_import():
    """GET /imports/{id}/forecast must return 404 when the import is soft-deleted."""
    name = "c1-test-forecast-404-soft-deleted"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        # Soft-delete the import via the DELETE endpoint
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            delete_resp = await client.delete(f"/imports/{import_id}")
        assert delete_resp.status_code == 204, (
            f"Setup: soft-delete must return 204, got {delete_resp.status_code}"
        )

        # Forecast request on a soft-deleted import must 404
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/forecast")
        assert response.status_code == 404, (
            f"Expected 404 for soft-deleted import, got {response.status_code}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_get_forecast_404_pending_import():
    """GET /imports/{id}/forecast must return 404 when the import status is 'pending'.

    A pending import has no file uploaded and therefore no n12m_line_items data.
    The endpoint must not return an empty rows list — it must 404.
    """
    name = "c1-test-forecast-404-pending"
    await _cleanup_by_name(name)
    # Create the import but do NOT upload a file — status remains 'pending'
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/forecast")
        assert response.status_code == 404, (
            f"Expected 404 for pending import (no data uploaded), "
            f"got {response.status_code}: {response.text}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_get_forecast_422_malformed_uuid():
    """GET /imports/{id}/forecast must return 422 when the id is not a valid UUID."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/imports/not-a-uuid/forecast")
    assert response.status_code == 422, (
        f"Expected 422 for malformed UUID path param, got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# C1 extension — new n12m fields: display_name, is_calculated, sort_order,
# is_actual.  These tests are intentionally RED.  The DB columns and schema
# fields do not exist yet.
# — Birdperson
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_forecast_rows_have_display_name():
    """Every row must carry a non-empty 'display_name' string.

    RED: 'display_name' is not yet in ForecastRow schema or DB columns.
    """
    name = "c1-ext-display-name"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/forecast")
        assert response.status_code == 200
        data = response.json()
        for row in data["rows"]:
            assert "display_name" in row, (
                f"'display_name' key missing from row {row.get('line_item')!r}"
            )
            assert isinstance(row["display_name"], str), (
                f"'display_name' must be a string for row {row.get('line_item')!r}, "
                f"got {type(row['display_name'])}"
            )
            assert row["display_name"] != "", (
                f"'display_name' must not be empty for row {row.get('line_item')!r}"
            )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_forecast_rows_have_is_calculated():
    """Every row must carry a boolean 'is_calculated' field; exactly 6 rows are True.

    RED: 'is_calculated' is not yet in ForecastRow schema or DB columns.
    """
    name = "c1-ext-is-calculated"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/forecast")
        assert response.status_code == 200
        data = response.json()
        for row in data["rows"]:
            assert "is_calculated" in row, (
                f"'is_calculated' key missing from row {row.get('line_item')!r}"
            )
            assert isinstance(row["is_calculated"], bool), (
                f"'is_calculated' must be a bool for row {row.get('line_item')!r}, "
                f"got {type(row['is_calculated'])}"
            )
        calculated_rows = [r for r in data["rows"] if r["is_calculated"] is True]
        assert len(calculated_rows) == 6, (
            f"Expected exactly 6 rows with is_calculated=true, "
            f"got {len(calculated_rows)}: "
            f"{[r.get('line_item') for r in calculated_rows]}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_forecast_rows_have_sort_order():
    """Every row must carry an integer 'sort_order'; sorting by it produces ascending order.

    RED: 'sort_order' is not yet in ForecastRow schema or DB columns.
    """
    name = "c1-ext-sort-order"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/forecast")
        assert response.status_code == 200
        data = response.json()
        for row in data["rows"]:
            assert "sort_order" in row, (
                f"'sort_order' key missing from row {row.get('line_item')!r}"
            )
            assert isinstance(row["sort_order"], int), (
                f"'sort_order' must be an integer for row {row.get('line_item')!r}, "
                f"got {type(row['sort_order'])}"
            )
        sort_orders = [r["sort_order"] for r in data["rows"]]
        assert sort_orders == sorted(sort_orders), (
            f"Rows are not ordered by sort_order ascending. "
            f"sort_order values: {sort_orders}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_forecast_entries_have_is_actual():
    """Every entry must carry a boolean 'is_actual' field.

    For the sample fixture actual_flags marks all 3 months as actual,
    so every entry must have is_actual=True.

    RED: 'is_actual' is not yet in ForecastEntry schema or DB columns.
    """
    name = "c1-ext-is-actual"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/forecast")
        assert response.status_code == 200
        data = response.json()
        for row in data["rows"]:
            section = row["section"]
            line_item = row["line_item"]
            for entry in row["entries"]:
                assert "is_actual" in entry, (
                    f"'is_actual' key missing from entry month={entry.get('month')} "
                    f"in {section}/{line_item}"
                )
                assert isinstance(entry["is_actual"], bool), (
                    f"'is_actual' must be a bool in {section}/{line_item} "
                    f"month={entry.get('month')}, got {type(entry['is_actual'])}"
                )
                # The sample fixture has actual_flags="true,true,true"
                assert entry["is_actual"] is True, (
                    f"Expected is_actual=True for all entries in sample fixture "
                    f"({section}/{line_item} month={entry.get('month')}), "
                    f"got {entry['is_actual']!r}"
                )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_forecast_display_name_for_gross_revenue():
    """The gross_revenue row must have display_name == 'Gross Revenue'.

    RED: 'display_name' is not yet in ForecastRow schema or DB columns.
    """
    name = "c1-ext-display-name-gross-revenue"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/forecast")
        assert response.status_code == 200
        data = response.json()
        gross_revenue_rows = [
            r for r in data["rows"] if r.get("line_item") == "gross_revenue"
        ]
        assert len(gross_revenue_rows) == 1, (
            f"Expected exactly one gross_revenue row, "
            f"got {len(gross_revenue_rows)}"
        )
        row = gross_revenue_rows[0]
        assert "display_name" in row, (
            "'display_name' key missing from gross_revenue row"
        )
        assert row["display_name"] == "Gross Revenue", (
            f"Expected display_name='Gross Revenue' for gross_revenue row, "
            f"got {row['display_name']!r}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_forecast_sort_order_is_unique():
    """All 22 sort_order values across forecast rows must be distinct.

    RED: 'sort_order' is not yet in ForecastRow schema or DB columns.
    """
    name = "c1-ext-sort-order-unique"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/forecast")
        assert response.status_code == 200
        data = response.json()
        sort_orders = [r["sort_order"] for r in data["rows"]]
        assert len(sort_orders) == 22, (
            f"Expected 22 rows, got {len(sort_orders)}"
        )
        assert len(set(sort_orders)) == len(sort_orders), (
            f"sort_order values are not unique. "
            f"Duplicates: "
            f"{[v for v in sort_orders if sort_orders.count(v) > 1]}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))
