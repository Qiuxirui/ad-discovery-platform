import React from 'react';
import Box from '@mui/material/Box';
import { AD_STATUS, REPORT_STATUS } from '../constants/enums.js';

/**
 * 状态彩色标签。颜色映射唯一来源：constants/enums.js（与后端 /api/meta 一致）。
 *
 * @param {{status?: string, kind?: 'ad'|'report', label?: string, size?: 'small'|'medium', sx?: object}} props
 */
export default function StatusChip({ status = '', kind = 'ad', label, size = 'small', sx }) {
  const table = kind === 'report' ? REPORT_STATUS : AD_STATUS;
  const meta = table[status] || null;
  const color = (meta && meta.color) || '#5A6472';
  const text = label || (meta && meta.label) || status || '未知';

  return (
    <Box
      component="span"
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        height: size === 'small' ? 22 : 26,
        px: size === 'small' ? 0.875 : 1.125,
        borderRadius: '6px',
        fontSize: size === 'small' ? 12 : 13,
        fontWeight: 700,
        lineHeight: 1,
        whiteSpace: 'nowrap',
        color,
        bgcolor: `${color}14`,
        border: `1px solid ${color}33`,
        ...sx,
      }}
    >
      {text}
    </Box>
  );
}
