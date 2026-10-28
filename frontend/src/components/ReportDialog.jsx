import React, { useEffect, useMemo, useState } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import { createReport } from '../api/reports.js';
import { REPORT_REASONS } from '../constants/reasons.js';
import { REPORT_SLA_TEXT } from '../constants/messages.js';
import { useToast } from '../context/ToastContext.jsx';
import { IconCheckCircle } from './icons.jsx';

const MAX_DETAIL = 200;

/**
 * 举报弹窗：6 项原因单选 + 说明（≤200 字，选填）→ 提交后展示举报码。
 * 同一广告 24h 内重复提交由后端合并并返回已有举报码。
 *
 * @param {{open:boolean, adId:number|string, adTitle?:string, reasons?:Array<{code:string,label:string}>, onClose:()=>void, onSubmitted?:(result:object)=>void}} props
 */
export default function ReportDialog({ open, adId, adTitle, reasons, onClose, onSubmitted }) {
  const { showToast } = useToast();
  const [reasonCode, setReasonCode] = useState('');
  const [detail, setDetail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const reasonList = useMemo(
    () => (Array.isArray(reasons) && reasons.length ? reasons : REPORT_REASONS),
    [reasons],
  );

  useEffect(() => {
    if (!open) return;
    setReasonCode('');
    setDetail('');
    setError('');
    setResult(null);
    setSubmitting(false);
  }, [open, adId]);

  const handleClose = () => {
    if (submitting) return;
    onClose();
  };

  const submit = async () => {
    if (!reasonCode) {
      setError('请选择举报原因');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const res = await createReport({
        ad_id: Number(adId),
        reason_code: reasonCode,
        detail: detail.trim() ? detail.trim() : undefined,
      });
      setResult(res || { code: '', duplicate: false, message: '' });
      showToast((res && res.message) || '已收到，我们会在 48 小时内处理', 'success');
      if (onSubmitted) onSubmitted(res);
    } catch (err) {
      setError(err.message || '提交失败，请稍后重试');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth aria-labelledby="adx-report-title">
      <DialogTitle id="adx-report-title" sx={{ fontSize: 17, fontWeight: 700, pb: 0.5 }}>
        举报这条广告
      </DialogTitle>
      <DialogContent dividers={false} sx={{ pt: 1 }}>
        {result ? (
          <Box sx={{ py: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5, color: '#1E7A46' }}>
              <IconCheckCircle size={20} />
              <Typography sx={{ fontSize: 15, fontWeight: 700 }}>
                {result.duplicate ? '该广告你已举报过，以下是原举报码' : '举报已提交'}
              </Typography>
            </Box>
            <Box
              sx={{
                bgcolor: '#F2F5F9',
                borderRadius: 2,
                px: 2,
                py: 1.5,
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                fontSize: 16,
                letterSpacing: 1,
                fontWeight: 700,
                color: '#1F3A5F',
                mb: 1.5,
              }}
            >
              {result.code || '—'}
            </Box>
            <Typography sx={{ fontSize: 14, color: '#5A6472', lineHeight: 1.7 }}>
              {result.message || REPORT_SLA_TEXT}。可凭此举报码在「举报进度查询」页查看处理结果，我们不会向任何人透露举报人信息。
            </Typography>
          </Box>
        ) : (
          <>
            {adTitle ? (
              <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 1.5, overflowWrap: 'anywhere' }}>
                广告：{adTitle}
              </Typography>
            ) : null}

            <Typography sx={{ fontSize: 14, fontWeight: 700, mb: 0.5 }}>举报原因</Typography>
            <RadioGroup
              value={reasonCode}
              onChange={(event) => {
                setReasonCode(event.target.value);
                setError('');
              }}
            >
              {reasonList.map((item) => (
                <FormControlLabel
                  key={item.code}
                  value={item.code}
                  control={<Radio size="small" />}
                  label={<Box sx={{ fontSize: 14 }}>{item.label}</Box>}
                  sx={{ ml: 0, '& .MuiFormControlLabel-label': { fontSize: 14 } }}
                />
              ))}
            </RadioGroup>

            <TextField
              label="补充说明（选填）"
              value={detail}
              onChange={(event) => setDetail(event.target.value.slice(0, MAX_DETAIL))}
              multiline
              minRows={3}
              fullWidth
              sx={{ mt: 1.5 }}
              placeholder="请描述具体问题，例如价格与描述不一致"
              helperText={`${detail.length}/${MAX_DETAIL}`}
              FormHelperTextProps={{ sx: { textAlign: 'right', mr: 0 } }}
            />

            {error ? (
              <Alert severity="error" sx={{ mt: 1.5 }}>
                {error}
              </Alert>
            ) : (
              <Typography sx={{ fontSize: 12, color: '#8A8F98', mt: 1.5 }}>{REPORT_SLA_TEXT}</Typography>
            )}
          </>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5, gap: 1 }}>
        {result ? (
          <Button variant="contained" onClick={handleClose} sx={{ bgcolor: '#1F3A5F', '&:hover': { bgcolor: '#17304F' } }}>
            知道了
          </Button>
        ) : (
          <>
            <Button onClick={handleClose} color="inherit" disabled={submitting} sx={{ color: '#5A6472' }}>
              取消
            </Button>
            <Button
              variant="contained"
              onClick={submit}
              disabled={submitting || !reasonCode}
              startIcon={submitting ? <CircularProgress size={14} sx={{ color: '#fff' }} /> : null}
              sx={{ bgcolor: '#1F3A5F', '&:hover': { bgcolor: '#17304F' } }}
            >
              {submitting ? '提交中…' : '提交举报'}
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
}
