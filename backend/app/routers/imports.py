"""Import router — Phase B3.

Three endpoints:
  POST   /imports         — create a new Import record (status defaults to pending)
  GET    /imports         — list all non-deleted imports
  DELETE /imports/{id}   — soft-delete (sets deleted_at); 404 if not found or already deleted

NOTE: POST /imports creates a metadata-only record (no xlsx attached).
B5 will attach the uploaded file and trigger the cascade via PATCH /imports/{id}/file.
Records created here will remain at status=pending until B5 processes them.
"""

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.domain.enums import ImportStatus
from app.domain.models import Import
from app.domain.schemas import ImportCreate, ImportResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/imports", tags=["imports"])


# ---------------------------------------------------------------------------
# DB session dependency
# ---------------------------------------------------------------------------

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# POST /imports
# ---------------------------------------------------------------------------

@router.post("", response_model=ImportResponse, status_code=201)
async def create_import(
    body: ImportCreate,
    session: AsyncSession = Depends(get_session),
) -> Import:
    log = logger.bind(name=body.name, version_type=body.version_type, source_type=body.source_type)
    log.info("import_create_start")

    record = Import(
        name=body.name,
        version_type=body.version_type,
        source_type=body.source_type,
        status=ImportStatus.pending,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    log.info("import_create_complete", import_id=str(record.id))
    return record


# ---------------------------------------------------------------------------
# GET /imports
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ImportResponse], status_code=200)
async def list_imports(
    session: AsyncSession = Depends(get_session),
) -> list[Import]:
    logger.info("import_list_start")
    result = await session.execute(
        select(Import).where(Import.deleted_at.is_(None)).order_by(Import.created_at.desc())
    )
    records = list(result.scalars().all())
    logger.info("import_list_complete", count=len(records))
    return records


# ---------------------------------------------------------------------------
# DELETE /imports/{id}
# ---------------------------------------------------------------------------

@router.delete("/{import_id}", status_code=204)
async def delete_import(
    import_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    log = logger.bind(import_id=str(import_id))
    log.info("import_delete_start")

    result = await session.execute(
        select(Import).where(Import.id == import_id, Import.deleted_at.is_(None))
    )
    record = result.scalar_one_or_none()

    if record is None:
        log.warning("import_delete_not_found")
        raise HTTPException(status_code=404, detail="Import not found or already deleted")

    record.deleted_at = datetime.now(timezone.utc)
    await session.commit()

    log.info("import_delete_complete")
    return Response(status_code=204)
