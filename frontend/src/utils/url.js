/**
 * URL / 筛选状态工具。
 * 筛选条件全部写入 URL query，保证可分享、刷新保持、前进后退可还原（PRD §7.2）。
 */

import { buildQueryString } from '../api/client.js';

/** 列表页筛选维度白名单 */
export const LIST_QUERY_KEYS = ['tag', 'category', 'city', 'ending', 'promo', 'sort', 'q', 'page'];

/**
 * 对象 → 查询串（空值跳过）。
 * @param {Record<string, unknown>} params
 * @returns {string}
 */
export function buildQuery(params) {
  return buildQueryString(params);
}

/**
 * URLSearchParams → 普通对象（同键多值取最后一个，兼容 ?a=1&a=2）。
 * @param {URLSearchParams} searchParams
 * @returns {Record<string, string>}
 */
export function parseQuery(searchParams) {
  const result = {};
  if (!searchParams) return result;
  searchParams.forEach((value, key) => {
    result[key] = value;
  });
  return result;
}

/**
 * 生成规范化列表路径（分页参数 page=1 省略，避免重复历史记录）。
 * @param {string} pathname 例：`/c/digital`
 * @param {Record<string, unknown>} params
 * @returns {string}
 */
export function canonicalListPath(pathname, params = {}) {
  const cleaned = {};
  Object.keys(params).forEach((key) => {
    const value = params[key];
    if (value === undefined || value === null || value === '') return;
    if (key === 'page' && String(value) === '1') return;
    cleaned[key] = value;
  });
  // 固定字段顺序，保证同一筛选组合生成同一 URL（利于分享与比较）
  const ordered = {};
  LIST_QUERY_KEYS.forEach((key) => {
    if (cleaned[key] !== undefined) ordered[key] = cleaned[key];
  });
  Object.keys(cleaned).forEach((key) => {
    if (ordered[key] === undefined) ordered[key] = cleaned[key];
  });
  const qs = buildQuery(ordered);
  return `${pathname}${qs}`;
}

/**
 * 从 URL query 解析列表筛选状态，带默认值。
 * @param {URLSearchParams} searchParams
 * @returns {{tag:string, category:string, city:string, ending:string, promo:string, sort:string, q:string, page:number}}
 */
export function readListState(searchParams) {
  const raw = parseQuery(searchParams);
  const pageNum = Number(raw.page);
  return {
    tag: raw.tag || '',
    category: raw.category || '',
    city: raw.city || '',
    ending: raw.ending === '1' ? '1' : '',
    promo: raw.promo === '1' ? '1' : '',
    sort: raw.sort === 'ending' || raw.sort === 'popular' ? raw.sort : 'latest',
    q: raw.q || '',
    page: Number.isFinite(pageNum) && pageNum >= 1 ? Math.floor(pageNum) : 1,
  };
}

/**
 * 是否处于"有筛选"状态（用于显示「清除全部筛选」）。
 * @param {{tag?:string, category?:string, city?:string, ending?:string, promo?:string, sort?:string, q?:string}} state
 * @returns {boolean}
 */
export function hasActiveFilters(state) {
  if (!state) return false;
  return Boolean(
    state.tag ||
      state.category ||
      state.city ||
      state.ending ||
      state.promo ||
      (state.sort && state.sort !== 'latest') ||
      state.q,
  );
}

export default buildQuery;
