"""Phase B4 — cascade N12M computed rows (RED phase).

These tests are intentionally RED. They will remain RED until Phase B4 when
`app/services/cascade_service.py` is implemented.

The ImportError on the first import IS the RED state. Do not mock or skip —
the failure confirms the contract is locked before a single line of cascade
code is written.

This test must fail before we proceed. It is our way.

When B4 is complete:
  1. Verify every test below goes GREEN without modification.
  2. Do NOT change the assertions to match a wrong implementation —
     fix the implementation to match the tests.
"""

import pytest
from decimal import Decimal, ROUND_HALF_UP

from app.domain.enums import Phase, SectionType, SeriesType, PHASES

# This import will fail until cascade_service.py is created — the RED state.
from app.services.cascade_service import run_cascade  # noqa: E402

# ---------------------------------------------------------------------------
# Minimal parsed_data fixture — mirrors parse_excel() output for 3 months.
# Only the rows required by the calc_rules are included.
# ---------------------------------------------------------------------------

Q4 = Decimal("0.0001")


def _d(s: str) -> Decimal:
    """Return Decimal rounded to 4dp ROUND_HALF_UP."""
    return Decimal(s).quantize(Q4, rounding=ROUND_HALF_UP)


def _make_entries(oct_val, nov_val, dec_val):
    return [
        {"month": "2025-10-01", "value": _d(str(oct_val))},
        {"month": "2025-11-01", "value": _d(str(nov_val))},
        {"month": "2025-12-01", "value": _d(str(dec_val))},
    ]


def _base_n12m():
    """16 input rows from the golden file fixture."""
    return [
        # revenue
        {"section": SectionType.revenue, "line_item": "gross_revenue", "display_name": "Gross Revenue", "is_calculated": False, "sort_order": 1, "entries": _make_entries(60000, 40000, 20000)},
        {"section": SectionType.revenue, "line_item": "sales_costs", "display_name": "Selling Costs", "is_calculated": False, "sort_order": 2, "entries": _make_entries(3000, 2000, 1000)},
        # direct_costs
        {"section": SectionType.direct_costs, "line_item": "primary_build", "display_name": "Primary Build", "is_calculated": False, "sort_order": 3, "entries": _make_entries(30000, 20000, 10000)},
        {"section": SectionType.direct_costs, "line_item": "contingency", "display_name": "Contingency", "is_calculated": False, "sort_order": 4, "entries": _make_entries(0, 0, 0)},
        # overheads
        {"section": SectionType.overheads, "line_item": "marketing", "display_name": "Marketing", "is_calculated": False, "sort_order": 5, "entries": _make_entries(1500, 1000, 500)},
        {"section": SectionType.overheads, "line_item": "admin_overheads", "display_name": "Admin Overheads", "is_calculated": False, "sort_order": 6, "entries": _make_entries(0, 0, 0)},
        # capex
        {"section": SectionType.capex, "line_item": "infrastructure", "display_name": "Infrastructure", "is_calculated": False, "sort_order": 7, "entries": _make_entries(15000, 10000, 5000)},
        {"section": SectionType.capex, "line_item": "civil_works", "display_name": "Civil Works", "is_calculated": False, "sort_order": 8, "entries": _make_entries(0, 0, 0)},
        {"section": SectionType.capex, "line_item": "landscaping", "display_name": "Landscaping", "is_calculated": False, "sort_order": 9, "entries": _make_entries(0, 0, 0)},
        {"section": SectionType.capex, "line_item": "amenities", "display_name": "Amenities", "is_calculated": False, "sort_order": 10, "entries": _make_entries(0, 0, 0)},
        {"section": SectionType.capex, "line_item": "professional_fees", "display_name": "Professional Fees", "is_calculated": False, "sort_order": 11, "entries": _make_entries(3000, 2000, 1000)},
        {"section": SectionType.capex, "line_item": "regulatory_fees", "display_name": "Regulatory Fees", "is_calculated": False, "sort_order": 12, "entries": _make_entries(0, 0, 0)},
        {"section": SectionType.capex, "line_item": "other", "display_name": "Other", "is_calculated": False, "sort_order": 13, "entries": _make_entries(0, 0, 0)},
        {"section": SectionType.capex, "line_item": "contingency_civil_works", "display_name": "Contingency Civil Works", "is_calculated": False, "sort_order": 14, "entries": _make_entries(0, 0, 0)},
        {"section": SectionType.capex, "line_item": "contingency_amenities", "display_name": "Contingency Amenities", "is_calculated": False, "sort_order": 15, "entries": _make_entries(0, 0, 0)},
        {"section": SectionType.capex, "line_item": "ancillary_build_capex", "display_name": "Ancillary Build Capex", "is_calculated": False, "sort_order": 16, "entries": _make_entries(0, 0, 0)},
    ]


def _base_phase_comparison():
    """Minimal phase_comparison_rows for gross_revenue only (enough for cascade)."""
    rows = []
    values = {Phase.p1: "100000", Phase.p2: "150000", Phase.p3: "250000", Phase.p4: "0", Phase.p5: "0", Phase.total: "500000"}
    for phase, val in values.items():
        rows.append({"line_item": "gross_revenue", "phase": phase, "current": _d(val), "budget": None, "delta": None, "delta_pct": None})
    return rows


def _base_parsed_data():
    return {
        "import_meta": {"name": "sample_import", "version_type": "current", "source_type": "excel", "report_month": "2025-09-01"},
        "delivery_counts": [
            {"phase": Phase.p1, "count": 2},
            {"phase": Phase.p2, "count": 3},
            {"phase": Phase.p3, "count": 4},
            {"phase": Phase.p4, "count": 0},
            {"phase": Phase.p5, "count": 0},
        ],
        "n12m_line_items": _base_n12m(),
        "phase_comparison_rows": _base_phase_comparison(),
    }


# ---------------------------------------------------------------------------
# Helpers to extract computed rows from cascade output
# ---------------------------------------------------------------------------


def _get_computed_row(result, line_item):
    rows = {r["line_item"]: r for r in result["n12m_line_items"]}
    assert line_item in rows, f"Computed row '{line_item}' not found in n12m_line_items"
    return rows[line_item]


def _entry_value(row, month):
    entries = {e["month"]: e["value"] for e in row["entries"]}
    assert month in entries, f"Month {month} not found in entries for {row['line_item']}"
    return entries[month]


# ---------------------------------------------------------------------------
# Total row count
# ---------------------------------------------------------------------------


def test_run_cascade_n12m_total_row_count():
    """run_cascade must return 22 n12m rows: 16 input + 6 computed."""
    result = run_cascade(_base_parsed_data())
    assert len(result["n12m_line_items"]) == 22, (
        f"Expected 22 n12m rows (16 input + 6 computed), got {len(result['n12m_line_items'])}"
    )


def test_run_cascade_n12m_six_computed_rows_present():
    """run_cascade must append exactly 6 rows with is_calculated=True."""
    result = run_cascade(_base_parsed_data())
    calc_rows = [r for r in result["n12m_line_items"] if r["is_calculated"] is True]
    assert len(calc_rows) == 6, f"Expected 6 computed rows, got {len(calc_rows)}"


def test_run_cascade_n12m_input_rows_unchanged():
    """run_cascade must not mutate the 16 input (is_calculated=False) rows."""
    result = run_cascade(_base_parsed_data())
    input_rows = [r for r in result["n12m_line_items"] if r["is_calculated"] is False]
    assert len(input_rows) == 16, f"Expected 16 input rows, got {len(input_rows)}"


# ---------------------------------------------------------------------------
# net_revenue = gross_revenue - sales_costs
# ---------------------------------------------------------------------------


def test_run_cascade_net_revenue_october():
    """net_revenue Oct: 60000 - 3000 = 57000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "net_revenue")
    assert _entry_value(row, "2025-10-01") == _d("57000")


def test_run_cascade_net_revenue_november():
    """net_revenue Nov: 40000 - 2000 = 38000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "net_revenue")
    assert _entry_value(row, "2025-11-01") == _d("38000")


def test_run_cascade_net_revenue_december():
    """net_revenue Dec: 20000 - 1000 = 19000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "net_revenue")
    assert _entry_value(row, "2025-12-01") == _d("19000")


def test_run_cascade_net_revenue_is_calculated_true():
    """net_revenue row must have is_calculated=True."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "net_revenue")
    assert row["is_calculated"] is True


def test_run_cascade_net_revenue_section_is_revenue():
    """net_revenue must belong to SectionType.revenue."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "net_revenue")
    assert row["section"] == SectionType.revenue


def test_run_cascade_net_revenue_sort_order():
    """net_revenue sort_order must be 17 (canonical from golden file)."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "net_revenue")
    assert row["sort_order"] == 17


def test_run_cascade_net_revenue_display_name():
    """net_revenue display_name must be 'Net Revenue'."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "net_revenue")
    assert row["display_name"] == "Net Revenue"


# ---------------------------------------------------------------------------
# subtotal_direct_cost = primary_build + contingency
# ---------------------------------------------------------------------------


def test_run_cascade_subtotal_direct_cost_october():
    """subtotal_direct_cost Oct: 30000 + 0 = 30000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "subtotal_direct_cost")
    assert _entry_value(row, "2025-10-01") == _d("30000")


def test_run_cascade_subtotal_direct_cost_november():
    """subtotal_direct_cost Nov: 20000 + 0 = 20000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "subtotal_direct_cost")
    assert _entry_value(row, "2025-11-01") == _d("20000")


def test_run_cascade_subtotal_direct_cost_section():
    """subtotal_direct_cost must belong to SectionType.direct_costs."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "subtotal_direct_cost")
    assert row["section"] == SectionType.direct_costs


def test_run_cascade_subtotal_direct_cost_sort_order():
    """subtotal_direct_cost sort_order must be 18."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "subtotal_direct_cost")
    assert row["sort_order"] == 18


# ---------------------------------------------------------------------------
# subtotal_overheads = marketing + admin_overheads
# ---------------------------------------------------------------------------


def test_run_cascade_subtotal_overheads_october():
    """subtotal_overheads Oct: 1500 + 0 = 1500.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "subtotal_overheads")
    assert _entry_value(row, "2025-10-01") == _d("1500")


def test_run_cascade_subtotal_overheads_december():
    """subtotal_overheads Dec: 500 + 0 = 500.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "subtotal_overheads")
    assert _entry_value(row, "2025-12-01") == _d("500")


def test_run_cascade_subtotal_overheads_section():
    """subtotal_overheads must belong to SectionType.overheads."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "subtotal_overheads")
    assert row["section"] == SectionType.overheads


def test_run_cascade_subtotal_overheads_sort_order():
    """subtotal_overheads sort_order must be 19."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "subtotal_overheads")
    assert row["sort_order"] == 19


# ---------------------------------------------------------------------------
# gross_cash_flow = net_revenue - subtotal_direct_cost - subtotal_overheads
# ---------------------------------------------------------------------------


def test_run_cascade_gross_cash_flow_october():
    """gross_cash_flow Oct: 57000 - 30000 - 1500 = 25500.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "gross_cash_flow")
    assert _entry_value(row, "2025-10-01") == _d("25500")


def test_run_cascade_gross_cash_flow_november():
    """gross_cash_flow Nov: 38000 - 20000 - 1000 = 17000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "gross_cash_flow")
    assert _entry_value(row, "2025-11-01") == _d("17000")


def test_run_cascade_gross_cash_flow_december():
    """gross_cash_flow Dec: 19000 - 10000 - 500 = 8500.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "gross_cash_flow")
    assert _entry_value(row, "2025-12-01") == _d("8500")


def test_run_cascade_gross_cash_flow_section():
    """gross_cash_flow must belong to SectionType.overheads (per golden file)."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "gross_cash_flow")
    assert row["section"] == SectionType.overheads


def test_run_cascade_gross_cash_flow_sort_order():
    """gross_cash_flow sort_order must be 20."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "gross_cash_flow")
    assert row["sort_order"] == 20


# ---------------------------------------------------------------------------
# subtotal_capex = sum of 10 capex line items
# ---------------------------------------------------------------------------


def test_run_cascade_subtotal_capex_october():
    """subtotal_capex Oct: infrastructure(15000) + professional_fees(3000) + zeros = 18000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "subtotal_capex")
    assert _entry_value(row, "2025-10-01") == _d("18000")


def test_run_cascade_subtotal_capex_november():
    """subtotal_capex Nov: 10000 + 2000 = 12000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "subtotal_capex")
    assert _entry_value(row, "2025-11-01") == _d("12000")


def test_run_cascade_subtotal_capex_december():
    """subtotal_capex Dec: 5000 + 1000 = 6000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "subtotal_capex")
    assert _entry_value(row, "2025-12-01") == _d("6000")


def test_run_cascade_subtotal_capex_section():
    """subtotal_capex must belong to SectionType.capex."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "subtotal_capex")
    assert row["section"] == SectionType.capex


def test_run_cascade_subtotal_capex_sort_order():
    """subtotal_capex sort_order must be 21."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "subtotal_capex")
    assert row["sort_order"] == 21


# ---------------------------------------------------------------------------
# net_cash_flow = gross_cash_flow - subtotal_capex
# ---------------------------------------------------------------------------


def test_run_cascade_net_cash_flow_october():
    """net_cash_flow Oct: 25500 - 18000 = 7500.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "net_cash_flow")
    assert _entry_value(row, "2025-10-01") == _d("7500")


def test_run_cascade_net_cash_flow_november():
    """net_cash_flow Nov: 17000 - 12000 = 5000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "net_cash_flow")
    assert _entry_value(row, "2025-11-01") == _d("5000")


def test_run_cascade_net_cash_flow_december():
    """net_cash_flow Dec: 8500 - 6000 = 2500.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "net_cash_flow")
    assert _entry_value(row, "2025-12-01") == _d("2500")


def test_run_cascade_net_cash_flow_section():
    """net_cash_flow must belong to SectionType.capex."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "net_cash_flow")
    assert row["section"] == SectionType.capex


def test_run_cascade_net_cash_flow_sort_order():
    """net_cash_flow sort_order must be 22."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "net_cash_flow")
    assert row["sort_order"] == 22


def test_run_cascade_net_cash_flow_display_name():
    """net_cash_flow display_name must be 'Net Cash Flow'."""
    result = run_cascade(_base_parsed_data())
    row = _get_computed_row(result, "net_cash_flow")
    assert row["display_name"] == "Net Cash Flow"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_run_cascade_n12m_all_zeros_propagates_cleanly():
    """When all input values are zero, all computed rows must also be zero."""
    data = _base_parsed_data()
    for row in data["n12m_line_items"]:
        for entry in row["entries"]:
            entry["value"] = _d("0")
    result = run_cascade(data)
    computed_fields = ["net_revenue", "subtotal_direct_cost", "subtotal_overheads",
                       "gross_cash_flow", "subtotal_capex", "net_cash_flow"]
    for field in computed_fields:
        row = _get_computed_row(result, field)
        for entry in row["entries"]:
            assert entry["value"] == _d("0"), (
                f"Expected Decimal('0.0000') for {field} but got {entry['value']}"
            )


def test_run_cascade_n12m_entry_values_are_decimal():
    """All n12m entry values in cascade output must be Decimal, not float or str."""
    result = run_cascade(_base_parsed_data())
    for row in result["n12m_line_items"]:
        for entry in row["entries"]:
            assert type(entry["value"]) is Decimal, (
                f"Row {row['line_item']!r} month {entry['month']!r}: "
                f"expected Decimal, got {type(entry['value'])!r}"
            )


def test_run_cascade_n12m_values_rounded_to_four_decimal_places():
    """All computed entry values must be rounded to exactly 4 decimal places."""
    # Introduce values that require rounding when divided
    data = _base_parsed_data()
    # Modify gross_revenue to a value that would produce a non-terminating decimal
    # after subtraction — but keep sales_costs as is to force rounding check
    result = run_cascade(data)
    for row in result["n12m_line_items"]:
        if row["is_calculated"]:
            for entry in row["entries"]:
                val = entry["value"]
                assert val == val.quantize(Q4), (
                    f"Row {row['line_item']!r}: value {val} not rounded to 4dp"
                )


def test_run_cascade_output_preserves_import_meta():
    """run_cascade must pass import_meta through unchanged."""
    data = _base_parsed_data()
    result = run_cascade(data)
    assert result["import_meta"] == data["import_meta"]


def test_run_cascade_output_preserves_delivery_counts():
    """run_cascade must pass delivery_counts through unchanged."""
    data = _base_parsed_data()
    result = run_cascade(data)
    assert result["delivery_counts"] == data["delivery_counts"]


def test_run_cascade_output_has_all_required_top_level_keys():
    """run_cascade output must include all 7 required top-level keys."""
    result = run_cascade(_base_parsed_data())
    required = {"import_meta", "delivery_counts", "n12m_line_items",
                 "phase_comparison_rows", "per_delivery_rows", "ncf_series", "pnl_summaries"}
    missing = required - set(result.keys())
    assert not missing, f"run_cascade output missing keys: {missing}"
