import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Divider from '@mui/material/Divider';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import EmptyState from '../components/EmptyState.jsx';
import { IconEye, IconEyeOff, IconTrash } from '../components/icons.jsx';
import { CITIES } from '../constants/cities.js';
import { getHides, removeHide } from '../api/visitor.js';
import useApi from '../hooks/useApi.js';
import { useVisitor } from '../context/VisitorContext.jsx';
import { useCategories } from '../context/CategoriesContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { COMMON, EMPTY } from '../constants/messages.js';

/**
 * 偏好设置（P0-U-02 / P0-U-03 / P0-U-07）。
 * 感兴趣类别多选（可全不选）、常看城市、已隐藏列表（可恢复）、清除全部偏好（二次确认）。
 */
export default function PreferencesPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { categories, loading: categoriesLoading } = useCategories();
  const { preferences, hides, savePreferences, clearAll, refresh } = useVisitor();

  const [selectedCategories, setSelectedCategories] = useState([]);
  const [city, setCity] = useState('');
  const [saving, setSaving] = useState(false);
  const [clearOpen, setClearOpen] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [hiddenItems, setHiddenItems] = useState([]);

  const hidesApi = useApi(() => getHides({ page: 1 }), []);

  useEffect(() => {
    setSelectedCategories(Array.isArray(preferences.categories) ? preferences.categories.map(Number) : []);
    setCity(preferences.city || '');
  }, [preferences.categories, preferences.city]);

  useEffect(() => {
    if (!hidesApi.data) return;
    const list = Array.isArray(hidesApi.data.items) ? hidesApi.data.items : [];
    setHiddenItems(list);
  }, [hidesApi.data]);

  const dirty = useMemo(() => {
    const original = [...(preferences.categories || [])].map(Number).sort();
    const current = [...selectedCategories].sort();
    const sameCategories = original.length === current.length && original.every((item, index) => item === current[index]);
    return !sameCategories || (preferences.city || '') !== (city || '');
  }, [preferences, selectedCategories, city]);

  const toggleCategory = (id) => {
    setSelectedCategories((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]));
  };

  const handleSave = async () => {
    setSaving(true);
    const ok = await savePreferences({ categories: selectedCategories, city });
    setSaving(false);
    if (ok) setSelectedCategories([...selectedCategories]);
  };

  const handleUnhide = async (adId) => {
    const ok = await removeHide(Number(adId)).then(
      () => true,
      (err) => {
        showToast(err.message || '恢复失败，请稍后重试', 'error');
        return false;
      },
    );
    if (!ok) return;
    setHiddenItems((prev) => prev.filter((item) => Number(item.id) !== Number(adId)));
    refresh();
    showToast('已恢复显示', 'success');
  };

  const handleClearAll = async () => {
    setClearing(true);
    const ok = await clearAll();
    setClearing(false);
    setClearOpen(false);
    if (ok) {
      setSelectedCategories([]);
      setCity('');
      setHiddenItems([]);
      hidesApi.reload();
    }
  };

  const hiddenCount = hiddenItems.length || hides.size;

  return (
    <Box sx={{ maxWidth: 880, mx: 'auto' }}>
      <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700, mb: 0.5 }}>
        偏好设置
      </Typography>
      <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 2.5, lineHeight: 1.7 }}>
        偏好仅保存在本设备（匿名 Cookie），用于让首页优先展示你感兴趣的类别。全不选 = 关闭个性化，按最新发布展示。
      </Typography>

      {!categoriesLoading && selectedCategories.length === 0 ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          {EMPTY.preferencesEmpty.title}。{EMPTY.preferencesEmpty.desc}
        </Alert>
      ) : null}

      {/* 感兴趣类别 */}
      <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 2, sm: 2.5 }, mb: 2 }}>
        <Typography component="h2" sx={{ fontSize: 16, fontWeight: 700, mb: 0.5 }}>
          感兴趣的类别
        </Typography>
        <Typography sx={{ fontSize: 12, color: '#8A8F98', mb: 1.5 }}>可多选，也可全不选</Typography>

        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' },
            gap: 0.5,
          }}
        >
          {categories.map((category) => (
            <FormControlLabel
              key={category.id}
              control={
                <Checkbox
                  size="small"
                  checked={selectedCategories.includes(Number(category.id))}
                  onChange={() => toggleCategory(Number(category.id))}
                />
              }
              label={
                <Box sx={{ fontSize: 14 }}>
                  {category.name}
                  <Box component="span" sx={{ fontSize: 12, color: '#8A8F98', ml: 0.75 }}>
                    在架 {Number(category.active_count) || 0} 条
                  </Box>
                </Box>
              }
              sx={{ ml: 0 }}
            />
          ))}
        </Box>

        <Divider sx={{ my: 2 }} />

        <Typography component="h3" sx={{ fontSize: 14, fontWeight: 700, mb: 1 }}>
          常看城市
        </Typography>
        <Select
          value={city}
          onChange={(event) => setCity(event.target.value)}
          displayEmpty
          size="small"
          aria-label="常看城市"
          sx={{ minWidth: 180, fontSize: 14, bgcolor: '#fff' }}
        >
          <MenuItem value="" sx={{ fontSize: 14 }}>
            不限城市
          </MenuItem>
          {CITIES.map((item) => (
            <MenuItem key={item} value={item} sx={{ fontSize: 14 }}>
              {item}
            </MenuItem>
          ))}
        </Select>

        <Box sx={{ display: 'flex', gap: 1, mt: 2.5, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={saving || !dirty}
            sx={{ bgcolor: '#1F3A5F', '&:hover': { bgcolor: '#17304F' } }}
          >
            {saving ? '保存中…' : dirty ? '保存偏好' : '已保存'}
          </Button>
          <Button
            variant="outlined"
            onClick={() => {
              setSelectedCategories([]);
              setCity('');
            }}
            sx={{ borderColor: '#C9D2DD', color: '#5A6472' }}
          >
            清空勾选（不保存）
          </Button>
        </Box>
      </Box>

      {/* 已隐藏 */}
      <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 2, sm: 2.5 }, mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
          <Box sx={{ color: '#5A6472', display: 'flex' }} aria-hidden="true">
            <IconEyeOff size={17} />
          </Box>
          <Typography component="h2" sx={{ fontSize: 16, fontWeight: 700 }}>
            已隐藏的广告（{hiddenCount}）
          </Typography>
        </Box>
        <Typography sx={{ fontSize: 12, color: '#8A8F98', mb: 1.5 }}>
          隐藏的广告不会再出现在列表中，恢复后立即重新可见
        </Typography>

        {hidesApi.error ? (
          <Alert
            severity="error"
            action={
              <Button color="inherit" size="small" onClick={hidesApi.reload}>
                {COMMON.retry}
              </Button>
            }
          >
            {hidesApi.error.message || '隐藏列表加载失败'}
          </Alert>
        ) : null}

        {!hidesApi.loading && hiddenItems.length === 0 ? (
          <Box sx={{ py: 2, textAlign: 'center' }}>
            <Typography sx={{ fontSize: 14, fontWeight: 600, color: '#33404F' }}>{EMPTY.hidesEmpty.title}</Typography>
            <Typography sx={{ fontSize: 13, color: '#8A8F98', mt: 0.5 }}>{EMPTY.hidesEmpty.desc}</Typography>
          </Box>
        ) : null}

        {hiddenItems.length > 0 ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {hiddenItems.map((ad) => (
              <Box
                key={ad.id}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                  p: 1.25,
                  border: '1px solid #E2E6EC',
                  borderRadius: 2,
                  bgcolor: '#FBFCFD',
                }}
              >
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography className="adx-clamp-1" sx={{ fontSize: 14, fontWeight: 600 }}>
                    {ad.title || '未命名广告'}
                  </Typography>
                  <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>
                    {ad.merchant_name || '商家未提供'}
                    {ad.is_expired ? ' · 已结束' : ''}
                  </Typography>
                </Box>
                <Button
                  size="small"
                  startIcon={<IconEye size={15} />}
                  onClick={() => handleUnhide(ad.id)}
                  sx={{ fontSize: 13, color: '#1F3A5F' }}
                >
                  恢复显示
                </Button>
              </Box>
            ))}
          </Box>
        ) : null}
      </Box>

      {/* 清除全部 */}
      <Box
        sx={{
          bgcolor: '#FFFFFF',
          border: '1px solid #F0D6D4',
          borderRadius: '12px',
          p: { xs: 2, sm: 2.5 },
        }}
      >
        <Typography component="h2" sx={{ fontSize: 16, fontWeight: 700, mb: 0.5 }}>
          删除我的本站数据
        </Typography>
        <Typography sx={{ fontSize: 13, color: '#5A6472', mb: 1.5, lineHeight: 1.7 }}>
          一次清空本设备的收藏、隐藏记录与偏好设置。举报记录会保留以完成处理，但不再关联你。此操作不可撤销。
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button
            variant="outlined"
            color="error"
            startIcon={<IconTrash size={16} />}
            onClick={() => setClearOpen(true)}
            sx={{ borderColor: '#B3261E', color: '#B3261E' }}
          >
            清除全部偏好
          </Button>
          <Button variant="text" onClick={() => navigate('/policy/privacy')} sx={{ color: '#1F3A5F' }}>
            查看隐私说明
          </Button>
        </Box>
      </Box>

      <ConfirmDialog
        open={clearOpen}
        title="清除全部偏好与收藏？"
        description="将删除本设备的收藏、隐藏记录与偏好设置，操作不可撤销。举报记录保留但会去除你的标识。"
        confirmText="确认清除"
        danger
        loading={clearing}
        onConfirm={handleClearAll}
        onClose={() => setClearOpen(false)}
      />
    </Box>
  );
}
