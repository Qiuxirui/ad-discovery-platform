/** 举报相关接口封装（匿名可提交），字段严格照 ARCHITECTURE.md §5.5 */
import { request } from './client.js';

/**
 * @param {{ad_id:number, reason_code:string, detail?:string}} body
 * @returns {Promise<{code:string, status:string, duplicate:boolean, message:string}>}
 */
export function createReport(body, options = {}) {
  return request('/api/reports', { ...options, method: 'POST', body });
}

/** 本设备提交过的举报 */
export function getMyReports(options = {}) {
  return request('/api/reports/mine', options);
}

/** 凭举报码查询（不返回举报人信息） @param {string} code */
export function lookupReport(code, options = {}) {
  return request('/api/reports/lookup', { ...options, query: { code } });
}

/**
 * 终态 7 天内追加说明（不改变状态）
 * @param {string} code
 * @param {string} note
 */
export function followupReport(code, note, options = {}) {
  return request(`/api/reports/${code}/followup`, { ...options, method: 'POST', body: { note } });
}
