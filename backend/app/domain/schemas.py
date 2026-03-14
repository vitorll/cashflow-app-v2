import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ImportStatus, Phase, SectionType, SeriesType, VersionType, SourceType


class ImportBase(BaseModel):
    name: str = Field(min_length=1)
    version_type: VersionType
    source_type: SourceType


class ImportCreate(ImportBase):
    pass


class ImportResponse(ImportBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ImportStatus
    template_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class ExcelTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    config: dict
    created_at: datetime


class PhaseComparisonRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    import_id: uuid.UUID
    line_item: str
    phase: Phase
    budget: Decimal | None = None
    current: Decimal | None = None
    delta: Decimal | None = None
    delta_pct: Decimal | None = None


class PerDeliveryRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    import_id: uuid.UUID
    line_item: str
    phase: Phase
    budget: Decimal | None = None
    current: Decimal | None = None
    delta: Decimal | None = None
    delta_pct: Decimal | None = None


class N12mLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    import_id: uuid.UUID
    month: int
    section: SectionType
    line_item: str
    value: Decimal


class NcfSeriesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    import_id: uuid.UUID
    month: int
    series_type: SeriesType
    value: Decimal


class PnlSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    import_id: uuid.UUID
    line_item: str
    budget: Decimal | None = None
    current: Decimal | None = None
    delta: Decimal | None = None


# ---------------------------------------------------------------------------
# Phase comparison schemas — C2
# ---------------------------------------------------------------------------


class PhaseComparisonEntry(BaseModel):
    phase: Phase
    budget: Decimal | None = None
    current: Decimal | None = None
    delta: Decimal | None = None
    delta_pct: Decimal | None = None


class PhaseComparisonGroupedRow(BaseModel):
    line_item: str
    entries: list[PhaseComparisonEntry]


class PhaseComparisonResponse(BaseModel):
    import_id: uuid.UUID
    rows: list[PhaseComparisonGroupedRow]


# ---------------------------------------------------------------------------
# Forecast schemas — C1
# ---------------------------------------------------------------------------


class ForecastEntry(BaseModel):
    month: int
    value: Decimal
    is_actual: bool


class ForecastRow(BaseModel):
    section: SectionType
    line_item: str
    display_name: str
    is_calculated: bool
    sort_order: int
    entries: list[ForecastEntry]


class ForecastResponse(BaseModel):
    import_id: uuid.UUID
    rows: list[ForecastRow]


# ---------------------------------------------------------------------------
# P&L schemas — C3
# ---------------------------------------------------------------------------


class PnlRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    line_item: str
    budget: Decimal | None = None
    current: Decimal | None = None
    delta: Decimal | None = None


class PnlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    import_id: uuid.UUID
    rows: list[PnlRow]
