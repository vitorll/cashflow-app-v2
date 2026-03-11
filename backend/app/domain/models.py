import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func, text

from app.domain.enums import ImportStatus, Phase, SectionType, SeriesType, VersionType, SourceType


class Base(DeclarativeBase):
    pass


class ExcelTemplate(Base):
    __tablename__ = "excel_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Import(Base):
    __tablename__ = "imports"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    status: Mapped[ImportStatus] = mapped_column(
        sa.Enum(ImportStatus, name="import_status_enum", create_type=False),
        nullable=False,
        default=ImportStatus.pending,
    )
    version_type: Mapped[VersionType] = mapped_column(
        sa.Enum(VersionType, name="version_type_enum", create_type=False),
        nullable=False,
    )
    source_type: Mapped[SourceType] = mapped_column(
        sa.Enum(SourceType, name="source_type_enum", create_type=False),
        nullable=False,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("excel_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )


class PhaseComparisonRow(Base):
    __tablename__ = "phase_comparison_rows"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    import_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("imports.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_item: Mapped[str] = mapped_column(sa.Text, nullable=False)
    phase: Mapped[Phase] = mapped_column(
        sa.Enum(Phase, name="phase_enum", create_type=False),
        nullable=False,
    )
    budget: Mapped[Decimal | None] = mapped_column(sa.NUMERIC(18, 4), nullable=True)
    current: Mapped[Decimal | None] = mapped_column(sa.NUMERIC(18, 4), nullable=True)
    delta: Mapped[Decimal | None] = mapped_column(
        sa.NUMERIC(18, 4),
        sa.Computed('"current" - budget', persisted=True),
        nullable=True,
    )
    delta_pct: Mapped[Decimal | None] = mapped_column(
        sa.NUMERIC(18, 4),
        sa.Computed(
            'CASE WHEN budget = 0 THEN NULL ELSE (("current" - budget) / ABS(budget)) * 100 END',
            persisted=True,
        ),
        nullable=True,
    )


class PerDeliveryRow(Base):
    __tablename__ = "per_delivery_rows"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    import_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("imports.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_item: Mapped[str] = mapped_column(sa.Text, nullable=False)
    phase: Mapped[Phase] = mapped_column(
        sa.Enum(Phase, name="phase_enum", create_type=False),
        nullable=False,
    )
    budget: Mapped[Decimal | None] = mapped_column(sa.NUMERIC(18, 4), nullable=True)
    current: Mapped[Decimal | None] = mapped_column(sa.NUMERIC(18, 4), nullable=True)
    delta: Mapped[Decimal | None] = mapped_column(
        sa.NUMERIC(18, 4),
        sa.Computed('"current" - budget', persisted=True),
        nullable=True,
    )
    delta_pct: Mapped[Decimal | None] = mapped_column(
        sa.NUMERIC(18, 4),
        sa.Computed(
            'CASE WHEN budget = 0 THEN NULL ELSE (("current" - budget) / ABS(budget)) * 100 END',
            persisted=True,
        ),
        nullable=True,
    )


class N12mLineItem(Base):
    __tablename__ = "n12m_line_items"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    import_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("imports.id", ondelete="CASCADE"),
        nullable=False,
    )
    month: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    section: Mapped[SectionType] = mapped_column(
        sa.Enum(SectionType, name="section_enum", create_type=False),
        nullable=False,
    )
    line_item: Mapped[str] = mapped_column(sa.Text, nullable=False)
    value: Mapped[Decimal] = mapped_column(sa.NUMERIC(18, 4), nullable=False)
    is_actual: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    is_calculated: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    display_name: Mapped[str] = mapped_column(sa.Text, nullable=False, default="")


class NcfSeries(Base):
    __tablename__ = "ncf_series"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    import_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("imports.id", ondelete="CASCADE"),
        nullable=False,
    )
    month: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    series_type: Mapped[SeriesType] = mapped_column(
        sa.Enum(SeriesType, name="series_type_enum", create_type=False),
        nullable=False,
    )
    value: Mapped[Decimal] = mapped_column(sa.NUMERIC(18, 4), nullable=False)


class PnlSummary(Base):
    __tablename__ = "pnl_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    import_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("imports.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_item: Mapped[str] = mapped_column(sa.Text, nullable=False)
    budget: Mapped[Decimal | None] = mapped_column(sa.NUMERIC(18, 4), nullable=True)
    current: Mapped[Decimal | None] = mapped_column(sa.NUMERIC(18, 4), nullable=True)
    delta: Mapped[Decimal | None] = mapped_column(
        sa.NUMERIC(18, 4),
        sa.Computed('"current" - budget', persisted=True),
        nullable=True,
    )
