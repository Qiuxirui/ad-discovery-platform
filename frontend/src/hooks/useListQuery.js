import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { canonicalListPath, readListState } from '../utils/url.js';

/**
 * URL query ↔ 筛选状态双向同步。
 * 筛选全部进 URL（?tag=&city=&ending=1&promo=1&sort=&q=&page=），刷新与前进后退都能还原。
 *
 * @param {string} pathname 当前列表路径（如 `/c/digital` 或 `/search`）
 * @returns {[{tag:string,city:string,ending:string,promo:string,sort:string,q:string,page:number}, (patch:object, options?:{replace?:boolean})=>void, () => void]}
 */
export default function useListQuery(pathname) {
  const [searchParams, setSearchParams] = useSearchParams();
  const paramsKey = searchParams.toString();

  const state = useMemo(() => readListState(new URLSearchParams(paramsKey)), [paramsKey]);

  const update = useCallback(
    (patch, options = {}) => {
      const { replace = false } = options;
      const next = { ...state, ...patch };
      // 除显式翻页外，任何筛选变化都回到第 1 页
      if (patch.page === undefined) next.page = 1;
      const target = canonicalListPath(pathname, next);
      const queryIndex = target.indexOf('?');
      const search = queryIndex >= 0 ? target.slice(queryIndex + 1) : '';
      setSearchParams(new URLSearchParams(search), { replace });
    },
    [pathname, setSearchParams, state],
  );

  const reset = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace: false });
  }, [setSearchParams]);

  return [state, update, reset];
}
