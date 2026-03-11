"""PATCH /imports/{id}/file integration tests — Phase B5.

These tests are intentionally RED. The PATCH /imports/{id}/file endpoint does
not exist yet. Every request will return 405 Method Not Allowed (or 404 from
the router) until the endpoint is implemented. That is the correct RED state.

Contract being tested:
  PATCH /imports/{id}/file  — multipart UploadFile (xlsx)
    200  success: parse + cascade + persist → status=complete, ImportResponse
    404  import not found (id never existed)
    404  import already soft-deleted
    409  import already complete (idempotency guard)
    422  uploaded file is not a valid xlsx (bad zip / not an xlsx)

Do not mock the DB session or the parser. These are real integration tests
against the Docker PostgreSQL instance. Each test cleans up its own records.

This test must fail before we proceed. It is our way.

— Birdperson
"""

import io
import uuid

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.domain.enums import ImportStatus, SourceType, VersionType
from app.domain.models import (
    Import,
    N12mLineItem,
    NcfSeries,
    PerDeliveryRow,
    PhaseComparisonRow,
    PnlSummary,
)
from app.main import app

# ---------------------------------------------------------------------------
# Fixture file path
# ---------------------------------------------------------------------------

from pathlib import Path

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


async def _fetch_import_by_id(import_id: uuid.UUID) -> Import | None:
    """Fetch a single Import row from the DB, including soft-deleted rows."""
    Session = _make_test_session()
    async with Session() as session:
        result = await session.execute(select(Import).where(Import.id == import_id))
        return result.scalar_one_or_none()


async def _count_rows(model, import_id: uuid.UUID) -> int:
    """Count rows for a given ORM model filtered by import_id."""
    Session = _make_test_session()
    async with Session() as session:
        result = await session.execute(
            select(func.count()).select_from(model).where(model.import_id == import_id)
        )
        return result.scalar_one()


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


# ---------------------------------------------------------------------------
# Helper: build multipart upload with the sample xlsx
# ---------------------------------------------------------------------------


def _xlsx_upload_files():
    """Return an httpx-compatible files dict for the sample xlsx."""
    return {
        "file": (
            "sample_import.xlsx",
            XLSX_PATH.read_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def _bad_file_upload_files():
    """Return an httpx-compatible files dict with a non-xlsx payload."""
    return {
        "file": (
            "not_an_xlsx.xlsx",
            b"this is not a zip file at all",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


# ---------------------------------------------------------------------------
# PATCH /imports/{id}/file — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_import_file_returns_200():
    """PATCH /imports/{id}/file must return HTTP 200 on a valid xlsx upload."""
    name = "b5-test-patch-returns-200"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert response.status_code == 200, (
            f"Expected 200 from PATCH /imports/{{id}}/file, got {response.status_code}: {response.text}"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_patch_import_file_returns_import_response_shape():
    """PATCH /imports/{id}/file response body must match ImportResponse schema."""
    name = "b5-test-patch-response-shape"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert response.status_code == 200
        data = response.json()
        for field in ("id", "name", "version_type", "source_type", "status", "created_at", "updated_at"):
            assert field in data, f"Field '{field}' missing from PATCH response"
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_patch_import_file_sets_status_to_complete():
    """PATCH /imports/{id}/file must update import status to 'complete'."""
    name = "b5-test-patch-status-complete"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ImportStatus.complete.value, (
            f"Expected status='complete', got '{data['status']}'"
        )
    finally:
        await _cleanup_by_id(uuid.UUID(import_id))


@pytest.mark.asyncio
async def test_patch_import_file_persists_status_complete_to_db():
    """PATCH /imports/{id}/file must persist status=complete to the DB."""
    name = "b5-test-patch-db-status"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert response.status_code == 200
        row = await _fetch_import_by_id(import_uuid)
        assert row is not None
        assert row.status == ImportStatus.complete, (
            f"Expected DB status=complete, got {row.status}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_import_file_persists_phase_comparison_rows():
    """PATCH /imports/{id}/file must insert rows into phase_comparison_rows."""
    name = "b5-test-patch-phase-comparison-rows"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert response.status_code == 200
        count = await _count_rows(PhaseComparisonRow, import_uuid)
        assert count > 0, (
            f"Expected non-zero phase_comparison_rows after file upload, got {count}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_import_file_persists_per_delivery_rows():
    """PATCH /imports/{id}/file must insert rows into per_delivery_rows."""
    name = "b5-test-patch-per-delivery-rows"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert response.status_code == 200
        count = await _count_rows(PerDeliveryRow, import_uuid)
        assert count > 0, (
            f"Expected non-zero per_delivery_rows after file upload, got {count}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_import_file_persists_n12m_line_items():
    """PATCH /imports/{id}/file must insert rows into n12m_line_items.

    Expected count: 22 rows (16 input + 6 computed) × 3 months = 66.
    """
    name = "b5-test-patch-n12m-line-items"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert response.status_code == 200
        count = await _count_rows(N12mLineItem, import_uuid)
        assert count == 66, (
            f"Expected 66 n12m_line_items (22 rows × 3 months), got {count}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_import_file_persists_ncf_series():
    """PATCH /imports/{id}/file must insert rows into ncf_series."""
    name = "b5-test-patch-ncf-series"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert response.status_code == 200
        count = await _count_rows(NcfSeries, import_uuid)
        assert count > 0, (
            f"Expected non-zero ncf_series after file upload, got {count}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_import_file_persists_pnl_summaries():
    """PATCH /imports/{id}/file must insert rows into pnl_summaries.

    Expected count: 7 (deliveries, revenue, cogs, gross_profit,
    sales_and_marketing, direct_costs, net_profit).
    """
    name = "b5-test-patch-pnl-summaries"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert response.status_code == 200
        count = await _count_rows(PnlSummary, import_uuid)
        assert count == 7, (
            f"Expected 7 pnl_summaries rows, got {count}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_import_file_phase_comparison_row_count_matches_golden():
    """phase_comparison_rows count must match the golden file (36 rows: 6 line items × 6 phases)."""
    name = "b5-test-patch-phase-comparison-count"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert response.status_code == 200
        count = await _count_rows(PhaseComparisonRow, import_uuid)
        # Golden file has 36 rows: 6 line_items × 6 phases (p1–p5 + total)
        assert count == 36, (
            f"Expected 36 phase_comparison_rows (6 line_items × 6 phases), got {count}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_import_file_per_delivery_row_count_matches_golden():
    """per_delivery_rows count must match the golden file (6 rows: 1 line item × 6 phases)."""
    name = "b5-test-patch-per-delivery-count"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert response.status_code == 200
        count = await _count_rows(PerDeliveryRow, import_uuid)
        # Golden file: gross_revenue × 6 phases (p1–p5 + total)
        assert count == 6, (
            f"Expected 6 per_delivery_rows (gross_revenue × 6 phases), got {count}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_import_file_ncf_series_count_matches_golden():
    """ncf_series count must match the golden file (6 rows: 3 periodic + 3 cumulative)."""
    name = "b5-test-patch-ncf-count"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert response.status_code == 200
        count = await _count_rows(NcfSeries, import_uuid)
        # Golden file: 3 periodic + 3 cumulative = 6
        assert count == 6, (
            f"Expected 6 ncf_series rows (3 periodic + 3 cumulative), got {count}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


# ---------------------------------------------------------------------------
# PATCH /imports/{id}/file — error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_import_file_returns_404_for_nonexistent_id():
    """PATCH /imports/{id}/file must return 404 when the import id does not exist."""
    nonexistent_id = uuid.uuid4()
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.patch(
            f"/imports/{nonexistent_id}/file",
            files=_xlsx_upload_files(),
        )
    assert response.status_code == 404, (
        f"Expected 404 for nonexistent import id, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_patch_import_file_returns_404_for_soft_deleted_import():
    """PATCH /imports/{id}/file must return 404 when the import is soft-deleted."""
    name = "b5-test-patch-404-soft-deleted"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        # Soft-delete the import
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            delete_resp = await client.delete(f"/imports/{import_id}")
        assert delete_resp.status_code == 204

        # Now attempt file upload — must 404
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert response.status_code == 404, (
            f"Expected 404 for soft-deleted import, got {response.status_code}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_import_file_returns_422_for_invalid_xlsx():
    """PATCH /imports/{id}/file must return 422 when the uploaded file is not a valid xlsx."""
    name = "b5-test-patch-422-invalid-file"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/imports/{import_id}/file",
                files=_bad_file_upload_files(),
            )
        assert response.status_code == 422, (
            f"Expected 422 for invalid xlsx payload, got {response.status_code}: {response.text}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_import_file_returns_409_when_already_complete():
    """PATCH /imports/{id}/file must return 409 when import is already complete (idempotency guard)."""
    name = "b5-test-patch-409-already-complete"
    await _cleanup_by_name(name)
    import_id = await _create_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        # First upload — must succeed
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first_resp = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert first_resp.status_code == 200, (
            f"Setup: first upload must succeed, got {first_resp.status_code}: {first_resp.text}"
        )

        # Second upload — must 409
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            second_resp = await client.patch(
                f"/imports/{import_id}/file",
                files=_xlsx_upload_files(),
            )
        assert second_resp.status_code == 409, (
            f"Expected 409 on second upload to already-complete import, got {second_resp.status_code}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_patch_import_file_returns_422_for_malformed_uuid():
    """PATCH /imports/{id}/file must return 422 when the id is not a valid UUID."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.patch(
            "/imports/not-a-uuid/file",
            files=_xlsx_upload_files(),
        )
    assert response.status_code == 422, (
        f"Expected 422 for malformed UUID path param, got {response.status_code}"
    )
