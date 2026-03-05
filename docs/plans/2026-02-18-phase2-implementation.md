# Phase 2: Deployment Readiness — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the app production-ready with a single-container build, health checks, structured logging, and CI/CD.

**Architecture:** Combine frontend and backend into one production container — FastAPI serves built frontend static files alongside the API. Add health checks with DB verification, structured JSON logging, and a GitHub Actions pipeline that runs tests and builds the production image.

**Tech Stack:** Python/FastAPI, gunicorn, React/Vite, Docker multi-stage builds, python-json-logger, GitHub Actions

---

### Task 1: Health Check with DB Connectivity

**Files:**
- Modify: `backend/app/main.py:33-35`
- Test: `backend/tests/test_health.py` (create)

**Step 1: Write the tests**

Create `backend/tests/test_health.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_ready_returns_ok(client):
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
```

**Step 2: Run tests to verify they fail**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest tests/test_health.py -v`

Expected: FAIL — current `/health` returns `{"status": "ok"}` without `database` or `version` fields.

**Step 3: Update health endpoints in main.py**

Replace the existing `/health` endpoint (lines 33-35) in `backend/app/main.py` with:

```python
from sqlalchemy import text
from app.database import async_session


@app.get("/health")
async def health():
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected", "version": "1.0.0"}
    except Exception:
        return {"status": "degraded", "database": "unavailable", "version": "1.0.0"}


@app.get("/health/ready")
async def health_ready():
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"ready": False})
```

Also add `text` to the sqlalchemy import at the top of the file, and import `async_session` from `app.database`.

**Step 4: Run tests**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest --tb=short`

Expected: All pass.

**Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_health.py
git commit -m "Add health check with DB connectivity and readiness probe"
```

---

### Task 2: Structured Logging

**Files:**
- Create: `backend/app/logging_config.py`
- Modify: `backend/app/main.py` (add logging setup + request logging middleware)
- Modify: `backend/app/services/cascade.py:1-10` (add logger)
- Modify: `backend/app/api/v1/imports.py:19-20` (add logger on upload)
- Modify: `backend/requirements.txt` (add python-json-logger)

**Step 1: Add dependency**

Add `python-json-logger==3.2.1` to `backend/requirements.txt`.

Run: `docker compose exec backend pip install python-json-logger==3.2.1`

**Step 2: Create logging config**

Create `backend/app/logging_config.py`:

```python
import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def setup_logging():
    formatter = JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Quiet down noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
```

**Step 3: Add request logging middleware to main.py**

Add these imports at the top of `backend/app/main.py`:

```python
import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from app.logging_config import setup_logging
```

Add request logging middleware class before the `app = FastAPI(...)` line:

```python
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000)
        logger = logging.getLogger("cashflow.request")
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
```

Call `setup_logging()` at the top of the lifespan function:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
```

Add the middleware after CORS middleware:

```python
app.add_middleware(RequestLoggingMiddleware)
```

**Step 4: Add logging to cascade.py**

At the top of `backend/app/services/cascade.py` (after the existing imports, around line 6), add:

```python
import logging

logger = logging.getLogger("cashflow.cascade")
```

In the `full_recalculate` function, add logging at the start and end. Find the function definition and add:

```python
async def full_recalculate(session: AsyncSession, import_id):
    logger.info("Cascade recalculation started", extra={"import_id": str(import_id)})
    # ... existing code ...
    logger.info("Cascade recalculation completed", extra={"import_id": str(import_id)})
```

**Step 5: Add logging to imports upload**

At the top of `backend/app/api/v1/imports.py`, add:

```python
import logging

logger = logging.getLogger("cashflow.imports")
```

In the `upload_excel` function, after successful parsing and commit, add:

```python
logger.info("Excel import completed", extra={
    "import_id": str(imp.id),
    "filename": file.filename,
    "file_size": file_size,
})
```

**Step 6: Run all tests**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest --tb=short`

Expected: All pass. Logging doesn't affect test behavior.

**Step 7: Commit**

```bash
git add backend/app/logging_config.py backend/app/main.py backend/app/services/cascade.py backend/app/api/v1/imports.py backend/requirements.txt
git commit -m "Add structured JSON logging with request middleware"
```

---

### Task 3: Startup Cleanup

**Files:**
- Modify: `backend/app/main.py:12-15` (remove create_all)
- Modify: `.env.example`

**Step 1: Remove create_all from lifespan**

In `backend/app/main.py`, change the lifespan function from:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
```

To:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield
    await engine.dispose()
```

Remove the `Base` import from `app.database` since it's no longer used in main.py. The `Base` import line should change from:

```python
from app.database import engine, Base
```

To:

```python
from app.database import engine
```

**Step 2: Update conftest.py**

The test conftest still uses `Base.metadata.create_all` for the test DB — that's correct and should stay. Tests create their own in-memory SQLite tables. Verify conftest imports `Base` from `app.database`.

**Step 3: Update .env.example**

Replace `.env.example` contents with:

```
DB_PASSWORD=your_password_here
DATABASE_URL=postgresql+asyncpg://cashflow:your_password_here@db:5432/cashflow
CORS_ORIGINS=http://localhost:5173
```

**Step 4: Run all tests**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest --tb=short`

Expected: All pass. Tests use their own `create_all` in conftest — they don't depend on the app's lifespan.

**Step 5: Commit**

```bash
git add backend/app/main.py .env.example
git commit -m "Remove create_all from startup, use Alembic only; fix .env.example"
```

---

### Task 4: Production Dockerfile

**Files:**
- Create: `Dockerfile.prod`
- Modify: `backend/app/main.py` (add static file serving)
- Create: `backend/gunicorn.conf.py`

**Step 1: Add static file serving to main.py**

At the bottom of `backend/app/main.py`, after `app.include_router(v1_router)` and the health endpoints, add:

```python
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Serve frontend static files in production
_frontend_dist = Path(__file__).resolve().parent.parent / "static"
if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="static-assets")

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        file_path = _frontend_dist / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_frontend_dist / "index.html")
```

This only activates when the `static/` directory exists (production build). In development, the directory doesn't exist so the mount is skipped and the Vite dev server handles the frontend.

**Step 2: Create gunicorn config**

Create `backend/gunicorn.conf.py`:

```python
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

**Step 3: Create Dockerfile.prod**

Create `Dockerfile.prod` at the project root:

```dockerfile
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Production backend + frontend static files
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy backend code
COPY backend/ .

# Copy built frontend into static/
COPY --from=frontend-build /app/dist ./static

# Run with gunicorn
EXPOSE 8000
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
```

**Step 4: Build and test the production image**

Run:
```bash
docker build -f Dockerfile.prod -t cashflow-prod .
```

Then verify it starts:
```bash
docker run --rm -d --name cashflow-test -p 8001:8000 \
  -e DATABASE_URL=postgresql+asyncpg://cashflow:localdev123@host.docker.internal:5432/cashflow \
  cashflow-prod
sleep 3
curl http://localhost:8001/health
curl http://localhost:8001/
docker stop cashflow-test
```

Expected: `/health` returns JSON, `/` returns the frontend HTML.

**Step 5: Run backend tests to make sure static mount doesn't break anything**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest --tb=short`

Expected: All pass. The static mount is conditional — it only activates when the `static/` directory exists.

**Step 6: Commit**

```bash
git add Dockerfile.prod backend/app/main.py backend/gunicorn.conf.py
git commit -m "Add production Dockerfile with multi-stage build and static serving"
```

---

### Task 5: GitHub Actions CI/CD Pipeline

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1: Create the workflow file**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: cashflow
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: cashflow
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U cashflow"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install backend dependencies
        run: pip install -r backend/requirements.txt

      - name: Run backend tests
        working-directory: backend
        env:
          DATABASE_URL: postgresql+asyncpg://cashflow:testpass@localhost:5432/cashflow
          PYTHONPATH: /home/runner/work/cashflow-app/cashflow-app/backend
        run: python -m pytest --tb=short

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install frontend dependencies
        working-directory: frontend
        run: npm ci

      - name: Run frontend lint
        working-directory: frontend
        run: npm run lint

      - name: Run frontend tests
        working-directory: frontend
        run: npx vitest run

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build production Docker image
        run: docker build -f Dockerfile.prod -t cashflow-prod .

      - name: Verify container starts and health check works
        run: |
          docker run --rm -d --name cashflow-test -p 8000:8000 \
            -e DATABASE_URL=sqlite+aiosqlite:// \
            cashflow-prod
          sleep 5
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
          echo "Health check returned: $STATUS"
          docker stop cashflow-test
          if [ "$STATUS" != "200" ]; then
            echo "Health check failed!"
            exit 1
          fi
```

Note: The build job uses `sqlite+aiosqlite://` as the DB URL — this means the health check will return `{"status": "degraded"}` (no real DB), but it will still return HTTP 200, confirming the container starts and serves requests. The health endpoint returns 200 even when degraded — only `/health/ready` returns 503.

**Step 2: Commit**

```bash
mkdir -p .github/workflows
git add .github/workflows/ci.yml
git commit -m "Add GitHub Actions CI pipeline with tests and Docker build"
```

---

### Task 6: Final Verification & Push

**Step 1: Run all tests in parallel**

Backend: `docker compose exec -e PYTHONPATH=/app backend python -m pytest --tb=short`
Frontend: `cd frontend && npx vitest run && npm run lint`

Expected: All pass.

**Step 2: Test the production Docker build**

```bash
docker build -f Dockerfile.prod -t cashflow-prod .
```

Expected: Builds successfully.

**Step 3: Push**

```bash
git push
```
