"""匿名访客接口：收藏、隐藏、偏好、清空数据。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..constants import CITIES, FAVORITES_LIMIT, HIDES_LIMIT
from ..database import get_db
from ..deps import get_visitor_id
from ..models import Ad, Category, Favorite, Hide, Preference
from ..schemas.visitor import (
    FavoriteIn,
    FavoriteListOut,
    FavoriteToggleOut,
    HideIn,
    HideListOut,
    PreferenceIn,
    PreferenceOut,
    PreferenceSaveOut,
    VisitorDataDeletedOut,
    VisitorLimitsOut,
    VisitorMeOut,
)
from ..services.ads import api_error
from ..services.events import EventService
from ..services.visibility import hydrate_card, is_visible
from ..utils.timeutil import now_utc
from ..visitor import ensure_visitor

router = APIRouter(tags=["visitor"])

HIDE_MESSAGE = "已生效：该类广告将少出现在你的列表"
FAVORITE_MESSAGE = "已加入收藏"


def _ensure_visitor(db: Session, visitor_id: str) -> None:
    """确保访客记录存在（中间件节流可能尚未落库）。"""
    ensure_visitor(db, visitor_id)


def _favorite_ids(db: Session, visitor_id: str) -> list[int]:
    return list(
        db.execute(
            select(Favorite.ad_id).where(Favorite.visitor_id == visitor_id).order_by(Favorite.created_at.desc())
        ).scalars().all()
    )


def _hide_ids(db: Session, visitor_id: str) -> list[int]:
    return list(
        db.execute(
            select(Hide.ad_id).where(Hide.visitor_id == visitor_id).order_by(Hide.created_at.desc())
        ).scalars().all()
    )


@router.get("/api/visitor/me", response_model=VisitorMeOut)
def get_me(db: Session = Depends(get_db), visitor_id: str = Depends(get_visitor_id)) -> VisitorMeOut:
    """当前匿名标识 + 收藏/隐藏/偏好 + 上限。"""
    _ensure_visitor(db, visitor_id)
    db.commit()
    favorites = _favorite_ids(db, visitor_id)
    hides = _hide_ids(db, visitor_id)
    preference = db.get(Preference, visitor_id)
    categories: list[int] = []
    city: str | None = None
    if preference is not None:
        try:
            parsed = json.loads(preference.categories or "[]")
            if isinstance(parsed, list):
                categories = [int(item) for item in parsed]
        except (json.JSONDecodeError, TypeError, ValueError):
            categories = []
        city = preference.city
    return VisitorMeOut(
        visitor_id=visitor_id,
        favorite_ids=favorites,
        hide_ids=hides,
        preference=PreferenceOut(categories=categories, city=city),
        counts={"favorites": len(favorites), "hides": len(hides)},
        limits=VisitorLimitsOut(favorites=FAVORITES_LIMIT, hides=HIDES_LIMIT),
    )


@router.get("/api/visitor/favorites", response_model=FavoriteListOut)
def list_favorites(
    page: int = Query(default=1, ge=0),
    page_size: int = Query(default=24, ge=1, le=60),
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> FavoriteListOut:
    """收藏列表；已结束的条目保留展示但单独分组。"""
    safe_page = max(1, page)
    rows = db.execute(
        select(Favorite)
        .where(Favorite.visitor_id == visitor_id)
        .order_by(Favorite.created_at.desc())
        .offset((safe_page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    ad_ids = [row.ad_id for row in rows]
    if not ad_ids:
        return FavoriteListOut(items=[], groups={"active": [], "expired": []})

    order = {ad_id: index for index, ad_id in enumerate(ad_ids)}
    ads = db.execute(select(Ad).where(Ad.id.in_(ad_ids))).unique().scalars().all()
    ads = sorted(ads, key=lambda item: order.get(item.id, 999))
    hides = _hide_ids(db, visitor_id)
    cards = [
        hydrate_card(
            ad,
            favorite_ids=set(ad_ids),
            hide_ids=set(hides),
            expired=not is_visible(ad),
        )
        for ad in ads
    ]
    groups = {
        "active": [card for card in cards if not card.is_expired],
        "expired": [card for card in cards if card.is_expired],
    }
    return FavoriteListOut(items=cards, groups=groups)


@router.post("/api/visitor/favorites", response_model=FavoriteToggleOut)
def add_favorite(
    payload: FavoriteIn,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> FavoriteToggleOut:
    """收藏（幂等；上限 200，超限 409）。"""
    _ensure_visitor(db, visitor_id)
    ad = db.get(Ad, payload.ad_id)
    if ad is None:
        raise api_error(404, "AD_NOT_FOUND", "该广告不存在或已被删除")

    existing = db.execute(
        select(Favorite).where(Favorite.visitor_id == visitor_id, Favorite.ad_id == payload.ad_id)
    ).scalars().first()
    count = db.execute(
        select(func.count()).select_from(Favorite).where(Favorite.visitor_id == visitor_id)
    ).scalar_one()
    if existing is not None:
        db.commit()
        return FavoriteToggleOut(count=int(count), limit=FAVORITES_LIMIT, message="已在收藏中")

    if count >= FAVORITES_LIMIT:
        raise api_error(
            409,
            "LIMIT_REACHED",
            f"收藏已达上限 {FAVORITES_LIMIT} 条，请先清理部分收藏",
        )

    db.add(Favorite(visitor_id=visitor_id, ad_id=payload.ad_id, created_at=now_utc()))
    EventService.insert_single(
        db, visitor_id=visitor_id, event_type="favorite", ad_id=payload.ad_id, page="detail"
    )
    db.commit()
    return FavoriteToggleOut(count=int(count) + 1, limit=FAVORITES_LIMIT, message=FAVORITE_MESSAGE)


@router.delete("/api/visitor/favorites/{ad_id}", response_model=FavoriteToggleOut)
def remove_favorite(
    ad_id: int,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> FavoriteToggleOut:
    """取消收藏（写 ``unfavorite`` 事件，不抵扣 favorite 计数）。"""
    favorite = db.execute(
        select(Favorite).where(Favorite.visitor_id == visitor_id, Favorite.ad_id == ad_id)
    ).scalars().first()
    if favorite is not None:
        db.delete(favorite)
        EventService.insert_single(
            db, visitor_id=visitor_id, event_type="unfavorite", ad_id=ad_id, page="favorites"
        )
        db.commit()
    count = db.execute(
        select(func.count()).select_from(Favorite).where(Favorite.visitor_id == visitor_id)
    ).scalar_one()
    return FavoriteToggleOut(count=int(count), limit=FAVORITES_LIMIT, message="已取消收藏")


@router.get("/api/visitor/hides", response_model=HideListOut)
def list_hides(
    page: int = Query(default=1, ge=0),
    page_size: int = Query(default=24, ge=1, le=60),
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> HideListOut:
    """已隐藏广告（含已过期，用于恢复）。"""
    safe_page = max(1, page)
    rows = db.execute(
        select(Hide)
        .where(Hide.visitor_id == visitor_id)
        .order_by(Hide.created_at.desc())
        .offset((safe_page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    ad_ids = [row.ad_id for row in rows]
    if not ad_ids:
        return HideListOut(items=[])
    order = {ad_id: index for index, ad_id in enumerate(ad_ids)}
    ads = db.execute(select(Ad).where(Ad.id.in_(ad_ids))).unique().scalars().all()
    ads = sorted(ads, key=lambda item: order.get(item.id, 999))
    favorites = set(_favorite_ids(db, visitor_id))
    cards = [
        hydrate_card(ad, favorite_ids=favorites, hide_ids=set(ad_ids), expired=not is_visible(ad))
        for ad in ads
    ]
    return HideListOut(items=cards)


@router.post("/api/visitor/hides", response_model=FavoriteToggleOut)
def add_hide(
    payload: HideIn,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> FavoriteToggleOut:
    """隐藏（幂等；上限 500）。"""
    _ensure_visitor(db, visitor_id)
    ad = db.get(Ad, payload.ad_id)
    if ad is None:
        raise api_error(404, "AD_NOT_FOUND", "该广告不存在或已被删除")

    existing = db.execute(
        select(Hide).where(Hide.visitor_id == visitor_id, Hide.ad_id == payload.ad_id)
    ).scalars().first()
    count = db.execute(
        select(func.count()).select_from(Hide).where(Hide.visitor_id == visitor_id)
    ).scalar_one()
    if existing is not None:
        db.commit()
        return FavoriteToggleOut(count=int(count), limit=HIDES_LIMIT, message=HIDE_MESSAGE)

    if count >= HIDES_LIMIT:
        raise api_error(409, "LIMIT_REACHED", f"隐藏已达上限 {HIDES_LIMIT} 条，请先在偏好页恢复部分广告")

    db.add(Hide(visitor_id=visitor_id, ad_id=payload.ad_id, created_at=now_utc()))
    EventService.insert_single(
        db, visitor_id=visitor_id, event_type="hide", ad_id=payload.ad_id, page="list"
    )
    db.commit()
    return FavoriteToggleOut(count=int(count) + 1, limit=HIDES_LIMIT, message=HIDE_MESSAGE)


@router.delete("/api/visitor/hides/{ad_id}", response_model=FavoriteToggleOut)
def remove_hide(
    ad_id: int,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> FavoriteToggleOut:
    """恢复显示。"""
    hide = db.execute(
        select(Hide).where(Hide.visitor_id == visitor_id, Hide.ad_id == ad_id)
    ).scalars().first()
    if hide is not None:
        db.delete(hide)
        db.commit()
    count = db.execute(
        select(func.count()).select_from(Hide).where(Hide.visitor_id == visitor_id)
    ).scalar_one()
    return FavoriteToggleOut(count=int(count), limit=HIDES_LIMIT, message="已恢复显示")


@router.get("/api/visitor/preferences", response_model=PreferenceOut)
def get_preferences(
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> PreferenceOut:
    """读取偏好。"""
    preference = db.get(Preference, visitor_id)
    if preference is None:
        return PreferenceOut(categories=[], city=None)
    try:
        parsed = json.loads(preference.categories or "[]")
        categories = [int(item) for item in parsed] if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError, ValueError):
        categories = []
    return PreferenceOut(categories=categories, city=preference.city)


@router.put("/api/visitor/preferences", response_model=PreferenceSaveOut)
def save_preferences(
    payload: PreferenceIn,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> PreferenceSaveOut:
    """保存偏好；全部不选 = 关闭个性化过滤。"""
    _ensure_visitor(db, visitor_id)
    category_ids = [int(item) for item in payload.categories]
    if category_ids:
        valid = set(
            db.execute(select(Category.id).where(Category.id.in_(category_ids))).scalars().all()
        )
        if len(valid) != len(set(category_ids)):
            raise api_error(422, "CATEGORY_NOT_FOUND", "选择的类别不存在")
    city = payload.city
    if city and city not in CITIES:
        raise api_error(422, "CITY_INVALID", "请选择列表中的城市")

    preference = db.get(Preference, visitor_id)
    if preference is None:
        preference = Preference(visitor_id=visitor_id, categories="[]", city=None, updated_at=now_utc())
        db.add(preference)
    preference.categories = json.dumps(sorted(set(category_ids)))
    preference.city = city
    preference.updated_at = now_utc()
    db.commit()
    return PreferenceSaveOut(categories=sorted(set(category_ids)), city=city)


@router.delete("/api/visitor/data", response_model=VisitorDataDeletedOut)
def delete_visitor_data(
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> VisitorDataDeletedOut:
    """一次清空本设备的收藏、隐藏与偏好。"""
    favorites = db.query(Favorite).filter(Favorite.visitor_id == visitor_id).delete(synchronize_session=False)
    hides = db.query(Hide).filter(Hide.visitor_id == visitor_id).delete(synchronize_session=False)
    preferences = db.query(Preference).filter(Preference.visitor_id == visitor_id).delete(synchronize_session=False)
    db.commit()
    return VisitorDataDeletedOut(
        deleted={
            "favorites": int(favorites or 0),
            "hides": int(hides or 0),
            "preferences": int(preferences or 0),
        }
    )
