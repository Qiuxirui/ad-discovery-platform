import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import { useAuth } from '../context/AuthContext.jsx';

/**
 * 路由守卫：role 校验，未登录跳对应登录页并带回跳地址。
 * 服务端仍会独立校验（前端守卫只是体验层，不是安全边界）。
 *
 * @param {{role: 'merchant'|'admin', children?: React.ReactNode}} props
 */
export default function RequireAuth({ role, children }) {
  const auth = useAuth();
  const location = useLocation();

  if (auth.loading) {
    return (
      <Box sx={{ minHeight: '60vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
        <CircularProgress size={26} />
        <Typography sx={{ fontSize: 13, color: '#5A6472' }}>正在校验登录状态…</Typography>
      </Box>
    );
  }

  if (auth.role !== role) {
    const loginPath = role === 'admin' ? '/admin/login' : '/merchant/login';
    return (
      <Navigate
        to={loginPath}
        replace
        state={{ from: `${location.pathname}${location.search || ''}` }}
      />
    );
  }

  return children || <Outlet />;
}
