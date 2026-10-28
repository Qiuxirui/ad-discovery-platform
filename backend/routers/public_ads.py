"""公开浏览接口：列表、详情、同类、外链。"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_optional_visitor_id, get_visitor_id
from ..models import Event, Hide
from ..schemas.ad import AdCardOut, AdDetailOut, AdListOut, OutboundOut
from ..services.visibility import (
    apply_filters,
    apply_sort,
    build_detail,
    count_stmt,
    get_related_ads,
    get_visible_ad,
    hydrate_cards,
    page_size_or_default,
    visible_ads_stmt,
)
from ..utils.timeutil import now_utc, utc_to_iso_z
from ..utils.urlsafety import check_url_safety

router = APIRouter(tags=["ads"])

audit_log = logging.getLogger("adx.audit")

AD_NOT_VISIBLE_DETAIL = "该广告已结束或暂不可见"


def _hidden_ids(db: Session, visitor_id: str | None) -> list[int]:
    """当前访客已隐藏的广告 id（列表与同类推荐要排除）。"""
    if not visitor_id:
        return []
    return list(db.execute(select(Hide.ad_id).where(Hide.visitor_id == visitor_id)).scalars().all())


@router.get("/api/ads", response_model=AdListOut)
def list_ads(
    q: str | None = Query(default=None, max_length=60, description="标题/描述/标签关键词"),
    category: str | None = Query(default=None, description="一级类别 slug"),
    tag: str | None = Query(default=None, description="二级标签 slug"),
    city: str | None = Query(default=None, description="服务城市"),
    ending: int = Query(default=0, description="1=仅看即将结束（≤48h）"),
    promo: int = Query(default=0, description="1=仅看有优惠"),
    sort: str = Query(default="latest", description="latest|ending|popular"),
    page: int = Query(default=1, ge=0),
    page_size: int = Query(default=24, ge=1, le=60),
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> AdListOut:
    """公开列表：只返回在架且在有效期内的广告（双保险）。"""
    safe_page = max(1, page)
    safe_size = page_size_or_default(page_size)
    current = now_utc()

    stmt = apply_filters(
        visible_ads_stmt(current),
        q=q,
        category_slug=category,
        tag_slug=tag,
        city=city,
        ending=bool(ending),
        promo=bool(promo),
        exclude_ad_ids=_hidden_ids(db, visitor_id),
        now=current,
    )
    total = int(db.execute(count_stmt(stmt)).scalar_one())
    rows = (
        db.execute(apply_sort(stmt, sort, current).offset((safe_page - 1) * safe_size).limit(safe_size))
        .unique()
        .scalars()
        .all()
    )
    items = hydrate_cards(db, list(rows), visitor_id)
    return AdListOut(
        items=items,
        page=safe_page,
        page_size=safe_size,
        total=total,
        has_more=safe_page * safe_size < total,
    )


@router.get("/api/ads/{ad_id}", response_model=AdDetailOut)
def get_ad_detail(
    ad_id: int,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> AdDetailOut:
    """详情页；不可见返回 ``404 AD_NOT_VISIBLE``。"""
    ad = get_visible_ad(db, ad_id)
    if ad is None:
        from ..services.ads import api_error

        raise api_error(404, "AD_NOT_VISIBLE", AD_NOT_VISIBLE_DETAIL)
    return build_detail(db, ad, visitor_id=visitor_id)


@router.get("/api/ads/{ad_id}/related", response_model=list[AdCardOut])
def get_ad_related(
    ad_id: int,
    limit: int = Query(default=3, ge=1, le=12),
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> list[AdCardOut]:
    """同类推荐：同类别 + 同城市（排除自身与已隐藏）。"""
    ad = get_visible_ad(db, ad_id)
    if ad is None:
        from ..services.ads import api_error

        raise api_error(404, "AD_NOT_VISIBLE", AD_NOT_VISIBLE_DETAIL)
    return get_related_ads(db, ad, visitor_id=visitor_id, limit=limit)


@router.get("/api/ads/{ad_id}/outbound", response_model=OutboundOut)
def get_ad_outbound(
    ad_id: int,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_optional_visitor_id),
) -> OutboundOut:
    """外链中间页数据：完整 URL 只在此接口下发，阻断时返回 ``url=None``。"""
    from ..services.ads import api_error

    ad = get_visible_ad(db, ad_id)
    if ad is None:
        raise api_error(404, "AD_NOT_VISIBLE", AD_NOT_VISIBLE_DETAIL)

    safety = check_url_safety(ad.landing_url)
    if not safety.ok:
        _record_blocked(db, ad.id, visitor_id, safety.domain or ad.landing_domain, safety.code, safety.reason)
        audit_log.warning(
            "outbound_blocked ad_id=%s code=%s domain=%s", ad.id, safety.code, safety.domain or ad.landing_domain
        )
        return OutboundOut(
            allowed=False,
            domain=safety.domain or ad.landing_domain,
            url=None,
            block_reason=safety.reason,
            block_code=safety.code,
        )

    return OutboundOut(
        allowed=True,
        domain=safety.domain,
        url=safety.url,
        block_reason=None,
        block_code=None,
    )


def _record_blocked(
    db: Session,
    ad_id: int,
    visitor_id: str | None,
    domain: str,
    code: str,
    reason: str,
) -> None:
    """记录 ``external_blocked`` 事件（不去重）与审计日志。"""
    if not visitor_id:
        return
    event = Event(
        id=str(uuid.uuid4()),
        event_type="external_blocked",
        ad_id=ad_id,
        visitor_id=visitor_id,
        session_id=str(uuid.uuid4()),
        ts=now_utc(),
        page="detail",
        position=None,
        meta=json.dumps({"domain": domain, "code": code, "reason": reason}, ensure_ascii=False),
    )
    try:
        db.add(event)
        db.commit()
    except Exception:  # noqa: BLE001 - 埋点失败不得影响阻断响应
        db.rollback()
        audit_log.warning("blocked_event_failed ad_id=%s code=%s", ad_id, code)


def _iso(value: datetime | None) -> str | None:
    """供调试使用的 ISO 输出。"""
    return utc_to_iso_z(value)
