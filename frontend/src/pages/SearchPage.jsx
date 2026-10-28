import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import InputBase from '@mui/material/InputBase';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Skeleton from '@mui/material/Skeleton';
import AdGrid from '../components/AdGrid.jsx';
import AdCard from '../components/AdCard.jsx';
import LoadMore from '../components/LoadMore.jsx';
import EmptyState from '../components/EmptyState.jsx';
import TagScroll from '../components/TagScroll.jsx';
import FilterBar from '../components/FilterBar.jsx';
import SortSelect from '../components/SortSelect.jsx';
import { IconSearch } from '../components/icons.jsx';
import { useCategories } from '../context/CategoriesContext.jsx';
import { useVisitor } from '../context/VisitorContext.jsx';
import useAdsList from '../hooks/useAdsList.js';
import useListQuery from '../hooks/useListQuery.js';
import { COMMON, EMPTY } from '../constants/messages.js';

const SUGGEST_KEYWORDS = ['优惠券', '家政', '耳机', '床品', '宠物'];

/**
 * 搜索结果（P0-B-03 / P0-C-02）。
 * 搜索框回填 + 结果数 + 复用列表组件（标签/筛选/排序）+ 空态建议。
 */
export default function SearchPage() {
  const navigate = useNavigate();
  const { categories, getCategory } = useCategories();
  const { hides } = useVisitor();

  const [state, update, reset] = useListQuery('/search');
  const [keyword, setKeyword] = useState(state.q || '');

  // URL 变化（含浏览器前进后退）时回填输入框
  useEffect(() => {
    setKeyword(state.q || '');
  }, [state.q]);

  const selectedCategory = state.category ? getCategory(state.category) : null;
  const tags = Array.isArray(selectedCategory && selectedCategory.tags) ? selectedCategory.tags : [];

  const list = useAdsList({
    q: state.q || undefined,
    category: state.category || undefined,
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

  const submitSearch = (event) => {
    event.preventDefault();
    update({ q: keyword.trim() });
  };

  const hasQuery = Boolean(state.q);

  return (
    <Box>
      <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700, mb: 1.5 }}>
        搜索广告
      </Typography>

      <Box
        component="form"
        role="search"
        onSubmit={submitSearch}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          maxWidth: 620,
          px: 1.5,
          height: 44,
          border: '1px solid #DCE3EB',
          borderRadius: 2,
          bgcolor: '#FFFFFF',
          mb: 1.5,
          '&:focus-within': { borderColor: '#1F3A5F' },
        }}
      >
        <Box sx={{ color: '#5A6472', display: 'flex' }} aria-hidden="true">
          <IconSearch size={18} />
        </Box>
        <InputBase
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          placeholder="输入关键词，例如：洗衣机"
          inputProps={{ 'aria-label': '搜索关键词', maxLength: 60 }}
          sx={{ flex: 1, fontSize: 14 }}
        />
        <Button type="submit" variant="contained" size="small" sx={{ bgcolor: '#1F3A5F', minWidth: 64 }}>
          搜索
        </Button>
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, flexWrap: 'wrap', mb: 1 }}>
        <Typography sx={{ fontSize: 14, color: '#33404F' }}>
          {hasQuery ? (
            <>
              关键词「<Box component="span" sx={{ fontWeight: 700 }}>{state.q}</Box>」共{' '}
              <Box component="span" sx={{ fontWeight: 700, color: '#1F3A5F' }}>{list.total}</Box> 条结果
            </>
          ) : (
            '未输入关键词，以下为全部在架广告'
          )}
        </Typography>
      </Box>

      {tags.length > 0 ? (
        <Box sx={{ mb: 1 }}>
          <TagScroll tags={tags} value={state.tag} onChange={(tag) => update({ tag })} />
        </Box>
      ) : null}

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
        <FilterBar
          state={state}
          onChange={update}
          onReset={reset}
          categoryOptions={categories.map((item) => ({ slug: item.slug, name: item.name }))}
        />
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
          {list.error.message || '搜索失败，请稍后重试'}
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
          title={hasQuery ? `没有找到与「${state.q}」相关的广告` : EMPTY.search.title}
          description={
            hasQuery
              ? '试试更简短的关键词，或换个类别看看。'
              : '调整筛选条件，或直接按类别浏览。'
          }
          actionText={COMMON.clearAllFilters}
          onAction={reset}
          suggestions={(categories.length ? categories.slice(0, 3) : []).map((item) => ({
            label: item.name,
            onClick: () => navigate(`/c/${item.slug}`),
          }))}
        />
      ) : null}

      {!hasQuery && visibleItems.length > 0 ? (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
          <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>试试：</Typography>
          {SUGGEST_KEYWORDS.map((word) => (
            <Button key={word} size="small" variant="outlined" onClick={() => update({ q: word })} sx={{ fontSize: 12, py: 0 }}>
              {word}
            </Button>
          ))}
        </Box>
      ) : null}

      {visibleItems.length > 0 ? (
        <>
          <AdGrid>
            {visibleItems.map((ad, index) => (
              <AdCard
                key={ad.id}
                ad={ad}
                page="search"
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
