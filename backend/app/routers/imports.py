"""Import router — Phase B3/B5.

Endpoints:
  POST   /imports              — create a new Import record (status defaults to pending)
  GET    /imports              — list all non-deleted imports
  DELETE /imports/{id}        — soft-delete (sets deleted_at); 404 if not found or already deleted
  PATCH  /imports/{id}/file   — upload xlsx, parse + cascade + persist; sets status=complete

NOTE: POST /imports creates a metadata-only record (no xlsx attached).
PATCH /imports/{id}/file (B5) attaches the uploaded file and triggers the cascade.
"""

import os
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.domain.enums import ImportStatus, Phase
from app.domain.models import Import, N12mLineItem, NcfSeries, PerDeliveryRow, PhaseComparisonRow, PnlSummary
from app.domain.schemas import ImportCreate, ImportResponse
from app.services.cascade_service import run_cascade
from app.services.excel_parser.base import parse_excel

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


# ---------------------------------------------------------------------------
# PATCH /imports/{id}/file
# ---------------------------------------------------------------------------


@router.patch("/{import_id}/file", response_model=ImportResponse, status_code=200)
async def upload_import_file(
    import_id: uuid.UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> Import:
    log = structlog.get_logger().bind(import_id=str(import_id))
    log.info("import_file_upload_start", filename=file.filename)

    # Fetch import — 404 if missing or soft-deleted
    result = await session.execute(
        select(Import).where(Import.id == import_id, Import.deleted_at.is_(None))
    )
    record = result.scalar_one_or_none()
    if record is None:
        log.warning("import_file_upload_not_found")
        raise HTTPException(status_code=404, detail="Import not found or already deleted")

    # 409 if already complete (idempotency guard)
    if record.status == ImportStatus.complete:
        log.warning("import_file_upload_already_complete")
        raise HTTPException(status_code=409, detail="Import already complete")

    # Write upload to a temp file, parse, catch bad zip / bad xlsx
    contents = await file.read()
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
    try:
        with os.fdopen(tmp_fd, "wb") as tmp_f:
            tmp_f.write(contents)

        try:
            parsed = parse_excel(tmp_path)
        except (zipfile.BadZipFile, ValueError) as exc:
            log.warning("import_file_upload_parse_error", error=str(exc))
            raise HTTPException(status_code=422, detail=f"Invalid xlsx file: {exc}") from exc
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # Run cascade (pure Python, no DB)
    cascade = run_cascade(parsed)

    # -----------------------------------------------------------------------
    # Persist phase_comparison_rows — from raw parser output (includes Phase.total)
    # -----------------------------------------------------------------------
    pc_rows = [
        PhaseComparisonRow(
            import_id=import_id,
            line_item=row["line_item"],
            phase=row["phase"],
            budget=row.get("budget"),
            current=row.get("current"),
            # delta and delta_pct are GENERATED ALWAYS AS — do not pass
        )
        for row in parsed["phase_comparison_rows"]
    ]
    session.add_all(pc_rows)

    # -----------------------------------------------------------------------
    # Persist per_delivery_rows — from cascade result
    # -----------------------------------------------------------------------
    pd_rows = [
        PerDeliveryRow(
            import_id=import_id,
            line_item=row["line_item"],
            phase=row["phase"],
            budget=row.get("budget"),
            current=row.get("current"),
            # delta and delta_pct are GENERATED ALWAYS AS — do not pass
        )
        for row in cascade["per_delivery_rows"]
    ]
    session.add_all(pd_rows)

    # -----------------------------------------------------------------------
    # Persist n12m_line_items — flatten entries list from cascade result
    # -----------------------------------------------------------------------
    n12m_rows = []
    for row in cascade["n12m_line_items"]:
        for entry in row["entries"]:
            month_int = int(entry["month"].split("-")[1])
            n12m_rows.append(
                N12mLineItem(
                    import_id=import_id,
                    month=month_int,
                    section=row["section"],
                    line_item=row["line_item"],
                    value=entry["value"],
                )
            )
    session.add_all(n12m_rows)

    # -----------------------------------------------------------------------
    # Persist ncf_series — no series_name column; series_type only
    # -----------------------------------------------------------------------
    ncf_rows = [
        NcfSeries(
            import_id=import_id,
            month=int(row["month"].split("-")[1]),
            series_type=row["series_type"],
            value=row["value"],
            # series_name dropped — no column in model
        )
        for row in cascade["ncf_series"]
    ]
    session.add_all(ncf_rows)

    # -----------------------------------------------------------------------
    # Persist pnl_summaries — map budget_total→budget, current_total→current
    # delta is GENERATED ALWAYS AS — do not pass
    # -----------------------------------------------------------------------
    pnl_rows = [
        PnlSummary(
            import_id=import_id,
            line_item=row["line_item"],
            budget=row.get("budget_total"),
            current=row.get("current_total"),
            # delta is GENERATED ALWAYS AS — do not pass
        )
        for row in cascade["pnl_summaries"]
    ]
    session.add_all(pnl_rows)

    # -----------------------------------------------------------------------
    # Mark import as complete
    # -----------------------------------------------------------------------
    record.status = ImportStatus.complete
    # updated_at is managed by onupdate=func.now() on the model — no manual assignment needed

    await session.commit()
    await session.refresh(record)

    log.info("import_file_upload_complete", import_id=str(import_id))
    return record
