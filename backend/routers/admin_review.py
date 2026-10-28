"""管理端审核：审核队列与通过/拒绝/编辑后通过/下架/整改重提。"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..constants import REJECT_REASON_LABELS
from ..database import get_db
from ..deps import require_admin
from ..models import Ad, AdminUser, Merchant, Report, Review
from ..schemas.admin import (
    AdEnvelope,
    ApproveIn,
    EditApproveIn,
    OfflineIn,
    RejectIn,
    RestoreIn,
    ReviewQueueItemOut,
    ReviewQueueMerchantOut,
    ReviewQueueOut,
)
from ..schemas.ad import AdUpdateIn
from ..services.ads import AdService, PrecheckResult, api_error, to_manage_out
from ..utils.timeutil import cst_date_str, now_utc, today_cst_range_utc, utc_to_iso_z

router = APIRouter(tags=["admin-review"])

audit_log = logging.getLogger("adx.audit")


def live_precheck(ad: Ad) -> PrecheckResult:
    """对库里当前内容重跑一次预检（只读，用于审核队列展示机器码）。

    只关心**内容类**规则（禁投词、落地页 URL 安全）与"是否已过期"：
    ``valid_from`` 用今天代替原始开始日，避免广告在队列里排队几天后
    被 ``DATE_TOO_EARLY`` 误判成预检不通过（那不是内容问题）。
    """
    payload = AdUpdateIn(
        title=ad.title,
        description=ad.description,
        landing_url=ad.landing_url,
        valid_from=cst_date_str(now_utc()),
        valid_to=cst_date_str(ad.valid_to),
    )
    return AdService.precheck(payload, category=ad.category)


def _merchant_history(db: Session, merchant: Merchant) -> ReviewQueueMerchantOut:
    """商家历史聚合（累计提交 / 被拒次数 / 举报成立次数）。"""
    total_submitted = int(
        db.execute(
            select(func.count()).select_from(Ad).where(Ad.merchant_id == merchant.id, Ad.submitted_at.is_not(None))
        ).scalar_one()
    )
    rejected_count = int(
        db.execute(
            select(func.count()).select_from(Ad).where(Ad.merchant_id == merchant.id, Ad.status == "rejected")
        ).scalar_one()
    )
    report_resolved = int(
        db.execute(
            select(func.count())
            .select_from(Report)
            .join(Ad, Ad.id == Report.ad_id)
            .where(Ad.merchant_id == merchant.id, Report.status == "resolved")
        ).scalar_one()
    )
    return ReviewQueueMerchantOut(
        id=merchant.id,
        name=merchant.name,
        total_submitted=total_submitted,
        rejected_count=rejected_count,
        report_resolved_count=report_resolved,
        joined_at=cst_date_str(merchant.created_at),
    )


@router.get("/api/admin/review-queue", response_model=ReviewQueueOut)
def review_queue(
    category_id: int | None = Query(default=None),
    sort: str = Query(default="oldest", description="oldest（等待最久优先）| newest"),
    page: int = Query(default=1, ge=0),
    page_size: int = Query(default=20, ge=1, le=60),
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001 - 仅要求登录
    db: Session = Depends(get_db),
) -> ReviewQueueOut:
    """审核队列：默认只含 ``pending``，按提交时间升序。"""
    safe_page = max(1, page)
    stmt = select(Ad).where(Ad.status == "pending")
    if category_id is not None:
        stmt = stmt.where(Ad.category_id == category_id)

    total = int(db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one())
    order = Ad.submitted_at.asc() if sort != "newest" else Ad.submitted_at.desc()
    rows = (
        db.execute(
            stmt.order_by(order, Ad.id.asc()).offset((safe_page - 1) * page_size).limit(page_size)
        )
        .unique()
        .scalars()
        .all()
    )

    current = now_utc()
    items: list[ReviewQueueItemOut] = []
    for ad in rows:
        merchant = db.get(Merchant, ad.merchant_id)
        waiting = 0
        if ad.submitted_at is not None:
            waiting = max(0, int((current - ad.submitted_at).total_seconds() // 60))
        live = live_precheck(ad)
        items.append(
            ReviewQueueItemOut(
                ad=to_manage_out(ad),
                merchant=_merchant_history(db, merchant) if merchant is not None else ReviewQueueMerchantOut(id=0, name="未知商家"),
                precheck=ad.precheck_note,
                precheck_passed=live.passed,
                precheck_code=live.code or "PRECHECK_PASSED",
                precheck_reason=live.reason,
                waiting_minutes=waiting,
                submitted_at=utc_to_iso_z(ad.submitted_at),
            )
        )

    start, end = today_cst_range_utc(current)
    today_processed = int(
        db.execute(
            select(func.count())
            .select_from(Review)
            .where(Review.action.in_(["approve", "reject", "edit_approve"]), Review.created_at >= start, Review.created_at < end)
        ).scalar_one()
    )
    return ReviewQueueOut(
        items=items,
        total=total,
        page=safe_page,
        page_size=page_size,
        today_processed=today_processed,
    )


def _pending_ad(db: Session, ad_id: int) -> Ad:
    ad = db.get(Ad, ad_id)
    if ad is None:
        raise api_error(404, "AD_NOT_FOUND", "该广告不存在")
    return ad


@router.post("/api/admin/ads/{ad_id}/approve", response_model=AdEnvelope)
def approve_ad(
    ad_id: int,
    payload: ApproveIn | None = None,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdEnvelope:
    """通过：``pending`` → ``active``/``scheduled``。"""
    ad = _pending_ad(db, ad_id)
    ad, changes = AdService.approve(db, ad, admin.id, note=payload.note if payload else None)
    return AdEnvelope(
        ad=to_manage_out(ad),
        changes=changes,
        message="已通过，广告已上线" if ad.status == "active" else "已通过，开始时间在未来，状态为待生效",
    )


@router.post("/api/admin/ads/{ad_id}/reject", response_model=AdEnvelope)
def reject_ad(
    ad_id: int,
    payload: RejectIn,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdEnvelope:
    """拒绝：``pending`` → ``rejected``（原因必填）。"""
    ad = _pending_ad(db, ad_id)
    if payload.reason_code not in REJECT_REASON_LABELS:
        raise api_error(422, "REASON_INVALID", "拒绝原因不在可选范围内", [
            {"field": "reason_code", "message": "请选择拒绝原因"}
        ])
    ad = AdService.reject(db, ad, admin.id, payload.reason_code, payload.reason_note)
    return AdEnvelope(ad=to_manage_out(ad), message="已拒绝，商家可修改后重新提交")


@router.post("/api/admin/ads/{ad_id}/edit-approve", response_model=AdEnvelope)
def edit_approve_ad(
    ad_id: int,
    payload: EditApproveIn,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdEnvelope:
    """编辑后通过：字段前后值写入 ``reviews.changes``。"""
    ad = _pending_ad(db, ad_id)
    ad, changes = AdService.approve(
        db,
        ad,
        admin.id,
        note=payload.note,
        edits=payload.changes or {},
        action="edit_approve",
    )
    return AdEnvelope(
        ad=to_manage_out(ad),
        changes=changes,
        message="已编辑并通过，变更已记录在操作历史中" if changes else "已通过（未检测到字段变更）",
    )


@router.post("/api/admin/ads/{ad_id}/offline", response_model=AdEnvelope)
def offline_ad(
    ad_id: int,
    payload: OfflineIn | None = None,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdEnvelope:
    """下架：``active|scheduled`` → ``offline``（原因为空 → 422 ``REASON_REQUIRED``）。"""
    ad = _pending_ad(db, ad_id)
    ad = AdService.offline(db, ad, admin.id, (payload.reason if payload else None) or "")
    return AdEnvelope(ad=to_manage_out(ad), message="已下架，用户端立刻不可见")


@router.post("/api/admin/ads/{ad_id}/restore", response_model=AdEnvelope)
def restore_ad(
    ad_id: int,
    payload: RestoreIn | None = None,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdEnvelope:
    """整改重提通道：``offline`` → ``pending``（保留下架原因）。"""
    ad = _pending_ad(db, ad_id)
    ad = AdService.restore(db, ad, admin.id, payload.note if payload else None)
    return AdEnvelope(ad=to_manage_out(ad), message="已恢复为待审核")


@router.get("/api/admin/ads/{ad_id}/reviews")
def ad_reviews_timeline(
    ad_id: int,
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """操作时间线（只增不改不删）。"""
    from ..constants import ACTOR_TYPE_LABELS, REVIEW_ACTION_LABELS

    ad = db.get(Ad, ad_id)
    if ad is None:
        raise api_error(404, "AD_NOT_FOUND", "该广告不存在")
    rows = (
        db.execute(select(Review).where(Review.ad_id == ad_id).order_by(Review.created_at.asc()))
        .scalars()
        .all()
    )
    items = []
    for row in rows:
        actor_name = ""
        if row.actor_type == "merchant":
            merchant = db.get(Merchant, row.actor_id) if row.actor_id else None
            actor_name = merchant.name if merchant is not None else ""
        elif row.actor_type == "admin":
            operator = db.get(AdminUser, row.actor_id) if row.actor_id else None
            actor_name = operator.display_name if operator is not None else ""
        else:
            actor_name = ACTOR_TYPE_LABELS.get("system", "系统")
        changes = None
        if row.changes:
            try:
                changes = json.loads(row.changes)
            except json.JSONDecodeError:
                changes = None
        items.append(
            {
                "action": row.action,
                "action_label": REVIEW_ACTION_LABELS.get(row.action, row.action),
                "actor_type": row.actor_type,
                "actor_name": actor_name,
                "reason": row.reason,
                "changes": changes,
                "created_at": utc_to_iso_z(row.created_at),
            }
        )
    return {"items": items}


__all__ = ["router"]
