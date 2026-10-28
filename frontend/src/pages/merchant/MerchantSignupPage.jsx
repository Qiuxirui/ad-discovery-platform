import React, { useState } from 'react';
import { Link as RouterLink, Navigate, useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import Link from '@mui/material/Link';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import { useAuth } from '../../context/AuthContext.jsx';
import { useCategories } from '../../context/CategoriesContext.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import * as merchantApi from '../../api/merchant.js';
import { CITIES } from '../../constants/cities.js';

const PHONE_RE = /^1[3-9]\d{9}$/;
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/;

/** 商家注册即入驻（P0-M-01），须勾选广告政策 */
export default function MerchantSignupPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { categories } = useCategories();

  const [form, setForm] = useState({
    name: '',
    contact_name: '',
    phone: '',
    email: '',
    password: '',
    city: '全国',
    main_category_id: '',
  });
  const [agree, setAgree] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!auth.loading && auth.role === 'merchant') {
    return <Navigate to="/merchant/ads" replace />;
  }

  const setField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [key]: '' }));
  };

  const validate = () => {
    const next = {};
    if (!form.name.trim()) next.name = '请填写商家名';
    else if (form.name.trim().length > 60) next.name = '商家名不能超过 60 字';
    if (!form.contact_name.trim()) next.contact_name = '请填写联系人';
    if (!PHONE_RE.test(form.phone.trim())) next.phone = '请填写 11 位手机号';
    if (!EMAIL_RE.test(form.email.trim())) next.email = '请填写有效邮箱';
    if (form.password.length < 8 || form.password.length > 64) next.password = '密码长度需为 8–64 位';
    if (!form.city) next.city = '请选择城市';
    if (!form.main_category_id) next.main_category_id = '请选择主营类别';
    if (!agree) next.agree = '请先阅读并勾选广告政策';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const submit = async (event) => {
    event.preventDefault();
    setSubmitError('');
    if (!validate()) return;
    setSubmitting(true);
    try {
      const res = await merchantApi.signup({
        name: form.name.trim(),
        contact_name: form.contact_name.trim(),
        phone: form.phone.trim(),
        email: form.email.trim(),
        password: form.password,
        city: form.city,
        main_category_id: Number(form.main_category_id),
        agree_policy: true,
      });
      const merchant = (res && res.merchant) || res || null;
      auth.applySession('merchant', merchant);
      showToast('注册成功，可以提交第一条广告了', 'success');
      navigate('/merchant/ads', { replace: true });
    } catch (err) {
      if (err.fields && Array.isArray(err.fields)) {
        const mapped = {};
        err.fields.forEach((item) => {
          if (item && item.field) mapped[item.field] = item.message;
        });
        setErrors(mapped);
      }
      setSubmitError(err.message || '注册失败，请稍后重试');
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

      <Box sx={{ flex: 1, display: 'flex', justifyContent: 'center', px: 2, pb: 6 }}>
        <Box
          component="form"
          onSubmit={submit}
          noValidate
          sx={{ width: '100%', maxWidth: 560, bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 2, sm: 3 } }}
        >
          <Typography component="h1" sx={{ fontSize: 22, fontWeight: 700, mb: 0.5 }}>
            商家注册入驻
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 2.5, lineHeight: 1.7 }}>
            注册即可提交广告，无需额外审核商家资质；提交内容需人工审核后公开。
          </Typography>

          {submitError ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {submitError}
            </Alert>
          ) : null}

          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' }, gap: 2 }}>
            <TextField
              label="商家名称 *"
              value={form.name}
              onChange={(event) => setField('name', event.target.value)}
              error={Boolean(errors.name)}
              helperText={errors.name}
              fullWidth
              inputProps={{ maxLength: 60 }}
            />
            <TextField
              label="联系人 *"
              value={form.contact_name}
              onChange={(event) => setField('contact_name', event.target.value)}
              error={Boolean(errors.contact_name)}
              helperText={errors.contact_name}
              fullWidth
              inputProps={{ maxLength: 30 }}
            />
            <TextField
              label="手机号 *"
              value={form.phone}
              onChange={(event) => setField('phone', event.target.value.replace(/\D/g, '').slice(0, 11))}
              error={Boolean(errors.phone)}
              helperText={errors.phone}
              fullWidth
              inputMode="numeric"
            />
            <TextField
              label="邮箱 *"
              value={form.email}
              onChange={(event) => setField('email', event.target.value)}
              error={Boolean(errors.email)}
              helperText={errors.email}
              fullWidth
              type="email"
            />
            <TextField
              label="密码 *"
              type="password"
              value={form.password}
              onChange={(event) => setField('password', event.target.value)}
              error={Boolean(errors.password)}
              helperText={errors.password || '8–64 位，加盐哈希存储'}
              fullWidth
              autoComplete="new-password"
            />
            <TextField
              select
              label="所在城市 *"
              value={form.city}
              onChange={(event) => setField('city', event.target.value)}
              error={Boolean(errors.city)}
              helperText={errors.city}
              fullWidth
            >
              {CITIES.map((city) => (
                <MenuItem key={city} value={city}>
                  {city}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="主营类别 *"
              value={form.main_category_id}
              onChange={(event) => setField('main_category_id', event.target.value)}
              error={Boolean(errors.main_category_id)}
              helperText={errors.main_category_id}
              fullWidth
              sx={{ gridColumn: { sm: 'span 2' } }}
            >
              {categories.map((category) => (
                <MenuItem key={category.id} value={category.id}>
                  {category.name}
                </MenuItem>
              ))}
            </TextField>
          </Box>

          <Box sx={{ mt: 2 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={agree}
                  onChange={(event) => {
                    setAgree(event.target.checked);
                    setErrors((prev) => ({ ...prev, agree: '' }));
                  }}
                />
              }
              label={
                <Typography sx={{ fontSize: 13, color: errors.agree ? '#B3261E' : '#33404F' }}>
                  我已阅读
                  <Link component={RouterLink} to="/policy/ads" sx={{ mx: 0.5, fontSize: 13 }}>
                    《广告政策》
                  </Link>
                  并保证信息真实有效
                </Typography>
              }
              sx={{ alignItems: 'flex-start', ml: 0 }}
            />
          </Box>

          <Button
            type="submit"
            variant="contained"
            fullWidth
            disabled={submitting}
            startIcon={submitting ? <CircularProgress size={14} sx={{ color: '#fff' }} /> : null}
            sx={{ mt: 2, bgcolor: '#1F3A5F', '&:hover': { bgcolor: '#17304F' }, height: 46 }}
          >
            {submitting ? '提交中…' : '注册并入驻'}
          </Button>

          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Typography sx={{ fontSize: 13, color: '#5A6472' }}>
              已有账号？
              <Link component={RouterLink} to="/merchant/login" sx={{ ml: 0.5, fontSize: 13, fontWeight: 600 }}>
                去登录
              </Link>
            </Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
