"""GET /imports/{id}/phase-comparison integration tests — Phase C2.

These tests are intentionally RED. The GET /imports/{id}/phase-comparison
endpoint does not exist yet. Every request will return 404 or 405 (Method
Not Allowed) from the router until the endpoint is implemented. That is the
correct RED state.

Contract being tested:
  GET /imports/{id}/phase-comparison
    200  success: flat rows from phase_comparison_rows, 36 rows for sample fixture
    404  import not found (id never existed)
    404  import soft-deleted
    404  import exists but status is 'pending' (no file uploaded)
    422  malformed UUID in path

Response shape:
  {
    "import_id": "<uuid>",
    "rows": [
      {
        "id": "<uuid>",
        "import_id": "<uuid>",
        "line_item": "gross_revenue",
        "phase": "p1",
        "budget": null,
        "current": "60000.0000",
        "delta": null,
        "delta_pct": null
      },
      ...
    ]
  }

Sample fixture specifics (sample_import.xlsx):
  - 36 rows total: 6 line_items × 6 phases (p1, p2, p3, p4, p5, total)
  - Line items: gross_revenue, sales_costs, primary_build, marketing,
                infrastructure, professional_fees
  - budget=null (no budget import uploaded) → delta=null, delta_pct=null
  - current has values for non-zero rows

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
# GET /imports/{id}/phase-comparison — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_phase_comparison_returns_200():
    """GET /imports/{id}/phase-comparison must return HTTP 200 on a complete import."""
    name = "c2-test-phase-comparison-returns-200"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/phase-comparison")
        assert response.status_code == 200, (
            f"Expected 200 from GET /imports/{{id}}/phase-comparison, "
            f"got {response.status_code}: {response.text}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_phase_comparison_response_shape():
    """GET /imports/{id}/phase-comparison response must have 'import_id' and 'rows' keys."""
    name = "c2-test-phase-comparison-response-shape"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/phase-comparison")
        assert response.status_code == 200
        data = response.json()
        assert "import_id" in data, "'import_id' key missing from phase-comparison response"
        assert "rows" in data, "'rows' key missing from phase-comparison response"
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
async def test_get_phase_comparison_row_count():
    """GET /imports/{id}/phase-comparison must return exactly 6 grouped rows for the sample fixture.

    6 = one row per line_item, each with 6 phase entries (p1, p2, p3, p4, p5, total).
    """
    name = "c2-test-phase-comparison-row-count"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/phase-comparison")
        assert response.status_code == 200
        data = response.json()
        row_count = len(data["rows"])
        assert row_count == 6, (
            f"Expected exactly 6 grouped rows (one per line_item), got {row_count}"
        )
        for row in data["rows"]:
            assert len(row["entries"]) == 6, (
                f"Expected 6 phase entries for line_item={row.get('line_item')!r}, "
                f"got {len(row['entries'])}"
            )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_phase_comparison_row_fields_present():
    """Every grouped row must have 'line_item' and 'entries'.
    Every entry must have 'phase', 'budget', 'current', 'delta', 'delta_pct'."""
    name = "c2-test-phase-comparison-row-fields"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/phase-comparison")
        assert response.status_code == 200
        data = response.json()
        assert len(data["rows"]) > 0, "'rows' must not be empty"
        required_row_fields = {"line_item", "entries"}
        required_entry_fields = {"phase", "budget", "current", "delta", "delta_pct"}
        for row in data["rows"]:
            missing_row = required_row_fields - set(row.keys())
            assert not missing_row, (
                f"Row for line_item={row.get('line_item')!r} is missing fields: {missing_row}"
            )
            for entry in row["entries"]:
                missing_entry = required_entry_fields - set(entry.keys())
                assert not missing_entry, (
                    f"Entry for line_item={row.get('line_item')!r} "
                    f"phase={entry.get('phase')!r} is missing fields: {missing_entry}"
                )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_phase_comparison_phase_values_are_valid_enum_strings():
    """Every entry's 'phase' value must be a valid Phase enum string (p1–p5 or total)."""
    name = "c2-test-phase-comparison-phase-enum"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/phase-comparison")
        assert response.status_code == 200
        data = response.json()
        valid_phases = {p.value for p in Phase}
        for row in data["rows"]:
            for entry in row["entries"]:
                phase_val = entry.get("phase")
                assert phase_val in valid_phases, (
                    f"Phase value {phase_val!r} for line_item={row.get('line_item')!r} "
                    f"is not one of {valid_phases}"
                )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_phase_comparison_all_six_phases_present():
    """All six phase values (p1, p2, p3, p4, p5, total) must appear in each row's entries."""
    name = "c2-test-phase-comparison-all-phases"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/phase-comparison")
        assert response.status_code == 200
        data = response.json()
        expected_phases = {p.value for p in Phase}
        for row in data["rows"]:
            returned_phases = {entry["phase"] for entry in row["entries"]}
            assert returned_phases == expected_phases, (
                f"line_item={row['line_item']!r}: expected phases {expected_phases}, "
                f"got {returned_phases}"
            )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_phase_comparison_budget_null_for_sample_fixture():
    """All entry 'budget' values must be null — the sample fixture has no budget import."""
    name = "c2-test-phase-comparison-budget-null"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/phase-comparison")
        assert response.status_code == 200
        data = response.json()
        for row in data["rows"]:
            for entry in row["entries"]:
                assert entry["budget"] is None, (
                    f"Expected budget=null for line_item={row.get('line_item')!r} "
                    f"phase={entry.get('phase')!r}, got {entry['budget']!r}"
                )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_phase_comparison_delta_null_when_budget_null():
    """All 'delta' and 'delta_pct' entry values must be null when budget is null.

    PostgreSQL GENERATED ALWAYS AS columns compute NULL when budget is NULL.
    """
    name = "c2-test-phase-comparison-delta-null"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/phase-comparison")
        assert response.status_code == 200
        data = response.json()
        for row in data["rows"]:
            for entry in row["entries"]:
                assert entry["delta"] is None, (
                    f"Expected delta=null (budget is null) for "
                    f"line_item={row.get('line_item')!r} phase={entry.get('phase')!r}, "
                    f"got {entry['delta']!r}"
                )
                assert entry["delta_pct"] is None, (
                    f"Expected delta_pct=null (budget is null) for "
                    f"line_item={row.get('line_item')!r} phase={entry.get('phase')!r}, "
                    f"got {entry['delta_pct']!r}"
                )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_phase_comparison_current_not_null_for_gross_revenue():
    """The gross_revenue row must have non-null 'current' in all 6 phase entries.

    gross_revenue is the primary revenue line — the sample fixture has non-zero
    values for all phases.
    """
    name = "c2-test-phase-comparison-current-not-null"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/phase-comparison")
        assert response.status_code == 200
        data = response.json()
        gross_revenue_rows = [r for r in data["rows"] if r.get("line_item") == "gross_revenue"]
        assert len(gross_revenue_rows) == 1, (
            f"Expected exactly 1 gross_revenue grouped row, got {len(gross_revenue_rows)}"
        )
        for entry in gross_revenue_rows[0]["entries"]:
            assert entry["current"] is not None, (
                f"Expected non-null current for gross_revenue phase={entry.get('phase')!r}"
            )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_phase_comparison_no_internal_ids_exposed():
    """Grouped rows must not expose internal DB ids — 'id' and 'import_id' must be absent.

    The grouped shape has no individually-addressable rows, so internal DB UUIDs
    must not leak into the consumer contract.
    """
    name = "c2-test-phase-comparison-no-internal-ids"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/phase-comparison")
        assert response.status_code == 200
        data = response.json()
        for row in data["rows"]:
            assert "id" not in row, (
                f"'id' must not appear on grouped row line_item={row.get('line_item')!r}"
            )
            for entry in row["entries"]:
                assert "id" not in entry, (
                    f"'id' must not appear in entry for line_item={row.get('line_item')!r} "
                    f"phase={entry.get('phase')!r}"
                )
                assert "import_id" not in entry, (
                    f"'import_id' must not appear in entry for line_item={row.get('line_item')!r} "
                    f"phase={entry.get('phase')!r}"
                )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_get_phase_comparison_six_line_items_present():
    """The six expected line items must all appear in the response rows."""
    name = "c2-test-phase-comparison-line-items"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/phase-comparison")
        assert response.status_code == 200
        data = response.json()
        returned_line_items = {row["line_item"] for row in data["rows"]}
        expected_line_items = {
            "gross_revenue",
            "sales_costs",
            "primary_build",
            "marketing",
            "infrastructure",
            "professional_fees",
        }
        assert expected_line_items.issubset(returned_line_items), (
            f"Missing line items: {expected_line_items - returned_line_items}. "
            f"Got: {returned_line_items}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


# ---------------------------------------------------------------------------
# GET /imports/{id}/phase-comparison — error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_phase_comparison_404_nonexistent_import():
    """GET /imports/{id}/phase-comparison must return 404 when the import id has never existed."""
    nonexistent_id = uuid.uuid4()
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/imports/{nonexistent_id}/phase-comparison")
    assert response.status_code == 404, (
        f"Expected 404 for nonexistent import id, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_get_phase_comparison_404_soft_deleted_import():
    """GET /imports/{id}/phase-comparison must return 404 when the import is soft-deleted."""
    name = "c2-test-phase-comparison-404-soft-deleted"
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

        # Phase-comparison request on soft-deleted import must 404
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/phase-comparison")
        assert response.status_code == 404, (
            f"Expected 404 for soft-deleted import, got {response.status_code}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_get_phase_comparison_404_pending_import():
    """GET /imports/{id}/phase-comparison must return 404 when the import status is 'pending'.

    A pending import has no file uploaded and therefore no phase_comparison_rows data.
    The endpoint must not return an empty rows list — it must 404.
    """
    name = "c2-test-phase-comparison-404-pending"
    await _cleanup_by_name(name)
    # Create the import but do NOT upload a file — status remains 'pending'
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/imports/{import_id}/phase-comparison")
        assert response.status_code == 404, (
            f"Expected 404 for pending import (no data uploaded), "
            f"got {response.status_code}: {response.text}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_get_phase_comparison_422_malformed_uuid():
    """GET /imports/{id}/phase-comparison must return 422 when the id is not a valid UUID."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/imports/not-a-uuid/phase-comparison")
    assert response.status_code == 422, (
        f"Expected 422 for malformed UUID path param, got {response.status_code}"
    )
