import React, { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import { NOTICE_BAR_TEXT } from '../constants/messages.js';
import { IconClose, IconInfo } from './icons.jsx';

const STORAGE_KEY = 'adx:notice-dismissed-at';
const SEVEN_DAYS = 7 * 24 * 60 * 60 * 1000;

/** 读取"是否仍在 7 天静默期" */
function isDismissed() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    const ts = Number(raw);
    if (!Number.isFinite(ts)) return false;
    return Date.now() - ts < SEVEN_DAYS;
  } catch {
    return false;
  }
}

/** 页脚「平台说明」调用：清除静默标记，重新显示说明条 */
export function resetNoticeDismissed() {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* localStorage 不可用时忽略 */
  }
}

/**
 * 首页顶部说明条（PRD §6.3 精确文案，首屏可见）。
 * 关闭后 7 天内不再出现，页脚常驻入口可重开。
 */
export default function NoticeBar() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(!isDismissed());
  }, []);

  const dismiss = () => {
    try {
      window.localStorage.setItem(STORAGE_KEY, String(Date.now()));
    } catch {
      /* 忽略写入失败，本次会话仍隐藏 */
    }
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <Box
      component="section"
      aria-label="平台说明"
      sx={{
        bgcolor: '#EEF2F7',
        borderBottom: '1px solid #DCE3EB',
      }}
    >
      <Box
        sx={{
          maxWidth: 1200,
          mx: 'auto',
          px: { xs: 2, sm: 3 },
          py: 1,
          display: 'flex',
          alignItems: 'flex-start',
          gap: 1,
        }}
      >
        <Box sx={{ color: '#1F3A5F', mt: '2px', display: 'flex' }} aria-hidden="true">
          <IconInfo size={16} />
        </Box>
        <Typography
          component="p"
          sx={{ flex: 1, m: 0, fontSize: { xs: 13, sm: 14 }, color: '#33404F', lineHeight: 1.6 }}
        >
          {NOTICE_BAR_TEXT}
          <Link
            component={RouterLink}
            to="/policy/ads"
            underline="hover"
            sx={{ ml: 0.5, fontSize: 'inherit', color: '#1F3A5F', fontWeight: 600 }}
          >
            查看广告政策
          </Link>
        </Typography>
        <Box
          component="button"
          type="button"
          onClick={dismiss}
          aria-label="关闭平台说明"
          sx={{
            border: 0,
            bgcolor: 'transparent',
            color: '#5A6472',
            cursor: 'pointer',
            p: 0.5,
            display: 'flex',
            mt: '-2px',
            '&:hover': { color: '#1F3A5F' },
          }}
        >
          <IconClose size={16} />
        </Box>
      </Box>
    </Box>
  );
}
