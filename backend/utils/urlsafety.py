"""URL 安全校验与禁投词扫描（PRD P0-K-01 / P0-K-02 / 架构 §3.5）。"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from ..constants import BANNED_KEYWORDS, DANGEROUS_SUFFIXES, PRIVATE_HOST_MARKERS, SHORTENER_DOMAINS

__all__ = [
    "BannedWordHit",
    "UrlSafetyResult",
    "check_url_safety",
    "extract_domain",
    "normalize_url",
    "scan_banned_words",
]

_ALLOWED_SCHEMES = ("http", "https")
_BARE_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-.]*\.[A-Za-z]{2,}(?::\d+)?(?:[/?#].*)?$")


@dataclass(slots=True)
class UrlSafetyResult:
    """URL 校验结果。"""

    ok: bool
    code: str = ""
    reason: str = ""
    domain: str = ""
    url: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.ok,
            "code": self.code,
            "reason": self.reason,
            "domain": self.domain,
        }


@dataclass(slots=True)
class BannedWordHit:
    """禁投词命中详情。"""

    word: str
    field: str

    @property
    def text(self) -> str:
        return f"命中禁投行业关键词「{self.word}」"


def normalize_url(raw: str) -> str:
    """规范化 URL：去空白、补协议、去片段、去默认端口。"""
    value = (raw or "").strip()
    if not value:
        return ""
    if "://" not in value and _BARE_HOST_RE.match(value):
        value = "https://" + value
    parts = urlsplit(value)
    scheme = (parts.scheme or "").lower()
    host = (parts.hostname or "").lower()
    port = parts.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def extract_domain(url: str) -> str:
    """取 host（小写、去 www 前缀保留可读性：这里保留原样，仅小写）。"""
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _is_bare_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _is_private_host(host: str) -> bool:
    lowered = host.lower()
    if any(marker in lowered for marker in PRIVATE_HOST_MARKERS):
        return True
    if lowered.startswith("172."):
        parts = lowered.split(".")
        if len(parts) >= 2 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
            return True
    return False


def check_url_safety(raw: str) -> UrlSafetyResult:
    """校验落地页 URL：仅 http(s)、非短链、非危险后缀、非内网/裸 IP。"""
    value = (raw or "").strip()
    if not value:
        return UrlSafetyResult(ok=False, code="URL_EMPTY", reason="落地页地址不能为空")

    normalized = normalize_url(value)
    try:
        parts = urlsplit(normalized)
    except ValueError:
        return UrlSafetyResult(ok=False, code="URL_INVALID", reason="落地页地址格式不正确")

    scheme = (parts.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        return UrlSafetyResult(
            ok=False,
            code="URL_SCHEME",
            reason="落地页只支持 http 或 https 地址，不接受 javascript:、data: 等写法",
        )

    if "@" in (parts.netloc or ""):
        return UrlSafetyResult(ok=False, code="URL_USERINFO", reason="落地页地址不允许包含用户名或密码信息")

    host = (parts.hostname or "").lower()
    if not host:
        return UrlSafetyResult(ok=False, code="URL_INVALID", reason="落地页地址缺少域名")

    if _is_bare_ip(host):
        return UrlSafetyResult(ok=False, code="URL_BARE_IP", reason="落地页不支持直接使用 IP 地址，请使用域名")

    if _is_private_host(host):
        return UrlSafetyResult(ok=False, code="URL_PRIVATE_HOST", reason="落地页不支持本机或内网地址")

    if host in SHORTENER_DOMAINS or any(host.endswith("." + item) for item in SHORTENER_DOMAINS):
        return UrlSafetyResult(
            ok=False,
            code="URL_SHORTENER",
            reason="落地页不支持短链接，请填写可直接访问的目标页面地址",
        )

    lowered_path = (parts.path or "").lower()
    for suffix in DANGEROUS_SUFFIXES:
        if lowered_path.endswith(suffix):
            return UrlSafetyResult(
                ok=False,
                code="URL_SUFFIX",
                reason=f"落地页不允许指向可执行文件或压缩包（{suffix}）",
            )

    if len(normalized) > 500:
        return UrlSafetyResult(ok=False, code="URL_TOO_LONG", reason="落地页地址过长（上限 500 字符）")

    return UrlSafetyResult(ok=True, domain=host, url=normalized)


def scan_banned_words(*fields: tuple[str, str | None]) -> list[BannedWordHit]:
    """扫描禁投行业关键词；``fields`` 为 ``(字段名, 文本)`` 序列。"""
    hits: list[BannedWordHit] = []
    for field_name, text in fields:
        if not text:
            continue
        lowered = text.lower()
        for word in BANNED_KEYWORDS:
            if word.lower() in lowered:
                hits.append(BannedWordHit(word=word, field=field_name))
    return hits
