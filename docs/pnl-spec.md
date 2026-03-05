# P&L Derivation Specification

This is the authoritative specification for P&L calculations. The E2E test fixture asserts against these exact derivations. Any change to these formulas requires: (1) update this spec, (2) update the test fixture, (3) verify the E2E test passes.

---

## Source Fields

All values are summed across all 12 months from `n12m_line_items` for a given import:

| Field | Source `line_item` key | Notes |
|---|---|---|
| Revenue | `gross_revenue` | Total revenue |
| Direct costs | `subtotal_direct_cost` | Stored as positive |
| Sales costs | `sales_costs` | Component of Sales & Marketing |
| Marketing | `marketing` | Component of Sales & Marketing |
| Capital expenditure | `subtotal_capex` | Stored as positive |
| Deliveries | `delivery_counts` total | From `delivery_counts` table, NOT from `n12m_line_items` |

---

## P&L Line Item Derivations

```
Revenue          = gross_revenue
COGS             = -(subtotal_direct_cost)
Gross Profit     = Revenue + COGS
Sales & Marketing = -(sales_costs + marketing)
Direct Costs     = -(subtotal_capex)
Net Profit       = Gross Profit + Sales & Marketing + Direct Costs
Deliveries       = sum of delivery_counts across all phases
```

**Sign convention:** Costs are stored as positive values in the database. The P&L negates them to reflect them as outflows.

---

## Rate Columns

Applies to all rows except Deliveries:

```
current_rate = current_total / current_delivery_count   (null if count = 0 or null)
budget_rate  = budget_total / budget_delivery_count     (null if count = 0 or null)
delta_rate   = current_rate - budget_rate               (null if either rate is null)
```

Deliveries row: `current_rate`, `budget_rate`, `delta_rate` are all `null`.

---

## Delta Column

```
delta_total = current_total - budget_total   (null if budget_total is null)
```

---

## Display Order

```
1. Deliveries
2. Revenue
3. COGS
4. Gross Profit
5. Sales & Marketing
6. Direct Costs
7. Net Profit
```

---

## Notes

- This spec was extracted from `cascade.py` (`recalculate_pnl`) in the v1 codebase on 2026-03-05.
- The v2 implementation must match these formulas exactly and is verified by the E2E golden file test.
- If the source Excel uses different formulas, this spec must be updated and re-verified before any test fixtures are regenerated.
