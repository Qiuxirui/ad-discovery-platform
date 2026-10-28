import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import MenuItem from '@mui/material/MenuItem';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TableContainer from '@mui/material/TableContainer';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import StatCard from '../../components/StatCard.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import StatusChip from '../../components/StatusChip.jsx';
import { IconDownload } from '../../components/icons.jsx';
import * as merchantApi from '../../api/merchant.js';
import useApi from '../../hooks/useApi.js';
import { useToast } from '../../context/ToastContext.jsx';
import { COMMON, EMPTY } from '../../constants/messages.js';
import { countText, daysLeftText, percentText, todayCST } from '../../utils/format.js';

/**
 * 效果报告（P1-R-01 / P1-R-02）。
 * 广告选择器 + 日期区间 + 4 个指标卡（带口径 tooltip）+ 按日趋势 + 导出 CSV。
 */
export default function MerchantReportPage() {
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [adId, setAdId] = useState('');
  const [from, setFrom] = useState(todayCST(-6));
  const [to, setTo] = useState(todayCST(0));
  const [exporting, setExporting] = useState(false);

  const adsApi = useApi(() => merchantApi.getAds({ page: 1 }), []);
  const ads = Array.isArray(adsApi.data && adsApi.data.items) ? adsApi.data.items : [];

  useEffect(() => {
    if (!adId && ads.length > 0) setAdId(String(ads[0].id));
  }, [ads, adId]);

  const reportApi = useApi(
    () => merchantApi.getReport({ ad_id: adId, from, to }),
    [adId, from, to],
    { enabled: Boolean(adId) },
  );

  const report = reportApi.data;
  const metrics = (report && report.metrics) || {};
  const daily = Array.isArray(report && report.daily) ? report.daily : [];
  const adInfo = (report && report.ad) || null;

  const hasEvents = useMemo(
    () => Number(metrics.impressions || 0) + Number(metrics.detail_views || 0) + Number(metrics.link_clicks || 0) > 0,
    [metrics],
  );

  const handleExport = async () => {
    if (!adId) return;
    setExporting(true);
    try {
      const filename = await merchantApi.exportReportCsv({ ad_id: adId, from, to }, `报告_${adId}_${from}_${to}.csv`);
      showToast(`已导出 ${filename}`, 'success');
    } catch (err) {
      showToast(err.message || '导出失败，请稍后重试', 'error');
    } finally {
      setExporting(false);
    }
  };

  return (
    <Box>
      <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700, mb: 0.5 }}>
        效果报告
      </Typography>
      <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 2 }}>
        仅统计你自己广告的匿名汇总数据；不含访客个人信息，也不代表成交或订单。
      </Typography>

      <Box
        sx={{
          display: 'flex',
          gap: 1.5,
          flexWrap: 'wrap',
          alignItems: 'center',
          bgcolor: '#FFFFFF',
          border: '1px solid #E2E6EC',
          borderRadius: '12px',
          p: { xs: 1.5, sm: 2 },
          mb: 2,
        }}
      >
        <TextField
          select
          label="选择广告"
          value={adId}
          onChange={(event) => setAdId(event.target.value)}
          sx={{ minWidth: 240, flex: '1 1 240px' }}
          disabled={ads.length === 0}
        >
          {ads.map((ad) => (
            <MenuItem key={ad.id} value={String(ad.id)}>
              {ad.title}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="开始日期"
          type="date"
          value={from}
          onChange={(event) => setFrom(event.target.value)}
          InputLabelProps={{ shrink: true }}
          sx={{ width: 168 }}
        />
        <TextField
          label="结束日期"
          type="date"
          value={to}
          onChange={(event) => setTo(event.target.value)}
          InputLabelProps={{ shrink: true }}
          sx={{ width: 168 }}
        />
        <Box sx={{ flex: 1 }} />
        <Button
          variant="outlined"
          startIcon={exporting ? <CircularProgress size={14} /> : <IconDownload size={16} />}
          onClick={handleExport}
          disabled={!adId || exporting}
          sx={{ borderColor: '#C9D2DD', color: '#1F3A5F' }}
        >
          {exporting ? '导出中…' : '导出 CSV'}
        </Button>
      </Box>

      {adsApi.error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {adsApi.error.message || '广告列表加载失败'}
        </Alert>
      ) : null}

      {!adsApi.loading && ads.length === 0 ? (
        <EmptyState
          title="还没有可统计的广告"
          description="先提交一条广告，审核通过上线后这里会有数据。"
          actionText="去新建广告"
          onAction={() => navigate('/merchant/ads/new')}
        />
      ) : null}

      {reportApi.error ? (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={reportApi.reload}>
              {COMMON.retry}
            </Button>
          }
        >
          {reportApi.error.message || '报告加载失败'}
        </Alert>
      ) : null}

      {adInfo ? (
        <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', flexWrap: 'wrap', mb: 1.5 }}>
          <StatusChip status={adInfo.status} />
          <Typography sx={{ fontSize: 13, color: '#5A6472' }}>
            有效期至 {adInfo.valid_to_local_date || '—'}（{daysLeftText(adInfo.days_left)}）
          </Typography>
        </Box>
      ) : null}

      {adId ? (
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', md: 'repeat(4, minmax(0, 1fr))' }, gap: 1.5, mb: 2 }}>
          <StatCard
            label="展示量"
            value={countText(metrics.impressions)}
            hint="含重复展示"
            tooltip="卡片在视口内可见 ≥50% 且停留 ≥1 秒计一次；同一会话内同一广告只计一次，跨会话会重复计入。"
          />
          <StatCard
            label="详情查看量"
            value={countText(metrics.detail_views)}
            tooltip="详情页主内容可见并停留 ≥1 秒计一次；同一会话 30 分钟内只计一次。"
          />
          <StatCard
            label="外链点击量"
            value={countText(metrics.link_clicks)}
            hint="不代表成交或订单"
            tooltip="在中间页点击「继续前往」并完成跳转才计一次；同一访客对同一广告 10 秒内只计一次，单日上限 20 次。"
          />
          <StatCard
            label="详情页点击率"
            value={percentText(metrics.link_clicks, metrics.detail_views)}
            tooltip="公式：外链点击量 ÷ 详情查看量。必须同时看分母，点击不等于成交。"
          />
        </Box>
      ) : null}

      {adId && !reportApi.loading && !hasEvents ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          {adInfo && adInfo.status !== 'active'
            ? '广告尚未上线（或已结束），当前区间没有可统计的展示；上线后自动开始统计。'
            : EMPTY.merchantReport.title + '。' + EMPTY.merchantReport.desc}
        </Alert>
      ) : null}

      {daily.length > 0 ? (
        <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', overflow: 'hidden' }}>
          <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid #E2E6EC' }}>
            <Typography sx={{ fontSize: 15, fontWeight: 700 }}>按日趋势（北京时间自然日）</Typography>
          </Box>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>日期</TableCell>
                  <TableCell align="right">展示量</TableCell>
                  <TableCell align="right">详情查看量</TableCell>
                  <TableCell align="right">外链点击量</TableCell>
                  <TableCell align="right">点击率</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {daily.map((row) => (
                  <TableRow key={row.date} hover>
                    <TableCell>{row.date}</TableCell>
                    <TableCell align="right">{countText(row.impressions)}</TableCell>
                    <TableCell align="right">{countText(row.detail_views)}</TableCell>
                    <TableCell align="right">{countText(row.link_clicks)}</TableCell>
                    <TableCell align="right">{percentText(row.link_clicks, row.detail_views)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      ) : null}

      {report && report.notes ? (
        <Box sx={{ mt: 2 }}>
          <Typography sx={{ fontSize: 12, color: '#8A8F98', lineHeight: 1.8 }}>
            口径说明：展示量与详情查看量均为事件计数，允许多次计数；点击率分母已在括号内给出；
            平台不做付费加权，也不把点击称为成交。
          </Typography>
        </Box>
      ) : null}
    </Box>
  );
}
