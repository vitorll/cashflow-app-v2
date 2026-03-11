"""Cascade recalculation service — Phase B4.

Pure Python, no DB calls. Accepts the dict produced by parse_excel() and
returns a fully-computed result dict with per_delivery_rows, ncf_series,
and pnl_summaries appended.

All financial arithmetic uses Decimal, quantized to 4dp ROUND_HALF_UP.
Enum types are enforced throughout — never string literals for phases,
sections, or series types.
"""
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

from app.domain.enums import Phase, SectionType, SeriesType, PHASES

# ---------------------------------------------------------------------------
# Rounding
# ---------------------------------------------------------------------------

Q4 = Decimal("0.0001")


def _q(value: Decimal) -> Decimal:
    return value.quantize(Q4, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Computed row metadata — canonical from golden file / spec
# ---------------------------------------------------------------------------

CALC_ROW_META = {
    "net_revenue":          {"display_name": "Net Revenue",          "sort_order": 17, "section": SectionType.revenue},
    "subtotal_direct_cost": {"display_name": "Subtotal Direct Cost", "sort_order": 18, "section": SectionType.direct_costs},
    "subtotal_overheads":   {"display_name": "Subtotal Overheads",   "sort_order": 19, "section": SectionType.overheads},
    "gross_cash_flow":      {"display_name": "Gross Cash Flow",      "sort_order": 20, "section": SectionType.overheads},
    "subtotal_capex":       {"display_name": "Subtotal Capex",       "sort_order": 21, "section": SectionType.capex},
    "net_cash_flow":        {"display_name": "Net Cash Flow",        "sort_order": 22, "section": SectionType.capex},
}

# ---------------------------------------------------------------------------
# Load calc rules from JSON once at module import time
# ---------------------------------------------------------------------------

_RULES_PATH = Path(__file__).parent / "calc_rules.json"

with open(_RULES_PATH) as _f:
    _CALC_RULES: list[dict] = json.load(_f)


# ---------------------------------------------------------------------------
# Step 1 — N12M computed rows
# ---------------------------------------------------------------------------


def _compute_n12m(n12m_line_items: list[dict]) -> list[dict]:
    """Apply calc_rules to produce 6 computed n12m rows appended to the input rows."""
    # Build a lookup: line_item -> {month -> Decimal value}
    by_item: dict[str, dict[str, Decimal]] = {}
    for row in n12m_line_items:
        by_item[row["line_item"]] = {e["month"]: e["value"] for e in row["entries"]}

    # Determine month set (preserve insertion order from first row)
    months = [e["month"] for e in n12m_line_items[0]["entries"]] if n12m_line_items else []

    computed_rows = []
    for rule in _CALC_RULES:
        field = rule["field"]
        op = rule["op"]
        inputs = rule["inputs"]

        entries = []
        for month in months:
            values = [by_item[inp][month] for inp in inputs]
            if op == "sum":
                result = sum(values, Decimal("0"))
            elif op == "subtract":
                result = values[0] - sum(values[1:], Decimal("0"))
            else:
                raise ValueError(f"Unknown op: {op!r}")

            result = _q(result)
            entries.append({"month": month, "value": result})

        meta = CALC_ROW_META[field]
        computed_row = {
            "section": meta["section"],
            "line_item": field,
            "display_name": meta["display_name"],
            "is_calculated": True,
            "sort_order": meta["sort_order"],
            "entries": entries,
        }
        computed_rows.append(computed_row)

        # Make this computed row available to subsequent rules
        by_item[field] = {e["month"]: e["value"] for e in entries}

    return list(n12m_line_items) + computed_rows


# ---------------------------------------------------------------------------
# Step 2 — NCF series
# ---------------------------------------------------------------------------


def _compute_ncf_series(n12m_line_items: list[dict], version_type: str) -> list[dict]:
    """Build periodic and cumulative NCF series from the net_cash_flow computed row."""
    ncf_row = next(r for r in n12m_line_items if r["line_item"] == "net_cash_flow")
    # Entries are already in month order from _compute_n12m
    entries = sorted(ncf_row["entries"], key=lambda e: e["month"])

    periodic = []
    for entry in entries:
        periodic.append({
            "series_type": SeriesType.periodic,
            "series_name": version_type,
            "month": entry["month"],
            "value": _q(entry["value"]),
        })

    cumulative = []
    running = Decimal("0")
    for entry in entries:
        running = _q(running + entry["value"])
        cumulative.append({
            "series_type": SeriesType.cumulative,
            "series_name": version_type,
            "month": entry["month"],
            "value": running,
        })

    return periodic + cumulative


# ---------------------------------------------------------------------------
# Step 3 — Per delivery rows
# ---------------------------------------------------------------------------


def _compute_per_delivery_rows(
    phase_comparison_rows: list[dict],
    delivery_counts: list[dict],
) -> list[dict]:
    """Compute per-delivery figures for gross_revenue only, for PHASES + total."""
    # Build delivery count lookup by phase
    count_by_phase: dict[Phase, int] = {dc["phase"]: dc["count"] for dc in delivery_counts}

    # Build phase_comparison lookup: (line_item, phase) -> current
    pc_lookup: dict[tuple[str, Phase], Optional[Decimal]] = {
        (r["line_item"], r["phase"]): r["current"]
        for r in phase_comparison_rows
    }

    # Only gross_revenue is tracked per delivery — revenue per unit settled is the
    # key business metric. Other line items (costs, capex) are not normalised per
    # delivery at this stage. When the excel_templates system is built (future phase),
    # this list will be driven by template config rather than hardcoded here.
    line_item = "gross_revenue"
    rows = []

    for phase in PHASES:
        count = count_by_phase.get(phase, 0)
        pc_current = pc_lookup.get((line_item, phase))
        if count > 0 and pc_current is not None:
            current: Optional[Decimal] = _q(Decimal(str(pc_current)) / Decimal(count))
        else:
            current = None

        rows.append({
            "line_item": line_item,
            "phase": phase,
            "current": current,
            "budget": None,
            "delta": None,
            "delta_pct": None,
        })

    # Total: sum p1..p5 current from phase_comparison (NOT the Phase.total row)
    total_deliveries = sum(count_by_phase.get(p, 0) for p in PHASES)
    if total_deliveries > 0:
        phase_sum = sum(
            Decimal(str(pc_lookup[(line_item, p)]))
            for p in PHASES
            if (line_item, p) in pc_lookup and pc_lookup[(line_item, p)] is not None
        )
        total_current: Optional[Decimal] = _q(phase_sum / Decimal(total_deliveries))
    else:
        total_current = None

    rows.append({
        "line_item": line_item,
        "phase": Phase.total,
        "current": total_current,
        "budget": None,
        "delta": None,
        "delta_pct": None,
    })

    return rows


# ---------------------------------------------------------------------------
# Step 4 — PnL summaries
# ---------------------------------------------------------------------------


def _sum_n12m(n12m_line_items: list[dict], line_item: str) -> Decimal:
    """Sum all monthly entries for a given line_item across all months."""
    row = next((r for r in n12m_line_items if r["line_item"] == line_item), None)
    if row is None:
        return Decimal("0")
    return sum((e["value"] for e in row["entries"]), Decimal("0"))


def _compute_pnl_summaries(
    n12m_line_items: list[dict],
    delivery_counts: list[dict],
) -> list[dict]:
    """Compute 7 PnL summary rows from n12m totals and delivery counts."""
    total_deliveries = sum(dc["count"] for dc in delivery_counts)

    def _rate(total: Decimal) -> Optional[Decimal]:
        if total_deliveries == 0:
            return None
        return _q(total / Decimal(total_deliveries))

    gross_revenue_sum = _sum_n12m(n12m_line_items, "gross_revenue")
    subtotal_dc_sum = _sum_n12m(n12m_line_items, "subtotal_direct_cost")
    sales_costs_sum = _sum_n12m(n12m_line_items, "sales_costs")
    marketing_sum = _sum_n12m(n12m_line_items, "marketing")
    subtotal_capex_sum = _sum_n12m(n12m_line_items, "subtotal_capex")

    revenue_total = _q(gross_revenue_sum)
    cogs_total = _q(-subtotal_dc_sum)
    gross_profit_total = _q(revenue_total + cogs_total)
    sm_total = _q(-(sales_costs_sum + marketing_sum))
    direct_costs_total = _q(-subtotal_capex_sum)
    net_profit_total = _q(gross_profit_total + sm_total + direct_costs_total)
    deliveries_total = _q(Decimal(total_deliveries))

    def _row(line_item: str, sort_order: int, current_total: Decimal, include_rate: bool = True) -> dict:
        return {
            "line_item": line_item,
            "sort_order": sort_order,
            "budget_total": None,
            "current_total": current_total,
            "delta_total": None,
            "budget_rate": None,
            "current_rate": _rate(current_total) if include_rate else None,
            "delta_rate": None,
        }

    return [
        {
            "line_item": "deliveries",
            "sort_order": 1,
            "budget_total": None,
            "current_total": deliveries_total,
            "delta_total": None,
            "budget_rate": None,
            "current_rate": None,  # rate not applicable for count rows
            "delta_rate": None,
        },
        _row("revenue",             2, revenue_total),
        _row("cogs",                3, cogs_total),
        _row("gross_profit",        4, gross_profit_total),
        _row("sales_and_marketing", 5, sm_total),
        _row("direct_costs",        6, direct_costs_total),
        _row("net_profit",          7, net_profit_total),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_cascade(parsed_data: dict) -> dict:
    """Run the full cascade recalculation pipeline.

    Accepts the dict produced by parse_excel() and returns a new dict
    containing all inputs plus the three computed collections:
    per_delivery_rows, ncf_series, and pnl_summaries.

    Pure function — no DB calls, no side effects.
    """
    import_meta = parsed_data["import_meta"]
    delivery_counts = parsed_data["delivery_counts"]
    n12m_line_items = parsed_data["n12m_line_items"]
    phase_comparison_rows = parsed_data["phase_comparison_rows"]

    # Step 1: compute n12m rows (input rows + 6 computed rows)
    full_n12m = _compute_n12m(n12m_line_items)

    # Step 2: NCF series from net_cash_flow n12m row
    ncf_series = _compute_ncf_series(full_n12m, import_meta["version_type"])

    # Step 3: per delivery rows (gross_revenue only)
    per_delivery_rows = _compute_per_delivery_rows(phase_comparison_rows, delivery_counts)

    # Step 4: PnL summaries
    pnl_summaries = _compute_pnl_summaries(full_n12m, delivery_counts)

    return {
        "import_meta": import_meta,
        "delivery_counts": delivery_counts,
        "n12m_line_items": full_n12m,
        "phase_comparison_rows": phase_comparison_rows,
        "per_delivery_rows": per_delivery_rows,
        "ncf_series": ncf_series,
        "pnl_summaries": pnl_summaries,
    }
