import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import { IconExternal, IconShield, IconWarn } from '../components/icons.jsx';
import EmptyState from '../components/EmptyState.jsx';
import { getOutbound } from '../api/public.js';
import useApi from '../hooks/useApi.js';
import tracker from '../tracker/index.js';
import {
  GO_BACK,
  GO_BLOCKED_FALLBACK,
  GO_BLOCKED_TITLE,
  GO_CONTINUE,
  GO_DISCLAIMER,
  GO_TITLE,
  goCountdownHint,
  goDomainLine,
} from '../constants/messages.js';

const COUNTDOWN_SECONDS = 5;

/**
 * 外链中间页（P0-B-07）。
 * 显示目标域名 + 完整 URL + 「您即将离开本站」+ 5 秒倒计时后启用「继续前往」+ 返回详情。
 * 不做自动跳转；被阻断时展示原因且只有「返回详情」。
 */
export default function GoPage() {
  const { adId = '' } = useParams();
  const navigate = useNavigate();
  const [seconds, setSeconds] = useState(COUNTDOWN_SECONDS);

  const outbound = useApi(() => getOutbound(adId), [adId]);
  const { data, loading, error, reload } = outbound;

  const allowed = Boolean(data && data.allowed);
  const targetUrl = data && data.url ? data.url : '';

  useEffect(() => {
    setSeconds(COUNTDOWN_SECONDS);
  }, [adId]);

  useEffect(() => {
    if (!allowed) return undefined;
    if (seconds <= 0) return undefined;
    const timer = window.setTimeout(() => setSeconds((value) => (value > 0 ? value - 1 : 0)), 1000);
    return () => window.clearTimeout(timer);
  }, [allowed, seconds]);

  const domain = useMemo(() => {
    if (!data) return '';
    if (data.domain) return data.domain;
    if (!targetUrl) return '';
    try {
      return new window.URL(targetUrl).host;
    } catch {
      return '';
    }
  }, [data, targetUrl]);

  const handleContinue = () => {
    if (!allowed || !targetUrl || seconds > 0) return;
    // 只报原始事实；限频与去重由后端 EventService 负责
    tracker.track('link_click', { ad_id: Number(adId), page: 'detail' });
    tracker.flush(true);
    window.location.assign(targetUrl);
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress size={26} />
      </Box>
    );
  }

  if (error) {
    return (
      <EmptyState
        title="无法获取跳转信息"
        description={error.message || '该广告可能已下线，请返回详情页重试。'}
        actionText="返回详情"
        onAction={() => navigate(`/ad/${adId}`)}
        icon={<IconWarn size={34} />}
      />
    );
  }

  if (data && data.allowed === false) {
    return (
      <Box sx={{ maxWidth: 640, mx: 'auto' }}>
        <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 2.5, sm: 3.5 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5, color: '#B3261E' }}>
            <IconShield size={22} />
            <Typography component="h1" sx={{ fontSize: 20, fontWeight: 700, color: '#B3261E' }}>
              {GO_BLOCKED_TITLE}
            </Typography>
          </Box>
          <Typography sx={{ fontSize: 14, color: '#33404F', lineHeight: 1.8 }}>
            {data.block_reason || GO_BLOCKED_FALLBACK}
          </Typography>
          {data.block_code ? (
            <Typography sx={{ fontSize: 12, color: '#8A8F98', mt: 1 }}>阻断码：{data.block_code}</Typography>
          ) : null}
          {domain ? (
            <Typography sx={{ fontSize: 13, color: '#5A6472', mt: 1.5 }}>{goDomainLine(domain)}</Typography>
          ) : null}
          <Alert severity="warning" sx={{ mt: 2 }}>
            平台无法保证该链接的内容安全，已停止跳转。如你认为判断有误，可在详情页提交举报。
          </Alert>
          <Button
            variant="contained"
            fullWidth
            onClick={() => navigate(`/ad/${adId}`)}
            sx={{ mt: 2.5, bgcolor: '#1F3A5F', '&:hover': { bgcolor: '#17304F' }, height: 46 }}
          >
            {GO_BACK}
          </Button>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 640, mx: 'auto' }}>
      <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 2.5, sm: 3.5 } }}>
        <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700, mb: 1.5 }}>
          {GO_TITLE}
        </Typography>

        <Box sx={{ bgcolor: '#F7F8FA', border: '1px solid #E2E6EC', borderRadius: 2, p: 1.75, mb: 1.5 }}>
          <Typography sx={{ fontSize: 14, color: '#1A1A1A', fontWeight: 700, mb: 0.75 }}>
            {goDomainLine(domain || '未知域名')}
          </Typography>
          <Typography
            sx={{
              fontSize: 12,
              color: '#5A6472',
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
              overflowWrap: 'anywhere',
              lineHeight: 1.7,
            }}
          >
            {targetUrl || '未提供完整链接'}
          </Typography>
        </Box>

        <Typography sx={{ fontSize: 13, color: '#5A6472', lineHeight: 1.8, mb: 0.5 }}>
          即将离开本平台，请自行判断网站安全性。{GO_DISCLAIMER}。
        </Typography>

        <Box sx={{ mt: 2.5 }}>
          <Button
            variant="contained"
            size="large"
            fullWidth
            endIcon={<IconExternal size={18} />}
            disabled={seconds > 0}
            onClick={handleContinue}
            sx={{ bgcolor: '#1F3A5F', '&:hover': { bgcolor: '#17304F' }, height: 48 }}
          >
            {seconds > 0 ? `${GO_CONTINUE}（${seconds}s）` : GO_CONTINUE}
          </Button>
          <Typography sx={{ fontSize: 12, color: '#8A8F98', mt: 0.75, textAlign: 'center' }}>
            {seconds > 0 ? goCountdownHint(seconds) : '倒计时结束，现在可以继续前往'}
          </Typography>
        </Box>

        <Button
          variant="text"
          fullWidth
          onClick={() => navigate(`/ad/${adId}`)}
          sx={{ mt: 1.5, color: '#1F3A5F', height: 44 }}
        >
          {GO_BACK}
        </Button>
      </Box>
    </Box>
  );
}
