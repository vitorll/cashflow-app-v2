# Demo Data Seed System — Design

**Date:** 2026-03-03
**Status:** Approved

## Goal

Create a reusable script to wipe the database and inject realistic demo data for customer presentations. All calculations must be verified correct by using the app's own cascade engine via the API.

## File Structure

```
scripts/
├── seed_demo.py              # Main seed script (runs from host, talks to backend API)
└── demo_profiles/
    └── default.json          # Default demo profile
```

## JSON Profile Schema

Each customer/demo gets a JSON profile in `scripts/demo_profiles/`. The profile defines:

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

### Parameter descriptions

| Parameter | Description |
|---|---|
| `project_name` | Label for the demo (used in script output only) |
| `report_month` | The reporting month for all imports (ISO date, first of month) |
| `months_start` | First month of the 12-month window |
| `delivery_counts` | Number of deliveries per phase (p1–p5) |
| `actual_months` | First N months flagged as actuals; rest are forecast |
| `base_values` | Per line item: `monthly_range` = [min, max] for random generation |
| `phase_weights` | Distribution of totals across phases (must sum to 1.0) |
| `budget_variance_pct` | Budget = current × (1 + this). Positive = budget was higher |
| `previous_variance_pct` | Previous = current × (1 − this). Positive = improvement over time |

## Script Flow (API-Driven)

The script uses Python `requests` to call the backend REST API at `http://localhost:8000/api/v1`.

### Step 1: Wipe
```
DELETE /api/v1/imports
```
Deletes all imports and cascades to all child tables.

### Step 2: Create budget import
```
POST /data-entry/imports
  { report_month, version_type: "budget" }
```

### Step 3: Populate budget grid
Generate values: `base_value × (1 + budget_variance_pct)` per line item, distributed across phases using `phase_weights`, with random variation within `monthly_range`.
```
PUT /data-entry/imports/{budget_id}/grid
  { values: [{phase, line_item, month, value}, ...] }
```
This triggers the server-side cascade (6 calc rules + NCF + summaries + P&L).

### Step 4: Set budget deliveries
```
PUT /data-entry/imports/{budget_id}/deliveries
  { p1: N, p2: N, ... }
```

### Step 5: Create previous import
Same flow as steps 2–4 but with `version_type: "previous"` and values scaled by `(1 − previous_variance_pct)`.

### Step 6: Create current import
Same flow but `version_type: "current"`, base values used directly. Links to budget and previous via `budget_import_id` and `previous_import_id`.

### Step 7: Verify
```
GET /summary/latest
GET /pnl/latest
```
Print key metrics to stdout for manual sanity check.

## Data Generation Strategy

For each of the 17 editable line items × 12 months × 5 phases:

1. Generate a base monthly value: `random.uniform(range_min, range_max)`
2. Apply phase weight: `value × phase_weights[phase]`
3. Apply version scaling:
   - Budget: `× (1 + budget_variance_pct)`
   - Previous: `× (1 − previous_variance_pct)`
   - Current: no scaling
4. Round to 2 decimal places

This produces realistic-looking data where:
- Revenue > costs (positive net cash flow in most months)
- Phase 1 has the most activity, Phase 5 the least
- Budget is slightly higher than current (showing under-budget performance)
- Previous is slightly lower than current (showing improvement)

## Calculation Verification

All calculated fields are computed by the backend's 7-step cascade engine, triggered by each `PUT /grid` and `PUT /deliveries` call. The formulas used are:

| Calculated Field | Formula |
|---|---|
| `net_revenue` | `gross_revenue − sales_costs` |
| `subtotal_direct_cost` | `primary_build + contingency` |
| `subtotal_overheads` | `marketing + admin_overheads` |
| `gross_cash_flow` | `net_revenue − subtotal_direct_cost − subtotal_overheads` |
| `subtotal_capex` | Sum of all 10 capex/contingency line items |
| `net_cash_flow` | `gross_cash_flow − subtotal_capex` |

Plus NCF series (periodic = net_cash_flow, cumulative = running sum), phase summaries with deltas, phase comparisons (budget vs current), per-delivery rates, and P&L derivations — all server-computed.

## Usage

```bash
# Default profile
python scripts/seed_demo.py

# Custom profile
python scripts/seed_demo.py --profile scripts/demo_profiles/customer_a.json

# With custom API URL
python scripts/seed_demo.py --api-url http://localhost:8000/api/v1
```

## Creating a New Customer Profile

1. Copy `scripts/demo_profiles/default.json`
2. Adjust `monthly_range` values for appropriate project scale
3. Set `delivery_counts` and `phase_weights` for the project shape
4. Run `python scripts/seed_demo.py --profile scripts/demo_profiles/new_customer.json`
