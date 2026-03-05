# Output_V2 Sheet Documentation

## Layout

The Output_V2 sheet (rows 2-164, columns E-FY) is the primary output view
that the app reads. It aggregates data from the individual DEV model sheets.

## Section Map

| Section | Rows | Columns | Key Content |
|---------|------|---------|-------------|
| Control Panel | 3-11 | E-N | Stage selector dropdowns, PCG report month, actuals date |
| Stage 1 Summary | 15-40 | E-R | Current vs Previous vs Budget for selected stage |
| WOL Summary | 43-67 | E-R | Whole-of-Life totals with same structure |
| All Stages | 70-94 | E-X | Budget and Current columns for each of 5 stages + WOP |
| Per Settlement | 95-116 | E-X | Same as All Stages but divided by settlement count ($k) |
| P&L | 126-134 | E-R | Revenue, COGS, Gross Profit, S&M, Dev Costs, Net Profit |
| NCF | 126-136 | S-FY | Cumulative + Periodic NCF (Current, Previous, Budget, Max, Min) |
| N12M | 139-164 | S-AE | 12-month forward cash flow by line item |

## Formula Patterns

### Control Panel (rows 3-11)
- Row 10: PCG Report Month — hardcoded dates
- Row 11: Adopted Actual To Date — references like `=+DEV.Sep25!$Q$3`

### Summary Tables (rows 15-94)
- "To Date" column: `=+DEV.Sep25!Q{row}` (references the TO DATE column in the DEV sheet)
- "TOTAL" column: `=+DEV.Sep25!P{row}`
- Delta columns: simple arithmetic `=I{row}-J{row}`
- Percentage columns: `=IF(J{row}=0,0,L{row}/J{row})`

### NCF (rows 126-136)
- Each cell references the corresponding month column in the DEV sheet
- Cumulative series accumulate periodic values
- Max/Min series track envelope bounds

### N12M (rows 139-164)
- Direct references to the 12-month forward window in the DEV sheet
- Line items: Revenue, Selling Costs, Net Revenue, Home Build, Contingency,
  Marketing, Overheads, Capex categories, Dev Cash Flow, Settlements, Home Orders

## Cross-Sheet References

The following sheets are referenced by Output_V2 formulas:
- `DEV.FY26B`
- `DEV.Jul25`
- `DEV.Sep25`
