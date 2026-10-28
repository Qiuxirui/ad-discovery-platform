/**
 * 同源 API 客户端 —— 形态严格照 ARCHITECTURE.md §6.3。
 * 铁律：一律相对路径（/api/...），不得出现任何域名字面量。
 */

/** 统一错误对象：detail → message，code → 机器码，fields → 字段级校验错误 */
export class ApiError extends Error {
  constructor(message, code, status, fields) {
    super(message || '请求失败');
    this.name = 'ApiError';
    this.code = code || 'UNKNOWN';
    this.status = typeof status === 'number' ? status : 0;
    this.fields = Array.isArray(fields) ? fields : null;
  }
}

const STATUS_FALLBACK = {
  0: '网络异常，请稍后重试',
  400: '请求参数有误',
  401: '登录状态已失效，请重新登录',
  403: '没有访问权限',
  404: '内容不存在或已下线',
  409: '操作与当前状态冲突',
  410: '该内容已结束',
  422: '提交内容有误，请检查后重试',
  423: '账号已被临时锁定',
  429: '操作过于频繁，请稍后再试',
  500: '服务器开小差了，请稍后重试',
  502: '服务暂时不可用，请稍后重试',
  503: '服务暂时不可用，请稍后重试',
};

/**
 * 把 query 对象序列化为查询串，空值（undefined/null/''）自动跳过。
 * @param {Record<string, unknown>|undefined|null} query
 * @returns {string}
 */
export function buildQueryString(query) {
  if (!query || typeof query !== 'object') return '';
  const params = new URLSearchParams();
  Object.keys(query).forEach((key) => {
    const value = query[key];
    if (value === undefined || value === null || value === '') return;
    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item === undefined || item === null || item === '') return;
        params.append(key, String(item));
      });
      return;
    }
    params.append(key, String(value));
  });
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

/**
 * 统一请求入口。
 * @param {string} path 以 /api 开头的相对路径
 * @param {{method?: string, body?: unknown, query?: object, signal?: AbortSignal, headers?: object}} [options]
 * @returns {Promise<any>}
 */
export async function request(path, options = {}) {
  const { method = 'GET', body, query, signal, headers: extraHeaders } = options;
  const url = `${path}${buildQueryString(query)}`;
  const headers = { Accept: 'application/json', ...(extraHeaders || {}) };
  const hasBody = body !== undefined && body !== null;
  if (hasBody) headers['Content-Type'] = 'application/json';

  let res;
  try {
    res = await fetch(url, {
      method,
      credentials: 'same-origin',
      headers,
      body: hasBody ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    if (err && (err.name === 'AbortError' || err.code === 20)) throw err;
    throw new ApiError(STATUS_FALLBACK[0], 'NETWORK', 0);
  }

  if (res.status === 204) return null;

  const rawText = await res.text();
  let payload = null;
  if (rawText) {
    try {
      payload = JSON.parse(rawText);
    } catch {
      payload = null;
    }
  }

  if (!res.ok) {
    if (res.status === 401 && (path.startsWith('/api/admin') || path.startsWith('/api/merchant'))) {
      const scope = path.startsWith('/api/admin') ? 'admin' : 'merchant';
      window.dispatchEvent(new CustomEvent('adx:unauthorized', { detail: { scope } }));
    }
    const message =
      (payload && typeof payload.detail === 'string' && payload.detail) ||
      STATUS_FALLBACK[res.status] ||
      `请求失败（${res.status}）`;
    const code = (payload && payload.code) || `HTTP_${res.status}`;
    const fields = payload && Array.isArray(payload.fields) ? payload.fields : null;
    throw new ApiError(message, code, res.status, fields);
  }

  return payload;
}

/**
 * multipart 上传（不设 Content-Type，交给浏览器补 boundary）。
 * @param {string} path
 * @param {FormData} formData
 * @param {{method?: string, signal?: AbortSignal}} [options]
 * @returns {Promise<any>}
 */
export async function requestForm(path, formData, options = {}) {
  const { method = 'POST', signal } = options;
  let res;
  try {
    res = await fetch(path, {
      method,
      credentials: 'same-origin',
      body: formData,
      signal,
    });
  } catch (err) {
    if (err && err.name === 'AbortError') throw err;
    throw new ApiError(STATUS_FALLBACK[0], 'NETWORK', 0);
  }
  const rawText = await res.text();
  let payload = null;
  if (rawText) {
    try {
      payload = JSON.parse(rawText);
    } catch {
      payload = null;
    }
  }
  if (!res.ok) {
    const message =
      (payload && typeof payload.detail === 'string' && payload.detail) ||
      STATUS_FALLBACK[res.status] ||
      `上传失败（${res.status}）`;
    throw new ApiError(message, (payload && payload.code) || `HTTP_${res.status}`, res.status, null);
  }
  return payload;
}

/**
 * 从 Content-Disposition 解析文件名（支持 RFC 5987 中文名）。
 * @param {string|null} headerValue
 * @param {string} fallback
 * @returns {string}
 */
function parseFilename(headerValue, fallback) {
  if (!headerValue) return fallback;
  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(headerValue);
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1].trim().replace(/^"|"$/g, ''));
    } catch {
      /* 解码失败则落回普通 filename */
    }
  }
  const plainMatch = /filename="?([^";]+)"?/i.exec(headerValue);
  if (plainMatch && plainMatch[1]) return plainMatch[1].trim();
  return fallback;
}

/**
 * 下载 CSV（保持同源、带 Cookie），失败抛 ApiError，页面自行提示。
 * @param {string} path
 * @param {{query?: object, fallbackName?: string}} [options]
 * @returns {Promise<string>} 实际使用的文件名
 */
export async function downloadFile(path, options = {}) {
  const { query, fallbackName = 'export.csv' } = options;
  const url = `${path}${buildQueryString(query)}`;
  let res;
  try {
    res = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'text/csv' } });
  } catch {
    throw new ApiError(STATUS_FALLBACK[0], 'NETWORK', 0);
  }
  if (!res.ok) {
    if (res.status === 401 && (path.startsWith('/api/admin') || path.startsWith('/api/merchant'))) {
      const scope = path.startsWith('/api/admin') ? 'admin' : 'merchant';
      window.dispatchEvent(new CustomEvent('adx:unauthorized', { detail: { scope } }));
    }
    let message = STATUS_FALLBACK[res.status] || `导出失败（${res.status}）`;
    try {
      const payload = await res.json();
      if (payload && typeof payload.detail === 'string') message = payload.detail;
    } catch {
      /* 非 JSON 错误体，沿用状态码文案 */
    }
    throw new ApiError(message, `HTTP_${res.status}`, res.status, null);
  }
  const filename = parseFilename(
    res.headers.get('Content-Disposition') || res.headers.get('content-disposition'),
    fallbackName,
  );
  const blob = await res.blob();
  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.rel = 'noopener';
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  // 延迟释放，避免 Safari 提前回收导致下载失败
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 4000);
  return filename;
}
