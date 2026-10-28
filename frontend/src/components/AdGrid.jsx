import React from 'react';
import Box from '@mui/material/Box';

/**
 * 响应式广告网格：手机 1 列 / 平板 2 列 / 桌面 3 列。
 * 严禁使用 MUI Grid（v6 已换 API，老写法会静默错位），统一 Box + CSS Grid。
 *
 * @param {{children: React.ReactNode, columns?: {xs?: string, sm?: string, md?: string}, gap?: number, sx?: object}} props
 */
export default function AdGrid({ children, columns, gap = 2, sx }) {
  const cols = columns || { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', md: 'repeat(3, minmax(0, 1fr))' };
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: cols,
        gap,
        alignItems: 'stretch',
        ...sx,
      }}
    >
      {children}
    </Box>
  );
}
