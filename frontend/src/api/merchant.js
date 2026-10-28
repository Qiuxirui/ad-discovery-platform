/** 商家端接口封装（薄封装，字段严格照 ARCHITECTURE.md §5.6） */
import { downloadFile, request, requestForm } from './client.js';

/** @param {{name:string, contact_name:string, phone:string, email:string, password:string, city:string, main_category_id:number, agree_policy:boolean}} body */
export function signup(body, options = {}) {
  return request('/api/merchant/signup', { ...options, method: 'POST', body });
}

/** @param {{account:string, password:string}} body */
export function login(body, options = {}) {
  return request('/api/merchant/login', { ...options, method: 'POST', body });
}

export function logout(options = {}) {
  return request('/api/merchant/logout', { ...options, method: 'POST' });
}

export function getMe(options = {}) {
  return request('/api/merchant/me', options);
}

/** @param {{contact_name?:string, phone?:string, city?:string, main_category_id?:number}} body */
export function updateMe(body, options = {}) {
  return request('/api/merchant/me', { ...options, method: 'PATCH', body });
}

/** @param {{old_password:string, new_password:string}} body */
export function changePassword(body, options = {}) {
  return request('/api/merchant/me/password', { ...options, method: 'POST', body });
}

/** @param {{status?:string, page?:number}} [query] */
export function getAds(query = {}, options = {}) {
  return request('/api/merchant/ads', { ...options, query });
}

/** @param {object} body AdCreateIn + submit */
export function createAd(body, options = {}) {
  return request('/api/merchant/ads', { ...options, method: 'POST', body });
}

/** @param {number|string} id */
export function getAd(id, options = {}) {
  return request(`/api/merchant/ads/${id}`, options);
}

/** @param {number|string} id @param {object} body */
export function updateAd(id, body, options = {}) {
  return request(`/api/merchant/ads/${id}`, { ...options, method: 'PATCH', body });
}

export function submitAd(id, options = {}) {
  return request(`/api/merchant/ads/${id}/submit`, { ...options, method: 'POST' });
}

export function withdrawAd(id, options = {}) {
  return request(`/api/merchant/ads/${id}/withdraw`, { ...options, method: 'POST' });
}

export function abandonAd(id, options = {}) {
  return request(`/api/merchant/ads/${id}/abandon`, { ...options, method: 'POST' });
}

export function duplicateAd(id, options = {}) {
  return request(`/api/merchant/ads/${id}/duplicate`, { ...options, method: 'POST' });
}

export function deleteAd(id, options = {}) {
  return request(`/api/merchant/ads/${id}`, { ...options, method: 'DELETE' });
}

/** @param {File} file @returns {Promise<{image_path:string}>} */
export function uploadImage(file, options = {}) {
  const form = new FormData();
  form.append('file', file);
  return requestForm('/api/merchant/uploads', form, options);
}

/** @param {{ad_id:number|string, from:string, to:string}} query */
export function getReport(query, options = {}) {
  return request('/api/merchant/report', { ...options, query });
}

/** @param {{ad_id:number|string, from:string, to:string}} query @param {string} fallbackName */
export function exportReportCsv(query, fallbackName = '报告.csv') {
  return downloadFile('/api/merchant/report/export.csv', { query, fallbackName });
}
