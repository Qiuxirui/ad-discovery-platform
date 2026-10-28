"""商家效果报告与 CSV 导出。"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_merchant
from ..models import Ad, Merchant
from ..services.ads import api_error
from ..services.stats import StatsService
from ..utils.csv_export import csv_response
from ..utils.timeutil import cst_date_range_utc, cst_date_str

router = APIRouter(prefix="/api/merchant", tags=["merchant-report"])


def _own_ad(db: Session, ad_id: int, merchant: Merchant) -> Ad:
    ad = db.get(Ad, ad_id)
    if ad is None or ad.merchant_id != merchant.id:
        raise api_error(404, "AD_NOT_FOUND", "该广告不存在")
    return ad


@router.get("/report")
def get_report(
    ad_id: int = Query(..., description="广告 id"),
    from_: str | None = Query(default=None, alias="from", description="开始日期 YYYY-MM-DD"),
    to: str | None = Query(default=None, description="结束日期 YYYY-MM-DD"),
    merchant: Merchant = Depends(require_merchant),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """单广告效果报告：4 个指标 + 按日趋势 + 口径说明。"""
    ad = _own_ad(db, ad_id, merchant)
    start, end = cst_date_range_utc(from_, to)
    report = StatsService.merchant_report(db, ad, start, end)
    report["ad"]["message"] = (
        "广告上线后开始统计"
        if ad.status in ("active", "expired")
        else "广告尚未上线，上线后开始统计"
    )
    return report


@router.get("/report/export.csv")
def export_report(
    ad_id: int = Query(..., description="广告 id"),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    merchant: Merchant = Depends(require_merchant),
    db: Session = Depends(get_db),
):
    """导出 CSV（UTF-8 BOM，Excel 打开中文正常）。"""
    ad = _own_ad(db, ad_id, merchant)
    start, end = cst_date_range_utc(from_, to)
    metrics = StatsService.metrics(db, ad.id, start, end)
    trend = StatsService.daily_trend(db, ad.id, start, end)

    header = ["日期", "展示量（含重复）", "详情查看量", "外链点击量"]
    rows: list[list[object]] = [
        [item["date"], item["impressions"], item["detail_views"], item["link_clicks"]] for item in trend
    ]
    rows.append(["合计", metrics["impressions"], metrics["detail_views"], metrics["link_clicks"]])
    rows.append([])
    rows.append(["指标", "数值", "口径说明", ""])
    rows.append(["展示量", metrics["impressions"], "count(impression)，含重复展示", ""])
    rows.append(["独立展示人数", metrics["unique_visitors"], "count(distinct visitor_id) where impression", ""])
    rows.append(["详情查看量", metrics["detail_views"], "count(detail_view)", ""])
    rows.append(["外链点击量", metrics["link_clicks"], "count(link_click)，不等于成交或订单", ""])
    rows.append(["详情页点击率", metrics["ctr_detail"], "外链点击 / 详情查看", ""])
    rows.append(["整体点击率", metrics["ctr_impression"], "外链点击 / 展示", ""])
    rows.append(["收藏数", metrics["favorites"], "count(favorite)", ""])
    rows.append(["举报数", metrics["reports"], "count(report)", ""])

    from_label = from_ or cst_date_str(start)
    to_label = to or cst_date_str(end - timedelta(seconds=1))
    filename = f"报告_{ad.title}_{from_label}_{to_label}.csv"
    return csv_response(rows, header, filename)
