import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Box from '@mui/material/Box';
import Header from './Header.jsx';
import Footer from './Footer.jsx';
import NoticeBar from './NoticeBar.jsx';

/**
 * 用户端骨架：Header + NoticeBar（仅首页）+ 内容区 + Footer。
 * 全站在架为 0 时不阻塞浏览，空态由各页面自行渲染。
 */
export default function AppLayout() {
  const location = useLocation();
  const showNotice = location.pathname === '/';

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', bgcolor: '#F7F8FA' }}>
      <Box component="a" href="#main-content" sx={skipLinkSx}>
        跳到主要内容
      </Box>
      <Header />
      {showNotice ? <NoticeBar /> : null}
      <Box
        component="main"
        id="main-content"
        sx={{ flex: 1, maxWidth: 1200, mx: 'auto', width: '100%', px: { xs: 2, sm: 3 }, py: { xs: 2, sm: 3 } }}
      >
        <Outlet />
      </Box>
      <Footer />
    </Box>
  );
}

const skipLinkSx = {
  position: 'absolute',
  left: -9999,
  top: 0,
  zIndex: 2000,
  bgcolor: '#1F3A5F',
  color: '#fff',
  px: 2,
  py: 1,
  borderRadius: 1,
  fontSize: 14,
  '&:focus': { left: 12, top: 12 },
};
