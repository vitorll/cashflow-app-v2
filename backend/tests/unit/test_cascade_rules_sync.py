"""Phase B4 — calc_rules.json contract guard.

docs/calc_rules.json is the canonical formula specification (CLAUDE.md rule).
backend/app/services/calc_rules.json is the runtime copy loaded by cascade_service.py.

These tests validate the runtime copy matches the expected formula spec. The
expected rules below are the source of truth for what the runtime JSON must contain.

If a rule needs to change: update docs/calc_rules.json, update EXPECTED_RULES below,
update the golden file fixture, verify the E2E test still passes. Never edit
backend/app/services/calc_rules.json directly without updating docs/calc_rules.json first.
"""

import json
from pathlib import Path

RUNTIME = Path(__file__).parent.parent.parent / "app" / "services" / "calc_rules.json"

# Canonical rule definitions — mirrors docs/calc_rules.json exactly.
# Any change here must also be reflected in docs/calc_rules.json.
EXPECTED_RULES = [
    {"field": "net_revenue",          "op": "subtract", "inputs": ["gross_revenue", "sales_costs"]},
    {"field": "subtotal_direct_cost", "op": "sum",      "inputs": ["primary_build", "contingency"]},
    {"field": "subtotal_overheads",   "op": "sum",      "inputs": ["marketing", "admin_overheads"]},
    {"field": "gross_cash_flow",      "op": "subtract", "inputs": ["net_revenue", "subtotal_direct_cost", "subtotal_overheads"]},
    {"field": "subtotal_capex",       "op": "sum",      "inputs": ["infrastructure", "civil_works", "landscaping", "amenities", "professional_fees", "regulatory_fees", "other", "contingency_civil_works", "contingency_amenities", "ancillary_build_capex"]},
    {"field": "net_cash_flow",        "op": "subtract", "inputs": ["gross_cash_flow", "subtotal_capex"]},
]


def test_calc_rules_json_exists():
    """Runtime calc_rules.json must exist at the expected path."""
    assert RUNTIME.exists(), f"Runtime calc_rules.json not found: {RUNTIME}"


def test_calc_rules_json_matches_expected_spec():
    """Runtime calc_rules.json must exactly match the expected formula spec.

    If this test fails: update docs/calc_rules.json AND EXPECTED_RULES above
    to reflect the intended change, then copy docs/calc_rules.json to
    backend/app/services/calc_rules.json.
    """
    rules = json.loads(RUNTIME.read_text())
    assert rules == EXPECTED_RULES, (
        "calc_rules.json does not match the expected spec.\n"
        "To change a rule: update docs/calc_rules.json + EXPECTED_RULES in this file "
        "+ the golden file fixture + verify E2E test passes."
    )


def test_calc_rules_json_has_required_fields():
    """Each rule in calc_rules.json must have 'field', 'op', and 'inputs' keys."""
    rules = json.loads(RUNTIME.read_text())
    for i, rule in enumerate(rules):
        assert "field" in rule, f"Rule {i} missing 'field': {rule}"
        assert "op" in rule, f"Rule {i} missing 'op': {rule}"
        assert "inputs" in rule, f"Rule {i} missing 'inputs': {rule}"
        assert rule["op"] in ("sum", "subtract"), (
            f"Rule {i} has unknown op {rule['op']!r} — must be 'sum' or 'subtract'"
        )
        assert isinstance(rule["inputs"], list) and len(rule["inputs"]) >= 1, (
            f"Rule {i} must have at least 1 input, got: {rule['inputs']}"
        )


def test_calc_rules_json_net_cash_flow_is_last():
    """net_cash_flow must be the final rule — it depends on gross_cash_flow and subtotal_capex.

    Rule order in calc_rules.json defines cascade execution order. net_cash_flow
    must be last because it depends on gross_cash_flow (rule 4) and subtotal_capex (rule 5).
    Swapping order would cause a KeyError in cascade_service._compute_n12m().
    """
    rules = json.loads(RUNTIME.read_text())
    assert rules[-1]["field"] == "net_cash_flow", (
        f"net_cash_flow must be the last rule, got: {rules[-1]['field']!r}. "
        "Changing this order breaks the cascade dependency chain."
    )


def test_calc_rules_json_six_rules_present():
    """calc_rules.json must contain exactly 6 rules (matching EXPECTED_RULES)."""
    rules = json.loads(RUNTIME.read_text())
    assert len(rules) == 6, (
        f"Expected 6 calc rules, got {len(rules)}. "
        "Update EXPECTED_RULES, docs/calc_rules.json, and the golden file fixture."
    )
