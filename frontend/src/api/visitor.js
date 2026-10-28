/** 匿名访客数据接口封装（收藏/隐藏/偏好/数据删除），字段严格照 ARCHITECTURE.md §5.4 */
import { request } from './client.js';

/** @returns {Promise<{visitor_id:string, favorite_ids:number[], hide_ids:number[], preference:{categories:number[],city:string}, counts:{favorites:number,hides:number}, limits:object}>} */
export function getMe(options = {}) {
  return request('/api/visitor/me', options);
}

/** @param {{page?:number}} [query] */
export function getFavorites(query = {}, options = {}) {
  return request('/api/visitor/favorites', { ...options, query });
}

/** @param {number} adId */
export function addFavorite(adId, options = {}) {
  return request('/api/visitor/favorites', { ...options, method: 'POST', body: { ad_id: adId } });
}

/** @param {number} adId */
export function removeFavorite(adId, options = {}) {
  return request(`/api/visitor/favorites/${adId}`, { ...options, method: 'DELETE' });
}

/** @param {{page?:number}} [query] */
export function getHides(query = {}, options = {}) {
  return request('/api/visitor/hides', { ...options, query });
}

/** @param {number} adId */
export function addHide(adId, options = {}) {
  return request('/api/visitor/hides', { ...options, method: 'POST', body: { ad_id: adId } });
}

/** @param {number} adId */
export function removeHide(adId, options = {}) {
  return request(`/api/visitor/hides/${adId}`, { ...options, method: 'DELETE' });
}

export function getPreferences(options = {}) {
  return request('/api/visitor/preferences', options);
}

/** @param {{categories:number[], city?:string}} body */
export function putPreferences(body, options = {}) {
  return request('/api/visitor/preferences', { ...options, method: 'PUT', body });
}

/** 一次清空收藏/隐藏/偏好（前端必须二次确认） */
export function clearAllData(options = {}) {
  return request('/api/visitor/data', { ...options, method: 'DELETE' });
}
