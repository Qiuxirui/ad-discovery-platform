"""可见性唯一权威实现（PRD 6.2 / 架构 §3.4）。

任何用户端查询都必须经过 :func:`visible_ads_stmt` 或 :func:`is_visible`，
禁止在其它模块手写 ``status`` + 有效期条件。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from ..constants import (
    AD_STATUS_ACTIVE,
    AD_STATUS_LABELS,
    MAX_PAGE_SIZE,
    PAGE_SIZE,
    SORT_LABELS,
)
from ..models import Ad, AdTag, Category, Favorite, Hide, Merchant, Tag
from ..schemas.ad import AdCardOut, AdDetailOut, MerchantBrief
from ..schemas.category import TagOut
from ..utils.timeutil import (
    cst_date_str,
    days_left,
    is_expiring_soon,
    now_utc,
    utc_to_iso_z,
)

__all__ = [
    "apply_filters",
    "apply_sort",
    "build_detail",
    "card_from_ad",
    "count_stmt",
    "get_related_ads",
    "get_visible_ad",
    "hydrate_card",
    "hydrate_cards",
    "is_visible",
    "merchant_brief",
    "page_size_or_default",
    "status_label",
    "visible_ads_stmt",
]


def visible_ads_stmt(now: datetime | None = None) -> Select:
    """唯一权威可见性条件：``status='active' AND valid_from<=now<valid_to``。"""
    current = now or now_utc()
    return select(Ad).where(
        Ad.status == AD_STATUS_ACTIVE,
        Ad.valid_from <= current,
        Ad.valid_to > current,
    )


def is_visible(ad: Ad | None, now: datetime | None = None) -> bool:
    """单条广告可见性判定（与 SQL 条件等价）。"""
    if ad is None:
        return False
    current = now or now_utc()
    return ad.status == AD_STATUS_ACTIVE and ad.valid_from <= current < ad.valid_to


def apply_filters(
    stmt: Select,
    *,
    q: str | None = None,
    category_slug: str | None = None,
    tag_slug: str | None = None,
    city: str | None = None,
    ending: bool = False,
    promo: bool = False,
    exclude_ad_ids: list[int] | None = None,
    merchant_id: int | None = None,
    now: datetime | None = None,
) -> Select:
    """按 PRD 7.2 的筛选维度叠加条件（维度之间 AND）。"""
    current = now or now_utc()

    if merchant_id is not None:
        stmt = stmt.where(Ad.merchant_id == merchant_id)

    if category_slug:
        stmt = stmt.where(
            Ad.category_id.in_(select(Category.id).where(Category.slug == category_slug))
        )

    if tag_slug:
        stmt = stmt.where(
            Ad.id.in_(
                select(AdTag.ad_id).join(Tag, Tag.id == AdTag.tag_id).where(Tag.slug == tag_slug)
            )
        )

    if city:
        stmt = stmt.where(or_(Ad.city == city, Ad.city == "全国"))

    if ending:
        stmt = stmt.where(Ad.valid_to <= current + timedelta(hours=48))

    if promo:
        stmt = stmt.where(
            or_(
                func.coalesce(func.trim(Ad.price_text), "") != "",
                func.coalesce(func.trim(Ad.promo_condition), "") != "",
            )
        )

    if exclude_ad_ids:
        stmt = stmt.where(Ad.id.notin_(exclude_ad_ids))

    keyword = (q or "").strip()
    if keyword:
        like = f"%{keyword.lower()}%"
        tag_hit = (
            select(AdTag.ad_id)
            .join(Tag, Tag.id == AdTag.tag_id)
            .where(func.lower(Tag.name).like(like))
        )
        stmt = stmt.where(
            or_(
                func.lower(Ad.title).like(like),
                func.lower(Ad.description).like(like),
                Ad.id.in_(tag_hit),
            )
        )

    return stmt


def apply_sort(stmt: Select, sort: str | None, now: datetime | None = None) -> Select:
    """三种排序，均带唯一键兜底保证翻页稳定（PRD 7.1）。"""
    current = now or now_utc()
    order_key = (sort or "latest").strip()
    if order_key not in SORT_LABELS:
        order_key = "latest"

    published = func.coalesce(Ad.published_at, Ad.created_at)

    if order_key == "ending":
        return stmt.order_by(Ad.valid_to.asc(), Ad.id.desc())

    if order_key == "popular":
        cutoff = current - timedelta(days=30)
        popular = (
            select(Favorite.ad_id.label("ad_id"), func.count(Favorite.id).label("fav_count"))
            .where(Favorite.created_at >= cutoff)
            .group_by(Favorite.ad_id)
            .subquery()
        )
        return (
            stmt.outerjoin(popular, popular.c.ad_id == Ad.id)
            .order_by(func.coalesce(popular.c.fav_count, 0).desc(), published.desc(), Ad.id.desc())
        )

    return stmt.order_by(published.desc(), Ad.id.desc())


def count_stmt(stmt: Select) -> Select:
    """把查询包成 ``count(*)`` 语句（保留 where 条件）。"""
    return select(func.count()).select_from(stmt.order_by(None).subquery())


def get_visible_ad(db: Session, ad_id: int, now: datetime | None = None) -> Ad | None:
    """按 id 取可见广告；不可见返回 ``None``。"""
    current = now or now_utc()
    return db.execute(visible_ads_stmt(current).where(Ad.id == ad_id)).unique().scalar_one_or_none()


def _tag_outs(ad: Ad) -> list[TagOut]:
    items = sorted(ad.tags, key=lambda tag: (tag.sort_order, tag.id))
    return [TagOut(id=tag.id, name=tag.name, slug=tag.slug, sort_order=tag.sort_order) for tag in items]


def _merchant_name(ad: Ad) -> str:
    merchant = ad.merchant
    return merchant.name if merchant is not None else "该商家已下线"


def _category_slug(ad: Ad) -> str:
    return ad.category.slug if ad.category is not None else ""


def _category_name(ad: Ad) -> str:
    return ad.category.name if ad.category is not None else ""


def card_from_ad(
    ad: Ad,
    *,
    now: datetime | None = None,
    is_favorited: bool = False,
    is_hidden: bool = False,
    expired: bool | None = None,
) -> AdCardOut:
    """ORM → 卡片模型（时间字段全部服务端预计算）。"""
    current = now or now_utc()
    expired_flag = ad.valid_to <= current if expired is None else expired
    return AdCardOut(
        id=ad.id,
        title=ad.title,
        price_text=ad.price_text,
        promo_condition=ad.promo_condition,
        city=ad.city,
        merchant_id=ad.merchant_id,
        merchant_name=_merchant_name(ad),
        image_path=ad.image_path,
        category_id=ad.category_id,
        category_slug=_category_slug(ad),
        category_name=_category_name(ad),
        tags=_tag_outs(ad),
        valid_from_local_date=cst_date_str(ad.valid_from),
        valid_to_local_date=cst_date_str(ad.valid_to),
        days_left=days_left(ad.valid_to, current),
        expiring_soon=is_expiring_soon(ad.valid_to, current),
        is_favorited=is_favorited,
        is_hidden=is_hidden,
        published_at=utc_to_iso_z(ad.published_at),
        status=ad.status,
        is_expired=expired_flag,
    )


def _visitor_sets(db: Session, visitor_id: str | None) -> tuple[set[int], set[int]]:
    if not visitor_id:
        return set(), set()
    favorite_ids = set(
        db.execute(select(Favorite.ad_id).where(Favorite.visitor_id == visitor_id)).scalars().all()
    )
    hide_ids = set(
        db.execute(select(Hide.ad_id).where(Hide.visitor_id == visitor_id)).scalars().all()
    )
    return favorite_ids, hide_ids


def hydrate_card(
    ad: Ad,
    *,
    now: datetime | None = None,
    favorite_ids: set[int] | None = None,
    hide_ids: set[int] | None = None,
    expired: bool | None = None,
) -> AdCardOut:
    """单条装配（调用方需自行提供收藏/隐藏集合以避免 N+1）。"""
    favorites = favorite_ids or set()
    hides = hide_ids or set()
    return card_from_ad(
        ad,
        now=now,
        is_favorited=ad.id in favorites,
        is_hidden=ad.id in hides,
        expired=expired,
    )


def hydrate_cards(db: Session, ads: list[Ad], visitor_id: str | None = None) -> list[AdCardOut]:
    """批量装配：一次查收藏/隐藏集合，避免逐条查询。"""
    current = now_utc()
    favorites, hides = _visitor_sets(db, visitor_id)
    return [hydrate_card(ad, now=current, favorite_ids=favorites, hide_ids=hides) for ad in ads]


def merchant_brief(db: Session, ad: Ad) -> MerchantBrief:
    """详情页商家信息块。"""
    merchant: Merchant | None = ad.merchant
    if merchant is None:
        return MerchantBrief(id=ad.merchant_id, name="该商家已下线", city=ad.city)
    main_category_name = merchant.category.name if merchant.category is not None else None
    active_count = len(
        db.execute(
            visible_ads_stmt().with_only_columns(Ad.id).where(Ad.merchant_id == merchant.id)
        )
        .scalars()
        .all()
    )
    return MerchantBrief(
        id=merchant.id,
        name=merchant.name,
        city=merchant.city,
        main_category_name=main_category_name,
        joined_at=cst_date_str(merchant.created_at),
        active_ad_count=active_count,
    )


def get_related_ads(
    db: Session,
    ad: Ad,
    *,
    visitor_id: str | None = None,
    limit: int = 3,
) -> list[AdCardOut]:
    """同类 3 条：同类别 + 同城市优先，不足时补同类别，排除自身与已隐藏。"""
    favorites, hides = _visitor_sets(db, visitor_id)
    base = visible_ads_stmt().where(Ad.id != ad.id, Ad.category_id == ad.category_id)
    if hides:
        base = base.where(Ad.id.notin_(list(hides)))

    same_city = db.execute(
        apply_sort(base.where(Ad.city == ad.city), "latest").limit(limit)
    ).unique().scalars().all()
    picked = list(same_city)
    if len(picked) < limit:
        picked_ids = [item.id for item in picked] or [0]
        extra = db.execute(
            apply_sort(base.where(Ad.id.notin_(picked_ids)), "latest").limit(limit - len(picked))
        ).unique().scalars().all()
        picked.extend(extra)

    return [
        hydrate_card(item, favorite_ids=favorites, hide_ids=hides)
        for item in picked[:limit]
    ]


def build_detail(
    db: Session,
    ad: Ad,
    *,
    visitor_id: str | None = None,
    now: datetime | None = None,
) -> AdDetailOut:
    """详情页完整响应（卡片字段 + 商家块 + 同类推荐）。"""
    current = now or now_utc()
    favorites, hides = _visitor_sets(db, visitor_id)
    card = hydrate_card(ad, now=current, favorite_ids=favorites, hide_ids=hides)
    related = get_related_ads(db, ad, visitor_id=visitor_id, limit=3)
    return AdDetailOut(
        **card.model_dump(),
        description=ad.description,
        restriction=ad.restriction,
        valid_from=utc_to_iso_z(ad.valid_from),
        valid_to=utc_to_iso_z(ad.valid_to),
        landing_domain=ad.landing_domain,
        merchant=merchant_brief(db, ad),
        related=related,
    )


def page_size_or_default(value: int | None) -> int:
    """分页大小归一（默认 24，上限 60）。"""
    if not value or value < 1:
        return PAGE_SIZE
    return min(value, MAX_PAGE_SIZE)


def status_label(status: str) -> str:
    """广告状态中文标签。"""
    return AD_STATUS_LABELS.get(status, status)
