# Data Dictionary

Reference for all database tables and views in the Cash Flow Projection application.

---

## Entity Relationships

```
imports (central record)
  ├── ncf_series          (1:many, CASCADE)
  ├── n12m_line_items     (1:many, CASCADE)
  ├── phase_summaries     (1:many, CASCADE)
  ├── phase_comparisons   (1:many, CASCADE)
  ├── per_deliveries      (1:many, CASCADE)
  ├── pnl_summaries       (1:many, CASCADE)
  ├── phase_inputs        (1:many, CASCADE)
  └── delivery_counts     (1:many, CASCADE)

imports.budget_import_id   → imports.id  (self-referential)
imports.previous_import_id → imports.id  (self-referential)
```

All child tables reference `imports.id` via `import_id` with `ON DELETE CASCADE`.

---

## Tables

### `imports`

Central record for each uploaded Excel file or manually created dataset.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | Primary key |
| `filename` | VARCHAR(255) | No | Original uploaded filename |
| `file_size` | INTEGER | No | File size in bytes |
| `sheet_name` | VARCHAR(100) | No | Excel sheet parsed (e.g. "DEV.Sep25") |
| `report_month` | DATE | No | Reporting month (first day of month) |
| `status` | VARCHAR(20) | No | "processing", "completed", or "failed" |
| `error_msg` | TEXT | Yes | Error message if status = "failed" |
| `created_at` | TIMESTAMPTZ | No | Record creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | Last update timestamp |
| `actual_flags` | JSON | Yes | `list[bool]` — one flag per month, true = actual, false = forecast |
| `version_type` | VARCHAR(20) | Yes | "budget", "current", or "previous" |
| `source_type` | VARCHAR(20) | No | "excel" or "manual" |
| `budget_import_id` | UUID | Yes | FK → `imports.id` — the budget baseline import |
| `previous_import_id` | UUID | Yes | FK → `imports.id` — the previous forecast import |

### `ncf_series`

Net Cash Flow cumulative and periodic series. One row per (import, series_type, series_name, month).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | Primary key |
| `import_id` | UUID | No | FK → `imports.id` |
| `series_type` | VARCHAR(20) | No | "cumulative" or "periodic" |
| `series_name` | VARCHAR(50) | No | Series identifier (e.g. "current", "budget") |
| `month` | DATE | No | Month (first day) |
| `value` | NUMERIC(18,2) | Yes | Dollar value |
| `created_at` | TIMESTAMPTZ | No | Record creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | Last update timestamp |

**Unique constraint:** `(import_id, series_type, series_name, month)`

### `n12m_line_items`

Next 12 Months line item values. One row per (import, line_item, month).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | Primary key |
| `import_id` | UUID | No | FK → `imports.id` |
| `section` | VARCHAR(30) | No | Section grouping (e.g. "revenue", "development", "overheads") |
| `line_item` | VARCHAR(100) | No | Machine-readable key |
| `display_name` | VARCHAR(100) | No | Human-readable label |
| `is_calculated` | BOOLEAN | No | True if value is computed (subtotal/total) |
| `sort_order` | INTEGER | No | Display ordering |
| `month` | DATE | No | Month (first day) |
| `value` | NUMERIC(18,2) | Yes | Dollar value |
| `created_at` | TIMESTAMPTZ | No | Record creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | Last update timestamp |

**Unique constraint:** `(import_id, line_item, month)`

### `phase_summaries`

Phase 1 and Total summary metrics. One row per (import, scope, line_item).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | Primary key |
| `import_id` | UUID | No | FK → `imports.id` |
| `scope` | VARCHAR(20) | No | "per_phase" or "total" |
| `line_item` | VARCHAR(100) | No | Metric name |
| `to_date` | FLOAT | Yes | Value to date |
| `pct_complete` | FLOAT | Yes | Percentage complete |
| `total_current` | FLOAT | Yes | Current forecast total |
| `total_previous` | FLOAT | Yes | Previous forecast total |
| `total_budget` | FLOAT | Yes | Budget total |
| `delta_prev_dollar` | FLOAT | Yes | Variance vs previous ($) |
| `delta_prev_pct` | FLOAT | Yes | Variance vs previous (%) |
| `delta_budget_dollar` | FLOAT | Yes | Variance vs budget ($) |
| `delta_budget_pct` | FLOAT | Yes | Variance vs budget (%) |
| `comment` | VARCHAR(500) | Yes | Optional commentary |
| `sort_order` | INTEGER | No | Display ordering |

### `phase_comparisons`

All-phases comparison data. JSON columns store values keyed by phase (p1–p5, total).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | Primary key |
| `import_id` | UUID | No | FK → `imports.id` |
| `line_item` | VARCHAR(100) | No | Metric name |
| `budget_values` | JSON | Yes | `{"p1": float, "p2": float, ..., "total": float}` |
| `current_values` | JSON | Yes | Same shape as budget_values |
| `delta_values` | JSON | Yes | Current minus budget |
| `delta_pct_values` | JSON | Yes | Delta as percentage |
| `sort_order` | INTEGER | No | Display ordering |

### `per_deliveries`

Per-delivery values across phases. Same JSON structure as `phase_comparisons`.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | Primary key |
| `import_id` | UUID | No | FK → `imports.id` |
| `line_item` | VARCHAR(100) | No | Metric name |
| `budget_values` | JSON | Yes | `{"p1": float, ..., "total": float}` |
| `current_values` | JSON | Yes | Same shape |
| `delta_values` | JSON | Yes | Current minus budget |
| `delta_pct_values` | JSON | Yes | Delta as percentage |
| `sort_order` | INTEGER | No | Display ordering |

### `pnl_summaries`

Profit & Loss summary. One row per (import, line_item).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | Primary key |
| `import_id` | UUID | No | FK → `imports.id` |
| `line_item` | VARCHAR(100) | No | P&L line item |
| `budget_total` | FLOAT | Yes | Budget total |
| `current_total` | FLOAT | Yes | Current forecast total |
| `delta_total` | FLOAT | Yes | Variance ($) |
| `budget_rate` | FLOAT | Yes | Budget rate/margin |
| `current_rate` | FLOAT | Yes | Current rate/margin |
| `delta_rate` | FLOAT | Yes | Rate variance |
| `sort_order` | INTEGER | No | Display ordering |

### `phase_inputs`

Manual data entry values per phase/month. Used for manual forecast creation.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | Primary key |
| `import_id` | UUID | No | FK → `imports.id` |
| `phase` | VARCHAR(10) | No | Phase identifier (e.g. "p1", "p2") |
| `line_item` | VARCHAR(100) | No | Machine-readable key |
| `is_calculated` | BOOLEAN | No | True if auto-computed |
| `sort_order` | INTEGER | No | Display ordering |
| `section` | VARCHAR(30) | No | Section grouping |
| `display_name` | VARCHAR(100) | No | Human-readable label |
| `month` | DATE | No | Month (first day) |
| `value` | NUMERIC(18,2) | Yes | Dollar value |

**Unique constraint:** `(import_id, phase, line_item, month)`

### `delivery_counts`

Number of deliveries per phase.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | Primary key |
| `import_id` | UUID | No | FK → `imports.id` |
| `phase` | VARCHAR(10) | No | Phase identifier |
| `count` | INTEGER | No | Number of deliveries |

**Unique constraint:** `(import_id, phase)`

---

## Database Views

These views flatten JSON columns into tabular data for direct querying.

### `vw_phase_comparison`

Unpivots `phase_comparisons` JSON columns into one row per (import, line_item, phase).

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Row ID from `phase_comparisons` |
| `import_id` | UUID | FK → `imports.id` |
| `line_item` | VARCHAR | Metric name |
| `sort_order` | INTEGER | Display ordering |
| `phase` | TEXT | Phase key (e.g. "p1", "p2", "total") |
| `budget` | FLOAT | Budget value for this phase |
| `current_value` | FLOAT | Current forecast value |
| `delta` | FLOAT | Current minus budget |
| `delta_pct` | FLOAT | Delta as percentage |

### `vw_per_delivery`

Unpivots `per_deliveries` JSON columns. Same structure as `vw_phase_comparison`.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Row ID from `per_deliveries` |
| `import_id` | UUID | FK → `imports.id` |
| `line_item` | VARCHAR | Metric name |
| `sort_order` | INTEGER | Display ordering |
| `phase` | TEXT | Phase key |
| `budget` | FLOAT | Budget value per delivery |
| `current_value` | FLOAT | Current forecast per delivery |
| `delta` | FLOAT | Current minus budget |
| `delta_pct` | FLOAT | Delta as percentage |

### `vw_actual_flags`

Unpacks the `imports.actual_flags` JSON array into one row per month.

| Column | Type | Description |
|--------|------|-------------|
| `import_id` | UUID | FK → `imports.id` |
| `month_index` | INTEGER | 0-based month index within the 12-month window |
| `is_actual` | BOOLEAN | True = actual data, False = forecast |

---

## Example Queries

```sql
-- All phase comparison data for the latest import
SELECT pc.*, i.report_month, i.filename
FROM vw_phase_comparison pc
JOIN imports i ON i.id = pc.import_id
ORDER BY pc.sort_order, pc.phase;

-- Monthly N12M data by section
SELECT line_item, display_name, month, value
FROM n12m_line_items
WHERE import_id = '<uuid>'
ORDER BY sort_order, month;

-- Per-delivery values with import metadata
SELECT pd.*, i.report_month
FROM vw_per_delivery pd
JOIN imports i ON i.id = pd.import_id
WHERE pd.phase = 'p1'
ORDER BY pd.sort_order;

-- Which months are actuals vs forecasts
SELECT af.*, i.report_month
FROM vw_actual_flags af
JOIN imports i ON i.id = af.import_id
ORDER BY af.month_index;

-- NCF cumulative series for charting
SELECT month, series_name, value
FROM ncf_series
WHERE import_id = '<uuid>' AND series_type = 'cumulative'
ORDER BY month;
```
