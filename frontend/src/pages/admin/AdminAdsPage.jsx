import React, { useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Skeleton from '@mui/material/Skeleton';
import StatusChip from '../../components/StatusChip.jsx';
import Pagination from '../../components/Pagination.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import { IconRefresh } from '../../components/icons.jsx';
import * as adminApi from '../../api/admin.js';
import useApi from '../../hooks/useApi.js';
import { useToast } from '../../context/ToastContext.jsx';
import { AD_STATUS } from '../../constants/enums.js';
import { COMMON, EMPTY } from '../../constants/messages.js';
import { countText, formatDateTimeCN } from '../../utils/format.js';

/**
 * 广告台账（P0-A-06 / P0-A-07 / PRD 5.3 广告管理）。
 * 状态筛选 + 搜索 + 曝光/点击/举报数 + 下架（必填原因）+ 操作历史 + 整改重提。
 */
export default function AdminAdsPage() {
  const { showToast } = useToast();

  const [status, setStatus] = useState('');
  const [keyword, setKeyword] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const [offlineTarget, setOfflineTarget] = useState(null);
  const [offlineReason, setOfflineReason] = useState('');
  const [busy, setBusy] = useState(false);

  const [historyTarget, setHistoryTarget] = useState(null);

  const listApi = useApi(
    () => adminApi.getAds({ status: status || undefined, q: search || undefined, page }),
    [status, search, page],
  );

  const historyApi = useApi(
    () => adminApi.getAdReviews(historyTarget.id),
    [historyTarget && historyTarget.id],
    { enabled: Boolean(historyTarget) },
  );

  const items = Array.isArray(listApi.data && listApi.data.items) ? listApi.data.items : [];
  const total = Number(listApi.data && listApi.data.total) || items.length;
  const counts = (listApi.data && listApi.data.counts) || {};

  useEffect(() => {
    setOfflineReason('');
  }, [offlineTarget]);

  const doOffline = async () => {
    if (!offlineTarget) return;
    if (!offlineReason.trim()) {
      showToast('请填写下架原因（必填）', 'warning');
      return;
    }
    setBusy(true);
    try {
      await adminApi.offlineAd(offlineTarget.id, { reason: offlineReason.trim() });
      showToast('已下架，用户端立即不可见', 'success');
      setOfflineTarget(null);
      listApi.reload();
    } catch (err) {
      showToast(err.message || '下架失败，请稍后重试', 'error');
    } finally {
      setBusy(false);
    }
  };

  const doRestore = async (row) => {
    setBusy(true);
    try {
      await adminApi.restoreAd(row.id, {});
      showToast('已允许整改重提，广告进入待审核', 'success');
      listApi.reload();
    } catch (err) {
      showToast(err.message || '操作失败，请稍后重试', 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
        <Box>
          <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700 }}>
            广告管理
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mt: 0.5 }}>
            共 {countText(total)} 条 · 下架必须填写原因并写入操作留痕
          </Typography>
        </Box>
        <Button size="small" startIcon={<IconRefresh size={15} />} onClick={listApi.reload} sx={{ color: '#5A6472' }}>
          刷新
        </Button>
      </Box>

      <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'center', mb: 2 }}>
        <TextField
          select
          size="small"
          label="状态"
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setPage(1);
          }}
          sx={{ minWidth: 132 }}
        >
          <MenuItem value="">全部状态</MenuItem>
          {Object.keys(AD_STATUS).map((code) => (
            <MenuItem key={code} value={code}>
              {AD_STATUS[code].label}
              {counts[code] !== undefined ? `（${counts[code]}）` : ''}
            </MenuItem>
          ))}
        </TextField>

        <Box component="form" onSubmit={(event) => { event.preventDefault(); setSearch(keyword.trim()); setPage(1); }} sx={{ display: 'flex', gap: 1 }}>
          <TextField
            size="small"
            label="搜索标题 / 商家"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            sx={{ minWidth: 200 }}
          />
          <Button type="submit" variant="outlined" sx={{ borderColor: '#C9D2DD', color: '#1F3A5F' }}>
            搜索
          </Button>
          {search ? (
            <Button
              onClick={() => {
                setSearch('');
                setKeyword('');
                setPage(1);
              }}
              sx={{ color: '#5A6472' }}
            >
              {COMMON.clearFilters}
            </Button>
          ) : null}
        </Box>
      </Box>

      {listApi.error ? (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={listApi.reload}>
              {COMMON.retry}
            </Button>
          }
        >
          {listApi.error.message || '广告列表加载失败'}
        </Alert>
      ) : null}

      {listApi.loading && items.length === 0 ? <Skeleton variant="rounded" height={320} /> : null}

      {!listApi.loading && items.length === 0 ? (
        <EmptyState
          title={EMPTY.adminAds.title}
          description={EMPTY.adminAds.desc}
          actionText={COMMON.clearAllFilters}
          onAction={() => {
            setStatus('');
            setSearch('');
            setKeyword('');
            setPage(1);
          }}
        />
      ) : null}

      {items.length > 0 ? (
        <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', overflow: 'hidden' }}>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>广告</TableCell>
                  <TableCell>商家</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>有效期至</TableCell>
                  <TableCell align="right">曝光</TableCell>
                  <TableCell align="right">点击</TableCell>
                  <TableCell align="right">举报</TableCell>
                  <TableCell align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map((row) => (
                  <TableRow key={row.id} hover>
                    <TableCell sx={{ maxWidth: 260 }}>
                      <Typography className="adx-clamp-1" sx={{ fontSize: 13, fontWeight: 600 }}>
                        {row.title}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>{row.merchant_name || '—'}</TableCell>
                    <TableCell>
                      <StatusChip status={row.status} />
                    </TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>{row.valid_to_local_date || '—'}</TableCell>
                    <TableCell align="right">{countText(row.impressions)}</TableCell>
                    <TableCell align="right">{countText(row.link_clicks)}</TableCell>
                    <TableCell align="right">{countText(row.reports)}</TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end', flexWrap: 'nowrap' }}>
                        <Button size="small" onClick={() => setHistoryTarget(row)} sx={{ fontSize: 12, minWidth: 0 }}>
                          历史
                        </Button>
                        {row.status === 'active' || row.status === 'scheduled' ? (
                          <Button
                            size="small"
                            onClick={() => setOfflineTarget(row)}
                            sx={{ fontSize: 12, minWidth: 0, color: '#B3261E' }}
                          >
                            下架
                          </Button>
                        ) : null}
                        {row.status === 'offline' ? (
                          <Button size="small" onClick={() => doRestore(row)} disabled={busy} sx={{ fontSize: 12, minWidth: 0 }}>
                            允许重提
                          </Button>
                        ) : null}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <Box sx={{ px: 2 }}>
            <Pagination page={page} total={total} pageSize={24} onChange={setPage} count={items.length} />
          </Box>
        </Box>
      ) : null}

      {/* 下架 */}
      <Dialog open={Boolean(offlineTarget)} onClose={() => setOfflineTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontSize: 17, fontWeight: 700 }}>下架广告</DialogTitle>
        <DialogContent>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 1.5 }}>
            {offlineTarget ? offlineTarget.title : ''}
          </Typography>
          <TextField
            label="下架原因 *"
            value={offlineReason}
            onChange={(event) => setOfflineReason(event.target.value.slice(0, 200))}
            multiline
            minRows={3}
            fullWidth
            helperText="原因必填，会写入操作留痕并回显给商家"
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setOfflineTarget(null)} color="inherit" sx={{ color: '#5A6472' }}>
            取消
          </Button>
          <Button
            variant="contained"
            onClick={doOffline}
            disabled={busy || !offlineReason.trim()}
            sx={{ bgcolor: '#B3261E', '&:hover': { bgcolor: '#8F1D17' } }}
          >
            {busy ? '处理中…' : '确认下架'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 操作历史 */}
      <Dialog open={Boolean(historyTarget)} onClose={() => setHistoryTarget(null)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontSize: 17, fontWeight: 700 }}>
          操作历史{historyTarget ? `：${historyTarget.title}` : ''}
        </DialogTitle>
        <DialogContent>
          {historyApi.error ? <Alert severity="error">{historyApi.error.message}</Alert> : null}
          {historyApi.loading ? <Skeleton height={80} /> : null}
          {!historyApi.loading && Array.isArray(historyApi.data && historyApi.data.items) && historyApi.data.items.length === 0 ? (
            <Typography sx={{ fontSize: 13, color: '#8A8F98' }}>暂无操作记录</Typography>
          ) : null}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
            {(historyApi.data && historyApi.data.items ? historyApi.data.items : []).map((entry, index) => (
              <Box key={`${entry.created_at}-${index}`} sx={{ borderLeft: '2px solid #E2E6EC', pl: 1.5, py: 0.25 }}>
                <Typography sx={{ fontSize: 13, fontWeight: 700 }}>
                  {entry.action_label || entry.action}
                  <Box component="span" sx={{ ml: 1, fontSize: 12, fontWeight: 400, color: '#8A8F98' }}>
                    {entry.actor_type === 'system' ? '系统' : entry.actor_name || entry.actor_type || '—'}
                  </Box>
                </Typography>
                <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>{formatDateTimeCN(entry.created_at)}</Typography>
                {entry.reason ? (
                  <Typography sx={{ fontSize: 12, color: '#5A6472', mt: 0.25 }}>原因：{entry.reason}</Typography>
                ) : null}
                {entry.changes ? (
                  <Typography sx={{ fontSize: 12, color: '#5A6472', mt: 0.25, overflowWrap: 'anywhere' }}>
                    变更：{typeof entry.changes === 'string' ? entry.changes : JSON.stringify(entry.changes)}
                  </Typography>
                ) : null}
              </Box>
            ))}
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setHistoryTarget(null)} sx={{ color: '#1F3A5F' }}>
            关闭
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
