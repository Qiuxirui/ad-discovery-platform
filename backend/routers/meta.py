"""元数据与健康检查。"""

from __future__ import annotations

from fastapi import APIRouter

from ..constants import (
    AD_STATUS_OPTIONS,
    CITIES,
    EVENT_TYPES,
    FAVORITES_LIMIT,
    HIDES_LIMIT,
    PAGE_IDS,
    PAGE_SIZE,
    REJECT_REASONS,
    REPORT_REASONS,
    REPORT_STATUS_OPTIONS,
    SORT_OPTIONS,
    DAILY_NEW_ADS_LIMIT,
    ONLINE_ADS_LIMIT,
)
from ..utils.timeutil import now_utc, utc_to_iso_z

router = APIRouter(tags=["meta"])

NOTICE_TEXT = "本站所有内容均为商家付费推广，已标注「广告」。平台不参与交易，请自行判断。"
CTA_TEXT = "前往商家页面"
LEAVE_HINT = "即将离开本平台"


@router.get("/api/health")
def health() -> dict[str, str]:
    """部署自检。"""
    return {"status": "ok", "time": utc_to_iso_z(now_utc()) or ""}


@router.get("/api/meta")
def get_meta() -> dict[str, object]:
    """前端唯一字典来源：城市、原因、状态、排序、上限、精确文案。"""
    return {
        "cities": CITIES,
        "report_reasons": REPORT_REASONS,
        "reject_reasons": REJECT_REASONS,
        "ad_statuses": AD_STATUS_OPTIONS,
        "report_statuses": REPORT_STATUS_OPTIONS,
        "sorts": SORT_OPTIONS,
        "event_types": list(EVENT_TYPES),
        "pages": list(PAGE_IDS),
        "limits": {
            "favorites": FAVORITES_LIMIT,
            "hides": HIDES_LIMIT,
            "daily_new_ads": DAILY_NEW_ADS_LIMIT,
            "online_ads": ONLINE_ADS_LIMIT,
            "page_size": PAGE_SIZE,
        },
        "texts": {
            "notice": NOTICE_TEXT,
            "ad_badge": "广告",
            "cta": CTA_TEXT,
            "leave_hint": LEAVE_HINT,
            "go_title": "您即将离开本站",
        },
    }
