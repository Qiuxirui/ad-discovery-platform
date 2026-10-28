"""后台定时任务：过期下架与预约生效（PRD 6.1 迁移 8 / 9）。

生命周期挂在 FastAPI ``lifespan`` 上：启动即跑一次，之后每 60 秒一次；
所有异常必须捕获，避免协程静默死掉。查询层的可见性双保险与定时任务互不依赖。
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import SessionLocal
from .models import Ad
from .services.ads import log_review
from .utils.timeutil import now_utc

__all__ = ["expire_ads", "activate_ads", "run_once", "scheduler_loop"]

audit_log = logging.getLogger("adx.audit")

EXPIRED_STATUSES = ("active", "scheduled")


def expire_ads(db: Session | None = None) -> int:
    """``active|scheduled`` 且 ``valid_to<=now`` → ``expired``（写 reviews/system_expire）。"""
    session = db or SessionLocal()
    own_session = db is None
    try:
        current = now_utc()
        rows = (
            session.execute(
                select(Ad).where(Ad.status.in_(EXPIRED_STATUSES), Ad.valid_to <= current)
            )
            .unique()
            .scalars()
            .all()
        )
        for ad in rows:
            ad.status = "expired"
            ad.updated_at = current
            log_review(
                session,
                ad,
                "system_expire",
                "system",
                None,
                reason="到达有效期结束时间，系统自动置为已过期",
            )
            audit_log.info("scheduler_expire ad_id=%s", ad.id)
        if rows:
            session.commit()
        return len(rows)
    except Exception:  # noqa: BLE001 - 定时任务不得抛出
        session.rollback()
        audit_log.exception("scheduler_expire_failed")
        return 0
    finally:
        if own_session:
            session.close()


def activate_ads(db: Session | None = None) -> int:
    """``scheduled`` 且 ``valid_from<=now<valid_to`` → ``active``（写 reviews/system_activate）。"""
    session = db or SessionLocal()
    own_session = db is None
    try:
        current = now_utc()
        rows = (
            session.execute(
                select(Ad).where(
                    Ad.status == "scheduled", Ad.valid_from <= current, Ad.valid_to > current
                )
            )
            .unique()
            .scalars()
            .all()
        )
        for ad in rows:
            ad.status = "active"
            ad.published_at = current
            ad.updated_at = current
            log_review(
                session,
                ad,
                "system_activate",
                "system",
                None,
                reason="到达有效期开始时间，系统自动上线",
            )
            audit_log.info("scheduler_activate ad_id=%s", ad.id)
        if rows:
            session.commit()
        return len(rows)
    except Exception:  # noqa: BLE001
        session.rollback()
        audit_log.exception("scheduler_activate_failed")
        return 0
    finally:
        if own_session:
            session.close()


def run_once() -> tuple[int, int]:
    """执行一轮任务，返回 ``(置为过期的条数, 置为在架的条数)``。"""
    expired = expire_ads()
    activated = activate_ads()
    return expired, activated


async def scheduler_loop(interval_seconds: int | None = None) -> None:
    """后台协程：启动即跑一次，之后按间隔循环。"""
    settings = get_settings()
    interval = interval_seconds or settings.scheduler_interval_seconds
    while True:
        try:
            expired, activated = run_once()
            if expired or activated:
                audit_log.info(
                    "scheduler_round expired=%s activated=%s", expired, activated
                )
        except Exception:  # noqa: BLE001 - 协程必须活着
            audit_log.exception("scheduler_round_failed")
        await asyncio.sleep(interval)
