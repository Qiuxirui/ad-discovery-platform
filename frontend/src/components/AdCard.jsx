import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Paper from '@mui/material/Paper';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import AdBadge from './AdBadge.jsx';
import ReportDialog from './ReportDialog.jsx';
import { IconEyeOff, IconImage, IconMore, IconReport, IconStar } from './icons.jsx';
import useTrackImpression from '../hooks/useTrackImpression.js';
import { useVisitor } from '../context/VisitorContext.jsx';
import { ENDING_SOON_LABEL, validToText } from '../utils/format.js';

/**
 * 广告卡片（PRD P0-B-04 / P0-T-01）。
 * 结构：图片区（「广告」角标 + 「即将结束」徽标）→ 标题 2 行 → 价格 → 商家 → 城市/有效期 → 收藏/更多菜单。
 * preview=true 时用于商家表单实时预览：不链接、不埋点、无操作按钮。
 *
 * @param {{ad: object, page?: string, position?: number, preview?: boolean, showActions?: boolean, onHidden?: (id:number)=>void, sx?: object}} props
 */
export default function AdCard({ ad, page = 'list', position, preview = false, showActions = true, onHidden, sx }) {
  const { favorites, toggleFavorite, hide } = useVisitor();
  const [imgError, setImgError] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [reportOpen, setReportOpen] = useState(false);

  const impressionRef = useTrackImpression({
    adId: ad && ad.id,
    page,
    position,
    enabled: Boolean(!preview && ad && ad.id),
  });

  if (!ad) return null;

  const adId = Number(ad.id);
  const favorited = favorites.has(adId);
  const detailPath = `/ad/${adId}`;

  const handleFavorite = async (event) => {
    event.preventDefault();
    event.stopPropagation();
    await toggleFavorite(adId);
  };

  const handleHide = async () => {
    setMenuAnchor(null);
    const ok = await hide(adId);
    if (ok && onHidden) onHidden(adId);
  };

  const openMenu = (event) => {
    event.preventDefault();
    event.stopPropagation();
    setMenuAnchor(event.currentTarget);
  };

  const closeMenu = () => setMenuAnchor(null);

  const openReport = () => {
    setMenuAnchor(null);
    setReportOpen(true);
  };

  return (
    <Paper
      ref={impressionRef}
      className={preview ? undefined : 'adx-card-hover'}
      sx={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: '#FFFFFF',
        borderRadius: '12px',
        border: '1px solid #E2E6EC',
        boxShadow: '0 1px 2px rgba(15,23,42,.06)',
        overflow: 'hidden',
        height: '100%',
        minWidth: 0,
        ...sx,
      }}
    >
      {/* 整卡点击层：覆盖卡片、键盘可达；操作按钮层级更高 */}
      {!preview ? (
        <Box
          component={RouterLink}
          to={detailPath}
          aria-label={`查看广告详情：${ad.title || ''}`}
          sx={{ position: 'absolute', inset: 0, zIndex: 1, borderRadius: '12px' }}
        />
      ) : null}

      <Box sx={{ p: 1.25, pb: 0 }}>
        <Box className="adx-card-media">
          {ad.image_path && !imgError ? (
            <Box
              component="img"
              className="adx-card-img"
              src={ad.image_path}
              alt=""
              loading="lazy"
              onError={() => setImgError(true)}
            />
          ) : (
            <Box className="adx-card-img-fallback" aria-hidden="true">
              <IconImage size={30} />
            </Box>
          )}

          {/* 角标：不随 hover 消失，图片失败时仍渲染，375px 窄屏不裁切 */}
          <AdBadge />

          {ad.expiring_soon ? (
            <Box
              component="span"
              className="adx-badge-ending"
              sx={{ position: 'absolute', top: '8px', right: '8px', zIndex: 3 }}
            >
              {ENDING_SOON_LABEL}
            </Box>
          ) : null}
        </Box>
      </Box>

      <Box sx={{ p: 1.25, pt: 1, display: 'flex', flexDirection: 'column', gap: 0.5, flex: 1, minWidth: 0 }}>
        <Typography
          component="h3"
          className="adx-clamp-2"
          sx={{ fontSize: 15, fontWeight: 700, lineHeight: 1.45, color: '#1A1A1A', minHeight: '2.9em' }}
        >
          {ad.title || '未命名广告'}
        </Typography>

        <Typography
          sx={{
            fontSize: 15,
            fontWeight: 700,
            color: '#B3261E',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {ad.price_text || '价格未提供'}
        </Typography>

        <Typography className="adx-clamp-1" sx={{ fontSize: 13, color: '#5A6472' }}>
          {ad.merchant_name || '商家未提供'}
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, minWidth: 0 }}>
          <Typography className="adx-clamp-1" sx={{ fontSize: 12, color: '#8A8F98', flex: 1, minWidth: 0 }}>
            {ad.city || '全国'} · {validToText(ad.valid_to_local_date)}
          </Typography>
        </Box>
      </Box>

      {showActions && !preview ? (
        <Box
          sx={{
            position: 'absolute',
            right: 6,
            bottom: 4,
            zIndex: 2,
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <Tooltip title={favorited ? '取消收藏' : '收藏'}>
            <IconButton
              size="small"
              onClick={handleFavorite}
              aria-label={favorited ? '取消收藏' : '收藏'}
              aria-pressed={favorited}
              sx={{ color: favorited ? '#E8590C' : '#8A8F98', '&:hover': { color: '#E8590C' } }}
            >
              <IconStar size={17} filled={favorited} />
            </IconButton>
          </Tooltip>
          <Tooltip title="更多">
            <IconButton
              size="small"
              onClick={openMenu}
              aria-label="更多操作"
              aria-haspopup="menu"
              sx={{ color: '#8A8F98' }}
            >
              <IconMore size={17} />
            </IconButton>
          </Tooltip>
        </Box>
      ) : null}

      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={closeMenu}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        MenuListProps={{ dense: true }}
      >
        <MenuItem onClick={handleHide}>
          <ListItemIcon sx={{ minWidth: 30 }}>
            <IconEyeOff size={16} />
          </ListItemIcon>
          <ListItemText primaryTypographyProps={{ fontSize: 14 }}>不感兴趣</ListItemText>
        </MenuItem>
        <MenuItem onClick={openReport}>
          <ListItemIcon sx={{ minWidth: 30 }}>
            <IconReport size={16} />
          </ListItemIcon>
          <ListItemText primaryTypographyProps={{ fontSize: 14 }}>举报</ListItemText>
        </MenuItem>
      </Menu>

      {!preview ? (
        <ReportDialog
          open={reportOpen}
          adId={adId}
          adTitle={ad.title}
          onClose={() => setReportOpen(false)}
        />
      ) : null}
    </Paper>
  );
}
