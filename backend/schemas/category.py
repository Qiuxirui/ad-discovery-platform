"""类别与标签的请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from .common import BaseORMModel

__all__ = [
    "AdminCategoryOut",
    "AdminTagOut",
    "CategoryOut",
    "TagCreateIn",
    "TagOut",
    "TagUpdateIn",
]


class TagOut(BaseORMModel):
    """二级标签（公开字段）。"""

    id: int
    name: str
    slug: str
    sort_order: int = 0


class CategoryOut(BaseORMModel):
    """一级类别 + 在架条数 + 标签列表。"""

    id: int
    slug: str
    name: str
    intro: str | None = None
    sort_order: int = 0
    active_count: int = 0
    tags: list[TagOut] = []


class AdminTagOut(TagOut):
    """标签（后台可见 ``is_active`` 与引用数）。"""

    is_active: bool = True
    ad_count: int = 0


class AdminCategoryOut(BaseORMModel):
    """后台类别视图（含停用标签）。"""

    id: int
    slug: str
    name: str
    is_active: bool = True
    tags: list[AdminTagOut] = []


class TagCreateIn(BaseModel):
    """新增标签。"""

    name: str = Field(min_length=1, max_length=20)
    sort_order: int = 0

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("标签名不能为空")
        return name


class TagUpdateIn(BaseModel):
    """修改标签（部分字段）。"""

    name: str | None = Field(default=None, min_length=1, max_length=20)
    sort_order: int | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def _strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = value.strip()
        if not name:
            raise ValueError("标签名不能为空")
        return name
