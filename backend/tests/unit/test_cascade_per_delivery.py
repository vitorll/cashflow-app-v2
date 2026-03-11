"""Phase B4 — cascade per_delivery_rows computation (RED phase).

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
    """Full phase_comparison for gross_revenue as in golden file."""
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


def _get_per_delivery(result, line_item, phase):
    rows = {(r["line_item"], r["phase"]): r for r in result["per_delivery_rows"]}
    key = (line_item, phase)
    assert key in rows, f"No per_delivery row for ({line_item!r}, {phase!r})"
    return rows[key]


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


def test_run_cascade_per_delivery_rows_present():
    """run_cascade output must include 'per_delivery_rows' key."""
    result = run_cascade(_base_parsed_data())
    assert "per_delivery_rows" in result


def test_run_cascade_per_delivery_gross_revenue_has_six_rows():
    """gross_revenue must have 6 per_delivery rows: p1, p2, p3, p4, p5, total."""
    result = run_cascade(_base_parsed_data())
    gross_rev = [r for r in result["per_delivery_rows"] if r["line_item"] == "gross_revenue"]
    assert len(gross_rev) == 6, f"Expected 6 gross_revenue per_delivery rows, got {len(gross_rev)}"


def test_run_cascade_per_delivery_phase_order():
    """per_delivery_rows must follow phase order: p1, p2, p3, p4, p5, total."""
    result = run_cascade(_base_parsed_data())
    gross_rev = [r for r in result["per_delivery_rows"] if r["line_item"] == "gross_revenue"]
    phases = [r["phase"] for r in gross_rev]
    expected_order = [Phase.p1, Phase.p2, Phase.p3, Phase.p4, Phase.p5, Phase.total]
    assert phases == expected_order, f"Phase order mismatch: {phases}"


def test_run_cascade_per_delivery_phase_is_enum():
    """per_delivery_rows must use Phase enum instances, not raw strings."""
    result = run_cascade(_base_parsed_data())
    for row in result["per_delivery_rows"]:
        assert isinstance(row["phase"], Phase), (
            f"Expected Phase enum, got {type(row['phase'])!r}: {row['phase']!r}"
        )


# ---------------------------------------------------------------------------
# Value calculations (from golden file)
# ---------------------------------------------------------------------------


def test_run_cascade_per_delivery_p1_value():
    """gross_revenue p1: 100000 / 2 = 50000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_per_delivery(result, "gross_revenue", Phase.p1)
    assert row["current"] == _d("50000")


def test_run_cascade_per_delivery_p2_value():
    """gross_revenue p2: 150000 / 3 = 50000.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_per_delivery(result, "gross_revenue", Phase.p2)
    assert row["current"] == _d("50000")


def test_run_cascade_per_delivery_p3_value():
    """gross_revenue p3: 250000 / 4 = 62500.0000."""
    result = run_cascade(_base_parsed_data())
    row = _get_per_delivery(result, "gross_revenue", Phase.p3)
    assert row["current"] == _d("62500")


def test_run_cascade_per_delivery_p4_zero_deliveries_is_none():
    """gross_revenue p4: count=0 → current must be None (not zero, not NaN)."""
    result = run_cascade(_base_parsed_data())
    row = _get_per_delivery(result, "gross_revenue", Phase.p4)
    assert row["current"] is None, (
        f"Expected None for p4 zero deliveries, got {row['current']!r}"
    )


def test_run_cascade_per_delivery_p5_zero_deliveries_is_none():
    """gross_revenue p5: count=0 → current must be None."""
    result = run_cascade(_base_parsed_data())
    row = _get_per_delivery(result, "gross_revenue", Phase.p5)
    assert row["current"] is None, (
        f"Expected None for p5 zero deliveries, got {row['current']!r}"
    )


def test_run_cascade_per_delivery_total_value():
    """gross_revenue total: sum(p1..p5 current) / sum(counts) = 500000 / 9 = 55555.5556."""
    result = run_cascade(_base_parsed_data())
    row = _get_per_delivery(result, "gross_revenue", Phase.total)
    # 500000 / 9 = 55555.555... rounds to 55555.5556 with ROUND_HALF_UP
    assert row["current"] == _d("55555.5556")


def test_run_cascade_per_delivery_total_uses_sum_of_phases_not_total_row():
    """The 'total' per_delivery must sum p1..p5 current values, not use the Phase.total row directly.

    This verifies independence from the phase_comparison total row — the cascade
    must recompute the total from individual phase rows and delivery counts.
    """
    # Use a scenario where the Phase.total row in phase_comparison is intentionally
    # wrong — the per_delivery total must still be computed correctly from p1..p5.
    data = _base_parsed_data()
    # Tamper with the Phase.total row in phase_comparison_rows
    for row in data["phase_comparison_rows"]:
        if row["phase"] == Phase.total:
            row["current"] = _d("999999")  # intentionally wrong
    result = run_cascade(data)
    per_delivery_total = _get_per_delivery(result, "gross_revenue", Phase.total)
    # Should still compute 500000/9 = 55555.5556 from the actual phase rows
    assert per_delivery_total["current"] == _d("55555.5556"), (
        f"per_delivery total must be computed from p1..p5 current / total_deliveries, "
        f"not from the Phase.total phase_comparison row"
    )


# ---------------------------------------------------------------------------
# Null fields (no budget import)
# ---------------------------------------------------------------------------


def test_run_cascade_per_delivery_budget_is_none():
    """All per_delivery budget fields must be None (no budget import in fixture)."""
    result = run_cascade(_base_parsed_data())
    for row in result["per_delivery_rows"]:
        assert row["budget"] is None, (
            f"Row {row['line_item']!r} {row['phase']!r}: budget must be None"
        )


def test_run_cascade_per_delivery_delta_is_none():
    """All per_delivery delta fields must be None (no budget to diff against)."""
    result = run_cascade(_base_parsed_data())
    for row in result["per_delivery_rows"]:
        assert row["delta"] is None, (
            f"Row {row['line_item']!r} {row['phase']!r}: delta must be None"
        )


def test_run_cascade_per_delivery_delta_pct_is_none():
    """All per_delivery delta_pct fields must be None."""
    result = run_cascade(_base_parsed_data())
    for row in result["per_delivery_rows"]:
        assert row["delta_pct"] is None, (
            f"Row {row['line_item']!r} {row['phase']!r}: delta_pct must be None"
        )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_run_cascade_per_delivery_current_is_decimal_when_not_none():
    """per_delivery current values must be Decimal (not float/str) when not None."""
    result = run_cascade(_base_parsed_data())
    for row in result["per_delivery_rows"]:
        if row["current"] is not None:
            assert type(row["current"]) is Decimal, (
                f"Row {row['line_item']!r} {row['phase']!r}: "
                f"expected Decimal, got {type(row['current'])!r}"
            )


def test_run_cascade_per_delivery_all_zero_counts_gives_all_none():
    """When all delivery counts are zero, all per_delivery current values must be None."""
    data = _base_parsed_data()
    for dc in data["delivery_counts"]:
        dc["count"] = 0
    result = run_cascade(data)
    for row in result["per_delivery_rows"]:
        assert row["current"] is None, (
            f"With all-zero counts, expected None for {row['line_item']!r} {row['phase']!r}, "
            f"got {row['current']!r}"
        )


def test_run_cascade_per_delivery_non_divisible_rounds_to_four_dp():
    """per_delivery values that are non-terminating decimals must round to 4dp ROUND_HALF_UP."""
    # 500000 / 9 = 55555.555... → 55555.5556 with ROUND_HALF_UP
    result = run_cascade(_base_parsed_data())
    total_row = _get_per_delivery(result, "gross_revenue", Phase.total)
    assert total_row["current"] == _d("55555.5556"), (
        f"Expected 55555.5556, got {total_row['current']}"
    )
