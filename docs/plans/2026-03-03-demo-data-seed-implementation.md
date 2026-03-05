# Demo Data Seed System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a reusable API-driven seed script that wipes the database and injects realistic demo data with correct calculations for customer presentations.

**Architecture:** A Python script on the host calls the backend REST API to create 3 linked imports (budget, previous, current), populate each with generated phase-level data, and let the cascade engine compute all derived fields. A JSON profile file configures the data shape per customer.

**Tech Stack:** Python 3 (requests library), JSON config files, FastAPI backend API

---

## Prerequisites

The current `/latest` endpoints (n12m, ncf, summary, phases, pnl) only query `source_type == "excel"` imports. Manual imports created via the data-entry API have `source_type == "manual"` and **will not appear** in the main Dashboard, Forecast, NCF, P&L, or Phase tabs. We need a small backend change first.

---

### Task 1: Extend data-entry create endpoint to accept source_type and actual_flags

**Files:**
- Modify: `backend/app/schemas/data_entry_schemas.py:8-12` (CreateManualImport)
- Modify: `backend/app/api/v1/data_entry.py:42-90` (create_manual_import handler)
- Test: `backend/tests/test_api_data_entry.py`

**Step 1: Write the failing test**

Add a test to `backend/tests/test_api_data_entry.py`:

```python
async def test_create_import_with_source_type(client, db_session):
    """Creating an import with source_type='excel' should set it on the record."""
    resp = await client.post("/api/v1/data-entry/imports", json={
        "report_month": "2026-03-01",
        "version_type": "current",
        "source_type": "excel",
        "actual_flags": [True, True, True, False, False, False, False, False, False, False, False, False],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_type"] == "excel"
```

**Step 2: Run test to verify it fails**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest tests/test_api_data_entry.py::test_create_import_with_source_type -v --tb=short`
Expected: FAIL (source_type field not accepted / still returns "manual")

**Step 3: Implement the change**

In `backend/app/schemas/data_entry_schemas.py`, add two optional fields to `CreateManualImport`:

```python
class CreateManualImport(BaseModel):
    report_month: date
    version_type: str  # "budget" | "previous" | "current"
    budget_import_id: UUID | None = None
    previous_import_id: UUID | None = None
    source_type: str = "manual"  # "manual" or "excel"
    actual_flags: list[bool] | None = None
```

In `backend/app/api/v1/data_entry.py`, use the new fields in `create_manual_import`:

Change line 56 from:
```python
        source_type="manual",
```
to:
```python
        source_type=body.source_type,
        actual_flags=body.actual_flags,
```

**Step 4: Run test to verify it passes**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest tests/test_api_data_entry.py -v --tb=short`
Expected: ALL PASS

**Step 5: Run full backend tests to verify no regressions**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest --tb=short`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add backend/app/schemas/data_entry_schemas.py backend/app/api/v1/data_entry.py backend/tests/test_api_data_entry.py
git commit -m "feat: accept source_type and actual_flags in data-entry create endpoint"
```

---

### Task 2: Create the default demo profile JSON

**Files:**
- Create: `scripts/demo_profiles/default.json`

**Step 1: Create directory and profile file**

```bash
mkdir -p scripts/demo_profiles
```

Write `scripts/demo_profiles/default.json`:

```json
{
  "project_name": "Demo Project",
  "report_month": "2026-03-01",
  "months_start": "2026-03-01",
  "delivery_counts": { "p1": 45, "p2": 60, "p3": 80, "p4": 55, "p5": 30 },
  "actual_months": 3,
  "base_values": {
    "gross_revenue":           { "monthly_range": [800000, 1500000] },
    "sales_costs":             { "monthly_range": [40000, 80000] },
    "primary_build":           { "monthly_range": [300000, 600000] },
    "contingency":             { "monthly_range": [20000, 50000] },
    "marketing":               { "monthly_range": [15000, 35000] },
    "admin_overheads":         { "monthly_range": [25000, 45000] },
    "infrastructure":          { "monthly_range": [50000, 120000] },
    "civil_works":             { "monthly_range": [80000, 200000] },
    "landscaping":             { "monthly_range": [10000, 30000] },
    "amenities":               { "monthly_range": [20000, 60000] },
    "professional_fees":       { "monthly_range": [15000, 40000] },
    "regulatory_fees":         { "monthly_range": [5000, 15000] },
    "other":                   { "monthly_range": [5000, 20000] },
    "contingency_civil_works": { "monthly_range": [8000, 25000] },
    "contingency_amenities":   { "monthly_range": [5000, 15000] },
    "ancillary_build_capex":   { "monthly_range": [10000, 30000] },
    "deliveries":              { "monthly_range": [3, 15] }
  },
  "phase_weights": { "p1": 0.30, "p2": 0.25, "p3": 0.20, "p4": 0.15, "p5": 0.10 },
  "budget_variance_pct": 0.05,
  "previous_variance_pct": 0.02
}
```

**Step 2: Commit**

```bash
git add scripts/demo_profiles/default.json
git commit -m "feat: add default demo profile for seed script"
```

---

### Task 3: Create the seed script — data generation module

**Files:**
- Create: `scripts/seed_demo.py`

This task creates the complete seed script. The script has four logical sections:
1. Profile loading + CLI args
2. Data generation (random values per phase/month)
3. API calls (wipe, create imports, populate grids, set deliveries)
4. Verification (fetch summary + pnl, print key metrics)

**Step 1: Write the seed script**

Create `scripts/seed_demo.py`:

```python
#!/usr/bin/env python3
"""
Demo data seed script.

Wipes the database and injects realistic demo data via the backend API.
All calculated fields are computed by the server-side cascade engine.

Usage:
    python scripts/seed_demo.py
    python scripts/seed_demo.py --profile scripts/demo_profiles/customer_a.json
    python scripts/seed_demo.py --api-url http://localhost:8000/api/v1
"""

import argparse
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

DEFAULT_PROFILE = Path(__file__).parent / "demo_profiles" / "default.json"
DEFAULT_API_URL = "http://localhost:8000/api/v1"

# The 17 editable (non-calculated) line items that the seed script populates.
# Calculated fields (net_revenue, subtotal_direct_cost, subtotal_overheads,
# gross_cash_flow, subtotal_capex, net_cash_flow) are computed by the cascade.
EDITABLE_LINE_ITEMS = [
    "deliveries",
    "gross_revenue",
    "sales_costs",
    "primary_build",
    "contingency",
    "marketing",
    "admin_overheads",
    "infrastructure",
    "civil_works",
    "landscaping",
    "amenities",
    "professional_fees",
    "regulatory_fees",
    "other",
    "contingency_civil_works",
    "contingency_amenities",
    "ancillary_build_capex",
]

PHASES = ["p1", "p2", "p3", "p4", "p5"]


def load_profile(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def generate_months(start: str, count: int = 12) -> list[str]:
    """Generate 12 month dates as ISO strings (YYYY-MM-DD), first of each month."""
    d = date.fromisoformat(start)
    months = []
    for i in range(count):
        y = d.year + (d.month - 1 + i) // 12
        m = (d.month - 1 + i) % 12 + 1
        months.append(date(y, m, 1).isoformat())
    return months


def generate_grid_values(
    profile: dict,
    months: list[str],
    version_scale: float = 1.0,
) -> list[dict]:
    """
    Generate cell values for all editable line items × phases × months.

    Returns a list of dicts ready for the BulkSaveRequest API:
        [{"phase": "p1", "line_item": "gross_revenue", "month": "2026-03-01", "value": 123456.78}, ...]
    """
    base_values = profile["base_values"]
    phase_weights = profile["phase_weights"]
    cells = []

    for line_item in EDITABLE_LINE_ITEMS:
        if line_item not in base_values:
            continue
        lo, hi = base_values[line_item]["monthly_range"]

        for month in months:
            # Generate one base value per month, then split across phases
            base = random.uniform(lo, hi)

            for phase in PHASES:
                weight = phase_weights.get(phase, 0.2)
                value = base * weight * version_scale

                # Deliveries should be integers
                if line_item == "deliveries":
                    value = max(0, round(value))
                else:
                    value = round(value, 2)

                cells.append({
                    "phase": phase,
                    "line_item": line_item,
                    "month": month,
                    "value": value,
                })

    return cells


def api_call(method: str, url: str, **kwargs) -> requests.Response:
    """Make an API call and raise on error."""
    resp = requests.request(method, url, **kwargs)
    if resp.status_code >= 400:
        print(f"  ERROR {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp


def wipe_database(api_url: str):
    print("Step 1: Wiping all existing data...")
    resp = api_call("DELETE", f"{api_url}/imports")
    print(f"  {resp.json().get('detail', 'Done')}")


def create_import(
    api_url: str,
    profile: dict,
    version_type: str,
    budget_import_id: str | None = None,
    previous_import_id: str | None = None,
) -> str:
    """Create an import and return its ID."""
    actual_flags = (
        [True] * profile["actual_months"]
        + [False] * (12 - profile["actual_months"])
    )
    body = {
        "report_month": profile["report_month"],
        "version_type": version_type,
        "source_type": "excel",
        "actual_flags": actual_flags,
    }
    if budget_import_id:
        body["budget_import_id"] = budget_import_id
    if previous_import_id:
        body["previous_import_id"] = previous_import_id

    resp = api_call("POST", f"{api_url}/data-entry/imports", json=body)
    import_id = resp.json()["id"]
    print(f"  Created {version_type} import: {import_id}")
    return import_id


def populate_grid(api_url: str, import_id: str, cells: list[dict]):
    """Bulk-save grid cells for an import. Triggers cascade recalculation."""
    print(f"  Populating grid ({len(cells)} cells)...")
    api_call("PUT", f"{api_url}/data-entry/imports/{import_id}/grid", json={"values": cells})
    print("  Grid saved + cascade complete.")


def set_deliveries(api_url: str, import_id: str, delivery_counts: dict):
    """Set delivery counts per phase."""
    print(f"  Setting delivery counts: {delivery_counts}")
    api_call("PUT", f"{api_url}/data-entry/imports/{import_id}/deliveries", json={"counts": delivery_counts})
    print("  Deliveries saved + cascade complete.")


def seed_version(
    api_url: str,
    profile: dict,
    months: list[str],
    version_type: str,
    version_scale: float,
    budget_import_id: str | None = None,
    previous_import_id: str | None = None,
) -> str:
    """Create an import, populate its grid, and set deliveries. Returns the import ID."""
    print(f"\nStep: Seeding {version_type} import...")
    import_id = create_import(
        api_url, profile, version_type,
        budget_import_id=budget_import_id,
        previous_import_id=previous_import_id,
    )
    cells = generate_grid_values(profile, months, version_scale=version_scale)
    populate_grid(api_url, import_id, cells)
    set_deliveries(api_url, import_id, profile["delivery_counts"])
    return import_id


def verify(api_url: str, import_id: str):
    """Fetch summary and P&L for the current import and print key metrics."""
    print("\nStep: Verifying seeded data...")

    # Use ?import_id= to verify specific import
    resp = api_call("GET", f"{api_url}/n12m", params={"import_id": import_id})
    n12m = resp.json()
    print(f"  N12M months: {n12m['months']}")
    print(f"  Actual flags: {n12m.get('actual_flags', [])}")

    # Count populated sections
    sections = n12m.get("sections", {})
    for sec_name, sec_data in sections.items():
        items = sec_data.get("items", [])
        print(f"  Section '{sec_name}': {len(items)} line items")

    resp = api_call("GET", f"{api_url}/summary", params={"import_id": import_id})
    summary = resp.json()
    total_items = summary.get("total", {}).get("items", [])
    print(f"\n  Summary (total scope):")
    for item in total_items:
        name = item["line_item"]
        current = item.get("total_current")
        budget_delta = item.get("delta_budget_dollar")
        if current is not None:
            print(f"    {name}: ${current:,.2f}" + (f" (vs budget: ${budget_delta:+,.2f})" if budget_delta else ""))

    resp = api_call("GET", f"{api_url}/pnl", params={"import_id": import_id})
    pnl = resp.json()
    print(f"\n  P&L:")
    for item in pnl.get("items", []):
        name = item["line_item"]
        current = item.get("current_total")
        if current is not None:
            print(f"    {name}: ${current:,.2f}")

    print("\nSeed complete! Open the app to verify visually.")


def main():
    parser = argparse.ArgumentParser(description="Seed demo data via the backend API")
    parser.add_argument(
        "--profile",
        default=str(DEFAULT_PROFILE),
        help=f"Path to JSON profile (default: {DEFAULT_PROFILE})",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"Backend API base URL (default: {DEFAULT_API_URL})",
    )
    args = parser.parse_args()

    profile = load_profile(args.profile)
    print(f"Profile: {profile['project_name']}")
    print(f"API: {args.api_url}")

    months = generate_months(profile["months_start"])

    # Step 1: Wipe
    wipe_database(args.api_url)

    # Step 2-4: Budget
    budget_id = seed_version(
        args.api_url, profile, months,
        version_type="budget",
        version_scale=1.0 + profile["budget_variance_pct"],
    )

    # Step 5: Previous
    previous_id = seed_version(
        args.api_url, profile, months,
        version_type="previous",
        version_scale=1.0 - profile["previous_variance_pct"],
    )

    # Step 6: Current (linked to budget + previous)
    current_id = seed_version(
        args.api_url, profile, months,
        version_type="current",
        version_scale=1.0,
        budget_import_id=budget_id,
        previous_import_id=previous_id,
    )

    # Step 7: Verify
    verify(args.api_url, current_id)


if __name__ == "__main__":
    main()
```

**Step 2: Verify the script runs successfully**

Run: `python scripts/seed_demo.py`

Expected output: Script prints progress for each step, ending with summary and P&L metrics. No errors.

**Step 3: Visually verify in browser**

Open `http://localhost:5173` and check:
- Dashboard tab shows summary cards with values and deltas
- Forecast tab shows 12 months of data across all sections
- Phase Comparison tab shows budget vs current with deltas
- P&L tab shows Revenue, COGS, Gross Profit, Net Profit
- Data Entry tab shows the grid with editable and calculated values

**Step 4: Commit**

```bash
git add scripts/seed_demo.py
git commit -m "feat: add API-driven demo data seed script with JSON profiles"
```

---

### Task 4: End-to-end verification — run seed and check all tabs

This is a manual verification task. After Tasks 1-3 are implemented:

**Step 1: Ensure Docker stack is running**

Run: `docker compose up -d`
Wait for: `docker compose exec backend curl -s http://localhost:8000/health` returns OK

**Step 2: Restart backend (to pick up schema changes from Task 1)**

Run: `docker compose restart backend`

**Step 3: Run the seed script**

Run: `python scripts/seed_demo.py`

Expected: Script completes without errors, prints summary metrics.

**Step 4: Verify each frontend tab**

Open `http://localhost:5173` and verify:

1. **Dashboard**: Net Revenue, Gross Cash Flow stats populated. Import picker shows the current import.
2. **Forecast**: 12-month grid with all sections populated. Calculated rows (Net Revenue, Subtotal Direct Cost, etc.) show correct values.
3. **Phase Comparison**: Budget and Current columns populated for all 5 phases. Delta columns show ~5% variance.
4. **P&L**: Revenue, COGS, Gross Profit, Net Profit rows populated with budget/current/delta columns.
5. **Data Entry**: Grid loads with editable cells and calculated cells. Editing a cell triggers cascade and updates calculated fields.

**Step 5: Verify formula correctness (spot check)**

Pick any month in the Forecast tab:
- `Net Revenue` should equal `Gross Revenue - Sales Costs`
- `Subtotal Direct Cost` should equal `Primary Build + Contingency`
- `Gross Cash Flow` should equal `Net Revenue - Subtotal Direct Cost - Subtotal Overheads`
- `Net Cash Flow` should equal `Gross Cash Flow - Subtotal Capex`

**Step 6: Run seed again to verify idempotency**

Run: `python scripts/seed_demo.py`

Expected: Wipes previous data, seeds fresh data, no errors.
