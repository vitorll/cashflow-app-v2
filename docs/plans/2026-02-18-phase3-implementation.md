# Phase 3: PowerBI Database Views — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create PostgreSQL views that flatten JSON columns into PowerBI-friendly tabular data, plus a data dictionary document.

**Architecture:** Add 3 database views via an Alembic migration. Views are read-only projections of existing tables — zero risk to application code. Add a data dictionary for the PowerBI team.

**Tech Stack:** PostgreSQL (JSONB functions), Alembic (raw SQL migration), Markdown (documentation)

---

### Task 1: Create Alembic Migration with PowerBI Views

**Files:**
- Create: `backend/alembic/versions/004_add_powerbi_views.py`

**Step 1: Create the migration file**

Create `backend/alembic/versions/004_add_powerbi_views.py`:

```python
"""add PowerBI-friendly database views

Revision ID: 004
Revises: 003
Create Date: 2026-02-18 00:00:00.000000
"""
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
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
        CROSS JOIN LATERAL jsonb_each_text(sc.budget_values) AS stage(key, value)
    """)

    op.execute("""
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
        CROSS JOIN LATERAL jsonb_each_text(ps.budget_values) AS stage(key, value)
    """)

    op.execute("""
        CREATE VIEW vw_actual_flags AS
        SELECT
            i.id AS import_id,
            (elem.ordinality - 1)::int AS month_index,
            elem.value::boolean AS is_actual
        FROM imports i
        CROSS JOIN LATERAL jsonb_array_elements_text(i.actual_flags::jsonb)
            WITH ORDINALITY AS elem(value, ordinality)
        WHERE i.actual_flags IS NOT NULL
    """)


def downgrade():
    op.execute("DROP VIEW IF EXISTS vw_actual_flags")
    op.execute("DROP VIEW IF EXISTS vw_per_settlement")
    op.execute("DROP VIEW IF EXISTS vw_stage_comparison")
```

**Step 2: Run the migration**

Run: `docker compose exec -e PYTHONPATH=/app backend alembic upgrade head`

Expected: Migration runs successfully, 3 views created.

**Step 3: Verify the views exist**

Run: `docker compose exec db psql -U cashflow -c "\dv"`

Expected: Lists `vw_stage_comparison`, `vw_per_settlement`, `vw_actual_flags`.

**Step 4: Verify views return data (if imports exist)**

Run:
```bash
docker compose exec db psql -U cashflow -c "SELECT * FROM vw_stage_comparison LIMIT 5"
docker compose exec db psql -U cashflow -c "SELECT * FROM vw_per_settlement LIMIT 5"
docker compose exec db psql -U cashflow -c "SELECT * FROM vw_actual_flags LIMIT 5"
```

Expected: Either rows (if data exists) or empty results (if no imports). No errors.

**Step 5: Run all backend tests to confirm nothing breaks**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest --tb=short`

Expected: All pass. Views don't affect any application code.

**Step 6: Commit**

```bash
git add backend/alembic/versions/004_add_powerbi_views.py
git commit -m "Add PowerBI-friendly database views for stage comparison, per settlement, and actual flags"
```

---

### Task 2: Write Data Dictionary

**Files:**
- Create: `docs/data-dictionary.md`

**Step 1: Create the data dictionary**

Create `docs/data-dictionary.md` documenting all 9 tables and 3 views. Include:

- Table name, description, and all columns with types
- Primary keys and foreign key relationships
- The 3 PowerBI views with column descriptions and example queries
- Entity-relationship overview showing how tables connect via `import_id`

Tables to document:
1. `imports` — Central record for each uploaded/manual dataset
2. `ncf_series` — Net Cash Flow cumulative and periodic series
3. `n12m_line_items` — Next 12 Months line item values by month
4. `stage_summaries` — Stage 1 and Whole-of-Life summary metrics
5. `stage_comparisons` — All stages comparison (JSON columns)
6. `per_settlements` — Per-settlement values across stages (JSON columns)
7. `pnl_summaries` — Profit & Loss summary
8. `stage_inputs` — Manual data entry values per stage/month
9. `settlement_counts` — Settlement counts per stage

Views to document:
1. `vw_stage_comparison` — Flattened stage comparison (one row per stage)
2. `vw_per_settlement` — Flattened per-settlement data (one row per stage)
3. `vw_actual_flags` — Unpacked actual/forecast flags (one row per month)

Include example PowerBI queries like:
```sql
-- All stage comparison data for the latest import
SELECT sc.*, i.report_month, i.filename
FROM vw_stage_comparison sc
JOIN imports i ON i.id = sc.import_id
ORDER BY sc.sort_order, sc.stage;

-- Monthly N12M data pivoted by section
SELECT line_item, display_name, month, value
FROM n12m_line_items
WHERE import_id = '<uuid>'
ORDER BY sort_order, month;
```

**Step 2: Commit**

```bash
git add docs/data-dictionary.md
git commit -m "Add data dictionary for PowerBI integration"
```

---

### Task 3: Final Verification & Push

**Step 1: Run all tests**

Backend: `docker compose exec -e PYTHONPATH=/app backend python -m pytest --tb=short`
Frontend: `cd frontend && npx vitest run && npm run lint`

Expected: All pass.

**Step 2: Push**

```bash
git push
```
