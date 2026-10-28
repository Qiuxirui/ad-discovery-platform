import React, { useEffect, useState } from 'react';
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import InputBase from '@mui/material/InputBase';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import { IconSearch, IconStar } from './icons.jsx';

/**
 * 用户端顶栏：Logo、搜索框（回车跳 /search）、收藏、偏好。
 * 窄屏时搜索框折到第二行并占满宽度。
 */
export default function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const [keyword, setKeyword] = useState('');

  // 在搜索页时回填关键词；离开搜索页清空，避免误导
  useEffect(() => {
    if (location.pathname === '/search') {
      const params = new URLSearchParams(location.search);
      setKeyword(params.get('q') || '');
    } else {
      setKeyword('');
    }
  }, [location.pathname, location.search]);

  const submitSearch = (event) => {
    event.preventDefault();
    const value = keyword.trim();
    if (value) {
      navigate(`/search?q=${encodeURIComponent(value)}`);
      return;
    }
    navigate('/search');
  };

  return (
    <Box
      component="header"
      sx={{
        position: 'sticky',
        top: 0,
        zIndex: 1100,
        bgcolor: '#FFFFFF',
        borderBottom: '1px solid #E2E6EC',
      }}
    >
      <Box
        sx={{
          maxWidth: 1200,
          mx: 'auto',
          px: { xs: 2, sm: 3 },
          py: 1.25,
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: { xs: 1, sm: 2 },
        }}
      >
        <Box
          component={RouterLink}
          to="/"
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            textDecoration: 'none',
            color: '#1F3A5F',
            flex: '0 0 auto',
            mr: { xs: 'auto', sm: 0 },
          }}
        >
          <Box
            aria-hidden="true"
            sx={{
              width: 26,
              height: 26,
              borderRadius: '7px',
              bgcolor: '#1F3A5F',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 13,
              fontWeight: 700,
              letterSpacing: 0.5,
            }}
          >
            广
          </Box>
          <Typography
            component="span"
            sx={{ fontSize: { xs: 16, sm: 17 }, fontWeight: 700, letterSpacing: 0.2, whiteSpace: 'nowrap' }}
          >
            广告发现站
          </Typography>
        </Box>

        <Box
          component="form"
          role="search"
          onSubmit={submitSearch}
          sx={{
            order: { xs: 3, sm: 2 },
            width: { xs: '100%', sm: 'auto' },
            flex: { sm: '1 1 260px' },
            maxWidth: { sm: 460 },
            display: 'flex',
            alignItems: 'center',
            gap: 0.75,
            px: 1.25,
            height: 38,
            border: '1px solid #E2E6EC',
            borderRadius: 2,
            bgcolor: '#F7F8FA',
            transition: 'border-color 150ms ease, background-color 150ms ease',
            '&:focus-within': { borderColor: '#1F3A5F', bgcolor: '#fff' },
          }}
        >
          <Box sx={{ color: '#5A6472', display: 'flex' }}>
            <IconSearch size={17} />
          </Box>
          <InputBase
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="搜索商业信息…"
            inputProps={{ 'aria-label': '搜索商业信息', maxLength: 60 }}
            sx={{ flex: 1, fontSize: 14 }}
          />
          <Box
            component="button"
            type="submit"
            sx={{
              border: 0,
              bgcolor: '#1F3A5F',
              color: '#fff',
              borderRadius: 1.5,
              fontSize: 13,
              fontWeight: 600,
              px: 1.25,
              py: 0.5,
              cursor: 'pointer',
              flex: '0 0 auto',
              '&:hover': { bgcolor: '#17304F' },
            }}
          >
            搜索
          </Box>
        </Box>

        <Box
          sx={{
            order: { xs: 2, sm: 3 },
            display: 'flex',
            alignItems: 'center',
            gap: { xs: 0.5, sm: 1.5 },
            ml: { sm: 'auto' },
            flex: '0 0 auto',
          }}
        >
          <IconButton
            component={RouterLink}
            to="/favorites"
            size="small"
            aria-label="收藏"
            sx={{ color: '#1F3A5F', gap: 0.5, borderRadius: 2, px: 1, width: 'auto' }}
          >
            <IconStar size={18} />
            <Typography component="span" sx={{ fontSize: 14, fontWeight: 600 }}>
              收藏
            </Typography>
          </IconButton>
          <IconButton
            component={RouterLink}
            to="/preferences"
            size="small"
            aria-label="偏好设置"
            sx={{ color: '#5A6472', borderRadius: 2, px: 1, width: 'auto' }}
          >
            <Typography component="span" sx={{ fontSize: 14, fontWeight: 600 }}>
              偏好
            </Typography>
          </IconButton>
        </Box>
      </Box>
      <Box sx={{ maxWidth: 1200, mx: 'auto', px: { xs: 2, sm: 3 } }}>
        <Link
          component={RouterLink}
          to="/report-status"
          underline="hover"
          sx={{ display: { xs: 'none', sm: 'inline-block' }, fontSize: 12, color: '#5A6472', pb: 0.75 }}
        >
          举报进度查询
        </Link>
      </Box>
    </Box>
  );
}
