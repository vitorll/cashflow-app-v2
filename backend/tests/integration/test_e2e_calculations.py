"""E2E golden file test — Phase A3.

This test is intentionally RED. It will remain RED until Phase B5 when
parse_excel() and run_cascade() are implemented.

The test imports from modules that do not exist yet. The ImportError IS the
RED state. Do not mock or skip — the failure confirms the contract is locked.

When B5 is complete:
  1. Remove the pytest.importorskip guard
  2. Implement the full assertion block
  3. Verify the test goes GREEN
"""

import json
import pytest
from decimal import Decimal
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
XLSX_PATH = FIXTURES / "sample_import.xlsx"
GOLDEN_PATH = FIXTURES / "expected_output.json"


def test_fixture_files_exist():
    """Both fixture files must be committed to the repo."""
    assert XLSX_PATH.exists(), f"Missing: {XLSX_PATH}"
    assert GOLDEN_PATH.exists(), f"Missing: {GOLDEN_PATH}"


def test_golden_file_is_valid_json():
    """expected_output.json must be parseable JSON with required top-level keys."""
    with open(GOLDEN_PATH) as f:
        data = json.load(f)

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
    with open(GOLDEN_PATH) as f:
        data = json.load(f)

    total = sum(row["count"] for row in data["delivery_counts"])
    assert total == 9


def test_golden_file_n12m_has_calculated_rows():
    """Golden file must contain both input and calculated N12M rows."""
    with open(GOLDEN_PATH) as f:
        data = json.load(f)

    calc_rows = [r for r in data["n12m_line_items"] if r["is_calculated"]]
    input_rows = [r for r in data["n12m_line_items"] if not r["is_calculated"]]
    assert len(calc_rows) >= 6, "Expected at least 6 calculated rows"
    assert len(input_rows) >= 10, "Expected at least 10 input rows"


def test_golden_file_pnl_net_profit_derivation():
    """Net profit must equal gross_profit + sales_and_marketing + direct_costs."""
    with open(GOLDEN_PATH) as f:
        data = json.load(f)

    rows = {r["line_item"]: r for r in data["pnl_summaries"]}
    gross_profit = Decimal(rows["gross_profit"]["current_total"])
    sm = Decimal(rows["sales_and_marketing"]["current_total"])
    direct = Decimal(rows["direct_costs"]["current_total"])
    net = Decimal(rows["net_profit"]["current_total"])
    assert net == gross_profit + sm + direct, "Net profit derivation mismatch in golden file"


@pytest.mark.xfail(
    reason="RED: parse_excel + run_cascade not yet implemented (Phase B2/B4/B5)",
    strict=True,
)
def test_e2e_cascade_output_matches_golden_file():
    """Full E2E: parse Excel → run cascade → assert output == expected_output.json.

    This test is xfail/strict=True:
      - It MUST fail until B5 is complete (strict=True enforces this)
      - When B5 is done, remove xfail and implement the body
    """
    # These imports will raise ImportError until B2/B4 are implemented.
    from app.services.excel_parser.base import parse_excel  # noqa: F401
    from app.services.cascade_service import run_cascade  # noqa: F401

    raise NotImplementedError("Implement in B5")
