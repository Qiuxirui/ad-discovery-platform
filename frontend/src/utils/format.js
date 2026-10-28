/**
 * 展示格式化工具（纯函数，无副作用）。
 * 注意：所有"剩余天数/是否即将结束"一律取后端预算字段（days_left / expiring_soon），
 * 前端不做任何时区换算（ARCHITECTURE.md §3.3）。
 */

/**
 * 把 "YYYY-MM-DD" 或 ISO 字符串格式化为中文日期。
 * @param {string|null|undefined} value
 * @param {{withYear?: boolean}} [options]
 * @returns {string}
 */
export function formatDateCN(value, options = {}) {
  const { withYear = false } = options;
  if (!value) return '未提供';
  const text = String(value);
  // 后端已给出本地日期字符串，直接截取，避免 new Date 造成时区漂移
  const localDateMatch = /^(\d{4})-(\d{2})-(\d{2})/.exec(text);
  if (localDateMatch) {
    const [, y, m, d] = localDateMatch;
    if (withYear) return `${y}-${m}-${d}`;
    return `${m}-${d}`;
  }
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return text;
  const y = parsed.getFullYear();
  const m = String(parsed.getMonth() + 1).padStart(2, '0');
  const d = String(parsed.getDate()).padStart(2, '0');
  return withYear ? `${y}-${m}-${d}` : `${m}-${d}`;
}

/**
 * 起止日期区间：跨年时两端都带年份。
 * @param {string} from
 * @param {string} to
 * @returns {string}
 */
export function formatRangeCN(from, to) {
  if (!from && !to) return '未提供';
  if (!from) return `至 ${formatDateCN(to, { withYear: true })}`;
  if (!to) return `${formatDateCN(from, { withYear: true })} 起`;
  const fromYear = String(from).slice(0, 4);
  const toYear = String(to).slice(0, 4);
  const crossYear = fromYear && toYear && fromYear !== toYear;
  return `${formatDateCN(from, { withYear: crossYear })} 至 ${formatDateCN(to, { withYear: true })}`;
}

/**
 * 列表卡片有效期文案："有效至 11-30"。
 * @param {string|null|undefined} validToLocalDate
 * @returns {string}
 */
export function validToText(validToLocalDate) {
  if (!validToLocalDate) return '有效期未提供';
  return `有效至 ${formatDateCN(validToLocalDate)}`;
}

/**
 * 详情页剩余天数文案（唯一来源是后端 days_left）。
 * @param {number|null|undefined} daysLeft
 * @returns {string}
 */
export function daysLeftText(daysLeft) {
  if (daysLeft === null || daysLeft === undefined || Number.isNaN(Number(daysLeft))) {
    return '剩余天数未提供';
  }
  const days = Number(daysLeft);
  if (days < 0) return '已结束';
  if (days === 0) return '今天结束';
  return `剩余 ${days} 天`;
}

/** 「即将结束」徽标文案 */
export const ENDING_SOON_LABEL = '即将结束';

/**
 * 计数文案（千分位）。
 * @param {number|string|null|undefined} value
 * @returns {string}
 */
export function countText(value) {
  const num = Number(value);
  if (value === null || value === undefined || Number.isNaN(num)) return '0';
  return num.toLocaleString('zh-CN');
}

/**
 * 百分比文案，必须带分母说明。
 * @param {number|null|undefined} numerator
 * @param {number|null|undefined} denominator
 * @returns {string} 例："3.2%（12/375）"
 */
export function percentText(numerator, denominator) {
  const n = Number(numerator) || 0;
  const d = Number(denominator) || 0;
  if (d <= 0) return '—（分母为 0）';
  const rate = (n / d) * 100;
  return `${rate.toFixed(1)}%（${countText(n)}/${countText(d)}）`;
}

/**
 * 比率文案，用于后端已给 0~1 的比率时（仍需传入分母）。
 * @param {number|null|undefined} rate
 * @param {number|null|undefined} numerator
 * @param {number|null|undefined} denominator
 * @returns {string}
 */
export function rateText(rate, numerator, denominator) {
  const d = Number(denominator) || 0;
  if (d <= 0) return '—（分母为 0）';
  const r = Number(rate);
  const value = Number.isNaN(r) ? 0 : r;
  const pct = value <= 1 ? value * 100 : value;
  return `${pct.toFixed(1)}%（${countText(numerator)}/${countText(denominator)}）`;
}

/**
 * 万分比文案（举报率口径）。
 * @param {number|null|undefined} permille
 * @returns {string}
 */
export function permilleText(permille) {
  const value = Number(permille);
  if (permille === null || permille === undefined || Number.isNaN(value)) return '0.0‱';
  return `${value.toFixed(1)}‱`;
}

/**
 * 等待时长文案（审核队列）。
 * @param {number|null|undefined} minutes
 * @returns {string}
 */
export function waitMinutesText(minutes) {
  const value = Number(minutes);
  if (!minutes && minutes !== 0) return '刚刚提交';
  if (Number.isNaN(value)) return '刚刚提交';
  if (value < 60) return `等待 ${value} 分钟`;
  const hours = Math.floor(value / 60);
  const rest = value % 60;
  if (hours < 24) return rest ? `等待 ${hours} 小时 ${rest} 分` : `等待 ${hours} 小时`;
  const days = Math.floor(hours / 24);
  return `等待 ${days} 天 ${hours % 24} 小时`;
}

/**
 * ISO 时间 → 北京时间展示（"2026-10-27 15:04"）。
 * 使用 Intl 指定 UTC+8，避免依赖浏览器时区。
 * @param {string|null|undefined} iso
 * @returns {string}
 */
export function formatDateTimeCN(iso) {
  if (!iso) return '未提供';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return String(iso);
  const parts = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(date);
  const pick = (type) => {
    const item = parts.find((part) => part.type === type);
    return item ? item.value : '';
  };
  return `${pick('year')}-${pick('month')}-${pick('day')} ${pick('hour')}:${pick('minute')}`;
}

/**
 * ISO 时间 → 北京时间日期（"2026-10"）。
 * @param {string|null|undefined} iso
 * @returns {string}
 */
export function formatMonthCN(iso) {
  if (!iso) return '未提供';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return String(iso).slice(0, 7);
  const parts = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
  }).formatToParts(date);
  const pick = (type) => {
    const item = parts.find((part) => part.type === type);
    return item ? item.value : '';
  };
  return `${pick('year')}-${pick('month')}`;
}

/**
 * 今天（北京）的 YYYY-MM-DD，供日期区间选择器默认值使用。
 * @param {number} [offsetDays] 相对今天的天数偏移
 * @returns {string}
 */
export function todayCST(offsetDays = 0) {
  const now = new Date();
  const shifted = new Date(now.getTime() + offsetDays * 86400000);
  const parts = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(shifted);
  const pick = (type) => {
    const item = parts.find((part) => part.type === type);
    return item ? item.value : '';
  };
  return `${pick('year')}-${pick('month')}-${pick('day')}`;
}
