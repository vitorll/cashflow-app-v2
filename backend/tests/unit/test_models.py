"""Phase A2 — SQLAlchemy model tests.

These tests are intentionally RED. The module app.domain.models does not exist yet.
The import below will raise ModuleNotFoundError — the canonical RED state.

It is our way.
"""

# This import will fail until app/domain/models.py is created.
from app.domain.models import Import, Base


def test_import_model_table_name():
    """Import model must map to the 'imports' table."""
    assert Import.__tablename__ == "imports"


def test_import_model_has_id_column():
    """Import table must have an 'id' primary-key column."""
    assert "id" in Import.__table__.columns


def test_import_model_has_status_column():
    """Import table must have a 'status' column backed by ImportStatus enum."""
    assert "status" in Import.__table__.columns


def test_import_model_has_deleted_at_column():
    """Import table must have a 'deleted_at' column for soft-delete support."""
    assert "deleted_at" in Import.__table__.columns


def test_import_model_status_is_nullable_false():
    """The 'status' column must be NOT NULL — status is always known."""
    col = Import.__table__.columns["status"]
    assert col.nullable is False, "'status' column must be NOT NULL"


def test_import_model_deleted_at_is_nullable():
    """The 'deleted_at' column must be nullable — NULL means the record is alive."""
    col = Import.__table__.columns["deleted_at"]
    assert col.nullable is True, "'deleted_at' column must be nullable"
