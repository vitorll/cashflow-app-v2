"""Import router — Phase B3–C4.

Endpoints:
  POST   /imports                          — create a new Import record (status defaults to pending)
  GET    /imports                          — list all non-deleted imports
  DELETE /imports/{id}                     — soft-delete (sets deleted_at); 404 if not found or already deleted
  PATCH  /imports/{id}/file               — upload xlsx, parse + cascade + persist; sets status=complete
  GET    /imports/{id}/forecast            — C1: N12M forecast rows grouped by line_item
  GET    /imports/{id}/phase-comparison    — C2: phase comparison rows grouped by line_item
  GET    /imports/{id}/pnl                 — C3: P&L summary rows (flat, 7 rows)
  PATCH  /imports/{id}/n12m/{line}/{month} — C4: single-cell edit → cascade recalc → 204
"""

import os
import tempfile
import uuid
import zipfile
from datetime import date, datetime, timezone
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.domain.enums import ImportStatus, Phase
from app.domain.models import DeliveryCount, Import, N12mLineItem, NcfSeries, PerDeliveryRow, PhaseComparisonRow, PnlSummary
from app.domain.schemas import ForecastEntry, ForecastResponse, ForecastRow, ImportCreate, ImportResponse, N12mPatchRequest, PhaseComparisonEntry, PhaseComparisonGroupedRow, PhaseComparisonResponse, PnlRow, PnlResponse
from app.services.cascade_service import run_cascade
from app.services.excel_parser.base import parse_excel

logger = structlog.get_logger()

router = APIRouter(prefix="/imports", tags=["imports"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _month_int_to_date_str(month: int, report_month) -> str:
    """Reconstruct a YYYY-MM-DD string from a stored month integer and the import's report_month.

    The 12-month window starts the month AFTER report_month. Months greater than or equal
    to the start month fall in the same year as report_month; smaller months fall in the
    following year.

    Example: report_month=2025-09-01 → start=October 2025
      month=10,11,12 → 2025-10-01, 2025-11-01, 2025-12-01
      month=1..9     → 2026-01-01 .. 2026-09-01
    """
    if report_month is None:
        # Fallback: assume current year (should not happen for complete imports)
        report_month = date.today().replace(day=1)
    start_month = report_month.month + 1
    start_year = report_month.year
    if start_month > 12:
        start_month = 1
        start_year += 1
    year = start_year if month >= start_month else start_year + 1
    return f"{year}-{month:02d}-01"


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
    # Persist delivery_counts — one row per phase (p1–p5, not total)
    # -----------------------------------------------------------------------
    dc_rows = [
        DeliveryCount(
            import_id=import_id,
            phase=dc["phase"],
            count=dc["count"],
        )
        for dc in parsed["delivery_counts"]
        if dc["phase"] != Phase.total
    ]
    session.add_all(dc_rows)

    # -----------------------------------------------------------------------
    # Mark import as complete and persist report_month
    # -----------------------------------------------------------------------
    record.status = ImportStatus.complete
    # updated_at is managed by onupdate=func.now() on the model — no manual assignment needed

    # Persist report_month from import_meta
    report_month_str = parsed["import_meta"].get("report_month", "")
    if report_month_str:
        record.report_month = date.fromisoformat(report_month_str)

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


# ---------------------------------------------------------------------------
# GET /imports/{id}/pnl — C3
# ---------------------------------------------------------------------------

_PNL_SORT_ORDER = [
    "deliveries", "revenue", "cogs", "gross_profit",
    "sales_and_marketing", "direct_costs", "net_profit",
]


@router.get("/{import_id}/pnl", response_model=PnlResponse, status_code=200)
async def get_pnl(
    import_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> PnlResponse:
    log = logger.bind(import_id=str(import_id))
    log.info("pnl_get_start")

    result = await session.execute(
        select(Import).where(Import.id == import_id, Import.deleted_at.is_(None))
    )
    record = result.scalar_one_or_none()
    if record is None:
        log.warning("pnl_get_not_found")
        raise HTTPException(status_code=404, detail="Import not found")

    if record.status != ImportStatus.complete:
        log.warning("pnl_get_not_complete", status=record.status)
        raise HTTPException(status_code=404, detail="Import data not available (status is not complete)")

    rows_result = await session.execute(
        select(PnlSummary).where(PnlSummary.import_id == import_id)
    )
    db_rows = list(rows_result.scalars().all())

    # Sort in canonical P&L order (insertion order not reliable for UUID PKs)
    sort_key = {name: i for i, name in enumerate(_PNL_SORT_ORDER)}
    db_rows.sort(key=lambda r: sort_key.get(r.line_item, len(_PNL_SORT_ORDER)))

    rows = [
        PnlRow(
            line_item=row.line_item,
            budget=row.budget,
            current=row.current,
            delta=row.delta,
        )
        for row in db_rows
    ]

    log.info("pnl_get_complete", import_id=str(import_id), row_count=len(rows))
    return PnlResponse(import_id=import_id, rows=rows)


# ---------------------------------------------------------------------------
# PATCH /imports/{id}/n12m/{line_item}/{month} — C4
# ---------------------------------------------------------------------------


@router.patch("/{import_id}/n12m/{line_item}/{month}", status_code=204)
async def patch_n12m(
    import_id: uuid.UUID,
    line_item: str,
    month: int,
    body: N12mPatchRequest,
    session: AsyncSession = Depends(get_session),
) -> Response:
    log = logger.bind(import_id=str(import_id), line_item=line_item, month=month)
    log.info("n12m_patch_start")

    # 404 if import missing, soft-deleted, or not complete
    result = await session.execute(
        select(Import).where(Import.id == import_id, Import.deleted_at.is_(None))
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Import not found")
    if record.status != ImportStatus.complete:
        raise HTTPException(status_code=404, detail="Import data not available (status is not complete)")

    # 404 if line_item/month combination not found
    n12m_result = await session.execute(
        select(N12mLineItem).where(
            N12mLineItem.import_id == import_id,
            N12mLineItem.line_item == line_item,
            N12mLineItem.month == month,
            N12mLineItem.is_calculated.is_(False),
        )
    )
    n12m_row = n12m_result.scalar_one_or_none()
    if n12m_row is None:
        raise HTTPException(status_code=404, detail=f"Line item '{line_item}' month {month} not found")

    # Update the value on the matched row
    n12m_row.value = body.value

    # Reconstruct cascade input from DB — non-calculated rows only
    all_n12m_result = await session.execute(
        select(N12mLineItem)
        .where(N12mLineItem.import_id == import_id, N12mLineItem.is_calculated.is_(False))
        .order_by(N12mLineItem.sort_order, N12mLineItem.month)
    )
    all_n12m = list(all_n12m_result.scalars().all())

    pc_result = await session.execute(
        select(PhaseComparisonRow).where(PhaseComparisonRow.import_id == import_id)
    )
    pc_rows = list(pc_result.scalars().all())

    dc_result = await session.execute(
        select(DeliveryCount).where(DeliveryCount.import_id == import_id)
    )
    dc_rows_db = list(dc_result.scalars().all())

    # Group n12m rows into cascade format
    n12m_by_item: dict[str, dict] = {}
    for row in all_n12m:
        key = row.line_item
        if key not in n12m_by_item:
            n12m_by_item[key] = {
                "section": row.section,
                "line_item": row.line_item,
                "display_name": row.display_name,
                "is_calculated": row.is_calculated,
                "sort_order": row.sort_order,
                "entries": [],
            }
        month_str = _month_int_to_date_str(row.month, record.report_month)
        n12m_by_item[key]["entries"].append({"month": month_str, "value": row.value})

    parsed_for_cascade = {
        "import_meta": {
            "version_type": record.version_type.value,
            "source_type": record.source_type.value,
        },
        "delivery_counts": [{"phase": r.phase, "count": r.count} for r in dc_rows_db],
        "n12m_line_items": list(n12m_by_item.values()),
        "phase_comparison_rows": [
            {
                "line_item": r.line_item,
                "phase": r.phase,
                "budget": r.budget,
                "current": r.current,
            }
            for r in pc_rows
        ],
    }

    cascade = run_cascade(parsed_for_cascade)

    # Re-persist derived tables (delete + re-insert in same transaction)
    await session.execute(sa_delete(PerDeliveryRow).where(PerDeliveryRow.import_id == import_id))
    await session.execute(sa_delete(NcfSeries).where(NcfSeries.import_id == import_id))
    await session.execute(sa_delete(PnlSummary).where(PnlSummary.import_id == import_id))

    new_pd_rows = [
        PerDeliveryRow(
            import_id=import_id,
            line_item=row["line_item"],
            phase=row["phase"],
            budget=row.get("budget"),
            current=row.get("current"),
        )
        for row in cascade["per_delivery_rows"]
    ]
    session.add_all(new_pd_rows)

    new_ncf_rows = [
        NcfSeries(
            import_id=import_id,
            month=int(row["month"].split("-")[1]),
            series_type=row["series_type"],
            value=row["value"],
        )
        for row in cascade["ncf_series"]
    ]
    session.add_all(new_ncf_rows)

    new_pnl_rows = [
        PnlSummary(
            import_id=import_id,
            line_item=row["line_item"],
            budget=row.get("budget_total"),
            current=row.get("current_total"),
        )
        for row in cascade["pnl_summaries"]
    ]
    session.add_all(new_pnl_rows)

    # Delete all calculated n12m rows and re-insert from cascade output
    await session.execute(
        sa_delete(N12mLineItem).where(
            N12mLineItem.import_id == import_id,
            N12mLineItem.is_calculated.is_(True),
        )
    )
    for row in cascade["n12m_line_items"]:
        if row["is_calculated"]:
            for entry in row["entries"]:
                month_int = int(entry["month"].split("-")[1])
                session.add(N12mLineItem(
                    import_id=import_id,
                    month=month_int,
                    section=row["section"],
                    line_item=row["line_item"],
                    value=entry["value"],
                    display_name=row["display_name"],
                    is_calculated=True,
                    sort_order=row["sort_order"],
                    is_actual=False,
                ))

    await session.commit()
    log.info("n12m_patch_complete")
    return Response(status_code=204)
