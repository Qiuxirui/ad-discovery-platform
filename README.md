# 广告发现站 · 广告自主浏览与智能分类平台（MVP）

把被动打断用户的广告，变成用户可以**自主发现、筛选和管理**的商业信息。

响应式 Web，匿名可浏览，商家自助提交，运营后台人工审核，全站商业内容强制标注「广告」。
本项目按《广告自主浏览与智能分类平台_一人公司项目计划书_V1.0》的 MVP 范围实现，对应 PRD 43 条 P0 + 9 条 P1。

---

## 1. 快速开始

### 方式一：一键启动（推荐）

双击根目录的 **`start.bat`**。首次运行会自动建库灌种子数据，然后打开浏览器访问：

```
http://127.0.0.1:8000
```

### 方式二：命令行

```powershell
# 1. 建虚拟环境并装依赖（只需一次）
python -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements.txt

# 2. 灌种子数据（只需一次；已有库会跳过）
.venv\Scripts\python -m backend.seed

# 3. 构建前端（只需一次；改了前端代码要重跑）
scripts\build.ps1

# 4. 启动
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### 方式三：开发模式（前端热更新）

```powershell
scripts\dev.ps1
```

- 后端 `http://127.0.0.1:8000`（`--reload` 自动重载）
- 前端 `http://127.0.0.1:5173`（Vite HMR，`/api` 与 `/static` 自动代理到 8000）

> 生产/演示请用方式一或二：单端口 8000，前端由后端同源托管，无跨域、无外部请求。

---

## 2. 初始账号

| 角色 | 入口 | 账号 | 密码 |
|---|---|---|---|
| 运营管理员 | `/admin/login` | `admin` | `adx-admin-2026` |
| 商家（8 个） | `/merchant/login` | `13800001001` ~ `13800001008` | `adx-merchant-2026` |

**普通用户不需要注册**，直接访问首页即可浏览、搜索、收藏、举报。匿名身份存在签名 Cookie `adx_vid` 里（HttpOnly，180 天），清理浏览器数据即丢失。

> 改管理员密码：启动前设置环境变量 `ADX_ADMIN_PASSWORD`，或登录后到后台修改。
> 正式上线前**必须**改掉默认密码。

---

## 3. 功能地图

### 用户端（匿名可用）

| 页面 | 路由 | 说明 |
|---|---|---|
| 首页 | `/` | 产品说明条 + 6 类别入口（显示在架数）+ 最新广告 |
| 分类浏览 | `/c/:slug` | 二级标签横滑、城市/有效期/优惠筛选、3 种排序、加载更多 |
| 搜索 | `/search` | 标题/描述/标签命中，空态给推荐类别 |
| 广告详情 | `/ad/:id` | 「广告」标识、商家、有效期剩余、限制条款、同类推荐 |
| 外链中间页 | `/go/:adId` | 显示目标域名与完整 URL，5 秒后可点「继续前往」，可疑链接直接阻断 |
| 收藏 | `/favorites` | 已结束的单独分组 |
| 偏好设置 | `/preferences` | 兴趣类别、常看城市、已隐藏恢复、清除全部数据 |
| 举报查询 | `/report-status` | 凭举报码或本设备记录查处置进度 |
| 政策页 | `/policy/ads｜privacy｜report`、`/about` | 广告政策、隐私说明、举报流程 |

### 商家端

注册即入驻 → 五步表单新建广告（右侧实时预览）→ 保存草稿 / 提交审核 → 我的广告（状态分页、被拒原因展开、撤回、复制）→ 效果报告（展示量/详情查看量/外链点击量/点击率 + 按日趋势 + CSV 导出）。

### 运营后台

运营首页（待审/待处理举报/SLA 超时/今日事件）→ 审核队列（左列表右详情，含预检结果与商家历史，通过 / 拒绝 / 编辑后通过）→ 广告台账（筛选、操作历史、下架）→ 举报处理（开始处理 / 成立 / 驳回）→ 商家管理（停用、核验标记）→ 分类标签维护 → 数据统计（总览、广告排行、类别分布、转化漏斗、CSV 导出）。

---

## 4. 目录结构

```
AD/
├── start.bat                 # 一键启动（自动灌种子 + 起服务）
├── scripts/
│   ├── build.ps1             # 构建前端到 frontend/dist
│   └── dev.ps1               # 开发模式（uvicorn --reload + vite）
├── docs/
│   ├── PRD.md                # 产品需求文档（60 条需求）
│   ├── ARCHITECTURE.md       # 系统架构（14 张表 / 60 个接口 / 12 个任务）
│   └── QA-REPORT.md          # 端到端验收报告
├── backend/
│   ├── main.py               # 应用装配：路由 / 静态资源 / SPA fallback / 定时任务
│   ├── config.py             # 配置（ADX_ 环境变量）
│   ├── database.py           # SQLite 引擎（WAL + 外键）
│   ├── models.py             # 14 张表 ORM
│   ├── constants.py          # 城市、原因、阈值、状态字典、类目色板
│   ├── security.py           # 密码哈希（pbkdf2_sha256）、JWT、登录锁定
│   ├── visitor.py            # 匿名访客 Cookie 签发与校验（HMAC）
│   ├── scheduler.py          # 每 60s 把过期/生效落库（可见性双保险的第 2 层）
│   ├── seed.py               # 种子数据（--reset 重建 / --no-events 不造事件）
│   ├── models | schemas | services | routers | utils | tests
│   ├── data/                 # adx.db（gitignore）
│   └── static/               # covers（广告封面 SVG）、uploads（商家上传图）
└── frontend/
    ├── src/{pages,components,api,hooks,context,constants,utils,tracker}
    └── dist/                 # 构建产物（gitignore，由 build.ps1 生成）
```

---

## 5. 常用命令

| 用途 | 命令 |
|---|---|
| 启动服务 | `start.bat` 或 `.venv\Scripts\python -m uvicorn backend.main:app --port 8000` |
| 重建数据库 | `.venv\Scripts\python -m backend.seed --reset` |
| 只灌数据不造事件 | `.venv\Scripts\python -m backend.seed --reset --no-events` |
| 构建前端 | `scripts\build.ps1` |
| 开发模式 | `scripts\dev.ps1` |
| 跑测试 | `.venv\Scripts\python -m pytest backend/tests -q` |
| 端到端验收 | `.venv\Scripts\python scripts\e2e.py`（需先启动服务；跑完会污染数据，记得重建库） |

---

## 6. 配置项

全部通过 `ADX_` 前缀环境变量覆盖，未设置时用默认值：

| 变量 | 默认 | 说明 |
|---|---|---|
| `ADX_DB_PATH` | `backend/data/adx.db` | 数据库文件路径（相对路径以 `backend/` 为基准） |
| `ADX_SECRET` | 自动生成 `backend/.secret` | JWT 与 Cookie 签名密钥 |
| `ADX_ADMIN_USERNAME` | `admin` | 初始管理员账号 |
| `ADX_ADMIN_PASSWORD` | `adx-admin-2026` | 初始管理员密码（**上线前必改**） |
| `ADX_COOKIE_SECURE` | `0` | 走 HTTPS 时置 `1`，本地 http 必须为 `0` |
| `ADX_TOKEN_TTL_SECONDS` | `259200` | 登录态有效期（3 天） |
| `ADX_SCHEDULER_ENABLED` | `1` | 是否启用过期/生效定时任务 |
| `ADX_SCHEDULER_INTERVAL_SECONDS` | `60` | 定时任务轮询间隔 |

---

## 7. 数据维护

- **重置演示数据**：`.venv\Scripts\python -m backend.seed --reset`
  > ⚠️ 重建前**先停掉服务**。服务运行时数据库处于 WAL 模式，重建后数据会留在 `-wal` 文件里，重启前后看起来像"空库"。停服务 → 重建 → 再启动即可。
- **备份**：停止服务后直接复制 `backend/data/adx.db`；或执行
  `sqlite3 backend/data/adx.db "VACUUM INTO 'backup.db'"`
- **换 PostgreSQL**：改 `backend/database.py` 的连接串并装 `psycopg`，模型层不用动（SQLAlchemy 2.0）。

---

## 8. 技术栈与关键设计

- **后端**：FastAPI + SQLAlchemy 2.0 + SQLite（WAL），Pydantic v2 校验，PyJWT + HttpOnly Cookie
- **前端**：React 18 + Vite 6 + MUI 6 + React Router 6，无 Redux（Context + 自定义 hooks）
- **部署形态**：单端口同源，后端同时提供 `/api`、`/static`、`/assets`，SPA 路由由 catch-all 回退 `index.html`
- **零外链**：不使用 CDN、外部字体、外部图片；广告封面由后端按「类别色板 + 标题哈希」生成确定性 SVG
- **可见性双保险**：查询层强制 `status=active AND valid_from<=now<valid_to`（单点实现在 `services/visibility.py`），同时 60s 定时任务把过期状态落库——任一侧失效都不会让过期广告继续露出
- **事件口径**：6 类事件全部在服务端去重（impression 按 session+ad、detail_view 30 分钟、link_click 10 秒且单日 20 次上限、favorite/hide 唯一、report 24 小时合并），前端只上报原始事实
- **合规**：「广告」角标常驻不随 hover 消失；外链强制中间页且不自动跳转；医疗/金融/博彩/酒类/成人/政治类内容不接入；举报四态可追踪；过期广告自动隐藏；后台必须登录且权限在服务端判定

---

## 9. 已实现 / 未实现

**已实现**：PRD 全部 P0（43 条）+ P1 中的事件埋点、基础分析、漏斗、商家报告及导出、标签维护、商家管理、举报 SLA 提醒、扩展排序。

**未实现（有意留到验证之后）**：P2 全部（试点订单、线上支付）、原生 App、AI 推荐/画像/竞价、自动抓取全网广告、平台内交易、社交评论、跨站追踪；账号注销与匿名数据合并（P1 后续）；自动备份（README 给了手动命令）；服务端 OG 图生成。

**已知简化**：详情页分享为浏览器原生复制链接，无服务端 OG 卡片；商家上传图不做裁剪（`object-fit: cover` 兜底）；政策页联系方式为「站内举报入口 / 联系运营者」，正式上线前需补真实联系方式。

---

## 10. 许可

本项目采用 [**PolyForm Noncommercial License 1.0.0**](LICENSE) 授权。

- **允许**：个人学习、研究、实验、爱好项目，以及学校、公益机构、公共研究机构、政府部门等非商业组织使用。
- **禁止**：任何商业用途——包括但不限于打包销售、SaaS 收费、作为商业产品或服务的一部分、在企业内部用于商业运营。
- **需要商业授权**：请到本仓库开 Issue 联系作者单独获取。

作者本人作为版权所有者不受上述限制。`docs/` 中的产品与商业设计文档同样保留所有权利。

