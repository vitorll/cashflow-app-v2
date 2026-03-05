# A3: Golden File Fixture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `backend/tests/fixtures/sample_import.xlsx` and `backend/tests/fixtures/expected_output.json` — the golden file pair that locks in the cascade contract before any service code is written.

**Architecture:** A Python script (`build_fixture.py`) generates a deterministic, minimal Excel file with synthetic round numbers covering all five calc_rules.json calculation paths. A companion `expected_output.json` contains the exact values the cascade must produce when parsing and processing that Excel file. A RED integration test imports the (non-existent) service functions — it fails because the service doesn't exist, not because the data is wrong.

**Tech Stack:** Python 3.11, openpyxl (fixture generation), pytest (RED test), decimal (NUMERIC(18,4) precision)

---

## Data Design (read this before any task)

### Import metadata
```
version_type: current
source_type:  excel
report_month: 2025-09-01
actual_flags: [true, true, true]      # all 3 N12M months are actuals
n12m_months:  2025-10-01, 2025-11-01, 2025-12-01
```

### Delivery counts
```
p1=2, p2=3, p3=4, p4=0, p5=0   total=9
```

### N12M raw input values (costs stored as POSITIVE per v2 convention)
```
line_item               section       is_calc  sort  Oct     Nov     Dec
gross_revenue           revenue       false     1    60000   40000   20000
sales_costs             revenue       false     2     3000    2000    1000
primary_build           direct_costs  false     3    30000   20000   10000
contingency             direct_costs  false     4        0       0       0
marketing               overheads     false     5     1500    1000     500
admin_overheads         overheads     false     6        0       0       0
infrastructure          capex         false     7    15000   10000    5000
civil_works             capex         false     8        0       0       0
landscaping             capex         false     9        0       0       0
amenities               capex         false    10        0       0       0
professional_fees       capex         false    11     3000    2000    1000
regulatory_fees         capex         false    12        0       0       0
other                   capex         false    13        0       0       0
contingency_civil_works capex         false    14        0       0       0
contingency_amenities   capex         false    15        0       0       0
ancillary_build_capex   capex         false    16        0       0       0
```

### Phase comparison (whole-of-project current values)
```
line_item        p1       p2       p3    p4  p5   total
gross_revenue   100000  150000  250000    0   0  500000
sales_costs       5000    7500   12500    0   0   25000
primary_build    50000   75000  125000    0   0  250000
marketing         5000    7500   12500    0   0   25000
infrastructure   20000   30000   50000    0   0  100000
professional_fees 10000  15000   25000    0   0   50000
(all other lines: 0 across all phases)
```

### Cascade derivations (calc_rules.json applied monthly)
```
Calculated N12M (cascade derives these; NOT in Excel input):
line_item               is_calc  sort   Oct       Nov      Dec     SUM
net_revenue             true      17   57000    38000    19000   114000
subtotal_direct_cost    true      18   30000    20000    10000    60000
subtotal_overheads      true      19    1500     1000      500     3000
gross_cash_flow         true      20   25500    17000     8500    51000
subtotal_capex          true      21   18000    12000     6000    36000
net_cash_flow           true      22    7500     5000     2500    15000
```

### NCF series (derived from net_cash_flow)
```
periodic/current:    Oct=7500,  Nov=5000,  Dec=2500
cumulative/current:  Oct=7500,  Nov=12500, Dec=15000
```

### P&L (from N12M sums, per pnl-spec.md — budget=null, no budget import)
```
line_item         sort  current_total   current_rate  (÷9 deliveries)
deliveries           1        9              null
revenue              2   120000.0000    13333.3333
cogs                 3   -60000.0000    -6666.6667
gross_profit         4    60000.0000     6666.6667
sales_and_marketing  5    -9000.0000    -1000.0000
direct_costs         6   -36000.0000    -4000.0000
net_profit           7    15000.0000     1666.6667
```
Budget totals and rates are null (no budget import linked).

### Per delivery (phase_comparison ÷ delivery_counts)
```
gross_revenue per delivery:
  p1: 100000/2=50000.0000   p2: 150000/3=50000.0000   p3: 250000/4=62500.0000
  p4: null (0 deliveries)   p5: null (0 deliveries)    total: 500000/9=55555.5556

Budget values: null (no budget import)
```

---

## Task 1: Add openpyxl to dev dependencies

**Files:**
- Modify: `backend/pyproject.toml`

**Step 1: Edit pyproject.toml**

Add `"openpyxl"` to `[project.optional-dependencies] dev`:

```toml
[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "pytest-cov",
    "ruff",
    "httpx",
    "openpyxl",
]
```

**Step 2: Rebuild Docker image to install the new dependency**

Run: `docker compose build backend`
Expected: build succeeds, `openpyxl` installed

**Step 3: Verify openpyxl is importable**

Run: `docker compose exec backend python -c "import openpyxl; print(openpyxl.__version__)"`
Expected: prints a version string like `3.1.x`

**Step 4: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore(A3): add openpyxl to dev dependencies"
```

---

## Task 2: Write the failing E2E test (RED)

**Files:**
- Create: `backend/tests/integration/__init__.py`
- Create: `backend/tests/integration/test_e2e_calculations.py`

**Step 1: Create the integration test directory**

```bash
touch backend/tests/integration/__init__.py
```

**Step 2: Write the failing test**

Create `backend/tests/integration/test_e2e_calculations.py`:

```python
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
```

**Step 3: Run the tests to verify they pass or fail correctly**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest tests/integration/test_e2e_calculations.py -v`

Expected output:
- `test_fixture_files_exist` — FAIL (fixtures don't exist yet — that's fine, Task 3 creates them)
- `test_golden_file_is_valid_json` — FAIL (no golden file yet)
- `test_golden_file_delivery_counts` — FAIL (no golden file yet)
- `test_golden_file_n12m_has_calculated_rows` — FAIL (no golden file yet)
- `test_golden_file_pnl_net_profit_derivation` — FAIL (no golden file yet)
- `test_e2e_cascade_output_matches_golden_file` — XFAIL (expected)

All failures are expected. Proceed to Task 3.

**Step 4: Commit the RED test**

```bash
git add backend/tests/integration/__init__.py
git add backend/tests/integration/test_e2e_calculations.py
git commit -m "test(A3): RED e2e golden file test — fails until B5"
```

---

## Task 3: Create `build_fixture.py` and generate `sample_import.xlsx`

**Files:**
- Create: `backend/tests/fixtures/build_fixture.py`

**Step 1: Create the fixtures directory**

```bash
mkdir -p backend/tests/fixtures
touch backend/tests/fixtures/__init__.py
```

**Step 2: Write `build_fixture.py`**

Create `backend/tests/fixtures/build_fixture.py`:

```python
"""Generates sample_import.xlsx — the golden file fixture for A3.

Run this script once to regenerate the fixture:
    docker compose exec -e PYTHONPATH=/app backend python tests/fixtures/build_fixture.py

The generated file is committed to the repo. This script is the source of truth
for its contents. If you change the data, regenerate AND update expected_output.json.
"""

from pathlib import Path
import openpyxl

OUTPUT_PATH = Path(__file__).parent / "sample_import.xlsx"

# ──────────────────────────────────────────────
# Data definitions
# ──────────────────────────────────────────────

METADATA = [
    ("report_month", "2025-09-01"),
    ("version_type", "current"),
    ("source_type", "excel"),
    ("actual_flags", "true,true,true"),
    ("n12m_months", "2025-10-01,2025-11-01,2025-12-01"),
]

DELIVERY_COUNTS = [
    ("p1", 2),
    ("p2", 3),
    ("p3", 4),
    ("p4", 0),
    ("p5", 0),
]

# Raw input N12M rows only (is_calculated=false).
# Costs are stored as POSITIVE values (v2 convention).
# Columns: section, line_item, display_name, is_calculated, sort_order, Oct, Nov, Dec
N12M_ROWS = [
    ("revenue",      "gross_revenue",           "Gross Revenue",             False,  1,  60000,  40000,  20000),
    ("revenue",      "sales_costs",             "Selling Costs",             False,  2,   3000,   2000,   1000),
    ("direct_costs", "primary_build",           "Primary Build",             False,  3,  30000,  20000,  10000),
    ("direct_costs", "contingency",             "Contingency",               False,  4,      0,      0,      0),
    ("overheads",    "marketing",               "Marketing",                 False,  5,   1500,   1000,    500),
    ("overheads",    "admin_overheads",         "Admin Overheads",           False,  6,      0,      0,      0),
    ("capex",        "infrastructure",          "Infrastructure",            False,  7,  15000,  10000,   5000),
    ("capex",        "civil_works",             "Civil Works",               False,  8,      0,      0,      0),
    ("capex",        "landscaping",             "Landscaping",               False,  9,      0,      0,      0),
    ("capex",        "amenities",               "Amenities",                 False, 10,      0,      0,      0),
    ("capex",        "professional_fees",       "Professional Fees",         False, 11,   3000,   2000,   1000),
    ("capex",        "regulatory_fees",         "Regulatory Fees",           False, 12,      0,      0,      0),
    ("capex",        "other",                   "Other",                     False, 13,      0,      0,      0),
    ("capex",        "contingency_civil_works", "Contingency Civil Works",   False, 14,      0,      0,      0),
    ("capex",        "contingency_amenities",   "Contingency Amenities",     False, 15,      0,      0,      0),
    ("capex",        "ancillary_build_capex",   "Ancillary Build Capex",     False, 16,      0,      0,      0),
]

# Phase comparison — whole-of-project current values.
# Only non-zero line items are listed; parser fills zeros for unlisted lines.
# Columns: line_item, p1, p2, p3, p4, p5, total
PHASE_COMPARISON_ROWS = [
    ("gross_revenue",    100000, 150000, 250000, 0, 0, 500000),
    ("sales_costs",        5000,   7500,  12500, 0, 0,  25000),
    ("primary_build",     50000,  75000, 125000, 0, 0, 250000),
    ("contingency",           0,      0,      0, 0, 0,      0),
    ("marketing",          5000,   7500,  12500, 0, 0,  25000),
    ("admin_overheads",       0,      0,      0, 0, 0,      0),
    ("infrastructure",    20000,  30000,  50000, 0, 0, 100000),
    ("civil_works",           0,      0,      0, 0, 0,      0),
    ("landscaping",           0,      0,      0, 0, 0,      0),
    ("amenities",             0,      0,      0, 0, 0,      0),
    ("professional_fees", 10000,  15000,  25000, 0, 0,  50000),
    ("regulatory_fees",       0,      0,      0, 0, 0,      0),
    ("other",                 0,      0,      0, 0, 0,      0),
    ("contingency_civil_works", 0, 0,    0, 0, 0,      0),
    ("contingency_amenities",   0, 0,    0, 0, 0,      0),
    ("ancillary_build_capex",   0, 0,    0, 0, 0,      0),
]


# ──────────────────────────────────────────────
# Build workbook
# ──────────────────────────────────────────────

def build():
    wb = openpyxl.Workbook()

    # Sheet 1: metadata
    ws = wb.active
    ws.title = "metadata"
    ws.append(["key", "value"])
    for row in METADATA:
        ws.append(list(row))

    # Sheet 2: delivery_counts
    ws = wb.create_sheet("delivery_counts")
    ws.append(["phase", "count"])
    for row in DELIVERY_COUNTS:
        ws.append(list(row))

    # Sheet 3: n12m
    ws = wb.create_sheet("n12m")
    ws.append([
        "section", "line_item", "display_name", "is_calculated", "sort_order",
        "2025-10-01", "2025-11-01", "2025-12-01",
    ])
    for row in N12M_ROWS:
        ws.append(list(row))

    # Sheet 4: phase_comparison (current values only; budget from linked import)
    ws = wb.create_sheet("phase_comparison")
    ws.append(["line_item", "p1", "p2", "p3", "p4", "p5", "total"])
    for row in PHASE_COMPARISON_ROWS:
        ws.append(list(row))

    wb.save(OUTPUT_PATH)
    print(f"Written: {OUTPUT_PATH}")


if __name__ == "__main__":
    build()
```

**Step 3: Run the script inside Docker**

Run: `docker compose exec -e PYTHONPATH=/app backend python tests/fixtures/build_fixture.py`
Expected: `Written: /app/tests/fixtures/sample_import.xlsx`

**Step 4: Verify the file was created**

Run: `docker compose exec backend python -c "import openpyxl; wb=openpyxl.load_workbook('/app/tests/fixtures/sample_import.xlsx'); print(wb.sheetnames)"`
Expected: `['metadata', 'delivery_counts', 'n12m', 'phase_comparison']`

**Step 5: Run fixture tests to check they now pass**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest tests/integration/test_e2e_calculations.py::test_fixture_files_exist -v`
Expected: this test still FAILs because `expected_output.json` is missing. That's correct — proceed to Task 4.

**Step 6: Commit**

```bash
git add backend/tests/fixtures/__init__.py
git add backend/tests/fixtures/build_fixture.py
git add backend/tests/fixtures/sample_import.xlsx
git commit -m "test(A3): golden file Excel fixture — sample_import.xlsx"
```

---

## Task 4: Create `expected_output.json`

**Files:**
- Create: `backend/tests/fixtures/expected_output.json`

**Step 1: Create the file**

Create `backend/tests/fixtures/expected_output.json` with the content below.

All monetary values are strings in `NUMERIC(18,4)` format. Integer counts are JSON numbers. Null means no budget import is linked.

```json
{
  "import_meta": {
    "name": "sample_import",
    "version_type": "current",
    "source_type": "excel",
    "report_month": "2025-09-01"
  },
  "delivery_counts": [
    {"phase": "p1", "count": 2},
    {"phase": "p2", "count": 3},
    {"phase": "p3", "count": 4},
    {"phase": "p4", "count": 0},
    {"phase": "p5", "count": 0}
  ],
  "n12m_line_items": [
    {
      "section": "revenue", "line_item": "gross_revenue",
      "display_name": "Gross Revenue", "is_calculated": false, "sort_order": 1,
      "entries": [
        {"month": "2025-10-01", "value": "60000.0000"},
        {"month": "2025-11-01", "value": "40000.0000"},
        {"month": "2025-12-01", "value": "20000.0000"}
      ]
    },
    {
      "section": "revenue", "line_item": "sales_costs",
      "display_name": "Selling Costs", "is_calculated": false, "sort_order": 2,
      "entries": [
        {"month": "2025-10-01", "value": "3000.0000"},
        {"month": "2025-11-01", "value": "2000.0000"},
        {"month": "2025-12-01", "value": "1000.0000"}
      ]
    },
    {
      "section": "direct_costs", "line_item": "primary_build",
      "display_name": "Primary Build", "is_calculated": false, "sort_order": 3,
      "entries": [
        {"month": "2025-10-01", "value": "30000.0000"},
        {"month": "2025-11-01", "value": "20000.0000"},
        {"month": "2025-12-01", "value": "10000.0000"}
      ]
    },
    {
      "section": "direct_costs", "line_item": "contingency",
      "display_name": "Contingency", "is_calculated": false, "sort_order": 4,
      "entries": [
        {"month": "2025-10-01", "value": "0.0000"},
        {"month": "2025-11-01", "value": "0.0000"},
        {"month": "2025-12-01", "value": "0.0000"}
      ]
    },
    {
      "section": "overheads", "line_item": "marketing",
      "display_name": "Marketing", "is_calculated": false, "sort_order": 5,
      "entries": [
        {"month": "2025-10-01", "value": "1500.0000"},
        {"month": "2025-11-01", "value": "1000.0000"},
        {"month": "2025-12-01", "value": "500.0000"}
      ]
    },
    {
      "section": "overheads", "line_item": "admin_overheads",
      "display_name": "Admin Overheads", "is_calculated": false, "sort_order": 6,
      "entries": [
        {"month": "2025-10-01", "value": "0.0000"},
        {"month": "2025-11-01", "value": "0.0000"},
        {"month": "2025-12-01", "value": "0.0000"}
      ]
    },
    {
      "section": "capex", "line_item": "infrastructure",
      "display_name": "Infrastructure", "is_calculated": false, "sort_order": 7,
      "entries": [
        {"month": "2025-10-01", "value": "15000.0000"},
        {"month": "2025-11-01", "value": "10000.0000"},
        {"month": "2025-12-01", "value": "5000.0000"}
      ]
    },
    {
      "section": "capex", "line_item": "civil_works",
      "display_name": "Civil Works", "is_calculated": false, "sort_order": 8,
      "entries": [
        {"month": "2025-10-01", "value": "0.0000"},
        {"month": "2025-11-01", "value": "0.0000"},
        {"month": "2025-12-01", "value": "0.0000"}
      ]
    },
    {
      "section": "capex", "line_item": "landscaping",
      "display_name": "Landscaping", "is_calculated": false, "sort_order": 9,
      "entries": [
        {"month": "2025-10-01", "value": "0.0000"},
        {"month": "2025-11-01", "value": "0.0000"},
        {"month": "2025-12-01", "value": "0.0000"}
      ]
    },
    {
      "section": "capex", "line_item": "amenities",
      "display_name": "Amenities", "is_calculated": false, "sort_order": 10,
      "entries": [
        {"month": "2025-10-01", "value": "0.0000"},
        {"month": "2025-11-01", "value": "0.0000"},
        {"month": "2025-12-01", "value": "0.0000"}
      ]
    },
    {
      "section": "capex", "line_item": "professional_fees",
      "display_name": "Professional Fees", "is_calculated": false, "sort_order": 11,
      "entries": [
        {"month": "2025-10-01", "value": "3000.0000"},
        {"month": "2025-11-01", "value": "2000.0000"},
        {"month": "2025-12-01", "value": "1000.0000"}
      ]
    },
    {
      "section": "capex", "line_item": "regulatory_fees",
      "display_name": "Regulatory Fees", "is_calculated": false, "sort_order": 12,
      "entries": [
        {"month": "2025-10-01", "value": "0.0000"},
        {"month": "2025-11-01", "value": "0.0000"},
        {"month": "2025-12-01", "value": "0.0000"}
      ]
    },
    {
      "section": "capex", "line_item": "other",
      "display_name": "Other", "is_calculated": false, "sort_order": 13,
      "entries": [
        {"month": "2025-10-01", "value": "0.0000"},
        {"month": "2025-11-01", "value": "0.0000"},
        {"month": "2025-12-01", "value": "0.0000"}
      ]
    },
    {
      "section": "capex", "line_item": "contingency_civil_works",
      "display_name": "Contingency Civil Works", "is_calculated": false, "sort_order": 14,
      "entries": [
        {"month": "2025-10-01", "value": "0.0000"},
        {"month": "2025-11-01", "value": "0.0000"},
        {"month": "2025-12-01", "value": "0.0000"}
      ]
    },
    {
      "section": "capex", "line_item": "contingency_amenities",
      "display_name": "Contingency Amenities", "is_calculated": false, "sort_order": 15,
      "entries": [
        {"month": "2025-10-01", "value": "0.0000"},
        {"month": "2025-11-01", "value": "0.0000"},
        {"month": "2025-12-01", "value": "0.0000"}
      ]
    },
    {
      "section": "capex", "line_item": "ancillary_build_capex",
      "display_name": "Ancillary Build Capex", "is_calculated": false, "sort_order": 16,
      "entries": [
        {"month": "2025-10-01", "value": "0.0000"},
        {"month": "2025-11-01", "value": "0.0000"},
        {"month": "2025-12-01", "value": "0.0000"}
      ]
    },
    {
      "section": "revenue", "line_item": "net_revenue",
      "display_name": "Net Revenue", "is_calculated": true, "sort_order": 17,
      "entries": [
        {"month": "2025-10-01", "value": "57000.0000"},
        {"month": "2025-11-01", "value": "38000.0000"},
        {"month": "2025-12-01", "value": "19000.0000"}
      ]
    },
    {
      "section": "direct_costs", "line_item": "subtotal_direct_cost",
      "display_name": "Subtotal Direct Cost", "is_calculated": true, "sort_order": 18,
      "entries": [
        {"month": "2025-10-01", "value": "30000.0000"},
        {"month": "2025-11-01", "value": "20000.0000"},
        {"month": "2025-12-01", "value": "10000.0000"}
      ]
    },
    {
      "section": "overheads", "line_item": "subtotal_overheads",
      "display_name": "Subtotal Overheads", "is_calculated": true, "sort_order": 19,
      "entries": [
        {"month": "2025-10-01", "value": "1500.0000"},
        {"month": "2025-11-01", "value": "1000.0000"},
        {"month": "2025-12-01", "value": "500.0000"}
      ]
    },
    {
      "section": "overheads", "line_item": "gross_cash_flow",
      "display_name": "Gross Cash Flow", "is_calculated": true, "sort_order": 20,
      "entries": [
        {"month": "2025-10-01", "value": "25500.0000"},
        {"month": "2025-11-01", "value": "17000.0000"},
        {"month": "2025-12-01", "value": "8500.0000"}
      ]
    },
    {
      "section": "capex", "line_item": "subtotal_capex",
      "display_name": "Subtotal Capex", "is_calculated": true, "sort_order": 21,
      "entries": [
        {"month": "2025-10-01", "value": "18000.0000"},
        {"month": "2025-11-01", "value": "12000.0000"},
        {"month": "2025-12-01", "value": "6000.0000"}
      ]
    },
    {
      "section": "capex", "line_item": "net_cash_flow",
      "display_name": "Net Cash Flow", "is_calculated": true, "sort_order": 22,
      "entries": [
        {"month": "2025-10-01", "value": "7500.0000"},
        {"month": "2025-11-01", "value": "5000.0000"},
        {"month": "2025-12-01", "value": "2500.0000"}
      ]
    }
  ],
  "phase_comparison_rows": [
    {"line_item": "gross_revenue",    "phase": "p1",    "budget": null, "current": "100000.0000", "delta": null, "delta_pct": null},
    {"line_item": "gross_revenue",    "phase": "p2",    "budget": null, "current": "150000.0000", "delta": null, "delta_pct": null},
    {"line_item": "gross_revenue",    "phase": "p3",    "budget": null, "current": "250000.0000", "delta": null, "delta_pct": null},
    {"line_item": "gross_revenue",    "phase": "p4",    "budget": null, "current": "0.0000",      "delta": null, "delta_pct": null},
    {"line_item": "gross_revenue",    "phase": "p5",    "budget": null, "current": "0.0000",      "delta": null, "delta_pct": null},
    {"line_item": "gross_revenue",    "phase": "total", "budget": null, "current": "500000.0000", "delta": null, "delta_pct": null},
    {"line_item": "sales_costs",      "phase": "p1",    "budget": null, "current": "5000.0000",   "delta": null, "delta_pct": null},
    {"line_item": "sales_costs",      "phase": "p2",    "budget": null, "current": "7500.0000",   "delta": null, "delta_pct": null},
    {"line_item": "sales_costs",      "phase": "p3",    "budget": null, "current": "12500.0000",  "delta": null, "delta_pct": null},
    {"line_item": "sales_costs",      "phase": "p4",    "budget": null, "current": "0.0000",      "delta": null, "delta_pct": null},
    {"line_item": "sales_costs",      "phase": "p5",    "budget": null, "current": "0.0000",      "delta": null, "delta_pct": null},
    {"line_item": "sales_costs",      "phase": "total", "budget": null, "current": "25000.0000",  "delta": null, "delta_pct": null},
    {"line_item": "primary_build",    "phase": "p1",    "budget": null, "current": "50000.0000",  "delta": null, "delta_pct": null},
    {"line_item": "primary_build",    "phase": "p2",    "budget": null, "current": "75000.0000",  "delta": null, "delta_pct": null},
    {"line_item": "primary_build",    "phase": "p3",    "budget": null, "current": "125000.0000", "delta": null, "delta_pct": null},
    {"line_item": "primary_build",    "phase": "p4",    "budget": null, "current": "0.0000",      "delta": null, "delta_pct": null},
    {"line_item": "primary_build",    "phase": "p5",    "budget": null, "current": "0.0000",      "delta": null, "delta_pct": null},
    {"line_item": "primary_build",    "phase": "total", "budget": null, "current": "250000.0000", "delta": null, "delta_pct": null},
    {"line_item": "marketing",        "phase": "p1",    "budget": null, "current": "5000.0000",   "delta": null, "delta_pct": null},
    {"line_item": "marketing",        "phase": "p2",    "budget": null, "current": "7500.0000",   "delta": null, "delta_pct": null},
    {"line_item": "marketing",        "phase": "p3",    "budget": null, "current": "12500.0000",  "delta": null, "delta_pct": null},
    {"line_item": "marketing",        "phase": "p4",    "budget": null, "current": "0.0000",      "delta": null, "delta_pct": null},
    {"line_item": "marketing",        "phase": "p5",    "budget": null, "current": "0.0000",      "delta": null, "delta_pct": null},
    {"line_item": "marketing",        "phase": "total", "budget": null, "current": "25000.0000",  "delta": null, "delta_pct": null},
    {"line_item": "infrastructure",   "phase": "p1",    "budget": null, "current": "20000.0000",  "delta": null, "delta_pct": null},
    {"line_item": "infrastructure",   "phase": "p2",    "budget": null, "current": "30000.0000",  "delta": null, "delta_pct": null},
    {"line_item": "infrastructure",   "phase": "p3",    "budget": null, "current": "50000.0000",  "delta": null, "delta_pct": null},
    {"line_item": "infrastructure",   "phase": "p4",    "budget": null, "current": "0.0000",      "delta": null, "delta_pct": null},
    {"line_item": "infrastructure",   "phase": "p5",    "budget": null, "current": "0.0000",      "delta": null, "delta_pct": null},
    {"line_item": "infrastructure",   "phase": "total", "budget": null, "current": "100000.0000", "delta": null, "delta_pct": null},
    {"line_item": "professional_fees","phase": "p1",    "budget": null, "current": "10000.0000",  "delta": null, "delta_pct": null},
    {"line_item": "professional_fees","phase": "p2",    "budget": null, "current": "15000.0000",  "delta": null, "delta_pct": null},
    {"line_item": "professional_fees","phase": "p3",    "budget": null, "current": "25000.0000",  "delta": null, "delta_pct": null},
    {"line_item": "professional_fees","phase": "p4",    "budget": null, "current": "0.0000",      "delta": null, "delta_pct": null},
    {"line_item": "professional_fees","phase": "p5",    "budget": null, "current": "0.0000",      "delta": null, "delta_pct": null},
    {"line_item": "professional_fees","phase": "total", "budget": null, "current": "50000.0000",  "delta": null, "delta_pct": null}
  ],
  "per_delivery_rows": [
    {"line_item": "gross_revenue",  "phase": "p1",    "budget": null, "current": "50000.0000",  "delta": null, "delta_pct": null},
    {"line_item": "gross_revenue",  "phase": "p2",    "budget": null, "current": "50000.0000",  "delta": null, "delta_pct": null},
    {"line_item": "gross_revenue",  "phase": "p3",    "budget": null, "current": "62500.0000",  "delta": null, "delta_pct": null},
    {"line_item": "gross_revenue",  "phase": "p4",    "budget": null, "current": null,           "delta": null, "delta_pct": null},
    {"line_item": "gross_revenue",  "phase": "p5",    "budget": null, "current": null,           "delta": null, "delta_pct": null},
    {"line_item": "gross_revenue",  "phase": "total", "budget": null, "current": "55555.5556",  "delta": null, "delta_pct": null}
  ],
  "pnl_summaries": [
    {
      "line_item": "deliveries", "sort_order": 1,
      "budget_total": null, "current_total": "9.0000",
      "delta_total": null,
      "budget_rate": null, "current_rate": null, "delta_rate": null
    },
    {
      "line_item": "revenue", "sort_order": 2,
      "budget_total": null, "current_total": "120000.0000",
      "delta_total": null,
      "budget_rate": null, "current_rate": "13333.3333", "delta_rate": null
    },
    {
      "line_item": "cogs", "sort_order": 3,
      "budget_total": null, "current_total": "-60000.0000",
      "delta_total": null,
      "budget_rate": null, "current_rate": "-6666.6667", "delta_rate": null
    },
    {
      "line_item": "gross_profit", "sort_order": 4,
      "budget_total": null, "current_total": "60000.0000",
      "delta_total": null,
      "budget_rate": null, "current_rate": "6666.6667", "delta_rate": null
    },
    {
      "line_item": "sales_and_marketing", "sort_order": 5,
      "budget_total": null, "current_total": "-9000.0000",
      "delta_total": null,
      "budget_rate": null, "current_rate": "-1000.0000", "delta_rate": null
    },
    {
      "line_item": "direct_costs", "sort_order": 6,
      "budget_total": null, "current_total": "-36000.0000",
      "delta_total": null,
      "budget_rate": null, "current_rate": "-4000.0000", "delta_rate": null
    },
    {
      "line_item": "net_profit", "sort_order": 7,
      "budget_total": null, "current_total": "15000.0000",
      "delta_total": null,
      "budget_rate": null, "current_rate": "1666.6667", "delta_rate": null
    }
  ],
  "ncf_series": [
    {"series_type": "periodic",    "series_name": "current", "month": "2025-10-01", "value": "7500.0000"},
    {"series_type": "periodic",    "series_name": "current", "month": "2025-11-01", "value": "5000.0000"},
    {"series_type": "periodic",    "series_name": "current", "month": "2025-12-01", "value": "2500.0000"},
    {"series_type": "cumulative",  "series_name": "current", "month": "2025-10-01", "value": "7500.0000"},
    {"series_type": "cumulative",  "series_name": "current", "month": "2025-11-01", "value": "12500.0000"},
    {"series_type": "cumulative",  "series_name": "current", "month": "2025-12-01", "value": "15000.0000"}
  ]
}
```

**Step 2: Manually verify the key derivations against the Data Design section**

Check these before committing:
- [ ] net_revenue(Oct) = gross_revenue(60000) - sales_costs(3000) = 57000 ✓
- [ ] gross_cash_flow(Oct) = net_revenue(57000) - subtotal_direct_cost(30000) - subtotal_overheads(1500) = 25500 ✓
- [ ] net_cash_flow(Oct) = gross_cash_flow(25500) - subtotal_capex(18000) = 7500 ✓
- [ ] NCF cumulative(Nov) = 7500 + 5000 = 12500 ✓
- [ ] P&L revenue = N12M gross_revenue sum = 60000+40000+20000 = 120000 ✓
- [ ] P&L cogs = -(N12M subtotal_direct_cost sum) = -(60000) = -60000 ✓
- [ ] P&L gross_profit = 120000 + (-60000) = 60000 ✓
- [ ] P&L sales_and_marketing = -(sales_costs_sum + marketing_sum) = -(6000+3000) = -9000 ✓
- [ ] P&L direct_costs = -(subtotal_capex_sum) = -(36000) = -36000 ✓
- [ ] P&L net_profit = 60000 + (-9000) + (-36000) = 15000 ✓
- [ ] per_delivery gross_revenue p1 = 100000 / 2 = 50000 ✓
- [ ] per_delivery gross_revenue total = 500000 / 9 = 55555.5556 ✓

**Step 3: Run all integration tests**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest tests/integration/ -v`

Expected:
- `test_fixture_files_exist` — PASS
- `test_golden_file_is_valid_json` — PASS
- `test_golden_file_delivery_counts` — PASS
- `test_golden_file_n12m_has_calculated_rows` — PASS
- `test_golden_file_pnl_net_profit_derivation` — PASS
- `test_e2e_cascade_output_matches_golden_file` — XFAIL (expected — no service code)

**Step 4: Run full test suite to confirm no regressions**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest --tb=short`
Expected: all existing tests pass, new integration tests show as above

**Step 5: Commit**

```bash
git add backend/tests/fixtures/expected_output.json
git commit -m "test(A3): golden file expected_output.json — cascade contract locked"
```

---

## Task 5: Verify final state

**Step 1: Run the full test suite one more time**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest --tb=short -v`

Expected summary:
- All A1 health tests: PASS
- All A2 domain tests: PASS (or SKIP if DB not available)
- `test_fixture_files_exist`: PASS
- `test_golden_file_is_valid_json`: PASS
- `test_golden_file_delivery_counts`: PASS
- `test_golden_file_n12m_has_calculated_rows`: PASS
- `test_golden_file_pnl_net_profit_derivation`: PASS
- `test_e2e_cascade_output_matches_golden_file`: XFAIL

**Step 2: Confirm the XFAIL is strict**

The `xfail(strict=True)` means if `test_e2e_cascade_output_matches_golden_file` accidentally passes, the test run fails. This protects against accidentally implementing the service before the RED phase is confirmed.

**Step 3: Tag A3 complete**

```bash
git tag a3-golden-file-fixture
git push origin main --tags
```

---

## What A3 Does NOT Include

These are B-phase concerns:
- The Excel parser that reads `sample_import.xlsx` (B2)
- The DB migrations for cascade output tables (B1)
- The cascade service that produces the golden file output (B4)
- Making `test_e2e_cascade_output_matches_golden_file` pass (B5)

A3 is complete when:
1. `sample_import.xlsx` is committed
2. `expected_output.json` is committed with manually verified values
3. The five structural integration tests pass
4. `test_e2e_cascade_output_matches_golden_file` is XFAIL (strict)
