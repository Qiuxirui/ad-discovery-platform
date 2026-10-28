import React from 'react';
import { Link as RouterLink, NavLink, Outlet, useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import { IconLogout } from './icons.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useToast } from '../context/ToastContext.jsx';

const NAV = [
  { to: '/merchant/ads', label: '我的广告' },
  { to: '/merchant/report', label: '效果报告' },
  { to: '/merchant/profile', label: '商家资料' },
];

/** 商家端骨架：顶栏 + 导航 + 登出，内容区渲染 <Outlet/> */
export default function MerchantLayout() {
  const auth = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const handleLogout = async () => {
    await auth.logout();
    showToast('已退出登录', 'info');
    navigate('/merchant/login', { replace: true });
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#F7F8FA', display: 'flex', flexDirection: 'column' }}>
      <Box
        component="header"
        sx={{ bgcolor: '#FFFFFF', borderBottom: '1px solid #E2E6EC', position: 'sticky', top: 0, zIndex: 1100 }}
      >
        <Box
          sx={{
            maxWidth: 1200,
            mx: 'auto',
            px: { xs: 2, sm: 3 },
            display: 'flex',
            alignItems: 'center',
            gap: { xs: 1, sm: 2 },
            flexWrap: 'wrap',
            py: 1.25,
          }}
        >
          <Box
            component={RouterLink}
            to="/merchant/ads"
            sx={{ display: 'flex', alignItems: 'center', gap: 1, textDecoration: 'none', color: '#1F3A5F', mr: 'auto' }}
          >
            <Box
              aria-hidden="true"
              sx={{
                width: 24,
                height: 24,
                borderRadius: '6px',
                bgcolor: '#1F3A5F',
                color: '#fff',
                fontSize: 12,
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              商
            </Box>
            <Typography sx={{ fontSize: 15, fontWeight: 700, whiteSpace: 'nowrap' }}>商家后台</Typography>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'wrap' }}>
            {NAV.map((item) => (
              <Box
                key={item.to}
                component={NavLink}
                to={item.to}
                sx={{
                  px: 1.25,
                  py: 0.75,
                  borderRadius: 2,
                  fontSize: 14,
                  fontWeight: 600,
                  textDecoration: 'none',
                  color: '#5A6472',
                  '&.active': { color: '#1F3A5F', bgcolor: 'rgba(31,58,95,.08)' },
                  '&:hover': { color: '#1F3A5F' },
                }}
              >
                {item.label}
              </Box>
            ))}
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography sx={{ fontSize: 13, color: '#5A6472', display: { xs: 'none', sm: 'block' } }}>
              {auth.me ? auth.me.name : ''}
            </Typography>
            <Button
              size="small"
              onClick={handleLogout}
              startIcon={<IconLogout size={15} />}
              sx={{ fontSize: 13, color: '#5A6472' }}
            >
              退出登录
            </Button>
          </Box>
        </Box>
      </Box>

      <Box
        component="main"
        sx={{ flex: 1, maxWidth: 1200, mx: 'auto', width: '100%', px: { xs: 2, sm: 3 }, py: { xs: 2, sm: 3 } }}
      >
        <Outlet />
      </Box>

      <Box component="footer" sx={{ borderTop: '1px solid #E2E6EC', bgcolor: '#FFFFFF', py: 2 }}>
        <Typography sx={{ fontSize: 12, color: '#8A8F98', textAlign: 'center' }}>
          商家后台 · 提交内容将公开标注为「广告」，并接受平台审核
        </Typography>
      </Box>
    </Box>
  );
}
