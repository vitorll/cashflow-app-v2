"""Phase B4 — cascade NCF series computation (RED phase).

These tests are intentionally RED. They will remain RED until Phase B4 when
`app/services/cascade_service.py` is implemented.

The ImportError on the first import IS the RED state. Do not mock or skip.

This test must fail before we proceed. It is our way.
"""

import pytest
from decimal import Decimal, ROUND_HALF_UP

from app.domain.enums import Phase, SectionType, SeriesType, PHASES

# This import will fail until cascade_service.py is created — the RED state.
from app.services.cascade_service import run_cascade  # noqa: E402

Q4 = Decimal("0.0001")


def _d(s: str) -> Decimal:
    return Decimal(s).quantize(Q4, rounding=ROUND_HALF_UP)


def _make_entries(oct_val, nov_val, dec_val):
    return [
        {"month": "2025-10-01", "value": _d(str(oct_val))},
        {"month": "2025-11-01", "value": _d(str(nov_val))},
        {"month": "2025-12-01", "value": _d(str(dec_val))},
    ]


def _base_n12m():
    return [
        {"section": SectionType.revenue, "line_item": "gross_revenue", "display_name": "Gross Revenue", "is_calculated": False, "sort_order": 1, "entries": _make_entries(60000, 40000, 20000)},
        {"section": SectionType.revenue, "line_item": "sales_costs", "display_name": "Selling Costs", "is_calculated": False, "sort_order": 2, "entries": _make_entries(3000, 2000, 1000)},
        {"section": SectionType.direct_costs, "line_item": "primary_build", "display_name": "Primary Build", "is_calculated": False, "sort_order": 3, "entries": _make_entries(30000, 20000, 10000)},
        {"section": SectionType.direct_costs, "line_item": "contingency", "display_name": "Contingency", "is_calculated": False, "sort_order": 4, "entries": _make_entries(0, 0, 0)},
        {"section": SectionType.overheads, "line_item": "marketing", "display_name": "Marketing", "is_calculated": False, "sort_order": 5, "entries": _make_entries(1500, 1000, 500)},
        {"section": SectionType.overheads, "line_item": "admin_overheads", "display_name": "Admin Overheads", "is_calculated": False, "sort_order": 6, "entries": _make_entries(0, 0, 0)},
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
    return [
        {"line_item": "gross_revenue", "phase": Phase.p1, "current": _d("100000"), "budget": None, "delta": None, "delta_pct": None},
        {"line_item": "gross_revenue", "phase": Phase.p2, "current": _d("150000"), "budget": None, "delta": None, "delta_pct": None},
        {"line_item": "gross_revenue", "phase": Phase.p3, "current": _d("250000"), "budget": None, "delta": None, "delta_pct": None},
        {"line_item": "gross_revenue", "phase": Phase.p4, "current": _d("0"), "budget": None, "delta": None, "delta_pct": None},
        {"line_item": "gross_revenue", "phase": Phase.p5, "current": _d("0"), "budget": None, "delta": None, "delta_pct": None},
        {"line_item": "gross_revenue", "phase": Phase.total, "current": _d("500000"), "budget": None, "delta": None, "delta_pct": None},
    ]


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
# NCF series structure
# ---------------------------------------------------------------------------


def test_run_cascade_ncf_series_present_in_output():
    """run_cascade must include 'ncf_series' key in output."""
    result = run_cascade(_base_parsed_data())
    assert "ncf_series" in result


def test_run_cascade_ncf_series_total_count():
    """NCF series must have 6 entries: 3 periodic + 3 cumulative for 3 months."""
    result = run_cascade(_base_parsed_data())
    assert len(result["ncf_series"]) == 6, (
        f"Expected 6 NCF entries, got {len(result['ncf_series'])}"
    )


def test_run_cascade_ncf_series_three_periodic_entries():
    """NCF series must have exactly 3 periodic entries."""
    result = run_cascade(_base_parsed_data())
    periodic = [r for r in result["ncf_series"] if r["series_type"] == SeriesType.periodic]
    assert len(periodic) == 3, f"Expected 3 periodic entries, got {len(periodic)}"


def test_run_cascade_ncf_series_three_cumulative_entries():
    """NCF series must have exactly 3 cumulative entries."""
    result = run_cascade(_base_parsed_data())
    cumulative = [r for r in result["ncf_series"] if r["series_type"] == SeriesType.cumulative]
    assert len(cumulative) == 3, f"Expected 3 cumulative entries, got {len(cumulative)}"


def test_run_cascade_ncf_series_type_is_enum():
    """All NCF series_type fields must be SeriesType enum instances, not strings."""
    result = run_cascade(_base_parsed_data())
    for row in result["ncf_series"]:
        assert isinstance(row["series_type"], SeriesType), (
            f"Expected SeriesType enum, got {type(row['series_type'])!r}: {row['series_type']!r}"
        )


# ---------------------------------------------------------------------------
# series_name = import_meta["version_type"]
# ---------------------------------------------------------------------------


def test_run_cascade_ncf_series_name_matches_version_type():
    """All NCF entries must have series_name == import_meta['version_type'] == 'current'."""
    result = run_cascade(_base_parsed_data())
    for row in result["ncf_series"]:
        assert row["series_name"] == "current", (
            f"Expected series_name='current', got {row['series_name']!r}"
        )


def test_run_cascade_ncf_series_name_reflects_budget_version_type():
    """series_name must change when import_meta version_type is 'budget'."""
    data = _base_parsed_data()
    data["import_meta"]["version_type"] = "budget"
    result = run_cascade(data)
    for row in result["ncf_series"]:
        assert row["series_name"] == "budget", (
            f"Expected series_name='budget', got {row['series_name']!r}"
        )


# ---------------------------------------------------------------------------
# Periodic values = net_cash_flow n12m entries
# ---------------------------------------------------------------------------


def test_run_cascade_ncf_periodic_october_value():
    """Periodic NCF Oct: net_cash_flow Oct = 7500.0000."""
    result = run_cascade(_base_parsed_data())
    periodic = {r["month"]: r["value"] for r in result["ncf_series"] if r["series_type"] == SeriesType.periodic}
    assert periodic["2025-10-01"] == _d("7500")


def test_run_cascade_ncf_periodic_november_value():
    """Periodic NCF Nov: net_cash_flow Nov = 5000.0000."""
    result = run_cascade(_base_parsed_data())
    periodic = {r["month"]: r["value"] for r in result["ncf_series"] if r["series_type"] == SeriesType.periodic}
    assert periodic["2025-11-01"] == _d("5000")


def test_run_cascade_ncf_periodic_december_value():
    """Periodic NCF Dec: net_cash_flow Dec = 2500.0000."""
    result = run_cascade(_base_parsed_data())
    periodic = {r["month"]: r["value"] for r in result["ncf_series"] if r["series_type"] == SeriesType.periodic}
    assert periodic["2025-12-01"] == _d("2500")


# ---------------------------------------------------------------------------
# Cumulative values = running sum of periodic entries
# ---------------------------------------------------------------------------


def test_run_cascade_ncf_cumulative_october_value():
    """Cumulative NCF Oct: 7500 (running sum after first month)."""
    result = run_cascade(_base_parsed_data())
    cumulative = {r["month"]: r["value"] for r in result["ncf_series"] if r["series_type"] == SeriesType.cumulative}
    assert cumulative["2025-10-01"] == _d("7500")


def test_run_cascade_ncf_cumulative_november_value():
    """Cumulative NCF Nov: 7500 + 5000 = 12500.0000."""
    result = run_cascade(_base_parsed_data())
    cumulative = {r["month"]: r["value"] for r in result["ncf_series"] if r["series_type"] == SeriesType.cumulative}
    assert cumulative["2025-11-01"] == _d("12500")


def test_run_cascade_ncf_cumulative_december_value():
    """Cumulative NCF Dec: 7500 + 5000 + 2500 = 15000.0000."""
    result = run_cascade(_base_parsed_data())
    cumulative = {r["month"]: r["value"] for r in result["ncf_series"] if r["series_type"] == SeriesType.cumulative}
    assert cumulative["2025-12-01"] == _d("15000")


def test_run_cascade_ncf_cumulative_is_running_sum_of_periodic():
    """Cumulative NCF must equal the running sum of periodic entries in month order."""
    result = run_cascade(_base_parsed_data())
    periodic = sorted(
        [r for r in result["ncf_series"] if r["series_type"] == SeriesType.periodic],
        key=lambda r: r["month"],
    )
    cumulative = {r["month"]: r["value"] for r in result["ncf_series"] if r["series_type"] == SeriesType.cumulative}
    running = _d("0")
    for p in periodic:
        running = (running + p["value"]).quantize(Q4, rounding=ROUND_HALF_UP)
        assert cumulative[p["month"]] == running, (
            f"Cumulative mismatch at {p['month']}: expected {running}, got {cumulative[p['month']]}"
        )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_run_cascade_ncf_entry_values_are_decimal():
    """All NCF entry values must be Decimal, not float or str."""
    result = run_cascade(_base_parsed_data())
    for row in result["ncf_series"]:
        assert type(row["value"]) is Decimal, (
            f"NCF entry {row['series_type']} {row['month']}: "
            f"expected Decimal, got {type(row['value'])!r}"
        )


def test_run_cascade_ncf_all_zero_net_cash_flow_gives_zero_series():
    """When net_cash_flow is zero every month, all NCF series values must be zero."""
    data = _base_parsed_data()
    # Zero out all n12m rows so net_cash_flow = 0 every month
    for row in data["n12m_line_items"]:
        for entry in row["entries"]:
            entry["value"] = _d("0")
    result = run_cascade(data)
    for row in result["ncf_series"]:
        assert row["value"] == _d("0"), (
            f"Expected zero NCF for {row['series_type']} {row['month']}, got {row['value']}"
        )


def test_run_cascade_ncf_entries_have_month_field():
    """All NCF entries must carry a 'month' key in YYYY-MM-DD format."""
    result = run_cascade(_base_parsed_data())
    expected_months = {"2025-10-01", "2025-11-01", "2025-12-01"}
    for row in result["ncf_series"]:
        assert "month" in row, f"NCF entry missing 'month' key: {row}"
        assert row["month"] in expected_months, (
            f"Unexpected month {row['month']!r} in NCF series"
        )


def test_run_cascade_ncf_entries_have_series_name_field():
    """All NCF entries must carry a 'series_name' key."""
    result = run_cascade(_base_parsed_data())
    for row in result["ncf_series"]:
        assert "series_name" in row, f"NCF entry missing 'series_name' key: {row}"
