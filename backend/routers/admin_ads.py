"""管理端广告台账：筛选列表、单条详情。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..constants import AD_STATUS, AD_STATUS_LABELS
from ..database import get_db
from ..deps import require_admin
from ..models import Ad, AdminUser, Event, Merchant
from ..schemas.admin import AdEnvelope, AdminAdListOut, AdminAdRowOut
from ..services.ads import api_error, to_manage_out
from ..utils.timeutil import cst_date_str, days_left, utc_to_iso_z

router = APIRouter(tags=["admin-ads"])


@router.get("/api/admin/ads", response_model=AdminAdListOut)
def list_ads(
    status: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=60),
    merchant_id: int | None = Query(default=None),
    category_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=0),
    page_size: int = Query(default=20, ge=1, le=60),
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> AdminAdListOut:
    """广告台账（管理员不过滤可见性，看全部状态）。"""
    safe_page = max(1, page)
    stmt = select(Ad)
    if status:
        if status not in AD_STATUS:
            raise api_error(422, "STATUS_INVALID", "状态筛选值不合法")
        stmt = stmt.where(Ad.status == status)
    if merchant_id is not None:
        stmt = stmt.where(Ad.merchant_id == merchant_id)
    if category_id is not None:
        stmt = stmt.where(Ad.category_id == category_id)
    keyword = (q or "").strip()
    if keyword:
        like = f"%{keyword.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Ad.title).like(like),
                Ad.merchant_id.in_(select(Merchant.id).where(func.lower(Merchant.name).like(like))),
            )
        )

    total = int(db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one())
    rows = (
        db.execute(
            stmt.order_by(Ad.updated_at.desc(), Ad.id.desc())
            .offset((safe_page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .scalars()
        .all()
    )
    ad_ids = [ad.id for ad in rows] or [0]
    metrics_rows = db.execute(
        select(Event.ad_id, Event.event_type, func.count(Event.id))
        .where(Event.ad_id.in_(ad_ids))
        .group_by(Event.ad_id, Event.event_type)
    ).all()
    metrics: dict[int, dict[str, int]] = {}
    for ad_id, event_type, count in metrics_rows:
        entry = metrics.setdefault(int(ad_id), {"impressions": 0, "detail_views": 0, "link_clicks": 0, "reports": 0})
        key_map = {"impression": "impressions", "detail_view": "detail_views", "link_click": "link_clicks", "report": "reports"}
        key = key_map.get(str(event_type))
        if key:
            entry[key] = int(count)

    items = []
    for ad in rows:
        entry = metrics.get(ad.id, {"impressions": 0, "detail_views": 0, "link_clicks": 0, "reports": 0})
        items.append(
            AdminAdRowOut(
                id=ad.id,
                title=ad.title,
                merchant_id=ad.merchant_id,
                merchant_name=ad.merchant.name if ad.merchant is not None else "",
                category_name=ad.category.name if ad.category is not None else "",
                status=ad.status,
                status_label=AD_STATUS_LABELS.get(ad.status, ad.status),
                valid_to_local_date=cst_date_str(ad.valid_to),
                days_left=days_left(ad.valid_to),
                impressions=entry["impressions"],
                detail_views=entry["detail_views"],
                link_clicks=entry["link_clicks"],
                reports=entry["reports"],
                offline_reason=ad.offline_reason,
                updated_at=utc_to_iso_z(ad.updated_at),
            )
        )

    count_rows = db.execute(select(Ad.status, func.count(Ad.id)).group_by(Ad.status)).all()
    counts = {code: 0 for code in AD_STATUS}
    counts["all"] = 0
    for code, count in count_rows:
        counts[str(code)] = int(count)
        counts["all"] += int(count)

    return AdminAdListOut(
        items=items, counts=counts, total=total, page=safe_page, page_size=page_size
    )


@router.get("/api/admin/ads/{ad_id}", response_model=AdEnvelope)
def get_ad(
    ad_id: int,
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> AdEnvelope:
    """单条广告全字段（后台详情/操作历史入口）。"""
    ad = db.get(Ad, ad_id)
    if ad is None:
        raise api_error(404, "AD_NOT_FOUND", "该广告不存在")
    return AdEnvelope(ad=to_manage_out(ad))
