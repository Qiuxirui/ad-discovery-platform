"""密码哈希、JWT 令牌与 Cookie 读写。

密码哈希**只用** ``passlib.hash.pbkdf2_sha256``：本机 bcrypt 5.0 与 passlib 1.7.4
不兼容（``AttributeError: module 'bcrypt' has no attribute '__about__'``），已实测。
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import jwt
from passlib.hash import pbkdf2_sha256
from starlette.responses import Response

from .config import get_settings
from .constants import ADMIN_LOCK_MINUTES, ADMIN_LOCK_THRESHOLD
from .utils.timeutil import now_utc

__all__ = [
    "COOKIE_ADMIN",
    "COOKIE_MERCHANT",
    "COOKIE_VISITOR",
    "LOCK_MINUTES",
    "LOCK_THRESHOLD",
    "clear_auth_cookie",
    "create_token",
    "decode_token",
    "hash_password",
    "next_lock_state",
    "set_auth_cookie",
    "verify_password",
]

COOKIE_VISITOR = "adx_vid"
COOKIE_MERCHANT = "adx_merchant"
COOKIE_ADMIN = "adx_admin"

PBKDF2_ROUNDS = 29000
JWT_ALGORITHM = "HS256"

LOCK_THRESHOLD = ADMIN_LOCK_THRESHOLD
LOCK_MINUTES = ADMIN_LOCK_MINUTES

_ISSUER = "adx"


def hash_password(raw: str) -> str:
    """生成 pbkdf2_sha256 哈希（含随机盐）。"""
    return pbkdf2_sha256.using(rounds=PBKDF2_ROUNDS, salt_size=16).hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    """校验密码，异常一律视为不匹配。"""
    try:
        return pbkdf2_sha256.verify(raw, hashed)
    except (ValueError, TypeError):
        return False


def create_token(subject: int | str, role: str, ttl_seconds: int | None = None) -> str:
    """签发 HS256 令牌。"""
    settings = get_settings()
    ttl = ttl_seconds or settings.token_ttl_seconds
    issued = int(time.time())
    payload = {
        "sub": str(subject),
        "role": role,
        "iss": _ISSUER,
        "iat": issued,
        "exp": issued + ttl,
    }
    return jwt.encode(payload, settings.resolved_secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str | None) -> dict | None:
    """解析令牌；无效或过期返回 ``None``。"""
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            get_settings().resolved_secret,
            algorithms=[JWT_ALGORITHM],
            issuer=_ISSUER,
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def set_auth_cookie(response: Response, name: str, token: str, max_age: int | None = None) -> None:
    """写入 HttpOnly 登录 Cookie（生产置 ``Secure``）。"""
    settings = get_settings()
    response.set_cookie(
        key=name,
        value=token,
        max_age=max_age or settings.token_ttl_seconds,
        httponly=True,
        samesite="lax",
        path="/",
        secure=settings.cookie_secure,
    )


def clear_auth_cookie(response: Response, name: str) -> None:
    """清除登录 Cookie。"""
    settings = get_settings()
    response.delete_cookie(key=name, path="/", httponly=True, samesite="lax", secure=settings.cookie_secure)


def next_lock_state(failed_attempts: int, now: datetime | None = None) -> tuple[int, datetime | None]:
    """登录失败计数 → ``(新计数, 锁定到期时间)``；第 5 次失败锁 15 分钟。"""
    current = now or now_utc()
    attempts = failed_attempts + 1
    if attempts >= LOCK_THRESHOLD:
        return attempts, current + timedelta(minutes=LOCK_MINUTES)
    return attempts, None


def utc_now_aware() -> datetime:
    """供外部比较用的 aware UTC 时间。"""
    return datetime.now(timezone.utc)
