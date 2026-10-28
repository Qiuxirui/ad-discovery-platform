import React from 'react';
import Box from '@mui/material/Box';
import { AD_BADGE } from '../constants/messages.js';

/**
 * 「广告」角标 —— PRD §6.3 / P0-T-01。
 * 实底强调橙 #E8590C + 白字 12px 加粗 + 圆角 4 + 距边 8px；
 * 不随滚动/hover 消失；图片加载失败时也照常渲染；375px 窄屏不裁切。
 *
 * @param {{sx?: object, offset?: number}} props
 */
export default function AdBadge({ sx, offset = 8 }) {
  return (
    <Box
      component="span"
      className="adx-badge-ad"
      sx={{
        position: 'absolute',
        top: `${offset}px`,
        left: `${offset}px`,
        zIndex: 3,
        // 保证任何父级 flex/grid 压缩都不影响角标宽度
        minWidth: 32,
        maxWidth: 'calc(100% - 16px)',
        ...sx,
      }}
    >
      {AD_BADGE}
    </Box>
  );
}
