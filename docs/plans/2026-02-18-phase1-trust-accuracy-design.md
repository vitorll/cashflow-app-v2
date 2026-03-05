# Phase 1: Trust & Accuracy -- Design Document

**Date**: 2026-02-18
**Status**: Approved
**Depends on**: 2026-02-17-project-review-design.md

---

## Overview

Phase 1 addresses the foundational trust layer: the app's calculations must provably match the source spreadsheet, and the NCF data pipeline must work end-to-end across both import and manual data entry flows.

Four work items, in priority order:

1. Fix NCF series naming bug
2. Transaction safety for cascade recalculation
3. Spreadsheet extraction & documentation
4. E2E calculation validation tests

---

## 1. Fix NCF Series Naming Bug

### Problem

Two independent naming regimes exist for NCF series, and they are inconsistent:

| Source | Series Names Produced | Frontend Expects |
|---|---|---|
| Excel parser | `current_sep25`, `previous_jul25`, `budget`, `max`, `min` | `current_sep25`, `previous_jul25`, `budget`, `max`, `min` |
| Cascade engine | `current`, `previous`, `budget` | `current_sep25`, `previous_jul25`, `budget`, `max`, `min` |

After any manual data entry cascade recalculation:
- NCF series are deleted and recreated with generic names (`current`, `previous`, `budget`)
- The frontend looks for `current_sep25` and `previous_jul25` -- finds nothing, displays empty rows
- `max` and `min` series are permanently deleted and never recreated

### Solution

Standardise on generic, date-free names everywhere.

**Backend changes:**

- `excel_parser.py`: Change `ncf_rows` dict from `"current_sep25"` / `"previous_jul25"` to `"current"` / `"previous"`. Keep `"budget"`, `"max"`, `"min"` unchanged.
- `cascade.py` (`recalculate_ncf`): Already uses `"current"` / `"previous"` / `"budget"` -- no change needed. Modify the delete-before-recreate logic to preserve `"max"` and `"min"` series (only delete `"current"`, `"previous"`, `"budget"`).

**Frontend changes:**

- `NcfSection.jsx`: Replace hardcoded series references with dynamic rendering. Iterate over whatever keys the API returns for `cumulative` and `periodic`. Derive human-readable labels from the key (`"current"` -> `"Current"`, `"previous"` -> `"Previous"`, `"budget"` -> `"Budget"`, `"max"` -> `"Max"`, `"min"` -> `"Min"`).

**API layer:** No changes needed -- `ncf.py` is already a transparent pass-through that groups by whatever `series_name` values exist in the database.

**Schema:** No changes needed -- `NcfResponse` already uses `dict[str, list]` for cumulative/periodic.

### Tests

- Update existing NCF tests to use generic series names
- Add test verifying cascade preserves max/min series
- Update frontend NcfSection tests for dynamic rendering

---

## 2. Transaction Safety for Cascade Recalculation

### Problem

The cascade is already atomically safe (all 7 steps use `flush()` within one transaction, `commit()` only at the end). However, failures surface as unhandled 500 errors with no structured message, making debugging difficult.

### Solution

Wrap the `full_recalculate` call in `try/except` in each of the 3 data entry endpoints that call it:

- `PUT /data-entry/imports/{id}/grid` (bulk save)
- `PATCH /data-entry/stage-inputs/{id}` (single cell edit)
- `PUT /data-entry/imports/{id}/settlements` (settlement counts)

On failure:
1. Explicitly roll back the session (`await db.rollback()`)
2. Raise `HTTPException(500, f"Cascade recalculation failed: {str(e)}")`

This preserves the existing atomicity (user edits + cascade all roll back together) while providing a meaningful error message.

### Tests

- Add test that simulates a cascade failure and verifies the response includes a structured error message
- Verify the database is clean after a failed cascade (no partial writes)

---

## 3. Spreadsheet Extraction & Documentation

### Problem

`Project.xlsx` is the source of truth for all business rules, formulas, and data structure. It is too large to process in one pass (17 sheets, largest being 3,918 rows x 421 columns). Analysis tools and LLMs hit size limits when trying to read it whole.

### Solution

Extract the workbook into chunked JSON (data + formulas) and Markdown (documentation) files, organised by sheet and logical section.

### Sheets to Extract

| Sheet | Scope | Rationale |
|---|---|---|
| `Output_V2` | Full (164 rows) | Primary sheet the app reads from |
| `DEV.Sep25` | Full (428 rows) | "Current" reference model, defines all formulas |
| `DEV.FY26B` | Structure only | Budget version, same layout as DEV.Sep25 |
| `DEV.Jul25` | Structure only | Previous version, same layout |
| `DEV.*.EM` | Skip | Raw EstateMaster exports, upstream of the app |

### Output Structure

```
docs/spreadsheet/
├── README.md                    # Overview, data flow diagram, sheet index
├── output_v2/
│   ├── output_v2.md             # Layout docs, formula patterns, cross-sheet refs
│   ├── control_panel.json       # Rows 3-11
│   ├── stage1_summary.json      # Rows 15-40
│   ├── wol_summary.json         # Rows 43-67
│   ├── all_stages.json          # Rows 70-94
│   ├── per_settlement.json      # Rows 96-116
│   ├── ncf.json                 # Rows 126-136
│   ├── n12m.json                # Rows 139-164
│   └── pnl.json                 # Rows 128-134
├── dev_sep25/
│   ├── dev_sep25.md             # Layout docs, row/col mapping
│   ├── header_and_timeline.json # Rows 2-10
│   ├── stage_details.json       # Rows 12-208 (per-category breakdowns)
│   ├── per_stage_pnl.json       # Rows 210-342 (S1-S5 P&L blocks)
│   └── wop_summary.json         # Rows 345-369
└── data_flow.md                 # Cross-sheet formula reference map
```

### JSON Format

Each JSON file contains:
- `sheet`: sheet name
- `range`: cell range covered
- `description`: what this section represents
- `headers`: column headers if applicable
- `rows`: array of objects, each with `row_number`, `label`, `values` (dict of col -> value), and `formulas` (dict of col -> formula string, where applicable)

### Markdown Format

Each markdown file documents:
- Section layout (row ranges, column meanings)
- Formula patterns (with examples, not every cell)
- Cross-sheet references (which cells reference which other sheets)
- Business logic explanation (what the numbers mean)

---

## 4. E2E Calculation Validation Tests

### Problem

The 7 `CALC_RULES` formulas are tested individually, but there is no integration test that verifies the full pipeline (import -> parse -> calculate) produces values matching the source spreadsheet.

### Solution

**Test 1: Parser accuracy** -- Load `Project.xlsx` via the parser. For each of the 6 calculated N12M line items across all 12 months (~72 values), read the expected value directly from the spreadsheet using openpyxl, and assert the parsed value matches within a tolerance of $0.01.

Calculated line items to verify:
- `net_revenue_proceeds` (revenue section)
- `subtotal_inventory_capex` (development section)
- `subtotal_dev_overheads` (overheads section)
- `gross_dev_cash_flow` (overheads section)
- `subtotal_dev_capex` (capex section)
- `net_dev_cash_flow` (capex section)

**Test 2: Cascade consistency** -- Seed `StageInput` rows from the parsed import data, run `full_recalculate`, and verify the recalculated `N12mLineItem` values match the originally parsed values. This confirms the cascade engine reproduces the same results as the Excel formulas.

**Test 3: NCF consistency** -- After cascade, verify NCF periodic values equal the `net_dev_cash_flow` monthly values, and cumulative values are the running sum.

**Skip condition**: All tests use `pytest.mark.skipif` to skip gracefully if `Project.xlsx` is not present (e.g., in CI environments where the file isn't checked in).

### File Location

`backend/tests/test_e2e_calculations.py`

---

## Data Flow After Phase 1

```
Project.xlsx
    |
    ├── docs/spreadsheet/ (extracted JSON + Markdown reference)
    |
    ├── Excel Parser (generic NCF names: current, previous, budget, max, min)
    |       |
    |       v
    |   Import + NcfSeries + N12mLineItem + Summaries + P&L
    |
    ├── Manual Data Entry
    |       |
    |       v
    |   StageInput edits
    |       |
    |       v
    |   full_recalculate (7 steps, wrapped in try/except)
    |       |  - preserves max/min NCF series
    |       |  - uses generic NCF names
    |       v
    |   Updated N12mLineItem + NcfSeries + Summaries + P&L
    |
    v
Frontend (dynamic NcfSection, renders whatever series the API returns)
```

---

## Success Criteria

1. NCF section displays correctly after both Excel import AND manual data entry cascade
2. Cascade failures return structured error messages and roll back cleanly
3. `docs/spreadsheet/` contains complete, parseable reference of the source workbook
4. E2E tests pass, proving calculation parity with the Excel source
