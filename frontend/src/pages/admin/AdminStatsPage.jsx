import React, { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
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
import StatCard from '../../components/StatCard.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import { IconDownload, IconRefresh, IconWarn } from '../../components/icons.jsx';
import * as adminApi from '../../api/admin.js';
import useApi from '../../hooks/useApi.js';
import { useToast } from '../../context/ToastContext.jsx';
import { COMMON, EMPTY } from '../../constants/messages.js';
import { countText, permilleText, rateText, todayCST } from '../../utils/format.js';

const EXPORT_TYPES = [
  { code: 'ads', label: '按广告明细' },
  { code: 'category', label: '按类别汇总' },
  { code: 'events', label: '事件流水' },
];

/**
 * 基础分析（P1-E-02 / P1-E-03 / P1-E-04）。
 * 日期区间 + 总览指标 + 按广告排行 + 按类别分布 + 漏斗四步 + 异常标记 + 导出 CSV。
 */
export default function AdminStatsPage() {
  const { showToast } = useToast();

  const [from, setFrom] = useState(todayCST(-6));
  const [to, setTo] = useState(todayCST(0));
  const [exportType, setExportType] = useState('ads');
  const [exporting, setExporting] = useState(false);

  const overviewApi = useApi(() => adminApi.getStatsOverview({ from, to }), [from, to]);
  const funnelApi = useApi(() => adminApi.getStatsFunnel({ from, to }), [from, to]);

  const range = (overviewApi.data && overviewApi.data.range) || { from, to };
  const totals = (overviewApi.data && overviewApi.data.totals) || {};
  const byAd = Array.isArray(overviewApi.data && overviewApi.data.by_ad) ? overviewApi.data.by_ad : [];
  const byCategory = Array.isArray(overviewApi.data && overviewApi.data.by_category) ? overviewApi.data.by_category : [];
  const abnormal = Array.isArray(overviewApi.data && overviewApi.data.abnormal) ? overviewApi.data.abnormal : [];
  const steps = Array.isArray(funnelApi.data && funnelApi.data.steps) ? funnelApi.data.steps : [];

  const hasData = Number(totals.impressions || 0) + Number(totals.detail_views || 0) + Number(totals.link_clicks || 0) > 0;

  const handleExport = async () => {
    setExporting(true);
    try {
      const filename = await adminApi.exportStatsCsv({ from, to, type: exportType }, `统计_${from}_${to}.csv`);
      showToast(`已导出 ${filename}`, 'success');
    } catch (err) {
      showToast(err.message || '导出失败，请稍后重试', 'error');
    } finally {
      setExporting(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
        <Box>
          <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700 }}>
            基础分析
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mt: 0.5 }}>
            统计区间：{range.from || from} 至 {range.to || to}（北京时间自然日）· 指标与事件表 count 一致
          </Typography>
        </Box>
        <Button
          size="small"
          startIcon={<IconRefresh size={15} />}
          onClick={() => {
            overviewApi.reload();
            funnelApi.reload();
          }}
          sx={{ color: '#5A6472' }}
        >
          刷新
        </Button>
      </Box>

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
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button size="small" onClick={() => { setFrom(todayCST(0)); setTo(todayCST(0)); }} sx={{ fontSize: 12, color: '#1F3A5F' }}>
            今天
          </Button>
          <Button size="small" onClick={() => { setFrom(todayCST(-6)); setTo(todayCST(0)); }} sx={{ fontSize: 12, color: '#1F3A5F' }}>
            近 7 天
          </Button>
          <Button size="small" onClick={() => { setFrom(todayCST(-29)); setTo(todayCST(0)); }} sx={{ fontSize: 12, color: '#1F3A5F' }}>
            近 30 天
          </Button>
        </Box>
        <Box sx={{ flex: 1 }} />
        <TextField
          select
          size="small"
          label="导出类型"
          value={exportType}
          onChange={(event) => setExportType(event.target.value)}
          sx={{ minWidth: 140 }}
        >
          {EXPORT_TYPES.map((item) => (
            <MenuItem key={item.code} value={item.code}>
              {item.label}
            </MenuItem>
          ))}
        </TextField>
        <Button
          variant="outlined"
          startIcon={exporting ? <CircularProgress size={14} /> : <IconDownload size={16} />}
          onClick={handleExport}
          disabled={exporting}
          sx={{ borderColor: '#C9D2DD', color: '#1F3A5F' }}
        >
          {exporting ? '导出中…' : '导出 CSV'}
        </Button>
      </Box>

      {overviewApi.error ? (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={overviewApi.reload}>
              {COMMON.retry}
            </Button>
          }
        >
          {overviewApi.error.message || '总览加载失败'}
        </Alert>
      ) : null}

      {overviewApi.loading && !overviewApi.data ? <Skeleton variant="rounded" height={300} /> : null}

      {!overviewApi.loading && !hasData ? (
        <EmptyState title={EMPTY.adminStats.title} description={EMPTY.adminStats.desc} />
      ) : null}

      {hasData ? (
        <>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', md: 'repeat(4, minmax(0, 1fr))' },
              gap: 1.5,
              mb: 1.5,
            }}
          >
            <StatCard
              label="展示量"
              value={countText(totals.impressions)}
              hint="含重复展示"
              tooltip="count(impression)，同一会话去重、跨会话重复计数。"
            />
            <StatCard
              label="独立展示人数"
              value={countText(totals.unique_visitors)}
              tooltip="count(distinct visitor_id) where event=impression，仅后台可见。"
            />
            <StatCard label="详情查看量" value={countText(totals.detail_views)} tooltip="count(detail_view)" />
            <StatCard
              label="外链点击量"
              value={countText(totals.link_clicks)}
              hint="不代表成交或订单"
              tooltip="count(link_click)；被限频的点击记为 link_click_suppressed，不计入。"
            />
            <StatCard
              label="详情页点击率"
              value={rateText(totals.ctr_detail, totals.link_clicks, totals.detail_views)}
              tooltip="link_click ÷ detail_view，括号内为分子/分母。"
            />
            <StatCard
              label="整体点击率"
              value={rateText(totals.ctr_impression, totals.link_clicks, totals.impressions)}
              tooltip="link_click ÷ impression，括号内为分子/分母。"
            />
            <StatCard label="收藏数" value={countText(totals.favorites)} tooltip="count(favorite)，取消收藏不抵扣。" />
            <StatCard
              label="举报率"
              value={permilleText(totals.report_rate_permille)}
              hint={`举报 ${countText(totals.reports)} 条`}
              tooltip="report 数 ÷ impression 数，以万分比展示。"
            />
          </Box>

          {/* 漏斗 */}
          <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 1.75, sm: 2 }, mb: 1.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mb: 1.5 }}>
              <Typography sx={{ fontSize: 15, fontWeight: 700 }}>转化漏斗</Typography>
              <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>首页访问 → 列表 → 详情 → 外链</Typography>
            </Box>
            {funnelApi.error ? <Alert severity="error">{funnelApi.error.message}</Alert> : null}
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(4, minmax(0, 1fr))' }, gap: 1.5 }}>
              {steps.map((step, index) => (
                <Box key={step.key || index} sx={{ border: '1px solid #EEF1F5', borderRadius: 2, p: 1.5, bgcolor: '#FBFCFD' }}>
                  <Typography sx={{ fontSize: 12, color: '#5A6472' }}>{step.label || step.key}</Typography>
                  <Typography sx={{ fontSize: 20, fontWeight: 700, color: '#1F3A5F', mt: 0.25 }}>
                    {countText(step.count)}
                  </Typography>
                  <Typography sx={{ fontSize: 12, color: '#8A8F98', mt: 0.25 }}>
                    {index === 0
                      ? '基准 100%'
                      : step.rate === undefined || step.rate === null
                        ? '—'
                        : rateText(step.rate, step.count, steps[index - 1] && steps[index - 1].count)}
                  </Typography>
                </Box>
              ))}
            </Box>
            {funnelApi.data && funnelApi.data.note ? (
              <Typography sx={{ fontSize: 12, color: '#8A8F98', mt: 1.25 }}>{funnelApi.data.note}</Typography>
            ) : null}
          </Box>

          {/* 异常标记 */}
          {abnormal.length > 0 ? (
            <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #F3D9C4', borderRadius: '12px', p: { xs: 1.75, sm: 2 }, mb: 1.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Box sx={{ color: '#E8590C', display: 'flex' }} aria-hidden="true">
                  <IconWarn size={16} />
                </Box>
                <Typography sx={{ fontSize: 15, fontWeight: 700 }}>疑似刷量（P1-E-03）</Typography>
                <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>同一访客单日对同一广告点击 &gt;20 次</Typography>
              </Box>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                {abnormal.map((item) => (
                  <Box key={item.ad_id} sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'baseline' }}>
                    <Typography sx={{ fontSize: 13, fontWeight: 600 }}>{item.title}</Typography>
                    <Typography sx={{ fontSize: 12, color: '#5A6472' }}>
                      标记访客 {countText(item.flagged_visitors)} · 总点击 {countText(item.total_clicks)}
                    </Typography>
                    {item.note ? <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>{item.note}</Typography> : null}
                  </Box>
                ))}
              </Box>
            </Box>
          ) : null}

          {/* 按广告 */}
          <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', overflow: 'hidden', mb: 1.5 }}>
            <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid #E2E6EC' }}>
              <Typography sx={{ fontSize: 15, fontWeight: 700 }}>按广告排行</Typography>
            </Box>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>广告</TableCell>
                    <TableCell>商家</TableCell>
                    <TableCell align="right">展示量</TableCell>
                    <TableCell align="right">详情查看</TableCell>
                    <TableCell align="right">外链点击</TableCell>
                    <TableCell align="right">详情页点击率</TableCell>
                    <TableCell align="right">收藏</TableCell>
                    <TableCell align="right">举报</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {byAd.map((row) => (
                    <TableRow key={row.ad_id} hover>
                      <TableCell sx={{ maxWidth: 220 }}>
                        <Typography className="adx-clamp-1" sx={{ fontSize: 13 }}>
                          {row.title}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ whiteSpace: 'nowrap' }}>{row.merchant_name || '—'}</TableCell>
                      <TableCell align="right">{countText(row.impressions)}</TableCell>
                      <TableCell align="right">{countText(row.detail_views)}</TableCell>
                      <TableCell align="right">{countText(row.link_clicks)}</TableCell>
                      <TableCell align="right">{rateText(row.ctr_detail, row.link_clicks, row.detail_views)}</TableCell>
                      <TableCell align="right">{countText(row.favorites)}</TableCell>
                      <TableCell align="right">{countText(row.reports)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>

          {/* 按类别 */}
          <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', overflow: 'hidden' }}>
            <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid #E2E6EC' }}>
              <Typography sx={{ fontSize: 15, fontWeight: 700 }}>按类别分布</Typography>
            </Box>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>类别</TableCell>
                    <TableCell align="right">展示量</TableCell>
                    <TableCell align="right">详情查看</TableCell>
                    <TableCell align="right">外链点击</TableCell>
                    <TableCell align="right">详情页点击率</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {byCategory.map((row) => (
                    <TableRow key={row.slug || row.name} hover>
                      <TableCell>{row.name || row.slug}</TableCell>
                      <TableCell align="right">{countText(row.impressions)}</TableCell>
                      <TableCell align="right">{countText(row.detail_views)}</TableCell>
                      <TableCell align="right">{countText(row.link_clicks)}</TableCell>
                      <TableCell align="right">{rateText(null, row.link_clicks, row.detail_views)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        </>
      ) : null}
    </Box>
  );
}
