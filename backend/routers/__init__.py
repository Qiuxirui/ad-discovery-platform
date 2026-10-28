"""路由汇总（注册顺序与架构 §3.2 一致）。"""

from __future__ import annotations

from . import (
    admin_ads,
    admin_auth,
    admin_categories,
    admin_merchants,
    admin_reports,
    admin_review,
    admin_stats,
    events,
    merchant_ads,
    merchant_auth,
    merchant_report,
    meta,
    public_ads,
    public_categories,
    reports,
    visitor,
)

API_ROUTERS = [
    meta.router,
    public_categories.router,
    public_ads.router,
    events.router,
    visitor.router,
    reports.router,
    merchant_auth.router,
    merchant_ads.router,
    merchant_report.router,
    admin_auth.router,
    admin_review.router,
    admin_ads.router,
    admin_reports.router,
    admin_merchants.router,
    admin_categories.router,
    admin_stats.router,
]
