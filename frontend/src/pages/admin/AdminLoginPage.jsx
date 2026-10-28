import React, { useState } from 'react';
import { Link as RouterLink, Navigate, useLocation, useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Link from '@mui/material/Link';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import { useAuth } from '../../context/AuthContext.jsx';
import { useToast } from '../../context/ToastContext.jsx';

/** 后台登录（P0-A-01）：失败 5 次锁定 15 分钟（后端 423 LOCKED） */
export default function AdminLoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { showToast } = useToast();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [locked, setLocked] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (!auth.loading && auth.role === 'admin') {
    return <Navigate to="/admin" replace />;
  }

  const redirectTo = (location.state && location.state.from) || '/admin';

  const submit = async (event) => {
    event.preventDefault();
    if (!username.trim() || !password) {
      setError('请输入账号与密码');
      return;
    }
    setSubmitting(true);
    setError('');
    setLocked(false);
    try {
      await auth.loginAdmin({ username: username.trim(), password });
      showToast('登录成功', 'success');
      navigate(redirectTo, { replace: true });
    } catch (err) {
      if (err.status === 423 || err.code === 'LOCKED') {
        setLocked(true);
        setError(err.message || '连续登录失败次数过多，账号已锁定 15 分钟');
      } else {
        setError(err.message || '账号或密码错误');
      }
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
            运营后台登录
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 2.5, lineHeight: 1.7 }}>
            仅限平台运营者使用。所有接口在服务端独立校验身份，与路径是否被猜到无关。
          </Typography>

          {error ? (
            <Alert severity={locked ? 'warning' : 'error'} sx={{ mb: 2 }}>
              {error}
            </Alert>
          ) : null}

          <TextField
            label="账号"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            fullWidth
            autoComplete="username"
            sx={{ mb: 2 }}
            inputProps={{ 'aria-label': '管理员账号' }}
          />
          <TextField
            label="密码"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            fullWidth
            autoComplete="current-password"
            sx={{ mb: 2 }}
            inputProps={{ 'aria-label': '管理员密码' }}
          />

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
        </Box>
      </Box>
    </Box>
  );
}
