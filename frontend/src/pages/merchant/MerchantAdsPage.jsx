import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Skeleton from '@mui/material/Skeleton';
import Collapse from '@mui/material/Collapse';
import StatusChip from '../../components/StatusChip.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import ConfirmDialog from '../../components/ConfirmDialog.jsx';
import { IconPlus, IconRefresh } from '../../components/icons.jsx';
import * as merchantApi from '../../api/merchant.js';
import useApi from '../../hooks/useApi.js';
import { useToast } from '../../context/ToastContext.jsx';
import { AD_STATUS_TABS } from '../../constants/enums.js';
import { labelOf, REJECT_REASONS } from '../../constants/reasons.js';
import { COMMON, EMPTY } from '../../constants/messages.js';
import { formatDateCN, formatDateTimeCN, validToText } from '../../utils/format.js';

/**
 * 我的广告（P0-M-04）。
 * 状态分页签 + 列表 + 被拒原因展开 + 新建/撤回/复制/删除。
 */
export default function MerchantAdsPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [tab, setTab] = useState('all');
  const [expanded, setExpanded] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const { data, loading, error, reload } = useApi(
    () => merchantApi.getAds({ status: tab === 'all' ? undefined : tab, page: 1 }),
    [tab],
  );

  const items = Array.isArray(data && data.items) ? data.items : [];
  const counts = (data && data.counts) || {};

  const runAction = async (label, action, adId) => {
    setBusyId(adId);
    try {
      await action();
      showToast(`${label}成功`, 'success');
      reload();
    } catch (err) {
      showToast(err.message || `${label}失败，请稍后重试`, 'error');
    } finally {
      setBusyId(null);
      setConfirm(null);
    }
  };

  const handleDuplicate = async (ad) => {
    setBusyId(ad.id);
    try {
      const res = await merchantApi.duplicateAd(ad.id);
      const newAd = (res && res.ad) || res;
      showToast('已复制为新草稿，请修改后提交', 'success');
      reload();
      if (newAd && newAd.id) navigate(`/merchant/ads/${newAd.id}`);
    } catch (err) {
      showToast(err.message || '复制失败，请稍后重试', 'error');
    } finally {
      setBusyId(null);
    }
  };

  const renderActions = (ad) => {
    const disabled = busyId === ad.id;
    const actions = [];

    actions.push(
      <Button key="edit" size="small" onClick={() => navigate(`/merchant/ads/${ad.id}`)} disabled={disabled} sx={{ fontSize: 13 }}>
        编辑
      </Button>,
    );

    if (ad.status === 'pending') {
      actions.push(
        <Button
          key="withdraw"
          size="small"
          disabled={disabled}
          onClick={() => runAction('撤回', () => merchantApi.withdrawAd(ad.id), ad.id)}
          sx={{ fontSize: 13, color: '#5A6472' }}
        >
          撤回
        </Button>,
      );
    }

    if (ad.status === 'draft') {
      actions.push(
        <Button
          key="submit"
          size="small"
          disabled={disabled}
          onClick={() => runAction('提交审核', () => merchantApi.submitAd(ad.id), ad.id)}
          sx={{ fontSize: 13, color: '#1F3A5F' }}
        >
          提交审核
        </Button>,
        <Button
          key="delete"
          size="small"
          disabled={disabled}
          onClick={() => setConfirm({ type: 'delete', ad })}
          sx={{ fontSize: 13, color: '#B3261E' }}
        >
          删除
        </Button>,
      );
    }

    if (ad.status === 'rejected') {
      actions.push(
        <Button
          key="abandon"
          size="small"
          disabled={disabled}
          onClick={() => runAction('转草稿', () => merchantApi.abandonAd(ad.id), ad.id)}
          sx={{ fontSize: 13, color: '#5A6472' }}
        >
          转为草稿
        </Button>,
      );
    }

    if (ad.status === 'expired' || ad.status === 'offline') {
      actions.push(
        <Button key="duplicate" size="small" disabled={disabled} onClick={() => handleDuplicate(ad)} sx={{ fontSize: 13, color: '#1F3A5F' }}>
          复制续期
        </Button>,
      );
    }

    return actions;
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
        <Box>
          <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700 }}>
            我的广告
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mt: 0.5 }}>
            共 {counts.all || items.length} 条 · 单日新建上限 5 条、同时在架上限 20 条
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button size="small" startIcon={<IconRefresh size={15} />} onClick={reload} sx={{ color: '#5A6472' }}>
            刷新
          </Button>
          <Button
            variant="contained"
            startIcon={<IconPlus size={16} />}
            onClick={() => navigate('/merchant/ads/new')}
            sx={{ bgcolor: '#1F3A5F', '&:hover': { bgcolor: '#17304F' } }}
          >
            新建广告
          </Button>
        </Box>
      </Box>

      <Box sx={{ borderBottom: '1px solid #E2E6EC', mb: 2 }}>
        <Tabs
          value={tab}
          onChange={(_, value) => setTab(value)}
          variant="scrollable"
          scrollButtons="auto"
          allowScrollButtonsMobile
          aria-label="广告状态筛选"
        >
          {AD_STATUS_TABS.map((item) => (
            <Tab
              key={item.code}
              value={item.code}
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  {item.label}
                  <Box component="span" sx={{ fontSize: 12, color: '#8A8F98' }}>
                    {item.code === 'all' ? counts.all || 0 : counts[item.code] || 0}
                  </Box>
                </Box>
              }
            />
          ))}
        </Tabs>
      </Box>

      {error ? (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={reload}>
              {COMMON.retry}
            </Button>
          }
        >
          {error.message || '广告列表加载失败'}
        </Alert>
      ) : null}

      {loading && items.length === 0 ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={`ads-sk-${index}`} variant="rounded" height={96} />
          ))}
        </Box>
      ) : null}

      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title={EMPTY.merchantAds.title}
          description="审核要点：标题与描述需与落地页一致、有效期不超过 90 天、落地页必须为 http/https 且无危险文件后缀、不得含禁投行业关键词。"
          actionText="新建第一条广告"
          onAction={() => navigate('/merchant/ads/new')}
          icon={<IconPlus size={34} />}
        />
      ) : null}

      {items.length > 0 ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
          {items.map((ad) => {
            const rejectLabel = ad.reject_reason_code ? labelOf(REJECT_REASONS, ad.reject_reason_code) : '';
            // 后端 AdManageOut 只有 reject_reason_code 与 reject_reason，
            // 且 reject_reason 已是「原因标签：补充说明」的完整文案（services/ads.py::reject），直接展示即可。
            const rejectText = ad.reject_reason || rejectLabel;
            const isExpanded = expanded === ad.id;
            return (
              <Box
                key={ad.id}
                sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 1.5, sm: 2 } }}
              >
                <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
                  <Box
                    sx={{
                      width: { xs: 88, sm: 112 },
                      flex: '0 0 auto',
                      aspectRatio: '16 / 9',
                      borderRadius: 1.5,
                      bgcolor: '#EEF1F5',
                      overflow: 'hidden',
                    }}
                  >
                    {ad.image_path ? (
                      <Box component="img" src={ad.image_path} alt="" sx={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    ) : null}
                  </Box>

                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
                      <StatusChip status={ad.status} />
                      <Typography className="adx-clamp-1" sx={{ fontSize: 15, fontWeight: 700, minWidth: 0 }}>
                        {ad.title || '未命名广告'}
                      </Typography>
                    </Box>
                    <Typography sx={{ fontSize: 12, color: '#5A6472' }}>
                      {ad.category_name || '类别未提供'} · {ad.city || '全国'} · {validToText(ad.valid_to_local_date)}
                    </Typography>
                    <Typography sx={{ fontSize: 12, color: '#8A8F98', mt: 0.25 }}>
                      提交时间：{formatDateTimeCN(ad.submitted_at || ad.created_at)}
                      {ad.valid_from_local_date ? ` · 生效 ${formatDateCN(ad.valid_from_local_date, { withYear: true })}` : ''}
                    </Typography>

                    {ad.status === 'rejected' ? (
                      <Box sx={{ mt: 0.75 }}>
                        <Button
                          size="small"
                          onClick={() => setExpanded(isExpanded ? null : ad.id)}
                          sx={{ fontSize: 12, color: '#B3261E', minWidth: 0, p: 0 }}
                        >
                          {isExpanded ? '收起拒绝原因' : '查看拒绝原因'}
                        </Button>
                        <Collapse in={isExpanded}>
                          <Alert severity="error" sx={{ mt: 1, fontSize: 13 }}>
                            {rejectText || '审核未通过，请修改后重新提交'}
                          </Alert>
                        </Collapse>
                      </Box>
                    ) : null}

                    <Box sx={{ display: 'flex', gap: 0.5, mt: 1, flexWrap: 'wrap' }}>{renderActions(ad)}</Box>
                  </Box>
                </Box>
              </Box>
            );
          })}
        </Box>
      ) : null}

      <ConfirmDialog
        open={Boolean(confirm)}
        title="删除草稿"
        description={confirm ? `将永久删除草稿「${confirm.ad.title}」，此操作不可撤销。` : ''}
        confirmText="删除"
        danger
        loading={Boolean(busyId)}
        onConfirm={() => {
          if (!confirm) return;
          runAction('删除', () => merchantApi.deleteAd(confirm.ad.id), confirm.ad.id);
        }}
        onClose={() => setConfirm(null)}
      />
    </Box>
  );
}
