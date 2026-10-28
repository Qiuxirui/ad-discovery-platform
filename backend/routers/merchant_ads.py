"""商家端广告管理：我的广告、新建、编辑、状态迁移、上传。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..constants import AD_STATUS, AD_STATUS_LABELS
from ..database import get_db
from ..deps import require_merchant
from ..models import Ad, Merchant
from ..schemas.ad import (
    AdCreateIn,
    AdManageEnvelope,
    AdManageOut,
    AdPrecheckOut,
    AdUpdateIn,
    MerchantAdListOut,
)
from ..schemas.common import OkOut
from ..services.ads import AdService, api_error, store_upload, to_manage_out
from ..services.stats import StatsService

router = APIRouter(prefix="/api/merchant", tags=["merchant-ads"])

STATUS_LABELS = AD_STATUS_LABELS


def own_ad(db: Session, ad_id: int, merchant: Merchant) -> Ad:
    """取本商家广告；越权一律 404（不泄露存在性）。"""
    ad = db.get(Ad, ad_id)
    if ad is None or ad.merchant_id != merchant.id:
        raise api_error(404, "AD_NOT_FOUND", "该广告不存在")
    return ad


@router.get("/ads", response_model=MerchantAdListOut)
def list_my_ads(
    status: str | None = Query(default=None, description="按状态筛选"),
    page: int = Query(default=1, ge=0),
    page_size: int = Query(default=24, ge=1, le=60),
    merchant: Merchant = Depends(require_merchant),
    db: Session = Depends(get_db),
) -> MerchantAdListOut:
    """我的广告列表 + 各状态计数。"""
    safe_page = max(1, page)
    stmt = select(Ad).where(Ad.merchant_id == merchant.id)
    if status:
        if status not in AD_STATUS:
            raise api_error(422, "STATUS_INVALID", "状态筛选值不合法")
        stmt = stmt.where(Ad.status == status)

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
    items: list[AdManageOut] = [to_manage_out(ad) for ad in rows]
    return MerchantAdListOut(
        items=items,
        counts=StatsService.merchant_status_counts(db, merchant.id),
        page=safe_page,
        page_size=page_size,
        total=total,
    )


@router.post("/ads", response_model=AdManageEnvelope)
def create_ad(
    payload: AdCreateIn,
    merchant: Merchant = Depends(require_merchant),
    db: Session = Depends(get_db),
) -> AdManageEnvelope:
    """新建广告；``submit=true`` 时直接进入待审核（预检不通过则直接已拒绝）。"""
    ad, precheck = AdService.create(db, merchant, payload)
    message = (
        "已提交，等待审核（预计 24 小时内）。审核通过前该广告不会公开。"
        if ad.status == "pending"
        else ("预检未通过，广告未提交：" + precheck.reason if not precheck.passed else "草稿已保存")
    )
    return AdManageEnvelope(
        ad=to_manage_out(ad),
        precheck=AdPrecheckOut(**precheck.as_dict()),
        message=message,
    )


@router.get("/ads/{ad_id}", response_model=AdManageEnvelope)
def get_my_ad(
    ad_id: int,
    merchant: Merchant = Depends(require_merchant),
    db: Session = Depends(get_db),
) -> AdManageEnvelope:
    """单条广告详情（仅自己）。"""
    ad = own_ad(db, ad_id, merchant)
    return AdManageEnvelope(ad=to_manage_out(ad), message=STATUS_LABELS.get(ad.status, ad.status))


@router.patch("/ads/{ad_id}", response_model=AdManageEnvelope)
def update_ad(
    ad_id: int,
    payload: AdUpdateIn,
    merchant: Merchant = Depends(require_merchant),
    db: Session = Depends(get_db),
) -> AdManageEnvelope:
    """编辑广告；``active`` 改核心字段会回到待审核并立即下线。"""
    ad = own_ad(db, ad_id, merchant)
    ad, became_pending = AdService.update(db, ad, payload, actor_type="merchant", actor_id=merchant.id)
    message = (
        "已保存。修改了核心字段，需重新审核，审核通过前该广告不对外展示。"
        if became_pending
        else "已保存"
    )
    return AdManageEnvelope(ad=to_manage_out(ad), became_pending=became_pending, message=message)


@router.delete("/ads/{ad_id}", response_model=OkOut)
def delete_ad(
    ad_id: int,
    merchant: Merchant = Depends(require_merchant),
    db: Session = Depends(get_db),
) -> OkOut:
    """删除草稿。"""
    ad = own_ad(db, ad_id, merchant)
    AdService.delete_draft(db, ad)
    return OkOut()


@router.post("/ads/{ad_id}/submit", response_model=AdManageEnvelope)
def submit_ad(
    ad_id: int,
    merchant: Merchant = Depends(require_merchant),
    db: Session = Depends(get_db),
) -> AdManageEnvelope:
    """提交审核：``draft|rejected`` → ``pending``（重跑完整校验 + 预检）。"""
    ad = own_ad(db, ad_id, merchant)
    ad, precheck = AdService.submit(db, ad)
    message = (
        "已提交，等待审核（预计 24 小时内）。审核通过前该广告不会公开。"
        if ad.status == "pending"
        else ("预检未通过：" + precheck.reason)
    )
    return AdManageEnvelope(
        ad=to_manage_out(ad),
        precheck=AdPrecheckOut(**precheck.as_dict()),
        message=message,
    )


@router.post("/ads/{ad_id}/withdraw", response_model=AdManageEnvelope)
def withdraw_ad(
    ad_id: int,
    merchant: Merchant = Depends(require_merchant),
    db: Session = Depends(get_db),
) -> AdManageEnvelope:
    """撤回：``pending`` → ``draft``。"""
    ad = own_ad(db, ad_id, merchant)
    ad = AdService.withdraw(db, ad)
    return AdManageEnvelope(ad=to_manage_out(ad), message="已撤回为草稿")


@router.post("/ads/{ad_id}/abandon", response_model=AdManageEnvelope)
def abandon_ad(
    ad_id: int,
    merchant: Merchant = Depends(require_merchant),
    db: Session = Depends(get_db),
) -> AdManageEnvelope:
    """放弃重提：``rejected`` → ``draft``。"""
    ad = own_ad(db, ad_id, merchant)
    ad = AdService.abandon(db, ad)
    return AdManageEnvelope(ad=to_manage_out(ad), message="已转为草稿")


@router.post("/ads/{ad_id}/duplicate", response_model=AdManageEnvelope)
def duplicate_ad(
    ad_id: int,
    merchant: Merchant = Depends(require_merchant),
    db: Session = Depends(get_db),
) -> AdManageEnvelope:
    """复制为新草稿（过期续期用，不复用旧 id）。"""
    ad = own_ad(db, ad_id, merchant)
    clone = AdService.duplicate(db, ad, merchant)
    return AdManageEnvelope(ad=to_manage_out(clone), message=f"已复制为新草稿#{clone.id}")


@router.post("/uploads")
def upload_image(
    file: UploadFile = File(...),
    merchant: Merchant = Depends(require_merchant),  # noqa: ARG001 - 仅要求登录
) -> dict[str, str]:
    """上传主图（jpg/png/webp，≤2MB，校验魔数）。"""
    data = file.file.read()
    image_path = store_upload(file.filename or "", file.content_type, data)
    return {"image_path": image_path}
