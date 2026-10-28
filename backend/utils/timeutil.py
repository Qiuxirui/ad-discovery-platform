"""时间工具：固定 +8 偏移（禁止 zoneinfo，本机无 tzdata）。

口径：
- 数据库一律存 **naive UTC**；
- ``now_utc()`` 返回 naive UTC；
- 商家输入的 ``YYYY-MM-DD`` 视为北京时间，开始取 00:00:00，结束取 23:59:59.999999；
- API 输出统一为带 ``Z`` 的 ISO 字符串。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

__all__ = [
    "CST",
    "UTC",
    "cst_date_range_utc",
    "cst_date_str",
    "days_left",
    "is_expiring_soon",
    "now_utc",
    "parse_cst_date_end",
    "parse_cst_date_start",
    "to_cst",
    "today_cst_range_utc",
    "utc_to_iso_z",
    "utc_to_local_date_str",
]

#: 中国标准时间（无夏令时，固定偏移等价于 Asia/Shanghai）
CST = timezone(timedelta(hours=8), "Asia/Shanghai")
UTC = timezone.utc

DATE_FMT = "%Y-%m-%d"


def now_utc() -> datetime:
    """当前 UTC 时间（naive，用于数据库读写）。"""
    return datetime.now(UTC).replace(tzinfo=None)


def utc_to_iso_z(value: datetime | None) -> str | None:
    """naive UTC → ``2026-11-15T15:59:59Z``；``None`` 原样返回。"""
    if value is None:
        return None
    naive = value.replace(tzinfo=None) if value.tzinfo is not None else value
    return naive.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_cst(value: datetime) -> datetime:
    """naive UTC → 北京时间（aware）。"""
    naive = value.replace(tzinfo=None) if value.tzinfo is not None else value
    return naive.replace(tzinfo=UTC).astimezone(CST)


def cst_date_str(value: datetime | None) -> str | None:
    """naive UTC → 北京时间自然日字符串 ``YYYY-MM-DD``。"""
    if value is None:
        return None
    return to_cst(value).strftime(DATE_FMT)


def utc_to_local_date_str(value: datetime | None) -> str | None:
    """别名：与 :func:`cst_date_str` 等价，语义更贴近输出字段名。"""
    return cst_date_str(value)


def _cst_to_utc_naive(value: datetime) -> datetime:
    """北京时间（naive）→ naive UTC。"""
    return value.replace(tzinfo=CST).astimezone(UTC).replace(tzinfo=None)


def parse_cst_date_start(text: str) -> datetime:
    """``YYYY-MM-DD`` → 北京时间当日 00:00:00 的 naive UTC。"""
    day = date.fromisoformat(text.strip())
    return _cst_to_utc_naive(datetime(day.year, day.month, day.day, 0, 0, 0))


def parse_cst_date_end(text: str) -> datetime:
    """``YYYY-MM-DD`` → 北京时间当日 23:59:59.999999 的 naive UTC。"""
    day = date.fromisoformat(text.strip())
    return _cst_to_utc_naive(datetime(day.year, day.month, day.day, 23, 59, 59, 999999))


def parse_cst_datetime(text: str) -> datetime:
    """支持 ``YYYY-MM-DD`` 或 ``YYYY-MM-DD HH:MM`` / ISO 形式，按北京时间解析。"""
    raw = text.strip()
    if len(raw) == 10:
        return parse_cst_date_start(raw)
    candidate = raw.replace("T", " ").split(".")[0]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            parsed = datetime.strptime(candidate, fmt)
        except ValueError:
            continue
        return _cst_to_utc_naive(parsed)
    raise ValueError(f"无法解析时间：{text}")


def days_left(valid_to: datetime, now: datetime | None = None) -> int:
    """剩余天数（向上取整，最小 0）。"""
    current = now or now_utc()
    delta = valid_to - current
    if delta.total_seconds() <= 0:
        return 0
    return int((delta.total_seconds() + 86399) // 86400)


def is_expiring_soon(valid_to: datetime, now: datetime | None = None) -> bool:
    """剩余有效期 ≤48h（PRD 6.2 "即将结束"徽标口径）。"""
    current = now or now_utc()
    delta = valid_to - current
    return timedelta(0) < delta <= timedelta(hours=48)


def today_cst_range_utc(now: datetime | None = None) -> tuple[datetime, datetime]:
    """北京时间"今天"对应的 ``[start_utc, end_utc)``。"""
    current = to_cst(now or now_utc())
    start_local = datetime(current.year, current.month, current.day, 0, 0, 0)
    end_local = start_local + timedelta(days=1)
    return _cst_to_utc_naive(start_local), _cst_to_utc_naive(end_local)


def cst_date_range_utc(from_date: str | None, to_date: str | None) -> tuple[datetime, datetime]:
    """``from``/``to`` 为北京时间自然日，返回 ``[start_utc, end_utc)``。

    缺省值：``to`` 为今天，``from`` 为 ``to`` 前 6 天（共 7 天）。
    """
    today = to_cst(now_utc())
    end_day = date.fromisoformat(to_date.strip()) if to_date else date(today.year, today.month, today.day)
    start_day = (
        date.fromisoformat(from_date.strip())
        if from_date
        else end_day - timedelta(days=6)
    )
    start_local = datetime(start_day.year, start_day.month, start_day.day, 0, 0, 0)
    end_local = datetime(end_day.year, end_day.month, end_day.day, 0, 0, 0) + timedelta(days=1)
    return _cst_to_utc_naive(start_local), _cst_to_utc_naive(end_local)
