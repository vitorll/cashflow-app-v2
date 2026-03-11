"""C1: add is_actual, is_calculated, sort_order, display_name to n12m_line_items

Revision ID: c1n12mmeta01
Revises: a1b2c3d4
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa

revision = "c1n12mmeta01"
down_revision = "a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("n12m_line_items", sa.Column("is_actual",     sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("n12m_line_items", sa.Column("is_calculated", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("n12m_line_items", sa.Column("sort_order",    sa.Integer(), nullable=False, server_default="0"))
    op.add_column("n12m_line_items", sa.Column("display_name",  sa.Text(),    nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("n12m_line_items", "display_name")
    op.drop_column("n12m_line_items", "sort_order")
    op.drop_column("n12m_line_items", "is_calculated")
    op.drop_column("n12m_line_items", "is_actual")
