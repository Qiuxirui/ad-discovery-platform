import React, { useMemo } from 'react';
import { Link as RouterLink, useNavigate, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import Skeleton from '@mui/material/Skeleton';
import Alert from '@mui/material/Alert';
import AdGrid from '../components/AdGrid.jsx';
import AdCard from '../components/AdCard.jsx';
import LoadMore from '../components/LoadMore.jsx';
import EmptyState from '../components/EmptyState.jsx';
import TagScroll from '../components/TagScroll.jsx';
import FilterBar from '../components/FilterBar.jsx';
import SortSelect from '../components/SortSelect.jsx';
import { IconHome } from '../components/icons.jsx';
import { useCategories } from '../context/CategoriesContext.jsx';
import { useVisitor } from '../context/VisitorContext.jsx';
import useAdsList from '../hooks/useAdsList.js';
import useListQuery from '../hooks/useListQuery.js';
import { COMMON, EMPTY } from '../constants/messages.js';

/**
 * 分类列表（P0-B-02 / P0-C-02 / P1-B-09）。
 * 面包屑 + 二级标签横滑 + 筛选 + 排序 + 网格 + 加载更多；筛选状态全部进 URL。
 */
export default function CategoryPage() {
  const { slug = '' } = useParams();
  const navigate = useNavigate();
  const { categories, getCategory, loading: categoriesLoading } = useCategories();
  const { hides } = useVisitor();

  const category = getCategory(slug);
  const [state, update, reset] = useListQuery(`/c/${slug}`);

  const list = useAdsList({
    category: slug,
    tag: state.tag || undefined,
    city: state.city || undefined,
    ending: state.ending || undefined,
    promo: state.promo || undefined,
    sort: state.sort || 'latest',
  });

  const visibleItems = useMemo(
    () => list.items.filter((ad) => !hides.has(Number(ad.id))),
    [list.items, hides],
  );

  const siblingCategories = useMemo(
    () => categories.filter((item) => item.slug !== slug).slice(0, 3),
    [categories, slug],
  );

  const tags = Array.isArray(category && category.tags) ? category.tags : [];

  if (!categoriesLoading && !category) {
    return (
      <EmptyState
        title="该类别不存在"
        description="可能链接有误，或该类别已下线。"
        actionText={COMMON.backHome}
        onAction={() => navigate('/')}
        icon={<IconHome size={34} />}
      />
    );
  }

  return (
    <Box>
      {/* 面包屑 + 在架数 */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap', mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, fontSize: 13, color: '#5A6472', flexWrap: 'wrap' }}>
          <Link component={RouterLink} to="/" sx={{ fontSize: 13, color: '#5A6472' }}>
            首页
          </Link>
          <Box component="span" aria-hidden="true">›</Box>
          <Typography component="span" sx={{ fontSize: 13, color: '#1A1A1A', fontWeight: 600 }}>
            {category ? category.name : slug}
          </Typography>
          {state.tag ? (
            <>
              <Box component="span" aria-hidden="true">›</Box>
              <Typography component="span" sx={{ fontSize: 13, color: '#1A1A1A' }}>
                {tags.find((tag) => tag.slug === state.tag)?.name || state.tag}
              </Typography>
            </>
          ) : null}
        </Box>
        <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>
          当前 <Box component="span" sx={{ color: '#1F3A5F', fontWeight: 700 }}>{list.total}</Box> 条在架
        </Typography>
      </Box>

      <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700, mb: 0.5 }}>
        {category ? category.name : '分类'}
      </Typography>
      {category && category.intro ? (
        <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 1.5, lineHeight: 1.7 }}>{category.intro}</Typography>
      ) : null}

      <Box sx={{ mb: 1 }}>
        <TagScroll
          tags={tags}
          value={state.tag}
          onChange={(tag) => update({ tag })}
          allLabel="全部"
        />
      </Box>

      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 1,
          borderTop: '1px solid #E2E6EC',
          borderBottom: '1px solid #E2E6EC',
          mb: 2,
        }}
      >
        <FilterBar state={state} onChange={update} onReset={reset} />
        <SortSelect value={state.sort} onChange={(sort) => update({ sort })} />
      </Box>

      {list.error ? (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={list.reload}>
              {COMMON.retry}
            </Button>
          }
        >
          {list.error.message || '列表加载失败，请稍后重试'}
        </Alert>
      ) : null}

      {list.loading && visibleItems.length === 0 ? (
        <AdGrid>
          {Array.from({ length: 6 }).map((_, index) => (
            <Box key={`sk-${index}`} sx={{ bgcolor: '#fff', border: '1px solid #E2E6EC', borderRadius: '12px', p: 1.25 }}>
              <Skeleton variant="rounded" sx={{ width: '100%', aspectRatio: '16 / 9', height: 'auto' }} />
              <Skeleton height={18} sx={{ mt: 1 }} />
              <Skeleton height={14} width="50%" />
            </Box>
          ))}
        </AdGrid>
      ) : null}

      {!list.loading && !list.error && visibleItems.length === 0 ? (
        <EmptyState
          title={EMPTY.category.title}
          description={EMPTY.category.desc}
          actionText={COMMON.clearAllFilters}
          onAction={reset}
          suggestions={siblingCategories.map((item) => ({
            label: item.name,
            onClick: () => navigate(`/c/${item.slug}`),
          }))}
        />
      ) : null}

      {visibleItems.length > 0 ? (
        <>
          <AdGrid>
            {visibleItems.map((ad, index) => (
              <AdCard
                key={ad.id}
                ad={ad}
                page="list"
                position={index + 1}
                onHidden={(id) => list.removeItem(id)}
              />
            ))}
          </AdGrid>
          <LoadMore
            hasMore={list.hasMore}
            loading={list.loadingMore}
            count={visibleItems.length}
            onClick={list.loadMore}
          />
        </>
      ) : null}
    </Box>
  );
}
