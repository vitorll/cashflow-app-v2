# Cross-Sheet Data Flow Reference

This document maps formula references between sheets in Project.xlsx.

## Output_V2 -> DEV Sheets

Output_V2 pulls data from the DEV model sheets. The control panel (rows 5-7)
determines which sheet maps to "Current", "Previous", and "Budget".

### Reference Pattern

```
Output_V2 cell  =  DEV.{version}!{column}{row}
```

Where:
- Column Q = "To Date" (actuals through the adopted date)
- Column P = "Total" (full project life)
- Column R = "To Go" (forecast remaining)
- Columns S+ = Monthly time-series

### Formula References by Target Sheet

#### DEV.FY26B

| Output_V2 Cell | Formula |
|----------------|--------|
| I11 | `=+DEV.FY26B!$Q$3` |
| T136 | `=+DEV.FY26B!AA369` |
| U136 | `=+DEV.FY26B!AB369` |
| V136 | `=+DEV.FY26B!AC369` |
| W136 | `=+DEV.FY26B!AD369` |
| X136 | `=+DEV.FY26B!AE369` |
| Y136 | `=+DEV.FY26B!AF369` |
| Z136 | `=+DEV.FY26B!AG369` |
| AA136 | `=+DEV.FY26B!AH369` |
| AB136 | `=+DEV.FY26B!AI369` |
| AC136 | `=+DEV.FY26B!AJ369` |
| AD136 | `=+DEV.FY26B!AK369` |
| AE136 | `=+DEV.FY26B!AL369` |
| AF136 | `=+DEV.FY26B!AM369` |
| AG136 | `=+DEV.FY26B!AN369` |
| AH136 | `=+DEV.FY26B!AO369` |
| AI136 | `=+DEV.FY26B!AP369` |
| AJ136 | `=+DEV.FY26B!AQ369` |
| AK136 | `=+DEV.FY26B!AR369` |
| AL136 | `=+DEV.FY26B!AS369` |
| AM136 | `=+DEV.FY26B!AT369` |
| AN136 | `=+DEV.FY26B!AU369` |
| AO136 | `=+DEV.FY26B!AV369` |
| AP136 | `=+DEV.FY26B!AW369` |
| AQ136 | `=+DEV.FY26B!AX369` |
| AR136 | `=+DEV.FY26B!AY369` |
| AS136 | `=+DEV.FY26B!AZ369` |
| AT136 | `=+DEV.FY26B!BA369` |
| AU136 | `=+DEV.FY26B!BB369` |
| AV136 | `=+DEV.FY26B!BC369` |
| ... | (133 more references) |

#### DEV.Jul25

| Output_V2 Cell | Formula |
|----------------|--------|
| H11 | `=+DEV.Jul25!$Q$3` |
| T135 | `=+DEV.Jul25!AA369` |
| U135 | `=+DEV.Jul25!AB369` |
| V135 | `=+DEV.Jul25!AC369` |
| W135 | `=+DEV.Jul25!AD369` |
| X135 | `=+DEV.Jul25!AE369` |
| Y135 | `=+DEV.Jul25!AF369` |
| Z135 | `=+DEV.Jul25!AG369` |
| AA135 | `=+DEV.Jul25!AH369` |
| AB135 | `=+DEV.Jul25!AI369` |
| AC135 | `=+DEV.Jul25!AJ369` |
| AD135 | `=+DEV.Jul25!AK369` |
| AE135 | `=+DEV.Jul25!AL369` |
| AF135 | `=+DEV.Jul25!AM369` |
| AG135 | `=+DEV.Jul25!AN369` |
| AH135 | `=+DEV.Jul25!AO369` |
| AI135 | `=+DEV.Jul25!AP369` |
| AJ135 | `=+DEV.Jul25!AQ369` |
| AK135 | `=+DEV.Jul25!AR369` |
| AL135 | `=+DEV.Jul25!AS369` |
| AM135 | `=+DEV.Jul25!AT369` |
| AN135 | `=+DEV.Jul25!AU369` |
| AO135 | `=+DEV.Jul25!AV369` |
| AP135 | `=+DEV.Jul25!AW369` |
| AQ135 | `=+DEV.Jul25!AX369` |
| AR135 | `=+DEV.Jul25!AY369` |
| AS135 | `=+DEV.Jul25!AZ369` |
| AT135 | `=+DEV.Jul25!BA369` |
| AU135 | `=+DEV.Jul25!BB369` |
| AV135 | `=+DEV.Jul25!BC369` |
| ... | (133 more references) |

#### DEV.Sep25

| Output_V2 Cell | Formula |
|----------------|--------|
| G11 | `=+DEV.Sep25!$Q$3` |
| T126 | `=+DEV.Sep25!AA7` |
| U126 | `=+DEV.Sep25!AB7` |
| V126 | `=+DEV.Sep25!AC7` |
| W126 | `=+DEV.Sep25!AD7` |
| X126 | `=+DEV.Sep25!AE7` |
| Y126 | `=+DEV.Sep25!AF7` |
| Z126 | `=+DEV.Sep25!AG7` |
| AA126 | `=+DEV.Sep25!AH7` |
| AB126 | `=+DEV.Sep25!AI7` |
| AC126 | `=+DEV.Sep25!AJ7` |
| AD126 | `=+DEV.Sep25!AK7` |
| AE126 | `=+DEV.Sep25!AL7` |
| AF126 | `=+DEV.Sep25!AM7` |
| AG126 | `=+DEV.Sep25!AN7` |
| AH126 | `=+DEV.Sep25!AO7` |
| AI126 | `=+DEV.Sep25!AP7` |
| AJ126 | `=+DEV.Sep25!AQ7` |
| AK126 | `=+DEV.Sep25!AR7` |
| AL126 | `=+DEV.Sep25!AS7` |
| AM126 | `=+DEV.Sep25!AT7` |
| AN126 | `=+DEV.Sep25!AU7` |
| AO126 | `=+DEV.Sep25!AV7` |
| AP126 | `=+DEV.Sep25!AW7` |
| AQ126 | `=+DEV.Sep25!AX7` |
| AR126 | `=+DEV.Sep25!AY7` |
| AS126 | `=+DEV.Sep25!AZ7` |
| AT126 | `=+DEV.Sep25!BA7` |
| AU126 | `=+DEV.Sep25!BB7` |
| AV126 | `=+DEV.Sep25!BC7` |
| ... | (295 more references) |

## DEV Sheet Internal Structure

Each DEV sheet (DEV.Sep25, DEV.Jul25, DEV.FY26B, etc.) follows the same
row/column layout. The Output_V2 formulas reference fixed row numbers,
meaning all DEV sheets must maintain identical row structure.

### Key Reference Points

| DEV Row | Content | Output_V2 Usage |
|---------|---------|-----------------|
| 3 | Actuals cutoff date (col Q) | Control panel row 11 |
| 6-10 | Timeline headers | N/A (used internally) |
| 12-208 | Stage details | Stage summaries, All Stages, Per Settlement |
| 210-342 | Per-stage P&L | P&L section |
| 345-369 | WOP summary | WOL summary |

### Column Mapping

| Column | Meaning |
|--------|---------|
| O | Budget |
| P | Total (Current forecast) |
| Q | To Date (Actuals) |
| R | To Go (Forecast remaining) |
| S-onwards | Monthly time-series (period 1 = Mar-21) |
