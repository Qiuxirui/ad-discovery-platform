/** 公开浏览接口的薄封装（不含业务逻辑），路径与参数严格照 ARCHITECTURE.md §5.1 / §5.2 */
import { request } from './client.js';

/** @returns {Promise<any>} 城市、原因、状态、排序、上限等单一字典来源 */
export function getMeta(options = {}) {
  return request('/api/meta', options);
}

/** @returns {Promise<Array>} 6 个一级类别 + 各自标签 + active_count */
export function getCategories(options = {}) {
  return request('/api/categories', options);
}

/**
 * @param {{q?:string,category?:string,tag?:string,city?:string,ending?:string|number,promo?:string|number,sort?:string,page?:number,page_size?:number}} [query]
 */
export function getAds(query = {}, options = {}) {
  return request('/api/ads', { ...options, query });
}

/** @param {number|string} id */
export function getAdDetail(id, options = {}) {
  return request(`/api/ads/${id}`, options);
}

/** @param {number|string} id @param {number} [limit] */
export function getRelatedAds(id, limit = 3, options = {}) {
  return request(`/api/ads/${id}/related`, { ...options, query: { limit } });
}

/** 外链落地页：完整 URL 只从这里下发 */
export function getOutbound(id, options = {}) {
  return request(`/api/ads/${id}/outbound`, options);
}

/** 部署自检 */
export function getHealth(options = {}) {
  return request('/api/health', options);
}
