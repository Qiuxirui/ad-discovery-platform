/**
 * 事件上报传输层（唯一出口）：sendBeacon 优先，失败降级 fetch keepalive。
 * 队列、批量、flush 时机在 tracker/index.js；此文件只负责「把一批事件送出去」。
 * 不重试、不抛错（埋点失败不得影响用户操作）。
 */

export const EVENTS_ENDPOINT = '/api/events';

/**
 * 发送一批事件。
 * @param {{session_id: string, events: Array<object>}} payload
 * @returns {Promise<boolean>} 是否成功送出（失败静默）
 */
export function postEvents(payload) {
  let body;
  try {
    body = JSON.stringify(payload);
  } catch {
    return Promise.resolve(false);
  }

  // sendBeacon：同源请求自动携带 Cookie，页面卸载时仍可送达
  if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
    try {
      const blob = new Blob([body], { type: 'application/json' });
      if (navigator.sendBeacon(EVENTS_ENDPOINT, blob)) {
        return Promise.resolve(true);
      }
    } catch {
      /* 落到 fetch 兜底 */
    }
  }

  try {
    return fetch(EVENTS_ENDPOINT, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body,
      keepalive: true,
    })
      .then((res) => Boolean(res && res.ok))
      .catch(() => false);
  } catch {
    return Promise.resolve(false);
  }
}

export default postEvents;
