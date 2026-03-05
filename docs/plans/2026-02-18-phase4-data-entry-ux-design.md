# Phase 4: Data Entry UX — Design Document

**Date**: 2026-02-18
**Status**: Approved
**Depends on**: 2026-02-18-phase3-powerbi-views-design.md

---

## Overview

The data entry grid is the primary use case of the application, but the current UX has significant friction: no keyboard navigation between cells, no real-time feedback on computed rows, and saving disrupts focus and scroll position. This phase addresses all three.

Three work items:

1. Shared calculation rules (single source of truth for client + server)
2. Keyboard navigation (Tab, Enter-to-advance, Escape)
3. Save UX improvements (preserve focus, discard confirmation, per-stage dirty indicators)

---

## 1. Shared Calculation Rules

### Problem

The 6 calculation rules (net_revenue_proceeds, subtotals, gross/net cash flow) are defined as Python lambdas in `calculations.py`. To preview computed values client-side as the user types, the frontend needs the same rules — but duplicating them creates a divergence risk.

### Solution

Extract the rules into a JSON config file. Both runtimes evaluate the same definition.

**`backend/app/calc_rules.json`:**

```json
[
  {"field": "net_revenue_proceeds", "op": "subtract", "inputs": ["gross_revenue_proceeds", "selling_costs"]},
  {"field": "subtotal_inventory_capex", "op": "sum", "inputs": ["home_build", "contingency"]},
  {"field": "subtotal_dev_overheads", "op": "sum", "inputs": ["marketing", "lpc_overheads"]},
  {"field": "gross_dev_cash_flow", "op": "subtract", "inputs": ["net_revenue_proceeds", "subtotal_inventory_capex", "subtotal_dev_overheads"]},
  {"field": "subtotal_dev_capex", "op": "sum", "inputs": ["estate_major_works", "civils_infrastructure", "general_landscaping", "clubhouse_amenities", "professional_fees", "statutory_fees", "other", "contingency_civils_emw", "contingency_clubhouse", "st_rental_unit_build_capex"]},
  {"field": "net_dev_cash_flow", "op": "subtract", "inputs": ["gross_dev_cash_flow", "subtotal_dev_capex"]}
]
```

Two operations: `sum` (add all inputs) and `subtract` (first input minus the rest). Array order = dependency order.

- **Backend:** `calculations.py` reads this JSON and evaluates it, replacing the current lambda-based `CALC_RULES`.
- **Frontend:** New `GET /api/v1/calc-rules` endpoint serves the JSON. A small evaluator function applies the rules client-side.
- **Real-time preview:** On every cell change, the frontend runs the rules against local values for that month. Computed rows update instantly with a subtle visual indicator (dimmed text) showing "preview — not yet saved". On save, the server runs the same rules authoritatively.

**Scope limitation:** Only the 6 within-stage-month rules get client-side preview. Cross-stage aggregates (NCF, summaries, P&L) stay server-side only — they involve the full 7-step cascade.

### Files

- Create: `backend/app/calc_rules.json`
- Modify: `backend/app/services/calculations.py` — read JSON instead of lambda dict
- Create: `backend/app/api/v1/calc_rules.py` — new GET endpoint
- Modify: `frontend/src/components/DataEntryGrid.jsx` — add evaluator and preview rendering

---

## 2. Keyboard Navigation

### Problem

The grid's only keyboard handler is Enter-to-blur. Users cannot Tab between cells, and Enter doesn't advance to the next row. For a data entry tool, this is the biggest ergonomic gap.

### Solution

Lightweight navigation that feels like a modern form, not a spreadsheet:

- **Tab / Shift+Tab** — move to next/previous editable cell, skipping calculated rows. Uses native browser tab order; calculated cells get `tabIndex={-1}`.
- **Enter** — commit current cell and move focus down to the next editable row in the same column. This is the one custom behavior — optimised for column-wise data entry (the most common pattern).
- **Escape** — revert current cell to its last-saved value and blur.

No arrow-key cell navigation, no editing-vs-navigating modes, no coordinate tracking. The goal is to remove friction, not replicate Excel.

### Files

- Modify: `frontend/src/components/DataEntryGrid.jsx` — keyboard handlers, tabIndex management

---

## 3. Save UX Improvements

### Problem

Saving triggers a full grid reload, which loses scroll position and focus. Discarding is instant with no confirmation. Users have no indication of unsaved changes on other stage tabs.

### Solution

**Preserve focus and scroll on save.** After the save response, merge updated values into existing grid state rather than re-fetching and re-rendering the entire grid. Track and restore the focused cell.

**Discard confirmation.** Show a styled confirmation modal ("Discard N unsaved changes?") instead of immediately clearing. Consistent with the app's dark theme — not a browser `confirm()`.

**Per-stage dirty indicators.** Add a small dot/badge on S1–S5 tab buttons when that stage has unsaved changes, visible even when viewing a different stage.

### Files

- Modify: `frontend/src/components/tabs/DataEntryTab.jsx` — merge-on-save, discard modal, dirty badges
- Modify: `frontend/src/components/DataEntryGrid.jsx` — expose focused cell for restore
- Create: `frontend/src/components/DiscardConfirmModal.jsx` (if warranted; may be inline)

---

## What This Phase Does NOT Do

- No auto-save (explicit save remains the model)
- No undo/redo history
- No multi-cell selection or range operations
- No copy/paste from external spreadsheets
- No cross-stage preview (NCF, summaries, P&L stay server-side)
- No role-based access (deferred to a future phase)

---

## Success Criteria

1. User can Tab through editable cells, Enter to advance down a column, Escape to revert
2. Computed rows update instantly as the user types (client-side preview)
3. Saving preserves scroll position and focus
4. Discard shows a confirmation dialog
5. Stage tabs show a dirty indicator when unsaved changes exist
6. Calculation rules defined in one place (JSON), consumed by both backend and frontend
7. All existing tests continue to pass; new tests cover keyboard navigation and calc preview
