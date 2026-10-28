import React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import { countText } from '../utils/format.js';

/**
 * 管理端表格分页。
 *
 * @param {{page:number, pageSize?:number, total:number, onChange:(page:number)=>void, count?:number}} props
 */
export default function Pagination({ page = 1, pageSize = 24, total = 0, onChange, count }) {
  const size = pageSize > 0 ? pageSize : 24;
  const totalPages = Math.max(1, Math.ceil((Number(total) || 0) / size));
  const current = Math.min(Math.max(1, Number(page) || 1), totalPages);
  const shown = typeof count === 'number' ? count : Math.min(size, Math.max(0, total - (current - 1) * size));

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 1,
        flexWrap: 'wrap',
        py: 1.5,
      }}
    >
      <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>
        第 {current} / {totalPages} 页 · 共 {countText(total)} 条{shown ? ` · 本页 ${shown} 条` : ''}
      </Typography>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <Button
          size="small"
          variant="outlined"
          disabled={current <= 1}
          onClick={() => onChange(current - 1)}
          sx={{ borderColor: '#C9D2DD', color: '#1F3A5F', fontSize: 13 }}
        >
          上一页
        </Button>
        <Button
          size="small"
          variant="outlined"
          disabled={current >= totalPages}
          onClick={() => onChange(current + 1)}
          sx={{ borderColor: '#C9D2DD', color: '#1F3A5F', fontSize: 13 }}
        >
          下一页
        </Button>
      </Box>
    </Box>
  );
}
