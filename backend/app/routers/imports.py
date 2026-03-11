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
from app.domain.schemas import ForecastEntry, ForecastResponse, ForecastRow, ImportCreate, ImportResponse, PhaseComparisonEntry, PhaseComparisonGroupedRow, PhaseComparisonResponse
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
    # Build month -> is_actual map from import_meta
    actual_flags_str = parsed["import_meta"].get("actual_flags", "")
    n12m_months_str = parsed["import_meta"].get("n12m_months", "")
    if actual_flags_str and n12m_months_str:
        _flags = [f.strip().lower() == "true" for f in actual_flags_str.split(",")]
        _months = [m.strip() for m in n12m_months_str.split(",")]
        month_is_actual = dict(zip(_months, _flags))
    else:
        month_is_actual = {}

    n12m_rows = []
    for row in cascade["n12m_line_items"]:
        for entry in row["entries"]:
            month_str = entry["month"]
            month_int = int(month_str.split("-")[1])
            n12m_rows.append(
                N12mLineItem(
                    import_id=import_id,
                    month=month_int,
                    section=row["section"],
                    line_item=row["line_item"],
                    value=entry["value"],
                    display_name=row["display_name"],
                    is_calculated=row["is_calculated"],
                    sort_order=row["sort_order"],
                    is_actual=month_is_actual.get(month_str, False),
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


# ---------------------------------------------------------------------------
# GET /imports/{id}/forecast — C1
# ---------------------------------------------------------------------------


@router.get("/{import_id}/forecast", response_model=ForecastResponse, status_code=200)
async def get_forecast(
    import_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ForecastResponse:
    log = logger.bind(import_id=str(import_id))
    log.info("forecast_get_start")

    # Fetch import — 404 if missing, soft-deleted, or not complete
    result = await session.execute(
        select(Import).where(Import.id == import_id, Import.deleted_at.is_(None))
    )
    record = result.scalar_one_or_none()
    if record is None:
        log.warning("forecast_get_not_found")
        raise HTTPException(status_code=404, detail="Import not found")

    if record.status != ImportStatus.complete:
        log.warning("forecast_get_not_complete", status=record.status)
        raise HTTPException(status_code=404, detail="Import data not available (status is not complete)")

    # Query all N12mLineItem rows for this import, ordered by sort_order then month
    items_result = await session.execute(
        select(N12mLineItem)
        .where(N12mLineItem.import_id == import_id)
        .order_by(N12mLineItem.sort_order, N12mLineItem.month)
    )
    items = list(items_result.scalars().all())

    # Group by (section, line_item), collect entries in sort_order sequence
    grouped: dict[tuple, dict] = {}
    for item in items:
        key = (item.section, item.line_item)
        if key not in grouped:
            grouped[key] = {
                "display_name": item.display_name,
                "is_calculated": item.is_calculated,
                "sort_order": item.sort_order,
                "entries": [],
            }
        grouped[key]["entries"].append(ForecastEntry(month=item.month, value=item.value, is_actual=item.is_actual))

    rows = [
        ForecastRow(
            section=section,
            line_item=line_item,
            display_name=meta["display_name"],
            is_calculated=meta["is_calculated"],
            sort_order=meta["sort_order"],
            entries=meta["entries"],
        )
        for (section, line_item), meta in grouped.items()
    ]

    log.info("forecast_get_complete", import_id=str(import_id), row_count=len(rows))
    return ForecastResponse(import_id=import_id, rows=rows)


# ---------------------------------------------------------------------------
# GET /imports/{id}/phase-comparison — C2
# ---------------------------------------------------------------------------


@router.get("/{import_id}/phase-comparison", response_model=PhaseComparisonResponse, status_code=200)
async def get_phase_comparison(
    import_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> PhaseComparisonResponse:
    log = logger.bind(import_id=str(import_id))
    log.info("phase_comparison_get_start")

    # Fetch import — 404 if missing, soft-deleted, or not complete
    result = await session.execute(
        select(Import).where(Import.id == import_id, Import.deleted_at.is_(None))
    )
    record = result.scalar_one_or_none()
    if record is None:
        log.warning("phase_comparison_get_not_found")
        raise HTTPException(status_code=404, detail="Import not found")

    if record.status != ImportStatus.complete:
        log.warning("phase_comparison_get_not_complete", status=record.status)
        raise HTTPException(status_code=404, detail="Import data not available (status is not complete)")

    # Query all PhaseComparisonRow rows for this import, ordered for stable grouping
    rows_result = await session.execute(
        select(PhaseComparisonRow)
        .where(PhaseComparisonRow.import_id == import_id)
        .order_by(PhaseComparisonRow.line_item, PhaseComparisonRow.phase)
    )
    db_rows = list(rows_result.scalars().all())

    # Group by line_item — insertion-order dict preserves line_item sequence
    grouped: dict[str, list[PhaseComparisonEntry]] = {}
    for row in db_rows:
        if row.line_item not in grouped:
            grouped[row.line_item] = []
        grouped[row.line_item].append(
            PhaseComparisonEntry(
                phase=row.phase,
                budget=row.budget,
                current=row.current,
                delta=row.delta,
                delta_pct=row.delta_pct,
            )
        )

    grouped_rows = [
        PhaseComparisonGroupedRow(line_item=line_item, entries=entries)
        for line_item, entries in grouped.items()
    ]

    log.info("phase_comparison_get_complete", import_id=str(import_id), row_count=len(grouped_rows))
    return PhaseComparisonResponse(import_id=import_id, rows=grouped_rows)
