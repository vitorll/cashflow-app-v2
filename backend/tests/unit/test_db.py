"""Phase B1 — app/db.py infrastructure coverage tests.

These tests verify that the database module exposes the correct objects.
They will PASS immediately — their purpose is to bring db.py from 0% to
100% coverage so the CI coverage gate does not reject B1.

Note: db.py is currently uncovered because no test imports it. These tests
lock the public interface of the module so future changes are not invisible.

It is our way.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

import app.db as db_module


def test_db_module_exposes_engine():
    """app.db must expose an 'engine' attribute."""
    assert hasattr(db_module, "engine"), "'engine' is missing from app.db"


def test_engine_is_async_engine():
    """app.db.engine must be an AsyncEngine instance."""
    assert isinstance(db_module.engine, AsyncEngine), (
        f"Expected AsyncEngine, got {type(db_module.engine)}"
    )


def test_db_module_exposes_async_session_local():
    """app.db must expose an 'AsyncSessionLocal' attribute."""
    assert hasattr(db_module, "AsyncSessionLocal"), (
        "'AsyncSessionLocal' is missing from app.db"
    )


def test_async_session_local_is_async_sessionmaker():
    """app.db.AsyncSessionLocal must be an async_sessionmaker instance."""
    assert isinstance(db_module.AsyncSessionLocal, async_sessionmaker), (
        f"Expected async_sessionmaker, got {type(db_module.AsyncSessionLocal)}"
    )


def test_engine_url_is_async_driver():
    """engine must use an async driver (asyncpg)."""
    url = str(db_module.engine.url)
    assert "asyncpg" in url or "postgresql" in url, (
        f"Expected async PostgreSQL driver, got: {url}"
    )


def test_async_session_local_expire_on_commit_false():
    """AsyncSessionLocal must have expire_on_commit=False to avoid lazy-load errors."""
    # async_sessionmaker stores kw args; inspect via kw attribute.
    assert db_module.AsyncSessionLocal.kw.get("expire_on_commit") is False
