import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * 通用异步数据 hook：{data, loading, error, reload}。
 * 页面必须自行展示 error.detail（不静默吞错）。
 *
 * @template T
 * @param {() => Promise<T>} fetcher 无参取数函数（内部自行调用 api 层）
 * @param {Array<unknown>} [deps] 依赖变化时重新取数
 * @param {{enabled?: boolean, initialData?: T}} [options]
 * @returns {{data: T|null, loading: boolean, error: Error|null, reload: () => void}}
 */
export default function useApi(fetcher, deps = [], options = {}) {
  const { enabled = true, initialData = null } = options;
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(Boolean(enabled));
  const [error, setError] = useState(null);
  const [nonce, setNonce] = useState(0);

  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const depsKey = JSON.stringify(deps);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return undefined;
    }
    let alive = true;
    setLoading(true);
    setError(null);

    Promise.resolve()
      .then(() => fetcherRef.current())
      .then((result) => {
        if (!alive) return;
        setData(result);
        setLoading(false);
      })
      .catch((err) => {
        if (!alive) return;
        setError(err instanceof Error ? err : new Error('加载失败'));
        setLoading(false);
      });

    return () => {
      alive = false;
    };
    // depsKey 已序列化全部依赖，nonce 用于手动 reload
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [depsKey, nonce, enabled]);

  const reload = useCallback(() => setNonce((value) => value + 1), []);

  return { data, loading, error, reload };
}
