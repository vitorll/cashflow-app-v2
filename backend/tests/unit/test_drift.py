"""Phase A2 — Enum drift tests.

Asserts that every Python enum value exactly matches the corresponding PostgreSQL
enum type in the live database. If a developer adds a value to Python but forgets
the Alembic migration (or vice versa), this test catches it immediately.

These tests are intentionally RED in two ways:
  1. The import of app.domain.enums will raise ModuleNotFoundError (module not written yet).
  2. Even if the import succeeded, the PostgreSQL enum types do not exist yet.

Both failure modes confirm RED. It is our way.

Note on engine name: db.py exports the async engine as `engine`. This test imports
it under the alias `async_engine` for clarity in the test body.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# This import will fail until app/domain/enums.py is created.
from app.domain.enums import (
    Phase,
    SectionType,
    SeriesType,
    ImportStatus,
    VersionType,
    SourceType,
)

from app.config import settings


# Map each PostgreSQL enum type name to its corresponding Python enum class.
# The pg type names must match exactly what the Alembic migration will create.
ENUM_PAIRS = [
    ("phase_enum", Phase),
    ("section_enum", SectionType),
    ("series_type_enum", SeriesType),
    ("import_status_enum", ImportStatus),
    ("version_type_enum", VersionType),
    ("source_type_enum", SourceType),
]


async def get_pg_enum_values(conn, enum_name: str) -> set[str]:
    """Fetch all label values for a given PostgreSQL enum type."""
    result = await conn.execute(
        text(
            "SELECT enumlabel "
            "FROM pg_enum "
            "JOIN pg_type ON pg_enum.enumtypid = pg_type.oid "
            "WHERE pg_type.typname = :name"
        ),
        {"name": enum_name},
    )
    return {row[0] for row in result}


@pytest.mark.parametrize("pg_name,py_enum", ENUM_PAIRS)
async def test_enum_drift(pg_name, py_enum):
    """Python enum values must exactly match PostgreSQL enum values. No drift allowed.

    A mismatch means either:
      - A value was added to Python but the Alembic migration was not written, or
      - A migration ran but the Python enum was not updated.

    Both are bugs. This test is the safety net.
    """
    # Create a fresh engine per test to avoid event-loop reuse issues with asyncpg.
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            pg_values = await get_pg_enum_values(conn, pg_name)
    finally:
        await engine.dispose()

    py_values = {m.value for m in py_enum}

    assert pg_values == py_values, (
        f"Drift detected in '{pg_name}':\n"
        f"  In DB but not Python : {pg_values - py_values}\n"
        f"  In Python but not DB : {py_values - pg_values}"
    )
