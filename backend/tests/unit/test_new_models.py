"""Phase B1 — New SQLAlchemy model tests.

ALL tests in this file are intentionally RED.
The models imported below do not exist yet in app/domain/models.py.
The import block will raise ImportError — the canonical RED state.

This test must fail before we proceed. It is our way.
"""

# These imports will raise ImportError until the models are added to models.py.
# That is the point. Do not suppress the error.
from app.domain.models import (
    PhaseComparisonRow,
    PerDeliveryRow,
    N12mLineItem,
    NcfSeries,
    PnlSummary,
    ExcelTemplate,
    Import,
)


# ---------------------------------------------------------------------------
# PhaseComparisonRow
# ---------------------------------------------------------------------------


def test_phase_comparison_row_table_name():
    """PhaseComparisonRow must map to the 'phase_comparison_rows' table."""
    assert PhaseComparisonRow.__tablename__ == "phase_comparison_rows"


def test_phase_comparison_row_has_import_id_column():
    """phase_comparison_rows must have an 'import_id' FK column."""
    assert "import_id" in PhaseComparisonRow.__table__.columns


def test_phase_comparison_row_has_line_item_column():
    """phase_comparison_rows must have a 'line_item' TEXT column."""
    assert "line_item" in PhaseComparisonRow.__table__.columns


def test_phase_comparison_row_has_phase_column():
    """phase_comparison_rows must have a 'phase' column backed by phase_enum."""
    assert "phase" in PhaseComparisonRow.__table__.columns


def test_phase_comparison_row_has_budget_column():
    """phase_comparison_rows must have a 'budget' NUMERIC column."""
    assert "budget" in PhaseComparisonRow.__table__.columns


def test_phase_comparison_row_has_current_column():
    """phase_comparison_rows must have a 'current' NUMERIC column."""
    assert "current" in PhaseComparisonRow.__table__.columns


def test_phase_comparison_row_has_delta_column():
    """phase_comparison_rows must have a 'delta' computed column."""
    assert "delta" in PhaseComparisonRow.__table__.columns


def test_phase_comparison_row_has_delta_pct_column():
    """phase_comparison_rows must have a 'delta_pct' computed column."""
    assert "delta_pct" in PhaseComparisonRow.__table__.columns


def test_phase_comparison_row_import_id_is_not_nullable():
    """phase_comparison_rows.import_id must be NOT NULL."""
    col = PhaseComparisonRow.__table__.columns["import_id"]
    assert col.nullable is False


def test_phase_comparison_row_line_item_is_not_nullable():
    """phase_comparison_rows.line_item must be NOT NULL."""
    col = PhaseComparisonRow.__table__.columns["line_item"]
    assert col.nullable is False


def test_phase_comparison_row_phase_is_not_nullable():
    """phase_comparison_rows.phase must be NOT NULL."""
    col = PhaseComparisonRow.__table__.columns["phase"]
    assert col.nullable is False


# ---------------------------------------------------------------------------
# PerDeliveryRow — identical structure to PhaseComparisonRow
# ---------------------------------------------------------------------------


def test_per_delivery_row_table_name():
    """PerDeliveryRow must map to the 'per_delivery_rows' table."""
    assert PerDeliveryRow.__tablename__ == "per_delivery_rows"


def test_per_delivery_row_has_import_id_column():
    """per_delivery_rows must have an 'import_id' FK column."""
    assert "import_id" in PerDeliveryRow.__table__.columns


def test_per_delivery_row_has_line_item_column():
    """per_delivery_rows must have a 'line_item' TEXT column."""
    assert "line_item" in PerDeliveryRow.__table__.columns


def test_per_delivery_row_has_phase_column():
    """per_delivery_rows must have a 'phase' column."""
    assert "phase" in PerDeliveryRow.__table__.columns


def test_per_delivery_row_has_budget_column():
    """per_delivery_rows must have a 'budget' NUMERIC column."""
    assert "budget" in PerDeliveryRow.__table__.columns


def test_per_delivery_row_has_current_column():
    """per_delivery_rows must have a 'current' NUMERIC column."""
    assert "current" in PerDeliveryRow.__table__.columns


def test_per_delivery_row_has_delta_column():
    """per_delivery_rows must have a 'delta' computed column."""
    assert "delta" in PerDeliveryRow.__table__.columns


def test_per_delivery_row_has_delta_pct_column():
    """per_delivery_rows must have a 'delta_pct' computed column."""
    assert "delta_pct" in PerDeliveryRow.__table__.columns


# ---------------------------------------------------------------------------
# N12mLineItem
# ---------------------------------------------------------------------------


def test_n12m_line_item_table_name():
    """N12mLineItem must map to the 'n12m_line_items' table."""
    assert N12mLineItem.__tablename__ == "n12m_line_items"


def test_n12m_line_item_has_import_id_column():
    """n12m_line_items must have an 'import_id' FK column."""
    assert "import_id" in N12mLineItem.__table__.columns


def test_n12m_line_item_has_month_column():
    """n12m_line_items must have a 'month' column (1–12)."""
    assert "month" in N12mLineItem.__table__.columns


def test_n12m_line_item_has_section_column():
    """n12m_line_items must have a 'section' column backed by section_type_enum."""
    assert "section" in N12mLineItem.__table__.columns


def test_n12m_line_item_has_line_item_column():
    """n12m_line_items must have a 'line_item' TEXT column."""
    assert "line_item" in N12mLineItem.__table__.columns


def test_n12m_line_item_has_value_column():
    """n12m_line_items must have a 'value' NUMERIC column."""
    assert "value" in N12mLineItem.__table__.columns


def test_n12m_line_item_import_id_is_not_nullable():
    """n12m_line_items.import_id must be NOT NULL."""
    col = N12mLineItem.__table__.columns["import_id"]
    assert col.nullable is False


def test_n12m_line_item_month_is_not_nullable():
    """n12m_line_items.month must be NOT NULL."""
    col = N12mLineItem.__table__.columns["month"]
    assert col.nullable is False


def test_n12m_line_item_section_is_not_nullable():
    """n12m_line_items.section must be NOT NULL."""
    col = N12mLineItem.__table__.columns["section"]
    assert col.nullable is False


def test_n12m_line_item_line_item_is_not_nullable():
    """n12m_line_items.line_item must be NOT NULL."""
    col = N12mLineItem.__table__.columns["line_item"]
    assert col.nullable is False


# ---------------------------------------------------------------------------
# NcfSeries
# ---------------------------------------------------------------------------


def test_ncf_series_table_name():
    """NcfSeries must map to the 'ncf_series' table."""
    assert NcfSeries.__tablename__ == "ncf_series"


def test_ncf_series_has_import_id_column():
    """ncf_series must have an 'import_id' FK column."""
    assert "import_id" in NcfSeries.__table__.columns


def test_ncf_series_has_month_column():
    """ncf_series must have a 'month' column (1–12)."""
    assert "month" in NcfSeries.__table__.columns


def test_ncf_series_has_series_type_column():
    """ncf_series must have a 'series_type' column backed by series_type_enum."""
    assert "series_type" in NcfSeries.__table__.columns


def test_ncf_series_has_value_column():
    """ncf_series must have a 'value' NUMERIC column."""
    assert "value" in NcfSeries.__table__.columns


def test_ncf_series_import_id_is_not_nullable():
    """ncf_series.import_id must be NOT NULL."""
    col = NcfSeries.__table__.columns["import_id"]
    assert col.nullable is False


def test_ncf_series_month_is_not_nullable():
    """ncf_series.month must be NOT NULL."""
    col = NcfSeries.__table__.columns["month"]
    assert col.nullable is False


def test_ncf_series_series_type_is_not_nullable():
    """ncf_series.series_type must be NOT NULL."""
    col = NcfSeries.__table__.columns["series_type"]
    assert col.nullable is False


# ---------------------------------------------------------------------------
# PnlSummary
# ---------------------------------------------------------------------------


def test_pnl_summary_table_name():
    """PnlSummary must map to the 'pnl_summaries' table."""
    assert PnlSummary.__tablename__ == "pnl_summaries"


def test_pnl_summary_has_import_id_column():
    """pnl_summaries must have an 'import_id' FK column."""
    assert "import_id" in PnlSummary.__table__.columns


def test_pnl_summary_has_line_item_column():
    """pnl_summaries must have a 'line_item' TEXT column."""
    assert "line_item" in PnlSummary.__table__.columns


def test_pnl_summary_has_budget_column():
    """pnl_summaries must have a 'budget' NUMERIC column."""
    assert "budget" in PnlSummary.__table__.columns


def test_pnl_summary_has_current_column():
    """pnl_summaries must have a 'current' NUMERIC column."""
    assert "current" in PnlSummary.__table__.columns


def test_pnl_summary_has_delta_column():
    """pnl_summaries must have a 'delta' computed column (current - budget)."""
    assert "delta" in PnlSummary.__table__.columns


def test_pnl_summary_import_id_is_not_nullable():
    """pnl_summaries.import_id must be NOT NULL."""
    col = PnlSummary.__table__.columns["import_id"]
    assert col.nullable is False


def test_pnl_summary_line_item_is_not_nullable():
    """pnl_summaries.line_item must be NOT NULL."""
    col = PnlSummary.__table__.columns["line_item"]
    assert col.nullable is False


# ---------------------------------------------------------------------------
# ExcelTemplate
# ---------------------------------------------------------------------------


def test_excel_template_table_name():
    """ExcelTemplate must map to the 'excel_templates' table."""
    assert ExcelTemplate.__tablename__ == "excel_templates"


def test_excel_template_has_id_column():
    """excel_templates must have a UUID primary key 'id' column."""
    assert "id" in ExcelTemplate.__table__.columns


def test_excel_template_id_is_primary_key():
    """excel_templates.id must be the primary key."""
    col = ExcelTemplate.__table__.columns["id"]
    assert col.primary_key is True


def test_excel_template_has_name_column():
    """excel_templates must have a 'name' TEXT column."""
    assert "name" in ExcelTemplate.__table__.columns


def test_excel_template_has_config_column():
    """excel_templates must have a 'config' JSONB column."""
    assert "config" in ExcelTemplate.__table__.columns


def test_excel_template_has_created_at_column():
    """excel_templates must have a 'created_at' timestamptz column."""
    assert "created_at" in ExcelTemplate.__table__.columns


def test_excel_template_name_is_not_nullable():
    """excel_templates.name must be NOT NULL."""
    col = ExcelTemplate.__table__.columns["name"]
    assert col.nullable is False


# ---------------------------------------------------------------------------
# Import — template_id FK added in B1
# ---------------------------------------------------------------------------


def test_import_model_has_template_id_column():
    """imports table must have a nullable 'template_id' FK column added in B1."""
    assert "template_id" in Import.__table__.columns


def test_import_model_template_id_is_nullable():
    """imports.template_id must be nullable — existing imports pre-date templates."""
    col = Import.__table__.columns["template_id"]
    assert col.nullable is True
