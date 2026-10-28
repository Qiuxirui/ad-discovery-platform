import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink, useNavigate, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Link from '@mui/material/Link';
import Skeleton from '@mui/material/Skeleton';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import AdBadge from '../components/AdBadge.jsx';
import AdGrid from '../components/AdGrid.jsx';
import AdCard from '../components/AdCard.jsx';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import EmptyState from '../components/EmptyState.jsx';
import ReportDialog from '../components/ReportDialog.jsx';
import StatusChip from '../components/StatusChip.jsx';
import { IconExternal, IconReport, IconStar, IconEyeOff, IconEye, IconClock, IconShield } from '../components/icons.jsx';
import { getAdDetail, getRelatedAds } from '../api/public.js';
import useApi from '../hooks/useApi.js';
import tracker from '../tracker/index.js';
import { useVisitor } from '../context/VisitorContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import {
  AD_NOT_VISIBLE,
  CTA_GO,
  LEAVE_NOTE,
  NO_RESTRICTION,
  WHY_LINK,
  detailAttribution,
} from '../constants/messages.js';
import { daysLeftText, formatMonthCN, formatRangeCN, validToText } from '../utils/format.js';

/** 信息行：标签 + 值 */
function InfoRow({ label, children }) {
  return (
    <Box sx={{ display: 'flex', gap: 1.5, py: 0.75, alignItems: 'flex-start' }}>
      <Typography sx={{ fontSize: 13, color: '#5A6472', width: 68, flex: '0 0 auto', lineHeight: 1.7 }}>
        {label}
      </Typography>
      <Box sx={{ fontSize: 14, color: '#1A1A1A', lineHeight: 1.7, flex: 1, minWidth: 0, overflowWrap: 'anywhere' }}>
        {children}
      </Box>
    </Box>
  );
}

/**
 * 广告详情（P0-B-05 / P0-T-02 / P0-T-03 / P0-T-04）。
 * 含「广告 · 由 X 提供」、价格/优惠/有效期/城市/限制条款、外链按钮 + 即将离开本平台提示、
 * 收藏/不感兴趣/举报、商家块、同类 3 条；不可见时给「该广告已结束或暂不可见」+ 同类推荐。
 */
export default function AdDetailPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { favorites, hides, toggleFavorite, hide, unhide } = useVisitor();

  const [reportOpen, setReportOpen] = useState(false);
  const [confirmHideOpen, setConfirmHideOpen] = useState(false);
  const viewTrackedRef = useRef(false);

  const detail = useApi(() => getAdDetail(id), [id]);
  const { data, loading, error, reload } = detail;

  const notVisible = Boolean(error && (error.code === 'AD_NOT_VISIBLE' || error.status === 404 || error.status === 410));

  const relatedApi = useApi(
    () => getRelatedAds(id, 3).catch(() => []),
    [id, notVisible],
    { enabled: notVisible },
  );

  // detail_view：主内容渲染后停留 ≥1000ms 才上报，每次挂载最多 1 次
  useEffect(() => {
    if (!data || !data.id) return undefined;
    const timer = window.setTimeout(() => {
      if (viewTrackedRef.current) return;
      viewTrackedRef.current = true;
      tracker.track('detail_view', { ad_id: data.id, page: 'detail' });
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [data]);

  const related = useMemo(() => {
    if (notVisible) return Array.isArray(relatedApi.data) ? relatedApi.data : [];
    return Array.isArray(data && data.related) ? data.related : [];
  }, [data, notVisible, relatedApi.data]);

  if (loading) {
    return (
      <Box>
        <Skeleton width={220} height={18} sx={{ mb: 2 }} />
        <Skeleton width="55%" height={30} sx={{ mb: 2 }} />
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1.05fr 1fr' }, gap: 3 }}>
          <Skeleton variant="rounded" sx={{ width: '100%', aspectRatio: '16 / 9', height: 'auto' }} />
          <Box>
            <Skeleton height={28} />
            <Skeleton height={20} />
            <Skeleton height={20} />
            <Skeleton height={20} />
            <Skeleton variant="rounded" height={46} sx={{ mt: 2 }} />
          </Box>
        </Box>
      </Box>
    );
  }

  if (notVisible) {
    return (
      <Box>
        <EmptyState
          title={AD_NOT_VISIBLE}
          description="该广告可能已到期、被下架或尚未通过审核。你可以看看下面这些同类广告。"
          actionText="返回首页"
          onAction={() => navigate('/')}
          icon={<IconClock size={34} />}
        />
        {related.length > 0 ? (
          <Box sx={{ mt: 3 }}>
            <Typography component="h2" sx={{ fontSize: 17, fontWeight: 700, mb: 1.5 }}>
              同类广告
            </Typography>
            <AdGrid>
              {related.slice(0, 3).map((ad, index) => (
                <AdCard key={ad.id} ad={ad} page="detail" position={index + 1} />
              ))}
            </AdGrid>
          </Box>
        ) : null}
      </Box>
    );
  }

  if (error) {
    return (
      <EmptyState
        title="详情加载失败"
        description={error.message || '请稍后重试'}
        actionText="重试"
        onAction={reload}
      />
    );
  }

  if (!data) return null;

  const adId = Number(data.id);
  const favorited = favorites.has(adId);
  const hidden = hides.has(adId);
  const merchant = data.merchant || {};
  const tags = Array.isArray(data.tags) ? data.tags : [];
  const categorySlug = data.category_slug || '';

  const handleFavorite = async () => {
    await toggleFavorite(adId);
  };

  const handleHide = async () => {
    setConfirmHideOpen(false);
    const ok = await hide(adId);
    if (ok) return;
  };

  const handleUnhide = async () => {
    await unhide(adId);
  };

  return (
    <Box>
      {/* 面包屑 */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, fontSize: 13, color: '#5A6472', flexWrap: 'wrap', mb: 1.5 }}>
        <Link component={RouterLink} to="/" sx={{ fontSize: 13, color: '#5A6472' }}>
          首页
        </Link>
        <Box component="span" aria-hidden="true">›</Box>
        {categorySlug ? (
          <>
            <Link component={RouterLink} to={`/c/${categorySlug}`} sx={{ fontSize: 13, color: '#5A6472' }}>
              {data.category_name || categorySlug}
            </Link>
            <Box component="span" aria-hidden="true">›</Box>
          </>
        ) : null}
        <Typography component="span" className="adx-clamp-1" sx={{ fontSize: 13, color: '#1A1A1A', maxWidth: 320 }}>
          {data.title}
        </Typography>
      </Box>

      {/* 广告标识 + 为什么看到这条 */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Typography sx={{ fontSize: 13, fontWeight: 700, color: '#E8590C' }}>
            {detailAttribution(merchant.name || data.merchant_name)}
          </Typography>
          <Box
            component="button"
            type="button"
            onClick={() => showToast('商家主页建设中', 'info')}
            sx={{
              border: 0,
              bgcolor: 'transparent',
              color: '#1F3A5F',
              fontSize: 12,
              cursor: 'pointer',
              p: 0,
              textDecoration: 'underline',
            }}
          >
            查看商家
          </Box>
        </Box>
        <Link component={RouterLink} to="/policy/ads#why" sx={{ fontSize: 12 }}>
          {WHY_LINK}
        </Link>
      </Box>

      <Typography component="h1" sx={{ fontSize: { xs: 21, sm: 26 }, fontWeight: 700, lineHeight: 1.35, mb: 1.5 }}>
        {data.title}
      </Typography>

      {/* 主图 + 信息区 */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1.05fr 1fr' }, gap: { xs: 2, md: 3 }, alignItems: 'start' }}>
        <Box className="adx-card-media" sx={{ borderRadius: '12px', border: '1px solid #E2E6EC', bgcolor: '#EEF1F5' }}>
          {data.image_path ? (
            <Box component="img" className="adx-card-img" src={data.image_path} alt={`${data.title} 主图`} />
          ) : (
            <Box className="adx-card-img-fallback">
              <Typography sx={{ fontSize: 13 }}>商家未提供图片</Typography>
            </Box>
          )}
          <AdBadge />
        </Box>

        <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 2, sm: 2.5 } }}>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1.5, flexWrap: 'wrap', mb: 0.5 }}>
            <Typography sx={{ fontSize: { xs: 22, sm: 26 }, fontWeight: 700, color: '#B3261E', lineHeight: 1.2 }}>
              {data.price_text || '价格未提供'}
            </Typography>
            {data.expiring_soon ? (
              <Box component="span" className="adx-badge-ending">
                即将结束
              </Box>
            ) : null}
          </Box>

          <Divider sx={{ my: 1.25 }} />

          <InfoRow label="优惠条件">{data.promo_condition || '商家未提供额外优惠条件'}</InfoRow>
          <InfoRow label="有效期">
            {formatRangeCN(data.valid_from_local_date, data.valid_to_local_date)}
            <Box component="span" sx={{ ml: 1, color: data.expiring_soon ? '#E8590C' : '#5A6472', fontWeight: 600 }}>
              （{daysLeftText(data.days_left)}）
            </Box>
          </InfoRow>
          <InfoRow label="服务城市">{data.city || '全国'}</InfoRow>
          <InfoRow label="限制条款">{data.restriction || NO_RESTRICTION}</InfoRow>
          <InfoRow label="落地页域名">{data.landing_domain || '未提供'}</InfoRow>

          <Box sx={{ mt: 1.5 }}>
            <Button
              variant="contained"
              size="large"
              fullWidth
              endIcon={<IconExternal size={18} />}
              onClick={() => navigate(`/go/${adId}`)}
              sx={{ bgcolor: '#1F3A5F', '&:hover': { bgcolor: '#17304F' }, height: 48 }}
            >
              {CTA_GO}
            </Button>
            <Typography sx={{ fontSize: 12, color: '#8A8F98', mt: 0.75, lineHeight: 1.6 }}>{LEAVE_NOTE}</Typography>
          </Box>

          <Box sx={{ display: 'flex', gap: 1, mt: 1.75, flexWrap: 'wrap' }}>
            <Button
              variant="outlined"
              size="small"
              startIcon={<IconStar size={16} filled={favorited} />}
              onClick={handleFavorite}
              sx={{ borderColor: favorited ? '#E8590C' : '#C9D2DD', color: favorited ? '#E8590C' : '#1F3A5F' }}
            >
              {favorited ? '已收藏' : '收藏'}
            </Button>
            {hidden ? (
              <Button variant="outlined" size="small" startIcon={<IconEye size={16} />} onClick={handleUnhide} sx={{ borderColor: '#C9D2DD', color: '#1F3A5F' }}>
                恢复显示
              </Button>
            ) : (
              <Button
                variant="outlined"
                size="small"
                startIcon={<IconEyeOff size={16} />}
                onClick={() => setConfirmHideOpen(true)}
                sx={{ borderColor: '#C9D2DD', color: '#5A6472' }}
              >
                不感兴趣
              </Button>
            )}
            <Button
              variant="outlined"
              size="small"
              startIcon={<IconReport size={16} />}
              onClick={() => setReportOpen(true)}
              sx={{ borderColor: '#C9D2DD', color: '#5A6472' }}
            >
              举报
            </Button>
          </Box>
        </Box>
      </Box>

      {/* 商品说明 */}
      <Box sx={{ mt: 3 }}>
        <Typography component="h2" sx={{ fontSize: 17, fontWeight: 700, mb: 1 }}>
          商品说明
        </Typography>
        <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 2, sm: 2.5 } }}>
          <Typography className="adx-preline" sx={{ fontSize: 15, lineHeight: 1.85, color: '#1A1A1A' }}>
            {data.description || '商家未提供详细说明'}
          </Typography>
          {tags.length > 0 ? (
            <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mt: 2 }}>
              {tags.map((tag) => (
                <Box
                  key={tag.slug || tag.name}
                  sx={{ fontSize: 12, color: '#5A6472', bgcolor: '#F2F5F9', borderRadius: '6px', px: 1, py: 0.375 }}
                >
                  {tag.name}
                </Box>
              ))}
            </Box>
          ) : null}
          {data.status && data.status !== 'active' ? (
            <Box sx={{ mt: 2 }}>
              <StatusChip status={data.status} />
            </Box>
          ) : null}
        </Box>
      </Box>

      {/* 商家信息 */}
      <Box sx={{ mt: 3 }}>
        <Typography component="h2" sx={{ fontSize: 17, fontWeight: 700, mb: 1 }}>
          商家信息
        </Typography>
        <Box
          sx={{
            bgcolor: '#FFFFFF',
            border: '1px solid #E2E6EC',
            borderRadius: '12px',
            p: { xs: 2, sm: 2.5 },
            display: 'flex',
            flexWrap: 'wrap',
            columnGap: 3,
            rowGap: 0.75,
            alignItems: 'center',
          }}
        >
          <Typography sx={{ fontSize: 15, fontWeight: 700 }}>{merchant.name || data.merchant_name || '未提供'}</Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472' }}>城市：{merchant.city || data.city || '未提供'}</Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472' }}>
            主营类别：{merchant.main_category_name || data.category_name || '未提供'}
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472' }}>
            入驻时间：{merchant.joined_at ? formatMonthCN(merchant.joined_at) : '未提供'}
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472' }}>
            当前在架：
            {merchant.active_ad_count === undefined || merchant.active_ad_count === null
              ? '未提供'
              : `${merchant.active_ad_count} 条`}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mt: 1 }}>
          <Box sx={{ color: '#5A6472', display: 'flex' }} aria-hidden="true">
            <IconShield size={14} />
          </Box>
          <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>
            平台仅提供信息展示，不参与交易；{validToText(data.valid_to_local_date)}的广告会自动下线。
          </Typography>
        </Box>
      </Box>

      {/* 同类广告（同类别 + 同城市） */}
      {related.length > 0 ? (
        <Box sx={{ mt: 3.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mb: 1.5 }}>
            <Typography component="h2" sx={{ fontSize: 17, fontWeight: 700 }}>
              同类广告
            </Typography>
            <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>同类别 + 同城市，规则匹配</Typography>
          </Box>
          <AdGrid>
            {related.slice(0, 3).map((item, index) => (
              <AdCard key={item.id} ad={item} page="detail" position={index + 1} />
            ))}
          </AdGrid>
        </Box>
      ) : null}

      <ReportDialog open={reportOpen} adId={adId} adTitle={data.title} onClose={() => setReportOpen(false)} />

      <ConfirmDialog
        open={confirmHideOpen}
        title="不感兴趣"
        description="该广告将不再出现在你的列表中，可在「偏好设置 → 已隐藏」恢复显示。"
        confirmText="不感兴趣"
        onConfirm={handleHide}
        onClose={() => setConfirmHideOpen(false)}
      />

      <Box sx={{ mt: 3 }}>
        <Tooltip title="按最新发布排序，不接受付费加权">
          <Link component={RouterLink} to="/policy/ads" sx={{ fontSize: 12, color: '#8A8F98' }}>
            广告政策与标识说明
          </Link>
        </Tooltip>
      </Box>
    </Box>
  );
}
