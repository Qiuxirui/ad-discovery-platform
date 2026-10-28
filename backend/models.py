"""14 张表的 ORM 定义（唯一模型文件，避免循环导入）。

字段与索引严格按 ``docs/ARCHITECTURE.md`` §4.2；状态一律 ``str`` + 常量比较，
不使用 ``sqlalchemy.Enum``（SQLite 下变更与报错都不友好）。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from .constants import (
    AD_STATUS_ACTIVE,
    AD_STATUS_EXPIRED,
    AD_STATUS_SCHEDULED,
    REPORT_STATUS_USER_TEXT,
)
from .database import Base
from .utils.timeutil import now_utc

if TYPE_CHECKING:  # pragma: no cover
    pass


def _now() -> datetime:
    return now_utc()


class Merchant(Base):
    """商家账号 + 资料 + 状态。"""

    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    contact_name: Mapped[str] = mapped_column(String(30), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(20), nullable=False)
    main_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", index=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    admin_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now, onupdate=_now)

    category: Mapped["Category | None"] = relationship("Category", lazy="joined")

    def is_disabled(self) -> bool:
        """商家是否已被停用。"""
        return self.status == "disabled"

    def active_ad_count(self, db: Session) -> int:
        """当前在架广告数（可见性口径）。"""
        from .services.visibility import visible_ads_stmt

        stmt = visible_ads_stmt().where(Ad.merchant_id == self.id).with_only_columns(Ad.id)
        return len(db.execute(stmt).scalars().all())


class AdminUser(Base):
    """管理员账号 + 登录锁定。"""

    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(40), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)

    def is_locked(self, now: datetime | None = None) -> bool:
        """是否处于登录锁定期。"""
        if self.locked_until is None:
            return False
        return self.locked_until > (now or now_utc())


class Category(Base):
    """一级类别（固定 6 条）。"""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    intro: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)

    tags: Mapped[list["Tag"]] = relationship("Tag", back_populates="category", lazy="selectin")


class Tag(Base):
    """二级标签（管理员可维护）。"""

    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("category_id", "name", name="uq_tags_category_name"),
        UniqueConstraint("category_id", "slug", name="uq_tags_category_slug"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    slug: Mapped[str] = mapped_column(String(40), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)

    category: Mapped["Category"] = relationship("Category", back_populates="tags")


class Ad(Base):
    """广告主表（图片字段并入本表）。"""

    __tablename__ = "ads"
    __table_args__ = (
        Index("ix_ads_status_valid_to", "status", "valid_to"),
        Index("ix_ads_pub_id", "status", "published_at", "id"),
        Index("ix_ads_cat_status", "category_id", "status"),
        Index("ix_ads_merchant_status", "merchant_id", "status"),
        Index("ix_ads_city", "city"),
        Index("ix_ads_landing_domain", "landing_domain"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(20), nullable=False)
    price_text: Mapped[str | None] = mapped_column(String(30), nullable=True)
    promo_condition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    restriction: Mapped[str | None] = mapped_column(String(200), nullable=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_to: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    landing_url: Mapped[str] = mapped_column(String(500), nullable=False)
    landing_domain: Mapped[str] = mapped_column(String(120), nullable=False)
    image_path: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", index=True)
    reject_reason_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    offline_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    precheck_note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now, onupdate=_now)

    merchant: Mapped["Merchant"] = relationship("Merchant", lazy="joined")
    category: Mapped["Category"] = relationship("Category", lazy="joined")
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary="ad_tags", lazy="selectin", viewonly=True)

    #: 核心字段（改动后从 ``active`` 回 ``pending``，PRD 迁移 11）
    CORE_FIELDS: tuple[str, ...] = (
        "title",
        "category_id",
        "price_text",
        "promo_condition",
        "valid_from",
        "valid_to",
        "landing_url",
        "image_path",
    )

    def visible(self, now: datetime | None = None) -> bool:
        """唯一可见性判据（PRD 6.2）：状态 + 有效期双条件。"""
        current = now or now_utc()
        return self.status == AD_STATUS_ACTIVE and self.valid_from <= current < self.valid_to

    def is_core_field_changed(self, old: dict[str, object]) -> bool:
        """与旧值比较，判断是否改动了需要重审的核心字段。"""
        for field in self.CORE_FIELDS:
            if field not in old:
                continue
            if getattr(self, field) != old[field]:
                return True
        return False

    def is_expired_now(self, now: datetime | None = None) -> bool:
        """是否已过有效期（供定时任务使用）。"""
        current = now or now_utc()
        return self.valid_to <= current

    def should_activate(self, now: datetime | None = None) -> bool:
        """``scheduled`` 且已进入有效期窗口。"""
        current = now or now_utc()
        return self.status == AD_STATUS_SCHEDULED and self.valid_from <= current < self.valid_to

    def should_expire(self, now: datetime | None = None) -> bool:
        """``active``/``scheduled`` 且已过期。"""
        current = now or now_utc()
        return self.status in (AD_STATUS_ACTIVE, AD_STATUS_SCHEDULED) and self.valid_to <= current

    def is_expired_record(self) -> bool:
        """状态层面已过期（用于收藏页"已结束"分组）。"""
        return self.status in (AD_STATUS_EXPIRED, AD_STATUS_OFFLINE)


class AdTag(Base):
    """广告 ↔ 标签 多对多。"""

    __tablename__ = "ad_tags"

    ad_id: Mapped[int] = mapped_column(
        ForeignKey("ads.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class Review(Base):
    """广告状态变更 / 审核留痕（只增不改不删）。"""

    __tablename__ = "reviews"
    __table_args__ = (Index("ix_reviews_ad_created", "ad_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ad_id: Mapped[int] = mapped_column(
        ForeignKey("ads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    changes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now, index=True)


class Visitor(Base):
    """匿名访客（仅 id / 首末访问）。"""

    __tablename__ = "visitors"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now, index=True)


class Favorite(Base):
    """收藏（单设备上限 200）。"""

    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("visitor_id", "ad_id", name="uq_favorites_visitor_ad"),
        Index("ix_favorites_ad_created", "ad_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visitor_id: Mapped[str] = mapped_column(
        ForeignKey("visitors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ad_id: Mapped[int] = mapped_column(
        ForeignKey("ads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)


class Hide(Base):
    """隐藏（单设备上限 500）。"""

    __tablename__ = "hides"
    __table_args__ = (UniqueConstraint("visitor_id", "ad_id", name="uq_hides_visitor_ad"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visitor_id: Mapped[str] = mapped_column(
        ForeignKey("visitors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ad_id: Mapped[int] = mapped_column(
        ForeignKey("ads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)


class Preference(Base):
    """偏好（每访客 1 行）。"""

    __tablename__ = "preferences"

    visitor_id: Mapped[str] = mapped_column(
        ForeignKey("visitors.id", ondelete="CASCADE"), primary_key=True
    )
    categories: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    city: Mapped[str | None] = mapped_column(String(20), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now, onupdate=_now)


class Report(Base):
    """举报单。"""

    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_status_created", "status", "created_at"),
        Index("ix_reports_ad_created", "ad_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(11), nullable=False, unique=True)
    ad_id: Mapped[int] = mapped_column(
        ForeignKey("ads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    visitor_id: Mapped[str] = mapped_column(
        ForeignKey("visitors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason_code: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    admin_note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    ad_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    handled_by: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now, onupdate=_now)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    ad: Mapped["Ad"] = relationship("Ad", lazy="joined")

    def to_user_text(self) -> str:
        """用户侧状态文案（PRD 6.6）。"""
        return REPORT_STATUS_USER_TEXT.get(self.status, "")


class ReportFollowup(Base):
    """举报"仍有疑问"追加（终态 7 天窗口内可提交）。"""

    __tablename__ = "report_followups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    visitor_id: Mapped[str] = mapped_column(
        ForeignKey("visitors.id", ondelete="CASCADE"), nullable=False
    )
    note: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)


class Event(Base):
    """事件流水（不可变；不设 FK 到 ads）。"""

    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_ad_type_ts", "ad_id", "event_type", "ts"),
        Index("ix_events_visitor_ad_ts", "visitor_id", "ad_id", "ts"),
        Index("ix_events_type_ts", "event_type", "ts"),
        Index("ix_events_session_ad", "session_id", "ad_id", "event_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    ad_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    visitor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)
    page: Mapped[str] = mapped_column(String(16), nullable=False)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meta: Mapped[str | None] = mapped_column(Text, nullable=True)
