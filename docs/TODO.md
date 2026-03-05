# Outstanding Work

## Backlog

### 1. Disable Delete All Imports API in production
The `DELETE /api/v1/imports` endpoint wipes all data. Must be disabled or protected in production environments (e.g., behind an admin auth gate or environment variable flag).

### 2. Data entry grid — currency formatting and field sizing
- Input fields don't display correct currency formatting
- Text fields are too small for the numbers being entered
- Need to improve cell width and add currency formatting to the editable cells in `DataEntryGrid.jsx`

### 3. Floating-point precision strategy for all views
- Delta percentages and computed values across all tabs can show small discrepancies due to floating-point precision differences between backend-stored values and displayed (rounded) values
- Need a definitive, project-wide solution (e.g., consistent rounding strategy, Decimal handling, or frontend-computed deltas) to prevent regressions across all views (Phases, P&L, Per-Delivery, etc.)
- Brainstorm session needed to evaluate approaches

### 4. Phase completion percentage in Dashboard overview
- Image 6 shows a "% Complete (Phase 1)" KPI card displaying 100.0% for Deliveries
- Question: how useful is it to show a percentage score for a single phase in the overview?
- Could we show it for the **current** phase instead? Is it possible to determine which phase is currently active?
- Needs design discussion on what "current phase" means and how to detect it from the data

### ~~5. Deliveries row shows zero in P&L tab~~ (Fixed)

### ~~6. Deliveries row shows zero in Phase Comparison tab~~ (Fixed)
