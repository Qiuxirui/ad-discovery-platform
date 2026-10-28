import React from 'react';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';

/**
 * 二级标签横滑单选条（含「全部」）。
 * 选中值变化由父级写入 URL query（?tag=），刷新/前进后退可还原。
 *
 * @param {{tags:Array<{slug:string,name:string}>, value:string, onChange:(slug:string)=>void, allLabel?:string}} props
 */
export default function TagScroll({ tags, value = '', onChange, allLabel = '全部' }) {
  const list = Array.isArray(tags) ? tags : [];
  if (list.length === 0) return null;

  return (
    <Box className="adx-hscroll" role="group" aria-label="二级标签筛选">
      <Chip
        label={allLabel}
        onClick={() => onChange('')}
        variant={value ? 'outlined' : 'filled'}
        sx={{
          flex: '0 0 auto',
          height: 30,
          fontSize: 13,
          fontWeight: 600,
          bgcolor: value ? 'transparent' : '#1F3A5F',
          color: value ? '#5A6472' : '#FFFFFF',
          borderColor: '#DCE3EB',
          '&:hover': { bgcolor: value ? 'rgba(31,58,95,.06)' : '#17304F' },
        }}
      />
      {list.map((tag) => {
        const active = tag.slug === value;
        return (
          <Chip
            key={tag.slug || tag.name}
            label={tag.name}
            onClick={() => onChange(active ? '' : tag.slug)}
            aria-pressed={active}
            sx={{
              flex: '0 0 auto',
              height: 30,
              fontSize: 13,
              fontWeight: 600,
              bgcolor: active ? '#1F3A5F' : '#FFFFFF',
              color: active ? '#FFFFFF' : '#5A6472',
              border: active ? '1px solid #1F3A5F' : '1px solid #DCE3EB',
              '&:hover': { bgcolor: active ? '#17304F' : 'rgba(31,58,95,.06)' },
            }}
          />
        );
      })}
    </Box>
  );
}
