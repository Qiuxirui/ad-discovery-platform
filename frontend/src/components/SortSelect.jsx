import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import { SORT_OPTIONS } from '../constants/enums.js';
import { IconFilter } from './icons.jsx';

/**
 * 排序选择器：最新发布（默认）/ 即将结束 / 最多收藏。
 * 不存在付费加权排序（PRD §7.1 硬规则）。
 *
 * @param {{value:string, onChange:(sort:string)=>void, options?:Array<{code:string,label:string}>}} props
 */
export default function SortSelect({ value = 'latest', onChange, options }) {
  const list = Array.isArray(options) && options.length ? options : SORT_OPTIONS;

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
      <Box sx={{ color: '#5A6472', display: 'flex' }} aria-hidden="true">
        <IconFilter size={15} />
      </Box>
      <Typography component="span" sx={{ fontSize: 13, color: '#5A6472', whiteSpace: 'nowrap' }}>
        排序
      </Typography>
      <Select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        size="small"
        aria-label="排序方式"
        sx={{
          fontSize: 13,
          height: 34,
          minWidth: 120,
          bgcolor: '#FFFFFF',
          '& .MuiSelect-select': { py: 0.75, fontSize: 13 },
        }}
      >
        {list.map((item) => (
          <MenuItem key={item.code} value={item.code} sx={{ fontSize: 13 }}>
            {item.label}
          </MenuItem>
        ))}
      </Select>
    </Box>
  );
}
