"""Phase B1 — Pydantic schema unit tests.

These tests cover app/domain/schemas.py, which had 0% coverage after A2.

Most tests here will PASS immediately (the schemas already exist and are correct).
They exist to lock the contract and bring coverage to 100% for schemas.py.

It is our way.
"""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from decimal import Decimal

from app.domain.enums import ImportStatus, Phase, SectionType, SeriesType, VersionType, SourceType
from app.domain.schemas import (
    ImportCreate,
    ImportResponse,
    ExcelTemplateResponse,
    PhaseComparisonRowResponse,
    PerDeliveryRowResponse,
    N12mLineItemResponse,
    NcfSeriesResponse,
    PnlSummaryResponse,
)


# ---------------------------------------------------------------------------
# ImportCreate — validation
# ---------------------------------------------------------------------------


def test_import_create_accepts_valid_payload():
    """ImportCreate must accept all valid enum values without raising."""
    obj = ImportCreate(
        name="Q1 Budget",
        version_type=VersionType.budget,
        source_type=SourceType.excel,
    )
    assert obj.name == "Q1 Budget"
    assert obj.version_type == VersionType.budget
    assert obj.source_type == SourceType.excel


def test_import_create_accepts_all_version_types():
    """ImportCreate must accept every VersionType variant."""
    for vt in VersionType:
        obj = ImportCreate(name="test", version_type=vt, source_type=SourceType.manual)
        assert obj.version_type == vt


def test_import_create_accepts_all_source_types():
    """ImportCreate must accept every SourceType variant."""
    for st in SourceType:
        obj = ImportCreate(name="test", version_type=VersionType.current, source_type=st)
        assert obj.source_type == st


def test_import_create_rejects_invalid_version_type():
    """ImportCreate must raise ValidationError for an unrecognised version_type."""
    with pytest.raises(ValidationError) as exc_info:
        ImportCreate(name="test", version_type="INVALID", source_type=SourceType.excel)
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("version_type",) for e in errors)


def test_import_create_rejects_invalid_source_type():
    """ImportCreate must raise ValidationError for an unrecognised source_type."""
    with pytest.raises(ValidationError) as exc_info:
        ImportCreate(name="test", version_type=VersionType.budget, source_type="INVALID")
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("source_type",) for e in errors)


def test_import_create_rejects_missing_name():
    """ImportCreate must raise ValidationError when 'name' is omitted."""
    with pytest.raises(ValidationError) as exc_info:
        ImportCreate(version_type=VersionType.budget, source_type=SourceType.excel)
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("name",) for e in errors)


def test_import_create_rejects_missing_version_type():
    """ImportCreate must raise ValidationError when 'version_type' is omitted."""
    with pytest.raises(ValidationError) as exc_info:
        ImportCreate(name="test", source_type=SourceType.excel)
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("version_type",) for e in errors)


def test_import_create_rejects_missing_source_type():
    """ImportCreate must raise ValidationError when 'source_type' is omitted."""
    with pytest.raises(ValidationError) as exc_info:
        ImportCreate(name="test", version_type=VersionType.budget)
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("source_type",) for e in errors)


def test_import_create_model_dump_round_trips():
    """model_dump() must return a dict that can reconstruct the same object."""
    original = ImportCreate(
        name="Round trip",
        version_type=VersionType.forecast,
        source_type=SourceType.api,
    )
    dumped = original.model_dump()
    reconstructed = ImportCreate(**dumped)
    assert reconstructed == original


def test_import_create_model_dump_contains_expected_keys():
    """model_dump() must contain exactly the three base fields."""
    obj = ImportCreate(
        name="Keys test",
        version_type=VersionType.current,
        source_type=SourceType.manual,
    )
    dumped = obj.model_dump()
    assert set(dumped.keys()) == {"name", "version_type", "source_type"}


# ---------------------------------------------------------------------------
# ImportResponse — deserialisation and field presence
# ---------------------------------------------------------------------------


def _make_import_response(**overrides):
    """Helper: build a minimal valid ImportResponse from an ORM-like dict."""
    now = datetime(2026, 3, 5, 12, 0, 0, tzinfo=timezone.utc)
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test Import",
        "version_type": VersionType.budget,
        "source_type": SourceType.excel,
        "status": ImportStatus.pending,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    defaults.update(overrides)
    return ImportResponse.model_validate(defaults)


def test_import_response_includes_id():
    """ImportResponse must expose an 'id' field of type UUID."""
    resp = _make_import_response()
    assert isinstance(resp.id, uuid.UUID)


def test_import_response_includes_status():
    """ImportResponse must expose a 'status' field backed by ImportStatus."""
    resp = _make_import_response(status=ImportStatus.complete)
    assert resp.status == ImportStatus.complete


def test_import_response_includes_created_at():
    """ImportResponse must expose a 'created_at' datetime."""
    resp = _make_import_response()
    assert isinstance(resp.created_at, datetime)


def test_import_response_includes_updated_at():
    """ImportResponse must expose an 'updated_at' datetime."""
    resp = _make_import_response()
    assert isinstance(resp.updated_at, datetime)


def test_import_response_deleted_at_defaults_to_none():
    """ImportResponse.deleted_at must be None when not provided."""
    resp = _make_import_response()
    assert resp.deleted_at is None


def test_import_response_deleted_at_accepts_datetime():
    """ImportResponse.deleted_at must accept a datetime value when the record is soft-deleted."""
    deleted_at = datetime(2026, 3, 6, 9, 0, 0, tzinfo=timezone.utc)
    resp = _make_import_response(deleted_at=deleted_at)
    assert resp.deleted_at == deleted_at


def test_import_response_all_import_status_variants_accepted():
    """ImportResponse must accept every ImportStatus variant in the 'status' field."""
    for status in ImportStatus:
        resp = _make_import_response(status=status)
        assert resp.status == status


def test_import_response_from_attributes_enabled():
    """ImportResponse.model_config must have from_attributes=True for ORM compatibility."""
    assert ImportResponse.model_config.get("from_attributes") is True


def test_import_response_rejects_missing_id():
    """ImportResponse must raise ValidationError when 'id' is absent."""
    now = datetime(2026, 3, 5, 12, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError) as exc_info:
        ImportResponse.model_validate(
            {
                "name": "No ID",
                "version_type": VersionType.budget,
                "source_type": SourceType.excel,
                "status": ImportStatus.pending,
                "created_at": now,
                "updated_at": now,
            }
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("id",) for e in errors)


# ---------------------------------------------------------------------------
# ExcelTemplateResponse
# ---------------------------------------------------------------------------

_TEMPLATE_DATA = {
    "id": uuid.uuid4(),
    "name": "Standard Template",
    "config": {"sheet": "n12m", "header_row": 3},
    "created_at": datetime.now(timezone.utc),
}


def test_excel_template_response_deserialises():
    obj = ExcelTemplateResponse.model_validate(_TEMPLATE_DATA)
    assert obj.name == "Standard Template"
    assert obj.config == {"sheet": "n12m", "header_row": 3}


def test_excel_template_response_from_attributes():
    assert ExcelTemplateResponse.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# PhaseComparisonRowResponse
# ---------------------------------------------------------------------------

_PCR_DATA = {
    "id": uuid.uuid4(),
    "import_id": uuid.uuid4(),
    "line_item": "Gross Revenue",
    "phase": Phase.p1,
    "budget": Decimal("1000.0000"),
    "current": Decimal("1200.0000"),
    "delta": Decimal("200.0000"),
    "delta_pct": Decimal("20.0000"),
}


def test_phase_comparison_row_response_deserialises():
    obj = PhaseComparisonRowResponse.model_validate(_PCR_DATA)
    assert obj.phase == Phase.p1
    assert obj.delta == Decimal("200.0000")


def test_phase_comparison_row_response_nullable_financials():
    data = {**_PCR_DATA, "budget": None, "current": None, "delta": None, "delta_pct": None}
    obj = PhaseComparisonRowResponse.model_validate(data)
    assert obj.budget is None
    assert obj.delta_pct is None


def test_phase_comparison_row_response_financial_fields_are_decimal():
    obj = PhaseComparisonRowResponse.model_validate(_PCR_DATA)
    assert isinstance(obj.budget, Decimal)
    assert isinstance(obj.delta, Decimal)


# ---------------------------------------------------------------------------
# PerDeliveryRowResponse
# ---------------------------------------------------------------------------

def test_per_delivery_row_response_deserialises():
    obj = PerDeliveryRowResponse.model_validate(_PCR_DATA)
    assert obj.phase == Phase.p1
    assert obj.delta_pct == Decimal("20.0000")


def test_per_delivery_row_response_from_attributes():
    assert PerDeliveryRowResponse.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# N12mLineItemResponse
# ---------------------------------------------------------------------------

_N12M_DATA = {
    "id": uuid.uuid4(),
    "import_id": uuid.uuid4(),
    "month": 6,
    "section": SectionType.revenue,
    "line_item": "Sales",
    "value": Decimal("50000.0000"),
}


def test_n12m_line_item_response_deserialises():
    obj = N12mLineItemResponse.model_validate(_N12M_DATA)
    assert obj.month == 6
    assert obj.section == SectionType.revenue
    assert isinstance(obj.value, Decimal)


def test_n12m_line_item_response_all_section_types():
    for section in SectionType:
        obj = N12mLineItemResponse.model_validate({**_N12M_DATA, "section": section})
        assert obj.section == section


# ---------------------------------------------------------------------------
# NcfSeriesResponse
# ---------------------------------------------------------------------------

_NCF_DATA = {
    "id": uuid.uuid4(),
    "import_id": uuid.uuid4(),
    "month": 3,
    "series_type": SeriesType.cumulative,
    "value": Decimal("-25000.0000"),
}


def test_ncf_series_response_deserialises():
    obj = NcfSeriesResponse.model_validate(_NCF_DATA)
    assert obj.series_type == SeriesType.cumulative
    assert obj.value == Decimal("-25000.0000")


def test_ncf_series_response_both_series_types():
    for st in SeriesType:
        obj = NcfSeriesResponse.model_validate({**_NCF_DATA, "series_type": st})
        assert obj.series_type == st


# ---------------------------------------------------------------------------
# PnlSummaryResponse
# ---------------------------------------------------------------------------

_PNL_DATA = {
    "id": uuid.uuid4(),
    "import_id": uuid.uuid4(),
    "line_item": "Gross Profit",
    "budget": Decimal("300000.0000"),
    "current": Decimal("320000.0000"),
    "delta": Decimal("20000.0000"),
}


def test_pnl_summary_response_deserialises():
    obj = PnlSummaryResponse.model_validate(_PNL_DATA)
    assert obj.line_item == "Gross Profit"
    assert obj.delta == Decimal("20000.0000")


def test_pnl_summary_response_nullable_financials():
    data = {**_PNL_DATA, "budget": None, "current": None, "delta": None}
    obj = PnlSummaryResponse.model_validate(data)
    assert obj.budget is None
    assert obj.delta is None


def test_pnl_summary_response_financial_fields_are_decimal():
    obj = PnlSummaryResponse.model_validate(_PNL_DATA)
    assert isinstance(obj.budget, Decimal)
    assert isinstance(obj.delta, Decimal)
