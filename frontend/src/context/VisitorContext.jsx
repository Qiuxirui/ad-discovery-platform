import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useToast } from './ToastContext.jsx';
import {
  addFavorite,
  addHide,
  clearAllData,
  getMe,
  putPreferences,
  removeFavorite,
  removeHide,
} from '../api/visitor.js';
import { HIDE_TOAST } from '../constants/messages.js';

/** 默认上限（与后端 limits 一致，仅在后端未返回时兜底） */
const DEFAULT_LIMITS = { favorites: 200, hides: 500 };

const VisitorContext = createContext(null);

/** @returns {Set<number>} */
function toIdSet(list) {
  const set = new Set();
  if (Array.isArray(list)) {
    list.forEach((id) => {
      const num = Number(id);
      if (Number.isFinite(num)) set.add(num);
    });
  }
  return set;
}

/**
 * 匿名访客状态：visitorId、收藏集合、隐藏集合、偏好、上限。
 * 收藏/隐藏/举报成功后的 favorite|hide|report 事件由**后端**写库（ARCHITECTURE.md §5.4），
 * 前端不重复上报，避免重复计数。
 */
export function VisitorProvider({ children }) {
  const { showToast } = useToast();

  const [visitorId, setVisitorId] = useState('');
  const [favorites, setFavorites] = useState(() => new Set());
  const [hides, setHides] = useState(() => new Set());
  const [preferences, setPreferences] = useState({ categories: [], city: '' });
  const [limits, setLimits] = useState(DEFAULT_LIMITS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const me = await getMe();
      setVisitorId((me && me.visitor_id) || '');
      setFavorites(toIdSet(me && me.favorite_ids));
      setHides(toIdSet(me && me.hide_ids));
      setPreferences({
        categories: Array.isArray(me && me.preference && me.preference.categories)
          ? me.preference.categories
          : [],
        city: (me && me.preference && me.preference.city) || '',
      });
      setLimits({
        favorites: Number(me && me.limits && me.limits.favorites) || DEFAULT_LIMITS.favorites,
        hides: Number(me && me.limits && me.limits.hides) || DEFAULT_LIMITS.hides,
      });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('访客信息加载失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  /**
   * 切换收藏（幂等；重复点击不产生重复记录）。
   * @param {{id:number}|number} adOrId
   * @returns {Promise<boolean>} 操作后是否为已收藏
   */
  const toggleFavorite = useCallback(
    async (adOrId) => {
      const id = typeof adOrId === 'object' && adOrId !== null ? Number(adOrId.id) : Number(adOrId);
      if (!Number.isFinite(id)) return false;

      if (favorites.has(id)) {
        try {
          await removeFavorite(id);
          setFavorites((prev) => {
            const next = new Set(prev);
            next.delete(id);
            return next;
          });
          showToast('已取消收藏', 'info');
          return false;
        } catch (err) {
          showToast(err.message || '取消收藏失败，请稍后重试', 'error');
          return true;
        }
      }

      try {
        await addFavorite(id);
        setFavorites((prev) => new Set(prev).add(id));
        showToast('已收藏，可在「收藏」里查看', 'success');
        return true;
      } catch (err) {
        showToast(err.message || '收藏失败，请稍后重试', 'error');
        return false;
      }
    },
    [favorites, showToast],
  );

  /**
   * 不感兴趣（隐藏）：立即从当前列表移除由调用方负责。
   * @param {{id:number}|number} adOrId
   * @returns {Promise<boolean>} 是否成功隐藏
   */
  const hide = useCallback(
    async (adOrId) => {
      const id = typeof adOrId === 'object' && adOrId !== null ? Number(adOrId.id) : Number(adOrId);
      if (!Number.isFinite(id)) return false;
      if (hides.has(id)) return true;
      try {
        await addHide(id);
        setHides((prev) => new Set(prev).add(id));
        showToast(HIDE_TOAST, 'success');
        return true;
      } catch (err) {
        showToast(err.message || '操作失败，请稍后重试', 'error');
        return false;
      }
    },
    [hides, showToast],
  );

  /**
   * 恢复已隐藏的广告。
   * @param {number} adId
   * @returns {Promise<boolean>}
   */
  const unhide = useCallback(
    async (adId) => {
      const id = Number(adId);
      if (!Number.isFinite(id)) return false;
      try {
        await removeHide(id);
        setHides((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
        showToast('已恢复显示', 'success');
        return true;
      } catch (err) {
        showToast(err.message || '恢复失败，请稍后重试', 'error');
        return false;
      }
    },
    [showToast],
  );

  /**
   * 保存偏好（全不选 = 关闭个性化过滤）。
   * @param {{categories:number[], city?:string}} next
   * @returns {Promise<boolean>}
   */
  const savePreferences = useCallback(
    async (next) => {
      const payload = {
        categories: Array.isArray(next && next.categories) ? next.categories.map(Number) : [],
        city: (next && next.city) || '',
      };
      try {
        await putPreferences(payload);
        setPreferences(payload);
        showToast(payload.categories.length ? '偏好已保存' : '已关闭个性化过滤，按最新发布展示', 'success');
        return true;
      } catch (err) {
        showToast(err.message || '保存失败，请稍后重试', 'error');
        return false;
      }
    },
    [showToast],
  );

  /** 一次清空收藏/隐藏/偏好（调用方必须二次确认） */
  const clearAll = useCallback(async () => {
    try {
      await clearAllData();
      setFavorites(new Set());
      setHides(new Set());
      setPreferences({ categories: [], city: '' });
      showToast('已清除本设备的收藏、隐藏与偏好记录', 'success');
      return true;
    } catch (err) {
      showToast(err.message || '清除失败，请稍后重试', 'error');
      return false;
    }
  }, [showToast]);

  /** 外部（如管理端同步）触发刷新 */
  const refresh = load;

  const value = useMemo(
    () => ({
      visitorId,
      favorites,
      hides,
      preferences,
      limits,
      loading,
      error,
      isFavorite: (id) => favorites.has(Number(id)),
      isHidden: (id) => hides.has(Number(id)),
      toggleFavorite,
      hide,
      unhide,
      savePreferences,
      clearAll,
      refresh,
    }),
    [
      visitorId,
      favorites,
      hides,
      preferences,
      limits,
      loading,
      error,
      toggleFavorite,
      hide,
      unhide,
      savePreferences,
      clearAll,
      refresh,
    ],
  );

  return <VisitorContext.Provider value={value}>{children}</VisitorContext.Provider>;
}

/** @returns {ReturnType<typeof VisitorProvider> extends never ? never : any} */
export function useVisitor() {
  const ctx = useContext(VisitorContext);
  if (!ctx) throw new Error('useVisitor 必须在 VisitorProvider 内使用');
  return ctx;
}

export default VisitorContext;
