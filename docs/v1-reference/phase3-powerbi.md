# Phase 3: PowerBI-Friendly Database Views -- Design Document

**Date**: 2026-02-18
**Status**: Approved
**Depends on**: 2026-02-18-phase2-deployment-readiness-design.md

---

## Overview

The database schema stores stage comparison and per-settlement data as JSON columns (`{"s1": val, "s2": val, ..., "wop": val}`). PowerBI cannot natively query inside JSON blobs — it needs flat, tabular data. Rather than migrating the schema (which would require changing models, API, and frontend), we create PostgreSQL views that flatten the JSON into PowerBI-friendly rows.

This phase also produces a data dictionary document for the PowerBI team.

Two work items:

1. Database views via Alembic migration
2. Data dictionary documentation

---

## 1. Database Views

### Problem

Three tables use JSON columns (9 columns total):

| Table | JSON Columns | Data Shape |
|-------|-------------|------------|
| `imports` | `actual_flags` | `list[bool]` |
| `stage_comparisons` | `budget_values`, `current_values`, `delta_values`, `delta_pct_values` | `dict{s1..s5, wop: float}` |
| `per_settlements` | `budget_values`, `current_values`, `delta_values`, `delta_pct_values` | `dict{s1..s5, wop: float}` |

PowerBI sees these as opaque text. It cannot filter, sort, or aggregate on individual stage values without custom M query transformations.

### Solution

Create 3 PostgreSQL views via an Alembic migration. Views are additive — they don't modify existing tables, so there is zero risk to the application.

**`vw_stage_comparison`**

Unpivots the 4 JSON columns into one row per (import, line_item, stage):

```sql
CREATE VIEW vw_stage_comparison AS
SELECT
    sc.id,
    sc.import_id,
    sc.line_item,
    sc.sort_order,
    stage.key AS stage,
    (sc.budget_values ->> stage.key)::float AS budget,
    (sc.current_values ->> stage.key)::float AS current_value,
    (sc.delta_values ->> stage.key)::float AS delta,
    (sc.delta_pct_values ->> stage.key)::float AS delta_pct
FROM stage_comparisons sc
CROSS JOIN LATERAL jsonb_each_text(sc.budget_values) AS stage(key, value);
```

**`vw_per_settlement`**

Same pattern:

```sql
CREATE VIEW vw_per_settlement AS
SELECT
    ps.id,
    ps.import_id,
    ps.line_item,
    ps.sort_order,
    stage.key AS stage,
    (ps.budget_values ->> stage.key)::float AS budget,
    (ps.current_values ->> stage.key)::float AS current_value,
    (ps.delta_values ->> stage.key)::float AS delta,
    (ps.delta_pct_values ->> stage.key)::float AS delta_pct
FROM per_settlements ps
CROSS JOIN LATERAL jsonb_each_text(ps.budget_values) AS stage(key, value);
```

**`vw_actual_flags`**

Unpacks the positional boolean list into indexed rows:

```sql
CREATE VIEW vw_actual_flags AS
SELECT
    i.id AS import_id,
    (elem.ordinality - 1) AS month_index,
    elem.value::boolean AS is_actual
FROM imports i
CROSS JOIN LATERAL jsonb_array_elements_text(i.actual_flags) WITH ORDINALITY AS elem(value, ordinality)
WHERE i.actual_flags IS NOT NULL;
```

### Files

- Create: Alembic migration `backend/alembic/versions/XXXX_add_powerbi_views.py`

### Tests

- Verify views exist after migration
- Verify views return correct data when the underlying tables have data

---

## 2. Data Dictionary

### Problem

The database schema is a public API for PowerBI. The PowerBI team needs a reference document listing every table, column, type, and how to use the views.

### Solution

Create `docs/data-dictionary.md` covering:

- All 9 database tables with column descriptions
- The 3 new views with usage examples
- Recommended joins for common PowerBI queries
- Entity-relationship overview

### Files

- Create: `docs/data-dictionary.md`

---

## What This Phase Does NOT Do

- No schema migration (views are additive)
- No parser changes (works fine for current customer)
- No API changes (frontend uses JSON as-is)
- No model changes
- No configurable parser (deferred until a second customer exists)

---

## Success Criteria

1. Three views exist in the database and return flat, tabular data
2. Data dictionary documents every table, column, and view
3. Zero changes to existing application code or tests
