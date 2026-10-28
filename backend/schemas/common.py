"""通用响应结构：错误体、分页、OK 包装。"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

__all__ = ["ApiError", "BaseORMModel", "IdOut", "MessageOut", "OkOut", "Page", "paginate"]


class BaseORMModel(BaseModel):
    """允许从 ORM 对象直接构造。"""

    model_config = ConfigDict(from_attributes=True)


class ApiError(BaseModel):
    """统一错误体：``{"detail": "中文说明", "code": "MACHINE_CODE"}``。"""

    detail: str
    code: str
    fields: list[dict[str, str]] | None = None


class OkOut(BaseModel):
    """最小成功响应。"""

    ok: bool = True


class IdOut(BaseModel):
    """仅返回主键。"""

    id: int


class MessageOut(BaseModel):
    """带中文提示的成功响应。"""

    ok: bool = True
    message: str = ""


class Page(BaseModel, Generic[T]):
    """分页响应。"""

    items: list[T] = []
    page: int = 1
    page_size: int = 24
    total: int = 0
    has_more: bool = False


def paginate(total: int, page: int, page_size: int) -> dict[str, int | bool]:
    """计算分页元信息。"""
    safe_page = max(1, page)
    return {
        "page": safe_page,
        "page_size": page_size,
        "total": total,
        "has_more": safe_page * page_size < total,
    }
