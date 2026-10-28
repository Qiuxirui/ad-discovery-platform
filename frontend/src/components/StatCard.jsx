import React from 'react';
import Box from '@mui/material/Box';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { IconInfo } from './icons.jsx';

/**
 * 指标卡：数字 + 口径说明（tooltip）。
 * 禁止裸「点击率」——必须带分母说明（ARCHITECTURE.md §6.6）。
 *
 * @param {{label:string, value:React.ReactNode, unit?:string, hint?:string, tooltip?:string, tone?:'default'|'primary'|'danger'|'success', footer?:React.ReactNode}} props
 */
export default function StatCard({ label, value, unit, hint, tooltip, tone = 'default', footer }) {
  const valueColor = {
    default: '#1A1A1A',
    primary: '#1F3A5F',
    danger: '#B3261E',
    success: '#1E7A46',
  }[tone];

  return (
    <Box
      sx={{
        bgcolor: '#FFFFFF',
        border: '1px solid #E2E6EC',
        borderRadius: '12px',
        p: { xs: 1.75, sm: 2 },
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 0.5,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <Typography sx={{ fontSize: 13, color: '#5A6472' }}>{label}</Typography>
        {tooltip ? (
          <Tooltip title={tooltip}>
            <Box sx={{ color: '#A7AEB8', display: 'flex', cursor: 'help' }} aria-label={`${label}口径说明`}>
              <IconInfo size={13} />
            </Box>
          </Tooltip>
        ) : null}
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5 }}>
        <Typography sx={{ fontSize: { xs: 22, sm: 26 }, fontWeight: 700, color: valueColor, lineHeight: 1.2 }}>
          {value}
        </Typography>
        {unit ? <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>{unit}</Typography> : null}
      </Box>
      {hint ? <Typography sx={{ fontSize: 12, color: '#8A8F98', lineHeight: 1.5 }}>{hint}</Typography> : null}
      {footer}
    </Box>
  );
}
