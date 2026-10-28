import React, { useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Divider from '@mui/material/Divider';
import { useAuth } from '../../context/AuthContext.jsx';
import { useCategories } from '../../context/CategoriesContext.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import * as merchantApi from '../../api/merchant.js';
import { CITIES } from '../../constants/cities.js';
import { formatMonthCN } from '../../utils/format.js';

const PHONE_RE = /^1[3-9]\d{9}$/;

/** 商家资料与改密码（PRD 5.2） */
export default function MerchantProfilePage() {
  const { me, refreshMe } = useAuth();
  const { showToast } = useToast();
  const { categories } = useCategories();

  const [form, setForm] = useState({ contact_name: '', phone: '', city: '全国', main_category_id: '' });
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const [pwd, setPwd] = useState({ old_password: '', new_password: '', confirm: '' });
  const [pwdErrors, setPwdErrors] = useState({});
  const [changing, setChanging] = useState(false);

  useEffect(() => {
    if (!me) return;
    setForm({
      contact_name: me.contact_name || '',
      phone: me.phone || '',
      city: me.city || '全国',
      main_category_id: (me.main_category && me.main_category.id) || me.main_category_id || '',
    });
  }, [me]);

  const setField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [key]: '' }));
  };

  const saveProfile = async (event) => {
    event.preventDefault();
    const next = {};
    if (!form.contact_name.trim()) next.contact_name = '请填写联系人';
    if (!PHONE_RE.test(form.phone.trim())) next.phone = '请填写 11 位手机号';
    setErrors(next);
    if (Object.keys(next).length > 0) return;

    setSaving(true);
    try {
      await merchantApi.updateMe({
        contact_name: form.contact_name.trim(),
        phone: form.phone.trim(),
        city: form.city,
        main_category_id: form.main_category_id ? Number(form.main_category_id) : undefined,
      });
      showToast('资料已保存', 'success');
      refreshMe();
    } catch (err) {
      showToast(err.message || '保存失败，请稍后重试', 'error');
    } finally {
      setSaving(false);
    }
  };

  const changePassword = async (event) => {
    event.preventDefault();
    const next = {};
    if (!pwd.old_password) next.old_password = '请输入原密码';
    if (pwd.new_password.length < 8 || pwd.new_password.length > 64) next.new_password = '新密码长度需为 8–64 位';
    if (pwd.new_password !== pwd.confirm) next.confirm = '两次输入的新密码不一致';
    setPwdErrors(next);
    if (Object.keys(next).length > 0) return;

    setChanging(true);
    try {
      await merchantApi.changePassword({ old_password: pwd.old_password, new_password: pwd.new_password });
      setPwd({ old_password: '', new_password: '', confirm: '' });
      showToast('密码已更新', 'success');
    } catch (err) {
      showToast(err.message || '修改失败，请稍后重试', 'error');
    } finally {
      setChanging(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 720 }}>
      <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700, mb: 0.5 }}>
        商家资料
      </Typography>
      <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 2 }}>
        商家名与登录账号不可自行修改，如需变更请联系运营者。
      </Typography>

      <Box
        component="form"
        onSubmit={saveProfile}
        sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 2, sm: 2.5 }, mb: 2 }}
      >
        <Typography component="h2" sx={{ fontSize: 16, fontWeight: 700, mb: 2 }}>
          基本信息
        </Typography>

        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' }, gap: 2 }}>
          <TextField label="商家名称" value={(me && me.name) || ''} fullWidth disabled />
          <TextField label="邮箱（登录账号）" value={(me && me.email) || ''} fullWidth disabled />
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
          <TextField select label="所在城市" value={form.city} onChange={(event) => setField('city', event.target.value)} fullWidth>
            {CITIES.map((city) => (
              <MenuItem key={city} value={city}>
                {city}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="主营类别"
            value={form.main_category_id}
            onChange={(event) => setField('main_category_id', event.target.value)}
            fullWidth
          >
            {categories.map((item) => (
              <MenuItem key={item.id} value={item.id}>
                {item.name}
              </MenuItem>
            ))}
          </TextField>
        </Box>

        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mt: 2, alignItems: 'center' }}>
          <Typography sx={{ fontSize: 13, color: '#5A6472' }}>
            入驻时间：{me && me.created_at ? formatMonthCN(me.created_at) : '—'}
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472' }}>
            账号状态：{me && me.status === 'disabled' ? '已停用' : '正常'}
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472' }}>
            资质核验：{me && me.verified ? '已核验' : '未核验'}
          </Typography>
        </Box>

        <Button type="submit" variant="contained" disabled={saving} sx={{ mt: 2, bgcolor: '#1F3A5F', '&:hover': { bgcolor: '#17304F' } }}>
          {saving ? '保存中…' : '保存资料'}
        </Button>
      </Box>

      <Box
        component="form"
        onSubmit={changePassword}
        sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 2, sm: 2.5 } }}
      >
        <Typography component="h2" sx={{ fontSize: 16, fontWeight: 700, mb: 0.5 }}>
          修改密码
        </Typography>
        <Typography sx={{ fontSize: 12, color: '#8A8F98', mb: 2 }}>
          密码以加盐慢哈希存储，平台无法查看你的原密码；忘记密码请联系运营者。
        </Typography>

        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, minmax(0, 1fr))' }, gap: 2 }}>
          <TextField
            label="原密码"
            type="password"
            value={pwd.old_password}
            onChange={(event) => {
              setPwd((prev) => ({ ...prev, old_password: event.target.value }));
              setPwdErrors((prev) => ({ ...prev, old_password: '' }));
            }}
            error={Boolean(pwdErrors.old_password)}
            helperText={pwdErrors.old_password}
            fullWidth
            autoComplete="current-password"
          />
          <TextField
            label="新密码"
            type="password"
            value={pwd.new_password}
            onChange={(event) => {
              setPwd((prev) => ({ ...prev, new_password: event.target.value }));
              setPwdErrors((prev) => ({ ...prev, new_password: '' }));
            }}
            error={Boolean(pwdErrors.new_password)}
            helperText={pwdErrors.new_password || '8–64 位'}
            fullWidth
            autoComplete="new-password"
          />
          <TextField
            label="确认新密码"
            type="password"
            value={pwd.confirm}
            onChange={(event) => {
              setPwd((prev) => ({ ...prev, confirm: event.target.value }));
              setPwdErrors((prev) => ({ ...prev, confirm: '' }));
            }}
            error={Boolean(pwdErrors.confirm)}
            helperText={pwdErrors.confirm}
            fullWidth
            autoComplete="new-password"
          />
        </Box>

        <Divider sx={{ my: 2 }} />
        <Button type="submit" variant="outlined" disabled={changing} sx={{ borderColor: '#C9D2DD', color: '#1F3A5F' }}>
          {changing ? '提交中…' : '更新密码'}
        </Button>
      </Box>

      <Alert severity="info" sx={{ mt: 2, fontSize: 12 }}>
        提示：修改手机号后请用新手机号登录；如账号被停用，你的在架广告已被批量下架，需联系运营者处理。
      </Alert>
    </Box>
  );
}
