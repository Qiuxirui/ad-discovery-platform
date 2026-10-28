"""商家认证：注册即入驻、登录、登出、资料、改密码。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_merchant
from ..models import Category, Merchant
from ..schemas.auth import (
    MerchantEnvelope,
    MerchantLoginIn,
    MerchantOut,
    MerchantSignupIn,
    MerchantUpdateIn,
    PasswordChangeIn,
)
from ..schemas.common import OkOut
from ..security import (
    COOKIE_MERCHANT,
    clear_auth_cookie,
    create_token,
    hash_password,
    set_auth_cookie,
    verify_password,
)
from ..services.ads import ApiError, api_error
from ..utils.timeutil import cst_date_str, now_utc

router = APIRouter(prefix="/api/merchant", tags=["merchant-auth"])

LOGIN_FAILED = "账号或密码错误"
DISABLED_TEXT = "该商家账号已被停用，请联系运营者"


def merchant_out(merchant: Merchant) -> MerchantOut:
    """ORM → 输出模型（不含密码哈希）。"""
    return MerchantOut(
        id=merchant.id,
        name=merchant.name,
        contact_name=merchant.contact_name,
        phone=merchant.phone,
        email=merchant.email,
        city=merchant.city,
        main_category_id=merchant.main_category_id,
        main_category_name=merchant.category.name if merchant.category is not None else None,
        verified=merchant.verified,
        status=merchant.status,
        created_at=cst_date_str(merchant.created_at),
    )


def _bind_login_cookie(response: Response, merchant: Merchant) -> None:
    set_auth_cookie(response, COOKIE_MERCHANT, create_token(merchant.id, "merchant"))


@router.post("/signup", response_model=MerchantEnvelope)
def signup(
    payload: MerchantSignupIn,
    response: Response,
    db: Session = Depends(get_db),
) -> MerchantEnvelope:
    """注册即入驻；重名/重手机/重邮箱返回 409。"""
    duplicated = db.execute(
        select(Merchant).where(
            or_(
                Merchant.name == payload.name,
                Merchant.phone == payload.phone,
                Merchant.email == payload.email,
            )
        )
    ).scalars().first()
    if duplicated is not None:
        if duplicated.name == payload.name:
            raise api_error(409, "NAME_TAKEN", "该商家名已被使用，请换一个名称")
        if duplicated.phone == payload.phone:
            raise api_error(409, "PHONE_TAKEN", "该手机号已注册，请直接登录")
        raise api_error(409, "EMAIL_TAKEN", "该邮箱已注册，请直接登录")

    if payload.main_category_id is not None:
        category = db.get(Category, payload.main_category_id)
        if category is None:
            raise api_error(422, "CATEGORY_NOT_FOUND", "所选主营类别不存在")

    current = now_utc()
    merchant = Merchant(
        name=payload.name,
        contact_name=payload.contact_name,
        phone=payload.phone,
        email=payload.email,
        password_hash=hash_password(payload.password),
        city=payload.city,
        main_category_id=payload.main_category_id,
        status="active",
        verified=False,
        last_login_at=current,
        created_at=current,
        updated_at=current,
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    _bind_login_cookie(response, merchant)
    return MerchantEnvelope(merchant=merchant_out(merchant))


@router.post("/login", response_model=MerchantEnvelope)
def login(
    payload: MerchantLoginIn,
    response: Response,
    db: Session = Depends(get_db),
) -> MerchantEnvelope:
    """邮箱或手机号 + 密码登录。"""
    account = payload.account.lower()
    merchant = db.execute(
        select(Merchant).where(or_(Merchant.email == account, Merchant.phone == account))
    ).scalars().first()
    if merchant is None or not verify_password(payload.password, merchant.password_hash):
        raise api_error(401, "LOGIN_FAILED", LOGIN_FAILED)
    if merchant.status != "active":
        raise api_error(403, "MERCHANT_DISABLED", DISABLED_TEXT)

    merchant.last_login_at = now_utc()
    db.commit()
    db.refresh(merchant)
    _bind_login_cookie(response, merchant)
    return MerchantEnvelope(merchant=merchant_out(merchant))


@router.post("/logout", response_model=OkOut)
def logout(response: Response) -> OkOut:
    """退出登录（清除 Cookie）。"""
    clear_auth_cookie(response, COOKIE_MERCHANT)
    return OkOut()


@router.get("/me", response_model=MerchantOut)
def get_me(merchant: Merchant = Depends(require_merchant)) -> MerchantOut:
    """当前商家资料。"""
    return merchant_out(merchant)


@router.patch("/me", response_model=MerchantOut)
def update_me(
    payload: MerchantUpdateIn,
    merchant: Merchant = Depends(require_merchant),
    db: Session = Depends(get_db),
) -> MerchantOut:
    """修改商家资料（手机号需唯一）。"""
    data = payload.model_dump(exclude_unset=True)
    if "phone" in data and data["phone"] and data["phone"] != merchant.phone:
        exists = db.execute(
            select(Merchant).where(Merchant.phone == data["phone"], Merchant.id != merchant.id)
        ).scalars().first()
        if exists is not None:
            raise api_error(409, "PHONE_TAKEN", "该手机号已被其他账号使用")
        merchant.phone = str(data["phone"])
    if "contact_name" in data and data["contact_name"]:
        merchant.contact_name = str(data["contact_name"])
    if "city" in data and data["city"]:
        merchant.city = str(data["city"])
    if "main_category_id" in data and data["main_category_id"] is not None:
        category = db.get(Category, int(data["main_category_id"]))
        if category is None:
            raise api_error(422, "CATEGORY_NOT_FOUND", "所选主营类别不存在")
        merchant.main_category_id = category.id
    merchant.updated_at = now_utc()
    db.commit()
    db.refresh(merchant)
    return merchant_out(merchant)


@router.post("/me/password", response_model=OkOut)
def change_password(
    payload: PasswordChangeIn,
    merchant: Merchant = Depends(require_merchant),
    db: Session = Depends(get_db),
) -> OkOut:
    """修改密码（需校验原密码）。"""
    if not verify_password(payload.old_password, merchant.password_hash):
        raise api_error(400, "PASSWORD_MISMATCH", "原密码不正确")
    merchant.password_hash = hash_password(payload.new_password)
    merchant.updated_at = now_utc()
    db.commit()
    return OkOut()


__all__ = ["ApiError", "merchant_out", "router"]
