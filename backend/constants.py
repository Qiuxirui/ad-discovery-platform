"""全站唯一字典来源：城市、原因、状态、排序、事件、阈值、色板、黑名单。

前端字典经 ``GET /api/meta`` 获取，后端内部一律引用本模块常量。
"""

from __future__ import annotations

__all__ = [
    "ACTOR_TYPE_LABELS",
    "ADMIN_LOCK_MINUTES",
    "ADMIN_LOCK_THRESHOLD",
    "AD_STATUS",
    "AD_STATUS_COLORS",
    "AD_STATUS_LABELS",
    "AD_STATUS_OPTIONS",
    "BANNED_KEYWORDS",
    "CATEGORY_PALETTES",
    "CITIES",
    "DAILY_NEW_ADS_LIMIT",
    "DANGEROUS_SUFFIXES",
    "EVENT_TYPES",
    "FAVORITES_LIMIT",
    "HIDES_LIMIT",
    "MAX_PAGE_SIZE",
    "ONLINE_ADS_LIMIT",
    "PAGE_IDS",
    "PAGE_SIZE",
    "REJECT_REASONS",
    "REJECT_REASON_LABELS",
    "REPORT_DAILY_LIMIT",
    "REPORT_REASONS",
    "REPORT_REASON_LABELS",
    "REPORT_SLA_HOURS",
    "REPORT_STATUS",
    "REPORT_STATUS_LABELS",
    "REPORT_STATUS_OPTIONS",
    "REPORT_STATUS_USER_TEXT",
    "REVIEW_ACTION_LABELS",
    "SHORTENER_DOMAINS",
    "SORT_OPTIONS",
    "SORT_LABELS",
    "TAG_MAX",
    "TAG_MIN",
    "VALID_DAYS_LIMIT",
]

# ---------------------------------------------------------------- 城市（30 城 + 全国）
CITIES: list[str] = [
    "全国",
    "北京",
    "上海",
    "广州",
    "深圳",
    "杭州",
    "南京",
    "苏州",
    "成都",
    "重庆",
    "武汉",
    "西安",
    "天津",
    "长沙",
    "郑州",
    "青岛",
    "宁波",
    "东莞",
    "佛山",
    "合肥",
    "福州",
    "厦门",
    "济南",
    "昆明",
    "大连",
    "沈阳",
    "无锡",
    "南昌",
    "贵阳",
    "石家庄",
    "太原",
]

# ---------------------------------------------------------------- 广告状态机（7 态）
AD_STATUS_DRAFT = "draft"
AD_STATUS_PENDING = "pending"
AD_STATUS_SCHEDULED = "scheduled"
AD_STATUS_ACTIVE = "active"
AD_STATUS_REJECTED = "rejected"
AD_STATUS_OFFLINE = "offline"
AD_STATUS_EXPIRED = "expired"

AD_STATUS: list[str] = [
    AD_STATUS_DRAFT,
    AD_STATUS_PENDING,
    AD_STATUS_SCHEDULED,
    AD_STATUS_ACTIVE,
    AD_STATUS_REJECTED,
    AD_STATUS_OFFLINE,
    AD_STATUS_EXPIRED,
]

AD_STATUS_LABELS: dict[str, str] = {
    AD_STATUS_DRAFT: "草稿",
    AD_STATUS_PENDING: "待审核",
    AD_STATUS_SCHEDULED: "待生效",
    AD_STATUS_ACTIVE: "展示中",
    AD_STATUS_REJECTED: "已拒绝",
    AD_STATUS_OFFLINE: "已下架",
    AD_STATUS_EXPIRED: "已过期",
}

AD_STATUS_COLORS: dict[str, str] = {
    AD_STATUS_DRAFT: "#5A6472",
    AD_STATUS_PENDING: "#B26A00",
    AD_STATUS_SCHEDULED: "#1F6F8B",
    AD_STATUS_ACTIVE: "#1E7A46",
    AD_STATUS_REJECTED: "#B3261E",
    AD_STATUS_OFFLINE: "#5A6472",
    AD_STATUS_EXPIRED: "#8A8F98",
}

AD_STATUS_OPTIONS: list[dict[str, str]] = [
    {"code": code, "label": AD_STATUS_LABELS[code], "color": AD_STATUS_COLORS[code]} for code in AD_STATUS
]

# ---------------------------------------------------------------- 举报状态（4 态）
REPORT_STATUS: list[str] = ["pending", "reviewing", "resolved", "dismissed"]

REPORT_STATUS_LABELS: dict[str, str] = {
    "pending": "待处理",
    "reviewing": "处理中",
    "resolved": "已处理",
    "dismissed": "不成立",
}

REPORT_STATUS_USER_TEXT: dict[str, str] = {
    "pending": "已收到，我们会在 48 小时内处理",
    "reviewing": "正在核查该广告",
    "resolved": "经核查，该广告已被下架/整改",
    "dismissed": "经核查，暂未发现违反平台规则的情况",
}

REPORT_STATUS_OPTIONS: list[dict[str, str]] = [
    {"code": code, "label": REPORT_STATUS_LABELS[code], "text": REPORT_STATUS_USER_TEXT[code]}
    for code in REPORT_STATUS
]

# ---------------------------------------------------------------- 举报原因（6 项）
REPORT_REASONS: list[dict[str, str]] = [
    {"code": "false_claim", "label": "虚假宣传"},
    {"code": "expired_info", "label": "过期信息"},
    {"code": "price_wrong", "label": "价格不实"},
    {"code": "suspicious_link", "label": "链接可疑"},
    {"code": "inappropriate", "label": "不当内容"},
    {"code": "other", "label": "其他"},
]

REPORT_REASON_LABELS: dict[str, str] = {item["code"]: item["label"] for item in REPORT_REASONS}

# ---------------------------------------------------------------- 拒绝原因（6 项）
REJECT_REASONS: list[dict[str, str]] = [
    {"code": "false_claim", "label": "虚假宣传或夸大功效"},
    {"code": "incomplete", "label": "信息不完整或不实"},
    {"code": "bad_link", "label": "链接不可访问或可疑"},
    {"code": "image_mismatch", "label": "图片与内容不符"},
    {"code": "banned_industry", "label": "禁投行业或违禁品"},
    {"code": "other", "label": "其他（需说明）"},
]

REJECT_REASON_LABELS: dict[str, str] = {item["code"]: item["label"] for item in REJECT_REASONS}

# ---------------------------------------------------------------- 排序
SORT_OPTIONS: list[dict[str, str]] = [
    {"code": "latest", "label": "最新发布"},
    {"code": "ending", "label": "即将结束"},
    {"code": "popular", "label": "最多收藏"},
]

SORT_LABELS: dict[str, str] = {item["code"]: item["label"] for item in SORT_OPTIONS}

# ---------------------------------------------------------------- 事件
EVENT_TYPES: tuple[str, ...] = (
    "impression",
    "detail_view",
    "link_click",
    "favorite",
    "unfavorite",
    "hide",
    "report",
    "page_view",
    "external_blocked",
    "link_click_suppressed",
)

PAGE_IDS: tuple[str, ...] = ("home", "list", "search", "detail", "favorites")

# ---------------------------------------------------------------- 分页与上限
PAGE_SIZE = 24
MAX_PAGE_SIZE = 60
FAVORITES_LIMIT = 200
HIDES_LIMIT = 500
DAILY_NEW_ADS_LIMIT = 5
ONLINE_ADS_LIMIT = 20
VALID_DAYS_LIMIT = 90
TAG_MIN = 1
TAG_MAX = 3

# ---------------------------------------------------------------- 举报 / 登录风控
REPORT_DAILY_LIMIT = 3
REPORT_SLA_HOURS = 24
ADMIN_LOCK_THRESHOLD = 5
ADMIN_LOCK_MINUTES = 15

# ---------------------------------------------------------------- 禁投行业关键词（PRD N7 / P0-K-01）
BANNED_KEYWORDS: list[str] = [
    "医疗",
    "治病",
    "疗效",
    "处方",
    "药品",
    "医美贷",
    "贷款",
    "理财",
    "荐股",
    "炒股",
    "炒币",
    "比特币",
    "虚拟币",
    "博彩",
    "彩票",
    "赌场",
    "下注",
    "白酒",
    "茅台",
    "烈酒",
    "成人用品",
    "情趣",
    "色情",
    "代孕",
    "招嫖",
    "政治",
    "选举",
    "高仿",
    "假货",
    "A货",
    "走私",
    "水货",
    "翻新机",
]

# ---------------------------------------------------------------- URL 安全
SHORTENER_DOMAINS: list[str] = [
    "bit.ly",
    "tinyurl.com",
    "t.cn",
    "dwz.cn",
    "goo.gl",
    "is.gd",
    "ow.ly",
    "t.ly",
    "rebrand.ly",
    "cutt.ly",
    "suo.im",
    "url.cn",
    "v.gd",
    "shorte.st",
    "tiny.cc",
    "rb.gy",
    "x.gd",
    "bit.do",
    "s.id",
]

DANGEROUS_SUFFIXES: list[str] = [
    ".exe",
    ".msi",
    ".apk",
    ".dmg",
    ".bat",
    ".cmd",
    ".scr",
    ".vbs",
    ".jar",
    ".zip",
    ".rar",
    ".7z",
    ".js",
    ".pkg",
    ".deb",
    ".sh",
]

#: 内网 / 本机主机名片段
PRIVATE_HOST_MARKERS: tuple[str, ...] = (
    "localhost",
    "127.",
    "0.0.0.0",
    "::1",
    "10.",
    "192.168.",
    ".local",
    ".internal",
    ".lan",
)

# ---------------------------------------------------------------- 类别色板（封面 SVG 用；强调橙不参与装饰）
CATEGORY_PALETTES: dict[str, tuple[str, str, str]] = {
    "local-service": ("#1F3A5F", "#2F6F7E", "#E8F1F3"),
    "deals": ("#1F3A5F", "#4C7A9B", "#EAF0F6"),
    "digital": ("#16324F", "#3E7CA6", "#E6F0F7"),
    "home": ("#24425F", "#4F7F72", "#E9F2EE"),
    "fashion": ("#2B3A5C", "#6C7F9E", "#EEF0F7"),
    "sports-pet": ("#1F3A5F", "#3C7F6A", "#E7F2EC"),
}

# ---------------------------------------------------------------- 审核动作（reviews.action）
REVIEW_ACTION_LABELS: dict[str, str] = {
    "submit": "提交审核",
    "withdraw": "撤回为草稿",
    "abandon": "放弃重提",
    "approve": "审核通过",
    "reject": "审核拒绝",
    "edit_approve": "编辑后通过",
    "offline": "下架",
    "restore": "恢复审核",
    "system_expire": "系统置为已过期",
    "system_activate": "系统置为展示中",
    "merchant_edit": "商家编辑",
    "duplicate": "复制为新广告",
}

ACTOR_TYPE_LABELS: dict[str, str] = {
    "merchant": "商家",
    "admin": "运营管理员",
    "system": "系统",
}

# ---------------------------------------------------------------- 数据整型常量（便于统一引用）
MAX_IMAGE_BYTES = 2 * 1024 * 1024
ALLOWED_IMAGE_EXTS: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp")
UPLOAD_URL_PREFIX = "/static/uploads"
COVER_URL_PREFIX = "/static/covers"
