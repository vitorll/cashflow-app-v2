# Architecture Team Report: Cashflow App v2 Rebuild

**Date:** 2026-03-05
**Status:** Architecture complete — awaiting Roy's requirements output (in progress)
**Team:** Moss (Architect), Roy (BA), Jen (Devil's Advocate)

---

## Context

The cashflow projection app (React 19 + FastAPI + PostgreSQL) was built without TDD. Tests were added after the fact, leaving coverage gaps — especially around cascade failure paths. A mid-project domain rename (stages/settlements/WOP → phases/deliveries/total) left schema debt. 13 documented issues exist in the current implementation. The user wants to rebuild the same app from scratch in a new repository, applying all lessons learned, with TDD from day one, agent team workflows, and a clean schema.

---

## Executive Summary

Rebuild the cashflow app in a new repository keeping the same tech stack (React 19 + FastAPI + PostgreSQL), same feature set (5 tabs), and same UI design language — but with: (1) TDD enforced from day one via RED/GREEN/REFACTOR with web-team agents, (2) a normalised schema replacing JSON phase columns, (3) PostgreSQL native enums as a single source of truth for domain concepts, (4) a config-driven Excel parser, and (5) CI coverage gates blocking merges below 80% backend / 70% frontend. All 13 known issues have a specific resolution mapped to a task.

---

## System Design (Moss)

### What Stays Identical
- Stack: React 19 + Vite 7 (JSX, no TypeScript), FastAPI + Python 3.11, PostgreSQL 16, Docker, Alembic, Gunicorn + Uvicorn
- UI: Dark theme, DM Serif Display + IBM Plex Sans, `#bb86fc` purple accent
- Domain model: Phases (p1–p5), Deliveries, Sections, N12M, NCF, Budget/Current/Previous
- Deployment: Single-tenant, customer-hosted Docker + managed PostgreSQL + HTTPS ingress
- 5-tab UI: Dashboard, Forecast, Phase Comparison, P&L, Data Entry

### Key Structural Changes

| Area | Old | New | Lesson Fixed |
|---|---|---|---|
| Excel parser | Hardcoded row/column mapping | Config-driven `TemplateParser` + `excel_templates` DB table | #1 |
| JSON phase columns | `{p1: val, p2: val, ...}` | Normalised `phase_comparison_rows` / `per_delivery_rows` | #4 |
| Numeric types | Mixed FLOAT/NUMERIC(18,2) | Uniform `NUMERIC(18,4)` everywhere | #7 |
| Delta calculation | Python floats | PostgreSQL `GENERATED ALWAYS AS` computed columns | #7 |
| NCF series naming | Date-stamped strings in parser, generic in cascade | `SeriesType` enum enforced at parse time | #3 |
| Test strategy | Post-hoc | TDD (RED/GREEN/REFACTOR) + coverage gates | #10 |
| Logging | None | structlog + request ID middleware | #13 |
| CORS | Hardcoded localhost | Env-var driven (`ALLOWED_ORIGINS`) | #12 |
| Request caching | Custom `useApi.js` | TanStack Query v5 | #8 |
| Bulk delete | Unguarded | Soft-delete + confirmation token | #9 |
| E2E validation | None | Golden file fixture + E2E test before any service code | #2 |

### Schema Improvements From Day One

**PostgreSQL native enums** (single source of truth):
```sql
CREATE TYPE phase_enum AS ENUM ('p1','p2','p3','p4','p5','total');
CREATE TYPE section_enum AS ENUM ('revenue','direct_costs','overheads','capex','contingency');
CREATE TYPE series_type_enum AS ENUM ('cumulative','periodic');
CREATE TYPE import_status_enum AS ENUM ('pending','processing','complete','failed');
CREATE TYPE version_type_enum AS ENUM ('budget','current','forecast');
CREATE TYPE source_type_enum AS ENUM ('excel','manual','api');
```

**Phase comparison / per delivery — normalised (replaces JSON columns):**
```sql
CREATE TABLE phase_comparison_rows (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_id   UUID NOT NULL REFERENCES imports(id) ON DELETE CASCADE,
    line_item   TEXT NOT NULL,
    phase       phase_enum NOT NULL,
    budget      NUMERIC(18,4),
    current     NUMERIC(18,4),
    delta       NUMERIC(18,4) GENERATED ALWAYS AS (current - budget) STORED,
    delta_pct   NUMERIC(18,4) GENERATED ALWAYS AS (
                    CASE WHEN budget = 0 THEN NULL
                         ELSE ((current - budget) / ABS(budget)) * 100
                    END) STORED,
    UNIQUE (import_id, line_item, phase)
);
-- per_delivery_rows: identical structure
```

**New tables:**
- `excel_templates` — stores template config (JSONB), linked to `imports.template_id`
- `imports.deleted_at` — soft delete column; hard delete admin endpoint separate

**All FLOAT columns** replaced with `NUMERIC(18,4)`. Python domain enums in `domain/enums.py` mirror DB enums exactly (drift tested in CI).

### Repository Structure

```
cashflow-app-v2/
├── .github/workflows/
│   ├── ci.yml          # PR gate: parallel backend-test + frontend-test + lint
│   └── deploy.yml      # Main branch: build image → push → health check
├── backend/
│   ├── app/
│   │   ├── domain/
│   │   │   ├── enums.py       # Single source of truth — all phase/section/series enums
│   │   │   ├── models.py      # SQLAlchemy ORM models
│   │   │   └── schemas.py     # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── cascade_service.py
│   │   │   ├── calc_rules.py
│   │   │   └── excel_parser/
│   │   │       ├── base.py          # Abstract parser interface
│   │   │       ├── template_parser.py
│   │   │       └── templates/       # Customer template YAMLs
│   │   ├── routers/
│   │   ├── middleware/
│   │   │   ├── request_id.py
│   │   │   └── logging.py
│   │   ├── config.py          # Pydantic Settings — all env vars
│   │   └── db/
│   ├── tests/
│   │   ├── fixtures/
│   │   │   ├── sample_import.xlsx
│   │   │   └── expected_output.json  # Golden file — created BEFORE service code
│   │   ├── unit/
│   │   └── integration/
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/client.js           # Axios instance
│   │   ├── hooks/queries/          # TanStack Query hooks (one file per domain)
│   │   └── components/
│   ├── tests/unit/ + tests/integration/
│   └── package.json
└── docs/                           # Carry forward from current repo
```

**Structural rule:** `domain/enums.py` is the canonical definition. Nothing else defines phase/section/series names.

### CI/CD

**PR gate (parallel):**
- `backend-test`: pytest + `--cov-fail-under=80` — hard gate
- `frontend-test`: vitest + `--coverage.thresholds.lines=70` — hard gate
- `lint`: ruff (backend) + eslint (frontend)

**Deploy (main branch):** build multi-stage Docker image → push to customer registry → poll `/health` → deployment status.

**`GET /health` returns:** `{status, version, db, alembic_head}` — minimum viable observability.

---

## Challenges & Assumptions (Jen)

Jen's core challenge: **The current app works.** 163 tests. A working deployment. Real users. So what user problem does a rewrite solve that fixing the current codebase can't?

**Key challenges raised:**
1. What happens to existing users during the rebuild? Going back to Excel is not an acceptable continuity plan.
2. TDD discipline doesn't require a new codebase — it could be introduced incrementally on the existing one.
3. Schema rename debt is a migration script, not a rewrite justification.
4. Rewrites always take longer than expected and lose undocumented edge-case knowledge baked into existing code.
5. Timeline pressure during a rewrite is exactly when TDD discipline gets "temporarily" dropped.

**Jen's conditions for the rebuild to justify itself:**
- Zero regression in user-facing behaviour before the old app is retired
- A concrete, tested data migration path for existing data
- A side-by-side period running both apps until parity is confirmed
- Must reach feature parity within 3 months or the business case has failed

**Jen's simplest alternative (not recommended by Moss, but on record):** Fix the actual problems in place — migration scripts for schema debt, add TDD going forward, refactor the Excel parser with tests, add auth as an additive feature. No rewrite needed.

---

## Requirements (Roy)

### Day One: Must Work Before the Old App Gets Switched Off

| Story | Requirement |
|---|---|
| US-01 | Manual data entry — enter values per phase/month/line-item, cascade runs all 7 steps, currency formatting, Tab/Enter/Escape keyboard nav, calculated rows preview live, cascade failure returns structured error with no partial writes |
| US-02 | Delivery count entry — editable per phase, triggers full cascade, per-delivery metrics divide correctly |
| US-03 | 12-Month Forecast tab — N12M by section with actual/forecast distinction, calculated rows visually distinct |
| US-04 | Phase Comparison tab — budget vs current vs delta ($, %) for all 5 phases + total, no floating-point divergence between dollar and percentage deltas |
| US-05 | P&L tab — Deliveries, Revenue, COGS, Gross Profit, Sales & Marketing, Direct Costs, Net Profit with rate columns |
| US-06 | NCF chart — current/previous/budget series with dynamic labels (no hardcoded date strings), cumulative = running sum of periodic |
| US-07 | Excel import — upload file, parse all tables, link budget/previous imports, fail cleanly with no partial data |
| US-08 | Dashboard KPIs — Net Revenue, Gross Cash Flow, reporting period from existing import data |

### Defer to Phase 2

Authentication, undo/redo, copy/paste from Excel, configurable parser, RBAC, audit trail, additional PowerBI views, mobile/responsive design, auto-save, cross-phase preview in Data Entry.

### Requirement Gaps — Answers Needed Before A2

**GAP-01: Schema fixes in the rebuild?**
`phase_summaries` currently only writes data for p1 (`("per_phase", "p1")` hardcoded in cascade). Is this intentional? JSON columns on `phase_comparisons`/`per_deliveries` — fix in rebuild (normalise) or carry forward?

**GAP-02: Floating-point precision strategy**
Decide before writing tests: `NUMERIC(18,4)` everywhere with display rounding at API layer, or frontend computes deltas? The TODO marks this unresolved. Cannot be "decided later."

**GAP-03: Phase count — fixed or configurable?**
p1–p5 is currently hardcoded in the cascade. If fixed, document it and use a PostgreSQL enum. If configurable, that changes the schema substantially.

**GAP-04: Import version relationship (budget/current/previous)**
Who links these at import creation? Can a current import exist without a budget link? How does a user pick which existing import is the budget baseline? The cascade handles null IDs gracefully but the UI workflow is undefined.

**GAP-05: P&L derivation formulas — where is the spec?**
The P&L step in cascade.py defines: `COGS = -(subtotal_direct_cost)`, `Gross Profit = revenue + COGS`, etc. This is not documented anywhere except in the code. If the code is wrong, there is no spec to catch it. The rebuild needs a written P&L spec before test fixtures can be created.

**GAP-06: Authentication — which option, when?**
Option A: Cloud proxy (IAP/ALB/Easy Auth) — zero app code, configure at deploy. Option B: FastAPI JWT middleware. Option C: API key (gets to prod faster, not SSO). The current app was blocked from production by this. Pick one before the rebuild reaches Phase E.

**GAP-07: Excel-imported vs manually-entered imports — edit boundary**
`source_type: "excel" | "manual"` exists but the edit boundary is unclear. Can a user edit an Excel-imported record via Data Entry, or is it read-only after import? The cascade scaffolds `phase_inputs` only for manual imports. This affects the Data Entry tab UX design.

### Explicitly Out of Scope

- Multi-tenancy
- Data migration from current DB (**confirmed: start fresh**)
- Auth implementation (cloud proxy handles it)
- Configurable Excel parser UI/admin
- Undo/redo beyond Escape-to-revert
- Audit trail
- Mobile/responsive design
- Bulk delete confirmation flow (disable the endpoint instead)

### Success Metrics

| Metric | Standard |
|---|---|
| SM-01: Calculation parity | All 72 N12M calculated values + NCF + phase summaries + P&L match source Excel within $0.01 — verified by E2E test in CI |
| SM-02: Data entry round-trip | Enter → save → Forecast/Phase Comparison/P&L all show correct derived values — covered by integration test |
| SM-03: Test coverage | Backend ≥ 80%, frontend ≥ 70% — hard CI gates; every piece of business logic tested RED before GREEN |
| SM-04: Zero floating-point divergence | Delta % across all views independently verifiable from dollar values; no view shows a different number for the same metric |
| SM-05: Cascade failure is recoverable | Cascade error → structured API response, no partial writes, user can retry — verified by test |
| SM-06: Deployable | Docker image builds, `/health` returns DB status, CORS from env var, destructive bulk-delete disabled |

### TDD Process Requirements

**P-01:** RED before GREEN — failing test committed before implementation. "Tests after" = tests that already pass = useless.

**P-02:** Each of the 7 cascade steps has its own test module with known fixture inputs and exact output assertions (no mocking the DB — use a test database).

**P-03:** `calc_rules.json` is the specification. Both Python and JS evaluators are derived from it. Changing a formula requires: update JSON → update test → verify E2E passes.

**P-04:** E2E calculation parity test is gating — runs in CI on every push, build fails if it fails. Not optional.

**P-05:** Frontend tests use real Pydantic response shapes as fixture data. When a schema changes, fixtures break — that's the point.

**P-06:** If deleting a function/component/endpoint doesn't break any test, it has no TDD coverage. Code reviews enforce this.

---

## Task Breakdown

Ordered phases with TDD enforced at every step:

### Phase A: Foundation
- **A1** — Repo scaffold: Docker Compose, Alembic, Ruff, ESLint, Vitest, pytest all runnable. `GET /health` returns 200. No business logic.
- **A2** — Domain enums + base models: PostgreSQL enums → `domain/enums.py` → SQLAlchemy models → Pydantic schemas. CI test asserts enum values match DB.
- **A3** — Golden file fixture: Extract one complete real import from the current system. Save as `tests/fixtures/sample_import.xlsx` + `tests/fixtures/expected_output.json`. **Must exist before any service code is written.**

### Phase B: Core Data Pipeline (web-team)
- **B1** — All 10 DB migrations (including `excel_templates`, soft-delete on `imports`)
- **B2** — Excel `TemplateParser` + `SeriesType` enum enforced at parse time. Unit tests against golden file.
- **B3** — Import service + router (`POST /imports`, `GET /imports`, `DELETE /imports/{id}` soft-delete)
- **B4** — Cascade recalculation service (7 steps, all referencing `domain/enums.py`)
- **B5** — CALC_RULES engine + E2E test: import xlsx → cascade → assert output matches golden file

### Phase C: API Endpoints (web-team)
- **C1** — Forecast endpoint
- **C2** — Phase comparison endpoint (flat rows, not JSON)
- **C3** — P&L endpoint
- **C4** — Data entry endpoints (optimistic update → cascade cycle)
- **C5** — structlog + request ID middleware

### Phase D: Frontend (web-team, starts after C1)
- **D1** — API client + TanStack Query v5 setup
- **D2–D6** — Port each tab (Dashboard, Forecast, Phase Comparison, P&L, Data Entry) with TanStack Query hooks and tab-prefixed CSS class names
- **D7** — Import/export flow

### Phase E: Hardening
- **E1** — Env config audit (no hardcoded values anywhere)
- **E2** — CORS via `ALLOWED_ORIGINS` env var
- **E3** — Coverage gates enforced in CI
- **E4** — Production Docker build + health check

### Dependency Order

```
A1 → A2 → A3
              ↓
        B1 → B2 → B3 → B4 → B5
                               ↓
                   C1 → C2 → C3 → C4 → C5
                                        ↓
                         D1 → D2–D6 → D7
                                        ↓
                              E1 → E2 → E3 → E4
```

---

## Issue Resolution Map

| # | Issue | Resolution | Task |
|---|---|---|---|
| 1 | Hardcoded Excel parser | Config-driven `TemplateParser` + `excel_templates` table | B2 |
| 2 | No E2E calculation validation | Golden file fixture + cascade E2E test | A3 + B5 |
| 3 | NCF series naming bug | `SeriesType` enum enforced at parse time | B2 + B4 |
| 4 | JSON columns PowerBI-unfriendly | Normalised `phase_comparison_rows` + `per_delivery_rows` | B1 |
| 5 | No authentication | OIDC/SAML via cloud proxy (zero app code change) — documented | E1 |
| 6 | Mid-project rename debt | Clean schema from A2, all enums canonical | A2 |
| 7 | Floating-point precision | `NUMERIC(18,4)` everywhere, computed columns in PostgreSQL | A2 + B1 |
| 8 | No request caching | TanStack Query v5 | D1 |
| 9 | Bulk delete unprotected | Soft delete + confirmation token | B3 |
| 10 | Tests added after code | TDD + coverage gates | All phases |
| 11 | CSS class name bleeding | Tab-prefixed class names enforced from D2 onward | D2–D6 |
| 12 | CORS hardcoded | `ALLOWED_ORIGINS` env var | E2 |
| 13 | No structured logging | structlog + request ID middleware | C5 |

---

## Open Questions (Decisions Needed Before Development Starts)

1. **Golden file (blocks A3 and all of Phase B):** Who extracts `sample_import.xlsx` + `expected_output.json` from the current system?
2. **Phase count:** Fixed at p1–p5, or configurable? Affects `phase_enum` design in A2.
3. **P&L spec (blocks B5):** The P&L derivation formulas only exist in `cascade.py`. A written spec is needed before E2E test fixtures can be created.
4. **Floating-point strategy:** `NUMERIC(18,4)` with API-layer rounding (Moss's recommendation), or frontend-computed deltas? Affects A2 schema design.
5. **Excel-imported import edit boundary:** Can a user edit an Excel-imported record in the Data Entry tab, or is it read-only? Affects D6.
6. **Import version linking UX:** How does a user designate which existing import is the budget/previous baseline when uploading? Affects D7 import flow.
7. **Authentication approach:** Cloud proxy (Option A), FastAPI JWT (Option B), or API key (Option C)? Must be decided before Phase E.
8. **Side-by-side validation period:** How long before cutover? Roy recommends at least one full reporting cycle.

**Resolved:**
- Data migration: **Start fresh** — no migration from current DB needed

---

Architecture complete. When ready to build, invoke the `web-team` skill and reference this document.

---

## Kickoff Plan: Repository Initialisation

**Remote:** `git@github.com:vitorll/cashflow-app-v2.git`
**Local:** `~/Developer/cashflow-app-v2/`

### Step 1: Init repo and remote

```bash
git init ~/Developer/cashflow-app-v2
cd ~/Developer/cashflow-app-v2
git remote add origin git@github.com:vitorll/cashflow-app-v2.git
```

### Step 2: Copy reference documents from current repo

These carry over verbatim — they are source of truth, not code:

| Source (current repo) | Destination (new repo) | Purpose |
|---|---|---|
| `docs/` (entire folder) | `docs/` | Architecture, data dictionary, design docs, spreadsheet reference |
| `backend/app/calc_rules.json` | `docs/calc_rules.json` | Formula spec (canonical — both Python and JS derived from this) |
| `skills/` symlinks | Recreate symlinks after init | Agent team skills |

### Step 3: Create new files

| File | Content |
|---|---|
| `.gitignore` | Python + Node + Docker standard ignores |
| `CLAUDE.md` | Rewritten for new repo: new stack notes, TDD mandate, CSS prefix convention, agent team workflow, all lessons from v1 |
| `docs/plans/2026-03-05-architecture.md` | This architecture team report (Moss + Roy + Jen) |
| `docs/pnl-spec.md` | P&L derivation formulas (documented above) |
| `README.md` | Brief project description, how to run dev env |

### Step 4: Initial commit and push

```bash
git add .
git commit -m "Initial commit: architecture docs and project foundation"
git push -u origin main
```

### What This Session Does NOT Include (Phase A — web-team scope)

The following are Phase A tasks, handed to the web-team in the next session:
- `backend/` scaffold (FastAPI app, Alembic, pyproject.toml, Dockerfile)
- `frontend/` scaffold (Vite, TanStack Query, vitest, package.json)
- `docker-compose.yml`
- GitHub Actions CI workflow
- Initial Alembic migration (enums + table skeletons)
- `GET /health` endpoint

This session just gets the repo initialized with all the knowledge assets in place so the web-team has everything it needs to start Phase A.

### Blocking Decisions — Both Resolved

**Q1 — Phase count: FIXED at p1–p5**
`CREATE TYPE phase_enum AS ENUM ('p1','p2','p3','p4','p5','total')`. Adding a phase later for a new customer requires: one Alembic migration (`ALTER TYPE phase_enum ADD VALUE 'p6'`), update `domain/enums.py`, update the single `PHASES` constant in cascade config. ~15–30 minutes. Not a rebuild. The discipline is: `PHASES` is one constant, never scattered.

**Q2 — P&L spec: Extracted from `cascade.py` (authoritative)**

```
Source fields (from n12m_line_items, summed across all 12 months):
  gross_revenue       — total revenue
  subtotal_direct_cost — total direct costs (stored as positive)
  sales_costs         — sales costs component
  marketing           — marketing costs component
  subtotal_capex      — capital expenditure (stored as positive)

P&L derivations:
  Revenue          = gross_revenue
  COGS             = -(subtotal_direct_cost)
  Gross Profit     = Revenue + COGS
  Sales & Marketing = -(sales_costs + marketing)
  Direct Costs     = -(subtotal_capex)
  Net Profit       = Gross Profit + Sales & Marketing + Direct Costs
  Deliveries       = delivery_counts total (not from n12m)

Rate columns (all except Deliveries):
  current_rate = current_total / current_delivery_count   (null if count = 0)
  budget_rate  = budget_total / budget_delivery_count     (null if count = 0)
  delta_rate   = current_rate - budget_rate               (null if either is null)
```

This is the spec. The E2E test fixture asserts against these exact derivations.

Everything else (GAP-04 import linking UX, GAP-06 auth approach, GAP-07 edit boundary) is decided during the relevant build phase — none block Phase A or B.
