# Cashflow App v2

A 12-month rolling cash flow projection tool. Rebuilt from scratch with TDD from day one, clean schema, and agent team workflows.

## Architecture

See `docs/plans/2026-03-05-v2-architecture.md` for the full architecture decision record, including all lessons learned from v1 and how they are resolved in v2.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 7, TanStack Query v5 |
| Backend | FastAPI, Python 3.11, structlog |
| Database | PostgreSQL 16, SQLAlchemy async, Alembic |
| Production | Gunicorn + Uvicorn, single Docker container |

## Development

```bash
# Start full dev stack
docker compose up

# Run backend tests
docker compose exec backend python -m pytest --tb=short

# Run frontend tests
cd frontend && npx vitest run

# Run frontend lint
cd frontend && npm run lint

# Apply database migrations
docker compose exec backend alembic upgrade head
```

## Documentation

- `docs/plans/` — Architecture and design decisions
- `docs/data-dictionary.md` — Database schema reference
- `docs/pnl-spec.md` — P&L derivation formulas (authoritative spec)
- `docs/calc_rules.json` — Formula specification (Python and JS both derived from this)
- `docs/spreadsheet/` — Excel reference data

## Status

Phase A in progress — repository foundation and documentation.
