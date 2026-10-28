import React from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';

/**
 * 二次确认弹窗（清除偏好、下架、停用商家等）。
 *
 * @param {{open:boolean, title:string, description?:React.ReactNode, confirmText?:string, cancelText?:string, danger?:boolean, loading?:boolean, onConfirm:()=>void, onClose:()=>void}} props
 */
export default function ConfirmDialog({
  open,
  title,
  description,
  confirmText = '确定',
  cancelText = '取消',
  danger = false,
  loading = false,
  onConfirm,
  onClose,
}) {
  const handleClose = () => {
    if (loading) return;
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth aria-labelledby="adx-confirm-title">
      <DialogTitle id="adx-confirm-title" sx={{ fontSize: 17, fontWeight: 700, pb: 1 }}>
        {title}
      </DialogTitle>
      {description ? (
        <DialogContent sx={{ pt: 0 }}>
          <DialogContentText component="div" sx={{ fontSize: 14, color: '#5A6472', lineHeight: 1.7 }}>
            {description}
          </DialogContentText>
        </DialogContent>
      ) : null}
      <DialogActions sx={{ px: 3, pb: 2.5, gap: 1 }}>
        <Button onClick={handleClose} color="inherit" disabled={loading} sx={{ color: '#5A6472' }}>
          {cancelText}
        </Button>
        <Button
          onClick={onConfirm}
          variant="contained"
          disabled={loading}
          sx={{
            bgcolor: danger ? '#B3261E' : '#1F3A5F',
            '&:hover': { bgcolor: danger ? '#8F1D17' : '#17304F' },
          }}
        >
          {loading ? '处理中…' : confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
