import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import InputBase from '@mui/material/InputBase';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import StatusChip from '../components/StatusChip.jsx';
import EmptyState from '../components/EmptyState.jsx';
import { IconReport, IconSearch } from '../components/icons.jsx';
import { followupReport, getMyReports, lookupReport } from '../api/reports.js';
import useApi from '../hooks/useApi.js';
import { useToast } from '../context/ToastContext.jsx';
import { reportStatusText } from '../constants/enums.js';
import { COMMON, EMPTY, REPORT_SLA_TEXT } from '../constants/messages.js';
import { formatDateTimeCN } from '../utils/format.js';

const TERMINAL = ['resolved', 'dismissed'];

/** 单条举报结果卡片 */
function ReportCard({ report, onFollowup }) {
  const terminal = TERMINAL.includes(report.status);
  return (
    <Box sx={{ border: '1px solid #E2E6EC', borderRadius: '12px', bgcolor: '#FFFFFF', p: { xs: 1.75, sm: 2 } }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 0.75 }}>
        <Typography sx={{ fontSize: 14, fontWeight: 700, letterSpacing: 0.5 }}>{report.code || '—'}</Typography>
        <StatusChip status={report.status} kind="report" />
        {report.overdue ? <StatusChip status="pending" label="已超时" /> : null}
      </Box>
      <Typography className="adx-clamp-2" sx={{ fontSize: 14, color: '#1A1A1A' }}>
        {report.ad_title || '广告信息已不可用'}
      </Typography>
      {report.reason_label ? (
        <Typography sx={{ fontSize: 12, color: '#5A6472', mt: 0.5 }}>举报原因：{report.reason_label}</Typography>
      ) : null}
      <Typography sx={{ fontSize: 13, color: '#1F3A5F', mt: 1, bgcolor: '#F2F5F9', borderRadius: 1.5, px: 1.25, py: 0.75 }}>
        {report.status_text || reportStatusText(report.status)}
      </Typography>
      {report.conclusion ? (
        <Typography sx={{ fontSize: 13, color: '#33404F', mt: 1, lineHeight: 1.7 }}>
          处理结论：{report.conclusion}
        </Typography>
      ) : null}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1, flexWrap: 'wrap', gap: 1 }}>
        <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>
          提交时间：{formatDateTimeCN(report.created_at)}
          {report.handled_at ? ` · 处理时间：${formatDateTimeCN(report.handled_at)}` : ''}
        </Typography>
        {terminal && onFollowup ? (
          <Button size="small" onClick={() => onFollowup(report)} sx={{ fontSize: 12, color: '#1F3A5F' }}>
            仍有疑问
          </Button>
        ) : null}
      </Box>
    </Box>
  );
}

/**
 * 举报进度查询（P0-U-04 / P0-U-05）。
 * 支持输入举报码查询 + 自动列出本设备提交的举报；只展示状态与结论，不泄露处理人信息。
 */
export default function ReportStatusPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [code, setCode] = useState('');
  const [queryCode, setQueryCode] = useState('');
  const [result, setResult] = useState(null);
  const [queryError, setQueryError] = useState('');
  const [querying, setQuerying] = useState(false);

  const [followupTarget, setFollowupTarget] = useState(null);
  const [note, setNote] = useState('');
  const [submittingFollowup, setSubmittingFollowup] = useState(false);

  const mine = useApi(() => getMyReports(), []);

  useEffect(() => {
    // 举报码形如 RP-XXXXXXXX，统一大写、去空格
    setCode((value) => value.toUpperCase().replace(/\s/g, ''));
  }, []);

  const submitQuery = async (event) => {
    event.preventDefault();
    const value = code.trim().toUpperCase();
    if (!value) {
      setQueryError('请输入举报码');
      return;
    }
    setQuerying(true);
    setQueryError('');
    setResult(null);
    setQueryCode(value);
    try {
      const data = await lookupReport(value);
      setResult(data);
    } catch (err) {
      setQueryError(err.message || '未找到该举报码对应的记录');
    } finally {
      setQuerying(false);
    }
  };

  const openFollowup = (report) => {
    setFollowupTarget(report);
    setNote('');
  };

  const submitFollowup = async () => {
    if (!followupTarget) return;
    if (!note.trim()) {
      showToast('请填写你的疑问说明', 'warning');
      return;
    }
    setSubmittingFollowup(true);
    try {
      await followupReport(followupTarget.code, note.trim().slice(0, 200));
      showToast('已收到你的补充说明，运营会再次核查', 'success');
      setFollowupTarget(null);
      setNote('');
      mine.reload();
    } catch (err) {
      showToast(err.message || '提交失败，请稍后重试', 'error');
    } finally {
      setSubmittingFollowup(false);
    }
  };

  const myReports = Array.isArray(mine.data && mine.data.items) ? mine.data.items : [];

  return (
    <Box sx={{ maxWidth: 780, mx: 'auto' }}>
      <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700, mb: 0.5 }}>
        举报进度查询
      </Typography>
      <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 2.5, lineHeight: 1.7 }}>
        凭举报码查询处理状态，或查看本设备提交过的举报。{REPORT_SLA_TEXT}。查询结果不含举报人与处理人的任何信息。
      </Typography>

      <Box
        component="form"
        onSubmit={submitQuery}
        sx={{
          display: 'flex',
          gap: 1,
          alignItems: 'center',
          flexWrap: 'wrap',
          bgcolor: '#FFFFFF',
          border: '1px solid #E2E6EC',
          borderRadius: '12px',
          p: { xs: 1.5, sm: 2 },
          mb: 2,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            flex: '1 1 240px',
            minWidth: 220,
            px: 1.25,
            height: 40,
            border: '1px solid #DCE3EB',
            borderRadius: 2,
            bgcolor: '#F7F8FA',
            '&:focus-within': { borderColor: '#1F3A5F', bgcolor: '#fff' },
          }}
        >
          <Box sx={{ color: '#5A6472', display: 'flex' }} aria-hidden="true">
            <IconSearch size={17} />
          </Box>
          <InputBase
            value={code}
            onChange={(event) => setCode(event.target.value.toUpperCase().slice(0, 11))}
            placeholder="RP-XXXXXXXX"
            inputProps={{ 'aria-label': '举报码', maxLength: 11 }}
            sx={{ flex: 1, fontSize: 14, letterSpacing: 0.5 }}
          />
        </Box>
        <Button type="submit" variant="contained" disabled={querying} sx={{ bgcolor: '#1F3A5F', minWidth: 96, height: 40 }}>
          {querying ? '查询中…' : '查询'}
        </Button>
      </Box>

      {queryError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {queryError}
        </Alert>
      ) : null}

      {result ? (
        <Box sx={{ mb: 3 }}>
          <Typography component="h2" sx={{ fontSize: 16, fontWeight: 700, mb: 1 }}>
            查询结果（{queryCode}）
          </Typography>
          <ReportCard report={result} onFollowup={openFollowup} />
        </Box>
      ) : null}

      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.25 }}>
          <Typography component="h2" sx={{ fontSize: 16, fontWeight: 700 }}>
            本设备提交的举报
          </Typography>
          <Button size="small" onClick={mine.reload} sx={{ fontSize: 12, color: '#1F3A5F' }}>
            刷新
          </Button>
        </Box>

        {mine.error ? (
          <Alert
            severity="error"
            action={
              <Button color="inherit" size="small" onClick={mine.reload}>
                {COMMON.retry}
              </Button>
            }
          >
            {mine.error.message || '举报列表加载失败'}
          </Alert>
        ) : null}

        {!mine.loading && myReports.length === 0 ? (
          <EmptyState
            title={EMPTY.reportStatus.title}
            description={EMPTY.reportStatus.desc}
            actionText="去浏览广告"
            onAction={() => navigate('/')}
            icon={<IconReport size={34} />}
          />
        ) : null}

        {myReports.length > 0 ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
            {myReports.map((report) => (
              <ReportCard key={report.code} report={report} onFollowup={openFollowup} />
            ))}
          </Box>
        ) : null}
      </Box>

      <Dialog open={Boolean(followupTarget)} onClose={() => setFollowupTarget(null)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontSize: 17, fontWeight: 700 }}>仍有疑问</DialogTitle>
        <DialogContent>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 1.5, lineHeight: 1.7 }}>
            补充说明会在处理结束后 7 天内受理，追加说明不会改变当前状态，运营会再次核查。
          </Typography>
          <TextField
            value={note}
            onChange={(event) => setNote(event.target.value.slice(0, 200))}
            multiline
            minRows={3}
            fullWidth
            label="补充说明"
            helperText={`${note.length}/200`}
            FormHelperTextProps={{ sx: { textAlign: 'right', mr: 0 } }}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setFollowupTarget(null)} color="inherit" sx={{ color: '#5A6472' }}>
            取消
          </Button>
          <Button
            variant="contained"
            onClick={submitFollowup}
            disabled={submittingFollowup}
            sx={{ bgcolor: '#1F3A5F', '&:hover': { bgcolor: '#17304F' } }}
          >
            {submittingFollowup ? '提交中…' : '提交说明'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
