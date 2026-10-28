import React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import StatCard from '../../components/StatCard.jsx';
import { IconChevronRight } from '../../components/icons.jsx';
import { getSummary } from '../../api/admin.js';
import useApi from '../../hooks/useApi.js';
import { COMMON } from '../../constants/messages.js';
import { countText } from '../../utils/format.js';

const SHORTCUTS = [
  { key: 'pending_ads', label: '待审广告', to: '/admin/review', hint: '逐条审核：通过 / 拒绝 / 编辑后通过' },
  { key: 'pending_reports', label: '待处理举报', to: '/admin/reports', hint: '48 小时内首次响应' },
  { key: 'sla_overdue_reports', label: '超时举报（>24h）', to: '/admin/reports?overdue=1', hint: '优先处理，避免 SLA 违约' },
];

/** 运营首页（PRD 5.3）：待审/待处理举报/超时举报/今日事件 + 快捷入口 */
export default function AdminDashboardPage() {
  const navigate = useNavigate();
  const { data, loading, error, reload } = useApi(() => getSummary(), []);
  const summary = data || {};

  return (
    <Box>
      <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700, mb: 0.5 }}>
        运营首页
      </Typography>
      <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 2 }}>
        数字与各列表过滤结果完全一致；点卡片进入对应处理页。
      </Typography>

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
          {error.message || '概览加载失败'}
        </Alert>
      ) : null}

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', md: 'repeat(4, minmax(0, 1fr))' },
          gap: 1.5,
          mb: 2.5,
        }}
      >
        <StatCard
          label="待审广告"
          value={loading ? '…' : countText(summary.pending_ads)}
          unit="条"
          tone="primary"
          tooltip="状态为 pending 的广告数量，与审核队列首屏一致。"
        />
        <StatCard
          label="待处理举报"
          value={loading ? '…' : countText(summary.pending_reports)}
          unit="条"
          hint="48 小时内首次响应"
        />
        <StatCard
          label="超时举报（>24h）"
          value={loading ? '…' : countText(summary.sla_overdue_reports)}
          unit="条"
          tone={Number(summary.sla_overdue_reports) > 0 ? 'danger' : 'success'}
          tooltip="提交超过 24 小时仍为待处理/处理中的举报数。"
        />
        <StatCard
          label="今日事件量"
          value={loading ? '…' : countText(summary.today_events)}
          unit="条"
          hint="北京时间自然日"
        />
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' }, gap: 1.5, mb: 2.5 }}>
        {SHORTCUTS.map((item) => (
          <Box
            key={item.key}
            component="button"
            type="button"
            onClick={() => navigate(item.to)}
            sx={{
              textAlign: 'left',
              cursor: 'pointer',
              bgcolor: '#FFFFFF',
              border: '1px solid #E2E6EC',
              borderRadius: '12px',
              p: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              '&:hover': { borderColor: '#C9D2DD', boxShadow: '0 4px 12px rgba(15,23,42,.08)' },
            }}
          >
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography sx={{ fontSize: 15, fontWeight: 700 }}>{item.label}</Typography>
              <Typography sx={{ fontSize: 12, color: '#8A8F98', mt: 0.25 }}>{item.hint}</Typography>
            </Box>
            <Box sx={{ color: '#5A6472', display: 'flex' }} aria-hidden="true">
              <IconChevronRight size={18} />
            </Box>
          </Box>
        ))}
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' }, gap: 1.5 }}>
        <StatCard label="今日已处理广告" value={loading ? '…' : countText(summary.today_processed_ads)} unit="条" />
        <StatCard label="近 7 天已处理举报" value={loading ? '…' : countText(summary.week_resolved_reports)} unit="条" />
        <Box
          sx={{
            bgcolor: '#FFFFFF',
            border: '1px solid #E2E6EC',
            borderRadius: '12px',
            p: 2,
            display: 'flex',
            flexDirection: 'column',
            gap: 0.75,
          }}
        >
          <Typography sx={{ fontSize: 13, color: '#5A6472' }}>快捷入口</Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Button size="small" onClick={() => navigate('/admin/ads')} sx={{ fontSize: 12, color: '#1F3A5F' }}>
              广告台账
            </Button>
            <Button size="small" onClick={() => navigate('/admin/merchants')} sx={{ fontSize: 12, color: '#1F3A5F' }}>
              商家管理
            </Button>
            <Button size="small" onClick={() => navigate('/admin/stats')} sx={{ fontSize: 12, color: '#1F3A5F' }}>
              基础分析
            </Button>
            <Button size="small" onClick={() => navigate('/admin/categories')} sx={{ fontSize: 12, color: '#1F3A5F' }}>
              标签维护
            </Button>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
