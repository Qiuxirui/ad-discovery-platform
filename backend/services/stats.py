"""统计服务：商家报告与管理端分析共用同一套口径（架构 §6.6）。

指标口径（禁止只写"点击率"不带分母）：
- 展示量 ``count(impression)``（含重复展示）
- 独立展示 ``count(distinct visitor_id) where impression``（仅后台）
- 详情查看量 ``count(detail_view)``
- 点击量 ``count(link_click)``（禁止称"成交/订单"）
- 详情页点击率 ``link_click / detail_view``；整体点击率 ``link_click / impression``
- 收藏率 ``favorite UV / detail_view UV``；举报率 ``report / impression``（万分比）
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..constants import AD_STATUS, AD_STATUS_LABELS
from ..models import Ad, Category, Event, Favorite, Merchant, Report
from ..utils.timeutil import cst_date_range_utc, cst_date_str, days_left, now_utc, utc_to_iso_z

__all__ = ["StatsService"]

NOUN_VISIBLE_NOTE = "展示量含重复展示；点击量不等于成交或订单"


def _safe_rate(numerator: int | float, denominator: int | float) -> float:
    """安全比率（分母为 0 返回 0.0），保留 4 位小数。"""
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _rate_permille(numerator: int | float, denominator: int | float) -> float:
    """万分比（分母为 0 返回 0.0）。

    直接对原始分子分母取万分位后保留 1 位小数，**不要**先把比率四舍五入到
    4 位小数再乘——那样会把 5/647 的 77.28 压成 77.0。
    """
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator) * 10000, 1)


def _count(db: Session, event_type: str, start: datetime, end: datetime, ad_id: int | None = None) -> int:
    stmt = select(func.count()).select_from(Event).where(
        Event.event_type == event_type, Event.ts >= start, Event.ts < end
    )
    if ad_id is not None:
        stmt = stmt.where(Event.ad_id == ad_id)
    return int(db.execute(stmt).scalar_one())


def _distinct_visitors(db: Session, event_type: str, start: datetime, end: datetime, ad_id: int | None = None) -> int:
    stmt = select(func.count(func.distinct(Event.visitor_id))).where(
        Event.event_type == event_type, Event.ts >= start, Event.ts < end
    )
    if ad_id is not None:
        stmt = stmt.where(Event.ad_id == ad_id)
    return int(db.execute(stmt).scalar_one())


class StatsService:
    """只读聚合。"""

    @staticmethod
    def metrics(db: Session, ad_id: int, start: datetime, end: datetime) -> dict[str, object]:
        """单广告指标集合。"""
        impressions = _count(db, "impression", start, end, ad_id)
        detail_views = _count(db, "detail_view", start, end, ad_id)
        link_clicks = _count(db, "link_click", start, end, ad_id)
        favorites = _count(db, "favorite", start, end, ad_id)
        reports = _count(db, "report", start, end, ad_id)
        unique_visitors = _distinct_visitors(db, "impression", start, end, ad_id)
        favorite_uv = _distinct_visitors(db, "favorite", start, end, ad_id)
        detail_uv = _distinct_visitors(db, "detail_view", start, end, ad_id)
        return {
            "impressions": impressions,
            "unique_visitors": unique_visitors,
            "detail_views": detail_views,
            "link_clicks": link_clicks,
            "favorites": favorites,
            "reports": reports,
            "ctr_detail": _safe_rate(link_clicks, detail_views),
            "ctr_impression": _safe_rate(link_clicks, impressions),
            "favorite_rate": _safe_rate(favorite_uv, detail_uv),
            "report_rate_permille": _rate_permille(reports, impressions),
        }

    @staticmethod
    def daily_trend(db: Session, ad_id: int, start: datetime, end: datetime) -> list[dict[str, object]]:
        """按北京时间自然日的趋势。"""
        day_expr = func.strftime("%Y-%m-%d", Event.ts, "+8 hours")
        rows = db.execute(
            select(day_expr.label("day"), Event.event_type, func.count(Event.id))
            .where(Event.ad_id == ad_id, Event.ts >= start, Event.ts < end)
            .group_by("day", Event.event_type)
            .order_by("day")
        ).all()
        bucket: dict[str, dict[str, object]] = {}
        for day, event_type, count in rows:
            entry = bucket.setdefault(
                str(day), {"date": str(day), "impressions": 0, "detail_views": 0, "link_clicks": 0}
            )
            if event_type == "impression":
                entry["impressions"] = int(count)
            elif event_type == "detail_view":
                entry["detail_views"] = int(count)
            elif event_type == "link_click":
                entry["link_clicks"] = int(count)
        return [bucket[key] for key in sorted(bucket)]

    @staticmethod
    def overview(db: Session, start: datetime, end: datetime) -> dict[str, object]:
        """平台总览：总计 + 按广告排行 + 按类别分布 + 异常标记。"""
        impressions = _count(db, "impression", start, end)
        detail_views = _count(db, "detail_view", start, end)
        link_clicks = _count(db, "link_click", start, end)
        favorites = _count(db, "favorite", start, end)
        reports = _count(db, "report", start, end)
        unique_visitors = _distinct_visitors(db, "impression", start, end)

        totals = {
            "impressions": impressions,
            "unique_visitors": unique_visitors,
            "detail_views": detail_views,
            "link_clicks": link_clicks,
            "favorites": favorites,
            "reports": reports,
            "ctr_detail": _safe_rate(link_clicks, detail_views),
            "ctr_impression": _safe_rate(link_clicks, impressions),
            "report_rate_permille": _rate_permille(reports, impressions),
        }

        ad_rows = db.execute(
            select(
                Event.ad_id,
                Event.event_type,
                func.count(Event.id),
            )
            .where(Event.ts >= start, Event.ts < end, Event.ad_id.is_not(None))
            .group_by(Event.ad_id, Event.event_type)
        ).all()
        per_ad: dict[int, dict[str, int]] = {}
        for ad_id, event_type, count in ad_rows:
            entry = per_ad.setdefault(int(ad_id), {"impressions": 0, "detail_views": 0, "link_clicks": 0, "reports": 0})
            if event_type == "impression":
                entry["impressions"] = int(count)
            elif event_type == "detail_view":
                entry["detail_views"] = int(count)
            elif event_type == "link_click":
                entry["link_clicks"] = int(count)
            elif event_type == "report":
                entry["reports"] = int(count)

        ads = db.execute(select(Ad).where(Ad.id.in_(list(per_ad.keys()) or [0]))).unique().scalars().all()
        ad_map = {ad.id: ad for ad in ads}
        by_ad = []
        for ad_id, entry in per_ad.items():
            ad = ad_map.get(ad_id)
            by_ad.append(
                {
                    "ad_id": ad_id,
                    "title": ad.title if ad is not None else "（广告已删除）",
                    "merchant_name": ad.merchant.name if ad is not None and ad.merchant is not None else "",
                    "category_name": ad.category.name if ad is not None and ad.category is not None else "",
                    "impressions": entry["impressions"],
                    "detail_views": entry["detail_views"],
                    "link_clicks": entry["link_clicks"],
                    "reports": entry["reports"],
                    "ctr_detail": _safe_rate(entry["link_clicks"], entry["detail_views"]),
                    "ctr_impression": _safe_rate(entry["link_clicks"], entry["impressions"]),
                }
            )
        by_ad.sort(key=lambda item: int(item["impressions"]), reverse=True)

        category_rows = db.execute(
            select(
                Category.slug,
                Category.name,
                Event.event_type,
                func.count(Event.id),
            )
            .join(Ad, Ad.id == Event.ad_id)
            .join(Category, Category.id == Ad.category_id)
            .where(Event.ts >= start, Event.ts < end)
            .group_by(Category.slug, Category.name, Event.event_type)
        ).all()
        cat_bucket: dict[str, dict[str, object]] = {}
        for slug, name, event_type, count in category_rows:
            entry = cat_bucket.setdefault(
                str(slug),
                {"slug": str(slug), "name": str(name), "impressions": 0, "detail_views": 0, "link_clicks": 0},
            )
            if event_type == "impression":
                entry["impressions"] = int(count)
            elif event_type == "detail_view":
                entry["detail_views"] = int(count)
            elif event_type == "link_click":
                entry["link_clicks"] = int(count)
        by_category = sorted(cat_bucket.values(), key=lambda item: int(item["impressions"]), reverse=True)

        return {
            "range": {"from": utc_to_iso_z(start), "to": utc_to_iso_z(end)},
            "totals": totals,
            "by_ad": by_ad,
            "by_category": by_category,
            "abnormal": StatsService.abnormal_flags(db, start, end),
            "notes": {"metrics": NOUN_VISIBLE_NOTE},
        }

    @staticmethod
    def funnel(db: Session, start: datetime, end: datetime) -> dict[str, object]:
        """漏斗：首页访问 → 列表 → 详情 → 外链（四步单调不增）。"""
        home = db.execute(
            select(func.count())
            .select_from(Event)
            .where(Event.event_type == "page_view", Event.page == "home", Event.ts >= start, Event.ts < end)
        ).scalar_one()
        listing = db.execute(
            select(func.count())
            .select_from(Event)
            .where(
                Event.event_type == "page_view",
                Event.page.in_(["list", "search"]),
                Event.ts >= start,
                Event.ts < end,
            )
        ).scalar_one()
        detail = _count(db, "detail_view", start, end)
        outbound = _count(db, "link_click", start, end)

        counts = [int(home), int(listing), int(detail), int(outbound)]
        # 四步必须单调不增，用前一步上界截断，避免口径差异造成"伪增长"
        for index in range(1, len(counts)):
            counts[index] = min(counts[index], counts[index - 1])
        base = counts[0] or 0

        labels = [("home", "首页访问"), ("list", "列表/搜索"), ("detail", "详情查看"), ("outbound", "外链点击")]
        steps = [
            {
                "key": key,
                "label": label,
                "count": counts[index],
                "rate": _safe_rate(counts[index], base) if base else 0.0,
            }
            for index, (key, label) in enumerate(labels)
        ]
        return {
            "steps": steps,
            "note": "转化率以首页访问为分母；点击量不等于成交",
        }

    @staticmethod
    def abnormal_flags(db: Session, start: datetime, end: datetime) -> list[dict[str, object]]:
        """同一 visitor 单日对同一广告点击 >20 次 → 疑似刷量标记（P1-E-03）。"""
        day_expr = func.strftime("%Y-%m-%d", Event.ts, "+8 hours")
        pairs = (
            select(
                Event.ad_id.label("ad_id"),
                Event.visitor_id.label("visitor_id"),
                day_expr.label("day"),
                func.count(Event.id).label("clicks"),
            )
            .where(
                Event.event_type == "link_click",
                Event.ts >= start,
                Event.ts < end,
                Event.ad_id.is_not(None),
            )
            .group_by("ad_id", "visitor_id", "day")
            .having(func.count(Event.id) > 20)
            .subquery()
        )
        rows = db.execute(
            select(pairs.c.ad_id, func.count(pairs.c.visitor_id), func.sum(pairs.c.clicks)).group_by(pairs.c.ad_id)
        ).all()
        if not rows:
            return []
        ad_ids = [int(row[0]) for row in rows]
        ads = db.execute(select(Ad).where(Ad.id.in_(ad_ids))).unique().scalars().all()
        title_map = {ad.id: ad.title for ad in ads}
        return [
            {
                "ad_id": int(row[0]),
                "title": title_map.get(int(row[0]), "（广告已删除）"),
                "flagged_visitors": int(row[1]),
                "total_clicks": int(row[2] or 0),
                "note": "含异常流量：同一访客单日点击超过 20 次",
            }
            for row in rows
        ]

    @staticmethod
    def merchant_report(db: Session, ad: Ad, start: datetime, end: datetime) -> dict[str, object]:
        """商家报告：指标 + 按日趋势 + 口径说明。"""
        metrics = StatsService.metrics(db, ad.id, start, end)
        trend = StatsService.daily_trend(db, ad.id, start, end)
        return {
            "ad": {
                "id": ad.id,
                "title": ad.title,
                "status": ad.status,
                "status_label": AD_STATUS_LABELS.get(ad.status, ad.status),
                "valid_to_local_date": cst_date_str(ad.valid_to),
                "days_left": days_left(ad.valid_to),
            },
            "range": {"from": utc_to_iso_z(start), "to": utc_to_iso_z(end)},
            "metrics": metrics,
            "daily": trend,
            "notes": {
                "impressions": "展示量含重复展示",
                "unique_visitors": "独立展示人数（按访客去重）",
                "detail_views": "详情页打开次数（同会话 30 分钟内计 1 次）",
                "link_clicks": "外链点击次数，不等于成交或订单",
                "ctr_detail": "点击率 = 外链点击 / 详情查看",
                "ctr_impression": "点击率 = 外链点击 / 展示",
                "report_rate_permille": "举报率（万分比）= 举报数 / 展示数 × 10000",
            },
        }

    @staticmethod
    def merchant_status_counts(db: Session, merchant_id: int) -> dict[str, int]:
        """商家端"我的广告"状态计数。"""
        rows = db.execute(
            select(Ad.status, func.count(Ad.id)).where(Ad.merchant_id == merchant_id).group_by(Ad.status)
        ).all()
        counts = {status: 0 for status in AD_STATUS}
        total = 0
        for status, count in rows:
            counts[str(status)] = int(count)
            total += int(count)
        counts["all"] = total
        return counts

    @staticmethod
    def merchant_report_range(from_date: str | None, to_date: str | None) -> tuple[datetime, datetime]:
        """默认近 7 天（北京时间自然日）。"""
        return cst_date_range_utc(from_date, to_date)

    @staticmethod
    def last_30_days() -> tuple[datetime, datetime]:
        """近 30 天窗口（"最多收藏"排序与风险聚合用）。"""
        end = now_utc()
        return end - timedelta(days=30), end

    @staticmethod
    def merchant_report_favorites(db: Session, ad_id: int, start: datetime, end: datetime) -> int:
        """收藏数（收藏表口径，非事件表）。"""
        return int(
            db.execute(
                select(func.count())
                .select_from(Favorite)
                .where(Favorite.ad_id == ad_id, Favorite.created_at >= start, Favorite.created_at < end)
            ).scalar_one()
        )

    @staticmethod
    def merchant_report_reports(db: Session, ad_id: int, start: datetime, end: datetime) -> int:
        """举报数（举报表口径）。"""
        return int(
            db.execute(
                select(func.count())
                .select_from(Report)
                .where(Report.ad_id == ad_id, Report.created_at >= start, Report.created_at < end)
            ).scalar_one()
        )

    @staticmethod
    def merchant_name(db: Session, merchant_id: int) -> str:
        """商家名（后台列表展示用）。"""
        merchant = db.get(Merchant, merchant_id)
        return merchant.name if merchant is not None else ""
