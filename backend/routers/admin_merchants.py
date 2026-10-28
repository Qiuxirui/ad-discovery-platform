"""管理端商家管理：列表（在架数/举报成立数/风险标记）、停用启用、核验、备注。"""

from __future__ import annotations

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..constants import AD_STATUS_ACTIVE, AD_STATUS_SCHEDULED
from ..database import get_db
from ..deps import require_admin
from ..models import Ad, AdminUser, Merchant, Report
from ..schemas.admin import MerchantNoteIn, MerchantRowOut, MerchantStatusIn, MerchantVerifyIn
from ..services.ads import AdService, api_error
from ..utils.timeutil import cst_date_str, now_utc

router = APIRouter(tags=["admin-merchants"])

audit_log = logging.getLogger("adx.audit")

RISK_THRESHOLD = 3
RISK_WINDOW_DAYS = 30


def _merchant_row(db: Session, merchant: Merchant) -> MerchantRowOut:
    active_ads = int(
        db.execute(
            select(func.count())
            .select_from(Ad)
            .where(Ad.merchant_id == merchant.id, Ad.status.in_([AD_STATUS_ACTIVE, AD_STATUS_SCHEDULED]))
        ).scalar_one()
    )
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
    window_start = now_utc() - timedelta(days=RISK_WINDOW_DAYS)
    resolved_30d = int(
        db.execute(
            select(func.count())
            .select_from(Report)
            .join(Ad, Ad.id == Report.ad_id)
            .where(
                Ad.merchant_id == merchant.id,
                Report.status == "resolved",
                Report.handled_at.is_not(None),
                Report.handled_at >= window_start,
            )
        ).scalar_one()
    )
    return MerchantRowOut(
        id=merchant.id,
        name=merchant.name,
        contact_name=merchant.contact_name,
        phone=merchant.phone,
        email=merchant.email,
        city=merchant.city,
        status=merchant.status,
        verified=merchant.verified,
        active_ads=active_ads,
        total_submitted=total_submitted,
        rejected_count=rejected_count,
        report_resolved_30d=resolved_30d,
        risk_flag=resolved_30d >= RISK_THRESHOLD,
        admin_note=merchant.admin_note,
        created_at=cst_date_str(merchant.created_at),
    )


@router.get("/api/admin/merchants", response_model=list[MerchantRowOut])
def list_merchants(
    q: str | None = Query(default=None, max_length=60),
    status: str | None = Query(default=None),
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> list[MerchantRowOut]:
    """商家列表（含风险标记与在架数）。"""
    stmt = select(Merchant)
    keyword = (q or "").strip()
    if keyword:
        like = f"%{keyword.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Merchant.name).like(like),
                func.lower(Merchant.contact_name).like(like),
                Merchant.phone.like(like),
                func.lower(Merchant.email).like(like),
            )
        )
    if status:
        stmt = stmt.where(Merchant.status == status)
    rows = db.execute(stmt.order_by(Merchant.created_at.desc()).limit(200)).scalars().all()
    return [_merchant_row(db, merchant) for merchant in rows]


@router.post("/api/admin/merchants/{merchant_id}/status")
def change_status(
    merchant_id: int,
    payload: MerchantStatusIn,
    admin: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """停用/启用商家；停用后其在架广告批量转 ``offline`` 并逐条写 reviews。"""
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        raise api_error(404, "MERCHANT_NOT_FOUND", "该商家不存在")
    if payload.status not in ("active", "disabled"):
        raise api_error(422, "STATUS_INVALID", "状态只能是 active 或 disabled")

    affected = 0
    merchant.status = payload.status
    if payload.note:
        merchant.admin_note = payload.note
    if payload.status == "disabled":
        ads = db.execute(
            select(Ad).where(
                Ad.merchant_id == merchant.id,
                Ad.status.in_([AD_STATUS_ACTIVE, AD_STATUS_SCHEDULED]),
            )
        ).unique().scalars().all()
        for ad in ads:
            AdService.offline(db, ad, admin.id, payload.note or "商家账号被停用，广告自动下架")
            affected += 1
    else:
        db.commit()
    audit_log.info("merchant_status merchant_id=%s status=%s affected=%s", merchant.id, payload.status, affected)
    db.refresh(merchant)
    return {"merchant": _merchant_row(db, merchant), "affected_ads": affected}


@router.post("/api/admin/merchants/{merchant_id}/verify", response_model=MerchantRowOut)
def verify_merchant(
    merchant_id: int,
    payload: MerchantVerifyIn,
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> MerchantRowOut:
    """标记"已核验/未核验"（Q2 裁决）。"""
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        raise api_error(404, "MERCHANT_NOT_FOUND", "该商家不存在")
    merchant.verified = payload.verified
    db.commit()
    db.refresh(merchant)
    return _merchant_row(db, merchant)


@router.patch("/api/admin/merchants/{merchant_id}", response_model=MerchantRowOut)
def update_merchant_note(
    merchant_id: int,
    payload: MerchantNoteIn,
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> MerchantRowOut:
    """更新管理员备注。"""
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        raise api_error(404, "MERCHANT_NOT_FOUND", "该商家不存在")
    merchant.admin_note = payload.admin_note
    db.commit()
    db.refresh(merchant)
    return _merchant_row(db, merchant)
