import React, { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Skeleton from '@mui/material/Skeleton';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import StatusChip from '../../components/StatusChip.jsx';
import { IconPlus, IconRefresh } from '../../components/icons.jsx';
import * as adminApi from '../../api/admin.js';
import useApi from '../../hooks/useApi.js';
import { useToast } from '../../context/ToastContext.jsx';
import { useCategories } from '../../context/CategoriesContext.jsx';
import { COMMON } from '../../constants/messages.js';

/**
 * 分类与标签维护（P1-O-01）。
 * 6 个一级类别只读；二级标签可新增 / 改名 / 调整排序 / 停用（停用后不进新建表单与筛选项）。
 */
export default function AdminCategoriesPage() {
  const { showToast } = useToast();
  const { reload: reloadPublicCategories } = useCategories();

  const { data, loading, error, reload } = useApi(() => adminApi.getCategories(), []);
  const categories = Array.isArray(data) ? data : [];

  const [editTarget, setEditTarget] = useState(null);
  const [editForm, setEditForm] = useState({ name: '', sort_order: 0 });
  const [createFor, setCreateFor] = useState(null);
  const [createForm, setCreateForm] = useState({ name: '', sort_order: 0 });
  const [busy, setBusy] = useState(false);

  const afterChange = () => {
    reload();
    reloadPublicCategories();
  };

  const openEdit = (category, tag) => {
    setEditTarget({ category, tag });
    setEditForm({ name: tag.name, sort_order: Number(tag.sort_order) || 0 });
  };

  const submitEdit = async () => {
    if (!editTarget) return;
    if (!editForm.name.trim()) {
      showToast('标签名不能为空', 'warning');
      return;
    }
    setBusy(true);
    try {
      await adminApi.patchTag(editTarget.tag.id, {
        name: editForm.name.trim(),
        sort_order: Number(editForm.sort_order) || 0,
      });
      showToast('标签已更新', 'success');
      setEditTarget(null);
      afterChange();
    } catch (err) {
      showToast(err.message || '更新失败，请稍后重试', 'error');
    } finally {
      setBusy(false);
    }
  };

  const toggleTag = async (category, tag) => {
    setBusy(true);
    try {
      await adminApi.patchTag(tag.id, { is_active: !tag.is_active });
      showToast(tag.is_active ? '标签已停用（已发布广告不受影响）' : '标签已启用', 'success');
      afterChange();
    } catch (err) {
      showToast(err.message || '操作失败，请稍后重试', 'error');
    } finally {
      setBusy(false);
    }
  };

  const submitCreate = async () => {
    if (!createFor) return;
    if (!createForm.name.trim()) {
      showToast('请填写标签名', 'warning');
      return;
    }
    setBusy(true);
    try {
      await adminApi.createTag(createFor.id, {
        name: createForm.name.trim(),
        sort_order: Number(createForm.sort_order) || 0,
      });
      showToast('标签已新增', 'success');
      setCreateFor(null);
      setCreateForm({ name: '', sort_order: 0 });
      afterChange();
    } catch (err) {
      showToast(err.message || '新增失败，请稍后重试', 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
        <Box>
          <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700 }}>
            分类与标签
          </Typography>
          <Typography sx={{ fontSize: 13, color: '#5A6472', mt: 0.5 }}>
            一级类别固定 6 个（只读）；二级标签可维护，停用后仅不再出现在新建表单与筛选项。
          </Typography>
        </Box>
        <Button size="small" startIcon={<IconRefresh size={15} />} onClick={reload} sx={{ color: '#5A6472' }}>
          刷新
        </Button>
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
          {error.message || '分类加载失败'}
        </Alert>
      ) : null}

      {loading && categories.length === 0 ? <Skeleton variant="rounded" height={320} /> : null}

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: 'repeat(2, minmax(0, 1fr))' }, gap: 1.5 }}>
        {categories.map((category) => {
          const tags = Array.isArray(category.tags) ? category.tags : [];
          return (
            <Box key={category.id} sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 1.75, sm: 2 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, mb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                  <Typography sx={{ fontSize: 15, fontWeight: 700 }}>{category.name}</Typography>
                  <StatusChip status="draft" label={category.slug} />
                  <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>{tags.length} 个标签</Typography>
                </Box>
                <Button
                  size="small"
                  startIcon={<IconPlus size={14} />}
                  onClick={() => {
                    setCreateFor(category);
                    setCreateForm({ name: '', sort_order: tags.length + 1 });
                  }}
                  sx={{ fontSize: 12, color: '#1F3A5F' }}
                >
                  新增标签
                </Button>
              </Box>

              {tags.length === 0 ? (
                <Box sx={{ py: 2, textAlign: 'center' }}>
                  <Typography sx={{ fontSize: 13, color: '#5A6472' }}>该类别暂无二级标签</Typography>
                  <Typography sx={{ fontSize: 12, color: '#8A8F98', mt: 0.25 }}>可在右上角新增</Typography>
                </Box>
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                  {tags.map((tag) => (
                    <Box
                      key={tag.id}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        py: 0.875,
                        borderTop: '1px solid #F0F2F5',
                        flexWrap: 'wrap',
                      }}
                    >
                      <Typography sx={{ fontSize: 13, fontWeight: 600, color: tag.is_active === false ? '#A7AEB8' : '#1A1A1A' }}>
                        {tag.name}
                      </Typography>
                      <Typography sx={{ fontSize: 12, color: '#A7AEB8' }}>{tag.slug}</Typography>
                      <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>排序 {tag.sort_order ?? 0}</Typography>
                      <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>广告 {tag.ad_count ?? 0}</Typography>
                      {tag.is_active === false ? <StatusChip status="offline" label="已停用" /> : null}
                      <Box sx={{ flex: 1 }} />
                      <Button size="small" onClick={() => openEdit(category, tag)} sx={{ fontSize: 12, minWidth: 0 }}>
                        改名/排序
                      </Button>
                      <Button
                        size="small"
                        disabled={busy}
                        onClick={() => toggleTag(category, tag)}
                        sx={{ fontSize: 12, minWidth: 0, color: tag.is_active === false ? '#1E7A46' : '#B3261E' }}
                      >
                        {tag.is_active === false ? '启用' : '停用'}
                      </Button>
                    </Box>
                  ))}
                </Box>
              )}
            </Box>
          );
        })}
      </Box>

      {/* 编辑标签 */}
      <Dialog open={Boolean(editTarget)} onClose={() => setEditTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontSize: 17, fontWeight: 700 }}>
          编辑标签{editTarget ? `：${editTarget.category.name}` : ''}
        </DialogTitle>
        <DialogContent>
          <TextField
            label="标签名"
            value={editForm.name}
            onChange={(event) => setEditForm((prev) => ({ ...prev, name: event.target.value.slice(0, 20) }))}
            fullWidth
            sx={{ mt: 0.5, mb: 2 }}
            helperText="≤20 字；同一类别内不可重名"
          />
          <TextField
            label="排序（越小越靠前）"
            type="number"
            value={editForm.sort_order}
            onChange={(event) => setEditForm((prev) => ({ ...prev, sort_order: event.target.value }))}
            fullWidth
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setEditTarget(null)} color="inherit" sx={{ color: '#5A6472' }}>
            取消
          </Button>
          <Button variant="contained" onClick={submitEdit} disabled={busy} sx={{ bgcolor: '#1F3A5F' }}>
            保存
          </Button>
        </DialogActions>
      </Dialog>

      {/* 新增标签 */}
      <Dialog open={Boolean(createFor)} onClose={() => setCreateFor(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontSize: 17, fontWeight: 700 }}>
          新增标签{createFor ? `：${createFor.name}` : ''}
        </DialogTitle>
        <DialogContent>
          <TextField
            label="标签名"
            value={createForm.name}
            onChange={(event) => setCreateForm((prev) => ({ ...prev, name: event.target.value.slice(0, 20) }))}
            fullWidth
            sx={{ mt: 0.5, mb: 2 }}
            helperText="≤20 字；新增后立即出现在商家提交表单"
          />
          <TextField
            label="排序（越小越靠前）"
            type="number"
            value={createForm.sort_order}
            onChange={(event) => setCreateForm((prev) => ({ ...prev, sort_order: event.target.value }))}
            fullWidth
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setCreateFor(null)} color="inherit" sx={{ color: '#5A6472' }}>
            取消
          </Button>
          <Button variant="contained" onClick={submitCreate} disabled={busy} sx={{ bgcolor: '#1F3A5F' }}>
            新增
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
