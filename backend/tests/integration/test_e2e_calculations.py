"""E2E golden file test — Phase A3 / B5.

Phase A3: fixture files committed; xfail guard held the test RED.
Phase B5: xfail removed; parse_excel() and run_cascade() are now implemented.
          This test must now pass GREEN in CI on every push.
"""

import json
from decimal import Decimal
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
XLSX_PATH = FIXTURES / "sample_import.xlsx"
GOLDEN_PATH = FIXTURES / "expected_output.json"


def _load_golden():
    with open(GOLDEN_PATH) as f:
        return json.load(f)


def test_fixture_files_exist():
    """Both fixture files must be committed to the repo."""
    assert XLSX_PATH.exists(), f"Missing: {XLSX_PATH}"
    assert GOLDEN_PATH.exists(), f"Missing: {GOLDEN_PATH}"


def test_golden_file_is_valid_json():
    """expected_output.json must be parseable JSON with required top-level keys."""
    data = _load_golden()

    required_keys = {
        "import_meta",
        "delivery_counts",
        "n12m_line_items",
        "phase_comparison_rows",
        "per_delivery_rows",
        "pnl_summaries",
        "ncf_series",
    }
    missing = required_keys - set(data.keys())
    assert not missing, f"expected_output.json missing keys: {missing}"


def test_golden_file_delivery_counts():
    """Delivery counts in golden file must sum to 9."""
    data = _load_golden()
    total = sum(row["count"] for row in data["delivery_counts"])
    assert total == 9


def test_golden_file_n12m_row_counts():
    """Golden file must contain exactly 16 input rows and 6 calculated rows."""
    data = _load_golden()
    calc_rows = [r for r in data["n12m_line_items"] if r["is_calculated"]]
    input_rows = [r for r in data["n12m_line_items"] if not r["is_calculated"]]
    assert len(calc_rows) == 6, f"Expected 6 calculated rows, got {len(calc_rows)}"
    assert len(input_rows) == 16, f"Expected 16 input rows, got {len(input_rows)}"


def test_golden_file_pnl_net_profit_derivation():
    """Net profit must equal gross_profit + sales_and_marketing + direct_costs."""
    data = _load_golden()
    rows = {r["line_item"]: r for r in data["pnl_summaries"]}
    gross_profit = Decimal(rows["gross_profit"]["current_total"])
    sm = Decimal(rows["sales_and_marketing"]["current_total"])
    direct = Decimal(rows["direct_costs"]["current_total"])
    net = Decimal(rows["net_profit"]["current_total"])
    assert net == gross_profit + sm + direct, "Net profit derivation mismatch in golden file"


def test_golden_file_ncf_series_structure():
    """NCF series must have 3 periodic + 3 cumulative entries, cumulative must be running sum."""
    data = _load_golden()
    periodic = [r for r in data["ncf_series"] if r["series_type"] == "periodic"]
    cumulative = [r for r in data["ncf_series"] if r["series_type"] == "cumulative"]

    assert len(periodic) == 3, f"Expected 3 periodic NCF entries, got {len(periodic)}"
    assert len(cumulative) == 3, f"Expected 3 cumulative NCF entries, got {len(cumulative)}"

    # Cumulative must equal running sum of periodic (sorted by month)
    periodic_sorted = sorted(periodic, key=lambda r: r["month"])
    cumulative_sorted = sorted(cumulative, key=lambda r: r["month"])
    running = Decimal("0")
    for p, c in zip(periodic_sorted, cumulative_sorted):
        running += Decimal(p["value"])
        assert Decimal(c["value"]) == running, (
            f"Cumulative NCF mismatch at {c['month']}: "
            f"expected {running}, got {c['value']}"
        )


def test_golden_file_per_delivery_rows():
    """per_delivery_rows must have exactly 6 entries (all phases + total) for gross_revenue."""
    data = _load_golden()
    gross_rev_rows = [r for r in data["per_delivery_rows"] if r["line_item"] == "gross_revenue"]
    assert len(gross_rev_rows) == 6, f"Expected 6 per_delivery rows for gross_revenue, got {len(gross_rev_rows)}"

    # Phases with zero deliveries must have null current value
    zero_delivery_phases = {"p4", "p5"}
    for row in gross_rev_rows:
        if row["phase"] in zero_delivery_phases:
            assert row["current"] is None, (
                f"Phase {row['phase']} has 0 deliveries — current must be null, got {row['current']}"
            )


def test_e2e_cascade_output_matches_golden_file():
    """Full E2E: parse Excel → run cascade → assert output == expected_output.json."""
    from app.services.excel_parser.base import parse_excel
    from app.services.cascade_service import run_cascade

    result = run_cascade(parse_excel(XLSX_PATH))
    golden = _load_golden()

    # import_meta
    assert result["import_meta"]["version_type"] == golden["import_meta"]["version_type"]
    assert result["import_meta"]["report_month"] == golden["import_meta"]["report_month"]

    # delivery_counts
    result_counts = {r["phase"]: r["count"] for r in result["delivery_counts"]}
    for row in golden["delivery_counts"]:
        assert result_counts[row["phase"]] == row["count"], f"delivery_count mismatch: {row['phase']}"

    # n12m_line_items — check all entries for all rows
    result_n12m = {
        (r["line_item"], e["month"]): Decimal(e["value"])
        for r in result["n12m_line_items"]
        for e in r["entries"]
    }
    for row in golden["n12m_line_items"]:
        for entry in row["entries"]:
            key = (row["line_item"], entry["month"])
            expected = Decimal(entry["value"])
            assert key in result_n12m, f"Missing n12m entry: {key}"
            assert abs(result_n12m[key] - expected) < Decimal("0.01"), (
                f"n12m value mismatch at {key}: expected {expected}, got {result_n12m[key]}"
            )

    # pnl_summaries — check current_total for all rows
    result_pnl = {r["line_item"]: r for r in result["pnl_summaries"]}
    for row in golden["pnl_summaries"]:
        assert row["line_item"] in result_pnl, f"Missing P&L row: {row['line_item']}"
        if row["current_total"] is not None:
            expected = Decimal(row["current_total"])
            actual = Decimal(result_pnl[row["line_item"]]["current_total"])
            assert abs(actual - expected) < Decimal("0.01"), (
                f"P&L mismatch for {row['line_item']}: expected {expected}, got {actual}"
            )

    # ncf_series — check all periodic and cumulative entries
    result_ncf = {
        (r["series_type"], r["series_name"], r["month"]): Decimal(r["value"])
        for r in result["ncf_series"]
    }
    for row in golden["ncf_series"]:
        key = (row["series_type"], row["series_name"], row["month"])
        assert key in result_ncf, f"Missing NCF entry: {key}"
        expected = Decimal(row["value"])
        assert abs(result_ncf[key] - expected) < Decimal("0.01"), (
            f"NCF mismatch at {key}: expected {expected}, got {row['value']}"
        )
