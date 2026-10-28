"""管理端认证：登录（5 次失败锁 15 分钟）、登出、当前账号。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..constants import ADMIN_LOCK_THRESHOLD
from ..database import get_db
from ..deps import require_admin
from ..models import AdminUser
from ..schemas.admin import AdminEnvelope
from ..schemas.auth import AdminLoginIn, AdminOut
from ..schemas.common import OkOut
from ..security import (
    COOKIE_ADMIN,
    LOCK_MINUTES,
    clear_auth_cookie,
    create_token,
    set_auth_cookie,
    verify_password,
)
from ..services.ads import api_error
from ..utils.timeutil import now_utc, utc_to_iso_z

router = APIRouter(tags=["admin-auth"])

audit_log = logging.getLogger("adx.audit")

LOGIN_FAILED = "账号或密码错误"


@router.post("/api/admin/login", response_model=AdminEnvelope)
def admin_login(
    payload: AdminLoginIn,
    response: Response,
    db: Session = Depends(get_db),
) -> AdminEnvelope:
    """后台登录；连续 5 次失败锁定 15 分钟（423）；返回 ``{admin:{...}}``。"""
    admin = db.execute(
        select(AdminUser).where(AdminUser.username == payload.username.strip())
    ).scalars().first()

    if admin is not None and admin.is_locked():
        remaining = int((admin.locked_until - now_utc()).total_seconds() // 60) + 1
        raise api_error(
            423,
            "LOCKED",
            f"登录失败次数过多，账号已锁定，请 {remaining} 分钟后再试",
        )

    if admin is None or not admin.is_active or not verify_password(payload.password, admin.password_hash):
        if admin is not None:
            admin.failed_attempts += 1
            if admin.failed_attempts >= ADMIN_LOCK_THRESHOLD:
                from datetime import timedelta as _timedelta

                admin.locked_until = now_utc() + _timedelta(minutes=LOCK_MINUTES)
                db.commit()
                audit_log.warning("admin_login_locked username=%s", admin.username)
                raise api_error(
                    423,
                    "LOCKED",
                    f"登录失败次数过多，账号已锁定 {LOCK_MINUTES} 分钟",
                )
            db.commit()
        raise api_error(401, "LOGIN_FAILED", LOGIN_FAILED)

    admin.failed_attempts = 0
    admin.locked_until = None
    admin.last_login_at = now_utc()
    db.commit()
    db.refresh(admin)

    set_auth_cookie(response, COOKIE_ADMIN, create_token(admin.id, "admin"))
    audit_log.info("admin_login_ok username=%s at=%s", admin.username, utc_to_iso_z(admin.last_login_at))
    return AdminEnvelope(
        admin=AdminOut(
            id=admin.id,
            username=admin.username,
            display_name=admin.display_name,
            role=admin.role,
        )
    )


@router.post("/api/admin/logout", response_model=OkOut)
def admin_logout(response: Response) -> OkOut:
    """退出登录。"""
    clear_auth_cookie(response, COOKIE_ADMIN)
    return OkOut()


@router.get("/api/admin/me", response_model=AdminOut)
def admin_me(admin: AdminUser = Depends(require_admin)) -> AdminOut:
    """当前管理员。"""
    return AdminOut(id=admin.id, username=admin.username, display_name=admin.display_name, role=admin.role)
