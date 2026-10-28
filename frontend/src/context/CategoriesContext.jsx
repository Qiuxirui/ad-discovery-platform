import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getCategories } from '../api/public.js';

const CategoriesContext = createContext(null);

/**
 * 分类字典（6 个一级类别 + 各自二级标签 + 在架数）。
 * 唯一允许做全局缓存的只读字典；其余服务端数据不允许塞进 Context。
 */
export function CategoriesProvider({ children }) {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await getCategories();
      setCategories(Array.isArray(list) ? list : []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('分类加载失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const categoryBySlug = useMemo(() => {
    const map = new Map();
    categories.forEach((item) => {
      if (item && item.slug) map.set(item.slug, item);
    });
    return map;
  }, [categories]);

  const tagIndex = useMemo(() => {
    const map = new Map();
    categories.forEach((category) => {
      const tags = Array.isArray(category && category.tags) ? category.tags : [];
      tags.forEach((tag) => {
        if (!tag || !tag.slug) return;
        map.set(`${category.slug}::${tag.slug}`, { ...tag, category_id: category.id, category_slug: category.slug, category_name: category.name });
        if (!map.has(tag.slug)) {
          map.set(tag.slug, { ...tag, category_id: category.id, category_slug: category.slug, category_name: category.name });
        }
      });
    });
    return map;
  }, [categories]);

  /**
   * @param {string} slug
   * @returns {object|null}
   */
  const getCategory = useCallback((slug) => categoryBySlug.get(slug) || null, [categoryBySlug]);

  /**
   * @param {string} slug 标签 slug（可带 categorySlug 精确定位）
   * @param {string} [categorySlug]
   * @returns {object|null}
   */
  const getTag = useCallback(
    (slug, categorySlug) => {
      if (!slug) return null;
      if (categorySlug) return tagIndex.get(`${categorySlug}::${slug}`) || null;
      return tagIndex.get(slug) || null;
    },
    [tagIndex],
  );

  const value = useMemo(
    () => ({
      categories,
      loading,
      error,
      getCategory,
      getTag,
      reload: load,
      totalActive: categories.reduce((sum, item) => sum + (Number(item && item.active_count) || 0), 0),
    }),
    [categories, loading, error, getCategory, getTag, load],
  );

  return <CategoriesContext.Provider value={value}>{children}</CategoriesContext.Provider>;
}

export function useCategories() {
  const ctx = useContext(CategoriesContext);
  if (!ctx) throw new Error('useCategories 必须在 CategoriesProvider 内使用');
  return ctx;
}

export default CategoriesContext;
