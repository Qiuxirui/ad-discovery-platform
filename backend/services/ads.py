"""广告领域服务：预检、CRUD、状态机迁移、审核留痕、图片落盘。

约定：
- :meth:`AdService.log_review` 是**唯一**写 ``reviews`` 表的入口（含定时任务；
  定时任务直接调用模块级 :func:`log_review`，同一个实现）；
- 状态迁移严格按 PRD 6.1 的 14 条迁移，禁止 ``draft→active`` 之类的跳变。
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..constants import (
    AD_STATUS_ACTIVE,
    AD_STATUS_DRAFT,
    AD_STATUS_EXPIRED,
    AD_STATUS_LABELS,
    AD_STATUS_OFFLINE,
    AD_STATUS_PENDING,
    AD_STATUS_REJECTED,
    AD_STATUS_SCHEDULED,
    ALLOWED_IMAGE_EXTS,
    DAILY_NEW_ADS_LIMIT,
    MAX_IMAGE_BYTES,
    ONLINE_ADS_LIMIT,
    TAG_MAX,
    TAG_MIN,
    UPLOAD_URL_PREFIX,
    VALID_DAYS_LIMIT,
)
from ..database import UPLOADS_DIR
from ..models import Ad, AdTag, Category, Merchant, Review, Tag
from ..schemas.ad import AdCreateIn, AdManageOut, AdUpdateIn
from ..schemas.category import TagOut
from ..utils.cover import write_cover_file
from ..utils.timeutil import (
    cst_date_str,
    days_left,
    is_expiring_soon,
    now_utc,
    parse_cst_date_end,
    parse_cst_date_start,
    today_cst_range_utc,
    utc_to_iso_z,
)
from ..utils.urlsafety import check_url_safety, normalize_url, scan_banned_words

__all__ = [
    "AdService",
    "PrecheckResult",
    "api_error",
    "create_ad_tag_links",
    "log_review",
    "store_upload",
    "to_manage_out",
]

audit_log = logging.getLogger("adx.audit")


class ApiError(Exception):
    """业务异常：由 ``main.py`` 的异常处理器转成 ``{detail, code}`` JSON。"""

    def __init__(self, status_code: int, code: str, detail: str, fields: list[dict[str, str]] | None = None) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.fields = fields or []


def api_error(status_code: int, code: str, detail: str, fields: list[dict[str, str]] | None = None) -> ApiError:
    """构造业务异常。"""
    return ApiError(status_code, code, detail, fields)


@dataclass(slots=True)
class PrecheckResult:
    """系统预检结论。"""

    passed: bool = True
    code: str = ""
    reason: str = ""
    banned_words: list[str] = field(default_factory=list)
    url_safe: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "code": self.code,
            "reason": self.reason,
            "banned_words": self.banned_words,
            "url_safe": self.url_safe,
        }


# ------------------------------------------------------------------ 审核留痕
def log_review(
    db: Session,
    ad: Ad,
    action: str,
    actor_type: str,
    actor_id: int | None = None,
    reason: str | None = None,
    changes: dict[str, object] | None = None,
) -> Review:
    """写入状态变更留痕（全项目唯一入口）。"""
    review = Review(
        ad_id=ad.id,
        action=action,
        actor_type=actor_type,
        actor_id=actor_id,
        reason=reason,
        changes=json.dumps(changes, ensure_ascii=False) if changes else None,
        created_at=now_utc(),
    )
    db.add(review)
    return review


def create_ad_tag_links(db: Session, ad: Ad, tag_ids: list[int]) -> None:
    """重建广告的标签关联（先删后插）。"""
    db.query(AdTag).filter(AdTag.ad_id == ad.id).delete(synchronize_session=False)
    for tag_id in tag_ids:
        db.add(AdTag(ad_id=ad.id, tag_id=tag_id))
    db.flush()
    db.refresh(ad)


def to_manage_out(ad: Ad, *, now=None) -> AdManageOut:
    """商家端/后台广告视图。"""
    current = now or now_utc()
    tags = sorted(ad.tags, key=lambda item: (item.sort_order, item.id))
    return AdManageOut(
        id=ad.id,
        title=ad.title,
        description=ad.description,
        category_id=ad.category_id,
        category_slug=ad.category.slug if ad.category is not None else "",
        category_name=ad.category.name if ad.category is not None else "",
        tags=[TagOut(id=tag.id, name=tag.name, slug=tag.slug, sort_order=tag.sort_order) for tag in tags],
        tag_ids=[tag.id for tag in tags],
        city=ad.city,
        price_text=ad.price_text,
        promo_condition=ad.promo_condition,
        restriction=ad.restriction,
        valid_from=utc_to_iso_z(ad.valid_from),
        valid_to=utc_to_iso_z(ad.valid_to),
        valid_from_local_date=cst_date_str(ad.valid_from),
        valid_to_local_date=cst_date_str(ad.valid_to),
        days_left=days_left(ad.valid_to, current),
        expiring_soon=is_expiring_soon(ad.valid_to, current),
        landing_url=ad.landing_url,
        landing_domain=ad.landing_domain,
        image_path=ad.image_path,
        status=ad.status,
        status_label=AD_STATUS_LABELS.get(ad.status, ad.status),
        submitted_at=utc_to_iso_z(ad.submitted_at),
        published_at=utc_to_iso_z(ad.published_at),
        created_at=utc_to_iso_z(ad.created_at),
        updated_at=utc_to_iso_z(ad.updated_at),
        reject_reason_code=ad.reject_reason_code,
        reject_reason=ad.reject_reason,
        offline_reason=ad.offline_reason,
        precheck_note=ad.precheck_note,
    )


# ------------------------------------------------------------------ 上传
_MAGIC_PREFIXES: dict[str, tuple[bytes, ...]] = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".webp": (b"RIFF",),
}


def _matches_magic(ext: str, data: bytes) -> bool:
    prefixes = _MAGIC_PREFIXES.get(ext, ())
    if not prefixes:
        return False
    if ext == ".webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return any(data.startswith(prefix) for prefix in prefixes)


def store_upload(filename: str, content_type: str | None, data: bytes) -> str:
    """校验并落盘上传图片，返回 Web 路径。"""
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise api_error(422, "UPLOAD_REJECTED", "只支持 jpg / png / webp 格式的图片")
    if not data:
        raise api_error(422, "UPLOAD_REJECTED", "图片内容为空")
    if len(data) > MAX_IMAGE_BYTES:
        raise api_error(422, "UPLOAD_REJECTED", "图片不能超过 2MB")
    if not _matches_magic(ext, data):
        raise api_error(422, "UPLOAD_REJECTED", "图片内容与扩展名不一致，请重新上传")

    expected_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    if content_type and content_type.split(";")[0].strip().lower() != expected_types[ext]:
        raise api_error(422, "UPLOAD_REJECTED", "图片类型与扩展名不匹配，请重新上传")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOADS_DIR / f"{uuid.uuid4().hex}{ext}"
    target.write_bytes(data)
    return f"{UPLOAD_URL_PREFIX}/{target.name}"


# ------------------------------------------------------------------ 服务
class AdService:
    """广告领域服务。"""

    # -------------------------------------------------------------- 预检
    @staticmethod
    def precheck(payload: AdCreateIn | AdUpdateIn, *, category: Category | None = None) -> PrecheckResult:
        """标题/描述长度、有效期、禁投词、URL 安全的全套预检。"""
        result = PrecheckResult()
        title = (getattr(payload, "title", None) or "").strip()
        description = (getattr(payload, "description", None) or "").strip()

        if title and len(title) > 40:
            return PrecheckResult(passed=False, code="TITLE_TOO_LONG", reason="标题不能超过 40 字")
        if description and len(description) > 500:
            return PrecheckResult(passed=False, code="DESC_TOO_LONG", reason="描述不能超过 500 字")

        hits = scan_banned_words(("title", title), ("description", description))
        if hits:
            words = sorted({hit.word for hit in hits})
            result.passed = False
            result.code = "BANNED_INDUSTRY"
            result.banned_words = words
            result.reason = (
                "内容命中禁投行业关键词：" + "、".join(words) + "。平台不接入医疗、金融、博彩、酒类、成人、政治类广告。"
            )
            return result

        valid_from_raw = getattr(payload, "valid_from", None)
        valid_to_raw = getattr(payload, "valid_to", None)
        if valid_from_raw and valid_to_raw:
            try:
                valid_from = parse_cst_date_start(valid_from_raw)
                valid_to = parse_cst_date_end(valid_to_raw)
            except ValueError:
                return PrecheckResult(passed=False, code="DATE_INVALID", reason="有效期日期格式应为 YYYY-MM-DD")
            if valid_to <= valid_from:
                return PrecheckResult(passed=False, code="DATE_REVERSED", reason="有效期结束日必须晚于开始日")
            inclusive_days = (valid_to - valid_from).days + 1
            if inclusive_days > VALID_DAYS_LIMIT:
                return PrecheckResult(
                    passed=False,
                    code="DATE_TOO_LONG",
                    reason=f"单条广告有效期不能超过 {VALID_DAYS_LIMIT} 天",
                )
            current = now_utc()
            if valid_from < current - timedelta(hours=24):
                return PrecheckResult(
                    passed=False,
                    code="DATE_TOO_EARLY",
                    reason="有效期开始日不能早于今天（最多允许比当前时间早 24 小时）",
                )
            if valid_to <= current:
                return PrecheckResult(
                    passed=False,
                    code="DATE_EXPIRED",
                    reason="有效期结束日必须晚于当前时间",
                )

        landing_url = (getattr(payload, "landing_url", None) or "").strip()
        if landing_url:
            safety = check_url_safety(landing_url)
            if not safety.ok:
                result.passed = False
                result.url_safe = False
                result.code = safety.code
                result.reason = safety.reason
                return result

        if category is not None and not category.is_active:
            return PrecheckResult(passed=False, code="CATEGORY_INACTIVE", reason="该类别已停止收录")

        return result

    # -------------------------------------------------------------- 标签校验
    @staticmethod
    def resolve_tags(
        db: Session,
        category_id: int,
        tag_ids: list[int] | None,
        *,
        require: bool,
    ) -> list[Tag]:
        """校验标签：必须存在、属于同一级类别、数量 1–3（草稿可 0）。"""
        ids = [int(item) for item in (tag_ids or []) if item is not None]
        if not ids:
            if require:
                raise api_error(422, "TAG_REQUIRED", "请至少选择 1 个二级标签", [
                    {"field": "tag_ids", "message": "请至少选择 1 个二级标签"}
                ])
            return []
        if len(ids) > TAG_MAX:
            raise api_error(422, "TAG_TOO_MANY", f"二级标签最多选 {TAG_MAX} 个", [
                {"field": "tag_ids", "message": f"二级标签最多选 {TAG_MAX} 个"}
            ])
        tags = db.execute(select(Tag).where(Tag.id.in_(ids))).scalars().all()
        if len(tags) != len(ids):
            raise api_error(422, "TAG_NOT_FOUND", "选择的标签不存在，请刷新页面重试", [
                {"field": "tag_ids", "message": "选择的标签不存在"}
            ])
        for tag in tags:
            if tag.category_id != category_id:
                raise api_error(422, "TAG_CROSS_CATEGORY", "二级标签必须属于所选的一级类别", [
                    {"field": "tag_ids", "message": "二级标签必须属于所选的一级类别"}
                ])
            if not tag.is_active:
                raise api_error(422, "TAG_INACTIVE", "该标签已停用，请重新选择", [
                    {"field": "tag_ids", "message": "该标签已停用"}
                ])
        order = {tag_id: index for index, tag_id in enumerate(ids)}
        return sorted(tags, key=lambda item: order.get(item.id, 0))

    # -------------------------------------------------------------- 频控
    @staticmethod
    def check_quota(db: Session, merchant: Merchant, *, submitting: bool) -> None:
        """单商家每日新建 ≤5 条、同时在线（active+scheduled）≤20 条。"""
        start, end = today_cst_range_utc()
        created_today = db.execute(
            select(func.count())
            .select_from(Ad)
            .where(Ad.merchant_id == merchant.id, Ad.created_at >= start, Ad.created_at < end)
        ).scalar_one()
        if created_today >= DAILY_NEW_ADS_LIMIT:
            raise api_error(
                429,
                "DAILY_QUOTA_EXCEEDED",
                f"今日新建广告已达 {DAILY_NEW_ADS_LIMIT} 条上限，请明日再提交（次日 00:00 恢复）",
            )
        if submitting:
            online = db.execute(
                select(func.count())
                .select_from(Ad)
                .where(
                    Ad.merchant_id == merchant.id,
                    Ad.status.in_([AD_STATUS_ACTIVE, AD_STATUS_SCHEDULED]),
                )
            ).scalar_one()
            if online >= ONLINE_ADS_LIMIT:
                raise api_error(
                    429,
                    "ONLINE_QUOTA_EXCEEDED",
                    f"同时在线广告已达 {ONLINE_ADS_LIMIT} 条上限，请先下架或等待过期后再提交",
                )

    # -------------------------------------------------------------- 创建
    @staticmethod
    def create(db: Session, merchant: Merchant, payload: AdCreateIn) -> tuple[Ad, PrecheckResult]:
        """新建广告（草稿或直接提交审核）。"""
        AdService.check_quota(db, merchant, submitting=payload.submit)

        category = db.get(Category, payload.category_id)
        if category is None:
            raise api_error(422, "CATEGORY_NOT_FOUND", "所选一级类别不存在")

        tags = AdService.resolve_tags(db, category.id, payload.tag_ids, require=payload.submit)
        if len(tags) < TAG_MIN and payload.submit:
            raise api_error(422, "TAG_REQUIRED", "请至少选择 1 个二级标签")

        valid_from = parse_cst_date_start(payload.valid_from)
        valid_to = parse_cst_date_end(payload.valid_to)
        safety = check_url_safety(payload.landing_url)
        if not safety.ok:
            raise api_error(422, safety.code, safety.reason, [
                {"field": "landing_url", "message": safety.reason}
            ])

        precheck = AdService.precheck(payload, category=category)

        ad = Ad(
            merchant_id=merchant.id,
            category_id=category.id,
            title=payload.title.strip(),
            description=payload.description.strip(),
            city=payload.city,
            price_text=payload.price_text,
            promo_condition=payload.promo_condition,
            restriction=payload.restriction,
            valid_from=valid_from,
            valid_to=valid_to,
            landing_url=safety.url or normalize_url(payload.landing_url),
            landing_domain=safety.domain,
            image_path=payload.image_path or "",
            status=AD_STATUS_DRAFT,
            created_at=now_utc(),
            updated_at=now_utc(),
        )
        db.add(ad)
        db.flush()

        if not ad.image_path:
            ad.image_path = write_cover_file(ad.id, ad.title, category.slug)

        create_ad_tag_links(db, ad, [tag.id for tag in tags])

        if payload.submit:
            if precheck.passed:
                ad.status = AD_STATUS_PENDING
                ad.submitted_at = now_utc()
                ad.precheck_note = "预检通过"
                ad.reject_reason = None
                ad.reject_reason_code = None
                log_review(db, ad, "submit", "merchant", merchant.id)
            else:
                ad.status = AD_STATUS_REJECTED
                ad.submitted_at = now_utc()
                ad.precheck_note = precheck.reason
                ad.reject_reason_code = "banned_industry" if precheck.code == "BANNED_INDUSTRY" else "other"
                ad.reject_reason = precheck.reason
                log_review(db, ad, "reject", "system", None, reason=precheck.reason)

        db.commit()
        db.refresh(ad)
        audit_log.info(
            "ad_create ad_id=%s merchant_id=%s status=%s", ad.id, merchant.id, ad.status
        )
        return ad, precheck

    # -------------------------------------------------------------- 编辑
    @staticmethod
    def update(db: Session, ad: Ad, payload: AdUpdateIn, *, actor_type: str, actor_id: int | None) -> tuple[Ad, bool]:
        """编辑广告；``active`` 改核心字段 → 回到 ``pending`` 并立即下线。"""
        if ad.status in (AD_STATUS_EXPIRED,):
            raise api_error(409, "AD_NOT_EDITABLE", "该广告已过期，请复制为新广告后重新提交")
        if ad.status == AD_STATUS_PENDING and actor_type == "merchant":
            raise api_error(409, "AD_NOT_EDITABLE", "广告待审核中，请先撤回为草稿再修改")

        old_values: dict[str, object] = {}
        for field_name in Ad.CORE_FIELDS:
            old_values[field_name] = getattr(ad, field_name)

        data = payload.model_dump(exclude_unset=True)
        tag_ids = data.pop("tag_ids", None)

        if "category_id" in data and data["category_id"] is not None:
            category = db.get(Category, int(data["category_id"]))
            if category is None:
                raise api_error(422, "CATEGORY_NOT_FOUND", "所选一级类别不存在")
            ad.category_id = category.id

        if tag_ids is not None:
            require = ad.status not in (AD_STATUS_DRAFT,)
            tags = AdService.resolve_tags(db, ad.category_id, tag_ids, require=require)
            create_ad_tag_links(db, ad, [tag.id for tag in tags])
        elif ad.category_id != old_values.get("category_id") and ad.status != AD_STATUS_DRAFT:
            existing = [tag.id for tag in ad.tags]
            AdService.resolve_tags(db, ad.category_id, existing, require=True)
            db.query(AdTag).filter(AdTag.ad_id == ad.id).delete(synchronize_session=False)
            db.flush()

        if "valid_from" in data and data["valid_from"]:
            ad.valid_from = parse_cst_date_start(str(data["valid_from"]))
        if "valid_to" in data and data["valid_to"]:
            ad.valid_to = parse_cst_date_end(str(data["valid_to"]))

        if "landing_url" in data and data["landing_url"]:
            safety = check_url_safety(str(data["landing_url"]))
            if not safety.ok:
                raise api_error(422, safety.code, safety.reason, [
                    {"field": "landing_url", "message": safety.reason}
                ])
            ad.landing_url = safety.url
            ad.landing_domain = safety.domain

        for field_name in (
            "title",
            "description",
            "city",
            "price_text",
            "promo_condition",
            "restriction",
            "image_path",
        ):
            if field_name in data:
                value = data[field_name]
                if field_name == "image_path" and not value:
                    continue
                setattr(ad, field_name, value)

        if ad.valid_to <= ad.valid_from:
            raise api_error(422, "DATE_REVERSED", "有效期结束日必须晚于开始日", [
                {"field": "valid_to", "message": "有效期结束日必须晚于开始日"}
            ])
        if (ad.valid_to - ad.valid_from).days + 1 > VALID_DAYS_LIMIT:
            raise api_error(422, "DATE_TOO_LONG", f"单条广告有效期不能超过 {VALID_DAYS_LIMIT} 天", [
                {"field": "valid_to", "message": f"有效期不能超过 {VALID_DAYS_LIMIT} 天"}
            ])

        ad.updated_at = now_utc()
        became_pending = False
        if ad.status == AD_STATUS_ACTIVE:
            changed = ad.is_core_field_changed(old_values)
            changes = _diff_changes(ad, old_values)
            if changed:
                ad.status = AD_STATUS_PENDING
                ad.submitted_at = now_utc()
                ad.published_at = ad.published_at
                became_pending = True
                log_review(
                    db,
                    ad,
                    "merchant_edit",
                    actor_type,
                    actor_id,
                    reason="修改核心字段，需重新审核",
                    changes=changes,
                )
                log_review(db, ad, "submit", actor_type, actor_id, reason="核心字段变更后重新提交")
            else:
                log_review(db, ad, "merchant_edit", actor_type, actor_id, changes=changes)
        else:
            log_review(db, ad, "merchant_edit", actor_type, actor_id)

        db.commit()
        db.refresh(ad)
        return ad, became_pending

    # -------------------------------------------------------------- 状态迁移
    @staticmethod
    def submit(db: Session, ad: Ad) -> tuple[Ad, PrecheckResult]:
        """``draft|rejected`` → ``pending``（重跑完整校验 + 预检）。"""
        if ad.status not in (AD_STATUS_DRAFT, AD_STATUS_REJECTED, AD_STATUS_OFFLINE):
            raise api_error(409, "INVALID_TRANSITION", "当前状态不支持提交审核")

        merchant = db.get(Merchant, ad.merchant_id)
        if merchant is None:
            raise api_error(409, "MERCHANT_MISSING", "商家信息不存在")
        AdService.check_quota(db, merchant, submitting=True)

        tag_ids = [tag.id for tag in ad.tags]
        tags = AdService.resolve_tags(db, ad.category_id, tag_ids, require=True)
        if not tags:
            raise api_error(422, "TAG_REQUIRED", "请至少选择 1 个二级标签")

        payload = AdCreateIn(
            title=ad.title,
            description=ad.description,
            category_id=ad.category_id,
            tag_ids=tag_ids,
            city=ad.city,
            price_text=ad.price_text,
            promo_condition=ad.promo_condition,
            restriction=ad.restriction,
            valid_from=cst_date_str(ad.valid_from) or "",
            valid_to=cst_date_str(ad.valid_to) or "",
            landing_url=ad.landing_url,
            image_path=ad.image_path,
            submit=True,
        )
        precheck = AdService.precheck(payload, category=ad.category)

        ad.submitted_at = now_utc()
        ad.updated_at = now_utc()
        if precheck.passed:
            ad.status = AD_STATUS_PENDING
            ad.precheck_note = "预检通过"
            ad.reject_reason = None
            ad.reject_reason_code = None
            log_review(db, ad, "submit", "merchant", ad.merchant_id)
        else:
            ad.status = AD_STATUS_REJECTED
            ad.precheck_note = precheck.reason
            ad.reject_reason = precheck.reason
            ad.reject_reason_code = "banned_industry" if precheck.code == "BANNED_INDUSTRY" else "other"
            log_review(db, ad, "reject", "system", None, reason=precheck.reason)

        db.commit()
        db.refresh(ad)
        return ad, precheck

    @staticmethod
    def withdraw(db: Session, ad: Ad) -> Ad:
        """``pending`` → ``draft``。"""
        if ad.status != AD_STATUS_PENDING:
            raise api_error(409, "INVALID_TRANSITION", "只有待审核的广告可以撤回")
        ad.status = AD_STATUS_DRAFT
        ad.updated_at = now_utc()
        log_review(db, ad, "withdraw", "merchant", ad.merchant_id)
        db.commit()
        db.refresh(ad)
        return ad

    @staticmethod
    def abandon(db: Session, ad: Ad) -> Ad:
        """``rejected`` → ``draft``。"""
        if ad.status != AD_STATUS_REJECTED:
            raise api_error(409, "INVALID_TRANSITION", "只有已拒绝的广告可以放弃重提")
        ad.status = AD_STATUS_DRAFT
        ad.updated_at = now_utc()
        log_review(db, ad, "abandon", "merchant", ad.merchant_id)
        db.commit()
        db.refresh(ad)
        return ad

    @staticmethod
    def duplicate(db: Session, ad: Ad, merchant: Merchant) -> Ad:
        """复制为新草稿（过期续期/复制用，不复用旧 id）。"""
        AdService.check_quota(db, merchant, submitting=False)
        current = now_utc()
        start = max(ad.valid_from, current)
        span = ad.valid_to - ad.valid_from
        clone = Ad(
            merchant_id=merchant.id,
            category_id=ad.category_id,
            title=ad.title,
            description=ad.description,
            city=ad.city,
            price_text=ad.price_text,
            promo_condition=ad.promo_condition,
            restriction=ad.restriction,
            valid_from=start,
            valid_to=start + span,
            landing_url=ad.landing_url,
            landing_domain=ad.landing_domain,
            image_path="",
            status=AD_STATUS_DRAFT,
            created_at=current,
            updated_at=current,
        )
        db.add(clone)
        db.flush()
        clone.image_path = write_cover_file(clone.id, clone.title, ad.category.slug if ad.category else "")
        create_ad_tag_links(db, clone, [tag.id for tag in ad.tags])
        log_review(db, clone, "duplicate", "merchant", merchant.id, reason=f"复制自广告 #{ad.id}")
        db.commit()
        db.refresh(clone)
        return clone

    @staticmethod
    def delete_draft(db: Session, ad: Ad) -> None:
        """仅 ``draft`` 可删除。"""
        if ad.status != AD_STATUS_DRAFT:
            raise api_error(409, "INVALID_TRANSITION", "只有草稿可以删除")
        db.query(AdTag).filter(AdTag.ad_id == ad.id).delete(synchronize_session=False)
        db.delete(ad)
        db.commit()

    # -------------------------------------------------------------- 审核动作
    @staticmethod
    def approve(
        db: Session,
        ad: Ad,
        admin_id: int,
        *,
        note: str | None = None,
        edits: dict[str, object] | None = None,
        action: str = "approve",
    ) -> tuple[Ad, dict[str, object]]:
        """通过审核：``pending`` → ``active`` / ``scheduled``，可带编辑。"""
        if ad.status != AD_STATUS_PENDING:
            raise api_error(409, "INVALID_TRANSITION", "只有待审核的广告可以通过")

        changes: dict[str, object] = {}
        if edits:
            changes = AdService._apply_admin_edits(db, ad, edits)

        current = now_utc()
        if ad.valid_from <= current < ad.valid_to:
            ad.status = AD_STATUS_ACTIVE
            ad.published_at = current
        elif ad.valid_from > current:
            ad.status = AD_STATUS_SCHEDULED
        else:
            raise api_error(409, "AD_EXPIRED", "该广告有效期已过，无法通过审核")

        ad.updated_at = current
        log_review(db, ad, action, "admin", admin_id, reason=note, changes=changes or None)
        db.commit()
        db.refresh(ad)
        audit_log.info(
            "ad_approve ad_id=%s admin_id=%s status=%s edited=%s", ad.id, admin_id, ad.status, bool(changes)
        )
        return ad, changes

    @staticmethod
    def _apply_admin_edits(db: Session, ad: Ad, edits: dict[str, object]) -> dict[str, object]:
        """应用管理员编辑并把前后值记录下来（P0-A-05）。"""
        changes: dict[str, object] = {}
        for key in ("title", "description", "category_id", "valid_from", "valid_to"):
            if key not in edits or edits[key] is None:
                continue
            new_value = edits[key]
            old_value = getattr(ad, key)
            if key == "valid_from":
                new_value = parse_cst_date_start(str(new_value))
            elif key == "valid_to":
                new_value = parse_cst_date_end(str(new_value))
            elif key == "category_id":
                new_value = int(new_value)
                category = db.get(Category, new_value)
                if category is None:
                    raise api_error(422, "CATEGORY_NOT_FOUND", "所选一级类别不存在")
            if old_value != new_value:
                changes[key] = {"from": _jsonable(old_value), "to": _jsonable(new_value)}
                setattr(ad, key, new_value)

        tag_ids = edits.get("tags")
        if tag_ids is not None:
            old_ids = [tag.id for tag in ad.tags]
            tags = AdService.resolve_tags(db, ad.category_id, [int(item) for item in tag_ids], require=True)
            new_ids = [tag.id for tag in tags]
            if sorted(old_ids) != sorted(new_ids):
                changes["tags"] = {"from": old_ids, "to": new_ids}
                create_ad_tag_links(db, ad, new_ids)

        if ad.valid_to <= ad.valid_from:
            raise api_error(422, "DATE_REVERSED", "有效期结束日必须晚于开始日")
        return changes

    @staticmethod
    def reject(db: Session, ad: Ad, admin_id: int, reason_code: str, note: str | None) -> Ad:
        """拒绝：``pending`` → ``rejected``，原因必填。"""
        if ad.status != AD_STATUS_PENDING:
            raise api_error(409, "INVALID_TRANSITION", "只有待审核的广告可以拒绝")
        if not reason_code:
            raise api_error(422, "REASON_REQUIRED", "拒绝必须选择原因", [
                {"field": "reason_code", "message": "拒绝必须选择原因"}
            ])
        from ..constants import REJECT_REASON_LABELS

        label = REJECT_REASON_LABELS.get(reason_code)
        if label is None:
            raise api_error(422, "REASON_INVALID", "拒绝原因不在可选范围内")
        ad.status = AD_STATUS_REJECTED
        ad.reject_reason_code = reason_code
        ad.reject_reason = f"{label}" + (f"：{note}" if note else "")
        ad.updated_at = now_utc()
        log_review(db, ad, "reject", "admin", admin_id, reason=ad.reject_reason)
        db.commit()
        db.refresh(ad)
        audit_log.info("ad_reject ad_id=%s admin_id=%s code=%s", ad.id, admin_id, reason_code)
        return ad

    @staticmethod
    def offline(db: Session, ad: Ad, admin_id: int | None, reason: str, *, actor_type: str = "admin") -> Ad:
        """下架：``active|scheduled`` → ``offline``，原因必填。"""
        if ad.status not in (AD_STATUS_ACTIVE, AD_STATUS_SCHEDULED):
            raise api_error(409, "INVALID_TRANSITION", "只有在架或待生效的广告可以下架")
        text = (reason or "").strip()
        if not text:
            raise api_error(422, "REASON_REQUIRED", "下架必须填写原因", [
                {"field": "reason", "message": "下架必须填写原因"}
            ])
        ad.status = AD_STATUS_OFFLINE
        ad.offline_reason = text[:300]
        ad.updated_at = now_utc()
        log_review(db, ad, "offline", actor_type, admin_id, reason=text)
        db.commit()
        db.refresh(ad)
        audit_log.info("ad_offline ad_id=%s actor=%s", ad.id, admin_id)
        return ad

    @staticmethod
    def restore(db: Session, ad: Ad, admin_id: int, note: str | None) -> Ad:
        """整改重提通道：``offline`` → ``pending``。"""
        if ad.status != AD_STATUS_OFFLINE:
            raise api_error(409, "INVALID_TRANSITION", "只有已下架的广告可以恢复审核")
        ad.status = AD_STATUS_PENDING
        ad.submitted_at = now_utc()
        ad.updated_at = now_utc()
        log_review(db, ad, "restore", "admin", admin_id, reason=note)
        db.commit()
        db.refresh(ad)
        return ad

    @staticmethod
    def log_review(
        db: Session,
        ad: Ad,
        action: str,
        actor_type: str,
        actor_id: int | None = None,
        reason: str | None = None,
        changes: dict[str, object] | None = None,
    ) -> Review:
        """实例方法形态的留痕入口（内部委托模块级 :func:`log_review`）。"""
        return log_review(db, ad, action, actor_type, actor_id, reason, changes)


def _jsonable(value: object) -> object:
    """把 datetime 等转成可 JSON 序列化的值。"""
    from datetime import datetime as _datetime

    if isinstance(value, _datetime):
        return utc_to_iso_z(value)
    return value


def _diff_changes(ad: Ad, old_values: dict[str, object]) -> dict[str, object]:
    """收集核心字段前后值差异。"""
    changes: dict[str, object] = {}
    for field_name, old_value in old_values.items():
        new_value = getattr(ad, field_name)
        if old_value != new_value:
            changes[field_name] = {"from": _jsonable(old_value), "to": _jsonable(new_value)}
    return changes
