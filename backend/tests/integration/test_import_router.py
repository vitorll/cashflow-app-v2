"""Import router integration tests — Phase B3.

These tests are intentionally RED. The /imports router does not exist yet.
All requests to POST /imports, GET /imports, and DELETE /imports/{id} will
return 404 until the router is implemented. That is the correct RED state.

Do not mock the DB session. These are real integration tests against the
Docker PostgreSQL instance. Each test cleans up its own records.

This test must fail before we proceed. It is our way.

— Birdperson
"""

import uuid

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.config import settings
from app.domain.enums import ImportStatus, SourceType, VersionType
from app.domain.models import Import
from app.main import app


# ---------------------------------------------------------------------------
# Test DB helpers — use NullPool to avoid cross-loop connection reuse issues
# ---------------------------------------------------------------------------

def _make_test_session() -> async_sessionmaker[AsyncSession]:
    """Create a fresh async_sessionmaker with NullPool for test helpers.

    NullPool ensures every session opens a brand-new connection and closes it
    immediately on exit — no connection is ever reused across async tasks or
    event loop boundaries.
    """
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


async def _cleanup_by_name(name: str) -> None:
    """Remove all Import rows with the given name from the DB."""
    Session = _make_test_session()
    async with Session() as session:
        await session.execute(delete(Import).where(Import.name == name))
        await session.commit()


async def _cleanup_by_id(import_id: uuid.UUID) -> None:
    """Remove the Import row with the given id from the DB (hard delete)."""
    Session = _make_test_session()
    async with Session() as session:
        await session.execute(delete(Import).where(Import.id == import_id))
        await session.commit()


async def _fetch_import_by_id(import_id: uuid.UUID) -> Import | None:
    """Fetch a single Import row from the DB, including soft-deleted rows."""
    Session = _make_test_session()
    async with Session() as session:
        result = await session.execute(
            select(Import).where(Import.id == import_id)
        )
        return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# POST /imports — create a new import record
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_imports_returns_201():
    """POST /imports must return HTTP 201 Created."""
    name = "b3-test-post-returns-201"
    await _cleanup_by_name(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/imports",
                json={
                    "name": name,
                    "version_type": VersionType.current.value,
                    "source_type": SourceType.excel.value,
                },
            )
        assert response.status_code == 201, (
            f"Expected 201 Created, got {response.status_code}: {response.text}"
        )
    finally:
        await _cleanup_by_name(name)


@pytest.mark.asyncio
async def test_post_imports_returns_import_response_shape():
    """POST /imports response body must match the ImportResponse schema shape."""
    name = "b3-test-post-response-shape"
    await _cleanup_by_name(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/imports",
                json={
                    "name": name,
                    "version_type": VersionType.budget.value,
                    "source_type": SourceType.manual.value,
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data, "Response must contain 'id'"
        assert "name" in data, "Response must contain 'name'"
        assert "version_type" in data, "Response must contain 'version_type'"
        assert "source_type" in data, "Response must contain 'source_type'"
        assert "status" in data, "Response must contain 'status'"
        assert "created_at" in data, "Response must contain 'created_at'"
        assert "updated_at" in data, "Response must contain 'updated_at'"
    finally:
        await _cleanup_by_name(name)


@pytest.mark.asyncio
async def test_post_imports_status_defaults_to_pending():
    """POST /imports must set status to 'pending' regardless of caller input."""
    name = "b3-test-post-status-pending"
    await _cleanup_by_name(name)
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/imports",
                json={
                    "name": name,
                    "version_type": VersionType.forecast.value,
                    "source_type": SourceType.api.value,
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == ImportStatus.pending.value, (
            f"Expected status='pending', got '{data['status']}'"
        )
    finally:
        await _cleanup_by_name(name)


@pytest.mark.asyncio
async def test_post_imports_persists_record_to_db():
    """POST /imports must persist the record in the database."""
    name = "b3-test-post-persists-db"
    await _cleanup_by_name(name)
    created_id = None
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/imports",
                json={
                    "name": name,
                    "version_type": VersionType.current.value,
                    "source_type": SourceType.excel.value,
                },
            )
        assert response.status_code == 201
        created_id = uuid.UUID(response.json()["id"])
        row = await _fetch_import_by_id(created_id)
        assert row is not None, "Import row must exist in DB after POST"
        assert row.name == name
        assert row.status == ImportStatus.pending
    finally:
        if created_id:
            await _cleanup_by_id(created_id)


@pytest.mark.asyncio
async def test_post_imports_returns_422_when_version_type_invalid():
    """POST /imports must return 422 when version_type is not a valid enum value."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/imports",
            json={
                "name": "b3-test-invalid-version-type",
                "version_type": "not_a_real_type",
                "source_type": SourceType.excel.value,
            },
        )
    assert response.status_code == 422, (
        f"Expected 422 for invalid version_type, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_post_imports_returns_422_when_source_type_invalid():
    """POST /imports must return 422 when source_type is not a valid enum value."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/imports",
            json={
                "name": "b3-test-invalid-source-type",
                "version_type": VersionType.budget.value,
                "source_type": "fax_machine",
            },
        )
    assert response.status_code == 422, (
        f"Expected 422 for invalid source_type, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_post_imports_returns_422_when_name_missing():
    """POST /imports must return 422 when the required 'name' field is absent."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/imports",
            json={
                "version_type": VersionType.budget.value,
                "source_type": SourceType.manual.value,
            },
        )
    assert response.status_code == 422, (
        f"Expected 422 when name missing, got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# GET /imports — list non-deleted imports
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_imports_returns_200():
    """GET /imports must return HTTP 200."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/imports")
    assert response.status_code == 200, (
        f"Expected 200 from GET /imports, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_get_imports_returns_a_list():
    """GET /imports response body must be a JSON array."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/imports")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list), (
        f"Expected a list from GET /imports, got {type(data).__name__}"
    )


@pytest.mark.asyncio
async def test_get_imports_includes_newly_created_import():
    """GET /imports must include an import created via POST /imports."""
    name = "b3-test-get-includes-new"
    await _cleanup_by_name(name)
    created_id = None
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            post_response = await client.post(
                "/imports",
                json={
                    "name": name,
                    "version_type": VersionType.current.value,
                    "source_type": SourceType.excel.value,
                },
            )
        assert post_response.status_code == 201
        created_id = post_response.json()["id"]

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            get_response = await client.get("/imports")
        assert get_response.status_code == 200
        ids = [item["id"] for item in get_response.json()]
        assert created_id in ids, (
            f"Newly created import {created_id} not found in GET /imports list"
        )
    finally:
        if created_id:
            await _cleanup_by_id(uuid.UUID(created_id))


@pytest.mark.asyncio
async def test_get_imports_excludes_soft_deleted_imports():
    """GET /imports must NOT return imports where deleted_at is set."""
    name = "b3-test-get-excludes-soft-deleted"
    await _cleanup_by_name(name)
    created_id = None
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create
            post_response = await client.post(
                "/imports",
                json={
                    "name": name,
                    "version_type": VersionType.budget.value,
                    "source_type": SourceType.manual.value,
                },
            )
        assert post_response.status_code == 201
        created_id = post_response.json()["id"]

        # Soft-delete
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            delete_response = await client.delete(f"/imports/{created_id}")
        assert delete_response.status_code == 204

        # List must not include the deleted record
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            get_response = await client.get("/imports")
        assert get_response.status_code == 200
        ids = [item["id"] for item in get_response.json()]
        assert created_id not in ids, (
            f"Soft-deleted import {created_id} must not appear in GET /imports"
        )
    finally:
        if created_id:
            await _cleanup_by_id(uuid.UUID(created_id))


@pytest.mark.asyncio
async def test_get_imports_each_item_has_required_fields():
    """GET /imports items must each contain the full ImportResponse fields."""
    name = "b3-test-get-item-fields"
    await _cleanup_by_name(name)
    created_id = None
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            post_response = await client.post(
                "/imports",
                json={
                    "name": name,
                    "version_type": VersionType.forecast.value,
                    "source_type": SourceType.api.value,
                },
            )
        assert post_response.status_code == 201
        created_id = post_response.json()["id"]

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            get_response = await client.get("/imports")
        assert get_response.status_code == 200
        items = get_response.json()
        match = next((i for i in items if i["id"] == created_id), None)
        assert match is not None, "Newly created import not found in list"
        for field in ("id", "name", "version_type", "source_type", "status", "created_at", "updated_at"):
            assert field in match, f"Field '{field}' missing from list item"
    finally:
        if created_id:
            await _cleanup_by_id(uuid.UUID(created_id))


# ---------------------------------------------------------------------------
# DELETE /imports/{id} — soft-delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_import_returns_204():
    """DELETE /imports/{id} must return HTTP 204 No Content."""
    name = "b3-test-delete-returns-204"
    await _cleanup_by_name(name)
    created_id = None
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            post_response = await client.post(
                "/imports",
                json={
                    "name": name,
                    "version_type": VersionType.current.value,
                    "source_type": SourceType.excel.value,
                },
            )
        assert post_response.status_code == 201
        created_id = post_response.json()["id"]

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            delete_response = await client.delete(f"/imports/{created_id}")
        assert delete_response.status_code == 204, (
            f"Expected 204, got {delete_response.status_code}: {delete_response.text}"
        )
    finally:
        if created_id:
            await _cleanup_by_id(uuid.UUID(created_id))


@pytest.mark.asyncio
async def test_delete_import_sets_deleted_at_in_db():
    """DELETE /imports/{id} must set deleted_at on the DB row (soft-delete, not hard-delete)."""
    name = "b3-test-delete-sets-deleted-at"
    await _cleanup_by_name(name)
    created_id = None
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            post_response = await client.post(
                "/imports",
                json={
                    "name": name,
                    "version_type": VersionType.budget.value,
                    "source_type": SourceType.manual.value,
                },
            )
        assert post_response.status_code == 201
        created_id = uuid.UUID(post_response.json()["id"])

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.delete(f"/imports/{created_id}")

        row = await _fetch_import_by_id(created_id)
        assert row is not None, "Row must still exist in DB after soft-delete"
        assert row.deleted_at is not None, (
            "deleted_at must be set after DELETE /imports/{id}"
        )
    finally:
        if created_id:
            await _cleanup_by_id(created_id)


@pytest.mark.asyncio
async def test_delete_import_returns_404_for_nonexistent_id():
    """DELETE /imports/{id} must return 404 when the id does not exist in the DB."""
    nonexistent_id = uuid.uuid4()
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.delete(f"/imports/{nonexistent_id}")
    assert response.status_code == 404, (
        f"Expected 404 for nonexistent import, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_delete_import_returns_404_when_already_soft_deleted():
    """DELETE /imports/{id} must return 404 if the import is already soft-deleted."""
    name = "b3-test-delete-already-deleted"
    await _cleanup_by_name(name)
    created_id = None
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            post_response = await client.post(
                "/imports",
                json={
                    "name": name,
                    "version_type": VersionType.current.value,
                    "source_type": SourceType.excel.value,
                },
            )
        assert post_response.status_code == 201
        created_id = post_response.json()["id"]

        # First delete — must succeed
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first_delete = await client.delete(f"/imports/{created_id}")
        assert first_delete.status_code == 204

        # Second delete — must 404
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            second_delete = await client.delete(f"/imports/{created_id}")
        assert second_delete.status_code == 404, (
            f"Expected 404 on second delete of same import, got {second_delete.status_code}"
        )
    finally:
        if created_id:
            await _cleanup_by_id(uuid.UUID(created_id))


@pytest.mark.asyncio
async def test_delete_import_returns_422_for_malformed_uuid():
    """DELETE /imports/{id} must return 422 when the id is not a valid UUID."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.delete("/imports/not-a-uuid")
    assert response.status_code == 422, (
        f"Expected 422 for malformed UUID path param, got {response.status_code}"
    )
