"""C4: add delivery_counts table

Revision ID: c4delivery01
Revises: c1n12mmeta01
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ENUM as PgEnum

revision = "c4delivery01"
down_revision = "c1n12mmeta01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "delivery_counts",
        sa.Column(
            "id",
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "import_id",
            PGUUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "phase",
            PgEnum("p1", "p2", "p3", "p4", "p5", "total", name="phase_enum", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.ForeignKeyConstraint(["import_id"], ["imports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("delivery_counts")
