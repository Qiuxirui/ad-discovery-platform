import React, { useEffect, useMemo, useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Skeleton from '@mui/material/Skeleton';
import CircularProgress from '@mui/material/CircularProgress';
import AdBadge from '../../components/AdBadge.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import StatusChip from '../../components/StatusChip.jsx';
import Pagination from '../../components/Pagination.jsx';
import { IconCheck, IconExternal, IconShield, IconWarn } from '../../components/icons.jsx';
import * as adminApi from '../../api/admin.js';
import useApi from '../../hooks/useApi.js';
import { useToast } from '../../context/ToastContext.jsx';
import { useCategories } from '../../context/CategoriesContext.jsx';
import { REJECT_REASONS } from '../../constants/reasons.js';
import { precheckCodeLabel } from '../../constants/enums.js';
import { COMMON, EMPTY } from '../../constants/messages.js';
import { formatDateTimeCN, formatMonthCN, formatRangeCN, waitMinutesText } from '../../utils/format.js';

/** 详情行 */
function Field({ label, children }) {
  return (
    <Box sx={{ display: 'flex', gap: 1.5, py: 0.5 }}>
      <Typography sx={{ fontSize: 12, color: '#5A6472', width: 64, flex: '0 0 auto', lineHeight: 1.8 }}>{label}</Typography>
      <Box sx={{ fontSize: 13, color: '#1A1A1A', flex: 1, minWidth: 0, overflowWrap: 'anywhere', lineHeight: 1.8 }}>
        {children}
      </Box>
    </Box>
  );
}

/**
 * 后端 GET /api/admin/review-queue 返回**嵌套结构**（ARCHITECTURE.md §5.7）：
 *   { items: [{
 *       ad: {...广告全字段},
 *       merchant: {...},
 *       precheck: '预检通过：无禁投词，落地页安全',   // 提交时留痕（字符串）
 *       precheck_passed: true,                      // 读取队列时实时复检
 *       precheck_code: 'PRECHECK_PASSED',
 *       precheck_reason: '',                        // 失败原因原句
 *       waiting_minutes, submitted_at,
 *     }], total }
 * 这里把每个队列条目统一拍平成「广告全字段 + precheck* / merchant / waiting_minutes / submitted_at」，
 * 页面其余部分只消费拍平后的对象，避免到处写 item.ad.xxx。
 * 同时兼容后端若改成扁平结构（广告字段直接在顶层）的情况，两种都能跑。
 *
 * @param {object} item 队列条目（后端嵌套结构）
 * @returns {object|null} 拍平后的广告视图模型
 */
function normalizeQueueItem(item) {
  if (!item || typeof item !== 'object') return null;
  const ad = item.ad && typeof item.ad === 'object' ? item.ad : null;
  const base = ad || item;
  const pick = (key) => (item[key] !== undefined ? item[key] : base[key]);
  const merchant = pick('merchant') || null;
  return {
    ...base,
    // 广告主键必须落在顶层，否则「通过/拒绝」会请求 /api/admin/ads/undefined/...
    id: base.id !== undefined ? base.id : item.ad_id,
    precheck: pick('precheck'),
    // 读取队列时的实时复检结论（后端 2026-10 新增，老后端没有则为 undefined）
    precheck_passed: pick('precheck_passed'),
    precheck_code: pick('precheck_code'),
    precheck_reason: pick('precheck_reason'),
    merchant,
    waiting_minutes: pick('waiting_minutes'),
    submitted_at: pick('submitted_at'),
    merchant_name: base.merchant_name || (merchant && merchant.name) || '',
  };
}

/**
 * 审核队列（P0-A-02 ~ P0-A-05）。
 * 左列表 + 右详情（全字段 + 预检结果 + 商家历史 + 落地页新窗口打开）+ 通过 / 拒绝（原因必填）/ 编辑后通过。
 */
export default function AdminReviewPage() {
  const { showToast } = useToast();
  const { categories } = useCategories();

  const [categoryId, setCategoryId] = useState('');
  const [sort, setSort] = useState('oldest');
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectNote, setRejectNote] = useState('');
  const [actionError, setActionError] = useState('');
  const [busy, setBusy] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editForm, setEditForm] = useState({ title: '', category_id: '', description: '', valid_from: '', valid_to: '' });

  const queueApi = useApi(
    () => adminApi.getReviewQueue({ category_id: categoryId || undefined, sort, page }),
    [categoryId, sort, page],
  );

  // 拍平 + 过滤掉没有有效 id 的脏数据（防止 setSelectedId(NaN)）
  const items = useMemo(() => {
    const payload = queueApi.data;
    if (!payload) return [];
    const raw = Array.isArray(payload) ? payload : Array.isArray(payload.items) ? payload.items : [];
    return raw
      .map(normalizeQueueItem)
      .filter((entry) => entry && Number.isFinite(Number(entry.id)) && Number(entry.id) > 0);
  }, [queueApi.data]);

  const total = Number(queueApi.data && queueApi.data.total) || items.length;

  const selected = useMemo(() => {
    if (items.length === 0) return null;
    const hit = items.find((entry) => Number(entry.id) === Number(selectedId));
    return hit || items[0];
  }, [items, selectedId]);

  useEffect(() => {
    if (selected && Number(selectedId) !== Number(selected.id)) {
      setSelectedId(Number(selected.id));
    }
  }, [selected, selectedId]);

  useEffect(() => {
    setRejectReason('');
    setRejectNote('');
    setActionError('');
  }, [selectedId]);

  const refresh = () => {
    queueApi.reload();
  };

  /** 动作前统一校验主键，杜绝 /api/admin/ads/undefined/... */
  const requireSelectedId = () => {
    const id = selected ? Number(selected.id) : NaN;
    if (!Number.isFinite(id) || id <= 0) {
      setActionError('未获取到有效的广告 ID，请刷新队列后重试');
      return null;
    }
    return id;
  };

  const handleApprove = async () => {
    const adId = requireSelectedId();
    if (!adId) return;
    setBusy(true);
    setActionError('');
    try {
      await adminApi.approveAd(adId, {});
      showToast('已通过，广告将按有效期上线', 'success');
      setSelectedId(null);
      refresh();
    } catch (err) {
      setActionError(err.message || '操作失败，请稍后重试');
    } finally {
      setBusy(false);
    }
  };

  const handleReject = async () => {
    const adId = requireSelectedId();
    if (!adId) return;
    if (!rejectReason) {
      setActionError('请选择拒绝原因（必填）');
      return;
    }
    setBusy(true);
    setActionError('');
    try {
      await adminApi.rejectAd(adId, {
        reason_code: rejectReason,
        reason_note: rejectNote.trim() || undefined,
      });
      showToast('已拒绝，原因已回显给商家', 'success');
      setSelectedId(null);
      refresh();
    } catch (err) {
      setActionError(err.message || '操作失败，请稍后重试');
    } finally {
      setBusy(false);
    }
  };

  const openEdit = () => {
    if (!selected) return;
    setEditForm({
      title: selected.title || '',
      category_id: selected.category_id || '',
      description: selected.description || '',
      valid_from: selected.valid_from_local_date || '',
      valid_to: selected.valid_to_local_date || '',
    });
    setEditOpen(true);
  };

  const submitEditApprove = async () => {
    const adId = requireSelectedId();
    if (!adId) return;
    setBusy(true);
    setActionError('');
    try {
      const changes = {};
      if (editForm.title !== (selected.title || '')) changes.title = editForm.title;
      if (Number(editForm.category_id) !== Number(selected.category_id)) changes.category_id = Number(editForm.category_id);
      if (editForm.description !== (selected.description || '')) changes.description = editForm.description;
      if (editForm.valid_from !== (selected.valid_from_local_date || '')) changes.valid_from = editForm.valid_from;
      if (editForm.valid_to !== (selected.valid_to_local_date || '')) changes.valid_to = editForm.valid_to;
      if (Object.keys(changes).length === 0) {
        setActionError('没有任何字段被修改');
        setBusy(false);
        return;
      }
      await adminApi.editApproveAd(adId, { changes });
      showToast('已编辑并通过，变更前后值已记录', 'success');
      setEditOpen(false);
      setSelectedId(null);
      refresh();
    } catch (err) {
      setActionError(err.message || '操作失败，请稍后重试');
    } finally {
      setBusy(false);
    }
  };

  /*
   * 预检有两个数据源，后端明确区分，前端也分开消费：
   *   1) `precheck`（字符串，= ad.precheck_note）：**提交当时**的留痕，原样存库；
   *   2) `precheck_passed` / `precheck_code` / `precheck_reason`：**读取队列时实时复检**的结论。
   * 队列里的广告可能排队数天，「提交时通过」不代表「现在仍然通过」（例如排队期间过了有效期），
   * 所以主结论用实时复检，`precheck` 作为「提交时留痕」副行展示，两者对照看最准。
   * 老后端只给字符串时，退回字符串解析，保证不白屏。
   */
  const precheckNote = selected && typeof selected.precheck === 'string' && selected.precheck.trim()
    ? selected.precheck.trim()
    : '';
  const livePassed = selected && typeof selected.precheck_passed === 'boolean' ? selected.precheck_passed : null;
  const precheckCode = (selected && selected.precheck_code) || '';
  const liveReason = (selected && selected.precheck_reason) || '';
  // 主结论：优先实时复检；缺失时退回字符串里的「预检通过」判断
  const precheckPassed = livePassed !== null ? livePassed : precheckNote ? /^预检通过/.test(precheckNote) : null;
  // 原因行：失败时展示后端原句；通过且字符串里带说明时退化成说明
  const precheckReason = precheckPassed === false
    ? liveReason || precheckNote || ''
    : precheckNote.replace(/^预检通过[：:]\s*/, '').trim();
  const precheckTitle =
    precheckPassed === null
      ? ''
      : precheckPassed
        ? '预检通过'
        : `预检未通过（${precheckCodeLabel(precheckCode)}）`;
  const hasPrecheck = precheckPassed !== null;
  const merchant = selected && selected.merchant ? selected.merchant : null;

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
        <Box>
          <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700 }}>
            审核队列
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mt: 0.5 }}>
            待审 {total} 条 · 默认等待最久优先
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <TextField
            select
            size="small"
            label="类别"
            value={categoryId}
            onChange={(event) => {
              setCategoryId(event.target.value);
              setPage(1);
              setSelectedId(null);
            }}
            sx={{ minWidth: 132 }}
          >
            <MenuItem value="">全部类别</MenuItem>
            {categories.map((category) => (
              <MenuItem key={category.id} value={category.id}>
                {category.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            size="small"
            label="排序"
            value={sort}
            onChange={(event) => {
              setSort(event.target.value);
              setPage(1);
              setSelectedId(null);
            }}
            sx={{ minWidth: 132 }}
          >
            <MenuItem value="oldest">等待最久优先</MenuItem>
            <MenuItem value="newest">最新提交优先</MenuItem>
          </TextField>
        </Box>
      </Box>

      {queueApi.error ? (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={queueApi.reload}>
              {COMMON.retry}
            </Button>
          }
        >
          {queueApi.error.message || '队列加载失败'}
        </Alert>
      ) : null}

      {queueApi.loading && items.length === 0 ? (
        <Skeleton variant="rounded" height={420} />
      ) : null}

      {!queueApi.loading && items.length === 0 ? (
        <EmptyState title={EMPTY.adminReview.title} description={`${EMPTY.adminReview.desc} 今日处理情况见运营首页。`} />
      ) : null}

      {items.length > 0 ? (
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '320px 1fr' }, gap: 2, alignItems: 'start' }}>
          {/* 左：队列列表 */}
          <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', overflow: 'hidden' }}>
            {items.map((queueItem) => {
              const active = selected && Number(selected.id) === Number(queueItem.id);
              return (
                <Box
                  key={queueItem.id}
                  component="button"
                  type="button"
                  onClick={() => setSelectedId(Number(queueItem.id))}
                  sx={{
                    display: 'block',
                    width: '100%',
                    textAlign: 'left',
                    px: 1.5,
                    py: 1.25,
                    border: 0,
                    borderBottom: '1px solid #EEF1F5',
                    borderLeft: active ? '3px solid #1F3A5F' : '3px solid transparent',
                    bgcolor: active ? 'rgba(31,58,95,.05)' : 'transparent',
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'rgba(31,58,95,.04)' },
                  }}
                >
                  <Typography className="adx-clamp-1" sx={{ fontSize: 14, fontWeight: 700 }}>
                    {queueItem.title}
                  </Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, mt: 0.25 }}>
                    <Typography className="adx-clamp-1" sx={{ fontSize: 12, color: '#5A6472' }}>
                      {queueItem.merchant_name || (queueItem.merchant && queueItem.merchant.name) || '—'}
                    </Typography>
                    <Typography sx={{ fontSize: 12, color: '#8A8F98', whiteSpace: 'nowrap' }}>
                      {waitMinutesText(queueItem.waiting_minutes)}
                    </Typography>
                  </Box>
                </Box>
              );
            })}
            <Box sx={{ px: 1 }}>
              <Pagination page={page} total={total} pageSize={20} onChange={setPage} count={items.length} />
            </Box>
          </Box>

          {/* 右：详情 */}
          {selected ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 2, sm: 2.5 } }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <StatusChip status={selected.status} />
                    <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>
                      队列第 {items.findIndex((item) => Number(item.id) === Number(selected.id)) + 1} / {items.length} 条 ·
                      等待 {waitMinutesText(selected.waiting_minutes)}
                    </Typography>
                  </Box>
                  <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>
                    提交时间：{formatDateTimeCN(selected.submitted_at || selected.created_at)}
                  </Typography>
                </Box>

                <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', flexWrap: { xs: 'wrap', sm: 'nowrap' } }}>
                  <Box className="adx-card-media" sx={{ width: { xs: '100%', sm: 220 }, flex: '0 0 auto' }}>
                    {selected.image_path ? (
                      <Box component="img" className="adx-card-img" src={selected.image_path} alt="" />
                    ) : (
                      <Box className="adx-card-img-fallback">
                        <Typography sx={{ fontSize: 12 }}>无图片</Typography>
                      </Box>
                    )}
                    <AdBadge />
                  </Box>

                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography sx={{ fontSize: 12, color: '#E8590C', fontWeight: 700, mb: 0.25 }}>
                      广告 · 由 {selected.merchant_name || (merchant && merchant.name) || '—'} 提供
                    </Typography>
                    <Typography sx={{ fontSize: 17, fontWeight: 700, mb: 0.5, overflowWrap: 'anywhere' }}>
                      {selected.title}
                    </Typography>
                    <Field label="类别">{selected.category_name || '—'}</Field>
                    <Field label="标签">
                      {Array.isArray(selected.tags) && selected.tags.length
                        ? selected.tags.map((tag) => tag.name).join('、')
                        : '—'}
                    </Field>
                    <Field label="城市 / 价格">
                      {selected.city || '全国'} · {selected.price_text || '—'}
                    </Field>
                    <Field label="优惠条件">{selected.promo_condition || '—'}</Field>
                    <Field label="有效期">
                      {formatRangeCN(selected.valid_from_local_date, selected.valid_to_local_date)}
                      {selected.days_left !== undefined && selected.days_left !== null ? `（剩余 ${selected.days_left} 天）` : ''}
                    </Field>
                    <Field label="限制条款">{selected.restriction || '商家未提供额外限制条款'}</Field>
                    <Field label="落地页">
                      {selected.landing_url ? (
                        <a
                          href={selected.landing_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: '#1F3A5F', wordBreak: 'break-all' }}
                        >
                          {selected.landing_url}
                        </a>
                      ) : selected.landing_domain ? (
                        <Box component="span" sx={{ fontSize: 13 }}>
                          {selected.landing_domain}
                          <Box component="span" sx={{ ml: 0.75, color: '#8A8F98', fontSize: 12 }}>
                            （未下发完整 URL）
                          </Box>
                        </Box>
                      ) : (
                        '—'
                      )}
                    </Field>
                  </Box>
                </Box>

                <Box sx={{ mt: 1.5 }}>
                  <Typography sx={{ fontSize: 12, color: '#5A6472', mb: 0.5 }}>广告描述</Typography>
                  <Typography className="adx-preline" sx={{ fontSize: 13, lineHeight: 1.85, color: '#33404F' }}>
                    {selected.description || '—'}
                  </Typography>
                </Box>
              </Box>

              {/* 商家历史 + 预检 */}
              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' }, gap: 1.5 }}>
                <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: 2 }}>
                  <Typography sx={{ fontSize: 13, fontWeight: 700, mb: 1 }}>商家历史</Typography>
                  {merchant ? (
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Typography sx={{ fontSize: 13 }}>{merchant.name || '—'}</Typography>
                      <Typography sx={{ fontSize: 12, color: '#5A6472' }}>
                        累计提交 {merchant.total_submitted ?? '—'} · 被拒 {merchant.rejected_count ?? '—'} · 举报成立{' '}
                        {merchant.report_resolved_count ?? '—'}
                      </Typography>
                      <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>
                        入驻时间：{merchant.joined_at ? formatMonthCN(merchant.joined_at) : '—'}
                      </Typography>
                    </Box>
                  ) : (
                    <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>商家信息未提供</Typography>
                  )}
                </Box>

                <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: 2 }}>
                  <Typography sx={{ fontSize: 13, fontWeight: 700, mb: 1 }}>预检结果</Typography>
                  {!hasPrecheck ? (
                    <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>预检结果未提供</Typography>
                  ) : (
                    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                      <Box sx={{ color: precheckPassed ? '#1E7A46' : '#B3261E', mt: '2px', display: 'flex' }} aria-hidden="true">
                        {precheckPassed ? <IconShield size={16} /> : <IconWarn size={16} />}
                      </Box>
                      <Box sx={{ minWidth: 0 }}>
                        <Typography sx={{ fontSize: 13, fontWeight: 700, color: precheckPassed ? '#1E7A46' : '#B3261E' }}>
                          {precheckTitle}
                        </Typography>
                        {precheckReason ? (
                          <Typography sx={{ fontSize: 12, color: '#5A6472', mt: 0.5, overflowWrap: 'anywhere' }}>
                            {precheckReason}
                          </Typography>
                        ) : null}
                        {precheckNote && livePassed !== null ? (
                          <Typography sx={{ fontSize: 11, color: '#8A8F98', mt: 0.5, overflowWrap: 'anywhere' }}>
                            提交时留痕：{precheckNote}
                          </Typography>
                        ) : null}
                        {livePassed !== null ? (
                          <Typography sx={{ fontSize: 11, color: '#8A8F98', mt: 0.25 }}>
                            结论为读取队列时的实时复核（排队期间可能已过期）
                          </Typography>
                        ) : null}
                      </Box>
                    </Box>
                  )}
                </Box>
              </Box>

              {/* 审核动作 */}
              <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 2, sm: 2.5 } }}>
                {actionError ? (
                  <Alert severity="error" sx={{ mb: 1.5 }}>
                    {actionError}
                  </Alert>
                ) : null}

                <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '200px 1fr' }, gap: 1.5 }}>
                  <TextField
                    select
                    label="拒绝原因 *"
                    value={rejectReason}
                    onChange={(event) => {
                      setRejectReason(event.target.value);
                      setActionError('');
                    }}
                    helperText={rejectReason ? '' : '未选择原因时「拒绝」按钮不可用'}
                  >
                    {REJECT_REASONS.map((item) => (
                      <MenuItem key={item.code} value={item.code}>
                        {item.label}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    label="补充说明（选填，会回显给商家）"
                    value={rejectNote}
                    onChange={(event) => setRejectNote(event.target.value.slice(0, 200))}
                    helperText={`${rejectNote.length}/200`}
                  />
                </Box>

                <Box sx={{ display: 'flex', gap: 1, mt: 2, flexWrap: 'wrap' }}>
                  <Button
                    variant="contained"
                    startIcon={busy ? <CircularProgress size={14} sx={{ color: '#fff' }} /> : <IconCheck size={16} />}
                    onClick={handleApprove}
                    disabled={busy}
                    sx={{ bgcolor: '#1E7A46', '&:hover': { bgcolor: '#176336' } }}
                  >
                    通过
                  </Button>
                  <Button variant="outlined" onClick={openEdit} disabled={busy} sx={{ borderColor: '#C9D2DD', color: '#1F3A5F' }}>
                    编辑后通过
                  </Button>
                  <Button
                    variant="outlined"
                    color="error"
                    onClick={handleReject}
                    disabled={busy || !rejectReason}
                    sx={{ borderColor: '#B3261E', color: '#B3261E' }}
                  >
                    拒绝
                  </Button>
                  <Box sx={{ flex: 1 }} />
                  <Button
                    variant="text"
                    onClick={() => setSelectedId(null)}
                    disabled={busy}
                    sx={{ color: '#5A6472' }}
                  >
                    下一个
                  </Button>
                </Box>
              </Box>
            </Box>
          ) : null}
        </Box>
      ) : null}

      {/* 编辑后通过 */}
      <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontSize: 17, fontWeight: 700 }}>编辑后通过</DialogTitle>
        <DialogContent>
          <Typography sx={{ fontSize: 12, color: '#5A6472', mb: 2 }}>
            修改内容会在「操作历史」中记录字段前后值，同时通知商家。
          </Typography>
          <TextField
            label="标题"
            value={editForm.title}
            onChange={(event) => setEditForm((prev) => ({ ...prev, title: event.target.value.slice(0, 40) }))}
            fullWidth
            sx={{ mb: 2 }}
          />
          <TextField
            select
            label="一级类别"
            value={editForm.category_id}
            onChange={(event) => setEditForm((prev) => ({ ...prev, category_id: event.target.value }))}
            fullWidth
            sx={{ mb: 2 }}
          >
            {categories.map((category) => (
              <MenuItem key={category.id} value={category.id}>
                {category.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="描述"
            value={editForm.description}
            onChange={(event) => setEditForm((prev) => ({ ...prev, description: event.target.value.slice(0, 500) }))}
            multiline
            minRows={3}
            fullWidth
            sx={{ mb: 2 }}
          />
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 2 }}>
            <TextField
              label="有效期开始"
              type="date"
              value={editForm.valid_from}
              onChange={(event) => setEditForm((prev) => ({ ...prev, valid_from: event.target.value }))}
              InputLabelProps={{ shrink: true }}
              fullWidth
            />
            <TextField
              label="有效期结束"
              type="date"
              value={editForm.valid_to}
              onChange={(event) => setEditForm((prev) => ({ ...prev, valid_to: event.target.value }))}
              InputLabelProps={{ shrink: true }}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setEditOpen(false)} color="inherit" sx={{ color: '#5A6472' }}>
            取消
          </Button>
          <Button variant="contained" onClick={submitEditApprove} disabled={busy} sx={{ bgcolor: '#1F3A5F' }}>
            {busy ? '提交中…' : '保存并通过'}
          </Button>
        </DialogActions>
      </Dialog>

      <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <Box sx={{ color: '#8A8F98', display: 'flex' }} aria-hidden="true">
          <IconExternal size={13} />
        </Box>
        <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>
          落地页在新窗口打开（rel="noopener noreferrer"），不继承后台会话。
        </Typography>
      </Box>
    </Box>
  );
}
