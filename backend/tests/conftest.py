"""pytest 夹具：临时数据库 + 最小可测数据集 + TestClient。

``ADX_DB_PATH`` 必须在导入任何 ``backend.*`` 模块之前设置（引擎在导入期创建）。
测试不启动 lifespan，因此不会起后台定时任务（需要时直接调用 ``scheduler.run_once``）。
"""

from __future__ import annotations

import os
import tempfile
from datetime import timedelta
from pathlib import Path

_TEMP_DIR = Path(tempfile.mkdtemp(prefix="adx-test-"))
os.environ["ADX_DB_PATH"] = str(_TEMP_DIR / "adx_test.db")
os.environ["ADX_SECRET"] = "unit-test-secret-key-0123456789abcdef0123456789"
os.environ["ADX_SCHEDULER_ENABLED"] = "0"
os.environ["ADX_ADMIN_PASSWORD"] = "admin-pass-2026"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from backend.database import Base, SessionLocal, engine  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models import (  # noqa: E402
    Ad,
    AdTag,
    AdminUser,
    Category,
    Merchant,
    Tag,
)
from backend.security import hash_password  # noqa: E402
from backend.utils.timeutil import now_utc  # noqa: E402

ADMIN_PASSWORD = "admin-pass-2026"
MERCHANT_PASSWORD = "merchant-pass-2026"


def _create_ad(
    db: Session,
    *,
    merchant_id: int,
    category_id: int,
    title: str,
    tag_ids: list[int],
    status: str,
    valid_from,
    valid_to,
    landing_url: str = "https://www.example.com/ad",
    price_text: str | None = "到手 99 元",
) -> Ad:
    current = now_utc()
    ad = Ad(
        merchant_id=merchant_id,
        category_id=category_id,
        title=title,
        description=f"{title} 的详细说明，用于测试。",
        city="全国",
        price_text=price_text,
        promo_condition=None,
        restriction=None,
        valid_from=valid_from,
        valid_to=valid_to,
        landing_url=landing_url,
        landing_domain="www.example.com",
        image_path="/static/covers/ad-1.svg",
        status=status,
        precheck_note="预检通过",
        submitted_at=current - timedelta(days=3) if status != "draft" else None,
        published_at=valid_from if status in ("active", "expired", "offline") else None,
        created_at=current - timedelta(days=5),
        updated_at=current - timedelta(days=2),
    )
    db.add(ad)
    db.flush()
    for tag_id in tag_ids:
        db.add(AdTag(ad_id=ad.id, tag_id=tag_id))
    db.flush()
    return ad


def _seed(db: Session) -> dict[str, object]:
    current = now_utc()
    digital = Category(slug="digital", name="数码与家电", intro="数码测试类", sort_order=1, is_active=True, created_at=current)
    local = Category(slug="local-service", name="本地生活服务", intro="本地测试类", sort_order=2, is_active=True, created_at=current)
    db.add_all([digital, local])
    db.flush()

    tag_appliance = Tag(category_id=digital.id, name="家用电器", slug="home-appliance", sort_order=1, is_active=True, created_at=current)
    tag_office = Tag(category_id=digital.id, name="电脑办公", slug="office", sort_order=2, is_active=True, created_at=current)
    tag_repair = Tag(category_id=local.id, name="维修安装", slug="repair", sort_order=1, is_active=True, created_at=current)
    db.add_all([tag_appliance, tag_office, tag_repair])
    db.flush()

    admin = AdminUser(
        username="admin",
        display_name="运营管理员",
        password_hash=hash_password(ADMIN_PASSWORD),
        role="admin",
        is_active=True,
        failed_attempts=0,
        created_at=current,
    )
    merchant_a = Merchant(
        name="甲商家",
        contact_name="张三",
        phone="13800000001",
        email="jia@example.com",
        password_hash=hash_password(MERCHANT_PASSWORD),
        city="深圳",
        main_category_id=digital.id,
        status="active",
        verified=True,
        created_at=current,
        updated_at=current,
    )
    merchant_b = Merchant(
        name="乙商家",
        contact_name="李四",
        phone="13800000002",
        email="yi@example.com",
        password_hash=hash_password(MERCHANT_PASSWORD),
        city="广州",
        main_category_id=local.id,
        status="active",
        verified=False,
        created_at=current,
        updated_at=current,
    )
    db.add_all([admin, merchant_a, merchant_b])
    db.flush()

    ads: dict[str, Ad] = {}
    ads["active"] = _create_ad(
        db,
        merchant_id=merchant_a.id,
        category_id=digital.id,
        title="洗衣机 家用 10 公斤 直降 500",
        tag_ids=[tag_appliance.id, tag_office.id],
        status="active",
        valid_from=current - timedelta(days=1),
        valid_to=current + timedelta(days=10),
    )
    ads["expiring"] = _create_ad(
        db,
        merchant_id=merchant_a.id,
        category_id=digital.id,
        title="便携榨汁杯 350ml",
        tag_ids=[tag_appliance.id],
        status="active",
        valid_from=current - timedelta(days=3),
        valid_to=current + timedelta(hours=10),
    )
    ads["pending"] = _create_ad(
        db,
        merchant_id=merchant_a.id,
        category_id=digital.id,
        title="待审广告甲",
        tag_ids=[tag_appliance.id],
        status="pending",
        valid_from=current - timedelta(days=1),
        valid_to=current + timedelta(days=10),
    )
    ads["rejected"] = _create_ad(
        db,
        merchant_id=merchant_a.id,
        category_id=digital.id,
        title="被拒广告甲",
        tag_ids=[tag_appliance.id],
        status="rejected",
        valid_from=current - timedelta(days=1),
        valid_to=current + timedelta(days=10),
    )
    ads["scheduled"] = _create_ad(
        db,
        merchant_id=merchant_a.id,
        category_id=digital.id,
        title="待生效广告甲",
        tag_ids=[tag_appliance.id],
        status="scheduled",
        valid_from=current + timedelta(days=5),
        valid_to=current + timedelta(days=20),
    )
    ads["expired"] = _create_ad(
        db,
        merchant_id=merchant_a.id,
        category_id=digital.id,
        title="已过期广告甲",
        tag_ids=[tag_appliance.id],
        status="expired",
        valid_from=current - timedelta(days=20),
        valid_to=current - timedelta(days=1),
    )
    ads["offline"] = _create_ad(
        db,
        merchant_id=merchant_a.id,
        category_id=digital.id,
        title="已下架广告甲",
        tag_ids=[tag_appliance.id],
        status="offline",
        valid_from=current - timedelta(days=2),
        valid_to=current + timedelta(days=8),
    )
    ads["other_active"] = _create_ad(
        db,
        merchant_id=merchant_b.id,
        category_id=digital.id,
        title="蓝牙耳机 降噪款",
        tag_ids=[tag_office.id],
        status="active",
        valid_from=current - timedelta(days=1),
        valid_to=current + timedelta(days=10),
    )
    ads["local_active"] = _create_ad(
        db,
        merchant_id=merchant_b.id,
        category_id=local.id,
        title="空调清洗 上门 深度除菌",
        tag_ids=[tag_repair.id],
        status="active",
        valid_from=current - timedelta(days=1),
        valid_to=current + timedelta(days=10),
    )
    ads["pending_other"] = _create_ad(
        db,
        merchant_id=merchant_b.id,
        category_id=local.id,
        title="待审广告乙",
        tag_ids=[tag_repair.id],
        status="pending",
        valid_from=current - timedelta(days=1),
        valid_to=current + timedelta(days=10),
    )
    db.commit()
    return {
        "admin_id": admin.id,
        "merchant_a": merchant_a.id,
        "merchant_b": merchant_b.id,
        "digital_id": digital.id,
        "local_id": local.id,
        "tag_appliance": tag_appliance.id,
        "tag_office": tag_office.id,
        "tag_repair": tag_repair.id,
        "ads": {key: ad.id for key, ad in ads.items()},
    }


@pytest.fixture()
def seeded() -> dict[str, object]:
    """每个测试用干净的库 + 最小数据集。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        return _seed(db)
    finally:
        db.close()


@pytest.fixture()
def client(seeded) -> TestClient:  # noqa: ARG001
    """匿名 TestClient（独立 Cookie 身份）。"""
    return TestClient(app)


@pytest.fixture()
def db_session(seeded) -> Session:  # noqa: ARG001
    """直连数据库会话（用于断言落库结果）。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def admin_client(seeded) -> TestClient:  # noqa: ARG001
    """已登录管理员的客户端。"""
    instance = TestClient(app)
    response = instance.post("/api/admin/login", json={"username": "admin", "password": ADMIN_PASSWORD})
    assert response.status_code == 200, response.text
    return instance


@pytest.fixture()
def merchant_client(seeded) -> TestClient:  # noqa: ARG001
    """已登录「甲商家」的客户端。"""
    instance = TestClient(app)
    response = instance.post(
        "/api/merchant/login", json={"account": "jia@example.com", "password": MERCHANT_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return instance
