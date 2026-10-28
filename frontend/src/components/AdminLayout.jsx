import React, { useEffect, useState } from 'react';
import { Link as RouterLink, NavLink, Outlet, useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Badge from '@mui/material/Badge';
import { IconLogout, IconRefresh } from './icons.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { getSummary } from '../api/admin.js';
import { countText } from '../utils/format.js';

const NAV = [
  { to: '/admin', label: '运营首页', end: true },
  { to: '/admin/review', label: '审核队列', badge: 'pending_ads' },
  { to: '/admin/reports', label: '举报处理', badge: 'pending_reports' },
  { to: '/admin/ads', label: '广告管理' },
  { to: '/admin/merchants', label: '商家管理' },
  { to: '/admin/categories', label: '分类管理' },
  { to: '/admin/stats', label: '基础分析' },
];

/**
 * 后台骨架：顶栏（待审/举报/超时/今日事件徽标）+ 侧边导航 + 内容区。
 * 徽标数字来自 GET /api/admin/summary，与各列表过滤结果一致（P1-O-03）。
 */
export default function AdminLayout() {
  const auth = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    let alive = true;
    getSummary()
      .then((data) => {
        if (alive) setSummary(data);
      })
      .catch(() => {
        /* 徽标失败不阻塞页面 */
      });
    return () => {
      alive = false;
    };
  }, []);

  const refreshSummary = async () => {
    try {
      setSummary(await getSummary());
      showToast('已刷新概览数据', 'success');
    } catch (err) {
      showToast(err.message || '刷新失败', 'error');
    }
  };

  const handleLogout = async () => {
    await auth.logout();
    showToast('已退出登录', 'info');
    navigate('/admin/login', { replace: true });
  };

  const badgeValue = (key) => Number(summary && summary[key]) || 0;

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#F7F8FA', display: 'flex', flexDirection: 'column' }}>
      <Box component="header" sx={{ bgcolor: '#1F3A5F', color: '#fff', position: 'sticky', top: 0, zIndex: 1200 }}>
        <Box
          sx={{
            maxWidth: 1440,
            mx: 'auto',
            px: { xs: 2, sm: 3 },
            py: 1.25,
            display: 'flex',
            alignItems: 'center',
            gap: { xs: 1, sm: 2 },
            flexWrap: 'wrap',
          }}
        >
          <Box component={RouterLink} to="/admin" sx={{ display: 'flex', alignItems: 'center', gap: 1, textDecoration: 'none', color: '#fff', mr: 'auto' }}>
            <Box
              aria-hidden="true"
              sx={{
                width: 24,
                height: 24,
                borderRadius: '6px',
                bgcolor: 'rgba(255,255,255,.16)',
                fontSize: 12,
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              运
            </Box>
            <Typography sx={{ fontSize: 15, fontWeight: 700, whiteSpace: 'nowrap' }}>运营后台</Typography>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 1, sm: 2 }, flexWrap: 'wrap' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, fontSize: 13 }}>
              <Typography component="span" sx={{ fontSize: 13, color: 'rgba(255,255,255,.72)' }}>
                待审
              </Typography>
              <Typography component="span" sx={{ fontSize: 13, fontWeight: 700 }}>
                {countText(badgeValue('pending_ads'))}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, fontSize: 13 }}>
              <Typography component="span" sx={{ fontSize: 13, color: 'rgba(255,255,255,.72)' }}>
                举报
              </Typography>
              <Typography component="span" sx={{ fontSize: 13, fontWeight: 700 }}>
                {countText(badgeValue('pending_reports'))}
              </Typography>
              {badgeValue('sla_overdue_reports') > 0 ? (
                <Box
                  component="span"
                  sx={{ ml: 0.5, px: 0.75, borderRadius: '4px', bgcolor: '#E8590C', fontSize: 11, fontWeight: 700 }}
                >
                  超时 {badgeValue('sla_overdue_reports')}
                </Box>
              ) : null}
            </Box>
            <Box sx={{ display: { xs: 'none', sm: 'flex' }, alignItems: 'center', gap: 0.5 }}>
              <Typography component="span" sx={{ fontSize: 13, color: 'rgba(255,255,255,.72)' }}>
                今日事件
              </Typography>
              <Typography component="span" sx={{ fontSize: 13, fontWeight: 700 }}>
                {countText(badgeValue('today_events'))}
              </Typography>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Button
              size="small"
              onClick={refreshSummary}
              startIcon={<IconRefresh size={14} />}
              sx={{ color: 'rgba(255,255,255,.85)', fontSize: 12 }}
            >
              刷新
            </Button>
            <Typography sx={{ fontSize: 12, color: 'rgba(255,255,255,.85)', display: { xs: 'none', md: 'block' } }}>
              {auth.me ? auth.me.display_name || auth.me.username : ''}
            </Typography>
            <Button
              size="small"
              onClick={handleLogout}
              startIcon={<IconLogout size={14} />}
              sx={{ color: 'rgba(255,255,255,.85)', fontSize: 12 }}
            >
              退出
            </Button>
          </Box>
        </Box>
      </Box>

      <Box sx={{ flex: 1, maxWidth: 1440, width: '100%', mx: 'auto', display: 'flex', alignItems: 'stretch', px: { xs: 0, sm: 2 } }}>
        <Box
          component="nav"
          aria-label="后台导航"
          sx={{
            width: { xs: '100%', sm: 168 },
            flex: '0 0 auto',
            bgcolor: { xs: '#FFFFFF', sm: 'transparent' },
            borderRight: { sm: '1px solid #E2E6EC' },
            borderBottom: { xs: '1px solid #E2E6EC', sm: 'none' },
            py: { xs: 0, sm: 2 },
            display: 'flex',
            flexDirection: { xs: 'row', sm: 'column' },
            gap: 0.25,
            overflowX: { xs: 'auto', sm: 'visible' },
          }}
        >
          {NAV.map((item) => (
            <Box
              key={item.to}
              component={NavLink}
              to={item.to}
              end={item.end}
              sx={{
                px: 1.5,
                py: 1,
                mx: { xs: 0.5, sm: 0 },
                my: { xs: 0.5, sm: 0 },
                borderRadius: 2,
                fontSize: 13,
                fontWeight: 600,
                textDecoration: 'none',
                color: '#5A6472',
                whiteSpace: 'nowrap',
                display: 'flex',
                alignItems: 'center',
                gap: 0.75,
                '&.active': { color: '#1F3A5F', bgcolor: 'rgba(31,58,95,.08)' },
                '&:hover': { color: '#1F3A5F' },
              }}
            >
              {item.label}
              {item.badge ? (
                <Badge
                  badgeContent={badgeValue(item.badge)}
                  max={99}
                  showZero={false}
                  sx={{ '& .MuiBadge-badge': { bgcolor: '#E8590C', color: '#fff', fontSize: 10, height: 16, minWidth: 16 } }}
                />
              ) : null}
            </Box>
          ))}
        </Box>

        <Box component="main" sx={{ flex: 1, minWidth: 0, px: { xs: 2, sm: 3 }, py: { xs: 2, sm: 2.5 } }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
