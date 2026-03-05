# Phase 5: Production Hardening — Design Document

**Date**: 2026-02-18
**Status**: Approved
**Depends on**: 2026-02-18-phase4-data-entry-ux-design.md

---

## Overview

The app is feature-complete for a first deployment. This phase closes the remaining gaps between the current Docker setup and a production-ready container for Azure Container Apps. No feature changes — purely infrastructure hardening.

Five work items:

1. Auto-run Alembic migrations on container startup
2. Remove hardcoded dev credentials from `alembic.ini`
3. Non-root user in `Dockerfile.prod`
4. `.dockerignore` file to speed up builds
5. Configurable gunicorn worker count via `WEB_CONCURRENCY`

---

## 1. Auto-Run Migrations on Startup

### Problem

The production container starts gunicorn directly. There is no mechanism to create or update the database schema. Alembic migrations must be run manually.

### Solution

Create `backend/entrypoint.sh` that runs `alembic upgrade head` then `exec`s gunicorn. Update `Dockerfile.prod` CMD to use the entrypoint. Alembic migrations are idempotent — safe to run on every container start.

### Files

- Create: `backend/entrypoint.sh`
- Modify: `Dockerfile.prod`

---

## 2. Remove Hardcoded Credentials from alembic.ini

### Problem

`backend/alembic.ini` contains `sqlalchemy.url = postgresql+asyncpg://cashflow:localdev123@db:5432/cashflow`. This is overridden at runtime by `env.py` but having credentials in a tracked file is bad practice.

### Solution

Replace with a placeholder: `sqlalchemy.url = driver://user:pass@host/dbname`.

### Files

- Modify: `backend/alembic.ini`

---

## 3. Non-Root User in Dockerfile.prod

### Problem

The production container runs as root. Azure Container Apps supports non-root containers and it is a security best practice.

### Solution

Add `RUN adduser --disabled-password --no-create-home appuser` and `USER appuser` in the production stage of `Dockerfile.prod`, after installing dependencies but before CMD.

### Files

- Modify: `Dockerfile.prod`

---

## 4. .dockerignore File

### Problem

No `.dockerignore` exists. The entire repo (including `node_modules`, `.git`, `pgdata`, `__pycache__`) is sent as build context, slowing builds.

### Solution

Create `.dockerignore` excluding build artifacts, dev files, and large directories.

### Files

- Create: `.dockerignore`

---

## 5. Configurable Gunicorn Workers

### Problem

`gunicorn.conf.py` uses `cpu_count() * 2 + 1` which can over-provision on Azure Container Apps where vCPUs may be fractional (e.g. 0.25 or 0.5).

### Solution

Read `WEB_CONCURRENCY` env var, falling back to the current formula.

### Files

- Modify: `backend/gunicorn.conf.py`

---

## What This Phase Does NOT Do

- No CI/CD deployment pipeline (deferred until Azure access is available)
- No Azure-specific configuration (Key Vault, Managed Identity, ACR)
- No feature changes
- No test changes (unless existing tests need updating)

---

## Success Criteria

1. `docker build -f Dockerfile.prod` succeeds
2. Container starts, runs migrations, and serves traffic
3. No credentials in tracked files
4. Container runs as non-root user
5. Build context excludes unnecessary files
6. Worker count controllable via `WEB_CONCURRENCY`
7. All existing tests continue to pass
