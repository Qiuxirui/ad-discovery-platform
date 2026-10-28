"""统计相关响应模型（管理端分析与漏斗）。"""

from __future__ import annotations

from pydantic import BaseModel

__all__ = [
    "AdStatRow",
    "CategoryStatRow",
    "FunnelOut",
    "FunnelStep",
    "MetricSet",
    "StatsOverviewOut",
    "TrendPoint",
]


class MetricSet(BaseModel):
    """一组指标（每个比率都必须带分母口径）。"""

    impressions: int = 0
    unique_visitors: int = 0
    detail_views: int = 0
    link_clicks: int = 0
    favorites: int = 0
    reports: int = 0
    ctr_detail: float = 0.0
    ctr_impression: float = 0.0
    favorite_rate: float = 0.0
    report_rate_permille: float = 0.0


class TrendPoint(BaseModel):
    """按日趋势点。"""

    date: str
    impressions: int = 0
    detail_views: int = 0
    link_clicks: int = 0


class AdStatRow(BaseModel):
    """按广告排行行。"""

    ad_id: int
    title: str
    merchant_name: str = ""
    category_name: str = ""
    impressions: int = 0
    detail_views: int = 0
    link_clicks: int = 0
    reports: int = 0
    ctr_detail: float = 0.0
    ctr_impression: float = 0.0


class CategoryStatRow(BaseModel):
    """按类别分布行。"""

    slug: str
    name: str
    impressions: int = 0
    detail_views: int = 0
    link_clicks: int = 0


class FunnelStep(BaseModel):
    """漏斗单步。"""

    key: str
    label: str
    count: int = 0
    rate: float = 0.0


class FunnelOut(BaseModel):
    """漏斗四步。"""

    steps: list[FunnelStep] = []
    note: str = ""


class StatsOverviewOut(BaseModel):
    """统计总览。"""

    range: dict[str, str | None] = {}
    totals: MetricSet = MetricSet()
    by_ad: list[AdStatRow] = []
    by_category: list[CategoryStatRow] = []
    abnormal: list[dict[str, object]] = []
    notes: dict[str, str] = {}
