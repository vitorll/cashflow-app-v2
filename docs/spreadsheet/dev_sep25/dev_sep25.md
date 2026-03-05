# DEV.Sep25 Sheet Documentation

## Overview

The DEV.Sep25 sheet (rows 2-428, columns G-LV) is the detailed development
model for the September 2025 PCG (Project Control Group) report. It contains
the full cash flow projections for all development stages.

## Layout

| Section | Rows | Content |
|---------|------|---------|
| Header & Timeline | 2-10 | Asset info, EMCF refs, period index, month labels, FY, days, actual/forecast flag |
| Stage Details | 12-208 | Per-stage blocks: completions, build starts, settlements, revenue, costs, capex |
| Per-Stage P&L | 210-342 | P&L view per stage with Budget/Total/To Date/To Go columns + monthly detail |
| WOP Summary | 345-369 | Whole-of-Project aggregated P&L |

## Row/Column Mapping

### Key Columns (header area)
| Column | Content |
|--------|---------|
| I | Stage number |
| J | Row label / line item name |
| O | Budget total |
| P | Current total |
| Q | To Date (actuals) |
| R | To Go (forecast) |
| S onwards | Monthly time-series (Mar-21 through ~Dec-30) |

### Per-Stage Block Structure (rows 12-208)

Each stage occupies a repeating block of ~40 rows with this structure:

1. **Completions** — Non-Perm Dwelling Completion #
2. **Build Starts** — Non-Perm Dwelling Build Start #
3. **Settlements** — Settlement count
4. **Revenue** — Gross Revenue Proceeds, Selling Costs, Net Revenue
5. **Inventory Capex** — Home Build, Contingency, Subtotal
6. **Overheads** — Marketing, LPC Overheads, Subtotal
7. **Gross Dev Cash Flow**
8. **Estate Capex** — Major Works, Civils, Landscaping, Clubhouse, Prof Fees, Statutory, Other, Contingencies
9. **Tourism/Rental** — Tourism unit capex, ST rental capex
10. **Subtotal Dev Capex**
11. **Net Dev Cash Flow**

Stages in order: Stage 1, Stage 2, Stage 3, Stage 4, Stage 5, then WOP total.

### Per-Stage P&L (rows 210-342)

Each stage block (~27 rows) repeats:
- Settlements count
- Revenue lines (Gross, Selling, Net)
- Cost lines (Home Build, Contingency, Subtotal Inventory Capex)
- Overhead lines (Marketing, LPC, Subtotal Dev Overheads)
- Gross Dev Cash Flow
- Estate capex lines
- Subtotal Dev Capex
- Net Dev Cash Flow

### WOP Summary (rows 345-369)

Same structure as per-stage P&L but aggregated across all stages.

## Data Flow

DEV.Sep25 is the "current" model. Output_V2 references it via formulas like:
- `=+DEV.Sep25!Q36` (To Date value for a specific line)
- `=+DEV.Sep25!P36` (Total value)
- `=+DEV.Sep25!$Q$3` (Actuals cutoff date)

The control panel in Output_V2 may switch between DEV sheets (DEV.Sep25, DEV.Jul25, DEV.FY26B)
for Current/Previous/Budget comparisons.
