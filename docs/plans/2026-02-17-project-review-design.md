# Project Review & Production Roadmap

> **Note (2026-03-02):** This document was written when Azure was the assumed deployment target. The application and documentation have since been made cloud-agnostic. See [Architecture Overview](../architecture-overview.md) and [Cloud Provider Appendices](../cloud-providers/README.md) for the current hosting model. Azure-specific references below (Azure AD, Azure Container Apps, Azure SQL) should be read as historical context.

**Date**: 2026-02-17
**Status**: Draft
**Scope**: Full architecture review, production readiness assessment, and prioritised roadmap

---

## 1. Product Context

### What This App Does

A **Property Development Cash Flow (PCG) Reporting Tool** that replaces error-prone Excel spreadsheets used to track expenditure across large-scope residential development projects.

The customer's spreadsheet (a PCG report) tracks every dollar flowing through a staged property development: settlements, revenue, construction costs, marketing, overheads, capital expenditure, and contingency -- projected across a rolling 12-month window and compared against budget and previous forecasts.

### Key Domain Concepts

- **Stages (S1-S5)**: Physical stages of a development (e.g., Stage 1 = first 50 lots). Each has its own cost and revenue timeline.
- **WOP (Whole of Project)**: Combined totals across all stages.
- **Settlements**: Buyer completes purchase of a lot/home -- when revenue is actually received.
- **N12M (Next 12 Months)**: Rolling 12-month cash flow projection.
- **NCF (Net Cash Flow)**: Cumulative and periodic net cash position.
- **Budget vs Current vs Previous**: Three forecast versions compared to track variances.
- **P&L**: Simplified profit & loss derived from the cash flow data.

### Deployment Model

- **Single-tenant**: One instance per customer, deployed on the client's Azure infrastructure.
- **Client-hosted**: The client owns the data and hosting (Azure Container Apps).
- **PowerBI integration**: The database should sit alongside the client's PowerBI databases so they can build their own dashboards from the data.
- **Azure AD SSO**: Authentication will integrate with the client's existing Azure Active Directory.

### Core Value Proposition

**Data entry is the primary use case** -- moving employees away from massive Excel spreadsheets that are error-prone and hard to scale. The dashboards are a secondary "nice to have". The critical requirement is that all calculations match the original Excel formulas exactly.

---

## 2. Current Architecture

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite 7 (JSX, no TypeScript) |
| Backend | FastAPI (Python 3.11, async) |
| Database | PostgreSQL 16 (via SQLAlchemy async + asyncpg) |
| Container | Docker Compose (3 services: db, backend, frontend) |
| Icons | Lucide React |
| Styling | Single CSS file, dark theme, class-based selectors |

### Backend Structure

- **24 API endpoints** across 6 routers (imports, ncf, n12m, summary, pnl, data-entry)
- **9 database models** all linked to a central `Import` model via cascading foreign keys
- **3 services**: Excel parser, calculation rules engine, cascade recalculation engine (7 steps)
- **3 Alembic migrations** (initial schema, Output_V2 tables, stage inputs)
- **58 tests** covering API endpoints, calculations, cascade logic, and parser utilities

### Frontend Structure

- **5 tabs**: Dashboard, 12-Month Forecast, Stage Comparison, P&L, Data Entry
- **20+ components** organised into cards/, tabs/, and shared components
- **No external state management** -- pure React hooks (useState, useMemo)
- **No client-side routing** -- tab-based navigation via state
- **105 tests** covering all tabs, cards, hooks, and utilities

### Data Flow

```
Excel Upload                Manual Data Entry
     |                            |
     v                            v
excel_parser.py             data_entry.py (scaffolds grid)
     |                            |
     v                            v
Import + child records      StageInput rows
     |                            |
     |                            v
     |                    cascade.py (7-step recalculation)
     |                            |
     v                            v
  Dashboard / Forecast / Stage Comparison / P&L views
                    |
                    v
            PowerBI (via direct DB access)
```

---

## 3. Findings

### What's Good

- **Clean separation of concerns**: API routes, models, schemas, and services are well-organised.
- **Cascade recalculation engine**: 7 ordered steps with clear responsibilities, handles the complex dependency chain between calculated fields.
- **Test coverage**: 163 total tests (58 backend + 105 frontend) covering all endpoints, business logic, and UI components.
- **Pydantic validation**: Request/response schemas enforce data contracts.
- **Async throughout**: FastAPI + SQLAlchemy async provides good concurrency for a web app.
- **Database cascades**: Both ORM-level (`cascade="all, delete-orphan"`) and DB-level (`ON DELETE CASCADE`) ensure referential integrity.

### Issues Found

#### Critical

**1. Hardcoded Excel Parser**

The parser maps to exact row numbers (347-369, 18-40, 72-94, etc.) and column ranges (70-110). This works for exactly one customer's spreadsheet format. Each new customer deployment would require modifying `excel_parser.py`.

The row mappings are spread across 6 constants: `N12M_ROW_MAP`, `STAGE1_ROW_MAP`, `WOL_ROW_MAP`, `COMPARISON_ROW_MAP`, `PER_SETTLEMENT_ROW_MAP`, `PNL_ROW_MAP`.

*Impact*: Blocks multi-customer deployment. Parser customisation requires developer involvement.

**2. No Calculation Validation Against Source**

The `CALC_RULES` in `calculations.py` are the heart of the product. If these don't match the Excel formulas exactly, the app loses trust. Currently:
- Individual formula tests exist (7 tests in `test_calculations.py`)
- No end-to-end test that imports the actual `Project.xlsx` and verifies every calculated value matches the spreadsheet's output

*Impact*: Risk of silent calculation drift. The single most important property of the app (calculation accuracy) has no integration-level verification.

**3. No Authentication**

The API is completely open -- no authentication, no authorisation. Any network-accessible client can read, modify, or delete all data.

*Impact*: Blocks production deployment. Azure AD SSO integration is required.

#### Medium

**4. Azure Database Compatibility**

PostgreSQL is the current database. Azure offers both Azure Database for PostgreSQL and Azure SQL Database (MS SQL). If the client's PowerBI environment already uses Azure SQL, a dialect change would be needed:

- `JSONB` columns (`actual_flags`, `budget_values`, `current_values`, `delta_values`, `delta_pct_values`) have no direct MS SQL equivalent -- would need `NVARCHAR(MAX)` with JSON functions
- `UUID` primary keys would become `UNIQUEIDENTIFIER`
- Alembic migrations would need regeneration

PostgreSQL on Azure requires zero code changes and has native PowerBI connector support.

**5. JSON Columns Are PowerBI-Unfriendly**

`stage_comparisons` and `per_settlements` store per-stage values as JSON dicts (`{s1, s2, s3, s4, s5, wop}`). PowerBI can query JSON but it's cumbersome. These should be denormalised into separate columns or a bridge table, or exposed via database views.

**6. No Error Recovery in Cascade**

The bulk save endpoint (`PUT /data-entry/imports/:id/grid`) runs the full 7-step cascade. If it fails mid-way, there's no explicit transaction management beyond SQLAlchemy's session. A partial cascade failure could leave data inconsistent.

**7. NCF Series Names Are Hardcoded**

`"current_sep25"`, `"previous_jul25"` are baked into the parser and frontend. These should be dynamic based on the import's `report_month` and linked imports.

#### Low

**8. No Request Caching/Deduplication**: Every tab mount triggers fresh API calls.

**9. Bulk Delete Has No Protection**: `DELETE /imports` wipes all data with no confirmation or role check.

**10. CORS Is Development-Only**: Set to `localhost:5173`, needs production URL configuration.

---

## 4. Production Readiness Assessment

| Requirement | Status | Notes |
|------------|--------|-------|
| Core data entry flow | Working | Grid + cascade recalculation functional |
| Excel import | Working | Parser functional for current customer format |
| Dashboard views | Working | All 5 tabs rendering correctly |
| Calculation accuracy | Unverified | No E2E validation against source spreadsheet |
| Authentication | Missing | No auth at all -- needs Azure AD integration |
| HTTPS/TLS | N/A | Handled by Azure Container Apps |
| Database backups | N/A | Handled by Azure managed database service |
| Environment config | Partial | Env vars supported but no Azure-specific config |
| CORS for production | Missing | Hardcoded to localhost |
| Health checks | Minimal | `/health` returns `{"status": "ok"}`, no DB check |
| Logging/monitoring | Missing | No structured logging or Azure App Insights |
| Configurable parser | Missing | Hardcoded to one spreadsheet format |
| PowerBI-ready schema | Partial | JSON columns need denormalisation or views |
| CI/CD pipeline | Missing | No automated build/test/deploy pipeline |

---

## 5. PowerBI Integration Strategy

Since the client wants to build PowerBI dashboards from this data, the database schema is effectively a **public API**. This means:

- Table and column names become contracts -- renaming later breaks PowerBI reports.
- The current schema is well-structured for PowerBI (flat tables with clear foreign keys, numeric columns).
- JSON columns need attention (see issue #5 above).

### Recommendations

1. **Document the database schema** as a "data dictionary" for the PowerBI team.
2. **Create database views** designed for PowerBI consumption (e.g., `vw_stage_comparison` that unpivots JSON columns into rows).
3. **Avoid schema changes** to existing tables once PowerBI reports are built against them. Use views as a stable interface layer.

---

## 6. Prioritised Roadmap

### Phase 1: Trust & Accuracy (Highest Priority)

The app's value depends on calculation correctness. Without verified accuracy, nothing else matters.

1. **E2E calculation validation tests** -- Import `Project.xlsx`, verify every calculated field matches the spreadsheet's values. This is the credibility test.
2. **Transaction safety for cascade** -- Wrap the 7-step cascade in explicit transaction boundaries with proper rollback on failure.
3. **Dynamic NCF series naming** -- Derive series names from import metadata instead of hardcoding.

### Phase 2: Deployment Readiness

4. **Azure AD SSO integration** -- Add JWT validation middleware using `fastapi-azure-auth` or equivalent.
5. **Azure database decision** -- Clarify with client: PostgreSQL or SQL Server. If PostgreSQL, no changes needed. If SQL Server, plan the dialect migration.
6. **Production configuration** -- CORS origins, health check with DB connectivity, structured logging.
7. **CI/CD pipeline** -- Automated testing and deployment to Azure Container Apps.

### Phase 3: Multi-Customer Scalability

8. **Configurable Excel parser** -- Design a mapping configuration format (JSON/YAML) so new customers don't require code changes. Consider an admin UI for defining mappings.
9. **PowerBI-friendly schema** -- Add database views that denormalise JSON columns. Document the data dictionary.

### Phase 4: UX & Polish

10. **Enhanced data entry UX** -- Since this is the primary use case, invest in usability: inline validation, undo/redo, keyboard navigation, cell-level change history.
11. **Role-based access** -- Admin (can delete imports, configure parser) vs Editor (can enter data) vs Viewer (read-only dashboards).
12. **Audit trail** -- Track who changed what and when, important for financial data.

---

## 7. Quick Wins (Can Do Now)

These require minimal effort and reduce risk:

- Add a DB connectivity check to `/health` endpoint
- Make CORS origins configurable via environment variable (already partially supported)
- Add `--no-cache-dir` to pip install in Dockerfile (already done)
- Pin all frontend dependencies to exact versions in `package.json`
- Add `.env.example` with required environment variables documented
