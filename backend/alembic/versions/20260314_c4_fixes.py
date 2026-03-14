"""c4 fixes: report_month on imports, unique constraint on delivery_counts

Revision ID: c4fixes01
Revises: c4delivery01
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa

revision = "c4fixes01"
down_revision = "c4delivery01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("imports", sa.Column("report_month", sa.Date(), nullable=True))
    op.create_unique_constraint(
        "uq_delivery_counts_import_phase",
        "delivery_counts",
        ["import_id", "phase"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_delivery_counts_import_phase", "delivery_counts", type_="unique")
    op.drop_column("imports", "report_month")
