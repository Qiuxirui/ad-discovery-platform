"""匿名访客身份：``adx_vid`` Cookie 的签发、验签与中间件。

Cookie 值 = ``base64url(随机 32 字节)`` + ``.`` + ``HMAC-SHA256(前段, secret)`` 的 base64url 前 16 字节。
签名不合法一律丢弃并重发新标识，不向用户报错；服务端只存 ``visitor_id`` / 首末访问时间。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .config import get_settings
from .database import SessionLocal
from .models import Visitor
from .security import COOKIE_VISITOR
from .utils.timeutil import now_utc

__all__ = [
    "COOKIE_MAX_AGE",
    "VisitorMiddleware",
    "ensure_visitor",
    "generate_visitor_id",
    "make_cookie_value",
    "parse_cookie_value",
    "touch_visitor",
]

audit_log = logging.getLogger("adx.audit")

COOKIE_MAX_AGE = 15552000  # 180 天
TOUCH_INTERVAL = timedelta(minutes=10)

_touch_cache: dict[str, datetime] = {}


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _secret_bytes() -> bytes:
    return get_settings().resolved_secret.encode("utf-8")


def generate_visitor_id() -> str:
    """生成 43 字符的 base64url 随机标识（32 字节熵）。"""
    return _b64url_encode(secrets.token_bytes(32))


def _signature(visitor_id: str) -> str:
    digest = hmac.new(_secret_bytes(), visitor_id.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(digest[:16])


def make_cookie_value(visitor_id: str) -> str:
    """拼装 ``id.signature``。"""
    return f"{visitor_id}.{_signature(visitor_id)}"


def parse_cookie_value(value: str | None) -> str | None:
    """验签并返回 ``visitor_id``；不合法返回 ``None``。"""
    if not value or "." not in value:
        return None
    visitor_id, _, signature = value.partition(".")
    if not visitor_id or not signature:
        return None
    expected = _signature(visitor_id)
    if not hmac.compare_digest(expected, signature):
        return None
    return visitor_id


def ensure_visitor(db, visitor_id: str):  # noqa: ANN001, ANN201
    """确保 ``visitors`` 行存在（收藏/举报/事件写入前调用，避免外键失败）。"""
    visitor = db.get(Visitor, visitor_id)
    current = now_utc()
    if visitor is None:
        visitor = Visitor(id=visitor_id, first_seen=current, last_seen=current)
        db.add(visitor)
        db.flush()
    else:
        visitor.last_seen = current
    return visitor


def touch_visitor(visitor_id: str) -> None:
    """落库访客首末访问时间（10 分钟节流）。"""
    current = now_utc()
    last = _touch_cache.get(visitor_id)
    if last is not None and current - last < TOUCH_INTERVAL:
        return
    db = SessionLocal()
    try:
        visitor = db.get(Visitor, visitor_id)
        if visitor is None:
            db.add(Visitor(id=visitor_id, first_seen=current, last_seen=current))
        else:
            visitor.last_seen = current
        db.commit()
        _touch_cache[visitor_id] = current
    except Exception:  # noqa: BLE001 - 匿名身份失败不得影响主请求
        db.rollback()
        audit_log.warning("visitor_touch_failed visitor=%s", visitor_id[:8])
    finally:
        db.close()


class VisitorMiddleware(BaseHTTPMiddleware):
    """无有效 ``adx_vid`` 时下发新标识，并把 visitor_id 放进 ``request.state``。"""

    async def dispatch(self, request: Request, call_next):  # noqa: ANN001, ANN201
        cookie_value = request.cookies.get(COOKIE_VISITOR)
        visitor_id = parse_cookie_value(cookie_value)
        issued = visitor_id is None
        if visitor_id is None:
            visitor_id = generate_visitor_id()
        request.state.visitor_id = visitor_id
        request.state.visitor_issued = issued

        if request.url.path.startswith("/api"):
            touch_visitor(visitor_id)

        response: Response = await call_next(request)
        if issued:
            settings = get_settings()
            response.set_cookie(
                key=COOKIE_VISITOR,
                value=make_cookie_value(visitor_id),
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax",
                path="/",
                secure=settings.cookie_secure,
            )
        return response
