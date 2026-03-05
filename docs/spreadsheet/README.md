# Project.xlsx — Spreadsheet Documentation

Extracted from `Project.xlsx` on 2026-02-18.

## Overview

The workbook contains a 12-month rolling cash flow projection model for a
multi-stage residential development project. The two primary sheets are:

| Sheet | Purpose | Rows | Columns |
|-------|---------|------|---------|
| **Output_V2** | Aggregated output view — summary tables, NCF time-series, N12M breakdown | 164 | E-FY (181) |
| **DEV.Sep25** | Detailed development model for the Sep-25 PCG report | 428 | G-LV (332) |

## Data Flow

```
DEV.Sep25 (detailed model)
  |
  +--> Output_V2 (control_panel selects which DEV sheet)
         |
         +--> Stage 1 Summary (rows 15-40)
         +--> WOL Summary     (rows 43-67)
         +--> All Stages      (rows 70-94)
         +--> Per Settlement   (rows 95-116)
         +--> P&L             (rows 126-134)
         +--> NCF             (rows 126-136, cols S-FY)
         +--> N12M            (rows 139-164, cols S-AE)
```

## File Index

### Output_V2
| File | Rows | Description |
|------|------|-------------|
| `control_panel.json` | 3-11 | Stage selectors, report months |
| `stage1_summary.json` | 15-40 | Stage 1 settlements, revenue, costs |
| `wol_summary.json` | 43-67 | Whole-of-Life aggregate |
| `all_stages.json` | 70-94 | All stages side-by-side |
| `per_settlement.json` | 95-116 | Per-settlement ($k) metrics |
| `pnl.json` | 126-134 | P&L summary |
| `ncf.json` | 126-136 | NCF cumulative + periodic time-series |
| `n12m.json` | 139-164 | Next 12 months line-item breakdown |

### DEV.Sep25
| File | Rows | Description |
|------|------|-------------|
| `header_and_timeline.json` | 2-10 | Timeline, period index, actual/forecast flags |
| `stage_details.json` | 12-208 | Per-stage cash flow detail |
| `per_stage_pnl.json` | 210-342 | Per-stage P&L |
| `wop_summary.json` | 345-369 | Whole-of-Project summary |

See also: [`data_flow.md`](data_flow.md) for cross-sheet formula references.
