import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Skeleton from '@mui/material/Skeleton';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import StatusChip from '../../components/StatusChip.jsx';
import Pagination from '../../components/Pagination.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import StatCard from '../../components/StatCard.jsx';
import { IconRefresh } from '../../components/icons.jsx';
import * as adminApi from '../../api/admin.js';
import useApi from '../../hooks/useApi.js';
import { useToast } from '../../context/ToastContext.jsx';
import { REPORT_STATUS_TABS } from '../../constants/enums.js';
import { COMMON, EMPTY } from '../../constants/messages.js';
import { countText, formatDateTimeCN } from '../../utils/format.js';

/**
 * 举报行里的广告快照解析。
 *
 * 后端 `AdminReportRowOut.ad_snapshot` 是 **dict**（`services/reports.py::_snapshot` 落库的 JSON），
 * 形如 `{ ad_id, title, merchant_name, status, image_path }`，**不是字符串**；
 * 所以不能像以前那样直接 `{row.ad_snapshot || ...}` 渲染进 JSX（React 渲染对象会直接抛错）。
 * 这里统一收敛成纯字符串字段，同时兼容后端将来返回字符串或 null 的情况。
 *
 * @param {object} row 举报行
 * @returns {{title: string, merchantName: string, adId: number|null}}
 */
function snapshotOf(row) {
  const raw = row && row.ad_snapshot;
  const snapshot = raw && typeof raw === 'object' && !Array.isArray(raw) ? raw : null;
  const titleFromRow = typeof (row && row.ad_title) === 'string' ? row.ad_title.trim() : '';
  const titleFromSnapshot = snapshot && typeof snapshot.title === 'string' ? snapshot.title.trim() : '';
  const legacyString = typeof raw === 'string' ? raw.trim() : '';
  const merchantName = snapshot && typeof snapshot.merchant_name === 'string' ? snapshot.merchant_name.trim() : '';
  const adId = (row && row.ad_id) || (snapshot && snapshot.ad_id) || null;
  return {
    title: titleFromRow || titleFromSnapshot || legacyString || '广告信息已不可用',
    merchantName,
    adId,
  };
}

/**
 * 举报处理（P1-O-03 / PRD 5.3 举报处理）。
 * 状态页签 + 超时高亮 + 开始处理 / 成立（下架或整改）/ 驳回（必填结论）。
 */
export default function AdminReportsPage() {
  const { showToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const [tab, setTab] = useState('pending');
  // 运营首页「超时举报」快捷入口 跳 /admin/reports?overdue=1，这里认这个参数，
  // 避免落地后还要人工再点一次「仅看超时」。
  const [overdueOnly, setOverdueOnly] = useState(() => searchParams.get('overdue') === '1');
  const [page, setPage] = useState(1);
  const [busyId, setBusyId] = useState(null);

  const [resolveTarget, setResolveTarget] = useState(null);
  const [resolveForm, setResolveForm] = useState({ action: 'offline', note: '' });
  const [dismissTarget, setDismissTarget] = useState(null);
  const [dismissNote, setDismissNote] = useState('');
  const [dialogError, setDialogError] = useState('');

  /** 切换「仅看超时」：状态与 URL 双向保持一致（?overdue=1）。 */
  const toggleOverdue = () => {
    const next = !overdueOnly;
    setOverdueOnly(next);
    setPage(1);
    const params = new URLSearchParams(searchParams);
    if (next) {
      params.set('overdue', '1');
    } else {
      params.delete('overdue');
    }
    setSearchParams(params, { replace: true });
  };

  const listApi = useApi(
    () =>
      adminApi.getReports({
        status: tab === 'all' ? undefined : tab,
        overdue: overdueOnly ? 1 : undefined,
        page,
      }),
    [tab, overdueOnly, page],
  );

  const items = Array.isArray(listApi.data && listApi.data.items) ? listApi.data.items : [];
  const total = Number(listApi.data && listApi.data.total) || items.length;
  const weekStats = (listApi.data && listApi.data.week_stats) || {};

  useEffect(() => {
    setDialogError('');
  }, [resolveTarget, dismissTarget]);

  const startHandling = async (row) => {
    setBusyId(row.id);
    try {
      await adminApi.startReport(row.id);
      showToast('已标记为处理中', 'success');
      listApi.reload();
    } catch (err) {
      showToast(err.message || '操作失败，请稍后重试', 'error');
    } finally {
      setBusyId(null);
    }
  };

  const submitResolve = async () => {
    if (!resolveTarget) return;
    if (!resolveForm.note.trim()) {
      setDialogError('请填写处理结论（必填）');
      return;
    }
    setBusyId(resolveTarget.id);
    try {
      await adminApi.resolveReport(resolveTarget.id, {
        action: resolveForm.action,
        note: resolveForm.note.trim(),
      });
      showToast(
        resolveForm.action === 'offline' ? '举报成立，广告已下架' : '举报成立，已要求商家整改',
        'success',
      );
      setResolveTarget(null);
      setResolveForm({ action: 'offline', note: '' });
      listApi.reload();
    } catch (err) {
      setDialogError(err.message || '操作失败，请稍后重试');
    } finally {
      setBusyId(null);
    }
  };

  const submitDismiss = async () => {
    if (!dismissTarget) return;
    if (!dismissNote.trim()) {
      setDialogError('请填写驳回结论（必填）');
      return;
    }
    setBusyId(dismissTarget.id);
    try {
      await adminApi.dismissReport(dismissTarget.id, { note: dismissNote.trim() });
      showToast('举报已驳回，结论会回显给举报人', 'success');
      setDismissTarget(null);
      setDismissNote('');
      listApi.reload();
    } catch (err) {
      setDialogError(err.message || '操作失败，请稍后重试');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
        <Box>
          <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700 }}>
            举报处理
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mt: 0.5 }}>
            共 {countText(total)} 条 · 承诺 48 小时内首次响应，超 24 小时未处理会高亮
          </Typography>
        </Box>
        <Button size="small" startIcon={<IconRefresh size={15} />} onClick={listApi.reload} sx={{ color: '#5A6472' }}>
          刷新
        </Button>
      </Box>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', md: 'repeat(4, minmax(0, 1fr))' },
          gap: 1.5,
          mb: 2,
        }}
      >
        <StatCard label="近 7 天收到" value={countText(weekStats.received)} unit="条" />
        <StatCard label="近 7 天成立" value={countText(weekStats.resolved)} unit="条" tone="success" />
        <StatCard label="近 7 天驳回" value={countText(weekStats.dismissed)} unit="条" />
        <StatCard
          label="平均处理时长"
          value={weekStats.avg_hours === undefined || weekStats.avg_hours === null ? '—' : Number(weekStats.avg_hours).toFixed(1)}
          unit="小时"
          tooltip="从提交到下结论的平均小时数，只统计终态举报。"
        />
      </Box>

      <Box sx={{ borderBottom: '1px solid #E2E6EC', mb: 1.5, display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Tabs
          value={tab}
          onChange={(_, value) => {
            setTab(value);
            setPage(1);
          }}
          variant="scrollable"
          scrollButtons="auto"
          aria-label="举报状态筛选"
        >
          {REPORT_STATUS_TABS.map((item) => (
            <Tab key={item.code} value={item.code} label={item.label} />
          ))}
        </Tabs>
        <Button
          size="small"
          variant={overdueOnly ? 'contained' : 'outlined'}
          onClick={toggleOverdue}
          sx={{
            borderColor: '#C9D2DD',
            bgcolor: overdueOnly ? '#E8590C' : 'transparent',
            color: overdueOnly ? '#fff' : '#5A6472',
            '&:hover': { bgcolor: overdueOnly ? '#C94E0A' : 'rgba(31,58,95,.04)' },
          }}
        >
          仅看超时（&gt;24h）
        </Button>
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
          {listApi.error.message || '举报列表加载失败'}
        </Alert>
      ) : null}

      {listApi.loading && items.length === 0 ? <Skeleton variant="rounded" height={320} /> : null}

      {!listApi.loading && items.length === 0 ? (
        <EmptyState title={EMPTY.adminReports.title} description="近 7 天处理情况见上方统计。" />
      ) : null}

      {items.length > 0 ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
          {items.map((row) => {
            const snapshot = snapshotOf(row);
            return (
            <Box
              key={row.id}
              sx={{
                bgcolor: '#FFFFFF',
                border: '1px solid #E2E6EC',
                borderLeft: row.overdue ? '4px solid #E8590C' : '1px solid #E2E6EC',
                borderRadius: '12px',
                p: { xs: 1.75, sm: 2 },
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 0.75 }}>
                <Typography sx={{ fontSize: 13, fontWeight: 700, letterSpacing: 0.5 }}>{row.code}</Typography>
                <StatusChip status={row.status} kind="report" />
                {row.overdue ? <StatusChip status="pending" label="已超时" /> : null}
                <Typography sx={{ fontSize: 12, color: '#8A8F98', ml: 'auto' }}>
                  提交：{formatDateTimeCN(row.created_at)}
                  {row.handled_at ? ` · 处理：${formatDateTimeCN(row.handled_at)}` : ''}
                </Typography>
              </Box>

              <Typography sx={{ fontSize: 14, fontWeight: 600 }}>
                {row.reason_label || '举报原因未提供'}
              </Typography>
              <Typography sx={{ fontSize: 13, color: '#33404F', mt: 0.5, lineHeight: 1.7, overflowWrap: 'anywhere' }}>
                {row.detail || '（无补充说明）'}
              </Typography>

              <Box sx={{ mt: 1, bgcolor: '#F7F8FA', border: '1px solid #EEF1F5', borderRadius: 1.5, px: 1.25, py: 1 }}>
                <Typography sx={{ fontSize: 12, color: '#5A6472', mb: 0.25 }}>广告快照</Typography>
                <Typography className="adx-clamp-2" sx={{ fontSize: 13 }}>
                  {snapshot.title}
                </Typography>
                <Typography sx={{ fontSize: 12, color: '#8A8F98', mt: 0.25 }}>
                  {snapshot.merchantName ? `商家：${snapshot.merchantName} · ` : ''}
                  广告 ID：{snapshot.adId || '未知'}
                </Typography>
              </Box>

              {Array.isArray(row.followups) && row.followups.length > 0 ? (
                <Box sx={{ mt: 1, border: '1px solid #EEF1F5', borderRadius: 1.5, px: 1.25, py: 1 }}>
                  <Typography sx={{ fontSize: 12, color: '#5A6472', mb: 0.5 }}>
                    用户追评（{row.followups.length}）
                  </Typography>
                  {row.followups.map((followup, index) => (
                    <Typography
                      key={`${followup.created_at}-${index}`}
                      sx={{ fontSize: 12, color: '#33404F', lineHeight: 1.8, overflowWrap: 'anywhere' }}
                    >
                      {formatDateTimeCN(followup.created_at)}：{followup.note}
                    </Typography>
                  ))}
                </Box>
              ) : null}

              {row.admin_note ? (
                <Typography sx={{ fontSize: 12, color: '#5A6472', mt: 1 }}>处理结论：{row.admin_note}</Typography>
              ) : null}

              <Box sx={{ display: 'flex', gap: 1, mt: 1.25, flexWrap: 'wrap' }}>
                {row.status === 'pending' ? (
                  <Button
                    size="small"
                    variant="outlined"
                    disabled={busyId === row.id}
                    onClick={() => startHandling(row)}
                    sx={{ borderColor: '#C9D2DD', color: '#1F3A5F', fontSize: 13 }}
                  >
                    开始处理
                  </Button>
                ) : null}
                {row.status === 'pending' || row.status === 'reviewing' ? (
                  <>
                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => setResolveTarget(row)}
                      sx={{ bgcolor: '#1E7A46', '&:hover': { bgcolor: '#176336' }, fontSize: 13 }}
                    >
                      成立（下架 / 整改）
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => setDismissTarget(row)}
                      sx={{ borderColor: '#C9D2DD', color: '#5A6472', fontSize: 13 }}
                    >
                      驳回
                    </Button>
                  </>
                ) : (
                  <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>已进入终态，不可再变更</Typography>
                )}
              </Box>
            </Box>
            );
          })}
          <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', px: 1.5 }}>
            <Pagination page={page} total={total} pageSize={24} onChange={setPage} count={items.length} />
          </Box>
        </Box>
      ) : null}

      {/* 成立 */}
      <Dialog open={Boolean(resolveTarget)} onClose={() => setResolveTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontSize: 17, fontWeight: 700 }}>举报成立</DialogTitle>
        <DialogContent>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 1.5 }}>
            成立后广告将立即下架或要求整改，举报人可见结论文案。
          </Typography>
          {dialogError ? (
            <Alert severity="error" sx={{ mb: 1.5 }}>
              {dialogError}
            </Alert>
          ) : null}
          <TextField
            select
            label="处理方式"
            value={resolveForm.action}
            onChange={(event) => setResolveForm((prev) => ({ ...prev, action: event.target.value }))}
            fullWidth
            sx={{ mb: 2 }}
          >
            <MenuItem value="offline">直接下架（offline）</MenuItem>
            <MenuItem value="rectify">要求整改（保留广告）</MenuItem>
          </TextField>
          <TextField
            label="处理结论 *"
            value={resolveForm.note}
            onChange={(event) => setResolveForm((prev) => ({ ...prev, note: event.target.value.slice(0, 200) }))}
            multiline
            minRows={3}
            fullWidth
            helperText={`${resolveForm.note.length}/200`}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setResolveTarget(null)} color="inherit" sx={{ color: '#5A6472' }}>
            取消
          </Button>
          <Button
            variant="contained"
            onClick={submitResolve}
            disabled={busyId === (resolveTarget && resolveTarget.id)}
            sx={{ bgcolor: '#1E7A46' }}
          >
            确认成立
          </Button>
        </DialogActions>
      </Dialog>

      {/* 驳回 */}
      <Dialog open={Boolean(dismissTarget)} onClose={() => setDismissTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontSize: 17, fontWeight: 700 }}>驳回举报</DialogTitle>
        <DialogContent>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 1.5 }}>
            驳回后广告状态不变，举报人会看到「经核查，暂未发现违反平台规则的情况」。
          </Typography>
          {dialogError ? (
            <Alert severity="error" sx={{ mb: 1.5 }}>
              {dialogError}
            </Alert>
          ) : null}
          <TextField
            label="驳回结论 *"
            value={dismissNote}
            onChange={(event) => setDismissNote(event.target.value.slice(0, 200))}
            multiline
            minRows={3}
            fullWidth
            helperText={`${dismissNote.length}/200`}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setDismissTarget(null)} color="inherit" sx={{ color: '#5A6472' }}>
            取消
          </Button>
          <Button
            variant="contained"
            onClick={submitDismiss}
            disabled={busyId === (dismissTarget && dismissTarget.id)}
            sx={{ bgcolor: '#1F3A5F' }}
          >
            确认驳回
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
