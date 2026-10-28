import React, { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Skeleton from '@mui/material/Skeleton';
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
import Pagination from '../../components/Pagination.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import ConfirmDialog from '../../components/ConfirmDialog.jsx';
import StatusChip from '../../components/StatusChip.jsx';
import { IconRefresh } from '../../components/icons.jsx';
import * as adminApi from '../../api/admin.js';
import useApi from '../../hooks/useApi.js';
import { useToast } from '../../context/ToastContext.jsx';
import { COMMON, EMPTY } from '../../constants/messages.js';
import { countText } from '../../utils/format.js';

/**
 * 商家管理（P1-O-02 / Q2 核验 / C6 高风险标记）。
 * 列表 + 停用启用（连带下架其在架广告）+ 核验标记 + 备注。
 */
export default function AdminMerchantsPage() {
  const { showToast } = useToast();

  const [keyword, setKeyword] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);

  const [statusTarget, setStatusTarget] = useState(null);
  const [statusNote, setStatusNote] = useState('');
  const [noteTarget, setNoteTarget] = useState(null);
  const [noteValue, setNoteValue] = useState('');
  const [busy, setBusy] = useState(false);

  const listApi = useApi(
    () => adminApi.getMerchants({ q: search || undefined, status: status || undefined, page }),
    [search, status, page],
  );

  const payload = listApi.data;
  const items = Array.isArray(payload) ? payload : Array.isArray(payload && payload.items) ? payload.items : [];
  const total = Array.isArray(payload) ? payload.length : Number(payload && payload.total) || items.length;

  const applyStatus = async () => {
    if (!statusTarget) return;
    setBusy(true);
    try {
      const res = await adminApi.setMerchantStatus(statusTarget.id, {
        status: statusTarget.status === 'active' ? 'disabled' : 'active',
        note: statusNote.trim() || undefined,
      });
      const affected = res && res.affected_ads ? res.affected_ads : 0;
      showToast(
        statusTarget.status === 'active'
          ? `已停用该商家，${affected} 条在架广告已下架`
          : '已启用该商家账号',
        'success',
      );
      setStatusTarget(null);
      setStatusNote('');
      listApi.reload();
    } catch (err) {
      showToast(err.message || '操作失败，请稍后重试', 'error');
    } finally {
      setBusy(false);
    }
  };

  const toggleVerify = async (row) => {
    setBusy(true);
    try {
      await adminApi.verifyMerchant(row.id, { verified: !row.verified });
      showToast(row.verified ? '已取消核验标记' : '已标记为已核验', 'success');
      listApi.reload();
    } catch (err) {
      showToast(err.message || '操作失败，请稍后重试', 'error');
    } finally {
      setBusy(false);
    }
  };

  const saveNote = async () => {
    if (!noteTarget) return;
    setBusy(true);
    try {
      await adminApi.patchMerchant(noteTarget.id, { admin_note: noteValue.trim() || null });
      showToast('备注已保存', 'success');
      setNoteTarget(null);
      listApi.reload();
    } catch (err) {
      showToast(err.message || '保存失败，请稍后重试', 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
        <Box>
          <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700 }}>
            商家管理
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mt: 0.5 }}>
            共 {countText(total)} 家 · 「高风险」= 30 天内举报成立 ≥3 次（实时聚合，不落库）
          </Typography>
        </Box>
        <Button size="small" startIcon={<IconRefresh size={15} />} onClick={listApi.reload} sx={{ color: '#5A6472' }}>
          刷新
        </Button>
      </Box>

      <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'center', mb: 2 }}>
        <Box
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            setSearch(keyword.trim());
            setPage(1);
          }}
          sx={{ display: 'flex', gap: 1 }}
        >
          <TextField
            size="small"
            label="搜索商家名 / 手机 / 邮箱"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            sx={{ minWidth: 220 }}
          />
          <Button type="submit" variant="outlined" sx={{ borderColor: '#C9D2DD', color: '#1F3A5F' }}>
            搜索
          </Button>
        </Box>
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
          <MenuItem value="active">正常</MenuItem>
          <MenuItem value="disabled">已停用</MenuItem>
        </TextField>
        {search || status ? (
          <Button
            onClick={() => {
              setSearch('');
              setKeyword('');
              setStatus('');
              setPage(1);
            }}
            sx={{ color: '#5A6472' }}
          >
            {COMMON.clearFilters}
          </Button>
        ) : null}
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
          {listApi.error.message || '商家列表加载失败'}
        </Alert>
      ) : null}

      {listApi.loading && items.length === 0 ? <Skeleton variant="rounded" height={320} /> : null}

      {!listApi.loading && items.length === 0 ? (
        <EmptyState title={EMPTY.adminMerchants.title} description={EMPTY.adminMerchants.desc} />
      ) : null}

      {items.length > 0 ? (
        <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', overflow: 'hidden' }}>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>商家</TableCell>
                  <TableCell>城市</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell align="right">在架</TableCell>
                  <TableCell align="right">累计提交</TableCell>
                  <TableCell align="right">被拒</TableCell>
                  <TableCell align="right">30 天举报成立</TableCell>
                  <TableCell>备注</TableCell>
                  <TableCell align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map((row) => (
                  <TableRow key={row.id} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, flexWrap: 'wrap' }}>
                        <Typography sx={{ fontSize: 13, fontWeight: 600 }}>{row.name}</Typography>
                        {row.verified ? <StatusChip status="active" label="已核验" /> : null}
                        {row.risk_flag ? <StatusChip status="rejected" label="高风险" /> : null}
                      </Box>
                    </TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>{row.city || '—'}</TableCell>
                    <TableCell>
                      <StatusChip status={row.status === 'disabled' ? 'offline' : 'active'} label={row.status === 'disabled' ? '已停用' : '正常'} />
                    </TableCell>
                    <TableCell align="right">{countText(row.active_ads)}</TableCell>
                    <TableCell align="right">{countText(row.total_submitted)}</TableCell>
                    <TableCell align="right">{countText(row.rejected_count)}</TableCell>
                    <TableCell align="right">{countText(row.report_resolved_30d)}</TableCell>
                    <TableCell sx={{ maxWidth: 180 }}>
                      <Typography className="adx-clamp-1" sx={{ fontSize: 12, color: '#5A6472' }}>
                        {row.admin_note || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end', flexWrap: 'nowrap' }}>
                        <Button size="small" onClick={() => toggleVerify(row)} disabled={busy} sx={{ fontSize: 12, minWidth: 0 }}>
                          {row.verified ? '取消核验' : '标记核验'}
                        </Button>
                        <Button
                          size="small"
                          onClick={() => {
                            setNoteTarget(row);
                            setNoteValue(row.admin_note || '');
                          }}
                          sx={{ fontSize: 12, minWidth: 0 }}
                        >
                          备注
                        </Button>
                        <Button
                          size="small"
                          onClick={() => {
                            setStatusTarget(row);
                            setStatusNote('');
                          }}
                          sx={{ fontSize: 12, minWidth: 0, color: row.status === 'active' ? '#B3261E' : '#1E7A46' }}
                        >
                          {row.status === 'active' ? '停用' : '启用'}
                        </Button>
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

      <ConfirmDialog
        open={Boolean(statusTarget)}
        title={statusTarget && statusTarget.status === 'active' ? '停用商家' : '启用商家'}
        description={
          statusTarget && statusTarget.status === 'active'
            ? `停用「${statusTarget.name}」后，该商家全部在架/待生效广告将被下架，且无法登录提交新广告。`
            : `启用「${statusTarget ? statusTarget.name : ''}」后，商家可重新登录提交广告（原已下架广告需整改重提）。`
        }
        confirmText={statusTarget && statusTarget.status === 'active' ? '确认停用' : '确认启用'}
        danger={Boolean(statusTarget && statusTarget.status === 'active')}
        loading={busy}
        onConfirm={applyStatus}
        onClose={() => setStatusTarget(null)}
      />

      <Dialog open={Boolean(noteTarget)} onClose={() => setNoteTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontSize: 17, fontWeight: 700 }}>商家备注</DialogTitle>
        <DialogContent>
          <TextField
            label="内部备注（不对商家展示）"
            value={noteValue}
            onChange={(event) => setNoteValue(event.target.value.slice(0, 200))}
            multiline
            minRows={3}
            fullWidth
            helperText={`${noteValue.length}/200`}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setNoteTarget(null)} color="inherit" sx={{ color: '#5A6472' }}>
            取消
          </Button>
          <Button variant="contained" onClick={saveNote} disabled={busy} sx={{ bgcolor: '#1F3A5F' }}>
            保存
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
