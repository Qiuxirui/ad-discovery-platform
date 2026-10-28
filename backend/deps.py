"""FastAPI 依赖注入：匿名身份、双角色鉴权、分页参数。

商家/管理员令牌放在 HttpOnly Cookie（``adx_merchant`` / ``adx_admin``），
所有权限判定都在服务端完成，与 URL 是否被猜到无关。
"""

from __future__ import annotations

from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from .constants import MAX_PAGE_SIZE, PAGE_SIZE
from .database import get_db
from .models import AdminUser, Merchant
from .security import COOKIE_ADMIN, COOKIE_MERCHANT, decode_token
from .services.ads import ApiError, api_error

__all__ = [
    "get_current_admin",
    "get_current_merchant",
    "get_optional_admin",
    "get_optional_merchant",
    "get_optional_visitor_id",
    "get_pagination",
    "get_visitor_id",
    "require_admin",
    "require_merchant",
]


def get_visitor_id(request: Request) -> str:
    """取匿名访客标识（由 ``VisitorMiddleware`` 保证一定存在）。"""
    visitor_id = getattr(request.state, "visitor_id", None)
    if not visitor_id:
        raise api_error(400, "VISITOR_MISSING", "缺少匿名访问标识，请刷新页面重试")
    return visitor_id


def get_optional_visitor_id(request: Request) -> str | None:
    """可选匿名标识（不强制存在）。"""
    return getattr(request.state, "visitor_id", None)


def get_optional_merchant(request: Request, db: Session = Depends(get_db)) -> Merchant | None:
    """已登录且状态正常的商家；否则 ``None``。"""
    payload = decode_token(request.cookies.get(COOKIE_MERCHANT))
    if not payload or payload.get("role") != "merchant":
        return None
    try:
        merchant_id = int(str(payload.get("sub")))
    except (TypeError, ValueError):
        return None
    merchant = db.get(Merchant, merchant_id)
    if merchant is None or merchant.status != "active":
        return None
    return merchant


def require_merchant(merchant: Merchant | None = Depends(get_optional_merchant)) -> Merchant:
    """强制要求商家登录。"""
    if merchant is None:
        raise api_error(401, "UNAUTHORIZED", "请先登录商家账号")
    return merchant


def get_optional_admin(request: Request, db: Session = Depends(get_db)) -> AdminUser | None:
    """已登录且启用的管理员；否则 ``None``。"""
    payload = decode_token(request.cookies.get(COOKIE_ADMIN))
    if not payload or payload.get("role") != "admin":
        return None
    try:
        admin_id = int(str(payload.get("sub")))
    except (TypeError, ValueError):
        return None
    admin = db.get(AdminUser, admin_id)
    if admin is None or not admin.is_active:
        return None
    return admin


def require_admin(admin: AdminUser | None = Depends(get_optional_admin)) -> AdminUser:
    """强制要求管理员登录（未登录一律 401）。"""
    if admin is None:
        raise api_error(401, "UNAUTHORIZED", "请先登录运营后台")
    return admin


def get_current_merchant(merchant: Merchant = Depends(require_merchant)) -> Merchant:
    """别名：语义化取当前商家。"""
    return merchant


def get_current_admin(admin: AdminUser = Depends(require_admin)) -> AdminUser:
    """别名：语义化取当前管理员。"""
    return admin


def get_pagination(
    page: int = Query(1, ge=0, description="页码，从 1 开始"),
    page_size: int = Query(PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="每页条数，上限 60"),
) -> tuple[int, int]:
    """分页参数（``page<1`` 归一为 1）。"""
    return max(1, page), min(page_size, MAX_PAGE_SIZE)


__all__ += ["ApiError"]
