import { useCallback, useEffect, useRef, useState } from 'react';
import { getAds } from '../api/public.js';

const DEFAULT_PAGE_SIZE = 24;

/**
 * 列表分页累加 hook：首页 + 「加载更多」追加，按 id 去重，暴露 has_more。
 * 不自动无限滚动（PRD P0-B-06 明确要求按钮式分页）。
 *
 * @param {Record<string, unknown>} params 后端筛选参数（q/category/tag/city/ending/promo/sort）
 * @param {{pageSize?: number, enabled?: boolean}} [options]
 * @returns {{items: Array<object>, total: number, loading: boolean, loadingMore: boolean, error: Error|null, hasMore: boolean, loadMore: () => void, reload: () => void, removeItem: (id:number)=>void}}
 */
export default function useAdsList(params = {}, options = {}) {
  const { pageSize = DEFAULT_PAGE_SIZE, enabled = true } = options;

  const [items, setItems] = useState(/** @type {Array<object>} */ ([]));
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(Boolean(enabled));
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [nonce, setNonce] = useState(0);

  const paramsKey = JSON.stringify(params || {});
  const requestIdRef = useRef(0);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const fetchPage = useCallback(
    async (targetPage, mode) => {
      const requestId = requestIdRef.current + 1;
      requestIdRef.current = requestId;

      if (mode === 'reset') {
        setLoading(true);
        setError(null);
      } else {
        setLoadingMore(true);
        setError(null);
      }

      try {
        const query = { ...(params || {}), page: targetPage, page_size: pageSize };
        const res = await getAds(query);
        if (!mountedRef.current || requestId !== requestIdRef.current) return;

        const nextItems = Array.isArray(res && res.items) ? res.items : [];
        if (mode === 'reset') {
          setItems(nextItems);
        } else {
          setItems((prev) => {
            const seen = new Set(prev.map((item) => item.id));
            const merged = [...prev];
            nextItems.forEach((item) => {
              if (item && !seen.has(item.id)) {
                seen.add(item.id);
                merged.push(item);
              }
            });
            return merged;
          });
        }
        setTotal(Number(res && res.total) || 0);
        setPage(targetPage);
        setHasMore(Boolean(res && res.has_more));
        setLoading(false);
        setLoadingMore(false);
      } catch (err) {
        if (!mountedRef.current || requestId !== requestIdRef.current) return;
        setError(err instanceof Error ? err : new Error('加载失败'));
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [paramsKey, pageSize],
  );

  // 筛选条件变化 → 回到第 1 页重新加载
  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    fetchPage(1, 'reset');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey, enabled, nonce]);

  const loadMore = useCallback(() => {
    if (loading || loadingMore || !hasMore) return;
    fetchPage(page + 1, 'append');
  }, [fetchPage, hasMore, loading, loadingMore, page]);

  const reload = useCallback(() => setNonce((value) => value + 1), []);

  /** 隐藏成功后立即从当前列表移除（PRD P0-U-02） */
  const removeItem = useCallback((id) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  }, []);

  return { items, total, loading, loadingMore, error, hasMore, loadMore, reload, removeItem };
}
