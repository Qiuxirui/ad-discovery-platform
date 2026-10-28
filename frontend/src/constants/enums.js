/**
 * 枚举中文字典（兜底副本）。
 * 运行时以 GET /api/meta 为唯一权威来源；此处仅用于 meta 未返回时的展示兜底，
 * 文案与 ARCHITECTURE.md §6.1 逐字一致。
 */

/** 广告状态 → 中文 + 标签色 */
export const AD_STATUS = {
  draft: { label: '草稿', color: '#5A6472' },
  pending: { label: '待审核', color: '#B26A00' },
  scheduled: { label: '待生效', color: '#1F6F8B' },
  active: { label: '展示中', color: '#1E7A46' },
  rejected: { label: '已拒绝', color: '#B3261E' },
  offline: { label: '已下架', color: '#5A6472' },
  expired: { label: '已过期', color: '#8A8F98' },
};

/** 商家端「我的广告」页签顺序 */
export const AD_STATUS_TABS = [
  { code: 'all', label: '全部' },
  { code: 'draft', label: '草稿' },
  { code: 'pending', label: '待审核' },
  { code: 'scheduled', label: '待生效' },
  { code: 'active', label: '展示中' },
  { code: 'rejected', label: '已拒绝' },
  { code: 'offline', label: '已下架' },
  { code: 'expired', label: '已过期' },
];

/** 举报状态 → 中文 + 用户可见文案 + 标签色 */
export const REPORT_STATUS = {
  pending: {
    label: '待处理',
    userText: '已收到，我们会在 48 小时内处理',
    color: '#B26A00',
  },
  reviewing: {
    label: '处理中',
    userText: '正在核查该广告',
    color: '#1F6F8B',
  },
  resolved: {
    label: '已处理',
    userText: '经核查，该广告已被下架/整改',
    color: '#1E7A46',
  },
  dismissed: {
    label: '不成立',
    userText: '经核查，暂未发现违反平台规则的情况',
    color: '#8A8F98',
  },
};

/** 举报状态页签（管理端） */
export const REPORT_STATUS_TABS = [
  { code: 'all', label: '全部' },
  { code: 'pending', label: '待处理' },
  { code: 'reviewing', label: '处理中' },
  { code: 'resolved', label: '已处理' },
  { code: 'dismissed', label: '不成立' },
];

/** 排序项：不存在付费加权排序 */
export const SORT_OPTIONS = [
  { code: 'latest', label: '最新发布' },
  { code: 'ending', label: '即将结束' },
  { code: 'popular', label: '最多收藏' },
];

/** 事件类型（前端只报原始事实，去重全部由后端负责） */
export const EVENT_TYPES = [
  'impression',
  'detail_view',
  'link_click',
  'favorite',
  'unfavorite',
  'hide',
  'report',
  'page_view',
  'external_blocked',
  'link_click_suppressed',
];

/** 页面标识枚举 */
export const PAGE_KEYS = ['home', 'list', 'search', 'detail', 'favorites'];

/** 有效期筛选 */
export const ENDING_OPTIONS = [
  { code: '', label: '不限有效期' },
  { code: '1', label: '即将结束（48 小时内）' },
];

/** 优惠筛选 */
export const PROMO_OPTIONS = [
  { code: '', label: '不限优惠' },
  { code: '1', label: '仅看有优惠' },
];

/**
 * 取广告状态中文标签。
 * @param {string} code
 * @returns {string}
 */
export function adStatusLabel(code) {
  return (AD_STATUS[code] && AD_STATUS[code].label) || code || '未知';
}

/**
 * 取广告状态标签色。
 * @param {string} code
 * @returns {string}
 */
export function adStatusColor(code) {
  return (AD_STATUS[code] && AD_STATUS[code].color) || '#5A6472';
}

/**
 * 取举报状态中文标签。
 * @param {string} code
 * @returns {string}
 */
export function reportStatusLabel(code) {
  return (REPORT_STATUS[code] && REPORT_STATUS[code].label) || code || '未知';
}

/**
 * 取举报状态用户可见文案。
 * @param {string} code
 * @returns {string}
 */
export function reportStatusText(code) {
  return (REPORT_STATUS[code] && REPORT_STATUS[code].userText) || '状态更新中';
}

/**
 * 预检结果机器码 → 中文短语（后端 `AdService.precheck()` 的 code，
 * 审核队列字段 `precheck_code`）。仅用于「预检未通过（xxx）」的括注。
 */
export const PRECHECK_CODE_LABELS = {
  PRECHECK_PASSED: '通过',
  BANNED_INDUSTRY: '内容命中禁投行业关键词',
  URL_SHORTENER: '落地页是短链接',
  URL_SCHEME: '落地页协议不安全',
  URL_BARE_IP: '落地页直接用了 IP 地址',
  URL_PRIVATE_HOST: '落地页指向本机或内网',
  URL_SUFFIX: '落地页是文件或压缩包',
  URL_TOO_LONG: '落地页地址过长',
  URL_INVALID: '落地页地址格式不正确',
  DATE_EXPIRED: '排队期间已过有效期',
  DATE_TOO_LONG: '有效期超过上限',
  DATE_REVERSED: '有效期起止颠倒',
};

/**
 * 取预检结果机器码的中文短语。
 * @param {string} code
 * @returns {string}
 */
export function precheckCodeLabel(code) {
  if (!code) return '原因未提供';
  return PRECHECK_CODE_LABELS[code] || code;
}
