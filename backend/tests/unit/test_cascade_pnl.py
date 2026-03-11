"""Phase B4 — cascade PnL summaries computation (RED phase).

These tests are intentionally RED. They will remain RED until Phase B4 when
`app/services/cascade_service.py` is implemented.

The ImportError on the first import IS the RED state. Do not mock or skip.

This test must fail before we proceed. It is our way.
"""

import pytest
from decimal import Decimal, ROUND_HALF_UP

from app.domain.enums import Phase, SectionType, PHASES

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


def _get_pnl(result, line_item):
    rows = {r["line_item"]: r for r in result["pnl_summaries"]}
    assert line_item in rows, f"PnL row '{line_item}' not found in pnl_summaries"
    return rows[line_item]


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


def test_run_cascade_pnl_summaries_present():
    """run_cascade output must include 'pnl_summaries' key."""
    result = run_cascade(_base_parsed_data())
    assert "pnl_summaries" in result


def test_run_cascade_pnl_has_seven_rows():
    """pnl_summaries must contain exactly 7 rows."""
    result = run_cascade(_base_parsed_data())
    assert len(result["pnl_summaries"]) == 7, (
        f"Expected 7 PnL rows, got {len(result['pnl_summaries'])}"
    )


def test_run_cascade_pnl_all_required_line_items_present():
    """pnl_summaries must include all 7 required line_item keys."""
    result = run_cascade(_base_parsed_data())
    present = {r["line_item"] for r in result["pnl_summaries"]}
    required = {"deliveries", "revenue", "cogs", "gross_profit", "sales_and_marketing", "direct_costs", "net_profit"}
    missing = required - present
    assert not missing, f"pnl_summaries missing line items: {missing}"


def test_run_cascade_pnl_sort_orders():
    """pnl_summaries sort_orders must match canonical golden file order."""
    result = run_cascade(_base_parsed_data())
    sort_map = {r["line_item"]: r["sort_order"] for r in result["pnl_summaries"]}
    expected = {
        "deliveries": 1,
        "revenue": 2,
        "cogs": 3,
        "gross_profit": 4,
        "sales_and_marketing": 5,
        "direct_costs": 6,
        "net_profit": 7,
    }
    for line_item, expected_order in expected.items():
        assert sort_map[line_item] == expected_order, (
            f"{line_item}: expected sort_order={expected_order}, got {sort_map[line_item]}"
        )


# ---------------------------------------------------------------------------
# deliveries row
# ---------------------------------------------------------------------------


def test_run_cascade_pnl_deliveries_current_total():
    """deliveries current_total: sum of all delivery counts = 9.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "deliveries")
    assert row["current_total"] == _d("9")


def test_run_cascade_pnl_deliveries_current_rate_is_none():
    """deliveries current_rate must be None — rate is not applicable for count rows."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "deliveries")
    assert row["current_rate"] is None, (
        f"deliveries current_rate must be None, got {row['current_rate']!r}"
    )


def test_run_cascade_pnl_deliveries_budget_fields_are_none():
    """deliveries budget_total and budget_rate must both be None."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "deliveries")
    assert row["budget_total"] is None
    assert row["budget_rate"] is None


# ---------------------------------------------------------------------------
# revenue row
# ---------------------------------------------------------------------------


def test_run_cascade_pnl_revenue_current_total():
    """revenue current_total: sum(gross_revenue entries) = 60000+40000+20000 = 120000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "revenue")
    assert row["current_total"] == _d("120000")


def test_run_cascade_pnl_revenue_current_rate():
    """revenue current_rate: 120000 / 9 = 13333.3333."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "revenue")
    assert row["current_rate"] == _d("13333.3333")


def test_run_cascade_pnl_revenue_budget_is_none():
    """revenue budget_total and budget_rate must be None (no budget import)."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "revenue")
    assert row["budget_total"] is None
    assert row["budget_rate"] is None


# ---------------------------------------------------------------------------
# cogs row
# ---------------------------------------------------------------------------


def test_run_cascade_pnl_cogs_current_total():
    """cogs current_total: -(subtotal_direct_cost total) = -(30000+20000+10000) = -60000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "cogs")
    assert row["current_total"] == _d("-60000")


def test_run_cascade_pnl_cogs_current_rate():
    """cogs current_rate: -60000 / 9 = -6666.6667."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "cogs")
    assert row["current_rate"] == _d("-6666.6667")


# ---------------------------------------------------------------------------
# gross_profit row
# ---------------------------------------------------------------------------


def test_run_cascade_pnl_gross_profit_current_total():
    """gross_profit current_total: revenue + cogs = 120000 + (-60000) = 60000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "gross_profit")
    assert row["current_total"] == _d("60000")


def test_run_cascade_pnl_gross_profit_current_rate():
    """gross_profit current_rate: 60000 / 9 = 6666.6667."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "gross_profit")
    assert row["current_rate"] == _d("6666.6667")


def test_run_cascade_pnl_gross_profit_derivation():
    """gross_profit must equal revenue + cogs (both signed), not gross_cash_flow."""
    result = run_cascade(_base_parsed_data())
    rows = {r["line_item"]: r for r in result["pnl_summaries"]}
    revenue = rows["revenue"]["current_total"]
    cogs = rows["cogs"]["current_total"]
    gross_profit = rows["gross_profit"]["current_total"]
    assert gross_profit == (revenue + cogs).quantize(Q4, rounding=ROUND_HALF_UP), (
        f"gross_profit {gross_profit} != revenue({revenue}) + cogs({cogs})"
    )


# ---------------------------------------------------------------------------
# sales_and_marketing row
# ---------------------------------------------------------------------------


def test_run_cascade_pnl_sales_and_marketing_current_total():
    """sales_and_marketing current_total: -(sales_costs + marketing) = -(6000 + 3000) = -9000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "sales_and_marketing")
    assert row["current_total"] == _d("-9000")


def test_run_cascade_pnl_sales_and_marketing_current_rate():
    """sales_and_marketing current_rate: -9000 / 9 = -1000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "sales_and_marketing")
    assert row["current_rate"] == _d("-1000")


# ---------------------------------------------------------------------------
# direct_costs row
# ---------------------------------------------------------------------------


def test_run_cascade_pnl_direct_costs_current_total():
    """direct_costs current_total: -(subtotal_capex total) = -(18000+12000+6000) = -36000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "direct_costs")
    assert row["current_total"] == _d("-36000")


def test_run_cascade_pnl_direct_costs_current_rate():
    """direct_costs current_rate: -36000 / 9 = -4000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "direct_costs")
    assert row["current_rate"] == _d("-4000")


# ---------------------------------------------------------------------------
# net_profit row
# ---------------------------------------------------------------------------


def test_run_cascade_pnl_net_profit_current_total():
    """net_profit current_total: gross_profit + sales_and_marketing + direct_costs = 60000 + (-9000) + (-36000) = 15000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "net_profit")
    assert row["current_total"] == _d("15000")


def test_run_cascade_pnl_net_profit_current_rate():
    """net_profit current_rate: 15000 / 9 = 1666.6667."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "net_profit")
    assert row["current_rate"] == _d("1666.6667")


def test_run_cascade_pnl_net_profit_derivation_matches_components():
    """net_profit must equal gross_profit + sales_and_marketing + direct_costs."""
    result = run_cascade(_base_parsed_data())
    rows = {r["line_item"]: r for r in result["pnl_summaries"]}
    gross_profit = rows["gross_profit"]["current_total"]
    sm = rows["sales_and_marketing"]["current_total"]
    direct = rows["direct_costs"]["current_total"]
    net = rows["net_profit"]["current_total"]
    expected = (gross_profit + sm + direct).quantize(Q4, rounding=ROUND_HALF_UP)
    assert net == expected, f"net_profit {net} != {expected}"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_run_cascade_pnl_delta_fields_all_none():
    """All PnL delta_total and delta_rate fields must be None (no budget import)."""
    result = run_cascade(_base_parsed_data())
    for row in result["pnl_summaries"]:
        assert row["delta_total"] is None, (
            f"PnL {row['line_item']!r}: delta_total must be None"
        )
        assert row["delta_rate"] is None, (
            f"PnL {row['line_item']!r}: delta_rate must be None"
        )


def test_run_cascade_pnl_rate_is_none_when_zero_deliveries():
    """When total_deliveries=0, all current_rate fields must be None (no division by zero)."""
    data = _base_parsed_data()
    for dc in data["delivery_counts"]:
        dc["count"] = 0
    result = run_cascade(data)
    for row in result["pnl_summaries"]:
        if row["line_item"] != "deliveries":
            assert row["current_rate"] is None, (
                f"PnL {row['line_item']!r}: current_rate must be None when deliveries=0, "
                f"got {row['current_rate']!r}"
            )


def test_run_cascade_pnl_numeric_values_are_decimal():
    """All non-None PnL numeric fields must be Decimal (not float or str)."""
    result = run_cascade(_base_parsed_data())
    for row in result["pnl_summaries"]:
        for field in ("current_total", "current_rate", "budget_total", "budget_rate", "delta_total", "delta_rate"):
            val = row.get(field)
            if val is not None:
                assert type(val) is Decimal, (
                    f"PnL {row['line_item']!r} field {field!r}: "
                    f"expected Decimal, got {type(val)!r}"
                )


def test_run_cascade_pnl_deliveries_current_total_is_decimal():
    """deliveries current_total must be Decimal('9.0000'), not int or float."""
    result = run_cascade(_base_parsed_data())
    row = _get_pnl(result, "deliveries")
    assert type(row["current_total"]) is Decimal, (
        f"Expected Decimal for deliveries current_total, got {type(row['current_total'])!r}"
    )
    assert row["current_total"] == _d("9")
