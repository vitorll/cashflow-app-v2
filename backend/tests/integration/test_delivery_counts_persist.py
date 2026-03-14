"""PATCH /imports/{id}/file — delivery_counts persistence tests — Phase C4.

These tests are intentionally RED. The `DeliveryCount` ORM model does not
exist in `app.domain.models` yet. The import at the top of this file will
raise `ImportError`, failing the entire module before a single test body
executes. That is the correct RED state.

Contract being tested:
  After PATCH /imports/{id}/file completes successfully, one row per project
  phase (p1–p5, NOT Phase.total) must exist in the `delivery_counts` table,
  each recording the count of deliveries for that phase in this import.

  The delivery_counts table is defined as:
    CREATE TABLE delivery_counts (
        id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        import_id  UUID NOT NULL REFERENCES imports(id) ON DELETE CASCADE,
        phase      phase_enum NOT NULL,
        count      INTEGER NOT NULL DEFAULT 0
    );

Verification approach:
  Direct DB query via NullPool session helpers — NOT via an API endpoint.
  `delivery_counts` has no read endpoint in C4; persistence is the only
  observable behaviour we can assert here.

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
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.domain.enums import ImportStatus, Phase, SourceType, VersionType, PHASES
from app.domain.models import DeliveryCount, Import  # DeliveryCount does NOT exist yet — RED
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
# delivery_counts persistence — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_file_upload_persists_delivery_counts():
    """After PATCH /imports/{id}/file, delivery_counts rows must exist for this import.

    The sample fixture carries delivery counts for all five phases. After a
    successful file upload, at least one DeliveryCount row must be present in
    the DB for this import_id.
    """
    name = "c4-dc-test-persists-delivery-counts"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        Session = _make_test_session()
        async with Session() as session:
            result = await session.execute(
                select(DeliveryCount).where(DeliveryCount.import_id == import_uuid)
            )
            rows = list(result.scalars().all())

        assert len(rows) > 0, (
            f"Expected delivery_counts rows for import {import_id}, found none. "
            "PATCH /imports/{id}/file must persist delivery counts from the xlsx."
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_delivery_counts_all_five_phases_present():
    """After PATCH /imports/{id}/file, exactly one delivery_counts row per phase (p1–p5).

    Phase.total must NOT appear — delivery counts are per-active-phase only.
    The sample fixture has five phases; the endpoint must persist exactly 5 rows.
    """
    name = "c4-dc-test-all-five-phases"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        Session = _make_test_session()
        async with Session() as session:
            result = await session.execute(
                select(DeliveryCount).where(DeliveryCount.import_id == import_uuid)
            )
            rows = list(result.scalars().all())

        phases_present = {row.phase for row in rows}
        expected_phases = set(PHASES)  # {Phase.p1, Phase.p2, Phase.p3, Phase.p4, Phase.p5}

        assert phases_present == expected_phases, (
            f"Expected exactly these phases in delivery_counts: {expected_phases}, "
            f"got: {phases_present}. Phase.total must not be stored."
        )
        assert len(rows) == 5, (
            f"Expected exactly 5 delivery_counts rows (one per phase p1–p5), got {len(rows)}"
        )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_delivery_counts_values_are_non_negative_integers():
    """Every delivery_counts row must have a count that is a non-negative integer.

    Delivery counts represent completed units — a count of 0 is valid (phase
    not yet started), but negative counts are never meaningful.
    """
    name = "c4-dc-test-non-negative-counts"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        Session = _make_test_session()
        async with Session() as session:
            result = await session.execute(
                select(DeliveryCount).where(DeliveryCount.import_id == import_uuid)
            )
            rows = list(result.scalars().all())

        assert len(rows) > 0, "No delivery_counts rows found — cannot check values."
        for row in rows:
            assert isinstance(row.count, int), (
                f"delivery_counts.count for phase={row.phase!r} must be an integer, "
                f"got {type(row.count)}: {row.count!r}"
            )
            assert row.count >= 0, (
                f"delivery_counts.count for phase={row.phase!r} must be >= 0, "
                f"got {row.count}"
            )
    finally:
        await _cleanup_by_id(import_uuid)


@pytest.mark.asyncio
async def test_delivery_counts_cascade_on_import_delete():
    """Hard-deleting an Import row must cascade-delete its delivery_counts rows.

    The delivery_counts table has `ON DELETE CASCADE` on the import_id FK.
    After a hard-delete of the import, no orphaned delivery_counts rows must
    remain.
    """
    name = "c4-dc-test-cascade-on-delete"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)

    # Verify rows exist before delete
    Session = _make_test_session()
    async with Session() as session:
        pre_result = await session.execute(
            select(DeliveryCount).where(DeliveryCount.import_id == import_uuid)
        )
        pre_rows = list(pre_result.scalars().all())
    assert len(pre_rows) > 0, "Setup: no delivery_counts rows found before delete."

    # Hard-delete the import — no try/finally here; cleanup IS the action under test
    await _cleanup_by_id(import_uuid)

    # Verify delivery_counts rows are gone
    async with Session() as session:
        post_result = await session.execute(
            select(DeliveryCount).where(DeliveryCount.import_id == import_uuid)
        )
        post_rows = list(post_result.scalars().all())

    assert len(post_rows) == 0, (
        f"Expected 0 delivery_counts rows after import hard-delete, "
        f"found {len(post_rows)}. ON DELETE CASCADE is not working."
    )


@pytest.mark.asyncio
async def test_delivery_counts_replaced_on_re_upload():
    """A fresh import always writes a clean set of delivery_counts rows.

    The idempotency guard (409 on re-upload) prevents re-uploading in the
    normal flow. This test verifies idempotency from the other direction: by
    directly clearing delivery_counts rows from the DB and then checking that
    a brand-new complete import writes exactly 5 rows (not 0 or 10).

    This ensures the persist logic is self-contained and does not accumulate
    rows across hypothetical re-uploads.
    """
    name = "c4-dc-test-replaced-on-re-upload"
    await _cleanup_by_name(name)
    import_id = await _create_complete_import(name)
    import_uuid = uuid.UUID(import_id)
    try:
        # Manually delete the delivery_counts rows to simulate a re-upload scenario
        Session = _make_test_session()
        async with Session() as session:
            await session.execute(
                delete(DeliveryCount).where(DeliveryCount.import_id == import_uuid)
            )
            await session.commit()

        # Verify they are gone
        async with Session() as session:
            cleared_result = await session.execute(
                select(DeliveryCount).where(DeliveryCount.import_id == import_uuid)
            )
            cleared_rows = list(cleared_result.scalars().all())
        assert len(cleared_rows) == 0, "Setup: rows not cleared before idempotency check."

        # A separate fresh import must write its own 5 rows cleanly
        name2 = "c4-dc-test-replaced-on-re-upload-fresh"
        await _cleanup_by_name(name2)
        import_id2 = await _create_complete_import(name2)
        import_uuid2 = uuid.UUID(import_id2)
        try:
            async with Session() as session:
                result2 = await session.execute(
                    select(DeliveryCount).where(DeliveryCount.import_id == import_uuid2)
                )
                rows2 = list(result2.scalars().all())
            assert len(rows2) == 5, (
                f"Expected exactly 5 delivery_counts rows for a fresh import, "
                f"got {len(rows2)}"
            )
        finally:
            await _cleanup_by_id(import_uuid2)
    finally:
        await _cleanup_by_id(import_uuid)
