import React, { useMemo, useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import InputBase from '@mui/material/InputBase';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import Skeleton from '@mui/material/Skeleton';
import Alert from '@mui/material/Alert';
import AdGrid from '../components/AdGrid.jsx';
import AdCard from '../components/AdCard.jsx';
import EmptyState from '../components/EmptyState.jsx';
import { IconSearch } from '../components/icons.jsx';
import { useCategories } from '../context/CategoriesContext.jsx';
import { useVisitor } from '../context/VisitorContext.jsx';
import useAdsList from '../hooks/useAdsList.js';
import { COMMON, EMPTY } from '../constants/messages.js';

const PREVIEW_COUNT = 12;

/** 首屏骨架：3 张卡片占位，避免布局跳动 */
function CardSkeletons({ count = 3 }) {
  return (
    <AdGrid>
      {Array.from({ length: count }).map((_, index) => (
        <Box
          key={`skeleton-${index}`}
          sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: 1.25 }}
        >
          <Box className="adx-skeleton" sx={{ width: '100%', aspectRatio: '16 / 9', borderRadius: '10px' }} />
          <Box className="adx-skeleton" sx={{ height: 16, mt: 1.25, width: '88%' }} />
          <Box className="adx-skeleton" sx={{ height: 14, mt: 1, width: '45%' }} />
          <Box className="adx-skeleton" sx={{ height: 12, mt: 1, width: '60%' }} />
        </Box>
      ))}
    </AdGrid>
  );
}

/**
 * 首页（P0-B-01）。
 * 说明条（AppLayout 提供）+ 搜索 + 6 类别入口（含在架数）+ 最新发布 12 条。
 * 偏好类别非空时作为默认过滤（全不选则不生效，PRD §7.2）。
 */
export default function HomePage() {
  const navigate = useNavigate();
  const { categories, loading: categoriesLoading, error: categoriesError, totalActive } = useCategories();
  const { preferences, hides } = useVisitor();
  const [keyword, setKeyword] = useState('');

  const list = useAdsList({ sort: 'latest' }, { pageSize: PREVIEW_COUNT });
  const { items, loading, error, total } = list;

  const preferredSlugs = useMemo(() => {
    const ids = Array.isArray(preferences.categories) ? preferences.categories.map(Number) : [];
    if (ids.length === 0) return new Set();
    const slugs = new Set();
    categories.forEach((category) => {
      if (ids.includes(Number(category.id))) slugs.add(category.slug);
    });
    return slugs;
  }, [preferences.categories, categories]);

  const visibleItems = useMemo(() => {
    const notHidden = items.filter((ad) => !hides.has(Number(ad.id)));
    if (preferredSlugs.size === 0) return notHidden;
    const filtered = notHidden.filter((ad) => preferredSlugs.has(ad.category_slug));
    // 偏好过滤后为空时回落为全量，避免首页"看起来没内容"
    return filtered.length > 0 ? filtered : notHidden;
  }, [items, hides, preferredSlugs]);

  const personalized = preferredSlugs.size > 0 && visibleItems.some((ad) => preferredSlugs.has(ad.category_slug));

  const submitSearch = (event) => {
    event.preventDefault();
    const value = keyword.trim();
    navigate(value ? `/search?q=${encodeURIComponent(value)}` : '/search');
  };

  const categoryCards = categories.length
    ? categories
    : [];

  return (
    <Box>
      {/* 首屏：标题 + 搜索 */}
      <Box
        sx={{
          bgcolor: '#FFFFFF',
          border: '1px solid #E2E6EC',
          borderRadius: '12px',
          px: { xs: 2, sm: 3 },
          py: { xs: 2.5, sm: 3.5 },
          mb: 2.5,
        }}
      >
        <Typography component="h1" sx={{ fontSize: { xs: 22, sm: 27 }, fontWeight: 700, letterSpacing: 0.2 }}>
          按类别浏览商家广告
        </Typography>
        <Typography sx={{ fontSize: { xs: 13, sm: 14 }, color: '#5A6472', mt: 1, lineHeight: 1.7 }}>
          全部内容均为商家付费推广，已逐条标注「广告」。排序只按发布时间与有效期，不接受任何付费加权。
        </Typography>

        <Box
          component="form"
          role="search"
          onSubmit={submitSearch}
          sx={{
            mt: 2,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            maxWidth: 560,
            px: 1.5,
            height: 44,
            border: '1px solid #DCE3EB',
            borderRadius: 2,
            bgcolor: '#F7F8FA',
            '&:focus-within': { borderColor: '#1F3A5F', bgcolor: '#fff' },
          }}
        >
          <Box sx={{ color: '#5A6472', display: 'flex' }} aria-hidden="true">
            <IconSearch size={18} />
          </Box>
          <InputBase
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="搜索商品、服务或商家…"
            inputProps={{ 'aria-label': '搜索广告', maxLength: 60 }}
            sx={{ flex: 1, fontSize: 14 }}
          />
          <Button type="submit" variant="contained" size="small" sx={{ bgcolor: '#1F3A5F', minWidth: 64 }}>
            搜索
          </Button>
        </Box>

        <Box sx={{ mt: 1.5, display: 'flex', flexWrap: 'wrap', gap: 1.5 }}>
          <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>
            全站在架 <Box component="span" sx={{ color: '#1F3A5F', fontWeight: 700 }}>{totalActive}</Box> 条
          </Typography>
          <Link component={RouterLink} to="/policy/ads#why" sx={{ fontSize: 12 }}>
            排序规则说明
          </Link>
          <Link component={RouterLink} to="/preferences" sx={{ fontSize: 12 }}>
            调整我的偏好
          </Link>
        </Box>
      </Box>

      {/* 6 个一级类别入口（含在架数） */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', mb: 1.25 }}>
          <Typography component="h2" sx={{ fontSize: 18, fontWeight: 700 }}>
            按类别浏览
          </Typography>
          {categoriesLoading ? (
            <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>{COMMON.loading}</Typography>
          ) : null}
        </Box>

        {categoriesError ? (
          <Alert severity="error" sx={{ mb: 1.5 }}>
            {categoriesError.message || '类别加载失败，请刷新重试'}
          </Alert>
        ) : null}

        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', sm: 'repeat(3, minmax(0, 1fr))', md: 'repeat(3, minmax(0, 1fr))' },
            gap: 1.5,
          }}
        >
          {categoriesLoading && categoryCards.length === 0
            ? Array.from({ length: 6 }).map((_, index) => (
                <Box key={`cat-skeleton-${index}`} className="adx-skeleton" sx={{ height: 92, borderRadius: '12px' }} />
              ))
            : categoryCards.map((category) => (
                <Box
                  key={category.slug}
                  component={RouterLink}
                  to={`/c/${category.slug}`}
                  sx={{
                    display: 'block',
                    textDecoration: 'none',
                    color: 'inherit',
                    bgcolor: '#FFFFFF',
                    border: '1px solid #E2E6EC',
                    borderRadius: '12px',
                    px: 1.75,
                    py: 1.5,
                    minHeight: 92,
                    transition: 'transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: '0 6px 16px rgba(15,23,42,.12)',
                      borderColor: '#C9D2DD',
                    },
                  }}
                >
                  <Typography sx={{ fontSize: 15, fontWeight: 700, color: '#1A1A1A' }}>
                    {category.name}
                  </Typography>
                  <Typography
                    className="adx-clamp-2"
                    sx={{ fontSize: 12, color: '#5A6472', mt: 0.5, minHeight: '2.4em', lineHeight: 1.6 }}
                  >
                    {category.intro || '按二级标签细分浏览'}
                  </Typography>
                  <Typography sx={{ fontSize: 12, color: '#1F3A5F', fontWeight: 700, mt: 0.75 }}>
                    在架 {Number(category.active_count) || 0} 条
                  </Typography>
                </Box>
              ))}
        </Box>
      </Box>

      {/* 最新发布 12 条 */}
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.25, flexWrap: 'wrap', gap: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
            <Typography component="h2" sx={{ fontSize: 18, fontWeight: 700 }}>
              最新发布
            </Typography>
            <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>
              {personalized ? '已按你的偏好类别优先展示' : '按发布时间倒序'}
            </Typography>
          </Box>
          <Link component={RouterLink} to="/preferences" sx={{ fontSize: 13 }}>
            偏好设置
          </Link>
        </Box>

        {error ? (
          <Alert
            severity="error"
            action={
              <Button color="inherit" size="small" onClick={list.reload}>
                {COMMON.retry}
              </Button>
            }
          >
            {error.message || '广告加载失败，请稍后重试'}
          </Alert>
        ) : null}

        {loading && items.length === 0 ? <CardSkeletons count={3} /> : null}

        {!loading && !error && visibleItems.length === 0 ? (
          <EmptyState
            title={EMPTY.home.title}
            description={EMPTY.home.desc}
            suggestions={categories.slice(0, 3).map((category) => ({
              label: category.name,
              onClick: () => navigate(`/c/${category.slug}`),
            }))}
          />
        ) : null}

        {visibleItems.length > 0 ? (
          <>
            <AdGrid>
              {visibleItems.map((ad, index) => (
                <AdCard key={ad.id} ad={ad} page="home" position={index + 1} />
              ))}
            </AdGrid>
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2.5 }}>
              <Button
                variant="text"
                onClick={() => navigate('/search')}
                sx={{ fontSize: 14, color: '#1F3A5F' }}
              >
                查看更多广告（共 {total} 条公开广告）
              </Button>
            </Box>
          </>
        ) : null}
      </Box>
    </Box>
  );
}
