import React, { useState } from 'react';
import { Link as RouterLink, Navigate, useLocation, useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import { useAuth } from '../../context/AuthContext.jsx';
import { useToast } from '../../context/ToastContext.jsx';

/** 商家登录（P0-M-01）：账号 = 邮箱或手机号 */
export default function MerchantLoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { showToast } = useToast();

  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!auth.loading && auth.role === 'merchant') {
    return <Navigate to="/merchant/ads" replace />;
  }

  const redirectTo = (location.state && location.state.from) || '/merchant/ads';

  const submit = async (event) => {
    event.preventDefault();
    if (!account.trim() || !password) {
      setError('请输入账号与密码');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      await auth.loginMerchant({ account: account.trim(), password });
      showToast('登录成功', 'success');
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err.message || '账号或密码错误');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#F7F8FA', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ maxWidth: 1200, width: '100%', mx: 'auto', px: { xs: 2, sm: 3 }, py: 2 }}>
        <Link component={RouterLink} to="/" sx={{ fontSize: 14, color: '#5A6472' }}>
          ← 返回广告发现站
        </Link>
      </Box>

      <Box sx={{ flex: 1, display: 'flex', alignItems: 'flex-start', justifyContent: 'center', px: 2, pb: 6 }}>
        <Box
          component="form"
          onSubmit={submit}
          sx={{ width: '100%', maxWidth: 400, bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: 3 }}
        >
          <Typography component="h1" sx={{ fontSize: 22, fontWeight: 700, mb: 0.5 }}>
            商家登录
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 2.5, lineHeight: 1.7 }}>
            登录后可提交与维护你的广告，并查看效果报告。
          </Typography>

          {error ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          ) : null}

          <TextField
            label="邮箱或手机号"
            value={account}
            onChange={(event) => setAccount(event.target.value)}
            fullWidth
            autoComplete="username"
            sx={{ mb: 2 }}
            inputProps={{ 'aria-label': '邮箱或手机号' }}
          />
          <TextField
            label="密码"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            fullWidth
            autoComplete="current-password"
            sx={{ mb: 1 }}
            inputProps={{ 'aria-label': '密码' }}
          />

          <Typography sx={{ fontSize: 12, color: '#8A8F98', mb: 2 }}>
            忘记密码？本期不提供自助重置，请联系运营者处理。
          </Typography>

          <Button
            type="submit"
            variant="contained"
            fullWidth
            disabled={submitting}
            startIcon={submitting ? <CircularProgress size={14} sx={{ color: '#fff' }} /> : null}
            sx={{ bgcolor: '#1F3A5F', '&:hover': { bgcolor: '#17304F' }, height: 46 }}
          >
            {submitting ? '登录中…' : '登录'}
          </Button>

          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Typography sx={{ fontSize: 13, color: '#5A6472' }}>
              还没有账号？
              <Link component={RouterLink} to="/merchant/signup" sx={{ ml: 0.5, fontSize: 13, fontWeight: 600 }}>
                注册入驻
              </Link>
            </Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
