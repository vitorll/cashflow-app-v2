"""b1_add_remaining_tables

Revision ID: a1b2c3d4
Revises: c8699e959445
Create Date: 2026-03-05 10:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID, ENUM as PgEnum


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4'
down_revision: Union[str, None] = 'c8699e959445'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- excel_templates (no enum deps, must come first — imports FKs to it) ---
    op.create_table(
        'excel_templates',
        sa.Column('id', PGUUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('config', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- ALTER imports to add template_id FK ---
    op.add_column(
        'imports',
        sa.Column('template_id', PGUUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_imports_template_id',
        'imports', 'excel_templates',
        ['template_id'], ['id'],
        ondelete='SET NULL',
    )

    # --- phase_comparison_rows ---
    op.create_table(
        'phase_comparison_rows',
        sa.Column('id', PGUUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('import_id', PGUUID(as_uuid=True), nullable=False),
        sa.Column('line_item', sa.Text(), nullable=False),
        sa.Column(
            'phase',
            PgEnum('p1', 'p2', 'p3', 'p4', 'p5', 'total', name='phase_enum', create_type=False),
            nullable=False,
        ),
        sa.Column('budget', sa.NUMERIC(18, 4), nullable=True),
        sa.Column('current', sa.NUMERIC(18, 4), nullable=True),
        sa.Column(
            'delta',
            sa.NUMERIC(18, 4),
            sa.Computed('"current" - budget', persisted=True),
            nullable=True,
        ),
        sa.Column(
            'delta_pct',
            sa.NUMERIC(18, 4),
            sa.Computed(
                'CASE WHEN budget = 0 THEN NULL ELSE (("current" - budget) / ABS(budget)) * 100 END',
                persisted=True,
            ),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(['import_id'], ['imports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('import_id', 'line_item', 'phase', name='uq_phase_comparison_rows'),
    )

    # --- per_delivery_rows (identical structure to phase_comparison_rows) ---
    op.create_table(
        'per_delivery_rows',
        sa.Column('id', PGUUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('import_id', PGUUID(as_uuid=True), nullable=False),
        sa.Column('line_item', sa.Text(), nullable=False),
        sa.Column(
            'phase',
            PgEnum('p1', 'p2', 'p3', 'p4', 'p5', 'total', name='phase_enum', create_type=False),
            nullable=False,
        ),
        sa.Column('budget', sa.NUMERIC(18, 4), nullable=True),
        sa.Column('current', sa.NUMERIC(18, 4), nullable=True),
        sa.Column(
            'delta',
            sa.NUMERIC(18, 4),
            sa.Computed('"current" - budget', persisted=True),
            nullable=True,
        ),
        sa.Column(
            'delta_pct',
            sa.NUMERIC(18, 4),
            sa.Computed(
                'CASE WHEN budget = 0 THEN NULL ELSE (("current" - budget) / ABS(budget)) * 100 END',
                persisted=True,
            ),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(['import_id'], ['imports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('import_id', 'line_item', 'phase', name='uq_per_delivery_rows'),
    )

    # --- n12m_line_items ---
    op.create_table(
        'n12m_line_items',
        sa.Column('id', PGUUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('import_id', PGUUID(as_uuid=True), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column(
            'section',
            PgEnum('revenue', 'direct_costs', 'overheads', 'capex', 'contingency',
                   name='section_enum', create_type=False),
            nullable=False,
        ),
        sa.Column('line_item', sa.Text(), nullable=False),
        sa.Column('value', sa.NUMERIC(18, 4), nullable=False),
        sa.ForeignKeyConstraint(['import_id'], ['imports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('import_id', 'month', 'section', 'line_item', name='uq_n12m_line_items'),
    )

    # --- ncf_series ---
    op.create_table(
        'ncf_series',
        sa.Column('id', PGUUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('import_id', PGUUID(as_uuid=True), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column(
            'series_type',
            PgEnum('cumulative', 'periodic', name='series_type_enum', create_type=False),
            nullable=False,
        ),
        sa.Column('value', sa.NUMERIC(18, 4), nullable=False),
        sa.ForeignKeyConstraint(['import_id'], ['imports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('import_id', 'month', 'series_type', name='uq_ncf_series'),
    )

    # --- pnl_summaries ---
    op.create_table(
        'pnl_summaries',
        sa.Column('id', PGUUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('import_id', PGUUID(as_uuid=True), nullable=False),
        sa.Column('line_item', sa.Text(), nullable=False),
        sa.Column('budget', sa.NUMERIC(18, 4), nullable=True),
        sa.Column('current', sa.NUMERIC(18, 4), nullable=True),
        sa.Column(
            'delta',
            sa.NUMERIC(18, 4),
            sa.Computed('"current" - budget', persisted=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(['import_id'], ['imports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('import_id', 'line_item', name='uq_pnl_summaries'),
    )


def downgrade() -> None:
    op.drop_table('pnl_summaries')
    op.drop_table('ncf_series')
    op.drop_table('n12m_line_items')
    op.drop_table('per_delivery_rows')
    op.drop_table('phase_comparison_rows')
    op.drop_constraint('fk_imports_template_id', 'imports', type_='foreignkey')
    op.drop_column('imports', 'template_id')
    op.drop_table('excel_templates')
