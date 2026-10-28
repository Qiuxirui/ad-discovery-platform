/** 管理端接口封装（薄封装，字段严格照 ARCHITECTURE.md §5.7） */
import { downloadFile, request } from './client.js';

/** @param {{username:string, password:string}} body */
export function login(body, options = {}) {
  return request('/api/admin/login', { ...options, method: 'POST', body });
}

export function logout(options = {}) {
  return request('/api/admin/logout', { ...options, method: 'POST' });
}

export function getMe(options = {}) {
  return request('/api/admin/me', options);
}

export function getSummary(options = {}) {
  return request('/api/admin/summary', options);
}

/** @param {{category_id?:number, sort?:string, page?:number}} [query] */
export function getReviewQueue(query = {}, options = {}) {
  return request('/api/admin/review-queue', { ...options, query });
}

/** @param {number|string} id @param {{note?:string}} [body] */
export function approveAd(id, body = {}, options = {}) {
  return request(`/api/admin/ads/${id}/approve`, { ...options, method: 'POST', body });
}

/** @param {number|string} id @param {{reason_code:string, reason_note?:string}} body */
export function rejectAd(id, body, options = {}) {
  return request(`/api/admin/ads/${id}/reject`, { ...options, method: 'POST', body });
}

/** @param {number|string} id @param {{changes:object, note?:string}} body */
export function editApproveAd(id, body, options = {}) {
  return request(`/api/admin/ads/${id}/edit-approve`, { ...options, method: 'POST', body });
}

/** @param {number|string} id @param {{reason:string}} body */
export function offlineAd(id, body, options = {}) {
  return request(`/api/admin/ads/${id}/offline`, { ...options, method: 'POST', body });
}

/** @param {number|string} id @param {{note?:string}} [body] */
export function restoreAd(id, body = {}, options = {}) {
  return request(`/api/admin/ads/${id}/restore`, { ...options, method: 'POST', body });
}

/** @param {number|string} id */
export function getAdReviews(id, options = {}) {
  return request(`/api/admin/ads/${id}/reviews`, options);
}

/** @param {{status?:string, q?:string, merchant_id?:number, category_id?:number, page?:number}} [query] */
export function getAds(query = {}, options = {}) {
  return request('/api/admin/ads', { ...options, query });
}

/** @param {{status?:string, overdue?:string|number, page?:number}} [query] */
export function getReports(query = {}, options = {}) {
  return request('/api/admin/reports', { ...options, query });
}

export function startReport(id, options = {}) {
  return request(`/api/admin/reports/${id}/start`, { ...options, method: 'POST' });
}

/** @param {{action:'offline'|'rectify', note:string}} body */
export function resolveReport(id, body, options = {}) {
  return request(`/api/admin/reports/${id}/resolve`, { ...options, method: 'POST', body });
}

/** @param {{note:string}} body */
export function dismissReport(id, body, options = {}) {
  return request(`/api/admin/reports/${id}/dismiss`, { ...options, method: 'POST', body });
}

/** @param {{q?:string, status?:string, page?:number}} [query] */
export function getMerchants(query = {}, options = {}) {
  return request('/api/admin/merchants', { ...options, query });
}

/** @param {{status:'active'|'disabled', note?:string}} body */
export function setMerchantStatus(id, body, options = {}) {
  return request(`/api/admin/merchants/${id}/status`, { ...options, method: 'POST', body });
}

/** @param {{verified:boolean}} body */
export function verifyMerchant(id, body, options = {}) {
  return request(`/api/admin/merchants/${id}/verify`, { ...options, method: 'POST', body });
}

/** @param {{admin_note?:string}} body */
export function patchMerchant(id, body, options = {}) {
  return request(`/api/admin/merchants/${id}`, { ...options, method: 'PATCH', body });
}

export function getCategories(options = {}) {
  return request('/api/admin/categories', options);
}

/** @param {number|string} categoryId @param {{name:string, sort_order?:number}} body */
export function createTag(categoryId, body, options = {}) {
  return request(`/api/admin/categories/${categoryId}/tags`, { ...options, method: 'POST', body });
}

/** @param {number|string} tagId @param {{name?:string, sort_order?:number, is_active?:boolean}} body */
export function patchTag(tagId, body, options = {}) {
  return request(`/api/admin/tags/${tagId}`, { ...options, method: 'PATCH', body });
}

/** @param {{from:string, to:string}} query */
export function getStatsOverview(query, options = {}) {
  return request('/api/admin/stats/overview', { ...options, query });
}

/** @param {{from:string, to:string}} query */
export function getStatsFunnel(query, options = {}) {
  return request('/api/admin/stats/funnel', { ...options, query });
}

/** @param {{from:string, to:string, type:'ads'|'category'|'events'}} query */
export function exportStatsCsv(query, fallbackName = '统计导出.csv') {
  return downloadFile('/api/admin/stats/export.csv', { query, fallbackName });
}
