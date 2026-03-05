"""create_domain_enums_and_imports

Revision ID: c8699e959445
Revises:
Create Date: 2026-03-05 09:31:13.934376+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PgEnum


# revision identifiers, used by Alembic.
revision: str = 'c8699e959445'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create all PostgreSQL enum types explicitly via raw DDL.
    # We use op.execute() so we own the lifecycle — Alembic does not auto-manage these.
    op.execute("CREATE TYPE phase_enum AS ENUM ('p1', 'p2', 'p3', 'p4', 'p5', 'total')")
    op.execute("CREATE TYPE section_enum AS ENUM ('revenue', 'direct_costs', 'overheads', 'capex', 'contingency')")
    op.execute("CREATE TYPE series_type_enum AS ENUM ('cumulative', 'periodic')")
    op.execute("CREATE TYPE import_status_enum AS ENUM ('pending', 'processing', 'complete', 'failed')")
    op.execute("CREATE TYPE version_type_enum AS ENUM ('budget', 'current', 'forecast')")
    op.execute("CREATE TYPE source_type_enum AS ENUM ('excel', 'manual', 'api')")

    # Use postgresql.ENUM with create_type=False so SQLAlchemy's _on_table_create
    # event does NOT attempt a second CREATE TYPE during op.create_table().
    op.create_table(
        'imports',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column(
            'status',
            PgEnum('pending', 'processing', 'complete', 'failed',
                   name='import_status_enum', create_type=False),
            nullable=False,
        ),
        sa.Column(
            'version_type',
            PgEnum('budget', 'current', 'forecast',
                   name='version_type_enum', create_type=False),
            nullable=False,
        ),
        sa.Column(
            'source_type',
            PgEnum('excel', 'manual', 'api',
                   name='source_type_enum', create_type=False),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('imports')
    op.execute("DROP TYPE source_type_enum")
    op.execute("DROP TYPE version_type_enum")
    op.execute("DROP TYPE import_status_enum")
    op.execute("DROP TYPE series_type_enum")
    op.execute("DROP TYPE section_enum")
    op.execute("DROP TYPE phase_enum")
