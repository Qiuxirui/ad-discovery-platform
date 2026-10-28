"""事件上报的请求/响应模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

__all__ = ["EventAcceptedOut", "EventBatchIn", "EventItemIn"]


class EventItemIn(BaseModel):
    """单条事件（前端只报事实，去重由服务端负责）。"""

    event_type: str = Field(min_length=1, max_length=32)
    ad_id: int | None = None
    page: str = Field(min_length=1, max_length=16)
    position: int | None = None
    meta: dict[str, Any] | None = None


class EventBatchIn(BaseModel):
    """批量上报（单批上限 20 条，超出 422）。"""

    session_id: str = Field(min_length=1, max_length=36)
    events: list[EventItemIn] = Field(default_factory=list, max_length=20)


class EventAcceptedOut(BaseModel):
    """上报结果：落库条数 + 逐条丢弃原因。"""

    accepted: int = 0
    dropped: list[dict[str, Any]] = []
