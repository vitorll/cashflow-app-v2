# Phase 2: Deployment Readiness -- Design Document

**Date**: 2026-02-18
**Status**: Approved
**Depends on**: 2026-02-18-phase1-trust-accuracy-design.md

---

## Overview

Phase 2 makes the app production-ready without deploying to Azure yet. No authentication (deferred to a later phase). Focus on: production container build, health checks, structured logging, startup cleanup, and CI/CD pipeline.

Five work items:

1. Production Dockerfile & static file serving
2. Health check with DB connectivity
3. Structured logging
4. Startup cleanup
5. GitHub Actions CI/CD pipeline

---

## 1. Production Dockerfile & Static File Serving

### Problem

Both Dockerfiles are development-only: the backend runs uvicorn with `--reload`, the frontend runs `npm run dev`. There is no production build, no static file serving, and the Vite dev proxy is the only thing routing `/api` to the backend.

### Solution

**Single production Dockerfile (`Dockerfile.prod`)** with a multi-stage build:

- **Stage 1 (frontend build)**: Node 20-alpine, runs `npm ci && npm run build`, outputs `dist/`.
- **Stage 2 (production)**: Python 3.11-slim, installs backend dependencies, copies built `dist/` into the container, runs gunicorn + uvicorn workers.

**FastAPI serves the frontend**: Mount `dist/` as a `StaticFiles` directory. API routes at `/api/v1` are registered first and take precedence. A catch-all route serves `index.html` for any non-API, non-static path.

**Result**: One container, one port. `localhost:8000/api/v1/...` for API, `localhost:8000/` for the frontend. No nginx, no CORS issues, no proxy config.

**Dev workflow unchanged**: The existing `docker-compose.yml` with 3 separate services and hot reload continues to work for development.

### Files

- Create: `Dockerfile.prod`
- Modify: `backend/app/main.py` (add StaticFiles mount + catch-all)
- Optionally: `docker-compose.prod.yml` for testing the production build locally

---

## 2. Health Check with DB Connectivity

### Problem

`/health` returns `{"status": "ok"}` without checking database connectivity. A healthy response while the DB is down misleads orchestrators.

### Solution

Update `/health` to run `SELECT 1` against the database:

```json
{"status": "ok", "database": "connected", "version": "1.0.0"}
```

On DB failure:

```json
{"status": "degraded", "database": "unavailable"}
```

Return HTTP 200 in both cases (container orchestrators shouldn't kill on transient DB issues).

Add `/health/ready` that returns HTTP 503 when DB is down -- for use as a readiness probe in Azure Container Apps.

### Files

- Modify: `backend/app/main.py`

---

## 3. Structured Logging

### Problem

No application logging exists. Debugging production issues requires log aggregation, and container orchestrators capture stdout.

### Solution

Add `python-json-logger` for JSON-formatted structured logs to stdout.

**Request logging middleware**: Log method, path, status code, and duration for every request.

**Application events**: Log cascade recalculation (start, complete, error) and import events (upload, parse complete).

No log files -- stdout only. Container orchestrators capture it natively.

### Files

- Create: `backend/app/logging_config.py`
- Modify: `backend/app/main.py` (add logging middleware, configure at startup)
- Modify: `backend/app/services/cascade.py` (add event logging)
- Modify: `backend/app/api/v1/imports.py` (add import event logging)
- Add: `python-json-logger` to `requirements.txt`

---

## 4. Startup Cleanup

### Problem

- `Base.metadata.create_all` runs on every startup, bypassing Alembic migrations. Not production-safe.
- `.env.example` contains real dev credentials (`localdev123`).

### Solution

- Remove `Base.metadata.create_all` from the lifespan in `main.py`. Rely on Alembic migrations only.
- Update `.env.example` with placeholder values.

### Files

- Modify: `backend/app/main.py`
- Modify: `.env.example`

---

## 5. GitHub Actions CI/CD Pipeline

### Problem

No automated testing or build verification. Changes can break the app without anyone knowing until manual testing.

### Solution

GitHub Actions workflow triggered on push to `main` and on pull requests.

**Job 1: Test**
- Start PostgreSQL service container
- Run backend tests (`pytest`)
- Run frontend tests (`vitest run`)
- Run frontend lint (`eslint`)

**Job 2: Build** (depends on Job 1 passing)
- Build the production Docker image (`Dockerfile.prod`)
- Start the container and verify `/health` responds with 200

No deployment step -- just validation.

### Files

- Create: `.github/workflows/ci.yml`

---

## Data Flow After Phase 2

```
Developer pushes code
    |
    v
GitHub Actions
    ├── Job 1: Run all tests (backend + frontend)
    └── Job 2: Build production image, verify /health

Production Container (single image)
    |
    ├── Gunicorn + Uvicorn workers
    |       ├── /api/v1/* → FastAPI routes
    |       ├── /health → DB connectivity check
    |       ├── /health/ready → Readiness probe
    |       └── /* → Static frontend files (dist/)
    |
    └── Structured JSON logs → stdout → orchestrator
```

---

## Success Criteria

1. `docker build -f Dockerfile.prod .` produces a working single container serving both API and frontend
2. `/health` reports database connectivity status
3. `/health/ready` returns 503 when DB is unreachable
4. All requests produce structured JSON log lines on stdout
5. GitHub Actions runs tests + builds on every push/PR
6. No `create_all` on startup -- Alembic only
