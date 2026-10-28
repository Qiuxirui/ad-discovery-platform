"""管理端运营首页与基础分析（总览 / 漏斗 / CSV 导出）。"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..constants import AD_STATUS_LABELS
from ..database import get_db
from ..deps import require_admin
from ..models import Ad, AdminUser, Event, Report, Review
from ..schemas.admin import AdminSummaryOut
from ..services.stats import StatsService
from ..utils.csv_export import csv_response
from ..utils.timeutil import cst_date_range_utc, cst_date_str, now_utc, today_cst_range_utc, utc_to_iso_z

router = APIRouter(tags=["admin-stats"])

SLA_HOURS = 24


@router.get("/api/admin/summary", response_model=AdminSummaryOut)
def admin_summary(
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> AdminSummaryOut:
    """运营首页数字（与对应列表过滤结果完全一致）。"""
    current = now_utc()
    pending_ads = int(
        db.execute(select(func.count()).select_from(Ad).where(Ad.status == "pending")).scalar_one()
    )
    pending_reports = int(
        db.execute(select(func.count()).select_from(Report).where(Report.status == "pending")).scalar_one()
    )
    overdue_reports = int(
        db.execute(
            select(func.count())
            .select_from(Report)
            .where(
                Report.status.in_(["pending", "reviewing"]),
                Report.created_at < current - timedelta(hours=SLA_HOURS),
            )
        ).scalar_one()
    )
    start, end = today_cst_range_utc(current)
    today_events = int(
        db.execute(
            select(func.count()).select_from(Event).where(Event.ts >= start, Event.ts < end)
        ).scalar_one()
    )
    today_processed = int(
        db.execute(
            select(func.count())
            .select_from(Review)
            .where(
                Review.action.in_(["approve", "reject", "edit_approve"]),
                Review.created_at >= start,
                Review.created_at < end,
            )
        ).scalar_one()
    )
    week_start = current - timedelta(days=7)
    week_resolved = int(
        db.execute(
            select(func.count())
            .select_from(Report)
            .where(Report.status == "resolved", Report.handled_at.is_not(None), Report.handled_at >= week_start)
        ).scalar_one()
    )
    return AdminSummaryOut(
        pending_ads=pending_ads,
        pending_reports=pending_reports,
        sla_overdue_reports=overdue_reports,
        today_events=today_events,
        today_processed_ads=today_processed,
        week_resolved_reports=week_resolved,
    )


@router.get("/api/admin/stats/overview")
def stats_overview(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """总览：总计 + 按广告排行 + 按类别分布 + 异常标记。"""
    start, end = cst_date_range_utc(from_, to)
    overview = StatsService.overview(db, start, end)
    overview["range"] = {"from": cst_date_str(start), "to": cst_date_str(end)}
    return overview


@router.get("/api/admin/stats/funnel")
def stats_funnel(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """漏斗：首页访问 → 列表/搜索 → 详情查看 → 外链点击。"""
    start, end = cst_date_range_utc(from_, to)
    funnel = StatsService.funnel(db, start, end)
    funnel["range"] = {"from": cst_date_str(start), "to": cst_date_str(end)}
    return funnel


@router.get("/api/admin/stats/export.csv")
def export_stats(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    type: str = Query(default="ads", description="ads|category|events"),
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
):
    """导出统计 CSV（UTF-8 BOM）。"""
    start, end = cst_date_range_utc(from_, to)
    kind = (type or "ads").strip()
    from_label = cst_date_str(start) or ""
    to_label = cst_date_str(end - timedelta(seconds=1)) or ""

    if kind == "ads":
        overview = StatsService.overview(db, start, end)
        header = ["广告ID", "标题", "商家", "类别", "展示量", "详情查看量", "外链点击量", "举报数", "详情页点击率", "整体点击率"]
        rows = [
            [
                item["ad_id"],
                item["title"],
                item["merchant_name"],
                item["category_name"],
                item["impressions"],
                item["detail_views"],
                item["link_clicks"],
                item["reports"],
                item["ctr_detail"],
                item["ctr_impression"],
            ]
            for item in overview["by_ad"]
        ]
        filename = f"广告统计_{from_label}_{to_label}.csv"
        return csv_response(rows, header, filename)

    if kind == "category":
        overview = StatsService.overview(db, start, end)
        header = ["一级类别", "展示量", "详情查看量", "外链点击量"]
        rows = [
            [item["name"], item["impressions"], item["detail_views"], item["link_clicks"]]
            for item in overview["by_category"]
        ]
        filename = f"类别统计_{from_label}_{to_label}.csv"
        return csv_response(rows, header, filename)

    header = ["事件ID", "类型", "广告ID", "访客标识", "页面", "时间(UTC)", "序号"]
    events = (
        db.execute(
            select(Event)
            .where(Event.ts >= start, Event.ts < end)
            .order_by(Event.ts.asc())
            .limit(20000)
        )
        .scalars()
        .all()
    )
    rows = [
        [
            event.id,
            event.event_type,
            event.ad_id or "",
            event.visitor_id,
            event.page,
            utc_to_iso_z(event.ts),
            event.position if event.position is not None else "",
        ]
        for event in events
    ]
    filename = f"事件明细_{from_label}_{to_label}.csv"
    return csv_response(rows, header, filename)


__all__ = ["AD_STATUS_LABELS", "router"]
