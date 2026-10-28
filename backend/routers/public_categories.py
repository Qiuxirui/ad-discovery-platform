"""公开类别接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_visitor_id  # noqa: F401 - 仅用于声明匿名身份依赖
from ..models import Ad, Category, Tag
from ..schemas.category import CategoryOut, TagOut
from ..services.visibility import visible_ads_stmt

router = APIRouter(tags=["categories"])


@router.get("/api/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryOut]:
    """6 个一级类别 + 各自启用的二级标签 + 在架条数（可见性统一走 helper）。"""
    counted = db.execute(
        visible_ads_stmt().with_only_columns(Ad.category_id, func.count(Ad.id).label("cnt")).group_by(Ad.category_id)
    ).all()
    count_map = {row[0]: int(row[1]) for row in counted}

    categories = db.execute(
        select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order, Category.id)
    ).scalars().all()

    result: list[CategoryOut] = []
    for category in categories:
        tags = db.execute(
            select(Tag)
            .where(Tag.category_id == category.id, Tag.is_active.is_(True))
            .order_by(Tag.sort_order, Tag.id)
        ).scalars().all()
        result.append(
            CategoryOut(
                id=category.id,
                slug=category.slug,
                name=category.name,
                intro=category.intro,
                sort_order=category.sort_order,
                active_count=count_map.get(category.id, 0),
                tags=[
                    TagOut(id=tag.id, name=tag.name, slug=tag.slug, sort_order=tag.sort_order)
                    for tag in tags
                ],
            )
        )
    return result
