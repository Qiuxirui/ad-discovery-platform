"""事件上报服务：所有去重规则在服务端实现（前端只报原始事实）。

去重口径见架构 §6.5：
- ``impression``：``(session_id, ad_id)`` 只计 1 次；
- ``detail_view``：``(session_id, ad_id)`` 30 分钟内只计 1 次；
- ``link_click``：``(visitor_id, ad_id)`` 10 秒内只计 1 次；当日（北京）≥20 次改写为
  ``link_click_suppressed`` 落库便于审计，原事件不计；
- ``favorite`` / ``hide``：``(visitor_id, ad_id, type)`` 唯一；
- ``report``：``(visitor_id, ad_id)`` 24 小时内只计 1 次；
- ``page_view`` / ``external_blocked`` / ``unfavorite`` / ``link_click_suppressed`` 不去重。
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..constants import EVENT_TYPES, PAGE_IDS
from ..models import Ad, Event
from ..schemas.event import EventItemIn
from ..utils.timeutil import now_utc, today_cst_range_utc

__all__ = ["EventService", "IngestResult"]

audit_log = logging.getLogger("adx.audit")

CLICK_DAILY_CAP = 20
CLICK_DEDUPE_SECONDS = 10
DETAIL_DEDUPE_MINUTES = 30
REPORT_DEDUPE_HOURS = 24

NO_DEDUPE_TYPES = {"page_view", "external_blocked", "unfavorite", "link_click_suppressed"}


@dataclass(slots=True)
class IngestResult:
    """批量上报结果。"""

    accepted: int = 0
    dropped: list[dict[str, object]] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {"accepted": self.accepted, "dropped": self.dropped}


def _existing(db: Session, **filters) -> bool:  # noqa: ANN003
    stmt = select(func.count()).select_from(Event)
    for key, value in filters.items():
        stmt = stmt.where(getattr(Event, key) == value)
    return bool(db.execute(stmt).scalar_one())


class EventService:
    """事件入库与去重。"""

    @staticmethod
    def insert_single(
        db: Session,
        *,
        visitor_id: str,
        event_type: str,
        ad_id: int | None,
        page: str = "detail",
        session_id: str | None = None,
        position: int | None = None,
        meta: dict[str, object] | None = None,
    ) -> Event:
        """直接写入单条事件（供服务端内部埋点使用）。"""
        event = Event(
            id=str(uuid.uuid4()),
            event_type=event_type,
            ad_id=ad_id,
            visitor_id=visitor_id,
            session_id=session_id or str(uuid.uuid4()),
            ts=now_utc(),
            page=page if page in PAGE_IDS else "detail",
            position=position,
            meta=json.dumps(meta, ensure_ascii=False) if meta else None,
        )
        db.add(event)
        return event

    @staticmethod
    def ingest(db: Session, visitor_id: str, session_id: str, items: list[EventItemIn]) -> IngestResult:
        """逐条校验 + 去重；单个事件失败不影响其余事件。"""
        result = IngestResult()
        current = now_utc()

        for index, item in enumerate(items):
            event_type = (item.event_type or "").strip()
            if event_type not in EVENT_TYPES:
                result.dropped.append({"index": index, "reason": "invalid_type"})
                continue

            if item.page not in PAGE_IDS:
                result.dropped.append({"index": index, "reason": "invalid_page"})
                continue

            ad_id = item.ad_id
            if event_type == "page_view":
                ad_id = None
            else:
                if ad_id is None:
                    result.dropped.append({"index": index, "reason": "ad_id_required"})
                    continue
                exists = db.execute(select(func.count()).select_from(Ad).where(Ad.id == ad_id)).scalar_one()
                if not exists:
                    result.dropped.append({"index": index, "reason": "ad_not_found"})
                    continue

            stored_type = event_type

            if event_type == "impression":
                if _existing(db, session_id=session_id, ad_id=ad_id, event_type="impression"):
                    result.dropped.append({"index": index, "reason": "dedupe_session"})
                    continue

            elif event_type == "detail_view":
                window_start = current - timedelta(minutes=DETAIL_DEDUPE_MINUTES)
                hit = db.execute(
                    select(func.count())
                    .select_from(Event)
                    .where(
                        Event.session_id == session_id,
                        Event.ad_id == ad_id,
                        Event.event_type == "detail_view",
                        Event.ts >= window_start,
                    )
                ).scalar_one()
                if hit:
                    result.dropped.append({"index": index, "reason": "dedupe_session_30m"})
                    continue

            elif event_type == "link_click":
                window_start = current - timedelta(seconds=CLICK_DEDUPE_SECONDS)
                hit = db.execute(
                    select(func.count())
                    .select_from(Event)
                    .where(
                        Event.visitor_id == visitor_id,
                        Event.ad_id == ad_id,
                        Event.event_type == "link_click",
                        Event.ts >= window_start,
                    )
                ).scalar_one()
                if hit:
                    result.dropped.append({"index": index, "reason": "dedupe_10s"})
                    continue
                start, end = today_cst_range_utc(current)
                today_clicks = db.execute(
                    select(func.count())
                    .select_from(Event)
                    .where(
                        Event.visitor_id == visitor_id,
                        Event.ad_id == ad_id,
                        Event.event_type == "link_click",
                        Event.ts >= start,
                        Event.ts < end,
                    )
                ).scalar_one()
                if today_clicks >= CLICK_DAILY_CAP:
                    stored_type = "link_click_suppressed"

            elif event_type in ("favorite", "hide"):
                hit = db.execute(
                    select(func.count())
                    .select_from(Event)
                    .where(
                        Event.visitor_id == visitor_id,
                        Event.ad_id == ad_id,
                        Event.event_type == event_type,
                    )
                ).scalar_one()
                if hit:
                    result.dropped.append({"index": index, "reason": "dedupe_unique"})
                    continue

            elif event_type == "report":
                window_start = current - timedelta(hours=REPORT_DEDUPE_HOURS)
                hit = db.execute(
                    select(func.count())
                    .select_from(Event)
                    .where(
                        Event.visitor_id == visitor_id,
                        Event.ad_id == ad_id,
                        Event.event_type == "report",
                        Event.ts >= window_start,
                    )
                ).scalar_one()
                if hit:
                    result.dropped.append({"index": index, "reason": "dedupe_24h"})
                    continue

            meta = item.meta
            if stored_type != event_type and isinstance(meta, dict):
                meta = {**meta, "suppressed_from": event_type}

            db.add(
                Event(
                    id=str(uuid.uuid4()),
                    event_type=stored_type,
                    ad_id=ad_id,
                    visitor_id=visitor_id,
                    session_id=session_id,
                    ts=current,
                    page=item.page,
                    position=item.position,
                    meta=json.dumps(meta, ensure_ascii=False) if meta else None,
                )
            )
            db.flush()
            result.accepted += 1

        db.commit()
        return result
