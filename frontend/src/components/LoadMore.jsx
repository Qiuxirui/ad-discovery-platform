import React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import { COMMON } from '../constants/messages.js';

/**
 * 列表底部动作：可点「加载更多」，到底显示「没有更多了」。
 * 不做无限滚动（PRD P0-B-06：避免无边界信息流）。
 *
 * @param {{hasMore:boolean, loading:boolean, count?:number, onClick:()=>void, error?:string}} props
 */
export default function LoadMore({ hasMore, loading, count = 0, onClick, error }) {
  if (!hasMore && count === 0) return null;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1, py: 3 }}>
      {error ? (
        <Box sx={{ fontSize: 13, color: '#B3261E', mb: 0.5 }}>{error}</Box>
      ) : null}
      {hasMore ? (
        <Button
          variant="outlined"
          onClick={onClick}
          disabled={loading}
          startIcon={loading ? <CircularProgress size={14} /> : null}
          sx={{
            minWidth: 160,
            borderColor: '#C9D2DD',
            color: '#1F3A5F',
            '&:hover': { borderColor: '#1F3A5F', bgcolor: 'rgba(31,58,95,.04)' },
          }}
        >
          {loading ? COMMON.loading : COMMON.loadMore}
        </Button>
      ) : (
        <Box sx={{ fontSize: 13, color: '#8A8F98', py: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box component="span" sx={{ width: 24, height: 1, bgcolor: '#DCE3EB' }} />
          {COMMON.noMore}
          <Box component="span" sx={{ width: 24, height: 1, bgcolor: '#DCE3EB' }} />
        </Box>
      )}
      {count > 0 ? (
        <Box sx={{ fontSize: 12, color: '#A7AEB8' }}>已加载 {count} 条</Box>
      ) : null}
    </Box>
  );
}
