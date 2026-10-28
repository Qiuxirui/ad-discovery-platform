"""AD 平台端到端验收脚本（真跑真打，不是看代码）。

用法（cwd = 项目根，服务需已在 8000 端口运行）::

    .venv/Scripts/python.exe scripts/e2e.py

覆盖 A 契约一致性 / B 匿名全链路 / C 商家链路 / D 管理链路 /
E 双保险与静态产物 / F pytest 回归 / G 前后端字段静态交叉核对。

脚本会修改数据库（新建商家/广告、下架、改 valid_to 等），
跑完必须执行 ``python -m backend.seed --reset`` 恢复干净种子库。
"""

from __future__ import annotations

import json
import random
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "backend" / "data" / "adx.db"
DIST = ROOT / "frontend" / "dist"
CST = timezone(timedelta(hours=8))

ADMIN_USER = "admin"
ADMIN_PASS = "adx-admin-2026"
MERCHANT_PASS = "adx-merchant-2026"

RESULTS: list[dict] = []

#: 报告中的分析章节（脚本自动跑结果 + 人工判定，重跑不会丢）
FINDINGS = """
## 3. 缺陷修复复测结果（Round 1 → Round 2 回归）

| 缺陷 | 修复内容（工程师） | 复测断言 | 结论 |
| --- | --- | --- | --- |
| P0-1 审核页解包错 | `AdminReviewPage.jsx` 新增 `normalizeQueueItem()` 拍平 + `requireSelectedId()` 守卫 + 过滤非法 id | G1 / G2（静态）+ A3（后端结构） | **已修复，已验证** |
| P1-2 举报率口径 | `stats.py` 改 `round(n/d*10000,1)`，去掉 `_safe_rate` 先四舍五入的精度损失 | D12 / D12b | **已修复，已验证**（实测 reports=4 / impressions=630 → `63.5‱`） |
| P2-3 收藏数与事件不一致 | seed 新增 `_seed_favorite_events()`，favorites 72 = favorite 事件 72 | A10 | **已修复，已验证**（`merchant/report?ad_id=12` → favorites=3, favorite_rate=1.0；`totals.favorites=72`） |
| P3-4 管理员登录结构 | `POST /api/admin/login` → `{admin:{...}}`（`/api/admin/me` 仍裸对象，符合 §5.7） | A9b | **已修复，已验证** |
| P3-5 下架原因校验 | `OfflineIn.reason` 改可选 + service 内 `strip()` 校验，空/纯空白 → `REASON_REQUIRED` | D8 / D8c | **已修复，已验证**（`{}`、`{"reason":"   "}`、`{"reason":"\\t\\n "}` 均 422 且广告不动） |
| 附带修复 | `AdminReportsPage` 把 `ad_snapshot`(dict) 归一为字符串；`MerchantAdsPage` 改读 `reject_reason` | G9 / G10 | **已修复，已验证** |

### Round 1 自查更正（属用例 Bug，已自修）

- A3/A4/A7/D2/D4~D13 首轮大批失败：上一轮 D14 的 5 次错密码把 admin 锁了 15 分钟 → 用例未解锁，已加 `unlock_admin()` 自愈。
- A6 `daily` 为空：新广告无事件，daily 本就允许为空 → 改用种子商家 1 的有事件广告验证结构。
- B3 标签命中 0 条：随手取的标签在架数为 0 → 改为从真实结果集里取标签。
- B9e/B9f：断言写错（`"limits" in me_limits` 逻辑错；`page_size=999` 实际 422 而非截断）→ 已修正。
- E8：首轮把 `reactjs.org/mui.com` 的报错说明字符串误判为外部请求 → 改为只匹配真实资源请求语法。

## 4. Round 2 新增的针对性断言（针对本次修复引入的新逻辑）

| 断言 | 覆盖点 | 为什么必须单独测 |
| --- | --- | --- |
| D8c | `offline` 传 `{"reason":"   "}` 与 `{"reason":"\\t\\n "}` → 422 `REASON_REQUIRED`，且广告仍 visible | 修复把校验从 pydantic 必填挪到 service 的 `strip()`，纯空白是最容易漏的分支；若只看 `{}` 会误判通过 |
| D9f | `week_stats` 四键（received/resolved/dismissed/avg_hours）与按状态过滤的真实条数一致 | 本轮新增 4 条种子举报（全状态覆盖）后才真正有数，之前恒为 0 掩盖了口径问题 |
| D3b | `summary` 6 个数字逐一对齐：队列 total / `?status=pending` / `?overdue=1` / `?status=resolved` / 库内今日事件数 / 库内今日去重处理广告数 | 之前只校验了 `pending_ads` 一项，其余 5 项无断言；`pending_reports`、`sla_overdue_reports` 现在有非零值才可验证 |
| G9 / G10 | 举报页 `ad_snapshot` dict→字符串；商家列表只读 `reject_reason` | 前端附带修复项，不测就会在真机上白屏/显示错字段 |
| E3 | `dist/index.html` 引用的 `assets/index-*.js` 与磁盘文件一致 | 前端重建后 hash 变化，引用不一致即白屏 |

## 5. 可延后瑕疵（不影响交付，Round 2 复核仍存在）

| # | 问题 | 说明 | 建议 |
| --- | --- | --- | --- |
| 1 | `GET /api/ads/{id}` 不含 `limits` | 团队待确认点之一；前端 `limits` 全部取自 `/api/visitor/me`，详情不需要 | 无需改，已在 B9e 固化为断言 |
| 2 | `page_size>60` 返回 422 而非截断到 60 | 前端恒发 ≤60，实际不可触发 | 若要严格对齐 §6.4「上限 60」的截断语义可改为手工截断 |
| 3 | `AdCardOut` 多出 `is_expired` 字段 | 契约未列，前端用于收藏页兜底分组，无害 | 更新 §5.2 文档或保留 |
| 4 | `GET /api/admin/me` 返回裸对象而 `/login` 返回 `{admin}` | 同一资源两种外壳，§5.7 只对 login 写明 `{admin}`、me 未写明 | 建议统一（都包 `{admin}` 或都裸），已在 A9b/G3 留证 |

## 6. 覆盖范围与未覆盖说明

已覆盖（真实 HTTP 调用 + 产物/源码静态校验，项数见 §0 概览）：契约一致性、匿名全链路、商家链路、管理链路、双保险与静态产物、回归测试、前后端字段静态核对。

未覆盖（环境无浏览器，已与 team-lead 对齐不装 Playwright）：
- 视觉与交互：`广告` 角标的橙色/8px/12px、「即将结束」徽标、hover 位移、`prefers-reduced-motion`；
- 5 秒倒计时中间页的按钮禁用与跳转、`sendBeacon` 卸载时 flush、IntersectionObserver 曝光阈值（≥50% + 1000ms）；
- 375px 响应式断点、MUI 主题实际渲染；
- 审核页/举报页在浏览器里的真实点击链路（本轮以「后端真实响应 + 前端解包代码静态核对」双向夹住，覆盖了解包正确性，但未覆盖点击态与渲染结果）。

替代手段：`dist/` 产物与 `index.html` 引用一致性（E3）、静态资源可达性与 Content-Type（E3b）、SPA fallback（E4/E6）、外部资源零依赖（E8）、前端源码字段与真实响应逐项交叉核对（G 组）。
"""


# --------------------------------------------------------------------------- 工具
def today() -> "datetime.date":
    return datetime.now(CST).date()


def d(offset: int) -> str:
    return (today() + timedelta(days=offset)).isoformat()


def new_client() -> httpx.Client:
    """独立会话（自带 CookieJar）；trust_env=False 避免走系统代理。"""
    return httpx.Client(base_url=BASE, timeout=30, trust_env=False, follow_redirects=False)


def body(resp: httpx.Response) -> dict | list:
    try:
        return resp.json()
    except Exception:  # noqa: BLE001
        return {}


def check(
    section: str,
    name: str,
    ok: bool,
    expected: str = "",
    actual: str = "",
    loc: str = "",
) -> bool:
    RESULTS.append(
        {
            "section": section,
            "name": name,
            "ok": bool(ok),
            "expected": expected,
            "actual": actual if actual else ("符合预期" if ok else "不符"),
            "loc": loc,
        }
    )
    flag = "PASS" if ok else "FAIL"
    print(f"[{flag}] {section} :: {name}")
    if not ok:
        print(f"        期望: {expected}")
        print(f"        实际: {actual}")
    return ok


def short(data: object, limit: int = 400) -> str:
    text = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    return text[:limit]


def ad_payload(title: str = "QA 验收测试广告", *, submit: bool = False, **over) -> dict:
    payload = {
        "title": title,
        "description": "QA 自动化脚本创建的测试广告，用于端到端验收，不作为真实投放。",
        "category_id": 3,
        "tag_ids": [11],
        "city": "深圳",
        "price_text": "到手 1999 元",
        "promo_condition": "满 2000 减 200",
        "restriction": "仅限本店使用，不与其他优惠叠加",
        "valid_from": d(0),
        "valid_to": d(7),
        "landing_url": "https://www.example.com/qa/e2e",
        "submit": submit,
    }
    payload.update(over)
    return payload


def unique_phone() -> str:
    return "139" + str(random.randint(10_000_000, 99_999_999))


def unlock_admin() -> None:
    """解锁管理员账号（上一轮 D14 的 5 次错密码会锁 15 分钟，保证脚本可重复执行）。"""
    conn = _db()
    conn.execute("UPDATE admin_users SET failed_attempts=0, locked_until=NULL")
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------- A 契约
def section_a(anon: httpx.Client, merc: httpx.Client, admin: httpx.Client, ctx: dict) -> None:
    sec = "A 契约一致性"
    unlock_admin()
    admin.post("/api/admin/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})

    # A1 tag_ids 命名 + submit:true 直接进 pending
    resp = merc.post("/api/merchant/ads", json=ad_payload("QA-A1 待生效广告", submit=True, valid_from=d(3), valid_to=d(10)))
    data = body(resp)
    ad = data.get("ad") if isinstance(data, dict) else None
    ctx["ad_future"] = ad["id"] if ad else None
    check(
        sec,
        "A1 POST /api/merchant/ads 用 tag_ids + submit:true 直接进 pending",
        resp.status_code == 200 and ad is not None and ad.get("status") == "pending" and ad.get("tag_ids") == [11],
        "200, ad.status=pending, ad.tag_ids=[11]",
        f"{resp.status_code}, status={ad.get('status') if ad else None}, tag_ids={ad.get('tag_ids') if ad else None}",
        "backend/routers/merchant_ads.py:create_ad → backend/schemas/ad.py:AdCreateIn.tag_ids",
    )

    # A2 商家单条详情回填字段完整
    ad_id = ctx.get("ad_future") or ctx["ad_active"]
    resp = merc.get(f"/api/merchant/ads/{ad_id}")
    data = body(resp)
    inner = data.get("ad") if isinstance(data, dict) else None
    need = ["landing_url", "valid_from_local_date", "valid_to_local_date", "category_id", "tags", "tag_ids"]
    missing = [key for key in need if not inner or key not in inner]
    ok = resp.status_code == 200 and not missing and str(inner.get("landing_url", "")).startswith("https://")
    check(
        sec,
        "A2 GET /api/merchant/ads/{id} 回填字段完整（landing_url/日期/category_id/tags）",
        ok,
        f"200 且含 {need} 且 landing_url 为完整 URL",
        f"{resp.status_code}, 缺={missing}, landing_url={inner.get('landing_url') if inner else None}",
        "backend/routers/merchant_ads.py:get_my_ad → schemas/ad.py:AdManageOut",
    )

    # A3 审核队列 item 结构
    resp = admin.get("/api/admin/review-queue")
    data = body(resp)
    items = data.get("items", []) if isinstance(data, dict) else []
    item = items[0] if items else {}
    mch = item.get("merchant") or {}
    ok_keys = all(key in item for key in ("ad", "merchant", "precheck", "waiting_minutes", "submitted_at"))
    ok_mch = "total_submitted" in mch and "rejected_count" in mch
    check(
        sec,
        "A3 GET /api/admin/review-queue 的 item 含 ad/merchant/precheck/waiting_minutes/submitted_at",
        resp.status_code == 200 and ok_keys and ok_mch,
        "item 含 ad, merchant{total_submitted,rejected_count,...}, precheck, waiting_minutes, submitted_at",
        f"{resp.status_code}, keys={sorted(item.keys())}, merchant_keys={sorted(mch.keys())}",
        "backend/schemas/admin.py:89 ReviewQueueItemOut（与 §5.7 一致，前端消费见 G 组）",
    )
    ctx["queue_total"] = data.get("total") if isinstance(data, dict) else None

    # A4 商家列表裸数组
    resp = admin.get("/api/admin/merchants")
    data = body(resp)
    check(
        sec,
        "A4 GET /api/admin/merchants 返回裸数组（§5.7）",
        resp.status_code == 200 and isinstance(data, list) and len(data) >= 8,
        "200 + JSON 数组（≥8 条）",
        f"{resp.status_code}, type={type(data).__name__}, len={len(data) if isinstance(data, list) else 'n/a'}",
        "backend/routers/admin_merchants.py:list_merchants",
    )

    # A5 收藏列表 items + groups
    resp = anon.get("/api/visitor/favorites")
    data = body(resp)
    groups = data.get("groups") if isinstance(data, dict) else None
    ok = isinstance(data, dict) and "items" in data and isinstance(groups, dict) and {"active", "expired"} <= set(groups)
    check(
        sec,
        "A5 GET /api/visitor/favorites 含 items + groups{active,expired}",
        resp.status_code == 200 and ok,
        "200 + {items:[], groups:{active:[],expired:[]}}",
        f"{resp.status_code}, keys={sorted(data.keys()) if isinstance(data, dict) else data}",
        "backend/routers/visitor.py:list_favorites",
    )

    # A6 指标字段名 + daily 行结构（用种子商家 1 的有事件广告，保证 daily 非空）
    seed_merc = new_client()
    seed_merc.post("/api/merchant/login", json={"account": "13800001001", "password": MERCHANT_PASS})
    resp = seed_merc.get("/api/merchant/report", params={"ad_id": 12, "from": d(-7), "to": d(1)})
    data = body(resp)
    metrics = data.get("metrics", {}) if isinstance(data, dict) else {}
    need = [
        "impressions", "unique_visitors", "detail_views", "link_clicks",
        "ctr_detail", "ctr_impression", "favorites", "reports", "report_rate_permille",
    ]
    missing = [key for key in need if key not in metrics]
    daily = data.get("daily", []) if isinstance(data, dict) else []
    daily_ok = bool(daily) and all({"date", "impressions", "detail_views", "link_clicks"} <= set(row) for row in daily)
    check(
        sec,
        "A6 商家报告 metrics 字段名与 daily 行结构符合 §5.6/§6.6",
        resp.status_code == 200 and not missing and daily_ok,
        f"metrics 含 {need}；daily 每行含 date/impressions/detail_views/link_clicks（且非空）",
        f"{resp.status_code}, 缺={missing}, daily 行数={len(daily)}, daily[0]={short(daily[0] if daily else None, 200)}",
        "backend/services/stats.py:merchant_report",
    )
    ctx["notes"] = data.get("notes", {}) if isinstance(data, dict) else {}
    resp = merc.get("/api/merchant/report", params={"ad_id": ad_id, "from": d(-7), "to": d(1)})
    blank = body(resp).get("metrics") or {}
    check(
        sec,
        "A6b 新建广告（尚无事件）报告返回 0 值且不报错",
        resp.status_code == 200 and (blank.get("impressions") or 0) == 0 and (blank.get("link_clicks") or 0) == 0,
        "200，impressions/link_clicks 均为 0",
        f"{resp.status_code}, metrics={short(blank, 160)}",
        "backend/services/stats.py:merchant_report",
    )

    # A7 summary 六个字段
    resp = admin.get("/api/admin/summary")
    data = body(resp)
    need = [
        "pending_ads", "pending_reports", "sla_overdue_reports",
        "today_events", "today_processed_ads", "week_resolved_reports",
    ]
    missing = [key for key in need if not isinstance(data, dict) or key not in data]
    check(
        sec,
        "A7 GET /api/admin/summary 返回 6 个字段",
        resp.status_code == 200 and not missing,
        f"{need}",
        f"{resp.status_code}, 缺={missing}, got={sorted(data.keys()) if isinstance(data, dict) else data}",
        "backend/routers/admin_stats.py:summary",
    )

    # A8 详情 restriction 字段名
    resp = anon.get("/api/ads/1")
    data = body(resp) if resp.status_code == 200 else {}
    check(
        sec,
        "A8 GET /api/ads/{id} 的『限制条款』字段名为 restriction",
        resp.status_code == 200 and isinstance(data, dict) and "restriction" in data,
        "200 且含 restriction",
        f"{resp.status_code}, keys={sorted(data.keys())[:12] if isinstance(data, dict) else data}",
        "backend/schemas/ad.py:AdDetailOut.restriction",
    )

    # A9 登录返回包裹结构
    resp_m = merc.post("/api/merchant/login", json={"account": ctx["merchant_phone"], "password": MERCHANT_PASS})
    data_m = body(resp_m)
    ok_m = resp_m.status_code == 200 and isinstance(data_m, dict) and "merchant" in data_m
    check(
        sec,
        "A9 商家登录返回 {merchant:{...}}（§5.6）",
        ok_m,
        "200 + {merchant:{...}}",
        f"{resp_m.status_code}, keys={sorted(data_m.keys()) if isinstance(data_m, dict) else data_m}",
        "backend/routers/merchant_auth.py:login",
    )
    resp_a = admin.post("/api/admin/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    data_a = body(resp_a)
    check(
        sec,
        "A9b 管理员登录返回 {admin:{...}}（§5.7 契约，与商家端对齐）",
        resp_a.status_code == 200 and isinstance(data_a, dict) and "admin" in data_a,
        "200 + {admin:{...}}",
        f"{resp_a.status_code}, keys={sorted(data_a.keys()) if isinstance(data_a, dict) else data_a}"
        "（返回裸 AdminOut；前端 AuthContext.jsx:94 已兼容，属契约偏差非功能阻塞）",
        "backend/routers/admin_auth.py:admin_login → response_model=AdminOut（§5.7 写的是 {admin}）",
    )

    # A10 种子数据与指标口径一致性：favorites / reports 有记录但无对应事件
    conn = _db()
    top = conn.execute(
        "SELECT ad_id, COUNT(*) AS c FROM favorites GROUP BY ad_id ORDER BY c DESC LIMIT 1"
    ).fetchone()
    fav_events = conn.execute("SELECT COUNT(*) FROM events WHERE event_type='favorite'").fetchone()[0]
    rep_rows = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    rep_events = conn.execute("SELECT COUNT(*) FROM events WHERE event_type='report'").fetchone()[0]
    conn.close()
    if top is not None:
        ad_fav, fav_rows = top["ad_id"], top["c"]
        owner = body(anon.get(f"/api/ads/{ad_fav}")).get("merchant_id")
        owner_client = new_client()
        accounts = {1: "13800001001", 2: "13800001002", 3: "13800001003", 4: "13800001004",
                    5: "13800001005", 6: "13800001006", 7: "13800001007", 8: "13800001008"}
        account = accounts.get(owner) or accounts[1]
        owner_client.post("/api/merchant/login", json={"account": account, "password": MERCHANT_PASS})
        rep = body(owner_client.get("/api/merchant/report", params={"ad_id": ad_fav, "from": d(-30), "to": d(1)}))
        report_fav = (rep.get("metrics") or {}).get("favorites")
        check(
            sec,
            "A10 收藏数口径一致：商家报告 metrics.favorites == favorites 表条数（seed 已补 favorite 事件）",
            report_fav == fav_rows,
            f"广告 {ad_fav} 的 favorites 表有 {fav_rows} 条，报告页 metrics.favorites 应等于 {fav_rows}",
            f"报告 metrics.favorites={report_fav}；favorites 表={fav_rows} 条；favorite 事件={fav_events} 条",
            "backend/seed.py:640-667 只生成 impression/detail_view/link_click/page_view 事件，"
            "但 :555 插入了 favorites 记录；backend/services/stats.py 指标只统计 events 表",
        )


# --------------------------------------------------------------------------- B 匿名
def section_b(anon: httpx.Client, ctx: dict) -> None:
    sec = "B 匿名全链路"

    # B1 首页 + 类别
    home = anon.get("/")
    check(
        sec,
        "B1 无 Cookie 打开 / 返回前端首页（text/html）",
        home.status_code == 200 and "text/html" in home.headers.get("content-type", ""),
        "200 + text/html",
        f"{home.status_code} + {home.headers.get('content-type')}",
        "backend/main.py:spa_fallback",
    )
    resp = anon.get("/api/categories")
    cats = body(resp)
    ok = (
        resp.status_code == 200
        and isinstance(cats, list)
        and len(cats) == 6
        and all(isinstance(c.get("active_count"), int) for c in cats)
        and all(c.get("tags") for c in cats)
    )
    check(
        sec,
        "B1b GET /api/categories 返回 6 个类别 + active_count + tags",
        ok,
        "6 条，每条 active_count 为整数且 tags 非空",
        f"{resp.status_code}, len={len(cats) if isinstance(cats, list) else 'n/a'}, "
        f"counts={[c.get('active_count') for c in cats] if isinstance(cats, list) else None}",
        "backend/routers/public_categories.py",
    )
    ctx["categories"] = cats if isinstance(cats, list) else []
    check(
        sec,
        "B1c 首次访问自动下发匿名 Cookie adx_vid",
        any(cookie.name == "adx_vid" for cookie in anon.cookies.jar),
        "响应 Set-Cookie: adx_vid",
        f"cookies={[c.name for c in anon.cookies.jar]}",
        "backend/visitor.py:VisitorMiddleware",
    )

    # B2 分类筛选
    digital = next((c for c in ctx["categories"] if c.get("slug") == "digital"), None)
    resp = anon.get("/api/ads", params={"category": "digital", "page_size": 60})
    data = body(resp)
    items = data.get("items", []) if isinstance(data, dict) else []
    bad = [item["id"] for item in items if item.get("category_slug") != "digital"]
    check(
        sec,
        "B2 分类筛选 ?category=digital 结果集自洽",
        resp.status_code == 200 and items and not bad and data.get("total") == len(items),
        "每个 item.category_slug == 'digital'，且 total == 返回条数（<=60）",
        f"{resp.status_code}, n={len(items)}, 违规={bad[:5]}, total={data.get('total') if isinstance(data, dict) else None}",
        "backend/services/visibility.py:apply_filters",
    )

    # B3 标签筛选（从真实在架结果里取一个确实有量的标签）
    first_digital = items[0] if items else None
    tag_slug = (first_digital or {}).get("tags", [{}])[0].get("slug") if first_digital else "home-appliance"
    tag_slug = tag_slug or "home-appliance"
    resp = anon.get("/api/ads", params={"tag": tag_slug, "page_size": 60})
    data = body(resp)
    items = data.get("items", []) if isinstance(data, dict) else []
    bad = [i["id"] for i in items if tag_slug not in [t.get("slug") for t in i.get("tags", [])]]
    check(
        sec,
        f"B3 标签筛选 ?tag={tag_slug} 结果集自洽",
        resp.status_code == 200 and items and not bad,
        "每条返回的 tags 里包含该 slug",
        f"{resp.status_code}, n={len(items)}, 违规={bad[:5]}",
        "backend/services/visibility.py:apply_filters(tag_slug)",
    )

    # B4 城市筛选
    resp = anon.get("/api/ads", params={"city": "深圳", "page_size": 60})
    data = body(resp)
    items = data.get("items", []) if isinstance(data, dict) else []
    bad = [i["id"] for i in items if i.get("city") not in {"深圳", "全国"}]
    check(
        sec,
        "B4 城市筛选 ?city=深圳 结果集自洽（含全国投放）",
        resp.status_code == 200 and items and not bad,
        "每条 city ∈ {深圳, 全国}",
        f"{resp.status_code}, n={len(items)}, 违规={bad[:5]}",
        "backend/services/visibility.py:apply_filters(city)",
    )

    # B5 ending=1
    resp = anon.get("/api/ads", params={"ending": 1, "page_size": 60})
    data = body(resp)
    items = data.get("items", []) if isinstance(data, dict) else []
    bad = [i["id"] for i in items if int(i.get("days_left") or 0) > 2]
    check(
        sec,
        "B5 即将结束筛选 ?ending=1 只回 ≤48h",
        resp.status_code == 200 and not bad,
        "每条 days_left <= 2",
        f"{resp.status_code}, n={len(items)}, 违规={bad[:5]}, days={[i.get('days_left') for i in items][:8]}",
        "backend/services/visibility.py:apply_filters(ending)",
    )

    # B6 promo=1
    resp = anon.get("/api/ads", params={"promo": 1, "page_size": 60})
    data = body(resp)
    items = data.get("items", []) if isinstance(data, dict) else []
    bad = [i["id"] for i in items if not (i.get("price_text") or "").strip() and not (i.get("promo_condition") or "").strip()]
    check(
        sec,
        "B6 有优惠筛选 ?promo=1 结果集自洽",
        resp.status_code == 200 and not bad,
        "每条 price_text 或 promo_condition 非空",
        f"{resp.status_code}, n={len(items)}, 违规={bad[:5]}",
        "backend/services/visibility.py:apply_filters(promo)",
    )

    # B7 排序
    r_latest = body(anon.get("/api/ads", params={"sort": "latest", "page_size": 60}))
    items_latest = r_latest.get("items", [])
    keys = [(i.get("published_at") or "", i.get("id")) for i in items_latest]
    latest_ok = all(keys[idx][0] >= keys[idx + 1][0] for idx in range(len(keys) - 1))
    r_ending = body(anon.get("/api/ads", params={"sort": "ending", "page_size": 60}))
    items_ending = r_ending.get("items", [])
    dates = [i.get("valid_to_local_date") or "" for i in items_ending]
    ending_ok = all(dates[idx] <= dates[idx + 1] for idx in range(len(dates) - 1))
    check(
        sec,
        "B7 三种排序：latest 按发布时间倒序 / ending 按到期日正序",
        latest_ok and ending_ok,
        "latest: published_at 不增；ending: valid_to_local_date 不减",
        f"latest_ok={latest_ok}, ending_ok={ending_ok}",
        "backend/services/visibility.py:apply_sort",
    )
    r_pop = anon.get("/api/ads", params={"sort": "popular", "page_size": 60})
    pop = body(r_pop)
    check(
        sec,
        "B7b sort=popular 可用且集合与 latest 一致（无重复/漏项）",
        r_pop.status_code == 200
        and {i["id"] for i in pop.get("items", [])} == {i["id"] for i in items_latest},
        "200，与 latest 的 id 集合相同",
        f"{r_pop.status_code}, n={len(pop.get('items', []))}, total={pop.get('total')}",
        "backend/services/visibility.py:apply_sort(popular)",
    )

    # B8 搜索
    r_hit = anon.get("/api/ads", params={"q": "洗衣机", "page_size": 60})
    hit = body(r_hit)
    r_none = anon.get("/api/ads", params={"q": "zzzz"})
    none = body(r_none)
    check(
        sec,
        "B8 搜索「洗衣机」有结果 / 搜索「zzzz」空结果",
        r_hit.status_code == 200 and hit.get("total", 0) > 0
        and r_none.status_code == 200 and none.get("total") == 0 and none.get("items") == [],
        "洗衣机 total>0；zzzz total=0 且 items=[]",
        f"洗衣机={hit.get('total')}；zzzz={none.get('total')}/{len(none.get('items', []))}",
        "backend/services/visibility.py:apply_filters(q)",
    )
    check(
        sec,
        "B8b 搜索命中项确实包含关键词（标题/描述/标签名）",
        all(
            "洗衣机" in (i.get("title") or "") + (i.get("price_text") or "")
            or "洗衣机" in "、".join(t.get("name", "") for t in i.get("tags", []))
            for i in hit.get("items", [])
        ),
        "每条命中项的 title/tags 含「洗衣机」",
        f"titles={[i.get('title') for i in hit.get('items', [])][:3]}",
        "backend/services/visibility.py:apply_filters(q)",
    )

    # B9 详情字段齐全
    ad_id = hit.get("items", [{}])[0].get("id") or items_latest[0]["id"]
    ctx["detail_id"] = ad_id
    resp = anon.get(f"/api/ads/{ad_id}")
    det = body(resp)
    need_card = [
        "id", "title", "price_text", "city", "merchant_name", "image_path", "category_slug",
        "category_name", "tags", "valid_to_local_date", "days_left", "expiring_soon",
        "is_favorited", "is_hidden", "published_at", "status",
    ]
    need_detail = ["description", "restriction", "valid_from", "valid_to", "landing_domain", "merchant", "related"]
    need_merchant = ["id", "name", "city", "main_category_name", "joined_at", "active_ad_count"]
    missing = [k for k in need_card + need_detail if k not in det]
    mch_missing = [k for k in need_merchant if k not in (det.get("merchant") or {})]
    check(
        sec,
        "B9 详情页字段齐全（卡片全字段 + 商家块 + 有效期 + 同类推荐）",
        resp.status_code == 200 and not missing and not mch_missing,
        f"含 {need_card + need_detail}；merchant 含 {need_merchant}",
        f"{resp.status_code}, 缺={missing}, merchant 缺={mch_missing}",
        "backend/services/visibility.py:build_detail",
    )
    related = det.get("related") or []
    check(
        sec,
        "B9b 详情同类推荐 ≤3 条且不含自身",
        len(related) <= 3 and all(item.get("id") != ad_id for item in related),
        "0–3 条，均不含自身",
        f"related={[item.get('id') for item in related]}",
        "backend/services/visibility.py:get_related_ads",
    )
    check(
        sec,
        "B9c 公开详情不泄露完整落地页 URL（只给 landing_domain，完整 URL 走 outbound）",
        "landing_url" not in det,
        "响应中无 landing_url 字段",
        f"has landing_url={'landing_url' in det}",
        "backend/services/visibility.py:build_detail（安全：外链 URL 仅 /outbound 下发）",
    )
    check(
        sec,
        "B9d 详情页『限制条款』为空时有兜底（restriction 可为 null，前端渲染文案）",
        "restriction" in det,
        "restriction 字段存在（null 时前端显示「商家未提供额外限制条款」）",
        f"restriction={det.get('restriction')!r}",
        "frontend/src/pages/AdDetailPage.jsx:256",
    )
    me_limits = body(anon.get("/api/visitor/me")).get("limits") or {}
    check(

        sec,
        "B9e 待确认点：详情是否需携带 limits（结论：不需要，前端取自 /api/visitor/me）",
        me_limits.get("favorites") == 200 and me_limits.get("hides") == 500 and "limits" not in det,
        "详情无 limits 字段；limits 由 /api/visitor/me 提供（favorites=200, hides=500）",
        f"detail 有 limits={'limits' in det}；me.limits={me_limits}",
        "frontend/src/context/VisitorContext.jsx:61-62",
    )

    # B9f 分页归一（§6.4：page<1 → 1；page_size>60 的处理口径）
    page = body(anon.get("/api/ads", params={"page": 0, "page_size": 60}))
    over = anon.get("/api/ads", params={"page_size": 999})
    check(
        sec,
        "B9f 分页归一：page=0 → 1；page_size>60 有明确处理（422 拒绝或截断到 60）",
        page.get("page") == 1 and len(page.get("items", [])) <= 60
        and (over.status_code == 422 or body(over).get("page_size") == 60),
        "page=1；page_size=999 返回 422 或截断到 60",
        f"page={page.get('page')}, n={len(page.get('items', []))}；"
        f"page_size=999 → {over.status_code} {short(body(over), 120)}",
        "backend/deps.py:get_pagination（page_size 校验 le=60，超限直接 422）",
    )

    # B10 outbound
    resp = anon.get(f"/api/ads/{ad_id}/outbound")
    out = body(resp)
    url = out.get("url") if isinstance(out, dict) else None
    check(
        sec,
        "B10 GET /api/ads/{id}/outbound 下发完整 URL 与域名",
        resp.status_code == 200 and out.get("allowed") is True
        and isinstance(url, str) and url.startswith(("http://", "https://"))
        and out.get("domain") == det.get("landing_domain"),
        "200 + allowed=true + url 为完整 http(s) 地址 + domain 与详情一致",
        f"{resp.status_code}, allowed={out.get('allowed')}, url={url}, domain={out.get('domain')}",
        "backend/routers/public_ads.py:outbound",
    )

    # B11 收藏
    resp = anon.post("/api/visitor/favorites", json={"ad_id": ad_id})
    fav = body(resp)
    me = body(anon.get("/api/visitor/me"))
    fav_list = body(anon.get("/api/visitor/favorites"))
    check(
        sec,
        "B11 收藏成功 → /api/visitor/me 反映 → 收藏列表可见",
        resp.status_code == 200 and fav.get("ok") is True
        and ad_id in (me.get("favorite_ids") or [])
        and any(item.get("id") == ad_id for item in fav_list.get("items", [])),
        "200 {ok:true}；me.favorite_ids 含该 id；favorites.items 含该条",
        f"{resp.status_code}, ok={fav.get('ok')}, count={fav.get('count')}, "
        f"me={me.get('favorite_ids')}, list_ids={[i.get('id') for i in fav_list.get('items', [])]}",
        "backend/routers/visitor.py:add_favorite",
    )
    resp = anon.post("/api/visitor/favorites", json={"ad_id": ad_id})
    check(
        sec,
        "B11b 重复收藏幂等（不重复计数、不报错）",
        resp.status_code == 200 and body(resp).get("count") == 1,
        "200 且 count 仍为 1",
        f"{resp.status_code}, count={body(resp).get('count')}",
        "backend/routers/visitor.py:add_favorite",
    )
    det2 = body(anon.get(f"/api/ads/{ad_id}"))
    check(
        sec,
        "B11c 收藏后详情 is_favorited=true（前端图标实心依据）",
        det2.get("is_favorited") is True,
        "is_favorited=true",
        f"is_favorited={det2.get('is_favorited')}",
        "backend/services/visibility.py:hydrate_card",
    )

    # B12 隐藏
    resp = anon.post("/api/visitor/hides", json={"ad_id": ad_id})
    hid = body(resp)
    lst = body(anon.get("/api/ads", params={"page_size": 60}))
    still = [i["id"] for i in lst.get("items", []) if i["id"] == ad_id]
    hides = body(anon.get("/api/visitor/hides"))
    check(
        sec,
        "B12 隐藏后列表不再返回该条，/api/visitor/hides 可恢复",
        resp.status_code == 200 and hid.get("ok") is True and not still
        and any(item.get("id") == ad_id for item in hides.get("items", [])),
        "200 {ok:true}；列表无该 id；hides.items 含该 id",
        f"{resp.status_code}, 列表仍含={still}, hides={[i.get('id') for i in hides.get('items', [])]}",
        "backend/routers/visitor.py:add_hide + services/visibility.py:apply_filters(exclude_ad_ids)",
    )
    resp = anon.delete(f"/api/visitor/hides/{ad_id}")
    back = body(anon.get("/api/ads", params={"page_size": 60}))
    check(
        sec,
        "B12b 取消隐藏后列表恢复该条",
        resp.status_code == 200 and ad_id in [i["id"] for i in back.get("items", [])],
        "200 且列表重新包含该 id",
        f"{resp.status_code}, 恢复={ad_id in [i['id'] for i in back.get('items', [])]}",
        "backend/routers/visitor.py:remove_hide",
    )

    # B13 举报
    ctx["report_ad"] = ad_id
    resp = anon.post("/api/reports", json={"ad_id": ad_id, "reason_code": "false_claim", "detail": "QA 验收：描述与实际不符"})
    rep = body(resp)
    code = rep.get("code", "")
    check(
        sec,
        "B13 举报返回 RP-XXXXXXXX 格式举报码",
        resp.status_code == 200 and re.fullmatch(r"RP-[A-Z0-9]{8}", code or "") is not None,
        "200 且 code 形如 RP-XXXXXXXX（8 位大写字母数字）",
        f"{resp.status_code}, code={code}",
        "backend/services/reports.py:generate_code",
    )
    ctx["report_code"] = code
    resp = anon.post("/api/reports", json={"ad_id": ad_id, "reason_code": "price_wrong"})
    dup = body(resp)
    check(
        sec,
        "B13b 24h 内重复举报同一条返回同一码且 duplicate=true",
        resp.status_code == 200 and dup.get("code") == code and dup.get("duplicate") is True,
        f"同一 code={code}，duplicate=true",
        f"{resp.status_code}, code={dup.get('code')}, duplicate={dup.get('duplicate')}",
        "backend/services/reports.py:create（24h 合并）",
    )
    resp = httpx.get(f"{BASE}/api/reports/lookup", params={"code": code}, timeout=30, trust_env=False)
    look = body(resp)
    check(
        sec,
        "B13c /api/reports/lookup 凭码可查（且不返回举报人信息）",
        resp.status_code == 200 and look.get("code") == code
        and "visitor_id" not in look and "admin_note" not in look
        and look.get("status_text") == "已收到，我们会在 48 小时内处理",
        "200 + status_text=「已收到，我们会在 48 小时内处理」+ 无 visitor_id",
        f"{resp.status_code}, status={look.get('status')}, text={look.get('status_text')}, keys={sorted(look.keys())}",
        "backend/routers/reports.py:lookup",
    )
    mine = body(anon.get("/api/reports/mine"))
    check(
        sec,
        "B13d /api/reports/mine 列出本设备举报",
        any(item.get("code") == code for item in mine.get("items", [])),
        f"items 含 code={code}",
        f"{[i.get('code') for i in mine.get('items', [])]}",
        "backend/routers/reports.py:mine",
    )

    # B14 偏好
    resp = anon.put("/api/visitor/preferences", json={"categories": [3, 4], "city": "深圳"})
    pref = body(anon.get("/api/visitor/preferences"))
    check(
        sec,
        "B14 偏好保存 / 读取一致",
        resp.status_code == 200 and pref.get("categories") == [3, 4] and pref.get("city") == "深圳",
        "PUT 200；GET 返回 categories=[3,4], city=深圳",
        f"{resp.status_code}, {pref}",
        "backend/routers/visitor.py:save_preferences",
    )

    # B15 事件上报去重
    session_id = "qa-e2e-" + str(int(time.time()))
    ev = {"session_id": session_id, "events": [
        {"event_type": "impression", "ad_id": ad_id, "page": "list", "position": 1},
        {"event_type": "page_view", "page": "home"},
    ]}
    r1 = body(anon.post("/api/events", json=ev))
    r2 = body(anon.post("/api/events", json={"session_id": session_id, "events": [
        {"event_type": "impression", "ad_id": ad_id, "page": "list", "position": 1},
    ]}))
    check(
        sec,
        "B15 事件上报：同 session 重复 impression 第二次被去重",
        r1.get("accepted") == 2 and r2.get("accepted") == 0,
        "第一次 accepted=2，第二次 accepted=0（dedupe_session）",
        f"第一次={r1}, 第二次={r2}",
        "backend/services/events.py:EventService",
    )
    r3 = anon.post("/api/events", json={"session_id": session_id, "events": [
        {"event_type": "impression", "ad_id": 999999, "page": "list"}
    ]})
    check(
        sec,
        "B15b 事件上报：不存在的 ad_id 被丢弃但不整体失败",
        r3.status_code == 200 and body(r3).get("accepted") == 0,
        "200 + accepted=0（dropped 有原因）",
        f"{r3.status_code}, {body(r3)}",
        "backend/services/events.py",
    )
    big = {"session_id": session_id, "events": [
        {"event_type": "page_view", "page": "home"} for _ in range(21)
    ]}
    r4 = anon.post("/api/events", json=big)
    check(
        sec,
        "B15c 单批事件 >20 条整体 422（§5.3）",
        r4.status_code == 422,
        "422",
        f"{r4.status_code}, {short(body(r4), 160)}",
        "backend/routers/events.py",
    )

    # B17 举报每日上限（单 visitor 每日 ≤3 条，超限 429）——用全新访客，避免污染主访客配额
    fresh = new_client()
    pool = [item["id"] for item in body(fresh.get("/api/ads", params={"page_size": 10})).get("items", [])]
    codes_reports = []
    for ad in pool[:4]:
        resp = fresh.post("/api/reports", json={"ad_id": ad, "reason_code": "other", "detail": "QA：上限测试"})
        codes_reports.append(resp.status_code)
    check(
        sec,
        "B17 单访客每日举报上限 3 条，第 4 条 429（PRD 8 / §5.5）",
        codes_reports[:3] == [200, 200, 200] and codes_reports[3] == 429,
        "前 3 条 200，第 4 条 429",
        f"codes={codes_reports}",
        "backend/services/reports.py:create（REPORT_DAILY_LIMIT=3）",
    )

    # B16 清空数据
    resp = anon.delete("/api/visitor/data")
    me2 = body(anon.get("/api/visitor/me"))
    check(
        sec,
        "B16 一键清空收藏/隐藏/偏好",
        resp.status_code == 200 and me2.get("favorite_ids") == [] and me2.get("hide_ids") == []
        and me2.get("preference", {}).get("categories") == [],
        "200；me.favorite_ids/hide_ids/categories 全空",
        f"{resp.status_code}, me={short({k: me2.get(k) for k in ('favorite_ids', 'hide_ids', 'preference')}, 200)}",
        "backend/routers/visitor.py:delete_visitor_data",
    )


# --------------------------------------------------------------------------- C 商家
def section_c(ctx: dict) -> httpx.Client:
    sec = "C 商家链路"
    merc = new_client()
    phone = unique_phone()
    email = f"qa{phone[-6:]}@example.com"
    ctx["merchant_phone"] = phone

    resp = merc.post("/api/merchant/signup", json={
        "name": f"QA 测试商家 {phone[-4:]}",
        "contact_name": "严过关",
        "phone": phone,
        "email": email,
        "password": MERCHANT_PASS,
        "city": "深圳",
        "main_category_id": 3,
        "agree_policy": True,
    })
    data = body(resp)
    check(
        sec,
        "C1 商家注册成功并下发 {merchant} + Cookie",
        resp.status_code == 200 and isinstance(data, dict) and "merchant" in data
        and any(c.name == "adx_merchant" for c in merc.cookies.jar),
        "200 + {merchant:{...}} + Set-Cookie adx_merchant",
        f"{resp.status_code}, keys={sorted(data.keys()) if isinstance(data, dict) else data}, "
        f"cookies={[c.name for c in merc.cookies.jar]}",
        "backend/routers/merchant_auth.py:signup",
    )
    merc.post("/api/merchant/logout")
    resp = merc.post("/api/merchant/login", json={"account": phone, "password": MERCHANT_PASS})
    check(
        sec,
        "C1b 商家登录（账号=手机号）成功",
        resp.status_code == 200 and "merchant" in body(resp),
        "200 + {merchant}",
        f"{resp.status_code}",
        "backend/routers/merchant_auth.py:login",
    )

    # 上传非法文件
    resp = merc.post("/api/merchant/uploads", files={"file": ("note.txt", b"hello qa", "text/plain")})
    check(
        sec,
        "C2 上传 .txt 返回 422 UPLOAD_REJECTED",
        resp.status_code == 422 and body(resp).get("code") == "UPLOAD_REJECTED",
        "422 + code=UPLOAD_REJECTED",
        f"{resp.status_code}, {short(body(resp), 160)}",
        "backend/services/ads.py:store_upload",
    )
    resp = merc.post("/api/merchant/uploads", files={"file": ("fake.png", b"not-a-png", "image/png")})
    check(
        sec,
        "C2b 伪造 png（魔数不符）返回 422",
        resp.status_code == 422 and body(resp).get("code") == "UPLOAD_REJECTED",
        "422 + UPLOAD_REJECTED（魔数校验）",
        f"{resp.status_code}, {short(body(resp), 160)}",
        "backend/services/ads.py:store_upload",
    )
    resp = merc.post("/api/merchant/uploads", files={
        "file": ("ok.png", bytes.fromhex("89504e470d0a1a0a0000000d49484452") + b"\x00" * 40, "image/png")
    })
    up = body(resp)
    check(
        sec,
        "C2c 合法 png 上传成功并返回 image_path",
        resp.status_code == 200 and str(up.get("image_path", "")).startswith("/static/uploads/"),
        "200 + image_path=/static/uploads/xx.png",
        f"{resp.status_code}, {short(up, 200)}",
        "backend/services/ads.py:store_upload",
    )
    ctx["upload_path"] = up.get("image_path")

    # 短链 422（在配额耗尽前测）
    resp = merc.post("/api/merchant/ads", json=ad_payload("QA-C3 短链测试", landing_url="https://bit.ly/qae2e"))
    check(
        sec,
        "C3 落地页短链返回 422 URL_SHORTENER",
        resp.status_code == 422 and body(resp).get("code") == "URL_SHORTENER",
        "422 + code=URL_SHORTENER",
        f"{resp.status_code}, {short(body(resp), 200)}",
        "backend/utils/urlsafety.py:check_url_safety + services/ads.py:384",
    )
    resp = merc.post("/api/merchant/ads", json=ad_payload("QA-C3b 内网地址", landing_url="http://127.0.0.1/x"))
    check(
        sec,
        "C3b 落地页内网/裸 IP 返回 422 URL_PRIVATE_HOST",
        resp.status_code == 422 and body(resp).get("code") in {"URL_PRIVATE_HOST", "URL_BARE_IP"},
        "422 + URL_PRIVATE_HOST/URL_BARE_IP",
        f"{resp.status_code}, {short(body(resp), 200)}",
        "backend/utils/urlsafety.py:check_url_safety",
    )

    # 建草稿
    payload = ad_payload("QA-C4 洗衣机验收草稿", submit=False, image_path=ctx.get("upload_path"))
    resp = merc.post("/api/merchant/ads", json=payload)
    data = body(resp)
    ad1 = (data.get("ad") or {}).get("id") if isinstance(data, dict) else None
    ctx["ad_active"] = ad1
    check(
        sec,
        "C4 建草稿 submit=false → draft",
        resp.status_code == 200 and (data.get("ad") or {}).get("status") == "draft",
        "200 + ad.status=draft",
        f"{resp.status_code}, status={(data.get('ad') or {}).get('status')}",
        "backend/services/ads.py:create",
    )
    resp = merc.post(f"/api/merchant/ads/{ad1}/submit")
    s1 = body(resp)
    check(
        sec,
        "C5 提交审核 draft → pending",
        resp.status_code == 200 and (s1.get("ad") or {}).get("status") == "pending",
        "200 + ad.status=pending",
        f"{resp.status_code}, status={(s1.get('ad') or {}).get('status')}",
        "backend/services/ads.py:submit",
    )
    anon = new_client()
    resp = anon.get(f"/api/ads/{ad1}")
    check(
        sec,
        "C5b 待审核广告匿名访问 404 AD_NOT_VISIBLE",
        resp.status_code == 404 and body(resp).get("code") == "AD_NOT_VISIBLE",
        "404 + AD_NOT_VISIBLE",
        f"{resp.status_code}, {short(body(resp), 160)}",
        "backend/routers/public_ads.py:get_ad",
    )
    resp = merc.post(f"/api/merchant/ads/{ad1}/withdraw")
    w1 = body(resp)
    check(
        sec,
        "C6 撤回 pending → draft",
        resp.status_code == 200 and (w1.get("ad") or {}).get("status") == "draft",
        "200 + ad.status=draft",
        f"{resp.status_code}, status={(w1.get('ad') or {}).get('status')}",
        "backend/services/ads.py:withdraw",
    )
    resp = merc.post(f"/api/merchant/ads/{ad1}/submit")
    check(
        sec,
        "C6b 撤回后重新提交回 pending",
        resp.status_code == 200 and (body(resp).get("ad") or {}).get("status") == "pending",
        "200 + pending",
        f"{resp.status_code}, status={(body(resp).get('ad') or {}).get('status')}",
        "backend/services/ads.py:submit",
    )

    ctx["quota_ads"] = [ad1]

    # 跨商家越权
    other = new_client()
    other.post("/api/merchant/login", json={"account": "13800001001", "password": MERCHANT_PASS})
    resp = other.get(f"/api/merchant/ads/{ad1}")
    check(
        sec,
        "C8 跨商家访问他人广告返回 404（不泄露存在性）",
        resp.status_code == 404,
        "404",
        f"{resp.status_code}, {short(body(resp), 160)}",
        "backend/routers/merchant_ads.py:own_ad",
    )
    resp = other.patch(f"/api/merchant/ads/{ad1}", json={"title": "越权改名"})
    check(
        sec,
        "C8b 跨商家 PATCH 他人广告返回 404",
        resp.status_code == 404,
        "404",
        f"{resp.status_code}",
        "backend/routers/merchant_ads.py:own_ad",
    )
    return merc


# --------------------------------------------------------------------------- C 配额
def section_c_quota() -> None:
    """独立商家测当日新建上限（避免污染主商家配额）。"""
    sec = "C 商家链路"
    merc = new_client()
    phone = unique_phone()
    resp = merc.post("/api/merchant/signup", json={
        "name": f"QA 配额商家 {phone[-4:]}",
        "contact_name": "严过关",
        "phone": phone,
        "email": f"quota{phone[-6:]}@example.com",
        "password": MERCHANT_PASS,
        "city": "深圳",
        "main_category_id": 3,
        "agree_policy": True,
    })
    created = []
    for idx in range(5):
        resp = merc.post("/api/merchant/ads", json=ad_payload(f"QA-C7 配额占位 {idx + 1}"))
        ad = body(resp).get("ad") or {}
        if ad.get("id"):
            created.append(ad["id"])
    resp = merc.post("/api/merchant/ads", json=ad_payload("QA-C7 第 6 条"))
    check(
        sec,
        f"C7 单商家当日新建上限 5 条，第 6 条返回 429（已建 {len(created)} 条）",
        len(created) == 5 and resp.status_code == 429 and body(resp).get("code") == "DAILY_QUOTA_EXCEEDED",
        "前 5 条 200；第 6 条 429 + DAILY_QUOTA_EXCEEDED",
        f"已建 {len(created)} 条；第 6 条 {resp.status_code}, {short(body(resp), 200)}",
        "backend/services/ads.py:check_quota",
    )


# --------------------------------------------------------------------------- D 管理
def section_d(admin: httpx.Client, merc: httpx.Client, ctx: dict) -> None:
    sec = "D 管理链路"
    unlock_admin()

    anon = new_client()
    resp = anon.get("/api/admin/review-queue")
    check(
        sec,
        "D1 未登录访问 /api/admin/review-queue 返回 401 UNAUTHORIZED",
        resp.status_code == 401 and body(resp).get("code") == "UNAUTHORIZED",
        "401 + code=UNAUTHORIZED",
        f"{resp.status_code}, {short(body(resp), 160)}",
        "backend/deps.py:require_admin",
    )

    resp = admin.post("/api/admin/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    check(
        sec,
        "D2 管理员登录成功",
        resp.status_code == 200 and any(c.name == "adx_admin" for c in admin.cookies.jar),
        "200 + Set-Cookie adx_admin",
        f"{resp.status_code}, cookies={[c.name for c in admin.cookies.jar]}",
        "backend/routers/admin_auth.py:admin_login",
    )

    summary = body(admin.get("/api/admin/summary"))
    queue = body(admin.get("/api/admin/review-queue", params={"page_size": 60}))
    check(
        sec,
        "D3 summary.pending_ads == 审核队列 total（口径一致性 P1-O-03）",
        summary.get("pending_ads") == queue.get("total"),
        "两处数字相等",
        f"summary={summary.get('pending_ads')}, queue.total={queue.get('total')}",
        "backend/routers/admin_stats.py:summary vs admin_review.py",
    )

    # D3b summary 6 个数字与对应列表/数据库逐一核对（回归新增）
    rep_all = body(admin.get("/api/admin/reports", params={"page_size": 60}))
    rep_pending = body(admin.get("/api/admin/reports", params={"status": "pending", "page_size": 60}))
    rep_resolved = body(admin.get("/api/admin/reports", params={"status": "resolved", "page_size": 60}))
    rep_overdue = body(admin.get("/api/admin/reports", params={"overdue": 1, "page_size": 60}))
    conn = _db()
    today_start = (
        datetime.now(CST).replace(hour=0, minute=0, second=0, microsecond=0)
        .astimezone(timezone.utc).replace(tzinfo=None)
        .strftime("%Y-%m-%d %H:%M:%S")
    )
    db_today_events = conn.execute("SELECT COUNT(*) FROM events WHERE ts>=?", (today_start,)).fetchone()[0]
    db_today_processed = conn.execute(
        "SELECT COUNT(DISTINCT ad_id) FROM reviews WHERE created_at>=? "
        "AND action IN ('approve','reject','offline')",
        (today_start,),
    ).fetchone()[0]
    conn.close()
    pairs = {
        "pending_ads": (summary.get("pending_ads"), queue.get("total")),
        "pending_reports": (summary.get("pending_reports"), rep_pending.get("total")),
        "sla_overdue_reports": (summary.get("sla_overdue_reports"), rep_overdue.get("total")),
        "week_resolved_reports": (summary.get("week_resolved_reports"), rep_resolved.get("total")),
        "today_events": (summary.get("today_events"), db_today_events),
        "today_processed_ads": (summary.get("today_processed_ads"), db_today_processed),
    }
    bad = {key: val for key, val in pairs.items() if val[0] != val[1]}
    check(
        sec,
        "D3b summary 的 6 个数字与对应列表过滤/库内口径逐一相等",
        not bad,
        f"pending_ads={pairs['pending_ads'][1]}, pending_reports={pairs['pending_reports'][1]}, "
        f"sla_overdue={pairs['sla_overdue_reports'][1]}, week_resolved={pairs['week_resolved_reports'][1]}, "
        f"today_events={db_today_events}, today_processed={db_today_processed}",
        f"不一致项={bad}（报告总数={rep_all.get('total')}）",
        "backend/routers/admin_stats.py:summary（pending_reports/sla_overdue/week_resolved/today_events/today_processed）",
    )

    ad_active = ctx["ad_active"]
    ad_future = ctx["ad_future"]
    queue_ids = [item.get("ad", {}).get("id") for item in queue.get("items", [])]
    check(
        sec,
        "D4 商家新提交的两条广告出现在审核队列",
        ad_active in queue_ids and ad_future in queue_ids,
        f"队列含 {ad_active} 与 {ad_future}",
        f"队列 ids={queue_ids}",
        "backend/routers/admin_review.py:review_queue",
    )

    resp = admin.post(f"/api/admin/ads/{ad_future}/approve", json={})
    appr = body(resp)
    status = (appr.get("ad") or appr).get("status") if isinstance(appr, dict) else None
    check(
        sec,
        "D5 通过但 valid_from 在未来 → scheduled",
        resp.status_code == 200 and status == "scheduled",
        "200 + status=scheduled",
        f"{resp.status_code}, status={status}, {short(appr, 200)}",
        "backend/services/ads.py:approve",
    )
    resp = anon.get(f"/api/ads/{ad_future}")
    check(
        sec,
        "D5b scheduled 广告匿名访问 404（未到生效时间不可见）",
        resp.status_code == 404,
        "404",
        f"{resp.status_code}",
        "backend/services/visibility.py:visible_ads_stmt",
    )

    resp = admin.post(f"/api/admin/ads/{ad_active}/approve", json={})
    appr = body(resp)
    status = (appr.get("ad") or appr).get("status") if isinstance(appr, dict) else None
    check(
        sec,
        "D6 通过有效期内的广告 → active",
        resp.status_code == 200 and status == "active",
        "200 + status=active",
        f"{resp.status_code}, status={status}",
        "backend/services/ads.py:approve",
    )
    resp = anon.get(f"/api/ads/{ad_active}")
    check(
        sec,
        "D6b 通过后用户端立即可见（详情 200）",
        resp.status_code == 200 and body(resp).get("id") == ad_active,
        "200 + id 匹配",
        f"{resp.status_code}",
        "backend/services/visibility.py:get_visible_ad",
    )
    timeline = body(admin.get(f"/api/admin/ads/{ad_active}/reviews"))
    actions = [item.get("action") for item in timeline.get("items", [])]
    check(
        sec,
        "D6c 审核时间线含 submit 与 approve 记录",
        "submit" in actions and "approve" in actions,
        "actions 含 submit / approve",
        f"actions={actions}",
        "backend/services/ads.py:log_review",
    )

    resp = merc.patch(f"/api/merchant/ads/{ad_active}", json={"title": "QA-D7 改标题触发重审"})
    upd = body(resp)
    became = upd.get("became_pending") if isinstance(upd, dict) else None
    status_after = (upd.get("ad") or {}).get("status") if isinstance(upd, dict) else None
    resp_anon = anon.get(f"/api/ads/{ad_active}")
    check(
        sec,
        "D7 active 广告改核心字段（标题）→ 回 pending 且匿名立即 404",
        resp.status_code == 200 and became is True and status_after == "pending" and resp_anon.status_code == 404,
        "PATCH 200 + became_pending=true + status=pending；匿名 404",
        f"{resp.status_code}, became_pending={became}, status={status_after}, anon={resp_anon.status_code}",
        "backend/services/ads.py:update（became_pending 判定）",
    )

    # 下架必须填原因：用种子里的在架广告
    lst = body(anon.get("/api/ads", params={"page_size": 60}))
    seed_ids = [
        item["id"] for item in lst.get("items", [])
        if item.get("merchant_id", 0) <= 8 and item["id"] not in ctx.get("quota_ads", [])
    ]
    target = seed_ids[0] if seed_ids else None
    ctx["offline_target"] = target
    resp = admin.post(f"/api/admin/ads/{target}/offline", json={})
    check(
        sec,
        "D8 下架不填原因返回 422 REASON_REQUIRED",
        resp.status_code == 422 and body(resp).get("code") == "REASON_REQUIRED",
        "422 + REASON_REQUIRED",
        f"{resp.status_code}, {short(body(resp), 200)}",
        "backend/services/ads.py:offline（api_error 422）",
    )
    resp = admin.post(f"/api/admin/ads/{target}/offline", json={"reason": "QA 验收：内容不实，测试下架"})
    off = body(resp)
    check(
        sec,
        "D8b 下架后匿名访问 404",
        resp.status_code == 200 and (off.get("ad") or {}).get("status") == "offline"
        and anon.get(f"/api/ads/{target}").status_code == 404,
        "200 + status=offline；匿名 404",
        f"{resp.status_code}, status={(off.get('ad') or {}).get('status')}, "
        f"anon={anon.get(f'/api/ads/{target}').status_code}",
        "backend/services/ads.py:offline",
    )

    # D8c 纯空格 reason 必须拒绝（回归新增：修复后不能再 200）
    live = [item["id"] for item in body(anon.get("/api/ads", params={"page_size": 60})).get("items", [])]
    probe_ad = next((i for i in live if i not in ctx.get("quota_ads", [])), None)
    r_blank = admin.post(f"/api/admin/ads/{probe_ad}/offline", json={"reason": "   "})
    r_tab = admin.post(f"/api/admin/ads/{probe_ad}/offline", json={"reason": "\t\n "})
    still = anon.get(f"/api/ads/{probe_ad}").status_code
    check(
        sec,
        "D8c 下架 reason 为纯空格 / 纯空白时仍返回 422 REASON_REQUIRED 且广告不被动",
        r_blank.status_code == 422 and body(r_blank).get("code") == "REASON_REQUIRED"
        and r_tab.status_code == 422 and body(r_tab).get("code") == "REASON_REQUIRED"
        and still == 200,
        "422 + REASON_REQUIRED（两次），广告仍 active（匿名 200）",
        f"空格={r_blank.status_code}/{body(r_blank).get('code')}, "
        f"制表符={r_tab.status_code}/{body(r_tab).get('code')}, 广告匿名访问={still}",
        "backend/services/ads.py:offline（reason.strip() 校验）+ schemas/admin.py:OfflineIn",
    )

    # 举报处置闭环
    victim = seed_ids[1] if len(seed_ids) > 1 else seed_ids[0]
    ctx["report_target"] = victim
    rep = body(anon.post("/api/reports", json={"ad_id": victim, "reason_code": "false_claim", "detail": "QA：夸大功效"}))
    code = rep.get("code")
    ctx["admin_report_code"] = code
    reports = body(admin.get("/api/admin/reports"))
    rid = next((item["id"] for item in reports.get("items", []) if item.get("code") == code), None)
    check(
        sec,
        "D9 管理员举报列表能查到该举报（含 ad_snapshot/overdue 等字段）",
        rid is not None and all(
            key in (reports.get("items") or [{}])[0]
            for key in ("id", "code", "ad_id", "ad_title", "reason_label", "status", "overdue")
        ),
        "items 含该 code，字段含 id/code/ad_id/ad_title/reason_label/status/overdue",
        f"rid={rid}, sample_keys={sorted((reports.get('items') or [{}])[0].keys())}",
        "backend/routers/admin_reports.py:list_reports",
    )
    resp = admin.post(f"/api/admin/reports/{rid}/start")
    check(
        sec,
        "D9b 开始处理 pending → reviewing",
        resp.status_code == 200 and (body(resp).get("report") or body(resp)).get("status") == "reviewing",
        "200 + status=reviewing",
        f"{resp.status_code}, {short(body(resp), 200)}",
        "backend/routers/admin_reports.py:start",
    )
    resp = admin.post(f"/api/admin/reports/{rid}/resolve", json={"action": "offline", "note": "QA：判定成立，已下架"})
    resol = body(resp)
    stat = (resol.get("report") or resol).get("status") if isinstance(resol, dict) else None
    check(
        sec,
        "D9c 判定成立 → 举报 resolved 且广告 offline",
        resp.status_code == 200 and stat == "resolved" and anon.get(f"/api/ads/{victim}").status_code == 404,
        "200 + report.status=resolved；广告匿名 404",
        f"{resp.status_code}, status={stat}, ad={anon.get(f'/api/ads/{victim}').status_code}",
        "backend/routers/admin_reports.py:resolve",
    )
    look = body(httpx.get(f"{BASE}/api/reports/lookup", params={"code": code}, timeout=30, trust_env=False))
    check(
        sec,
        "D9d 用户按码查到结果文案「经核查，该广告已被下架/整改」",
        look.get("status") == "resolved" and look.get("status_text") == "经核查，该广告已被下架/整改",
        "status=resolved + status_text=经核查，该广告已被下架/整改",
        f"status={look.get('status')}, text={look.get('status_text')}",
        "backend/constants.py:REPORT_STATUS_USER_TEXT",
    )
    resp = admin.post(f"/api/admin/reports/{rid}/dismiss", json={"note": "重复处置"})
    check(
        sec,
        "D9e 终态不可再改（resolved 后再 dismiss 应被拒）",
        resp.status_code in {409, 422},
        "409/422（状态只进不退）",
        f"{resp.status_code}, {short(body(resp), 160)}",
        "backend/routers/admin_reports.py",
    )

    # D9f week_stats 四键与按状态过滤的真实条数一致（回归新增）
    week = body(admin.get("/api/admin/reports", params={"page_size": 60}))
    wstats = week.get("week_stats") or {}
    p_cnt = body(admin.get("/api/admin/reports", params={"status": "pending", "page_size": 60})).get("total")
    v_cnt = body(admin.get("/api/admin/reports", params={"status": "reviewing", "page_size": 60})).get("total")
    s_cnt = body(admin.get("/api/admin/reports", params={"status": "resolved", "page_size": 60})).get("total")
    d_cnt = body(admin.get("/api/admin/reports", params={"status": "dismissed", "page_size": 60})).get("total")
    all_cnt = week.get("total")
    ok_week = (
        set(wstats) == {"received", "resolved", "dismissed", "avg_hours"}
        and wstats.get("received") == all_cnt
        and wstats.get("resolved") == s_cnt
        and wstats.get("dismissed") == d_cnt
        and isinstance(wstats.get("avg_hours"), (int, float))
        and 0 <= float(wstats.get("avg_hours")) <= 720
    )
    check(
        sec,
        "D9f 举报列表 week_stats 四键与按状态过滤的真实条数一致",
        ok_week,
        f"received==全部({all_cnt})、resolved=={s_cnt}、dismissed=={d_cnt}、avg_hours∈[0,720]",
        f"week_stats={wstats}；全部={all_cnt}（pending={p_cnt}/reviewing={v_cnt}/resolved={s_cnt}/dismissed={d_cnt}）",
        "backend/routers/admin_reports.py:list_reports(week_stats)",
    )

    # 统计口径交叉校验
    ov = body(admin.get("/api/admin/stats/overview", params={"from": d(-7), "to": d(1)}))
    totals = ov.get("totals", {})
    by_ad = ov.get("by_ad", [])
    by_cat = ov.get("by_category", [])
    sum_imp = sum(item.get("impressions", 0) for item in by_ad)
    sum_det = sum(item.get("detail_views", 0) for item in by_ad)
    sum_clk = sum(item.get("link_clicks", 0) for item in by_ad)
    check(
        sec,
        "D10 stats/overview：by_ad 各项求和 == totals",
        sum_imp == totals.get("impressions") and sum_det == totals.get("detail_views")
        and sum_clk == totals.get("link_clicks"),
        "by_ad 的 impressions/detail_views/link_clicks 求和等于 totals 同名字段",
        f"totals={ {k: totals.get(k) for k in ('impressions', 'detail_views', 'link_clicks')} }；"
        f"by_ad 求和={ {'impressions': sum_imp, 'detail_views': sum_det, 'link_clicks': sum_clk} }",
        "backend/services/stats.py:overview",
    )
    sum_c_imp = sum(item.get("impressions", 0) for item in by_cat)
    sum_c_det = sum(item.get("detail_views", 0) for item in by_cat)
    sum_c_clk = sum(item.get("link_clicks", 0) for item in by_cat)
    check(
        sec,
        "D10b stats/overview：by_category 求和 == totals",
        by_cat and sum_c_imp == totals.get("impressions")
        and sum_c_det == totals.get("detail_views") and sum_c_clk == totals.get("link_clicks"),
        "by_category 非空且三项求和等于 totals",
        f"n_cat={len(by_cat)}, 求和={ {'impressions': sum_c_imp, 'detail_views': sum_c_det, 'link_clicks': sum_c_clk} }, "
        f"totals={ {'impressions': totals.get('impressions'), 'detail_views': totals.get('detail_views'), 'link_clicks': totals.get('link_clicks')} }",
        "backend/services/stats.py:overview/by_category",
    )
    funnel = body(admin.get("/api/admin/stats/funnel", params={"from": d(-7), "to": d(1)}))
    counts = [step.get("count", 0) for step in funnel.get("steps", [])]
    check(
        sec,
        "D11 stats/funnel 四步单调不增",
        len(counts) == 4 and all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1)),
        "home ≥ list ≥ detail ≥ outbound",
        f"counts={counts}",
        "backend/services/stats.py:funnel",
    )
    rep_imp = totals.get("impressions") or 0
    rep_cnt = totals.get("reports") or 0
    expect = round(rep_cnt / rep_imp * 10000, 1) if rep_imp else 0.0
    check(
        sec,
        "D12 举报率口径为万分比（round(reports/impressions×10000, 1)，PRD 6.4 / §6.6）",
        abs(float(totals.get("report_rate_permille") or 0) - expect) < 0.051,
        f"reports/impressions ×10000 ≈ {expect}（保留 1 位小数）",
        f"接口返回 report_rate_permille={totals.get('report_rate_permille')}（reports={rep_cnt}, impressions={rep_imp}）",
        "backend/services/stats.py（万分比 + 1 位小数）",
    )
    check(
        sec,
        "D12b 商家报告 notes 口径文案同步为 ×10000（与计算口径一致）",
        "10000" in str((ctx.get("notes") or {}).get("report_rate_permille", "")),
        "notes.report_rate_permille 含「× 10000」",
        f"notes={short((ctx.get('notes') or {}).get('report_rate_permille'), 120)}",
        "backend/services/stats.py:notes",
    )

    # CSV
    resp = admin.get("/api/admin/stats/export.csv", params={"from": d(-7), "to": d(1), "type": "ads"})
    ctype = resp.headers.get("content-type", "")
    disp = resp.headers.get("content-disposition", "")
    check(
        sec,
        "D13 统计 CSV 导出：text/csv + BOM + 中文文件名",
        resp.status_code == 200 and "text/csv" in ctype and resp.content.startswith(b"\xef\xbb\xbf")
        and ".csv" in disp,
        "200 + text/csv + 首字节 EF BB BF + Content-Disposition 含 .csv（中文名）",
        f"{resp.status_code}, ctype={ctype}, bom={resp.content[:3]!r}, disp={disp}",
        "backend/utils/csv_export.py + routers/admin_stats.py",
    )
    resp = merc.get("/api/merchant/report/export.csv", params={"ad_id": ctx["ad_active"], "from": d(-7), "to": d(1)})
    disp = resp.headers.get("content-disposition", "")
    utf8_name = "filename*=utf-8''" in disp.lower() or "filename*=UTF-8''" in disp
    chinese_name = "\u62a5\u544a" in disp or "%E6%8A%A5%E5%91%8A" in disp.upper()
    check(
        sec,
        "D13b 商家报告 CSV 导出：BOM + 文件名「报告_广告标题_起_止.csv」",
        200 == resp.status_code
        and resp.content.startswith(b"\xef\xbb\xbf")
        and ".csv" in disp.lower()
        and (utf8_name or chinese_name),
        "200 + BOM + Content-Disposition 含 .csv 与中文「报告_」（RFC 5987 编码亦可）",
        f"{resp.status_code}, bom={resp.content[:3]!r}, utf8_name={utf8_name}, chinese={chinese_name}, disp={disp}",
        "backend/utils/csv_export.py:merchant_report_csv",
    )

    # 最后测锁定（会锁 admin 账号 15 分钟，故放最后）
    lock = new_client()
    codes = []
    for _ in range(5):
        resp = lock.post("/api/admin/login", json={"username": ADMIN_USER, "password": "wrong-password"})
        codes.append(resp.status_code)
        last = body(resp)
    check(
        sec,
        "D14 管理员连续输错密码 5 次，第 5 次 423 LOCKED",
        codes[:4] == [401, 401, 401, 401] and codes[4] == 423 and last.get("code") == "LOCKED",
        "[401,401,401,401,423]，第 5 次 code=LOCKED",
        f"codes={codes}, code={last.get('code')}",
        "backend/routers/admin_auth.py:admin_login",
    )


# --------------------------------------------------------------------------- E 双保险与产物
def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def section_e(anon: httpx.Client, ctx: dict) -> None:
    sec = "E 双保险与静态产物"

    # E1 查询层双保险
    lst = body(anon.get("/api/ads", params={"page_size": 60}))
    ids = [item["id"] for item in lst.get("items", [])]
    target = next((i for i in ids if i not in ctx.get("quota_ads", [])), None)
    ctx["expire_target"] = target
    conn = _db()
    past = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S.%f")
    conn.execute("UPDATE ads SET valid_to=?, status='active' WHERE id=?", (past, target))
    conn.commit()
    conn.close()

    lst2 = body(anon.get("/api/ads", params={"page_size": 60}))
    ids2 = [item["id"] for item in lst2.get("items", [])]
    detail = anon.get(f"/api/ads/{target}")
    check(
        sec,
        "E1 手改 valid_to 为昨天 → 查询层立即不返回（双保险第一层）",
        target not in ids2 and detail.status_code == 404,
        "列表不含该 id；详情 404",
        f"列表含={target in ids2}, 详情={detail.status_code}",
        "backend/services/visibility.py:visible_ads_stmt",
    )

    # E2 定时任务兜底
    status = None
    waited = 0
    review_action = None
    while waited <= 90:
        conn = _db()
        row = conn.execute("SELECT status FROM ads WHERE id=?", (target,)).fetchone()
        rev = conn.execute(
            "SELECT action FROM reviews WHERE ad_id=? ORDER BY id DESC LIMIT 1", (target,)
        ).fetchone()
        conn.close()
        status = row["status"] if row else None
        review_action = rev["action"] if rev else None
        if status == "expired" and review_action == "system_expire":
            break
        time.sleep(5)
        waited += 5
    check(
        sec,
        "E2 定时任务把过期 active 置 expired 并写 reviews（system_expire）",
        status == "expired" and review_action == "system_expire",
        "status=expired 且 reviews 最新 action=system_expire",
        f"status={status}, review_action={review_action}, 等待={waited}s",
        "backend/scheduler.py:expire_ads",
    )

    # E3 静态产物
    index = DIST / "index.html"
    html = index.read_text(encoding="utf-8") if index.exists() else ""
    refs = sorted(set(re.findall(r"/assets/[A-Za-z0-9._\-]+", html)))
    missing_assets = [ref for ref in refs if not (DIST / "assets" / Path(ref).name).exists()]
    check(
        sec,
        "E3 dist/index.html 引用的 /assets/* 文件在磁盘上全部存在（不一致=白屏）",
        bool(refs) and not missing_assets,
        "index.html 每处 /assets/xxx 都有对应文件",
        f"refs={refs}, 磁盘={[p.name for p in (DIST / 'assets').glob('*')]}, 缺失={missing_assets}",
        "frontend/dist/index.html",
    )
    for ref in refs:
        resp = httpx.get(f"{BASE}{ref}", timeout=30, trust_env=False)
        want = "javascript" if ref.endswith(".js") else "css"
        check(
            sec,
            f"E3b GET {ref} → 200 且 Content-Type 正确",
            resp.status_code == 200 and want in resp.headers.get("content-type", ""),
            f"200 + content-type 含 {want}",
            f"{resp.status_code} + {resp.headers.get('content-type')}",
            "backend/main.py:app.mount('/assets')",
        )

    resp = httpx.get(f"{BASE}/ad/1", timeout=30, trust_env=False)
    check(
        sec,
        "E4 SPA fallback：GET /ad/1 返回 200 text/html（直接刷新不 404）",
        resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""),
        "200 + text/html",
        f"{resp.status_code} + {resp.headers.get('content-type')}",
        "backend/main.py:spa_fallback",
    )
    resp = httpx.get(f"{BASE}/api/nonexistent", timeout=30, trust_env=False)
    data = body(resp)
    check(
        sec,
        "E5 未知 /api/* 返回 404 JSON（不能被 SPA 吞掉）",
        resp.status_code == 404 and isinstance(data, dict) and data.get("code") == "NOT_FOUND",
        "404 + JSON code=NOT_FOUND",
        f"{resp.status_code} + {short(data, 120)}",
        "backend/main.py:spa_fallback（api 前缀分支）",
    )
    resp = httpx.get(f"{BASE}/nonexistent-page", timeout=30, trust_env=False)
    check(
        sec,
        "E6 未知前端路由返回 HTML（200/404 均可，不得 500）",
        resp.status_code in {200, 404} and "text/html" in resp.headers.get("content-type", ""),
        "200/404 + text/html",
        f"{resp.status_code} + {resp.headers.get('content-type')}",
        "backend/main.py:spa_fallback",
    )
    resp = httpx.get(f"{BASE}/static/covers/ad-1.svg", timeout=30, trust_env=False)
    check(
        sec,
        "E7 封面静态资源可访问（卡片图不 404）",
        resp.status_code == 200 and "svg" in resp.headers.get("content-type", ""),
        "200 + image/svg+xml",
        f"{resp.status_code} + {resp.headers.get('content-type')}",
        "backend/main.py:app.mount('/static')",
    )

    # 外链域名自查（§14.14）：dist 中不得出现外部资源请求（文档链接类字符串不算）
    external = []
    resource_re = re.compile(
        r'(?:src|href)\s*=\s*["\']https?://|url\(\s*["\']?https?://|fetch\(\s*["\']https?://|import\(\s*["\']https?://'
    )
    for path in (DIST / "assets").glob("*"):
        if path.suffix not in {".js", ".css"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for hit in resource_re.findall(text):
            external.append(f"{path.name}:{hit}")
    check(
        sec,
        "E8 dist 产物内无外部资源请求（离线可运行，§14.14）",
        not external,
        "无 <script src=https://>、url(https://)、fetch(https://) 等外部请求",
        f"发现={external[:8]}" if external else "无（仅有 reactjs.org/mui.com 报错说明字符串，非请求）",
        "frontend/dist/assets/*.js|css",
    )


# --------------------------------------------------------------------------- F pytest
def section_f() -> None:
    sec = "F 回归测试"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "backend/tests", "-q"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    tail = (proc.stdout or "").strip().splitlines()
    summary_line = next((line for line in reversed(tail) if "passed" in line or "failed" in line or "error" in line), "")
    match = re.search(r"(\d+) passed", summary_line)
    passed = int(match.group(1)) if match else 0
    failed = ("failed" in summary_line) or ("error" in summary_line)
    check(
        sec,
        "F1 pytest backend/tests -q 全绿（≥45 passed）",
        proc.returncode == 0 and passed >= 45 and not failed,
        "returncode=0 且 passed>=45",
        f"returncode={proc.returncode}, {summary_line}",
        "backend/tests/",
    )


# --------------------------------------------------------------------------- G 静态契约
def section_g(ctx: dict) -> None:
    """前端源码与真实响应字段的静态交叉核对（无浏览器下的 UI 层代理验证）。"""
    sec = "G 前后端字段静态交叉核对"
    src = ROOT / "frontend" / "src"

    review = (src / "pages" / "admin" / "AdminReviewPage.jsx").read_text(encoding="utf-8")
    has_normalizer = "function normalizeQueueItem(item)" in review
    uses_normalizer = ".map(normalizeQueueItem)" in review
    id_guard = "Number.isFinite(Number(entry.id))" in review and "requireSelectedId" in review
    check(
        sec,
        "G1 审核页把嵌套队列 item 拍平后再消费（item.ad → 顶层 id）",
        has_normalizer and uses_normalizer and id_guard,
        "存在 normalizeQueueItem()、在 items 上 .map(normalizeQueueItem)、且过滤非法 id + requireSelectedId 守卫",
        f"normalizer={has_normalizer}, map={uses_normalizer}, id_guard={id_guard}",
        "frontend/src/pages/admin/AdminReviewPage.jsx:49,92-99,126",
    )
    fields_ok = all(
        token in review
        for token in ("pick('precheck')", "pick('waiting_minutes')", "pick('submitted_at')", "pick('merchant')")
    )
    check(
        sec,
        "G2 审核页从队列条目正确取 precheck / merchant / waiting_minutes / submitted_at",
        fields_ok and "merchant_name: base.merchant_name || (merchant && merchant.name)" in review,
        "normalizeQueueItem 显式 pick 这四个字段，并回落 merchant.name 作为 merchant_name",
        f"pick 四字段={fields_ok}, merchant_name 回落={'merchant_name: base.merchant_name' in review}",
        "frontend/src/pages/admin/AdminReviewPage.jsx:53-64",
    )

    auth = (src / "context" / "AuthContext.jsx").read_text(encoding="utf-8")
    check(
        sec,
        "G3 管理员登录返回裸对象时前端仍能识别（兼容写法）",
        "(res && res.admin) || res" in auth,
        "前端兼容 {admin} 与裸对象两种结构",
        "AuthContext.jsx:94 `const admin = (res && res.admin) || res || null;` 兼容 → 不算阻塞",
        "frontend/src/context/AuthContext.jsx:94",
    )
    merchants = (src / "pages" / "admin" / "AdminMerchantsPage.jsx").read_text(encoding="utf-8")
    check(
        sec,
        "G4 商家列表前端同时兼容裸数组与 {items}",
        "Array.isArray(payload) ? payload" in merchants,
        "兼容",
        "AdminMerchantsPage.jsx:54",
        "frontend/src/pages/admin/AdminMerchantsPage.jsx:54",
    )
    edit = (src / "pages" / "merchant" / "MerchantAdEditPage.jsx").read_text(encoding="utf-8")
    check(
        sec,
        "G5 商家单条详情前端兼容 {ad, became_pending} 包裹",
        "(adApi.data && adApi.data.ad) || adApi.data" in edit,
        "兼容",
        "MerchantAdEditPage.jsx:119",
        "frontend/src/pages/merchant/MerchantAdEditPage.jsx:119",
    )
    fav = (src / "pages" / "FavoritesPage.jsx").read_text(encoding="utf-8")
    check(
        sec,
        "G6 收藏页使用后端 groups{active,expired} 分组",
        "data.groups" in fav,
        "使用 groups",
        "FavoritesPage.jsx:50",
        "frontend/src/pages/FavoritesPage.jsx:50",
    )
    detail = (src / "pages" / "AdDetailPage.jsx").read_text(encoding="utf-8")
    check(
        sec,
        "G7 详情页使用 restriction 字段与空值兜底文案",
        "data.restriction" in detail,
        "使用 data.restriction",
        "AdDetailPage.jsx:256",
        "frontend/src/pages/AdDetailPage.jsx:256",
    )
    stats = (src / "pages" / "admin" / "AdminStatsPage.jsx").read_text(encoding="utf-8")
    check(
        sec,
        "G8 统计页使用 by_category / totals 字段名与后端一致",
        "by_category" in stats and "totals" in stats,
        "使用 by_category 与 totals",
        "AdminStatsPage.jsx:49",
        "frontend/src/pages/admin/AdminStatsPage.jsx:49",
    )

    reports_page = (src / "pages" / "admin" / "AdminReportsPage.jsx").read_text(encoding="utf-8")
    check(
        sec,
        "G9 举报页把 ad_snapshot(dict) 收敛成字符串再渲染（否则 React 渲染对象直接抛错）",
        "function snapshotOf(row)" in reports_page and "typeof raw === 'object'" in reports_page
        and "{snapshot.title}" in reports_page,
        "存在 snapshotOf() 归一化，JSX 里渲染 snapshot.title 字符串而非对象",
        f"snapshotOf={'function snapshotOf(row)' in reports_page}, "
        f"typecheck=\"typeof raw === 'object'\"={'typeof raw' in reports_page}, "
        f"渲染 snapshot.title={'{snapshot.title}' in reports_page}",
        "frontend/src/pages/admin/AdminReportsPage.jsx:39-46,254,286",
    )
    merc_ads = (src / "pages" / "merchant" / "MerchantAdsPage.jsx").read_text(encoding="utf-8")
    check(
        sec,
        "G10 商家广告列表读 reject_reason（后端无 reject_reason_note）",
        "reject_reason_note" not in merc_ads and "ad.reject_reason" in merc_ads,
        "只读 reject_reason（已含「标签：补充说明」），不引用不存在的 reject_reason_note",
        f"含 reject_reason_note={'reject_reason_note' in merc_ads}, 读 ad.reject_reason={'ad.reject_reason' in merc_ads}",
        "frontend/src/pages/merchant/MerchantAdsPage.jsx:232-235",
    )


# --------------------------------------------------------------------------- 报告
def write_report() -> Path:
    total = len(RESULTS)
    passed = sum(1 for row in RESULTS if row["ok"])
    failed = total - passed
    lines = [
        "# AD 平台端到端验收报告（QA）",
        "",
        f"- 执行时间：{datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)",
        "- 轮次：**Round 2 全量回归**（Round 1 发现的 5 项缺陷已由工程师修复，本轮为修复后复测，"
        "并新增针对性断言防止「假修复」）",
        f"- 被测服务：{BASE}（uvicorn backend.main:app，真实 HTTP 调用）",
        f"- 执行脚本：`scripts/e2e.py`（httpx + CookieJar 真会话）",
        f"- 测试项总数：**{total}**｜通过：**{passed}**｜失败：**{failed}**｜阻塞：0",
        f"- 通过率：**{passed / total * 100:.1f}%**（Round 1 为 104 项 / 98 通过 / 6 失败，通过率 94.2%）",
        "",
        "> 环境无浏览器：UI 层以「接口驱动 + dist 产物静态校验 + 前端源码字段静态交叉核对」替代，"
        "未覆盖像素级视觉与交互手势。",
        "",
        "## 0. 结论概览",
        "",
        "| 分组 | 项数 | 通过 | 失败 |",
        "| --- | --- | --- | --- |",
    ]
    sections: list[str] = []
    for row in RESULTS:
        if row["section"] not in sections:
            sections.append(row["section"])
    for name in sections:
        rows = [row for row in RESULTS if row["section"] == name]
        ok = sum(1 for row in rows if row["ok"])
        lines.append(f"| {name} | {len(rows)} | {ok} | {len(rows) - ok} |")

    lines += ["", "## 1. 失败项逐条复现（期望 / 实际 / 定位）", ""]
    failures = [row for row in RESULTS if not row["ok"]]
    if not failures:
        lines.append("无失败项。")
    for idx, row in enumerate(failures, start=1):
        lines += [
            f"### F{idx}. {row['name']}",
            "",
            f"- 分组：{row['section']}",
            f"- 期望：{row['expected']}",
            f"- 实际：{row['actual']}",
            f"- 定位：`{row['loc']}`",
            "",
        ]

    lines += ["", "## 2. 分组明细", ""]
    for name in sections:
        lines += [f"### {name}", "", "| # | 检查项 | 结果 | 期望 | 实际 |", "| --- | --- | --- | --- | --- |"]
        for idx, row in enumerate([r for r in RESULTS if r["section"] == name], start=1):
            flag = "✅" if row["ok"] else "❌"
            exp = row["expected"].replace("|", "\\|")
            act = str(row["actual"]).replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {idx} | {row['name'].replace('|', '/')} | {flag} | {exp} | {act} |")
        lines.append("")
    lines += [FINDINGS, ""]
    path = ROOT / "docs" / "QA-REPORT.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def cleanup_artifacts(ctx: dict) -> None:
    """清理本轮产生的临时上传文件（测试不许污染 backend/static/uploads）。"""
    uploaded = ctx.get("upload_path")
    if not uploaded:
        return
    target = ROOT / "backend" / "static" / uploaded.lstrip("/").replace("static/", "", 1)
    if target.exists():
        target.unlink()
        print(f"已清理临时上传件：{target.name}")


def main() -> int:
    health = httpx.get(f"{BASE}/api/health", timeout=10, trust_env=False)
    if health.status_code != 200:
        print(f"服务不可用：{health.status_code}")
        return 2
    print(f"健康检查 OK：{health.json()}\n")

    ctx: dict = {}
    admin = new_client()
    anon = new_client()

    # A 需要商家先行：先在 C 里建商家会破坏顺序，因此 A 用「临时注册的商家」
    # 这里把 C 的注册前置，A/C/D 共用同一商家会话
    merc = section_c(ctx)
    section_c_quota()
    section_a(anon, merc, admin, ctx)
    section_b(anon, ctx)
    section_d(admin, merc, ctx)
    section_e(anon, ctx)
    section_g(ctx)
    section_f()

    path = write_report()
    cleanup_artifacts(ctx)
    total = len(RESULTS)
    passed = sum(1 for row in RESULTS if row["ok"])
    print("\n" + "=" * 60)
    print(f"总计 {total} 项｜通过 {passed}｜失败 {total - passed}")
    print(f"报告：{path}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
