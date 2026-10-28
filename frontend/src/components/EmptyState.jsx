import React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import { IconSearch } from './icons.jsx';

/**
 * 统一空态：标题 + 说明 + 主操作 + 推荐类别入口。
 * 文案来自 constants/messages.js（逐字对齐 PRD §5.1 空状态列）。
 *
 * @param {{title:string, description?:string, actionText?:string, onAction?:()=>void, suggestions?:Array<{label:string, onClick:()=>void}>, icon?:React.ReactNode, compact?:boolean}} props
 */
export default function EmptyState({
  title,
  description,
  actionText,
  onAction,
  suggestions,
  icon,
  compact = false,
}) {
  const hasSuggestions = Array.isArray(suggestions) && suggestions.length > 0;

  return (
    <Box
      role="status"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        gap: 1.25,
        py: compact ? 4 : { xs: 5, sm: 7 },
        px: 2,
        bgcolor: '#FFFFFF',
        border: '1px dashed #DCE3EB',
        borderRadius: '12px',
      }}
    >
      <Box sx={{ color: '#B9C2CD', mb: 0.5 }} aria-hidden="true">
        {icon || <IconSearch size={34} />}
      </Box>
      <Typography sx={{ fontSize: 16, fontWeight: 700, color: '#33404F' }}>{title}</Typography>
      {description ? (
        <Typography sx={{ fontSize: 14, color: '#5A6472', maxWidth: 520, lineHeight: 1.7 }}>
          {description}
        </Typography>
      ) : null}
      {actionText && onAction ? (
        <Button variant="contained" onClick={onAction} sx={{ mt: 1, bgcolor: '#1F3A5F', '&:hover': { bgcolor: '#17304F' } }}>
          {actionText}
        </Button>
      ) : null}
      {hasSuggestions ? (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center', mt: 1 }}>
          {suggestions.map((item) => (
            <Button
              key={item.label}
              variant="outlined"
              size="small"
              onClick={item.onClick}
              sx={{ borderColor: '#C9D2DD', color: '#1F3A5F', fontSize: 13 }}
            >
              {item.label}
            </Button>
          ))}
        </Box>
      ) : null}
    </Box>
  );
}
