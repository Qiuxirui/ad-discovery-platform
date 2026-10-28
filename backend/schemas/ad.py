"""广告相关请求/响应模型。

所有时间字段输出为带 ``Z`` 的 ISO 字符串；同时预计算北京时间的自然日、
剩余天数与"即将结束"标记，前端不做任何时区换算。
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from ..constants import CITIES
from .category import TagOut

__all__ = [
    "AdCardOut",
    "AdCreateIn",
    "AdDetailOut",
    "AdListOut",
    "AdManageEnvelope",
    "AdManageOut",
    "AdPrecheckOut",
    "AdUpdateIn",
    "MerchantAdListOut",
    "MerchantBrief",
    "OutboundOut",
    "RelatedAdOut",
]


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


class MerchantBrief(BaseModel):
    """详情页商家信息块（P0-T-02，缺失项显示"未提供"由前端兜底）。"""

    id: int
    name: str
    city: str
    main_category_name: str | None = None
    joined_at: str | None = None
    active_ad_count: int = 0


class AdCardOut(BaseModel):
    """列表/收藏卡片。"""

    id: int
    title: str
    price_text: str | None = None
    promo_condition: str | None = None
    city: str
    merchant_id: int
    merchant_name: str
    image_path: str
    category_id: int
    category_slug: str
    category_name: str
    tags: list[TagOut] = []
    valid_from_local_date: str | None = None
    valid_to_local_date: str | None = None
    days_left: int = 0
    expiring_soon: bool = False
    is_favorited: bool = False
    is_hidden: bool = False
    published_at: str | None = None
    status: str = "active"
    is_expired: bool = False


class AdDetailOut(AdCardOut):
    """详情页全字段。"""

    description: str
    restriction: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    landing_domain: str
    merchant: MerchantBrief
    related: list[AdCardOut] = []


class RelatedAdOut(BaseModel):
    """同类推荐（同类别 + 同城市）。"""

    items: list[AdCardOut] = []


class OutboundOut(BaseModel):
    """外链中间页数据；阻断时 ``url`` 为 ``None``。"""

    allowed: bool
    domain: str = ""
    url: str | None = None
    block_reason: str | None = None
    block_code: str | None = None


class AdListOut(BaseModel):
    """列表分页响应。"""

    items: list[AdCardOut] = []
    page: int = 1
    page_size: int = 24
    total: int = 0
    has_more: bool = False


class AdPrecheckOut(BaseModel):
    """系统预检结论（回显商家端）。"""

    passed: bool = True
    code: str = ""
    reason: str = ""
    banned_words: list[str] = []
    url_safe: bool = True


class AdManageOut(BaseModel):
    """商家端广告管理项（含全部可编辑字段）。"""

    id: int
    title: str
    description: str
    category_id: int
    category_slug: str
    category_name: str
    tags: list[TagOut] = []
    tag_ids: list[int] = []
    city: str
    price_text: str | None = None
    promo_condition: str | None = None
    restriction: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    valid_from_local_date: str | None = None
    valid_to_local_date: str | None = None
    days_left: int = 0
    expiring_soon: bool = False
    landing_url: str
    landing_domain: str
    image_path: str
    status: str
    status_label: str
    submitted_at: str | None = None
    published_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    reject_reason_code: str | None = None
    reject_reason: str | None = None
    offline_reason: str | None = None
    precheck_note: str | None = None


class AdCreateIn(BaseModel):
    """新建广告（``submit=True`` 时直接提交审核）。"""

    title: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=500)
    category_id: int
    tag_ids: list[int] = Field(default_factory=list)
    city: str = Field(min_length=1, max_length=20)
    price_text: str | None = Field(default=None, max_length=30)
    promo_condition: str | None = Field(default=None, max_length=100)
    restriction: str | None = Field(default=None, max_length=200)
    valid_from: str
    valid_to: str
    landing_url: str = Field(min_length=1, max_length=500)
    image_path: str | None = Field(default=None, max_length=200)
    submit: bool = False

    @field_validator("title", "description")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("该字段不能为空")
        return text

    @field_validator("city")
    @classmethod
    def _check_city(cls, value: str) -> str:
        city = value.strip()
        if city not in CITIES:
            raise ValueError("请选择列表中的服务城市")
        return city

    @field_validator("price_text", "promo_condition", "restriction", "image_path")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        return _clean_optional(value)

    @field_validator("tag_ids")
    @classmethod
    def _check_tags(cls, value: list[int]) -> list[int]:
        unique: list[int] = []
        for item in value:
            if item not in unique:
                unique.append(item)
        if len(unique) > 3:
            raise ValueError("二级标签最多选 3 个")
        return unique

    @model_validator(mode="after")
    def _check_dates(self) -> "AdCreateIn":
        if self.valid_to < self.valid_from:
            raise ValueError("有效期结束日不能早于开始日")
        return self


class AdUpdateIn(BaseModel):
    """编辑广告（部分字段；`active` 改核心字段会回到待审核）。"""

    title: str | None = Field(default=None, min_length=1, max_length=40)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    category_id: int | None = None
    tag_ids: list[int] | None = None
    city: str | None = Field(default=None, max_length=20)
    price_text: str | None = Field(default=None, max_length=30)
    promo_condition: str | None = Field(default=None, max_length=100)
    restriction: str | None = Field(default=None, max_length=200)
    valid_from: str | None = None
    valid_to: str | None = None
    landing_url: str | None = Field(default=None, max_length=500)
    image_path: str | None = Field(default=None, max_length=200)

    @field_validator("title", "description")
    @classmethod
    def _strip_optional_required(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("该字段不能为空")
        return text

    @field_validator("city")
    @classmethod
    def _check_optional_city(cls, value: str | None) -> str | None:
        if value is None:
            return None
        city = value.strip()
        if city not in CITIES:
            raise ValueError("请选择列表中的服务城市")
        return city

    @field_validator("price_text", "promo_condition", "restriction", "image_path")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        return _clean_optional(value)

    @field_validator("tag_ids")
    @classmethod
    def _check_optional_tags(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        unique: list[int] = []
        for item in value:
            if item not in unique:
                unique.append(item)
        if len(unique) > 3:
            raise ValueError("二级标签最多选 3 个")
        return unique


class AdManageEnvelope(BaseModel):
    """商家端单条操作结果。"""

    ad: AdManageOut
    became_pending: bool = False
    precheck: AdPrecheckOut | None = None
    message: str = ""


class MerchantAdListOut(BaseModel):
    """商家端"我的广告"列表 + 状态计数。"""

    items: list[AdManageOut] = []
    counts: dict[str, int] = {}
    page: int = 1
    page_size: int = 24
    total: int = 0
