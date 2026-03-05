# V1 Reference

These documents describe design decisions made during v1 development. They are preserved as historical context explaining *why* v2 was built the way it was. They do not describe v2's implementation.

## Files

| File | Original purpose |
|---|---|
| `project-review.md` | Full audit of v1 codebase: 13 known issues, critical/medium/low findings |
| `phase1-trust-accuracy.md` | NCF series naming bug, transaction safety, spreadsheet extraction |
| `phase2-deployment.md` | Deployment readiness and infrastructure design |
| `phase3-powerbi.md` | PowerBI views design |
| `phase5-hardening.md` | Production hardening design |

## How to use these

When a v2 design decision needs justification, trace it back here. For example: "why are phase columns normalised?" → see `project-review.md` issue #4 and `phase3-powerbi.md`.

Do not treat any of these as specifications for v2 behaviour. The authoritative v2 specs are:
- `docs/plans/2026-03-05-v2-architecture.md` — full architecture and task breakdown
- `docs/pnl-spec.md` — P&L derivation formulas
- `docs/calc_rules.json` — formula specification
- `CLAUDE.md` — project conventions and TDD mandate
