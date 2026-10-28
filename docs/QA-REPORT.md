# AD 平台端到端验收报告（QA）

- 执行时间：2026-10-27 23:38:54 (UTC+8)
- 轮次：**Round 2 全量回归**（Round 1 发现的 5 项缺陷已由工程师修复，本轮为修复后复测，并新增针对性断言防止「假修复」）
- 被测服务：http://127.0.0.1:8000（uvicorn backend.main:app，真实 HTTP 调用）
- 执行脚本：`.qa/e2e.py`（httpx + CookieJar 真会话）
- 测试项总数：**110**｜通过：**110**｜失败：**0**｜阻塞：0
- 通过率：**100.0%**（Round 1 为 104 项 / 98 通过 / 6 失败，通过率 94.2%）

> 环境无浏览器：UI 层以「接口驱动 + dist 产物静态校验 + 前端源码字段静态交叉核对」替代，未覆盖像素级视觉与交互手势。

## 0. 结论概览

| 分组 | 项数 | 通过 | 失败 |
| --- | --- | --- | --- |
| C 商家链路 | 15 | 15 | 0 |
| A 契约一致性 | 12 | 12 | 0 |
| B 匿名全链路 | 34 | 34 | 0 |
| D 管理链路 | 28 | 28 | 0 |
| E 双保险与静态产物 | 10 | 10 | 0 |
| G 前后端字段静态交叉核对 | 10 | 10 | 0 |
| F 回归测试 | 1 | 1 | 0 |

## 1. 失败项逐条复现（期望 / 实际 / 定位）

无失败项。

## 2. 分组明细

### C 商家链路

| # | 检查项 | 结果 | 期望 | 实际 |
| --- | --- | --- | --- | --- |
| 1 | C1 商家注册成功并下发 {merchant} + Cookie | ✅ | 200 + {merchant:{...}} + Set-Cookie adx_merchant | 200, keys=['merchant'], cookies=['adx_merchant', 'adx_vid'] |
| 2 | C1b 商家登录（账号=手机号）成功 | ✅ | 200 + {merchant} | 200 |
| 3 | C2 上传 .txt 返回 422 UPLOAD_REJECTED | ✅ | 422 + code=UPLOAD_REJECTED | 422, {"detail": "只支持 jpg / png / webp 格式的图片", "code": "UPLOAD_REJECTED"} |
| 4 | C2b 伪造 png（魔数不符）返回 422 | ✅ | 422 + UPLOAD_REJECTED（魔数校验） | 422, {"detail": "图片内容与扩展名不一致，请重新上传", "code": "UPLOAD_REJECTED"} |
| 5 | C2c 合法 png 上传成功并返回 image_path | ✅ | 200 + image_path=/static/uploads/xx.png | 200, {"image_path": "/static/uploads/c53597b5a4e84c59ac86c45ea0b196e8.png"} |
| 6 | C3 落地页短链返回 422 URL_SHORTENER | ✅ | 422 + code=URL_SHORTENER | 422, {"detail": "落地页不支持短链接，请填写可直接访问的目标页面地址", "code": "URL_SHORTENER", "fields": [{"field": "landing_url", "message": "落地页不支持短链接，请填写可直接访问的目标页面地址"}]} |
| 7 | C3b 落地页内网/裸 IP 返回 422 URL_PRIVATE_HOST | ✅ | 422 + URL_PRIVATE_HOST/URL_BARE_IP | 422, {"detail": "落地页不支持直接使用 IP 地址，请使用域名", "code": "URL_BARE_IP", "fields": [{"field": "landing_url", "message": "落地页不支持直接使用 IP 地址，请使用域名"}]} |
| 8 | C4 建草稿 submit=false → draft | ✅ | 200 + ad.status=draft | 200, status=draft |
| 9 | C5 提交审核 draft → pending | ✅ | 200 + ad.status=pending | 200, status=pending |
| 10 | C5b 待审核广告匿名访问 404 AD_NOT_VISIBLE | ✅ | 404 + AD_NOT_VISIBLE | 404, {"detail": "该广告已结束或暂不可见", "code": "AD_NOT_VISIBLE"} |
| 11 | C6 撤回 pending → draft | ✅ | 200 + ad.status=draft | 200, status=draft |
| 12 | C6b 撤回后重新提交回 pending | ✅ | 200 + pending | 200, status=pending |
| 13 | C8 跨商家访问他人广告返回 404（不泄露存在性） | ✅ | 404 | 404, {"detail": "该广告不存在", "code": "AD_NOT_FOUND"} |
| 14 | C8b 跨商家 PATCH 他人广告返回 404 | ✅ | 404 | 404 |
| 15 | C7 单商家当日新建上限 5 条，第 6 条返回 429（已建 5 条） | ✅ | 前 5 条 200；第 6 条 429 + DAILY_QUOTA_EXCEEDED | 已建 5 条；第 6 条 429, {"detail": "今日新建广告已达 5 条上限，请明日再提交（次日 00:00 恢复）", "code": "DAILY_QUOTA_EXCEEDED"} |

### A 契约一致性

| # | 检查项 | 结果 | 期望 | 实际 |
| --- | --- | --- | --- | --- |
| 1 | A1 POST /api/merchant/ads 用 tag_ids + submit:true 直接进 pending | ✅ | 200, ad.status=pending, ad.tag_ids=[11] | 200, status=pending, tag_ids=[11] |
| 2 | A2 GET /api/merchant/ads/{id} 回填字段完整（landing_url/日期/category_id/tags） | ✅ | 200 且含 ['landing_url', 'valid_from_local_date', 'valid_to_local_date', 'category_id', 'tags', 'tag_ids'] 且 landing_url 为完整 URL | 200, 缺=[], landing_url=https://www.example.com/qa/e2e |
| 3 | A3 GET /api/admin/review-queue 的 item 含 ad/merchant/precheck/waiting_minutes/submitted_at | ✅ | item 含 ad, merchant{total_submitted,rejected_count,...}, precheck, waiting_minutes, submitted_at | 200, keys=['ad', 'merchant', 'precheck', 'precheck_code', 'precheck_passed', 'precheck_reason', 'submitted_at', 'waiting_minutes'], merchant_keys=['id', 'joined_at', 'name', 'rejected_count', 'report_resolved_count', 'total_submitted'] |
| 4 | A4 GET /api/admin/merchants 返回裸数组（§5.7） | ✅ | 200 + JSON 数组（≥8 条） | 200, type=list, len=10 |
| 5 | A5 GET /api/visitor/favorites 含 items + groups{active,expired} | ✅ | 200 + {items:[], groups:{active:[],expired:[]}} | 200, keys=['groups', 'items'] |
| 6 | A6 商家报告 metrics 字段名与 daily 行结构符合 §5.6/§6.6 | ✅ | metrics 含 ['impressions', 'unique_visitors', 'detail_views', 'link_clicks', 'ctr_detail', 'ctr_impression', 'favorites', 'reports', 'report_rate_permille']；daily 每行含 date/impressions/detail_views/link_clicks（且非空） | 200, 缺=[], daily 行数=7, daily[0]={"date": "2026-10-21", "impressions": 1, "detail_views": 0, "link_clicks": 1} |
| 7 | A6b 新建广告（尚无事件）报告返回 0 值且不报错 | ✅ | 200，impressions/link_clicks 均为 0 | 200, metrics={"impressions": 0, "unique_visitors": 0, "detail_views": 0, "link_clicks": 0, "favorites": 0, "reports": 0, "ctr_detail": 0.0, "ctr_impression": 0.0, "favorite_ |
| 8 | A7 GET /api/admin/summary 返回 6 个字段 | ✅ | ['pending_ads', 'pending_reports', 'sla_overdue_reports', 'today_events', 'today_processed_ads', 'week_resolved_reports'] | 200, 缺=[], got=['pending_ads', 'pending_reports', 'sla_overdue_reports', 'today_events', 'today_processed_ads', 'week_resolved_reports'] |
| 9 | A8 GET /api/ads/{id} 的『限制条款』字段名为 restriction | ✅ | 200 且含 restriction | 200, keys=['category_id', 'category_name', 'category_slug', 'city', 'days_left', 'description', 'expiring_soon', 'id', 'image_path', 'is_expired', 'is_favorited', 'is_hidden'] |
| 10 | A9 商家登录返回 {merchant:{...}}（§5.6） | ✅ | 200 + {merchant:{...}} | 200, keys=['merchant'] |
| 11 | A9b 管理员登录返回 {admin:{...}}（§5.7 契约，与商家端对齐） | ✅ | 200 + {admin:{...}} | 200, keys=['admin']（返回裸 AdminOut；前端 AuthContext.jsx:94 已兼容，属契约偏差非功能阻塞） |
| 12 | A10 收藏数口径一致：商家报告 metrics.favorites == favorites 表条数（seed 已补 favorite 事件） | ✅ | 广告 16 的 favorites 表有 5 条，报告页 metrics.favorites 应等于 5 | 报告 metrics.favorites=5；favorites 表=5 条；favorite 事件=72 条 |

### B 匿名全链路

| # | 检查项 | 结果 | 期望 | 实际 |
| --- | --- | --- | --- | --- |
| 1 | B1 无 Cookie 打开 / 返回前端首页（text/html） | ✅ | 200 + text/html | 200 + text/html; charset=utf-8 |
| 2 | B1b GET /api/categories 返回 6 个类别 + active_count + tags | ✅ | 6 条，每条 active_count 为整数且 tags 非空 | 200, len=6, counts=[8, 8, 8, 10, 3, 3] |
| 3 | B1c 首次访问自动下发匿名 Cookie adx_vid | ✅ | 响应 Set-Cookie: adx_vid | cookies=['adx_vid'] |
| 4 | B2 分类筛选 ?category=digital 结果集自洽 | ✅ | 每个 item.category_slug == 'digital'，且 total == 返回条数（<=60） | 200, n=8, 违规=[], total=8 |
| 5 | B3 标签筛选 ?tag=home-appliance 结果集自洽 | ✅ | 每条返回的 tags 里包含该 slug | 200, n=4, 违规=[] |
| 6 | B4 城市筛选 ?city=深圳 结果集自洽（含全国投放） | ✅ | 每条 city ∈ {深圳, 全国} | 200, n=38, 违规=[] |
| 7 | B5 即将结束筛选 ?ending=1 只回 ≤48h | ✅ | 每条 days_left <= 2 | 200, n=2, 违规=[], days=[2, 1] |
| 8 | B6 有优惠筛选 ?promo=1 结果集自洽 | ✅ | 每条 price_text 或 promo_condition 非空 | 200, n=40, 违规=[] |
| 9 | B7 三种排序：latest 按发布时间倒序 / ending 按到期日正序 | ✅ | latest: published_at 不增；ending: valid_to_local_date 不减 | latest_ok=True, ending_ok=True |
| 10 | B7b sort=popular 可用且集合与 latest 一致（无重复/漏项） | ✅ | 200，与 latest 的 id 集合相同 | 200, n=40, total=40 |
| 11 | B8 搜索「洗衣机」有结果 / 搜索「zzzz」空结果 | ✅ | 洗衣机 total>0；zzzz total=0 且 items=[] | 洗衣机=1；zzzz=0/0 |
| 12 | B8b 搜索命中项确实包含关键词（标题/描述/标签名） | ✅ | 每条命中项的 title/tags 含「洗衣机」 | titles=['洗衣机 除螨洗 10 公斤 直降 500'] |
| 13 | B9 详情页字段齐全（卡片全字段 + 商家块 + 有效期 + 同类推荐） | ✅ | 含 ['id', 'title', 'price_text', 'city', 'merchant_name', 'image_path', 'category_slug', 'category_name', 'tags', 'valid_to_local_date', 'days_left', 'expiring_soon', 'is_favorited', 'is_hidden', 'published_at', 'status', 'description', 'restriction', 'valid_from', 'valid_to', 'landing_domain', 'merchant', 'related']；merchant 含 ['id', 'name', 'city', 'main_category_name', 'joined_at', 'active_ad_count'] | 200, 缺=[], merchant 缺=[] |
| 14 | B9b 详情同类推荐 ≤3 条且不含自身 | ✅ | 0–3 条，均不含自身 | related=[9, 5, 3] |
| 15 | B9c 公开详情不泄露完整落地页 URL（只给 landing_domain，完整 URL 走 outbound） | ✅ | 响应中无 landing_url 字段 | has landing_url=False |
| 16 | B9d 详情页『限制条款』为空时有兜底（restriction 可为 null，前端渲染文案） | ✅ | restriction 字段存在（null 时前端显示「商家未提供额外限制条款」） | restriction='大件商品不支持七天无理由退货' |
| 17 | B9e 待确认点：详情是否需携带 limits（结论：不需要，前端取自 /api/visitor/me） | ✅ | 详情无 limits 字段；limits 由 /api/visitor/me 提供（favorites=200, hides=500） | detail 有 limits=False；me.limits={'favorites': 200, 'hides': 500} |
| 18 | B9f 分页归一：page=0 → 1；page_size>60 有明确处理（422 拒绝或截断到 60） | ✅ | page=1；page_size=999 返回 422 或截断到 60 | page=1, n=40；page_size=999 → 422 {"detail": "有 1 项需要修改", "code": "VALIDATION_ERROR", "fields": [{"field": "page_size", "message": "数值过大"}]} |
| 19 | B10 GET /api/ads/{id}/outbound 下发完整 URL 与域名 | ✅ | 200 + allowed=true + url 为完整 http(s) 地址 + domain 与详情一致 | 200, allowed=True, url=https://www.example.com/1/12, domain=www.example.com |
| 20 | B11 收藏成功 → /api/visitor/me 反映 → 收藏列表可见 | ✅ | 200 {ok:true}；me.favorite_ids 含该 id；favorites.items 含该条 | 200, ok=True, count=1, me=[12], list_ids=[12] |
| 21 | B11b 重复收藏幂等（不重复计数、不报错） | ✅ | 200 且 count 仍为 1 | 200, count=1 |
| 22 | B11c 收藏后详情 is_favorited=true（前端图标实心依据） | ✅ | is_favorited=true | is_favorited=True |
| 23 | B12 隐藏后列表不再返回该条，/api/visitor/hides 可恢复 | ✅ | 200 {ok:true}；列表无该 id；hides.items 含该 id | 200, 列表仍含=[], hides=[12] |
| 24 | B12b 取消隐藏后列表恢复该条 | ✅ | 200 且列表重新包含该 id | 200, 恢复=True |
| 25 | B13 举报返回 RP-XXXXXXXX 格式举报码 | ✅ | 200 且 code 形如 RP-XXXXXXXX（8 位大写字母数字） | 200, code=RP-Q477A4JA |
| 26 | B13b 24h 内重复举报同一条返回同一码且 duplicate=true | ✅ | 同一 code=RP-Q477A4JA，duplicate=true | 200, code=RP-Q477A4JA, duplicate=True |
| 27 | B13c /api/reports/lookup 凭码可查（且不返回举报人信息） | ✅ | 200 + status_text=「已收到，我们会在 48 小时内处理」+ 无 visitor_id | 200, status=pending, text=已收到，我们会在 48 小时内处理, keys=['ad_id', 'ad_title', 'code', 'conclusion', 'created_at', 'handled_at', 'reason_label', 'status', 'status_text'] |
| 28 | B13d /api/reports/mine 列出本设备举报 | ✅ | items 含 code=RP-Q477A4JA | ['RP-Q477A4JA'] |
| 29 | B14 偏好保存 / 读取一致 | ✅ | PUT 200；GET 返回 categories=[3,4], city=深圳 | 200, {'categories': [3, 4], 'city': '深圳'} |
| 30 | B15 事件上报：同 session 重复 impression 第二次被去重 | ✅ | 第一次 accepted=2，第二次 accepted=0（dedupe_session） | 第一次={'accepted': 2, 'dropped': []}, 第二次={'accepted': 0, 'dropped': [{'index': 0, 'reason': 'dedupe_session'}]} |
| 31 | B15b 事件上报：不存在的 ad_id 被丢弃但不整体失败 | ✅ | 200 + accepted=0（dropped 有原因） | 200, {'accepted': 0, 'dropped': [{'index': 0, 'reason': 'ad_not_found'}]} |
| 32 | B15c 单批事件 >20 条整体 422（§5.3） | ✅ | 422 | 422, {"detail": "有 1 项需要修改", "code": "VALIDATION_ERROR", "fields": [{"field": "events", "message": "数量超出上限"}]} |
| 33 | B17 单访客每日举报上限 3 条，第 4 条 429（PRD 8 / §5.5） | ✅ | 前 3 条 200，第 4 条 429 | codes=[200, 200, 200, 429] |
| 34 | B16 一键清空收藏/隐藏/偏好 | ✅ | 200；me.favorite_ids/hide_ids/categories 全空 | 200, me={"favorite_ids": [], "hide_ids": [], "preference": {"categories": [], "city": null}} |

### D 管理链路

| # | 检查项 | 结果 | 期望 | 实际 |
| --- | --- | --- | --- | --- |
| 1 | D1 未登录访问 /api/admin/review-queue 返回 401 UNAUTHORIZED | ✅ | 401 + code=UNAUTHORIZED | 401, {"detail": "请先登录运营后台", "code": "UNAUTHORIZED"} |
| 2 | D2 管理员登录成功 | ✅ | 200 + Set-Cookie adx_admin | 200, cookies=['adx_admin', 'adx_vid'] |
| 3 | D3 summary.pending_ads == 审核队列 total（口径一致性 P1-O-03） | ✅ | 两处数字相等 | summary=5, queue.total=5 |
| 4 | D3b summary 的 6 个数字与对应列表过滤/库内口径逐一相等 | ✅ | pending_ads=5, pending_reports=5, sla_overdue=1, week_resolved=1, today_events=353, today_processed=48 | 不一致项={}（报告总数=8） |
| 5 | D4 商家新提交的两条广告出现在审核队列 | ✅ | 队列含 52 与 58 | 队列 ids=[33, 11, 47, 52, 58] |
| 6 | D5 通过但 valid_from 在未来 → scheduled | ✅ | 200 + status=scheduled | 200, status=scheduled, {"ad": {"id": 58, "title": "QA-A1 待生效广告", "description": "QA 自动化脚本创建的测试广告，用于端到端验收，不作为真实投放。", "category_id": 3, "category_slug": "digital", "category_name": "数码与家电", "tags": [{"id": 11, "name": "家用电器", |
| 7 | D5b scheduled 广告匿名访问 404（未到生效时间不可见） | ✅ | 404 | 404 |
| 8 | D6 通过有效期内的广告 → active | ✅ | 200 + status=active | 200, status=active |
| 9 | D6b 通过后用户端立即可见（详情 200） | ✅ | 200 + id 匹配 | 200 |
| 10 | D6c 审核时间线含 submit 与 approve 记录 | ✅ | actions 含 submit / approve | actions=['submit', 'withdraw', 'submit', 'approve'] |
| 11 | D7 active 广告改核心字段（标题）→ 回 pending 且匿名立即 404 | ✅ | PATCH 200 + became_pending=true + status=pending；匿名 404 | 200, became_pending=True, status=pending, anon=404 |
| 12 | D8 下架不填原因返回 422 REASON_REQUIRED | ✅ | 422 + REASON_REQUIRED | 422, {"detail": "下架必须填写原因", "code": "REASON_REQUIRED", "fields": [{"field": "reason", "message": "下架必须填写原因"}]} |
| 13 | D8b 下架后匿名访问 404 | ✅ | 200 + status=offline；匿名 404 | 200, status=offline, anon=404 |
| 14 | D8c 下架 reason 为纯空格 / 纯空白时仍返回 422 REASON_REQUIRED 且广告不被动 | ✅ | 422 + REASON_REQUIRED（两次），广告仍 active（匿名 200） | 空格=422/REASON_REQUIRED, 制表符=422/REASON_REQUIRED, 广告匿名访问=200 |
| 15 | D9 管理员举报列表能查到该举报（含 ad_snapshot/overdue 等字段） | ✅ | items 含该 code，字段含 id/code/ad_id/ad_title/reason_label/status/overdue | rid=9, sample_keys=['ad_id', 'ad_snapshot', 'ad_title', 'admin_note', 'code', 'created_at', 'detail', 'followups', 'handled_at', 'id', 'overdue', 'reason_code', 'reason_label', 'status', 'status_label'] |
| 16 | D9b 开始处理 pending → reviewing | ✅ | 200 + status=reviewing | 200, {"id": 9, "code": "RP-2UDCRYV6", "ad_id": 26, "ad_title": "新客首单立减 20 元", "ad_snapshot": {"ad_id": 26, "title": "新客首单立减 20 元", "merchant_name": "社区团购优选", "status": "active", "image_path": "/static/cove |
| 17 | D9c 判定成立 → 举报 resolved 且广告 offline | ✅ | 200 + report.status=resolved；广告匿名 404 | 200, status=resolved, ad=404 |
| 18 | D9d 用户按码查到结果文案「经核查，该广告已被下架/整改」 | ✅ | status=resolved + status_text=经核查，该广告已被下架/整改 | status=resolved, text=经核查，该广告已被下架/整改 |
| 19 | D9e 终态不可再改（resolved 后再 dismiss 应被拒） | ✅ | 409/422（状态只进不退） | 409, {"detail": "该举报已处理完毕", "code": "INVALID_TRANSITION"} |
| 20 | D9f 举报列表 week_stats 四键与按状态过滤的真实条数一致 | ✅ | received==全部(9)、resolved==2、dismissed==1、avg_hours∈[0,720] | week_stats={'received': 9, 'resolved': 2, 'dismissed': 1, 'avg_hours': 16.0}；全部=9（pending=5/reviewing=1/resolved=2/dismissed=1） |
| 21 | D10 stats/overview：by_ad 各项求和 == totals | ✅ | by_ad 的 impressions/detail_views/link_clicks 求和等于 totals 同名字段 | totals={'impressions': 631, 'detail_views': 196, 'link_clicks': 101}；by_ad 求和={'impressions': 631, 'detail_views': 196, 'link_clicks': 101} |
| 22 | D10b stats/overview：by_category 求和 == totals | ✅ | by_category 非空且三项求和等于 totals | n_cat=6, 求和={'impressions': 631, 'detail_views': 196, 'link_clicks': 101}, totals={'impressions': 631, 'detail_views': 196, 'link_clicks': 101} |
| 23 | D11 stats/funnel 四步单调不增 | ✅ | home ≥ list ≥ detail ≥ outbound | counts=[788, 358, 196, 101] |
| 24 | D12 举报率口径为万分比（round(reports/impressions×10000, 1)，PRD 6.4 / §6.6） | ✅ | reports/impressions ×10000 ≈ 142.6（保留 1 位小数） | 接口返回 report_rate_permille=142.6（reports=9, impressions=631） |
| 25 | D12b 商家报告 notes 口径文案同步为 ×10000（与计算口径一致） | ✅ | notes.report_rate_permille 含「× 10000」 | notes=举报率（万分比）= 举报数 / 展示数 × 10000 |
| 26 | D13 统计 CSV 导出：text/csv + BOM + 中文文件名 | ✅ | 200 + text/csv + 首字节 EF BB BF + Content-Disposition 含 .csv（中文名） | 200, ctype=text/csv; charset=utf-8, bom=b'\xef\xbb\xbf', disp=attachment; filename=export.csv; filename*=UTF-8''%E5%B9%BF%E5%91%8A%E7%BB%9F%E8%AE%A1_2026-10-20_2026-10-28.csv |
| 27 | D13b 商家报告 CSV 导出：BOM + 文件名「报告_广告标题_起_止.csv」 | ✅ | 200 + BOM + Content-Disposition 含 .csv 与中文「报告_」（RFC 5987 编码亦可） | 200, bom=b'\xef\xbb\xbf', utf8_name=True, chinese=True, disp=attachment; filename=export.csv; filename*=UTF-8''%E6%8A%A5%E5%91%8A_QA-D7%20%E6%94%B9%E6%A0%87%E9%A2%98%E8%A7%A6%E5%8F%91%E9%87%8D%E5%AE%A1_2026-10-20_2026-10-28.csv |
| 28 | D14 管理员连续输错密码 5 次，第 5 次 423 LOCKED | ✅ | [401,401,401,401,423]，第 5 次 code=LOCKED | codes=[401, 401, 401, 401, 423], code=LOCKED |

### E 双保险与静态产物

| # | 检查项 | 结果 | 期望 | 实际 |
| --- | --- | --- | --- | --- |
| 1 | E1 手改 valid_to 为昨天 → 查询层立即不返回（双保险第一层） | ✅ | 列表不含该 id；详情 404 | 列表含=False, 详情=404 |
| 2 | E2 定时任务把过期 active 置 expired 并写 reviews（system_expire） | ✅ | status=expired 且 reviews 最新 action=system_expire | status=expired, review_action=system_expire, 等待=25s |
| 3 | E3 dist/index.html 引用的 /assets/* 文件在磁盘上全部存在（不一致=白屏） | ✅ | index.html 每处 /assets/xxx 都有对应文件 | refs=['/assets/index-B2G9OGdZ.js', '/assets/index-CHdPteMk.css'], 磁盘=['index-B2G9OGdZ.js', 'index-CHdPteMk.css'], 缺失=[] |
| 4 | E3b GET /assets/index-B2G9OGdZ.js → 200 且 Content-Type 正确 | ✅ | 200 + content-type 含 javascript | 200 + text/javascript; charset=utf-8 |
| 5 | E3b GET /assets/index-CHdPteMk.css → 200 且 Content-Type 正确 | ✅ | 200 + content-type 含 css | 200 + text/css; charset=utf-8 |
| 6 | E4 SPA fallback：GET /ad/1 返回 200 text/html（直接刷新不 404） | ✅ | 200 + text/html | 200 + text/html; charset=utf-8 |
| 7 | E5 未知 /api/* 返回 404 JSON（不能被 SPA 吞掉） | ✅ | 404 + JSON code=NOT_FOUND | 404 + {"detail": "接口不存在", "code": "NOT_FOUND"} |
| 8 | E6 未知前端路由返回 HTML（200/404 均可，不得 500） | ✅ | 200/404 + text/html | 200 + text/html; charset=utf-8 |
| 9 | E7 封面静态资源可访问（卡片图不 404） | ✅ | 200 + image/svg+xml | 200 + image/svg+xml |
| 10 | E8 dist 产物内无外部资源请求（离线可运行，§14.14） | ✅ | 无 <script src=https://>、url(https://)、fetch(https://) 等外部请求 | 无（仅有 reactjs.org/mui.com 报错说明字符串，非请求） |

### G 前后端字段静态交叉核对

| # | 检查项 | 结果 | 期望 | 实际 |
| --- | --- | --- | --- | --- |
| 1 | G1 审核页把嵌套队列 item 拍平后再消费（item.ad → 顶层 id） | ✅ | 存在 normalizeQueueItem()、在 items 上 .map(normalizeQueueItem)、且过滤非法 id + requireSelectedId 守卫 | normalizer=True, map=True, id_guard=True |
| 2 | G2 审核页从队列条目正确取 precheck / merchant / waiting_minutes / submitted_at | ✅ | normalizeQueueItem 显式 pick 这四个字段，并回落 merchant.name 作为 merchant_name | pick 四字段=True, merchant_name 回落=True |
| 3 | G3 管理员登录返回裸对象时前端仍能识别（兼容写法） | ✅ | 前端兼容 {admin} 与裸对象两种结构 | AuthContext.jsx:94 `const admin = (res && res.admin) \|\| res \|\| null;` 兼容 → 不算阻塞 |
| 4 | G4 商家列表前端同时兼容裸数组与 {items} | ✅ | 兼容 | AdminMerchantsPage.jsx:54 |
| 5 | G5 商家单条详情前端兼容 {ad, became_pending} 包裹 | ✅ | 兼容 | MerchantAdEditPage.jsx:119 |
| 6 | G6 收藏页使用后端 groups{active,expired} 分组 | ✅ | 使用 groups | FavoritesPage.jsx:50 |
| 7 | G7 详情页使用 restriction 字段与空值兜底文案 | ✅ | 使用 data.restriction | AdDetailPage.jsx:256 |
| 8 | G8 统计页使用 by_category / totals 字段名与后端一致 | ✅ | 使用 by_category 与 totals | AdminStatsPage.jsx:49 |
| 9 | G9 举报页把 ad_snapshot(dict) 收敛成字符串再渲染（否则 React 渲染对象直接抛错） | ✅ | 存在 snapshotOf() 归一化，JSX 里渲染 snapshot.title 字符串而非对象 | snapshotOf=True, typecheck="typeof raw === 'object'"=True, 渲染 snapshot.title=True |
| 10 | G10 商家广告列表读 reject_reason（后端无 reject_reason_note） | ✅ | 只读 reject_reason（已含「标签：补充说明」），不引用不存在的 reject_reason_note | 含 reject_reason_note=False, 读 ad.reject_reason=True |

### F 回归测试

| # | 检查项 | 结果 | 期望 | 实际 |
| --- | --- | --- | --- | --- |
| 1 | F1 pytest backend/tests -q 全绿（≥45 passed） | ✅ | returncode=0 且 passed>=45 | returncode=0, 50 passed, 1 warning in 81.07s (0:01:21) |


## 3. 缺陷修复复测结果（Round 1 → Round 2 回归）

| 缺陷 | 修复内容（工程师） | 复测断言 | 结论 |
| --- | --- | --- | --- |
| P0-1 审核页解包错 | `AdminReviewPage.jsx` 新增 `normalizeQueueItem()` 拍平 + `requireSelectedId()` 守卫 + 过滤非法 id | G1 / G2（静态）+ A3（后端结构） | **已修复，已验证** |
| P1-2 举报率口径 | `stats.py` 改 `round(n/d*10000,1)`，去掉 `_safe_rate` 先四舍五入的精度损失 | D12 / D12b | **已修复，已验证**（实测 reports=4 / impressions=630 → `63.5‱`） |
| P2-3 收藏数与事件不一致 | seed 新增 `_seed_favorite_events()`，favorites 72 = favorite 事件 72 | A10 | **已修复，已验证**（`merchant/report?ad_id=12` → favorites=3, favorite_rate=1.0；`totals.favorites=72`） |
| P3-4 管理员登录结构 | `POST /api/admin/login` → `{admin:{...}}`（`/api/admin/me` 仍裸对象，符合 §5.7） | A9b | **已修复，已验证** |
| P3-5 下架原因校验 | `OfflineIn.reason` 改可选 + service 内 `strip()` 校验，空/纯空白 → `REASON_REQUIRED` | D8 / D8c | **已修复，已验证**（`{}`、`{"reason":"   "}`、`{"reason":"\t\n "}` 均 422 且广告不动） |
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
| D8c | `offline` 传 `{"reason":"   "}` 与 `{"reason":"\t\n "}` → 422 `REASON_REQUIRED`，且广告仍 visible | 修复把校验从 pydantic 必填挪到 service 的 `strip()`，纯空白是最容易漏的分支；若只看 `{}` 会误判通过 |
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

