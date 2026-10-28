"""匿名访客、收藏、隐藏、偏好、举报的请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from ..constants import REPORT_REASON_LABELS
from .ad import AdCardOut

__all__ = [
    "FavoriteIn",
    "FavoriteListOut",
    "FavoriteToggleOut",
    "FollowupIn",
    "HideIn",
    "HideListOut",
    "PreferenceIn",
    "PreferenceOut",
    "PreferenceSaveOut",
    "ReportIn",
    "ReportLookupOut",
    "ReportMineItem",
    "ReportMineOut",
    "ReportOut",
    "VisitorDataDeletedOut",
    "VisitorLimitsOut",
    "VisitorMeOut",
]


class PreferenceOut(BaseModel):
    """偏好：感兴趣的一级类别 id 列表 + 常看城市。"""

    categories: list[int] = []
    city: str | None = None


class VisitorLimitsOut(BaseModel):
    """单设备上限。"""

    favorites: int = 200
    hides: int = 500


class VisitorMeOut(BaseModel):
    """``GET /api/visitor/me``：匿名标识 + 收藏/隐藏/偏好 + 上限。"""

    visitor_id: str
    favorite_ids: list[int] = []
    hide_ids: list[int] = []
    preference: PreferenceOut = PreferenceOut()
    counts: dict[str, int] = {}
    limits: VisitorLimitsOut = VisitorLimitsOut()


class FavoriteIn(BaseModel):
    """收藏/隐藏请求体。"""

    ad_id: int


class HideIn(BaseModel):
    """隐藏请求体。"""

    ad_id: int


class FavoriteToggleOut(BaseModel):
    """收藏结果（重复收藏幂等）。"""

    ok: bool = True
    count: int = 0
    limit: int = 200
    message: str = ""


class FavoriteListOut(BaseModel):
    """收藏列表：过期条目保留展示但分组。"""

    items: list[AdCardOut] = []
    groups: dict[str, list[AdCardOut]] = {}


class HideListOut(BaseModel):
    """隐藏列表（含已过期，用于恢复）。"""

    items: list[AdCardOut] = []


class PreferenceIn(BaseModel):
    """保存偏好（全部不选 = 关闭个性化）。"""

    categories: list[int] = Field(default_factory=list, max_length=6)
    city: str | None = Field(default=None, max_length=20)


class PreferenceSaveOut(PreferenceOut):
    """保存偏好的结果。"""

    ok: bool = True


class VisitorDataDeletedOut(BaseModel):
    """清空本设备数据的结果。"""

    ok: bool = True
    deleted: dict[str, int] = {}


class ReportIn(BaseModel):
    """举报请求体。"""

    ad_id: int
    reason_code: str = Field(min_length=1, max_length=32)
    detail: str | None = Field(default=None, max_length=200)

    @field_validator("reason_code")
    @classmethod
    def _check_reason(cls, value: str) -> str:
        if value not in REPORT_REASON_LABELS:
            raise ValueError("请选择有效的举报原因")
        return value

    @field_validator("detail")
    @classmethod
    def _strip_detail(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class ReportOut(BaseModel):
    """举报提交结果（含 24h 合并标记）。"""

    code: str
    status: str
    duplicate: bool = False
    message: str = "已收到，我们会在 48 小时内处理"


class ReportLookupOut(BaseModel):
    """按举报码查询（不含举报人与处理人信息）。"""

    code: str
    ad_id: int
    ad_title: str = ""
    reason_label: str = ""
    status: str
    status_text: str = ""
    created_at: str | None = None
    handled_at: str | None = None
    conclusion: str | None = None


class ReportMineItem(ReportLookupOut):
    """本设备举报列表项。"""


class ReportMineOut(BaseModel):
    """本设备举报列表。"""

    items: list[ReportMineItem] = []


class FollowupIn(BaseModel):
    """举报"仍有疑问"追加说明（≤200 字）。"""

    note: str = Field(min_length=1, max_length=200)

    @field_validator("note")
    @classmethod
    def _strip_note(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("请填写补充说明")
        return text
