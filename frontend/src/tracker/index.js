/**
 * 事件上报客户端（唯一出口）。
 * 铁律：只报原始事实，**不做任何去重判断**（去重全部由后端 EventService 负责）。
 * 传输：sendBeacon 优先（页面卸载也可靠），失败降级 fetch keepalive；批量 ≤20 条或 3s 空闲 flush。
 */

import { postEvents } from '../api/events.js';

const MAX_BATCH = 20;
const FLUSH_DELAY_MS = 3000;
const SESSION_KEY = 'adx:session_id';

/**
 * 生成本次会话 id（仅存内存 + sessionStorage，非指纹、不上传设备信息）。
 * @returns {string}
 */
function createSessionId() {
  const cryptoObj = typeof window !== 'undefined' ? window.crypto : undefined;
  if (cryptoObj && typeof cryptoObj.randomUUID === 'function') {
    return cryptoObj.randomUUID();
  }
  if (cryptoObj && typeof cryptoObj.getRandomValues === 'function') {
    const bytes = new Uint8Array(16);
    cryptoObj.getRandomValues(bytes);
    return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
  }
  return `s-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

/**
 * 取（或创建）会话 id；sessionStorage 不可用时退化为内存值。
 * @returns {string}
 */
function resolveSessionId() {
  try {
    const existing = window.sessionStorage.getItem(SESSION_KEY);
    if (existing) return existing;
    const created = createSessionId();
    window.sessionStorage.setItem(SESSION_KEY, created);
    return created;
  } catch {
    return createSessionId();
  }
}

/** @typedef {{event_type:string, ad_id?:number, page?:string, position?:number, meta?:object}} RawEvent */

class Tracker {
  constructor() {
    this.queue = [];
    this.timer = null;
    this.sessionId = '';
    this.bound = false;
  }

  /** 懒初始化：拿到 sessionId 并挂上卸载/隐藏时的强制 flush */
  init() {
    if (this.bound) return;
    this.sessionId = resolveSessionId();
    this.bound = true;

    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
          this.flush(true);
        }
      });
    }
    if (typeof window !== 'undefined') {
      window.addEventListener('pagehide', () => this.flush(true));
    }
  }

  /**
   * 记录一个事件并加入队列。
   * @param {string} eventType 枚举见 constants/enums.js EVENT_TYPES
   * @param {{ad_id?:number|string, page?:string, position?:number, meta?:object}} [payload]
   */
  track(eventType, payload = {}) {
    if (!eventType) return;
    this.init();
    const item = { event_type: eventType };
    if (payload.ad_id !== undefined && payload.ad_id !== null) {
      const adId = Number(payload.ad_id);
      if (Number.isFinite(adId)) item.ad_id = adId;
    }
    if (payload.page) item.page = payload.page;
    if (payload.position !== undefined && payload.position !== null) {
      const position = Number(payload.position);
      if (Number.isFinite(position)) item.position = position;
    }
    if (payload.meta && typeof payload.meta === 'object') {
      item.meta = payload.meta;
    }
    this.queue.push(item);

    if (this.queue.length >= MAX_BATCH) {
      this.flush();
      return;
    }
    this.scheduleFlush();
  }

  /** 3s 空闲后 flush */
  scheduleFlush() {
    if (this.timer) return;
    this.timer = window.setTimeout(() => {
      this.timer = null;
      this.flush();
    }, FLUSH_DELAY_MS);
  }

  /**
   * 立即发送队列中的事件（每次最多 20 条，剩余留下继续排）。
   * @param {boolean} [sync] 页面正在卸载时传 true：尽可能把队列发完
   */
  flush(sync = false) {
    this.init();
    if (this.timer) {
      window.clearTimeout(this.timer);
      this.timer = null;
    }
    if (this.queue.length === 0) return;

    const rounds = sync ? Math.ceil(this.queue.length / MAX_BATCH) : 1;
    for (let i = 0; i < rounds; i += 1) {
      const batch = this.queue.splice(0, MAX_BATCH);
      if (batch.length === 0) break;
      postEvents({ session_id: this.sessionId, events: batch }).catch(() => {
        /* 静默失败：埋点不影响体验 */
      });
    }

    if (this.queue.length > 0) {
      this.scheduleFlush();
    }
  }

  /** 当前会话 id（调试与联调用） */
  getSessionId() {
    this.init();
    return this.sessionId;
  }
}

const tracker = new Tracker();

export default tracker;
export { tracker, MAX_BATCH };
