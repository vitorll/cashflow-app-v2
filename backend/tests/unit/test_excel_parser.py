"""Phase B2 — Excel TemplateParser unit tests (RED phase).

These tests are intentionally RED. They will remain RED until Phase B2 when
`app/services/excel_parser/base.py` and
`app/services/excel_parser/template_parser.py` are implemented.

The ImportError on the first import IS the RED state. Do not mock or skip —
the failure confirms the contract is locked before a single line of parser
code is written.

This test must fail before we proceed. It is our way.

When B2 is complete:
  1. Verify every test below goes GREEN without modification.
  2. Do NOT change the assertions to match a wrong implementation —
     fix the implementation to match the tests.
"""

import pytest
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent / "fixtures"
XLSX_PATH = FIXTURES / "sample_import.xlsx"

# ---------------------------------------------------------------------------
# Module-level imports — their absence IS the RED state.
# ---------------------------------------------------------------------------

from app.services.excel_parser.base import parse_excel  # noqa: E402
from app.services.excel_parser.template_parser import TemplateParser  # noqa: E402

# ---------------------------------------------------------------------------
# import_meta
# ---------------------------------------------------------------------------


def test_parse_excel_returns_import_meta_version_type():
    """parse_excel must return import_meta with version_type == 'current'."""
    result = parse_excel(XLSX_PATH)
    assert result["import_meta"]["version_type"] == "current"


def test_parse_excel_returns_import_meta_source_type():
    """parse_excel must return import_meta with source_type == 'excel'."""
    result = parse_excel(XLSX_PATH)
    assert result["import_meta"]["source_type"] == "excel"


def test_parse_excel_returns_import_meta_report_month():
    """parse_excel must return import_meta with report_month == '2025-09-01'."""
    result = parse_excel(XLSX_PATH)
    assert result["import_meta"]["report_month"] == "2025-09-01"


def test_parse_excel_import_meta_has_name_key():
    """parse_excel must include a 'name' key in import_meta."""
    result = parse_excel(XLSX_PATH)
    assert "name" in result["import_meta"]


# ---------------------------------------------------------------------------
# delivery_counts
# ---------------------------------------------------------------------------


def test_parse_excel_delivery_counts_length():
    """parse_excel must return exactly 5 delivery_count rows (one per phase)."""
    result = parse_excel(XLSX_PATH)
    assert len(result["delivery_counts"]) == 5


def test_parse_excel_delivery_counts_phase_enum_values():
    """delivery_counts must use Phase enum instances, not raw strings."""
    from app.domain.enums import Phase

    result = parse_excel(XLSX_PATH)
    for row in result["delivery_counts"]:
        assert isinstance(row["phase"], Phase), (
            f"Expected Phase enum, got {type(row['phase'])!r} for value {row['phase']!r}"
        )


def test_parse_excel_delivery_counts_correct_values():
    """delivery_counts must match fixture: p1=2, p2=3, p3=4, p4=0, p5=0."""
    from app.domain.enums import Phase

    result = parse_excel(XLSX_PATH)
    counts = {row["phase"]: row["count"] for row in result["delivery_counts"]}
    assert counts[Phase.p1] == 2
    assert counts[Phase.p2] == 3
    assert counts[Phase.p3] == 4
    assert counts[Phase.p4] == 0
    assert counts[Phase.p5] == 0


def test_parse_excel_delivery_counts_zero_preserved():
    """Zero delivery counts (p4, p5) must be preserved as integer 0, not None or omitted."""
    from app.domain.enums import Phase

    result = parse_excel(XLSX_PATH)
    counts = {row["phase"]: row["count"] for row in result["delivery_counts"]}
    assert counts[Phase.p4] == 0, "p4 zero delivery count must be preserved"
    assert counts[Phase.p5] == 0, "p5 zero delivery count must be preserved"
    assert isinstance(counts[Phase.p4], int)
    assert isinstance(counts[Phase.p5], int)


def test_parse_excel_delivery_counts_total_is_nine():
    """Sum of all delivery counts must equal 9."""
    result = parse_excel(XLSX_PATH)
    total = sum(row["count"] for row in result["delivery_counts"])
    assert total == 9


# ---------------------------------------------------------------------------
# n12m_line_items — row counts
# ---------------------------------------------------------------------------


def test_parse_excel_n12m_returns_only_input_rows():
    """parse_excel must return only the 16 input (is_calculated=False) n12m rows.

    Calculated rows (is_calculated=True) are produced by cascade B4, never by
    the parser. Returning them here would violate the separation of concerns.
    """
    result = parse_excel(XLSX_PATH)
    assert len(result["n12m_line_items"]) == 16, (
        f"Expected 16 input rows, got {len(result['n12m_line_items'])}"
    )


def test_parse_excel_n12m_all_rows_have_is_calculated_false():
    """Every n12m row returned by parse_excel must have is_calculated=False."""
    result = parse_excel(XLSX_PATH)
    for row in result["n12m_line_items"]:
        assert row["is_calculated"] is False, (
            f"Row {row['line_item']!r} has is_calculated={row['is_calculated']!r}; "
            "calculated rows must not be returned by parse_excel"
        )


# ---------------------------------------------------------------------------
# n12m_line_items — SectionType enum enforcement
# ---------------------------------------------------------------------------


def test_parse_excel_n12m_section_is_enum():
    """n12m_line_items must carry SectionType enum instances, not raw strings."""
    from app.domain.enums import SectionType

    result = parse_excel(XLSX_PATH)
    for row in result["n12m_line_items"]:
        assert isinstance(row["section"], SectionType), (
            f"Row {row['line_item']!r}: expected SectionType enum, "
            f"got {type(row['section'])!r}"
        )


def test_parse_excel_n12m_revenue_section_present():
    """At least one n12m row must carry SectionType.revenue."""
    from app.domain.enums import SectionType

    result = parse_excel(XLSX_PATH)
    sections = {row["section"] for row in result["n12m_line_items"]}
    assert SectionType.revenue in sections


# ---------------------------------------------------------------------------
# n12m_line_items — Decimal enforcement
# ---------------------------------------------------------------------------


def test_parse_excel_n12m_entry_values_are_decimal():
    """All n12m monthly entry values must be Decimal, not float or str."""
    result = parse_excel(XLSX_PATH)
    for row in result["n12m_line_items"]:
        for entry in row["entries"]:
            assert isinstance(entry["value"], Decimal), (
                f"Row {row['line_item']!r} month {entry['month']!r}: "
                f"expected Decimal, got {type(entry['value'])!r}"
            )


def test_parse_excel_n12m_gross_revenue_first_entry_value():
    """gross_revenue first month (2025-10-01) must equal Decimal('60000')."""
    result = parse_excel(XLSX_PATH)
    gr_rows = [r for r in result["n12m_line_items"] if r["line_item"] == "gross_revenue"]
    assert gr_rows, "gross_revenue row not found in n12m_line_items"
    entries_by_month = {e["month"]: e["value"] for e in gr_rows[0]["entries"]}
    assert entries_by_month["2025-10-01"] == Decimal("60000"), (
        f"Expected Decimal('60000'), got {entries_by_month['2025-10-01']!r}"
    )


def test_parse_excel_n12m_decimal_precision_is_not_float():
    """Values must not be IEEE 754 floats — Decimal arithmetic must be exact."""
    result = parse_excel(XLSX_PATH)
    for row in result["n12m_line_items"]:
        for entry in row["entries"]:
            # float would fail this: float(60000) == 60000 is True,
            # but isinstance check above already guards this. Reinforce with
            # type identity — no float subtypes allowed.
            assert type(entry["value"]) is Decimal, (
                f"Row {row['line_item']!r}: value must be exactly Decimal, "
                f"got {type(entry['value'])!r}"
            )


def test_parse_excel_n12m_entries_have_three_months():
    """Each n12m row must have exactly 3 monthly entries (fixture has 3 months)."""
    result = parse_excel(XLSX_PATH)
    for row in result["n12m_line_items"]:
        assert len(row["entries"]) == 3, (
            f"Row {row['line_item']!r}: expected 3 monthly entries, "
            f"got {len(row['entries'])}"
        )


def test_parse_excel_n12m_entry_months_are_strings():
    """Monthly entry keys must be string dates in YYYY-MM-DD format."""
    result = parse_excel(XLSX_PATH)
    expected_months = {"2025-10-01", "2025-11-01", "2025-12-01"}
    for row in result["n12m_line_items"]:
        actual_months = {e["month"] for e in row["entries"]}
        assert actual_months == expected_months, (
            f"Row {row['line_item']!r}: expected months {expected_months}, "
            f"got {actual_months}"
        )


# ---------------------------------------------------------------------------
# phase_comparison_rows — count and enum enforcement
# ---------------------------------------------------------------------------


def test_parse_excel_phase_comparison_row_count():
    """parse_excel must return exactly 96 phase_comparison_rows (16 items × 6 phases)."""
    result = parse_excel(XLSX_PATH)
    assert len(result["phase_comparison_rows"]) == 96, (
        f"Expected 96 phase_comparison_rows (16 line_items × 6 phases), "
        f"got {len(result['phase_comparison_rows'])}"
    )


def test_parse_excel_phase_comparison_phase_is_enum():
    """phase_comparison_rows must use Phase enum instances, not raw strings."""
    from app.domain.enums import Phase

    result = parse_excel(XLSX_PATH)
    for row in result["phase_comparison_rows"]:
        assert isinstance(row["phase"], Phase), (
            f"Row {row['line_item']!r}: expected Phase enum, "
            f"got {type(row['phase'])!r}"
        )


def test_parse_excel_phase_comparison_includes_total_phase():
    """phase_comparison_rows must include rows for Phase.total."""
    from app.domain.enums import Phase

    result = parse_excel(XLSX_PATH)
    phases_present = {row["phase"] for row in result["phase_comparison_rows"]}
    assert Phase.total in phases_present, "Phase.total must be present in phase_comparison_rows"


def test_parse_excel_phase_comparison_all_phases_present():
    """phase_comparison_rows must include all 5 phases plus total."""
    from app.domain.enums import Phase

    result = parse_excel(XLSX_PATH)
    phases_present = {row["phase"] for row in result["phase_comparison_rows"]}
    expected_phases = {Phase.p1, Phase.p2, Phase.p3, Phase.p4, Phase.p5, Phase.total}
    assert expected_phases == phases_present, (
        f"Missing phases: {expected_phases - phases_present}"
    )


def test_parse_excel_phase_comparison_current_values_are_decimal():
    """phase_comparison_rows current field must be Decimal, not float or str."""
    result = parse_excel(XLSX_PATH)
    for row in result["phase_comparison_rows"]:
        assert isinstance(row["current"], Decimal), (
            f"Row {row['line_item']!r} phase {row['phase']!r}: "
            f"expected Decimal for current, got {type(row['current'])!r}"
        )


def test_parse_excel_phase_comparison_budget_is_none():
    """Budget field must be None — fixture has no budget import."""
    result = parse_excel(XLSX_PATH)
    for row in result["phase_comparison_rows"]:
        assert row["budget"] is None, (
            f"Row {row['line_item']!r} phase {row['phase']!r}: "
            f"budget must be None for a current-only import, got {row['budget']!r}"
        )


def test_parse_excel_phase_comparison_delta_is_none():
    """Delta field must be None — no budget to diff against in this fixture."""
    result = parse_excel(XLSX_PATH)
    for row in result["phase_comparison_rows"]:
        assert row["delta"] is None, (
            f"Row {row['line_item']!r} phase {row['phase']!r}: "
            f"delta must be None, got {row['delta']!r}"
        )


def test_parse_excel_phase_comparison_delta_pct_is_none():
    """Delta_pct field must be None — no budget to diff against in this fixture."""
    result = parse_excel(XLSX_PATH)
    for row in result["phase_comparison_rows"]:
        assert row["delta_pct"] is None, (
            f"Row {row['line_item']!r} phase {row['phase']!r}: "
            f"delta_pct must be None, got {row['delta_pct']!r}"
        )


# ---------------------------------------------------------------------------
# SeriesType enum enforcement via TemplateParser._parse_series_type
# ---------------------------------------------------------------------------


def test_template_parser_parse_series_type_periodic():
    """_parse_series_type('periodic') must return SeriesType.periodic."""
    from app.domain.enums import SeriesType

    result = TemplateParser._parse_series_type("periodic")
    assert result == SeriesType.periodic


def test_template_parser_parse_series_type_cumulative():
    """_parse_series_type('cumulative') must return SeriesType.cumulative."""
    from app.domain.enums import SeriesType

    result = TemplateParser._parse_series_type("cumulative")
    assert result == SeriesType.cumulative


def test_template_parser_parse_series_type_rejects_invalid():
    """_parse_series_type must raise ValueError for unrecognised series type strings.

    This guards against the v1 naming-drift bug where raw strings like
    'Cumulative' or 'rolling_total' silently propagated into the database.
    """
    with pytest.raises(ValueError, match="Invalid series_type"):
        TemplateParser._parse_series_type("INVALID")


def test_template_parser_parse_series_type_rejects_empty_string():
    """_parse_series_type must raise ValueError for an empty string."""
    with pytest.raises(ValueError):
        TemplateParser._parse_series_type("")


def test_template_parser_parse_series_type_rejects_wrong_case():
    """_parse_series_type must raise ValueError for wrong-cased variants.

    'Cumulative' and 'Periodic' are not valid — only lowercase canonical values.
    This prevents the v1 NCF naming bug from recurring.
    """
    with pytest.raises(ValueError):
        TemplateParser._parse_series_type("Cumulative")
    with pytest.raises(ValueError):
        TemplateParser._parse_series_type("Periodic")


def test_template_parser_parse_series_type_rejects_none():
    """_parse_series_type must raise TypeError or ValueError for None input."""
    with pytest.raises((TypeError, ValueError)):
        TemplateParser._parse_series_type(None)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_parse_excel_raises_file_not_found_for_missing_path():
    """parse_excel must raise FileNotFoundError for a non-existent path."""
    missing = FIXTURES / "does_not_exist.xlsx"
    with pytest.raises(FileNotFoundError):
        parse_excel(missing)


def test_parse_excel_returns_all_required_top_level_keys():
    """parse_excel must return a dict with all four required top-level keys."""
    result = parse_excel(XLSX_PATH)
    required_keys = {"import_meta", "delivery_counts", "n12m_line_items", "phase_comparison_rows"}
    missing = required_keys - set(result.keys())
    assert not missing, f"parse_excel result missing keys: {missing}"
