import { useEffect, useRef } from 'react';
import tracker from '../tracker/index.js';

/**
 * 曝光埋点：卡片在视口内可见面积 ≥50% 且持续 ≥1000ms 时上报 impression。
 * 用 ref 保证**每次挂载最多上报 1 次**（去重仍由后端根据 session_id 负责）。
 *
 * @param {{adId?: number|string, page?: string, position?: number, enabled?: boolean}} args
 * @returns {import('react').RefObject<HTMLElement>} 挂到卡片最外层元素上的 ref
 */
export default function useTrackImpression({ adId, page, position, enabled = true }) {
  const ref = useRef(null);
  const reportedRef = useRef(false);

  useEffect(() => {
    const element = ref.current;
    if (!enabled || !adId || !element) return undefined;
    if (reportedRef.current) return undefined;

    if (typeof window === 'undefined' || typeof window.IntersectionObserver !== 'function') {
      return undefined;
    }

    let timerId = null;

    const observer = new window.IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const visibleEnough = entry.isIntersecting && entry.intersectionRatio >= 0.5;
          if (visibleEnough && timerId === null && !reportedRef.current) {
            timerId = window.setTimeout(() => {
              timerId = null;
              if (reportedRef.current) return;
              reportedRef.current = true;
              tracker.track('impression', { ad_id: adId, page, position });
              observer.disconnect();
            }, 1000);
            return;
          }
          if (!visibleEnough && timerId !== null) {
            window.clearTimeout(timerId);
            timerId = null;
          }
        });
      },
      { threshold: 0.5 },
    );

    observer.observe(element);

    return () => {
      observer.disconnect();
      if (timerId !== null) {
        window.clearTimeout(timerId);
        timerId = null;
      }
    };
    // reportedRef 是每次挂载的守卫，故意不进依赖
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adId, page, position, enabled]);

  return ref;
}
