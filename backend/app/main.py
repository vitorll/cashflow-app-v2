import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.db import engine

logger = structlog.get_logger()

app = FastAPI(
    title="Cashflow API",
    version=settings.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    logger.info("health_check")
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        logger.warning("health_check_db_failed", error=str(exc))
        db_status = "error"
    payload = {"status": "ok", "version": settings.APP_VERSION, "db": db_status}
    if db_status == "error":
        return JSONResponse(status_code=503, content=payload)
    return payload
