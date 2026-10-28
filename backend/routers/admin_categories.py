"""管理端分类与标签维护（一级类别只读，标签可增改停用）。"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import Ad, AdTag, AdminUser, Category, Tag
from ..schemas.category import AdminCategoryOut, AdminTagOut, TagCreateIn, TagUpdateIn
from ..services.ads import api_error
from ..utils.timeutil import now_utc

router = APIRouter(tags=["admin-categories"])

audit_log = logging.getLogger("adx.audit")


@router.get("/api/admin/categories", response_model=list[AdminCategoryOut])
def list_categories(
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> list[AdminCategoryOut]:
    """6 个一级类别（只读）+ 全部标签（含停用）+ 每个标签被引用数。"""
    categories = db.execute(select(Category).order_by(Category.sort_order, Category.id)).scalars().all()
    usage_rows = db.execute(select(AdTag.tag_id, func.count(AdTag.ad_id)).group_by(AdTag.tag_id)).all()
    usage = {int(row[0]): int(row[1]) for row in usage_rows}

    result: list[AdminCategoryOut] = []
    for category in categories:
        tags = db.execute(
            select(Tag).where(Tag.category_id == category.id).order_by(Tag.sort_order, Tag.id)
        ).scalars().all()
        result.append(
            AdminCategoryOut(
                id=category.id,
                slug=category.slug,
                name=category.name,
                is_active=category.is_active,
                tags=[
                    AdminTagOut(
                        id=tag.id,
                        name=tag.name,
                        slug=tag.slug,
                        sort_order=tag.sort_order,
                        is_active=tag.is_active,
                        ad_count=usage.get(tag.id, 0),
                    )
                    for tag in tags
                ],
            )
        )
    return result


@router.post("/api/admin/categories/{category_id}/tags", response_model=AdminTagOut)
def create_tag(
    category_id: int,
    payload: TagCreateIn,
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> AdminTagOut:
    """新增二级标签（slug 自动生成，避免中文 slug 造成路由困扰）。"""
    category = db.get(Category, category_id)
    if category is None:
        raise api_error(404, "CATEGORY_NOT_FOUND", "该一级类别不存在")

    duplicated = db.execute(
        select(Tag).where(Tag.category_id == category_id, Tag.name == payload.name)
    ).scalars().first()
    if duplicated is not None:
        raise api_error(409, "TAG_EXISTS", "该类别下已存在同名标签")

    tag = Tag(
        category_id=category_id,
        name=payload.name,
        slug=f"tag-{uuid.uuid4().hex[:10]}",
        sort_order=payload.sort_order,
        is_active=True,
        created_at=now_utc(),
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    audit_log.info("tag_create category_id=%s tag_id=%s", category_id, tag.id)
    return AdminTagOut(
        id=tag.id,
        name=tag.name,
        slug=tag.slug,
        sort_order=tag.sort_order,
        is_active=tag.is_active,
        ad_count=0,
    )


@router.patch("/api/admin/tags/{tag_id}", response_model=AdminTagOut)
def update_tag(
    tag_id: int,
    payload: TagUpdateIn,
    admin: AdminUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> AdminTagOut:
    """改名/排序/停用标签；停用后不影响已发布广告，仅不再出现在新建表单与筛选项。"""
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise api_error(404, "TAG_NOT_FOUND", "该标签不存在")

    data = payload.model_dump(exclude_unset=True)
    if data.get("name"):
        duplicated = db.execute(
            select(Tag).where(
                Tag.category_id == tag.category_id, Tag.name == data["name"], Tag.id != tag.id
            )
        ).scalars().first()
        if duplicated is not None:
            raise api_error(409, "TAG_EXISTS", "该类别下已存在同名标签")
        tag.name = str(data["name"])
    if data.get("sort_order") is not None:
        tag.sort_order = int(data["sort_order"])
    if data.get("is_active") is not None:
        tag.is_active = bool(data["is_active"])
    db.commit()
    db.refresh(tag)

    usage = int(
        db.execute(select(func.count()).select_from(AdTag).where(AdTag.tag_id == tag.id)).scalar_one()
    )
    audit_log.info("tag_update tag_id=%s active=%s", tag.id, tag.is_active)
    return AdminTagOut(
        id=tag.id,
        name=tag.name,
        slug=tag.slug,
        sort_order=tag.sort_order,
        is_active=tag.is_active,
        ad_count=usage,
    )


__all__ = ["Ad", "router"]
