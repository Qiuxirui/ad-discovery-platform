"""举报接口（匿名可提交，凭码可查）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..constants import REPORT_STATUS_USER_TEXT
from ..database import get_db
from ..deps import get_visitor_id
from ..schemas.common import OkOut
from ..schemas.visitor import FollowupIn, ReportIn, ReportLookupOut, ReportMineItem, ReportMineOut, ReportOut
from ..services.ads import api_error
from ..services.reports import ReportService

router = APIRouter(tags=["reports"])


@router.post("/api/reports", response_model=ReportOut)
def create_report(
    payload: ReportIn,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> ReportOut:
    """提交举报；同访客对同一广告 24h 内返回已有举报码。"""
    report, duplicate = ReportService.create(
        db, visitor_id, payload.ad_id, payload.reason_code, payload.detail
    )
    return ReportOut(
        code=report.code,
        status=report.status,
        duplicate=duplicate,
        message=(
            f"该广告你已在 24 小时内举报过，举报码 {report.code}，我们会在 48 小时内处理"
            if duplicate
            else REPORT_STATUS_USER_TEXT.get("pending", "已收到，我们会在 48 小时内处理")
        ),
    )


@router.get("/api/reports/mine", response_model=ReportMineOut)
def list_my_reports(
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> ReportMineOut:
    """本设备提交过的举报及状态。"""
    reports = ReportService.mine(db, visitor_id)
    items = [ReportMineItem(**ReportService.to_lookup_dict(report)) for report in reports]
    return ReportMineOut(items=items)


@router.get("/api/reports/lookup", response_model=ReportLookupOut)
def lookup_report(
    code: str = Query(min_length=3, max_length=16),
    db: Session = Depends(get_db),
) -> ReportLookupOut:
    """按举报码查询（不返回举报人与处理人信息）。"""
    report = ReportService.lookup(db, code)
    if report is None:
        raise api_error(404, "REPORT_NOT_FOUND", "未找到该举报码，请核对后重试")
    return ReportLookupOut(**ReportService.to_lookup_dict(report))


@router.post("/api/reports/{code}/followup", response_model=OkOut)
def add_followup(
    code: str,
    payload: FollowupIn,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> OkOut:
    """终态 7 天内可追加"仍有疑问"说明（不改状态）。"""
    report = ReportService.lookup(db, code)
    if report is None or report.visitor_id != visitor_id:
        raise api_error(404, "REPORT_NOT_FOUND", "未找到该举报，请核对举报码")
    ReportService.add_followup(db, report, visitor_id, payload.note)
    return OkOut()
