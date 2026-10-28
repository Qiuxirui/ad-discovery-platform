import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Skeleton from '@mui/material/Skeleton';
import AdGrid from '../components/AdGrid.jsx';
import AdCard from '../components/AdCard.jsx';
import EmptyState from '../components/EmptyState.jsx';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import { IconStar } from '../components/icons.jsx';
import { getFavorites, removeFavorite } from '../api/visitor.js';
import useApi from '../hooks/useApi.js';
import { useVisitor } from '../context/VisitorContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { useCategories } from '../context/CategoriesContext.jsx';
import { COMMON, EMPTY, FAVORITES_DEVICE_TIP } from '../constants/messages.js';

/**
 * 收藏夹（P0-U-01 / P0-U-07）。
 * 已收藏卡片网格 + 批量取消 + 「已结束」分组 + 本设备提示。
 * 过期条目保留展示但单独分组（后端 groups 优先，缺失时按 is_expired 兜底分组）。
 */
export default function FavoritesPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { refresh } = useVisitor();
  const { categories } = useCategories();

  const [items, setItems] = useState([]);
  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState(() => new Set());
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [removing, setRemoving] = useState(false);

  const { data, loading, error, reload } = useApi(() => getFavorites({ page: 1 }), []);

  useEffect(() => {
    if (!data) return;
    const list = Array.isArray(data.items) ? data.items : [];
    setItems(list);
    setSelected(new Set());
  }, [data]);

  const { activeItems, expiredItems } = useMemo(() => {
    // 收藏页展示用户主动收藏的全部条目（隐藏状态不影响收藏可见性）
    const visible = items;
    const groups = data && data.groups ? data.groups : null;
    if (groups && Array.isArray(groups.active) && Array.isArray(groups.expired)) {
      const activeIds = new Set(groups.active.map((item) => Number(item.id)));
      return {
        activeItems: visible.filter((item) => activeIds.has(Number(item.id))),
        expiredItems: visible.filter((item) => !activeIds.has(Number(item.id))),
      };
    }
    return {
      activeItems: visible.filter((item) => !item.is_expired),
      expiredItems: visible.filter((item) => Boolean(item.is_expired)),
    };
  }, [items, data]);

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleCancelOne = async (ad) => {
    try {
      await removeFavorite(Number(ad.id));
      setItems((prev) => prev.filter((item) => Number(item.id) !== Number(ad.id)));
      showToast('已取消收藏', 'info');
      refresh();
    } catch (err) {
      showToast(err.message || '取消收藏失败，请稍后重试', 'error');
    }
  };

  const handleBatchCancel = async () => {
    const ids = Array.from(selected);
    if (ids.length === 0) {
      setConfirmOpen(false);
      return;
    }
    setRemoving(true);
    let failed = 0;
    for (let i = 0; i < ids.length; i += 1) {
      try {
        // 串行执行，避免瞬时并发过多
        // eslint-disable-next-line no-await-in-loop
        await removeFavorite(ids[i]);
      } catch {
        failed += 1;
      }
    }
    const removedSet = new Set(ids);
    setItems((prev) => prev.filter((item) => !removedSet.has(Number(item.id))));
    setSelected(new Set());
    setSelectMode(false);
    setRemoving(false);
    setConfirmOpen(false);
    refresh();
    if (failed > 0) {
      showToast(`已取消 ${ids.length - failed} 条收藏，${failed} 条失败`, 'warning');
    } else {
      showToast(`已取消 ${ids.length} 条收藏`, 'success');
    }
  };

  const total = items.length;

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap', mb: 1 }}>
        <Box>
          <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700 }}>
            我的收藏
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mt: 0.5 }}>
            共 {total} 条 · {FAVORITES_DEVICE_TIP}
          </Typography>
        </Box>
        {total > 0 ? (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              size="small"
              variant={selectMode ? 'contained' : 'outlined'}
              onClick={() => {
                setSelectMode((prev) => !prev);
                setSelected(new Set());
              }}
              sx={{
                borderColor: '#C9D2DD',
                bgcolor: selectMode ? '#1F3A5F' : 'transparent',
                color: selectMode ? '#fff' : '#1F3A5F',
              }}
            >
              {selectMode ? '退出批量' : '批量取消'}
            </Button>
            {selectMode ? (
              <Button
                size="small"
                variant="contained"
                disabled={selected.size === 0}
                onClick={() => setConfirmOpen(true)}
                sx={{ bgcolor: '#B3261E', '&:hover': { bgcolor: '#8F1D17' } }}
              >
                取消所选（{selected.size}）
              </Button>
            ) : null}
          </Box>
        ) : null}
      </Box>

      <Alert severity="info" sx={{ mb: 2 }}>
        {FAVORITES_DEVICE_TIP}；广告结束后收藏仍会保留，但会移入「已结束」分组。
      </Alert>

      {error ? (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={reload}>
              {COMMON.retry}
            </Button>
          }
        >
          {error.message || '收藏加载失败'}
        </Alert>
      ) : null}

      {loading && items.length === 0 ? (
        <AdGrid>
          {Array.from({ length: 3 }).map((_, index) => (
            <Box key={`fav-sk-${index}`} sx={{ bgcolor: '#fff', border: '1px solid #E2E6EC', borderRadius: '12px', p: 1.25 }}>
              <Skeleton variant="rounded" sx={{ width: '100%', aspectRatio: '16 / 9', height: 'auto' }} />
              <Skeleton height={18} sx={{ mt: 1 }} />
              <Skeleton height={14} width="50%" />
            </Box>
          ))}
        </AdGrid>
      ) : null}

      {!loading && !error && total === 0 ? (
        <EmptyState
          title={EMPTY.favorites.title}
          description={EMPTY.favorites.desc}
          actionText="去浏览广告"
          onAction={() => navigate('/')}
          icon={<IconStar size={34} />}
          suggestions={categories.slice(0, 3).map((item) => ({
            label: item.name,
            onClick: () => navigate(`/c/${item.slug}`),
          }))}
        />
      ) : null}

      {activeItems.length > 0 ? (
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.25 }}>
            <Typography component="h2" sx={{ fontSize: 16, fontWeight: 700 }}>
              仍在展示（{activeItems.length}）
            </Typography>
            {selectMode ? (
              <Button
                size="small"
                onClick={() => setSelected(new Set(activeItems.map((item) => Number(item.id))))}
                sx={{ fontSize: 12, color: '#1F3A5F' }}
              >
                全选
              </Button>
            ) : null}
          </Box>
          <AdGrid>
            {activeItems.map((ad, index) => (
              <Box key={ad.id} sx={{ position: 'relative' }}>
                {selectMode ? (
                  <Checkbox
                    checked={selected.has(Number(ad.id))}
                    onChange={() => toggleSelect(Number(ad.id))}
                    inputProps={{ 'aria-label': `选择收藏：${ad.title}` }}
                    sx={{ position: 'absolute', top: 6, right: 6, zIndex: 5, bgcolor: 'rgba(255,255,255,.9)', borderRadius: 1 }}
                  />
                ) : null}
                <AdCard
                  ad={ad}
                  page="favorites"
                  position={index + 1}
                  onHidden={() => reload()}
                />
                {!selectMode ? (
                  <Box sx={{ mt: 0.75, textAlign: 'right' }}>
                    <Button size="small" onClick={() => handleCancelOne(ad)} sx={{ fontSize: 12, color: '#5A6472' }}>
                      取消收藏
                    </Button>
                  </Box>
                ) : null}
              </Box>
            ))}
          </AdGrid>
        </Box>
      ) : null}

      {expiredItems.length > 0 ? (
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mb: 1.25 }}>
            <Typography component="h2" sx={{ fontSize: 16, fontWeight: 700, color: '#5A6472' }}>
              已结束（{expiredItems.length}）
            </Typography>
            <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>广告已过期或下架，仅保留记录</Typography>
          </Box>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', md: 'repeat(3, minmax(0, 1fr))' },
              gap: 1.5,
            }}
          >
            {expiredItems.map((ad) => (
              <Box
                key={ad.id}
                sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: 1.5, opacity: 0.9 }}
              >
                <Typography className="adx-clamp-2" sx={{ fontSize: 14, fontWeight: 600, color: '#5A6472', minHeight: '2.8em' }}>
                  {ad.title}
                </Typography>
                <Typography sx={{ fontSize: 12, color: '#8A8F98', mt: 0.5 }}>
                  {ad.merchant_name || '商家未提供'} · 已结束
                </Typography>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                  <Button size="small" onClick={() => handleCancelOne(ad)} sx={{ fontSize: 12, color: '#5A6472', minWidth: 0 }}>
                    取消收藏
                  </Button>
                  <Button
                    size="small"
                    onClick={() => navigate(`/ad/${ad.id}`)}
                    sx={{ fontSize: 12, color: '#1F3A5F', minWidth: 0 }}
                  >
                    查看详情
                  </Button>
                </Box>
              </Box>
            ))}
          </Box>
        </Box>
      ) : null}

      <ConfirmDialog
        open={confirmOpen}
        title="取消所选收藏"
        description={`将取消 ${selected.size} 条收藏记录，广告本身不受影响。`}
        confirmText="取消收藏"
        danger
        loading={removing}
        onConfirm={handleBatchCancel}
        onClose={() => setConfirmOpen(false)}
      />
    </Box>
  );
}
