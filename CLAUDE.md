# Cashflow App v2

A 12-month rolling cash flow projection application. Rebuilt from scratch with TDD from day one, clean schema, and agent team workflows. See `docs/plans/2026-03-05-v2-architecture.md` for the full architecture decision record.

## Recommended Skills

- **brainstorming** — Planning new features or process improvements
- **writing-plans** — Structured implementation planning
- **systematic-debugging** — Investigating bugs or unexpected behaviour
- **web-team** — All backend and frontend development (TDD, RED/GREEN/REFACTOR)
- **architecture-team** — Architectural decisions, major features, schema changes

## Agent Teams

For all development work, invoke the `web-team` skill. It enforces RED/GREEN/REFACTOR TDD with specialised agents.

### Available Teams

- **Architecture/planning** → `architecture-team` (Moss, Roy, Jen)
  - Use when: starting new features, making schema changes, planning major work
- **Backend or frontend web development** → `web-team` (Rick & Morty cast)
  - Use when: implementing any feature, bug fix, or endpoint
  - ALL development goes through the web-team TDD workflow

### Phase Transitions

Do not auto-transition between teams. Wait for explicit user confirmation:
1. Architecture team for planning
2. Web-team for implementation
3. Back to architecture if scope changes significantly

### Skill Locations

Skills are located at:
- `skills/architecture-team/SKILL.md`
- `skills/web-team/SKILL.md`

## Tech Stack

- **Framework**: React 19 with JSX (not TypeScript)
- **Build Tool**: Vite 7
- **State/Cache**: TanStack Query v5 (replaces custom useApi hooks)
- **Icons**: Lucide React
- **Styling**: External CSS (`App.css`) with class-based selectors
- **Backend**: FastAPI + Python 3.11, async throughout
- **Database**: PostgreSQL 16, SQLAlchemy async, Alembic migrations
- **Logging**: structlog with request ID middleware
- **Production**: Gunicorn + Uvicorn, single Docker container

## Project Structure

```
cashflow-app-v2/
├── backend/
│   ├── app/
│   │   ├── domain/
│   │   │   ├── enums.py        # SINGLE SOURCE OF TRUTH for all phase/section/series names
│   │   │   ├── models.py       # SQLAlchemy ORM models
│   │   │   └── schemas.py      # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── cascade_service.py
│   │   │   ├── calc_rules.py
│   │   │   └── excel_parser/
│   │   │       ├── base.py
│   │   │       ├── template_parser.py
│   │   │       └── templates/
│   │   ├── routers/
│   │   ├── middleware/
│   │   │   ├── request_id.py
│   │   │   └── logging.py
│   │   └── config.py           # Pydantic Settings — ALL config from env vars
│   ├── tests/
│   │   ├── fixtures/
│   │   │   ├── sample_import.xlsx
│   │   │   └── expected_output.json  # GOLDEN FILE — created before any service code
│   │   ├── unit/
│   │   └── integration/
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── api/client.js           # Axios instance
│   │   ├── hooks/queries/          # TanStack Query hooks (one file per domain)
│   │   └── components/
│   └── tests/
│       ├── unit/
│       └── integration/
└── docs/
    ├── plans/                  # Architecture and design decisions
    ├── data-dictionary.md      # Canonical field definitions
    ├── pnl-spec.md             # P&L derivation formulas (authoritative spec)
    ├── calc_rules.json         # Formula spec (Python + JS derived from this)
    └── spreadsheet/            # Excel reference data
```

## Domain Terminology

The app uses generic terminology reusable across industries:
- **Phase** (p1–p5): Project phases — FIXED at 5. Adding p6 requires one Alembic migration + update `PHASES` constant.
- **Delivery**: A completed unit/milestone (generic for settlement, handover, etc.)
- **Total**: Whole-of-project aggregate
- **Sections**: Revenue, Direct Costs, Overheads, Capital Expenditure, Contingency

## TDD Mandate (Non-Negotiable)

**Every piece of business logic has a failing test before implementation.** This is enforced by CI coverage gates.

### Rules

1. RED before GREEN — failing test committed before implementation code
2. Each cascade step (1–7) has its own test module in `tests/unit/`
3. `calc_rules.json` is the specification — never the Python or JS code
4. The E2E golden file test (`tests/integration/test_e2e_calculations.py`) runs in CI on every push — build fails if it fails
5. Frontend tests use real Pydantic response shapes as fixture data
6. If deleting a function doesn't break a test, it has no TDD coverage

### Coverage Gates (CI enforced)

- Backend: `pytest --cov-fail-under=80`
- Frontend: `vitest run --coverage --coverage.thresholds.lines=70`

Both are hard gates — PRs cannot merge below threshold.

## Code Style

### Backend

- Use `domain/enums.py` exclusively — never string literals for phases, sections, or series names
- `PHASES = [Phase.p1, Phase.p2, Phase.p3, Phase.p4, Phase.p5]` — one constant, used everywhere
- All financial values: `NUMERIC(18,4)` in DB, `Decimal` in Python, rounded to 2dp at API response layer
- Delta calculations: PostgreSQL `GENERATED ALWAYS AS` computed columns, never Python floats
- structlog for all logging — every log event carries `request_id` and `import_id` where relevant
- All config from environment variables via `config.py` (Pydantic Settings) — no hardcoded values

### Frontend

- JSX file extension (`.jsx`) for React components
- Functional components with hooks (`useState`, `useMemo`)
- TanStack Query for all API calls — no ad-hoc fetch or custom useApi hooks
- **CSS class names must be unique per tab** — prefix with the tab name:
  - `forecast-row`, `forecast-label`
  - `phase-comparison-row`, `phase-comparison-label`
  - `pnl-row`, `pnl-label`
  - `data-entry-row`, `data-entry-label`
  - `dashboard-card`, `dashboard-stat`
- Dark theme with purple accent colour (`#bb86fc`)
- Fonts: DM Serif Display (headings), IBM Plex Sans (body)

## Lessons From v1 (Do Not Repeat)

| # | Lesson | How v2 prevents it |
|---|---|---|
| 1 | Hardcoded Excel parser | Config-driven `TemplateParser` + `excel_templates` DB table |
| 2 | No E2E calculation validation | Golden file fixture created BEFORE any service code; E2E test in CI |
| 3 | NCF series naming bug | `SeriesType` enum enforced at parse time — no string literals |
| 4 | JSON phase columns | Normalised `phase_comparison_rows` + `per_delivery_rows` tables |
| 5 | No authentication | OIDC/SAML via cloud proxy — documented, zero app code needed |
| 6 | Mid-project rename debt | All enums canonical from A2; `domain/enums.py` is the authority |
| 7 | Floating-point precision | `NUMERIC(18,4)` everywhere; computed columns in PostgreSQL |
| 8 | No request caching | TanStack Query v5 |
| 9 | Bulk delete unprotected | Soft-delete + confirmation token; destructive endpoint disabled |
| 10 | Tests added after code | TDD enforced; CI coverage gates block merges |
| 11 | CSS class name bleeding | Tab-prefixed class names mandatory from day one |
| 12 | CORS hardcoded | `ALLOWED_ORIGINS` env var via `config.py` |
| 13 | No structured logging | structlog + request ID middleware on every request |

## Commands

- `npm run dev` — Start frontend dev server
- `npm run build` — Build for production
- `npm run lint` — Run ESLint
- `npx vitest run` — Run frontend tests
- `docker compose up` — Start full dev stack
- `docker compose exec backend pytest --tb=short` — Run backend tests
- `docker compose exec backend alembic upgrade head` — Run migrations

## ESLint Configuration

- Flat config format (`eslint.config.js`)
- React Hooks and React Refresh plugins enabled
- Unused vars allowed if capitalised or prefixed with underscore

## Agent Preferences

- Use Task agents to parallelise independent work
- After writing code, run backend and frontend tests in parallel using separate Bash agents
- Backend tests: `docker compose exec -e PYTHONPATH=/app backend python -m pytest --tb=short`
- Frontend tests: `cd frontend && npx vitest run`
- Run frontend lint alongside tests when checking for regressions
- Use `docker compose exec` for any backend commands needing the database
- Use `docker compose restart backend` after changing backend code that isn't hot-reloaded
