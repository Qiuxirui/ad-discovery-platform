import React from 'react';
import Box from '@mui/material/Box';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import { CITIES } from '../constants/cities.js';
import { ENDING_OPTIONS, PROMO_OPTIONS } from '../constants/enums.js';
import { COMMON } from '../constants/messages.js';
import { hasActiveFilters } from '../utils/url.js';

/**
 * 筛选条：城市 + 有效期 + 是否有优惠 + 清除全部筛选。
 * 任何筛选都写入 URL query，结果为空时也保留「清除全部筛选」。
 *
 * @param {{state:{city:string,ending:string,promo:string,tag?:string,sort?:string,q?:string}, onChange:(patch:object)=>void, onReset:()=>void, cities?:string[], categoryOptions?:Array<{slug:string,name:string}>}} props
 */
export default function FilterBar({ state, onChange, onReset, cities, categoryOptions }) {
  const cityList = Array.isArray(cities) && cities.length ? cities : CITIES;
  const active = hasActiveFilters(state);

  const selectSx = {
    fontSize: 13,
    height: 34,
    bgcolor: '#FFFFFF',
    '& .MuiSelect-select': { py: 0.75, fontSize: 13 },
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: { xs: 1, sm: 1.25 },
        py: 1.25,
      }}
    >
      {Array.isArray(categoryOptions) && categoryOptions.length > 0 ? (
        <Select
          value={state.category || ''}
          onChange={(event) => onChange({ category: event.target.value, tag: '' })}
          displayEmpty
          size="small"
          aria-label="一级类别"
          sx={{ ...selectSx, minWidth: 132 }}
        >
          <MenuItem value="" sx={{ fontSize: 13 }}>
            全部类别
          </MenuItem>
          {categoryOptions.map((item) => (
            <MenuItem key={item.slug} value={item.slug} sx={{ fontSize: 13 }}>
              {item.name}
            </MenuItem>
          ))}
        </Select>
      ) : null}

      <Select
        value={state.city || ''}
        onChange={(event) => onChange({ city: event.target.value })}
        displayEmpty
        size="small"
        aria-label="服务城市"
        sx={{ ...selectSx, minWidth: 118 }}
      >
        <MenuItem value="" sx={{ fontSize: 13 }}>
          全部城市
        </MenuItem>
        {cityList.map((city) => (
          <MenuItem key={city} value={city} sx={{ fontSize: 13 }}>
            {city}
          </MenuItem>
        ))}
      </Select>

      <Select
        value={state.ending || ''}
        onChange={(event) => onChange({ ending: event.target.value })}
        displayEmpty
        size="small"
        aria-label="有效期筛选"
        sx={{ ...selectSx, minWidth: 132 }}
      >
        {ENDING_OPTIONS.map((item) => (
          <MenuItem key={item.code || 'all'} value={item.code} sx={{ fontSize: 13 }}>
            {item.code ? item.label : '不限有效期'}
          </MenuItem>
        ))}
      </Select>

      <Select
        value={state.promo || ''}
        onChange={(event) => onChange({ promo: event.target.value })}
        displayEmpty
        size="small"
        aria-label="优惠筛选"
        sx={{ ...selectSx, minWidth: 118 }}
      >
        {PROMO_OPTIONS.map((item) => (
          <MenuItem key={item.code || 'all'} value={item.code} sx={{ fontSize: 13 }}>
            {item.code ? item.label : '不限优惠'}
          </MenuItem>
        ))}
      </Select>

      {active ? (
        <Button size="small" onClick={onReset} sx={{ fontSize: 13, color: '#1F3A5F', minWidth: 0 }}>
          {COMMON.clearAllFilters}
        </Button>
      ) : (
        <Typography sx={{ fontSize: 12, color: '#A7AEB8' }}>未设置筛选</Typography>
      )}
    </Box>
  );
}
