"""冒烟与关键规则测试（覆盖健康、可见性双保险、状态机、事件去重、权限隔离、URL 阻断、举报）。

约定：每个测试拿到干净的库（见 ``conftest.py``），断言尽量落到"可复现的行为"上。
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.models import Ad, Event, Report
from backend.scheduler import expire_ads, run_once
from backend.utils.timeutil import now_utc, to_cst, today_cst_range_utc

ADMIN_PASSWORD = "admin-pass-2026"
MERCHANT_PASSWORD = "merchant-pass-2026"


def _today_cst(offset: int = 0) -> str:
    from datetime import date

    base = to_cst(now_utc()).date()
    return date.fromordinal(base.toordinal() + offset).isoformat()


def _new_ad_payload(seeded: dict, **overrides) -> dict:
    payload = {
        "title": "测试新广告标题",
        "description": "这是一条用于测试的广告描述，包含足够的信息。",
        "category_id": seeded["digital_id"],
        "tag_ids": [seeded["tag_appliance"]],
        "city": "全国",
        "price_text": "到手 199 元",
        "promo_condition": None,
        "restriction": None,
        "valid_from": _today_cst(0),
        "valid_to": _today_cst(10),
        "landing_url": "https://www.example.com/new",
        "submit": False,
    }
    payload.update(overrides)
    return payload


# ------------------------------------------------------------------ 健康与元数据
def test_health_ok(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["time"].endswith("Z")


def test_meta_and_categories(client: TestClient, seeded: dict):
    meta = client.get("/api/meta").json()
    assert "全国" in meta["cities"]
    assert len(meta["report_reasons"]) == 6
    assert len(meta["reject_reasons"]) == 6
    assert meta["limits"]["favorites"] == 200
    assert meta["limits"]["hides"] == 500

    categories = client.get("/api/categories").json()
    assert len(categories) == 2
    digital = next(item for item in categories if item["slug"] == "digital")
    assert digital["active_count"] == 3, digital
    assert len(digital["tags"]) == 2


# ------------------------------------------------------------------ 可见性
def test_list_only_returns_visible_ads(client: TestClient, seeded: dict):
    body = client.get("/api/ads?page_size=60").json()
    ids = {item["id"] for item in body["items"]}
    ads = seeded["ads"]
    assert ads["active"] in ids
    assert ads["expiring"] in ids
    assert ads["other_active"] in ids
    assert ads["local_active"] in ids
    for key in ("pending", "rejected", "scheduled", "expired", "offline", "pending_other"):
        assert ads[key] not in ids, key
    assert body["total"] == 4


def test_detail_of_non_visible_ad_returns_404(client: TestClient, seeded: dict):
    response = client.get(f"/api/ads/{seeded['ads']['pending']}")
    assert response.status_code == 404
    assert response.json()["code"] == "AD_NOT_VISIBLE"
    assert response.json()["detail"] == "该广告已结束或暂不可见"


def test_visibility_double_insurance(client: TestClient, seeded: dict, db_session):
    """手工把 valid_to 改到过去：即使没跑定时任务，列表也不返回该广告。"""
    ad = db_session.get(Ad, seeded["ads"]["active"])
    ad.valid_to = now_utc() - timedelta(days=1)
    db_session.commit()

    body = client.get("/api/ads?page_size=60").json()
    assert ad.id not in {item["id"] for item in body["items"]}
    assert client.get(f"/api/ads/{ad.id}").status_code == 404

    expired_count = expire_ads()
    assert expired_count == 1
    db_session.expire_all()
    assert db_session.get(Ad, ad.id).status == "expired"


def test_scheduler_activates_scheduled_ad(seeded: dict, db_session):
    ad = db_session.get(Ad, seeded["ads"]["scheduled"])
    ad.valid_from = now_utc() - timedelta(minutes=1)
    ad.valid_to = now_utc() + timedelta(days=5)
    db_session.commit()

    expired, activated = run_once()
    assert activated == 1
    assert expired == 0
    db_session.expire_all()
    assert db_session.get(Ad, ad.id).status == "active"


def test_search_and_ending_filter(client: TestClient, seeded: dict):
    hit = client.get("/api/ads?q=洗衣机").json()
    assert hit["total"] == 1
    assert hit["items"][0]["id"] == seeded["ads"]["active"]

    tag_hit = client.get("/api/ads?tag=office").json()
    assert {item["id"] for item in tag_hit["items"]} == {
        seeded["ads"]["active"],
        seeded["ads"]["other_active"],
    }

    ending = client.get("/api/ads?ending=1").json()
    assert [item["id"] for item in ending["items"]] == [seeded["ads"]["expiring"]]
    assert ending["items"][0]["expiring_soon"] is True
    assert ending["items"][0]["days_left"] <= 2


# ------------------------------------------------------------------ 状态机
def test_state_machine_draft_submit_withdraw(merchant_client: TestClient, seeded: dict):
    created = merchant_client.post("/api/merchant/ads", json=_new_ad_payload(seeded))
    assert created.status_code == 200, created.text
    ad = created.json()["ad"]
    assert ad["status"] == "draft"

    submitted = merchant_client.post(f"/api/merchant/ads/{ad['id']}/submit").json()
    assert submitted["ad"]["status"] == "pending"
    assert submitted["precheck"]["passed"] is True

    withdrawn = merchant_client.post(f"/api/merchant/ads/{ad['id']}/withdraw").json()
    assert withdrawn["ad"]["status"] == "draft"


def test_state_machine_rejected_abandon(merchant_client: TestClient, seeded: dict):
    abandoned = merchant_client.post(f"/api/merchant/ads/{seeded['ads']['rejected']}/abandon").json()
    assert abandoned["ad"]["status"] == "draft"


def test_approve_makes_ad_active(admin_client: TestClient, client: TestClient, seeded: dict):
    pending_id = seeded["ads"]["pending"]
    assert client.get(f"/api/ads/{pending_id}").status_code == 404

    response = admin_client.post(f"/api/admin/ads/{pending_id}/approve", json={"note": "内容合规"})
    assert response.status_code == 200, response.text
    assert response.json()["ad"]["status"] == "active"
    assert client.get(f"/api/ads/{pending_id}").status_code == 200


def test_approve_future_ad_becomes_scheduled(admin_client: TestClient, merchant_client: TestClient, seeded: dict):
    payload = _new_ad_payload(seeded, valid_from=_today_cst(5), valid_to=_today_cst(20), submit=True)
    created = merchant_client.post("/api/merchant/ads", json=payload).json()
    assert created["ad"]["status"] == "pending"

    approved = admin_client.post(f"/api/admin/ads/{created['ad']['id']}/approve", json={})
    assert approved.status_code == 200
    assert approved.json()["ad"]["status"] == "scheduled"


def test_reject_requires_reason(admin_client: TestClient, seeded: dict):
    pending_id = seeded["ads"]["pending"]
    missing = admin_client.post(f"/api/admin/ads/{pending_id}/reject", json={})
    assert missing.status_code == 422

    rejected = admin_client.post(
        f"/api/admin/ads/{pending_id}/reject",
        json={"reason_code": "false_claim", "reason_note": "价格与页面不符"},
    )
    assert rejected.status_code == 200
    body = rejected.json()["ad"]
    assert body["status"] == "rejected"
    assert "虚假宣传" in body["reject_reason"]


def test_offline_requires_reason_and_hides_ad(admin_client: TestClient, client: TestClient, seeded: dict):
    active_id = seeded["ads"]["active"]
    assert admin_client.post(f"/api/admin/ads/{active_id}/offline", json={"reason": ""}).status_code == 422

    response = admin_client.post(f"/api/admin/ads/{active_id}/offline", json={"reason": "服务范围与实际不符"})
    assert response.status_code == 200
    assert response.json()["ad"]["status"] == "offline"
    assert client.get(f"/api/ads/{active_id}").status_code == 404


def test_edit_core_field_on_active_returns_to_pending(
    merchant_client: TestClient, client: TestClient, seeded: dict
):
    active_id = seeded["ads"]["active"]
    patched = merchant_client.patch(f"/api/merchant/ads/{active_id}", json={"title": "洗衣机 改标题后需重审"})
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["became_pending"] is True
    assert body["ad"]["status"] == "pending"
    assert client.get(f"/api/ads/{active_id}").status_code == 404
    assert merchant_client.patch(f"/api/merchant/ads/{seeded['ads']['pending']}", json={"title": "x"}).status_code == 409


def test_reviews_timeline_keeps_history(admin_client: TestClient, seeded: dict):
    pending_id = seeded["ads"]["pending"]
    admin_client.post(f"/api/admin/ads/{pending_id}/approve", json={"note": "通过"})
    timeline = admin_client.get(f"/api/admin/ads/{pending_id}/reviews").json()
    actions = [item["action"] for item in timeline["items"]]
    assert "approve" in actions
    assert all(item["created_at"].endswith("Z") for item in timeline["items"])


# ------------------------------------------------------------------ 事件与去重
def _post_events(client: TestClient, session_id: str, events: list[dict]) -> dict:
    response = client.post("/api/events", json={"session_id": session_id, "events": events})
    assert response.status_code == 200, response.text
    return response.json()


def test_event_impression_dedupe_by_session(client: TestClient, seeded: dict):
    ad_id = seeded["ads"]["active"]
    payload = [{"event_type": "impression", "ad_id": ad_id, "page": "list", "position": 0}]
    first = _post_events(client, "session-imp", payload)
    second = _post_events(client, "session-imp", payload)
    assert first["accepted"] == 1
    assert second["accepted"] == 0
    assert second["dropped"][0]["reason"] == "dedupe_session"


def test_event_detail_view_and_favorite_and_hide_dedupe(client: TestClient, seeded: dict):
    ad_id = seeded["ads"]["active"]
    _post_events(client, "session-dv", [{"event_type": "detail_view", "ad_id": ad_id, "page": "detail"}])
    dup = _post_events(client, "session-dv", [{"event_type": "detail_view", "ad_id": ad_id, "page": "detail"}])
    assert dup["accepted"] == 0
    assert dup["dropped"][0]["reason"] == "dedupe_session_30m"

    _post_events(client, "session-fav", [{"event_type": "favorite", "ad_id": ad_id, "page": "detail"}])
    dup_fav = _post_events(client, "session-fav", [{"event_type": "favorite", "ad_id": ad_id, "page": "detail"}])
    assert dup_fav["dropped"][0]["reason"] == "dedupe_unique"

    _post_events(client, "session-hide", [{"event_type": "hide", "ad_id": ad_id, "page": "list"}])
    dup_hide = _post_events(client, "session-hide", [{"event_type": "hide", "ad_id": ad_id, "page": "list"}])
    assert dup_hide["dropped"][0]["reason"] == "dedupe_unique"


def test_event_link_click_10s_dedupe(client: TestClient, seeded: dict):
    ad_id = seeded["ads"]["active"]
    _post_events(client, "session-click", [{"event_type": "link_click", "ad_id": ad_id, "page": "detail"}])
    dup = _post_events(client, "session-click", [{"event_type": "link_click", "ad_id": ad_id, "page": "detail"}])
    assert dup["accepted"] == 0
    assert dup["dropped"][0]["reason"] == "dedupe_10s"


def test_event_link_click_daily_cap_writes_suppressed(
    client: TestClient, seeded: dict, db_session
):
    visitor_id = client.get("/api/visitor/me").json()["visitor_id"]
    ad_id = seeded["ads"]["active"]
    day_start, _day_end = today_cst_range_utc(now_utc())
    current = day_start + timedelta(minutes=1)
    for _ in range(20):
        db_session.add(
            Event(
                id=str(uuid.uuid4()),
                event_type="link_click",
                ad_id=ad_id,
                visitor_id=visitor_id,
                session_id=str(uuid.uuid4()),
                ts=current,
                page="detail",
            )
        )
    db_session.commit()

    result = _post_events(client, "session-cap", [{"event_type": "link_click", "ad_id": ad_id, "page": "detail"}])
    assert result["accepted"] == 1
    stored = db_session.execute(
        select(Event).where(Event.visitor_id == visitor_id, Event.event_type == "link_click_suppressed")
    ).scalars().all()
    assert len(stored) == 1


def test_event_batch_limit_and_invalid_type(client: TestClient, seeded: dict):
    too_many = client.post(
        "/api/events",
        json={
            "session_id": "session-21",
            "events": [
                {"event_type": "page_view", "page": "home"} for _ in range(21)
            ],
        },
    )
    assert too_many.status_code == 422

    result = _post_events(
        client,
        "session-invalid",
        [
            {"event_type": "hack", "ad_id": seeded["ads"]["active"], "page": "list"},
            {"event_type": "detail_view", "ad_id": 999999, "page": "detail"},
            {"event_type": "detail_view", "ad_id": seeded["ads"]["active"], "page": "unknown"},
        ],
    )
    assert result["accepted"] == 0
    assert [item["reason"] for item in result["dropped"]] == [
        "invalid_type",
        "ad_not_found",
        "invalid_page",
    ]


# ------------------------------------------------------------------ 访客数据
def test_favorites_flow_and_events(client: TestClient, seeded: dict, db_session):
    ad_id = seeded["ads"]["active"]
    added = client.post("/api/visitor/favorites", json={"ad_id": ad_id}).json()
    assert added["count"] == 1 and added["limit"] == 200

    again = client.post("/api/visitor/favorites", json={"ad_id": ad_id}).json()
    assert again["count"] == 1

    me = client.get("/api/visitor/me").json()
    assert me["favorite_ids"] == [ad_id]
    assert me["counts"]["favorites"] == 1
    assert me["limits"] == {"favorites": 200, "hides": 500}

    favorites = client.get("/api/visitor/favorites").json()
    assert len(favorites["groups"]["active"]) == 1

    removed = client.delete(f"/api/visitor/favorites/{ad_id}").json()
    assert removed["count"] == 0

    visitor_id = me["visitor_id"]
    types = {
        row[0]
        for row in db_session.execute(
            select(Event.event_type).where(Event.visitor_id == visitor_id)
        ).all()
    }
    assert {"favorite", "unfavorite"} <= types


def test_preferences_and_clear_all(client: TestClient, seeded: dict):
    saved = client.put(
        "/api/visitor/preferences",
        json={"categories": [seeded["digital_id"]], "city": "深圳"},
    ).json()
    assert saved["ok"] is True
    assert saved["categories"] == [seeded["digital_id"]]

    client.post("/api/visitor/favorites", json={"ad_id": seeded["ads"]["active"]})
    client.post("/api/visitor/hides", json={"ad_id": seeded["ads"]["expiring"]})

    cleared = client.delete("/api/visitor/data").json()
    assert cleared["deleted"]["favorites"] == 1
    assert cleared["deleted"]["hides"] == 1
    assert client.get("/api/visitor/preferences").json()["categories"] == []


def test_hidden_ads_disappear_from_list(client: TestClient, seeded: dict):
    ad_id = seeded["ads"]["active"]
    client.post("/api/visitor/hides", json={"ad_id": ad_id})
    body = client.get("/api/ads?page_size=60").json()
    assert ad_id not in {item["id"] for item in body["items"]}
    client.delete(f"/api/visitor/hides/{ad_id}")
    body_again = client.get("/api/ads?page_size=60").json()
    assert ad_id in {item["id"] for item in body_again["items"]}


# ------------------------------------------------------------------ 举报
def test_report_merge_within_24h(client: TestClient, seeded: dict, db_session):
    ad_id = seeded["ads"]["active"]
    first = client.post("/api/reports", json={"ad_id": ad_id, "reason_code": "price_wrong"}).json()
    second = client.post("/api/reports", json={"ad_id": ad_id, "reason_code": "price_wrong"}).json()
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert first["code"] == second["code"]
    assert first["message"] == "已收到，我们会在 48 小时内处理"
    assert db_session.execute(select(Report).where(Report.ad_id == ad_id)).scalars().all()

    lookup = client.get(f"/api/reports/lookup?code={first['code']}").json()
    assert lookup["status_text"] == "已收到，我们会在 48 小时内处理"
    assert lookup["ad_title"]
    assert "visitor_id" not in lookup


def test_report_daily_limit(client: TestClient, seeded: dict):
    ads = seeded["ads"]
    targets = [ads["active"], ads["expiring"], ads["other_active"], ads["local_active"]]
    for ad_id in targets[:3]:
        assert client.post("/api/reports", json={"ad_id": ad_id, "reason_code": "other"}).status_code == 200
    fourth = client.post("/api/reports", json={"ad_id": targets[3], "reason_code": "other"})
    assert fourth.status_code == 429
    assert fourth.json()["code"] == "REPORT_DAILY_LIMIT"


def test_admin_resolve_report_offlines_ad(admin_client: TestClient, client: TestClient, seeded: dict):
    ad_id = seeded["ads"]["active"]
    code = client.post("/api/reports", json={"ad_id": ad_id, "reason_code": "false_claim"}).json()["code"]
    report_id = admin_client.get("/api/admin/reports?status=pending").json()["items"][0]["id"]

    started = admin_client.post(f"/api/admin/reports/{report_id}/start")
    assert started.status_code == 200
    assert started.json()["status"] == "reviewing"

    resolved = admin_client.post(
        f"/api/admin/reports/{report_id}/resolve",
        json={"action": "offline", "note": "价格与页面不符，已下架"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert client.get(f"/api/ads/{ad_id}").status_code == 404

    lookup = client.get(f"/api/reports/lookup?code={code}").json()
    assert lookup["status_text"] == "经核查，该广告已被下架/整改"


# ------------------------------------------------------------------ 权限隔离
def test_admin_endpoints_require_login(client: TestClient):
    for path in ("/api/admin/review-queue", "/api/admin/summary", "/api/admin/reports"):
        response = client.get(path)
        assert response.status_code == 401, path
        assert response.json()["code"] == "UNAUTHORIZED"


def test_merchant_endpoints_require_login(client: TestClient):
    assert client.get("/api/merchant/ads").status_code == 401
    assert client.get("/api/merchant/me").status_code == 401


def test_merchant_cannot_see_other_merchant_ad(merchant_client: TestClient, seeded: dict):
    other_id = seeded["ads"]["other_active"]
    response = merchant_client.get(f"/api/merchant/ads/{other_id}")
    assert response.status_code == 404
    assert response.json()["code"] == "AD_NOT_FOUND"


def test_admin_login_lock_after_five_failures(client: TestClient):
    for attempt in range(1, 6):
        response = client.post("/api/admin/login", json={"username": "admin", "password": "wrong-pass"})
        if attempt < 5:
            assert response.status_code == 401, attempt
        else:
            assert response.status_code == 423
            assert response.json()["code"] == "LOCKED"


def test_admin_login_returns_admin_envelope(client: TestClient):
    """§5.7：登录返回 ``{admin:{...}}``，与商家端 ``{merchant}`` 对齐。"""
    response = client.post("/api/admin/login", json={"username": "admin", "password": ADMIN_PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"admin"}
    assert body["admin"]["username"] == "admin"
    assert body["admin"]["display_name"] == "运营管理员"
    assert "password_hash" not in body["admin"]


def test_admin_offline_requires_reason(admin_client: TestClient, seeded: dict):
    """下架原因为空 → 422 ``REASON_REQUIRED``（不再被 pydantic 拦成 VALIDATION_ERROR）。"""
    ad_id = seeded["ads"]["active"]

    no_body = admin_client.post(f"/api/admin/ads/{ad_id}/offline")
    assert no_body.status_code == 422
    assert no_body.json()["code"] == "REASON_REQUIRED"
    assert no_body.json()["detail"] == "下架必须填写原因"

    blank = admin_client.post(f"/api/admin/ads/{ad_id}/offline", json={"reason": "   "})
    assert blank.status_code == 422
    assert blank.json()["code"] == "REASON_REQUIRED"

    ok = admin_client.post(f"/api/admin/ads/{ad_id}/offline", json={"reason": "举报核实：虚假宣传"})
    assert ok.status_code == 200
    assert ok.json()["ad"]["status"] == "offline"


def test_report_rate_permille_is_per_ten_thousand(
    admin_client: TestClient, seeded: dict, db_session
):
    """举报率是万分比：1 举报 / 4 展示 → 2500.0（千分比会算成 250.0）。"""
    ad_id = seeded["ads"]["active"]
    current = now_utc()
    for index in range(4):
        db_session.add(
            Event(
                id=str(uuid.uuid4()),
                event_type="impression",
                ad_id=ad_id,
                visitor_id=f"rate-visitor-{index}",
                session_id=f"rate-session-{index}",
                ts=current,
                page="list",
            )
        )
    db_session.add(
        Event(
            id=str(uuid.uuid4()),
            event_type="report",
            ad_id=ad_id,
            visitor_id="rate-visitor-0",
            session_id="rate-session-report",
            ts=current,
            page="detail",
        )
    )
    db_session.commit()

    overview = admin_client.get(
        f"/api/admin/stats/overview?from={_today_cst(0)}&to={_today_cst(0)}"
    ).json()
    assert overview["totals"]["impressions"] == 4
    assert overview["totals"]["reports"] == 1
    assert overview["totals"]["report_rate_permille"] == 2500.0


def test_favorite_event_feeds_favorites_metrics(
    admin_client: TestClient, client: TestClient, merchant_client: TestClient, seeded: dict
):
    """收藏必须同时写 ``favorite`` 事件，否则收藏数/收藏率恒为 0。"""
    ad_id = seeded["ads"]["active"]
    client.post("/api/visitor/favorites", json={"ad_id": ad_id})

    report = merchant_client.get(
        f"/api/merchant/report?ad_id={ad_id}&from={_today_cst(-6)}&to={_today_cst(0)}"
    ).json()
    assert report["metrics"]["favorites"] == 1

    overview = admin_client.get(
        f"/api/admin/stats/overview?from={_today_cst(-6)}&to={_today_cst(0)}"
    ).json()
    assert overview["totals"]["favorites"] >= 1


# ------------------------------------------------------------------ URL 安全
def test_outbound_blocks_dangerous_url(client: TestClient, seeded: dict, db_session):
    ad = db_session.get(Ad, seeded["ads"]["other_active"])
    ad.landing_url = "javascript:alert(1)"
    db_session.commit()

    response = client.get(f"/api/ads/{ad.id}/outbound").json()
    assert response["allowed"] is False
    assert response["url"] is None
    assert response["block_code"] == "URL_SCHEME"


def test_outbound_allows_safe_url(client: TestClient, seeded: dict):
    body = client.get(f"/api/ads/{seeded['ads']['active']}/outbound").json()
    assert body["allowed"] is True
    assert body["url"] == "https://www.example.com/ad"
    assert body["domain"] == "www.example.com"


def test_create_ad_rejects_short_link_and_banned_keyword(merchant_client: TestClient, seeded: dict):
    short_link = merchant_client.post(
        "/api/merchant/ads", json=_new_ad_payload(seeded, landing_url="https://bit.ly/abc123")
    )
    assert short_link.status_code == 422
    assert short_link.json()["code"] == "URL_SHORTENER"

    banned = merchant_client.post(
        "/api/merchant/ads",
        json=_new_ad_payload(
            seeded,
            title="医疗美容 低息贷款",
            description="含禁投行业关键词",
            submit=True,
        ),
    )
    assert banned.status_code == 200
    body = banned.json()
    assert body["ad"]["status"] == "rejected"
    assert body["precheck"]["passed"] is False


def test_create_ad_validation_limits(merchant_client: TestClient, seeded: dict):
    too_many_tags = merchant_client.post(
        "/api/merchant/ads",
        json=_new_ad_payload(
            seeded,
            tag_ids=[seeded["tag_appliance"], seeded["tag_office"], seeded["tag_repair"], 999],
        ),
    )
    assert too_many_tags.status_code == 422

    too_long = merchant_client.post(
        "/api/merchant/ads", json=_new_ad_payload(seeded, valid_to=_today_cst(120))
    )
    assert too_long.status_code == 200
    assert too_long.json()["precheck"]["code"] == "DATE_TOO_LONG"


def test_merchant_daily_quota(merchant_client: TestClient, seeded: dict):
    for index in range(5):
        response = merchant_client.post(
            "/api/merchant/ads", json=_new_ad_payload(seeded, title=f"配额测试广告 {index}")
        )
        assert response.status_code == 200, response.text
    sixth = merchant_client.post(
        "/api/merchant/ads", json=_new_ad_payload(seeded, title="配额测试广告 6")
    )
    assert sixth.status_code == 429
    assert sixth.json()["code"] == "DAILY_QUOTA_EXCEEDED"


def test_upload_rejects_non_image(merchant_client: TestClient):
    response = merchant_client.post(
        "/api/merchant/uploads", files={"file": ("note.txt", b"hello world", "text/plain")}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "UPLOAD_REJECTED"

    fake_png = merchant_client.post(
        "/api/merchant/uploads", files={"file": ("fake.png", b"not-a-real-png", "image/png")}
    )
    assert fake_png.status_code == 422


# ------------------------------------------------------------------ 管理端统计
def test_summary_matches_review_queue(admin_client: TestClient, seeded: dict):
    summary = admin_client.get("/api/admin/summary").json()
    queue = admin_client.get("/api/admin/review-queue").json()
    assert summary["pending_ads"] == queue["total"] == 2
    assert summary["pending_reports"] == 0

    overview = admin_client.get("/api/admin/stats/overview").json()
    assert "totals" in overview and "by_ad" in overview
    assert overview["totals"]["impressions"] == 0


def test_review_queue_exposes_precheck_code(admin_client: TestClient, seeded: dict, db_session):
    """审核队列要给出机器码，前端不必正则匹配中文预检文案。"""
    from backend.tests.conftest import _create_ad

    queue = admin_client.get("/api/admin/review-queue").json()
    item = queue["items"][0]
    assert item["precheck_passed"] is True
    assert item["precheck_code"] == "PRECHECK_PASSED"
    assert item["precheck"] == "预检通过"

    current = now_utc()
    banned = _create_ad(
        db_session,
        merchant_id=seeded["merchant_b"],
        category_id=seeded["local_id"],
        title="医疗美容 到院咨询 体验价",
        tag_ids=[seeded["tag_repair"]],
        status="pending",
        valid_from=current - timedelta(days=1),
        valid_to=current + timedelta(days=10),
    )
    db_session.commit()

    items = admin_client.get("/api/admin/review-queue?page_size=50").json()["items"]
    row = next(entry for entry in items if entry["ad"]["id"] == banned.id)
    assert row["precheck_passed"] is False
    assert row["precheck_code"] == "BANNED_INDUSTRY"
    assert "禁投行业关键词" in row["precheck_reason"]


def test_funnel_steps_monotonic(admin_client: TestClient, client: TestClient, seeded: dict):
    ad_id = seeded["ads"]["active"]
    client.post(
        "/api/events",
        json={
            "session_id": "session-funnel",
            "events": [
                {"event_type": "page_view", "page": "home"},
                {"event_type": "page_view", "page": "list"},
                {"event_type": "page_view", "page": "search"},
                {"event_type": "detail_view", "ad_id": ad_id, "page": "detail"},
                {"event_type": "link_click", "ad_id": ad_id, "page": "detail"},
            ],
        },
    )
    steps = admin_client.get("/api/admin/stats/funnel").json()["steps"]
    counts = [step["count"] for step in steps]
    assert counts == sorted(counts, reverse=True)
    assert counts[0] >= 1


def test_merchant_report_metrics_match_events(admin_client: TestClient, merchant_client: TestClient, seeded: dict):
    ad_id = seeded["ads"]["active"]
    merchant_client.post(
        "/api/events",
        json={
            "session_id": "session-report",
            "events": [
                {"event_type": "impression", "ad_id": ad_id, "page": "list"},
                {"event_type": "detail_view", "ad_id": ad_id, "page": "detail"},
                {"event_type": "link_click", "ad_id": ad_id, "page": "detail"},
            ],
        },
    )
    report = merchant_client.get(f"/api/merchant/report?ad_id={ad_id}&from={_today_cst(-6)}&to={_today_cst(0)}")
    assert report.status_code == 200, report.text
    metrics = report.json()["metrics"]
    assert metrics["impressions"] == 1
    assert metrics["detail_views"] == 1
    assert metrics["link_clicks"] == 1
    assert metrics["ctr_detail"] == 1.0

    csv_response = merchant_client.get(f"/api/merchant/report/export.csv?ad_id={ad_id}")
    assert csv_response.status_code == 200
    assert csv_response.content.startswith(b"\xef\xbb\xbf")
    assert "text/csv" in csv_response.headers["content-type"]


def test_merchant_status_counts(merchant_client: TestClient):
    body = merchant_client.get("/api/merchant/ads").json()
    counts = body["counts"]
    assert counts["all"] == 7
    assert counts["active"] == 2
    assert counts["pending"] == 1
    assert counts["rejected"] == 1
    assert counts["scheduled"] == 1
    assert counts["expired"] == 1
    assert counts["offline"] == 1


def test_admin_categories_tag_crud(admin_client: TestClient, seeded: dict):
    created = admin_client.post(
        f"/api/admin/categories/{seeded['digital_id']}/tags",
        json={"name": "智能穿戴", "sort_order": 5},
    )
    assert created.status_code == 200
    tag = created.json()
    assert tag["is_active"] is True

    updated = admin_client.patch(f"/api/admin/tags/{tag['id']}", json={"is_active": False})
    assert updated.status_code == 200
    assert updated.json()["is_active"] is False

    categories = admin_client.get("/api/admin/categories").json()
    digital = next(item for item in categories if item["slug"] == "digital")
    names = {item["name"] for item in digital["tags"]}
    assert "智能穿戴" in names

    public = admin_client.get("/api/categories").json()
    public_digital = next(item for item in public if item["slug"] == "digital")
    assert "智能穿戴" not in {item["name"] for item in public_digital["tags"]}


def test_admin_merchant_disable_offlines_ads(admin_client: TestClient, seeded: dict, db_session):
    response = admin_client.post(
        f"/api/admin/merchants/{seeded['merchant_a']}/status",
        json={"status": "disabled", "note": "多次违规"},
    )
    assert response.status_code == 200
    assert response.json()["affected_ads"] == 3

    db_session.expire_all()
    remaining = db_session.execute(
        select(Ad).where(Ad.merchant_id == seeded["merchant_a"], Ad.status.in_(["active", "scheduled"]))
    ).scalars().all()
    assert remaining == []


def test_spa_fallback_and_api_404(client: TestClient):
    api_missing = client.get("/api/does-not-exist")
    assert api_missing.status_code == 404
    assert api_missing.json()["code"] == "NOT_FOUND"

    page = client.get("/ad/1")
    assert page.status_code in (200, 404)
    if page.status_code == 404:
        assert page.json()["code"] == "FRONTEND_NOT_BUILT"


def test_favorite_limit_returns_409(client: TestClient, seeded: dict, db_session):
    """单设备收藏上限 200：第 201 条返回 409 ``LIMIT_REACHED``（T03 验收）。"""
    from backend.constants import FAVORITES_LIMIT
    from backend.models import Favorite, Visitor
    from backend.tests.conftest import _create_ad

    visitor_id = client.get("/api/visitor/me").json()["visitor_id"]

    current = now_utc()
    filler: list[int] = []
    for index in range(FAVORITES_LIMIT):
        ad = _create_ad(
            db_session,
            merchant_id=seeded["merchant_a"],
            category_id=seeded["digital_id"],
            title=f"收藏占位广告 {index:03d}",
            tag_ids=[],
            status="active",
            valid_from=current - timedelta(days=1),
            valid_to=current + timedelta(days=10),
        )
        filler.append(ad.id)
    for ad_id in filler:
        db_session.add(Favorite(visitor_id=visitor_id, ad_id=ad_id, created_at=current))
    db_session.commit()

    assert db_session.get(Visitor, visitor_id) is not None
    assert db_session.execute(
        select(Favorite).where(Favorite.visitor_id == visitor_id)
    ).scalars().all()

    overflow = client.post("/api/visitor/favorites", json={"ad_id": seeded["ads"]["active"]})
    assert overflow.status_code == 409
    assert overflow.json()["code"] == "LIMIT_REACHED"


def test_scheduler_expires_ad_after_valid_to(client: TestClient, seeded: dict, db_session):
    """手工把 active 广告改成昨天到期：列表立即不返回，调度器一次后状态变 expired（T06 验收）。"""
    from backend.models import Review

    ad_id = seeded["ads"]["active"]
    ad = db_session.get(Ad, ad_id)
    ad.valid_to = now_utc() - timedelta(days=1)
    db_session.commit()

    listed = client.get("/api/ads?page_size=60").json()
    assert ad_id not in {item["id"] for item in listed["items"]}

    detail = client.get(f"/api/ads/{ad_id}")
    assert detail.status_code == 404
    assert detail.json()["code"] == "AD_NOT_VISIBLE"

    run_once()

    db_session.expire_all()
    assert db_session.get(Ad, ad_id).status == "expired"
    system_logs = db_session.execute(
        select(Review).where(Review.ad_id == ad_id, Review.actor_type == "system")
    ).scalars().all()
    assert system_logs, "过期状态必须留下 reviews(actor_type=system) 记录"

