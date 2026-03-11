"""Phase B4 — run_cascade() end-to-end integration test (RED phase).

This test uses the golden file fixture at backend/tests/fixtures/expected_output.json
and the sample xlsx at backend/tests/fixtures/sample_import.xlsx.

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

import json
import pytest
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from app.domain.enums import Phase, SectionType, SeriesType, PHASES

# These imports will fail until the respective modules are implemented.
from app.services.excel_parser.base import parse_excel  # noqa: E402
from app.services.cascade_service import run_cascade  # noqa: E402

FIXTURES = Path(__file__).parent.parent / "fixtures"
XLSX_PATH = FIXTURES / "sample_import.xlsx"
GOLDEN_PATH = FIXTURES / "expected_output.json"

Q4 = Decimal("0.0001")


def _d(s) -> Decimal:
    return Decimal(str(s)).quantize(Q4, rounding=ROUND_HALF_UP)


def _load_golden():
    with open(GOLDEN_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Precondition: fixture files must exist
# ---------------------------------------------------------------------------


def test_cascade_service_fixture_files_exist():
    """Both fixture files required for E2E assertions must be present."""
    assert XLSX_PATH.exists(), f"Missing fixture: {XLSX_PATH}"
    assert GOLDEN_PATH.exists(), f"Missing fixture: {GOLDEN_PATH}"


# ---------------------------------------------------------------------------
# run_cascade called with live parse_excel output
# ---------------------------------------------------------------------------


def test_run_cascade_accepts_parse_excel_output_without_error():
    """run_cascade must accept parse_excel() output and return a dict without raising."""
    parsed = parse_excel(XLSX_PATH)
    result = run_cascade(parsed)
    assert isinstance(result, dict), f"run_cascade must return dict, got {type(result)!r}"


def test_run_cascade_output_has_all_required_keys():
    """run_cascade output must contain all 7 top-level keys."""
    result = run_cascade(parse_excel(XLSX_PATH))
    required = {"import_meta", "delivery_counts", "n12m_line_items",
                 "phase_comparison_rows", "per_delivery_rows", "ncf_series", "pnl_summaries"}
    missing = required - set(result.keys())
    assert not missing, f"run_cascade missing output keys: {missing}"


# ---------------------------------------------------------------------------
# n12m_line_items — match golden file exactly
# ---------------------------------------------------------------------------


def test_run_cascade_n12m_total_row_count_matches_golden():
    """run_cascade must produce 22 n12m rows (16 input + 6 computed)."""
    result = run_cascade(parse_excel(XLSX_PATH))
    assert len(result["n12m_line_items"]) == 22, (
        f"Expected 22 n12m rows, got {len(result['n12m_line_items'])}"
    )


def test_run_cascade_n12m_computed_values_match_golden():
    """All 6 computed n12m rows must have values matching expected_output.json."""
    result = run_cascade(parse_excel(XLSX_PATH))
    golden = _load_golden()

    # Index golden computed rows by (line_item, month) → value
    golden_computed = {}
    for row in golden["n12m_line_items"]:
        if row["is_calculated"]:
            for entry in row["entries"]:
                golden_computed[(row["line_item"], entry["month"])] = _d(entry["value"])

    # Index result computed rows
    result_computed = {}
    for row in result["n12m_line_items"]:
        if row.get("is_calculated"):
            for entry in row["entries"]:
                result_computed[(row["line_item"], entry["month"])] = entry["value"]

    assert set(golden_computed.keys()) == set(result_computed.keys()), (
        f"Computed row keys mismatch.\n"
        f"Missing from result: {set(golden_computed.keys()) - set(result_computed.keys())}\n"
        f"Extra in result: {set(result_computed.keys()) - set(golden_computed.keys())}"
    )

    for key, expected in golden_computed.items():
        actual = result_computed[key]
        assert actual == expected, (
            f"n12m computed mismatch at {key}: expected {expected}, got {actual}"
        )


def test_run_cascade_n12m_input_rows_match_golden():
    """Input n12m rows (is_calculated=False) must be passed through unchanged from parse_excel."""
    result = run_cascade(parse_excel(XLSX_PATH))
    golden = _load_golden()

    golden_input = {}
    for row in golden["n12m_line_items"]:
        if not row["is_calculated"]:
            for entry in row["entries"]:
                golden_input[(row["line_item"], entry["month"])] = _d(entry["value"])

    result_input = {}
    for row in result["n12m_line_items"]:
        if not row.get("is_calculated", True):
            for entry in row["entries"]:
                result_input[(row["line_item"], entry["month"])] = entry["value"]

    for key, expected in golden_input.items():
        assert key in result_input, f"Input n12m entry missing: {key}"
        assert result_input[key] == expected, (
            f"Input n12m value mismatch at {key}: expected {expected}, got {result_input[key]}"
        )


# ---------------------------------------------------------------------------
# per_delivery_rows — match golden file exactly
# ---------------------------------------------------------------------------


def test_run_cascade_per_delivery_rows_match_golden():
    """per_delivery_rows must match expected_output.json exactly."""
    result = run_cascade(parse_excel(XLSX_PATH))
    golden = _load_golden()

    golden_pd = {
        (r["line_item"], r["phase"]): r["current"]
        for r in golden["per_delivery_rows"]
    }
    result_pd = {
        (r["line_item"], r["phase"].value if isinstance(r["phase"], Phase) else r["phase"]): r["current"]
        for r in result["per_delivery_rows"]
    }

    assert len(result["per_delivery_rows"]) == len(golden["per_delivery_rows"]), (
        f"per_delivery row count mismatch: expected {len(golden['per_delivery_rows'])}, "
        f"got {len(result['per_delivery_rows'])}"
    )

    for (line_item, phase), expected_str in golden_pd.items():
        assert (line_item, phase) in result_pd, (
            f"Missing per_delivery row: ({line_item!r}, {phase!r})"
        )
        expected = _d(expected_str) if expected_str is not None else None
        actual = result_pd[(line_item, phase)]
        if actual is not None:
            actual = _d(str(actual))
        assert actual == expected, (
            f"per_delivery mismatch ({line_item!r}, {phase!r}): expected {expected}, got {actual}"
        )


# ---------------------------------------------------------------------------
# ncf_series — match golden file exactly
# ---------------------------------------------------------------------------


def test_run_cascade_ncf_series_match_golden():
    """ncf_series must match expected_output.json exactly (periodic + cumulative)."""
    result = run_cascade(parse_excel(XLSX_PATH))
    golden = _load_golden()

    golden_ncf = {
        (r["series_type"], r["series_name"], r["month"]): _d(r["value"])
        for r in golden["ncf_series"]
    }

    result_ncf = {}
    for r in result["ncf_series"]:
        series_type = r["series_type"].value if isinstance(r["series_type"], SeriesType) else r["series_type"]
        result_ncf[(series_type, r["series_name"], r["month"])] = _d(str(r["value"]))

    assert set(golden_ncf.keys()) == set(result_ncf.keys()), (
        f"NCF key mismatch.\n"
        f"Missing: {set(golden_ncf.keys()) - set(result_ncf.keys())}\n"
        f"Extra: {set(result_ncf.keys()) - set(golden_ncf.keys())}"
    )

    for key, expected in golden_ncf.items():
        assert result_ncf[key] == expected, (
            f"NCF mismatch at {key}: expected {expected}, got {result_ncf[key]}"
        )


# ---------------------------------------------------------------------------
# pnl_summaries — match golden file exactly
# ---------------------------------------------------------------------------


def test_run_cascade_pnl_summaries_match_golden():
    """pnl_summaries must match expected_output.json for all current_total and current_rate fields."""
    result = run_cascade(parse_excel(XLSX_PATH))
    golden = _load_golden()

    golden_pnl = {r["line_item"]: r for r in golden["pnl_summaries"]}
    result_pnl = {r["line_item"]: r for r in result["pnl_summaries"]}

    assert set(golden_pnl.keys()) == set(result_pnl.keys()), (
        f"PnL line_item mismatch.\n"
        f"Missing: {set(golden_pnl.keys()) - set(result_pnl.keys())}\n"
        f"Extra: {set(result_pnl.keys()) - set(golden_pnl.keys())}"
    )

    for line_item, golden_row in golden_pnl.items():
        result_row = result_pnl[line_item]

        for field in ("current_total", "current_rate", "budget_total", "budget_rate", "delta_total", "delta_rate"):
            expected_raw = golden_row.get(field)
            actual_raw = result_row.get(field)

            if expected_raw is None:
                assert actual_raw is None, (
                    f"PnL {line_item!r} {field}: expected None, got {actual_raw!r}"
                )
            else:
                expected = _d(expected_raw)
                actual = _d(str(actual_raw)) if actual_raw is not None else None
                assert actual == expected, (
                    f"PnL {line_item!r} {field}: expected {expected}, got {actual}"
                )


def test_run_cascade_pnl_sort_orders_match_golden():
    """pnl_summaries sort_order must match golden file for all 7 rows."""
    result = run_cascade(parse_excel(XLSX_PATH))
    golden = _load_golden()

    golden_orders = {r["line_item"]: r["sort_order"] for r in golden["pnl_summaries"]}
    result_orders = {r["line_item"]: r["sort_order"] for r in result["pnl_summaries"]}

    for line_item, expected_order in golden_orders.items():
        assert result_orders.get(line_item) == expected_order, (
            f"PnL {line_item!r}: expected sort_order={expected_order}, "
            f"got {result_orders.get(line_item)!r}"
        )


# ---------------------------------------------------------------------------
# import_meta and delivery_counts pass-through
# ---------------------------------------------------------------------------


def test_run_cascade_import_meta_passthrough():
    """run_cascade must pass import_meta through unchanged from parse_excel."""
    parsed = parse_excel(XLSX_PATH)
    result = run_cascade(parsed)
    golden = _load_golden()

    assert result["import_meta"]["version_type"] == golden["import_meta"]["version_type"]
    assert result["import_meta"]["report_month"] == golden["import_meta"]["report_month"]
    assert result["import_meta"]["source_type"] == golden["import_meta"]["source_type"]


def test_run_cascade_delivery_counts_passthrough():
    """run_cascade must pass delivery_counts through unchanged from parse_excel."""
    parsed = parse_excel(XLSX_PATH)
    result = run_cascade(parsed)

    counts = {r["phase"]: r["count"] for r in result["delivery_counts"]}
    assert counts[Phase.p1] == 2
    assert counts[Phase.p2] == 3
    assert counts[Phase.p3] == 4
    assert counts[Phase.p4] == 0
    assert counts[Phase.p5] == 0


# ---------------------------------------------------------------------------
# Enum integrity in output
# ---------------------------------------------------------------------------


def test_run_cascade_output_n12m_section_fields_are_enums():
    """All n12m section fields in run_cascade output must be SectionType enums."""
    result = run_cascade(parse_excel(XLSX_PATH))
    for row in result["n12m_line_items"]:
        assert isinstance(row["section"], SectionType), (
            f"n12m row {row['line_item']!r}: section must be SectionType enum, "
            f"got {type(row['section'])!r}"
        )


def test_run_cascade_output_per_delivery_phase_fields_are_enums():
    """All per_delivery_rows phase fields in run_cascade output must be Phase enums."""
    result = run_cascade(parse_excel(XLSX_PATH))
    for row in result["per_delivery_rows"]:
        assert isinstance(row["phase"], Phase), (
            f"per_delivery row {row['line_item']!r}: phase must be Phase enum, "
            f"got {type(row['phase'])!r}"
        )


def test_run_cascade_output_ncf_series_type_fields_are_enums():
    """All ncf_series series_type fields in run_cascade output must be SeriesType enums."""
    result = run_cascade(parse_excel(XLSX_PATH))
    for row in result["ncf_series"]:
        assert isinstance(row["series_type"], SeriesType), (
            f"NCF entry: series_type must be SeriesType enum, "
            f"got {type(row['series_type'])!r}"
        )
