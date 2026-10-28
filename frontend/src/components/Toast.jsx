import React from 'react';
import Box from '@mui/material/Box';
import { useToast } from '../context/ToastContext.jsx';
import { IconCheckCircle, IconClose, IconInfo, IconWarn } from './icons.jsx';

const LEVEL_STYLE = {
  info: { bg: '#33404F', color: '#FFFFFF', Icon: IconInfo },
  success: { bg: '#1E7A46', color: '#FFFFFF', Icon: IconCheckCircle },
  error: { bg: '#B3261E', color: '#FFFFFF', Icon: IconWarn },
  warning: { bg: '#8A5300', color: '#FFFFFF', Icon: IconWarn },
};

/** 轻提示渲染位：读 ToastContext，固定在底部居中，不阻挡点击 */
export default function Toast() {
  const { toasts, removeToast } = useToast();

  if (!toasts || toasts.length === 0) return null;

  return (
    <Box
      role="status"
      aria-live="polite"
      sx={{
        position: 'fixed',
        left: '50%',
        bottom: 'calc(20px + env(safe-area-inset-bottom, 0px))',
        transform: 'translateX(-50%)',
        zIndex: 1500,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        alignItems: 'center',
        pointerEvents: 'none',
        px: 2,
        width: 'min(92vw, 480px)',
      }}
    >
      {toasts.map((item) => {
        const style = LEVEL_STYLE[item.level] || LEVEL_STYLE.info;
        const LevelIcon = style.Icon;
        return (
          <Box
            key={item.id}
            sx={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 1,
              width: '100%',
              px: 1.75,
              py: 1.25,
              borderRadius: 2,
              bgcolor: style.bg,
              color: style.color,
              boxShadow: '0 8px 24px rgba(15,23,42,.24)',
              fontSize: 14,
              lineHeight: 1.55,
              pointerEvents: 'auto',
            }}
          >
            <Box sx={{ mt: '2px', display: 'flex' }}>
              <LevelIcon size={16} />
            </Box>
            <Box sx={{ flex: 1, overflowWrap: 'anywhere' }}>{item.message}</Box>
            <Box
              component="button"
              type="button"
              aria-label="关闭提示"
              onClick={() => removeToast(item.id)}
              sx={{
                border: 0,
                bgcolor: 'transparent',
                color: 'inherit',
                cursor: 'pointer',
                p: 0,
                display: 'flex',
                opacity: 0.75,
                '&:hover': { opacity: 1 },
              }}
            >
              <IconClose size={14} />
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}
