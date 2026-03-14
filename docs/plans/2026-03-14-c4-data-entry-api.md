# C4: Data Entry API — Design Document

**Date**: 2026-03-14
**Status**: Approved — implementation starting
**Phase**: C4 (backend API only; frontend in D5)

---

## Overview

C4 adds:
1. A `delivery_counts` DB table (migration + B5 handler update to persist it)
2. A single-cell data entry endpoint: `PATCH /imports/{id}/n12m/{line_item}/{month}`

On a successful edit, the server re-runs the full cascade from DB-reconstructed inputs and re-persists all derived tables in one transaction.

---

## Decisions

### 1. delivery_counts table (Option A — persist, not derive)

**Decision:** Add a `delivery_counts` table. Populate it during `PATCH /imports/{id}/file` alongside the existing child tables.

**Rejected alternative:** Back-derive counts from `per_delivery_rows` at cascade time.
**Why rejected:** Lossy — a phase with 0 deliveries is indistinguishable from missing data (both have null current). PnL rates would be wrong.

**Table shape:**
```sql
CREATE TABLE delivery_counts (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_id  UUID NOT NULL REFERENCES imports(id) ON DELETE CASCADE,
    phase      phase_enum NOT NULL,
    count      INTEGER NOT NULL DEFAULT 0
);
```

### 2. Endpoint shape — single-cell PATCH

**Decision:** `PATCH /imports/{id}/n12m/{line_item}/{month}` with body `{"value": <decimal>}`.

**Rejected alternative:** Bulk PATCH (`PATCH /imports/{id}/n12m` with array body).
**Why rejected:** Bulk is a "form submit" pattern. The frontend uses TanStack Query mutations per cell — single-cell maps naturally. Debouncing lives on the frontend (300–500ms), not the API.

### 3. Response — 204 No Content

**Decision:** Return `204 No Content` on success. Frontend invalidates TanStack Query caches for `forecast`, `phase-comparison`, and `pnl`.

**Rejected alternative:** Return the full `ForecastResponse` (or all three cascade responses).
**Why rejected:** The cascade affects three endpoints. Returning all three couples the response shape to the frontend's current needs and sends a lot of data per keystroke. TanStack Query invalidation handles the fan-out cleanly without the backend knowing what the frontend needs.

**Tradeoff accepted:** Brief refetch flash after edit (cascade effects not instantly visible). For a financial tool where correctness > perceived speed, this is preferable to showing wrong derived values during an optimistic update.

### 4. Cascade re-run strategy

On edit, the server reconstructs the cascade input from DB:

```python
parsed = {
    "import_meta": {
        "version_type": import_record.version_type.value,
        "source_type": import_record.source_type.value,
    },
    "delivery_counts": [{"phase": r.phase, "count": r.count} for r in delivery_count_rows],
    "n12m_line_items": [...],        # rebuilt from n12m_line_items table
    "phase_comparison_rows": [...],  # rebuilt from phase_comparison_rows table
}
cascade = run_cascade(parsed)
```

Then, in a single transaction:
- Delete existing `per_delivery_rows`, `ncf_series`, `pnl_summaries` for this import
- Re-insert from cascade output
- `n12m_line_items` and `phase_comparison_rows` are source data — not deleted, the edited row is updated in place

### 5. Error handling

- `404` — import not found, soft-deleted, or not complete
- `404` — `line_item` not found in this import's n12m data
- `422` — malformed UUID or invalid month (not 1–12)
- `409` — (future) if import is locked for editing

---

## What C4 Does NOT Do

- No delivery_count editing (counts come from the original Excel upload)
- No phase_comparison editing (source data from Excel, not user-editable in this phase)
- No `?force=true` re-upload escape hatch (deferred)
- No async processing / background jobs (cascade runs synchronously, ~ms for 12 months)
- No undo/redo history
- No locking / concurrent edit protection

---

## Files to Create/Modify

| File | Change |
|---|---|
| `alembic/versions/<hash>_c4_delivery_counts.py` | New migration: `delivery_counts` table |
| `backend/app/domain/models.py` | Add `DeliveryCount` ORM model |
| `backend/app/routers/imports.py` | Update B5 handler to persist delivery_counts; add PATCH endpoint |
| `backend/tests/integration/test_data_entry_endpoint.py` | New integration test file |

---

## Success Criteria

1. `delivery_counts` table created and populated on every `PATCH /imports/{id}/file`
2. `PATCH /imports/{id}/n12m/{line_item}/{month}` returns 204 after updating n12m and re-running cascade
3. All derived tables (per_delivery_rows, ncf_series, pnl_summaries) reflect the updated values
4. Existing C1/C2/C3 read endpoints return updated data after an edit
5. All existing 361 tests continue to pass; new tests cover edit + cascade + 404/422 paths
