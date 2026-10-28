"""管理端请求/响应模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .ad import AdManageOut
from .auth import AdminOut
from .common import BaseORMModel

__all__ = [
    "AdminAdListOut",
    "AdminAdRowOut",
    "AdminEnvelope",
    "AdminReportListOut",
    "AdminReportRowOut",
    "AdminSummaryOut",
    "AdEnvelope",
    "ApproveIn",
    "DismissIn",
    "EditApproveIn",
    "MerchantNoteIn",
    "MerchantRowOut",
    "MerchantStatusIn",
    "MerchantVerifyIn",
    "OfflineIn",
    "RejectIn",
    "RestoreIn",
    "ResolveIn",
    "ReviewQueueItemOut",
    "ReviewQueueMerchantOut",
    "ReviewQueueOut",
    "ReviewTimelineItemOut",
    "ReviewTimelineOut",
]


class ApproveIn(BaseModel):
    """通过审核（备注可选）。"""

    note: str | None = Field(default=None, max_length=300)


class AdminEnvelope(BaseModel):
    """管理员登录结果（与商家端 ``{merchant}`` 结构对齐，见 §5.7）。"""

    admin: AdminOut


class RejectIn(BaseModel):
    """拒绝（原因必填）。"""

    reason_code: str = Field(min_length=1, max_length=32)
    reason_note: str | None = Field(default=None, max_length=300)


class EditApproveIn(BaseModel):
    """编辑后通过（记录字段前后值）。"""

    changes: dict[str, Any] = Field(default_factory=dict)
    note: str | None = Field(default=None, max_length=300)


class OfflineIn(BaseModel):
    """下架请求（原因由服务层校验，缺失或全空白返回 ``REASON_REQUIRED``）。"""

    reason: str | None = Field(default=None, max_length=300)


class RestoreIn(BaseModel):
    """整改重提（offline → pending）。"""

    note: str | None = Field(default=None, max_length=300)


class AdEnvelope(BaseModel):
    """单条广告操作结果。"""

    ad: AdManageOut
    changes: dict[str, Any] = {}
    message: str = ""


class ReviewQueueMerchantOut(BaseModel):
    """审核卡片的商家历史。"""

    id: int
    name: str
    total_submitted: int = 0
    rejected_count: int = 0
    report_resolved_count: int = 0
    joined_at: str | None = None


class ReviewQueueItemOut(BaseModel):
    """审核队列条目（含全部提交字段 + 商家历史 + 等待时长 + 预检结果）。

    ``precheck``：提交时的预检留痕（人话，原样存库）；
    ``precheck_passed`` / ``precheck_code`` / ``precheck_reason``：读取队列时**重新预检**的结果，
    便于前端按机器码分支（``BANNED_INDUSTRY`` / ``URL_SHORTENER`` / ``DATE_*`` / ``PRECHECK_PASSED``），
    不必靠正则匹配中文。
    """

    ad: AdManageOut
    merchant: ReviewQueueMerchantOut
    precheck: str | None = None
    precheck_passed: bool = True
    precheck_code: str = "PRECHECK_PASSED"
    precheck_reason: str = ""
    waiting_minutes: int = 0
    submitted_at: str | None = None


class ReviewQueueOut(BaseModel):
    """审核队列响应。"""

    items: list[ReviewQueueItemOut] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    today_processed: int = 0


class ReviewTimelineItemOut(BaseModel):
    """操作时间线条目。"""

    action: str
    action_label: str = ""
    actor_type: str
    actor_name: str = ""
    reason: str | None = None
    changes: dict[str, Any] | None = None
    created_at: str | None = None


class ReviewTimelineOut(BaseModel):
    """操作时间线（只增不改不删）。"""

    items: list[ReviewTimelineItemOut] = []


class AdminAdRowOut(BaseModel):
    """广告台账行。"""

    id: int
    title: str
    merchant_id: int
    merchant_name: str
    category_name: str
    status: str
    status_label: str
    valid_to_local_date: str | None = None
    days_left: int = 0
    impressions: int = 0
    detail_views: int = 0
    link_clicks: int = 0
    reports: int = 0
    offline_reason: str | None = None
    updated_at: str | None = None


class AdminAdListOut(BaseModel):
    """广告台账列表。"""

    items: list[AdminAdRowOut] = []
    counts: dict[str, int] = {}
    total: int = 0
    page: int = 1
    page_size: int = 20


class AdminReportRowOut(BaseORMModel):
    """举报处理行。"""

    id: int
    code: str
    ad_id: int
    ad_title: str = ""
    ad_snapshot: dict[str, Any] | None = None
    reason_code: str
    reason_label: str = ""
    detail: str | None = None
    status: str
    status_label: str = ""
    created_at: str | None = None
    handled_at: str | None = None
    overdue: bool = False
    admin_note: str | None = None
    followups: list[dict[str, Any]] = []


class AdminReportListOut(BaseModel):
    """举报列表 + 近 7 天统计。"""

    items: list[AdminReportRowOut] = []
    week_stats: dict[str, Any] = {}
    total: int = 0
    page: int = 1
    page_size: int = 20


class ResolveIn(BaseModel):
    """举报判定成立（下架或要求整改）。"""

    action: str = Field(default="offline", max_length=16)
    note: str = Field(min_length=1, max_length=300)


class DismissIn(BaseModel):
    """举报判定不成立。"""

    note: str = Field(min_length=1, max_length=300)


class MerchantRowOut(BaseModel):
    """商家管理行。"""

    id: int
    name: str
    contact_name: str
    phone: str
    email: str
    city: str
    status: str
    verified: bool = False
    active_ads: int = 0
    total_submitted: int = 0
    rejected_count: int = 0
    report_resolved_30d: int = 0
    risk_flag: bool = False
    admin_note: str | None = None
    created_at: str | None = None


class MerchantStatusIn(BaseModel):
    """停用/启用商家。"""

    status: str = Field(min_length=1, max_length=16)
    note: str | None = Field(default=None, max_length=200)


class MerchantVerifyIn(BaseModel):
    """核验标记（Q2 裁决）。"""

    verified: bool


class MerchantNoteIn(BaseModel):
    """管理员备注。"""

    admin_note: str | None = Field(default=None, max_length=200)


class AdminSummaryOut(BaseModel):
    """运营首页数字（必须与对应列表过滤结果一致）。"""

    pending_ads: int = 0
    pending_reports: int = 0
    sla_overdue_reports: int = 0
    today_events: int = 0
    today_processed_ads: int = 0
    week_resolved_reports: int = 0
