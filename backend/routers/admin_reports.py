"""管理端举报处理：列表（超时高亮）、开始处理、成立、驳回、近 7 天统计。"""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..constants import REPORT_REASON_LABELS, REPORT_STATUS_LABELS, REPORT_STATUS_USER_TEXT
from ..database import get_db
from ..deps import require_admin
from ..models import Ad, AdminUser, Report, ReportFollowup
from ..schemas.admin import AdminReportListOut, AdminReportRowOut, DismissIn, ResolveIn
from ..services.ads import api_error
from ..services.reports import ReportService
from ..utils.timeutil import now_utc, utc_to_iso_z

router = APIRouter(tags=["admin-reports"])

audit_log = logging.getLogger("adx.audit")

SLA_HOURS = 24


def report_row(db: Session, report: Report) -> AdminReportRowOut:
    """举报行（含广告快照与追加说明）。"""
    snapshot = None
    if report.ad_snapshot:
        try:
            loaded = json.loads(report.ad_snapshot)
            snapshot = loaded if isinstance(loaded, dict) else None
        except json.JSONDecodeError:
            snapshot = None
    ad_title = ""
    if snapshot:
        ad_title = str(snapshot.get("title", ""))
    if not ad_title:
        ad = db.get(Ad, report.ad_id)
        ad_title = ad.title if ad is not None else "（广告已删除）"

    followups = db.execute(
        select(ReportFollowup).where(ReportFollowup.report_id == report.id).order_by(ReportFollowup.created_at.asc())
    ).scalars().all()

    overdue = False
    if report.status in ("pending", "reviewing") and report.created_at is not None:
        overdue = report.created_at < now_utc() - timedelta(hours=SLA_HOURS)

    return AdminReportRowOut(
        id=report.id,
        code=report.code,
        ad_id=report.ad_id,
        ad_title=ad_title,
        ad_snapshot=snapshot,
        reason_code=report.reason_code,
        reason_label=REPORT_REASON_LABELS.get(report.reason_code, report.reason_code),
        detail=report.detail,
        status=report.status,
        status_label=REPORT_STATUS_LABELS.get(report.status, report.status),
        created_at=utc_to_iso_z(report.created_at),
        handled_at=utc_to_iso_z(report.handled_at),
        overdue=overdue,
        admin_note=report.admin_note,
        followups=[
            {"note": item.note, "created_at": utc_to_iso_z(item.created_at)} for item in followups
        ],
    )


@router.get("/api/admin/reports", response_model=AdminReportListOut)
def list_reports(
    status: str | None = Query(default=None),
    overdue: int = Query(default=0, description="1=只看超 24h 未处理"),
    page: int = Query(default=1, ge=0),
    page_size: int = Query(default=20, ge=1, le=60),
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> AdminReportListOut:
    """举报列表（按状态与时间排序，超时标记）。"""
    safe_page = max(1, page)
    stmt = select(Report)
    if status:
        if status not in REPORT_STATUS_LABELS:
            raise api_error(422, "STATUS_INVALID", "举报状态筛选值不合法")
        stmt = stmt.where(Report.status == status)
    if overdue:
        stmt = stmt.where(
            Report.status.in_(["pending", "reviewing"]),
            Report.created_at < now_utc() - timedelta(hours=SLA_HOURS),
        )

    total = int(db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one())
    rows = (
        db.execute(
            stmt.order_by(Report.created_at.desc()).offset((safe_page - 1) * page_size).limit(page_size)
        )
        .unique()
        .scalars()
        .all()
    )
    items = [report_row(db, report) for report in rows]

    week_start = now_utc() - timedelta(days=7)
    received = int(
        db.execute(select(func.count()).select_from(Report).where(Report.created_at >= week_start)).scalar_one()
    )
    resolved = int(
        db.execute(
            select(func.count())
            .select_from(Report)
            .where(Report.status == "resolved", Report.created_at >= week_start)
        ).scalar_one()
    )
    dismissed = int(
        db.execute(
            select(func.count())
            .select_from(Report)
            .where(Report.status == "dismissed", Report.created_at >= week_start)
        ).scalar_one()
    )
    handled = db.execute(
        select(Report.created_at, Report.handled_at).where(
            Report.handled_at.is_not(None), Report.created_at >= week_start
        )
    ).all()
    avg_hours = 0.0
    if handled:
        total_hours = sum((row[1] - row[0]).total_seconds() / 3600 for row in handled)
        avg_hours = round(total_hours / len(handled), 1)

    return AdminReportListOut(
        items=items,
        week_stats={
            "received": received,
            "resolved": resolved,
            "dismissed": dismissed,
            "avg_hours": avg_hours,
        },
        total=total,
        page=safe_page,
        page_size=page_size,
    )


def _get_report(db: Session, report_id: int) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise api_error(404, "REPORT_NOT_FOUND", "该举报不存在")
    return report


@router.post("/api/admin/reports/{report_id}/start", response_model=AdminReportRowOut)
def start_report(
    report_id: int,
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> AdminReportRowOut:
    """开始处理：``pending`` → ``reviewing``。"""
    report = _get_report(db, report_id)
    report = ReportService.start_review(db, report)
    return report_row(db, report)


@router.post("/api/admin/reports/{report_id}/resolve", response_model=AdminReportRowOut)
def resolve_report(
    report_id: int,
    payload: ResolveIn,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminReportRowOut:
    """判定成立：举报 ``resolved`` + 广告下架（或记录整改要求）。"""
    report = _get_report(db, report_id)
    report = ReportService.resolve(db, report, admin.id, payload.action, payload.note)
    return report_row(db, report)


@router.post("/api/admin/reports/{report_id}/dismiss", response_model=AdminReportRowOut)
def dismiss_report(
    report_id: int,
    payload: DismissIn,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminReportRowOut:
    """判定不成立：举报 ``dismissed``，广告不变。"""
    report = _get_report(db, report_id)
    report = ReportService.dismiss(db, report, admin.id, payload.note)
    return report_row(db, report)


__all__ = ["REPORT_STATUS_USER_TEXT", "router"]
