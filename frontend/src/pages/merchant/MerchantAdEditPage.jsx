import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import CircularProgress from '@mui/material/CircularProgress';
import Divider from '@mui/material/Divider';
import FormControlLabel from '@mui/material/FormControlLabel';
import Link from '@mui/material/Link';
import MenuItem from '@mui/material/MenuItem';
import Skeleton from '@mui/material/Skeleton';
import Step from '@mui/material/Step';
import StepButton from '@mui/material/StepButton';
import Stepper from '@mui/material/Stepper';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { Link as RouterLink } from 'react-router-dom';
import AdCard from '../../components/AdCard.jsx';
import StatusChip from '../../components/StatusChip.jsx';
import { IconUpload } from '../../components/icons.jsx';
import * as merchantApi from '../../api/merchant.js';
import useApi from '../../hooks/useApi.js';
import { useCategories } from '../../context/CategoriesContext.jsx';
import { useAuth } from '../../context/AuthContext.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { CITIES } from '../../constants/cities.js';
import { AD_STATUS } from '../../constants/enums.js';
import {
  SUBMIT_BANNER,
  SUBMIT_EDIT_ACTIVE_HINT,
  SUBMIT_PENDING_HINT,
  SUBMIT_POLICY_CHECK,
} from '../../constants/messages.js';
import { formatRangeCN } from '../../utils/format.js';

const STEPS = ['基本信息', '分类', '优惠与有效期', '落地页与素材', '预览确认'];
const STEP_FIELDS = [
  ['title', 'description'],
  ['category_id', 'tag_ids', 'city'],
  ['price_text', 'promo_condition', 'restriction', 'valid_from', 'valid_to'],
  ['landing_url', 'image_path'],
  ['agree'],
];

const MAX_IMAGE_BYTES = 2 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const DANGEROUS_SUFFIX = /\.(exe|msi|apk|dmg|bat|cmd|scr|vbs|jar|zip|rar|7z|js)$/i;

const EMPTY_FORM = {
  title: '',
  description: '',
  category_id: '',
  tag_ids: [],
  city: '全国',
  price_text: '',
  promo_condition: '',
  restriction: '',
  valid_from: '',
  valid_to: '',
  landing_url: '',
  image_path: '',
};

/** 广告实体 → 表单值（兼容后端返回的 local_date 字段） */
function mapAdToForm(ad) {
  if (!ad) return { ...EMPTY_FORM };
  const tags = Array.isArray(ad.tags) ? ad.tags : [];
  return {
    title: ad.title || '',
    description: ad.description || '',
    category_id: ad.category_id || (ad.category && ad.category.id) || '',
    tag_ids: tags.map((tag) => Number(tag.id)).filter((id) => Number.isFinite(id)),
    city: ad.city || '全国',
    price_text: ad.price_text || '',
    promo_condition: ad.promo_condition || '',
    restriction: ad.restriction || '',
    valid_from: ad.valid_from_local_date || (ad.valid_from ? String(ad.valid_from).slice(0, 10) : ''),
    valid_to: ad.valid_to_local_date || (ad.valid_to ? String(ad.valid_to).slice(0, 10) : ''),
    landing_url: ad.landing_url || '',
    image_path: ad.image_path || '',
  };
}

/** 天数差（同一 YYYY-MM-DD 格式，纯本地计算，不涉及时区） */
function dayDiff(from, to) {
  const start = new Date(`${from}T00:00:00`).getTime();
  const end = new Date(`${to}T00:00:00`).getTime();
  if (Number.isNaN(start) || Number.isNaN(end)) return NaN;
  return Math.round((end - start) / 86400000);
}

/**
 * 提交 / 编辑广告（P0-M-02 / P0-M-05，PRD §9.4 五步表单）。
 * 逐步校验 + 右侧实时预览（AdCard preview 模式）+ 顶部错误汇总 + 字段级红字定位。
 */
export default function MerchantAdEditPage({ mode = 'create' }) {
  const { id = '' } = useParams();
  const isEdit = mode === 'edit';
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { categories } = useCategories();
  const { me } = useAuth();

  const [step, setStep] = useState(0);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [errors, setErrors] = useState({});
  const [agree, setAgree] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [originalAd, setOriginalAd] = useState(null);
  const fileInputRef = useRef(null);

  const adApi = useApi(() => merchantApi.getAd(id), [id], { enabled: isEdit && Boolean(id) });

  useEffect(() => {
    if (!adApi.data) return;
    const ad = (adApi.data && adApi.data.ad) || adApi.data;
    setOriginalAd(ad);
    setForm(mapAdToForm(ad));
  }, [adApi.data]);

  const category = useMemo(
    () => categories.find((item) => Number(item.id) === Number(form.category_id)) || null,
    [categories, form.category_id],
  );

  const tags = Array.isArray(category && category.tags) ? category.tags : [];

  const setField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [key]: '' }));
  };

  const toggleTag = (tagId) => {
    setForm((prev) => {
      const exists = prev.tag_ids.includes(tagId);
      const next = exists ? prev.tag_ids.filter((item) => item !== tagId) : [...prev.tag_ids, tagId];
      return { ...prev, tag_ids: next.slice(0, 3) };
    });
    setErrors((prev) => ({ ...prev, tag_ids: '' }));
  };

  // 换类别时清空跨类别标签（P0-C-03：跨类别标签不可选）
  const changeCategory = (categoryId) => {
    setForm((prev) => ({ ...prev, category_id: categoryId, tag_ids: [] }));
    setErrors((prev) => ({ ...prev, category_id: '', tag_ids: '' }));
  };

  const validate = () => {
    const next = {};

    if (!form.title.trim()) next.title = '请填写标题';
    else if (form.title.trim().length > 40) next.title = '标题不能超过 40 字';

    if (!form.description.trim()) next.description = '请填写描述';
    else if (form.description.trim().length > 500) next.description = '描述不能超过 500 字';

    if (!form.category_id) next.category_id = '请选择一个一级类别';

    if (form.tag_ids.length === 0) next.tag_ids = '请至少选择 1 个二级标签';
    else if (form.tag_ids.length > 3) next.tag_ids = '二级标签最多选择 3 个';

    if (!form.city) next.city = '请选择服务城市';

    if (!form.price_text.trim()) next.price_text = '请填写价格文案';
    else if (form.price_text.trim().length > 30) next.price_text = '价格文案不能超过 30 字';

    if (form.promo_condition.length > 100) next.promo_condition = '优惠条件不能超过 100 字';
    if (form.restriction.length > 200) next.restriction = '限制条款不能超过 200 字';

    if (!form.valid_from) next.valid_from = '请选择有效期开始日期';
    if (!form.valid_to) next.valid_to = '请选择有效期结束日期（必须填写，属透明度要求）';

    if (form.valid_from && form.valid_to) {
      const diff = dayDiff(form.valid_from, form.valid_to);
      if (Number.isNaN(diff)) {
        next.valid_to = '日期格式不正确';
      } else if (diff < 0) {
        next.valid_to = '结束日期必须晚于开始日期';
      } else if (diff > 90) {
        next.valid_to = '单条广告有效期不能超过 90 天';
      }
    }

    if (!form.landing_url.trim()) {
      next.landing_url = '请填写落地页 URL';
    } else if (!/^https?:\/\//i.test(form.landing_url.trim())) {
      next.landing_url = '落地页必须以 http:// 或 https:// 开头';
    } else if (DANGEROUS_SUFFIX.test(form.landing_url.trim())) {
      next.landing_url = '落地页不得指向可执行文件或压缩包';
    }

    if (!agree) next.agree = '请阅读并勾选广告政策后再提交审核';

    return next;
  };

  const firstStepWithError = (errorMap) => {
    for (let index = 0; index < STEP_FIELDS.length; index += 1) {
      const hit = STEP_FIELDS[index].some((field) => errorMap[field]);
      if (hit) return index;
    }
    return 0;
  };

  const buildPayload = () => ({
    title: form.title.trim(),
    description: form.description.trim(),
    category_id: Number(form.category_id),
    tag_ids: form.tag_ids.map(Number),
    city: form.city,
    price_text: form.price_text.trim(),
    promo_condition: form.promo_condition.trim(),
    restriction: form.restriction.trim(),
    valid_from: form.valid_from,
    valid_to: form.valid_to,
    landing_url: form.landing_url.trim(),
    image_path: form.image_path || null,
  });

  const handleSave = async (submitNow) => {
    setSubmitError('');
    const errorMap = submitNow ? validate() : {};

    if (submitNow && Object.keys(errorMap).length > 0) {
      setErrors(errorMap);
      setStep(firstStepWithError(errorMap));
      setSubmitError(`还有 ${Object.keys(errorMap).length} 项需要修改`);
      return;
    }

    setSubmitting(true);
    try {
      if (isEdit) {
        const res = await merchantApi.updateAd(id, buildPayload());
        if (submitNow) {
          await merchantApi.submitAd(id);
        }
        const becamePending = res && res.became_pending;
        if (submitNow) {
          showToast(SUBMIT_PENDING_HINT, 'success');
        } else if (becamePending) {
          showToast(SUBMIT_EDIT_ACTIVE_HINT, 'warning');
        } else {
          showToast('已保存', 'success');
        }
      } else {
        await merchantApi.createAd({ ...buildPayload(), submit: submitNow });
        showToast(
          submitNow ? SUBMIT_PENDING_HINT : '已保存草稿，可稍后继续填写',
          submitNow ? 'success' : 'info',
        );
      }
      navigate('/merchant/ads');
    } catch (err) {
      if (err.fields && Array.isArray(err.fields)) {
        const mapped = {};
        err.fields.forEach((item) => {
          if (item && item.field) mapped[item.field] = item.message;
        });
        setErrors(mapped);
        setStep(firstStepWithError(mapped));
      }
      setSubmitError(err.message || '保存失败，请稍后重试');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpload = async (event) => {
    const file = event.target.files && event.target.files[0];
    event.target.value = '';
    if (!file) return;
    if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
      setErrors((prev) => ({ ...prev, image_path: '仅支持 jpg / png / webp 图片' }));
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setErrors((prev) => ({ ...prev, image_path: '图片不能超过 2MB' }));
      return;
    }
    setUploading(true);
    setErrors((prev) => ({ ...prev, image_path: '' }));
    try {
      const res = await merchantApi.uploadImage(file);
      const path = (res && res.image_path) || '';
      setField('image_path', path);
      showToast('图片已上传', 'success');
    } catch (err) {
      setErrors((prev) => ({ ...prev, image_path: err.message || '上传失败，请重试' }));
    } finally {
      setUploading(false);
    }
  };

  const previewAd = useMemo(
    () => ({
      id: 0,
      title: form.title || '标题会显示在这里',
      price_text: form.price_text || '价格文案',
      merchant_name: (me && me.name) || '你的商家名',
      city: form.city || '全国',
      valid_to_local_date: form.valid_to || null,
      expiring_soon: false,
      image_path: form.image_path || '',
      category_slug: category ? category.slug : '',
      status: 'draft',
    }),
    [form, me, category],
  );

  const errorCount = Object.keys(errors).filter((key) => errors[key]).length;

  if (isEdit && adApi.loading) {
    return (
      <Box>
        <Skeleton height={40} width="60%" sx={{ mb: 2 }} />
        <Skeleton variant="rounded" height={420} />
      </Box>
    );
  }

  if (isEdit && adApi.error) {
    return (
      <Alert
        severity="error"
        action={
          <Button color="inherit" size="small" onClick={adApi.reload}>
            重试
          </Button>
        }
      >
        {adApi.error.message || '广告加载失败（可能不属于你的账号）'}
      </Alert>
    );
  }

  const status = originalAd ? originalAd.status : 'draft';
  const isActive = status === 'active' || status === 'scheduled';

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap', mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Typography component="h1" sx={{ fontSize: { xs: 20, sm: 24 }, fontWeight: 700 }}>
            {isEdit ? '编辑广告' : '新建广告'}
          </Typography>
          {originalAd ? <StatusChip status={status} /> : null}
        </Box>
        <Button size="small" onClick={() => navigate('/merchant/ads')} sx={{ color: '#5A6472' }}>
          返回我的广告
        </Button>
      </Box>

      <Alert severity="info" icon={false} sx={{ mb: 2, bgcolor: '#FFF4E8', color: '#8A3B00', border: '1px solid #FFD8B2' }}>
        <Typography sx={{ fontSize: 13, fontWeight: 700 }}>{SUBMIT_BANNER}</Typography>
        {isActive ? (
          <Typography sx={{ fontSize: 12, mt: 0.5 }}>{SUBMIT_EDIT_ACTIVE_HINT}</Typography>
        ) : null}
      </Alert>

      {submitError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {submitError}
        </Alert>
      ) : null}

      <Box sx={{ borderBottom: '1px solid #E2E6EC', mb: 2, overflowX: 'auto' }}>
        <Stepper nonLinear activeStep={step} sx={{ minWidth: 560, pb: 1 }}>
          {STEPS.map((label, index) => (
            <Step key={label} completed={false}>
              <StepButton onClick={() => setStep(index)}>
                {`${index + 1} ${label}`}
              </StepButton>
            </Step>
          ))}
        </Stepper>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 320px' }, gap: 2.5, alignItems: 'start' }}>
        <Box sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 2, sm: 2.5 } }}>
          {step === 0 ? (
            <Box>
              <Typography component="h2" sx={{ fontSize: 16, fontWeight: 700, mb: 2 }}>
                ① 基本信息
              </Typography>
              <TextField
                label="标题 *"
                value={form.title}
                onChange={(event) => setField('title', event.target.value.slice(0, 40))}
                error={Boolean(errors.title)}
                helperText={errors.title || `${form.title.length}/40`}
                fullWidth
                sx={{ mb: 2 }}
              />
              <TextField
                label="描述 *"
                value={form.description}
                onChange={(event) => setField('description', event.target.value.slice(0, 500))}
                error={Boolean(errors.description)}
                helperText={errors.description || `${form.description.length}/500（纯文本，换行会保留）`}
                multiline
                minRows={6}
                fullWidth
              />
            </Box>
          ) : null}

          {step === 1 ? (
            <Box>
              <Typography component="h2" sx={{ fontSize: 16, fontWeight: 700, mb: 2 }}>
                ② 分类
              </Typography>
              <TextField
                select
                label="一级类别 *"
                value={form.category_id}
                onChange={(event) => changeCategory(event.target.value)}
                error={Boolean(errors.category_id)}
                helperText={errors.category_id}
                fullWidth
                sx={{ mb: 2 }}
              >
                {categories.map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.name}
                  </MenuItem>
                ))}
              </TextField>

              <Typography sx={{ fontSize: 14, fontWeight: 700, mb: 0.5 }}>
                二级标签 *（1–3 个，已选 {form.tag_ids.length}/3）
              </Typography>
              <Typography sx={{ fontSize: 12, color: '#8A8F98', mb: 1 }}>
                只能选择所选一级类别下的标签；跨类别标签不可选
              </Typography>

              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' },
                  gap: 0.5,
                  mb: 1,
                }}
              >
                {tags.map((tag) => {
                  const checked = form.tag_ids.includes(Number(tag.id));
                  const disabled = !checked && form.tag_ids.length >= 3;
                  return (
                    <FormControlLabel
                      key={tag.id}
                      disabled={disabled}
                      control={
                        <Checkbox
                          size="small"
                          checked={checked}
                          onChange={() => toggleTag(Number(tag.id))}
                        />
                      }
                      label={<Box sx={{ fontSize: 14 }}>{tag.name}</Box>}
                      sx={{ ml: 0 }}
                    />
                  );
                })}
              </Box>
              {errors.tag_ids ? (
                <Typography sx={{ fontSize: 12, color: '#B3261E' }}>{errors.tag_ids}</Typography>
              ) : null}

              <TextField
                select
                label="服务城市 *"
                value={form.city}
                onChange={(event) => setField('city', event.target.value)}
                error={Boolean(errors.city)}
                helperText={errors.city}
                fullWidth
                sx={{ mt: 2 }}
              >
                {CITIES.map((city) => (
                  <MenuItem key={city} value={city}>
                    {city}
                  </MenuItem>
                ))}
              </TextField>
            </Box>
          ) : null}

          {step === 2 ? (
            <Box>
              <Typography component="h2" sx={{ fontSize: 16, fontWeight: 700, mb: 2 }}>
                ③ 优惠与有效期
              </Typography>
              <TextField
                label="价格文案 *"
                value={form.price_text}
                onChange={(event) => setField('price_text', event.target.value.slice(0, 30))}
                error={Boolean(errors.price_text)}
                helperText={errors.price_text || '例：到手 1299 元 / 直降 400 元'}
                fullWidth
                sx={{ mb: 2 }}
              />
              <TextField
                label="优惠条件"
                value={form.promo_condition}
                onChange={(event) => setField('promo_condition', event.target.value.slice(0, 100))}
                error={Boolean(errors.promo_condition)}
                helperText={errors.promo_condition || `${form.promo_condition.length}/100`}
                fullWidth
                sx={{ mb: 2 }}
              />
              <TextField
                label="限制条款"
                value={form.restriction}
                onChange={(event) => setField('restriction', event.target.value.slice(0, 200))}
                error={Boolean(errors.restriction)}
                helperText={errors.restriction || `${form.restriction.length}/200（留空时用户端显示「商家未提供额外限制条款」）`}
                multiline
                minRows={2}
                fullWidth
                sx={{ mb: 2 }}
              />

              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' }, gap: 2 }}>
                <TextField
                  label="有效期开始 *"
                  type="date"
                  value={form.valid_from}
                  onChange={(event) => setField('valid_from', event.target.value)}
                  error={Boolean(errors.valid_from)}
                  helperText={errors.valid_from}
                  InputLabelProps={{ shrink: true }}
                  inputProps={{ max: form.valid_to || undefined }}
                  fullWidth
                />
                <TextField
                  label="有效期结束 *"
                  type="date"
                  value={form.valid_to}
                  onChange={(event) => setField('valid_to', event.target.value)}
                  error={Boolean(errors.valid_to)}
                  helperText={errors.valid_to || '结束当日 23:59（北京时间）自动下线'}
                  InputLabelProps={{ shrink: true }}
                  inputProps={{ min: form.valid_from || undefined }}
                  fullWidth
                />
              </Box>
              <Typography sx={{ fontSize: 12, color: '#8A8F98', mt: 1 }}>
                单条广告有效期最长 90 天；建议提前 1 天开始，避免刚上线就结束。
              </Typography>
            </Box>
          ) : null}

          {step === 3 ? (
            <Box>
              <Typography component="h2" sx={{ fontSize: 16, fontWeight: 700, mb: 2 }}>
                ④ 落地页与素材
              </Typography>
              <TextField
                label="落地页 URL *"
                value={form.landing_url}
                onChange={(event) => setField('landing_url', event.target.value.slice(0, 500))}
                error={Boolean(errors.landing_url)}
                helperText={errors.landing_url || '必须 http/https；不得为短链、裸 IP、可执行文件或压缩包'}
                fullWidth
                sx={{ mb: 2 }}
                placeholder="以 https:// 开头的商品页或店铺页地址"
              />

              <Typography sx={{ fontSize: 14, fontWeight: 700, mb: 0.5 }}>主图</Typography>
              <Typography sx={{ fontSize: 12, color: '#8A8F98', mb: 1 }}>
                建议 16:9、≤2MB，仅支持 jpg/png/webp；不上传时系统会生成一张确定性封面
              </Typography>

              <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', flexWrap: 'wrap' }}>
                <Box
                  sx={{
                    width: 200,
                    aspectRatio: '16 / 9',
                    borderRadius: 1.5,
                    bgcolor: '#EEF1F5',
                    border: '1px solid #E2E6EC',
                    overflow: 'hidden',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {form.image_path ? (
                    <Box component="img" src={form.image_path} alt="主图预览" sx={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  ) : (
                    <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>未上传</Typography>
                  )}
                </Box>
                <Box>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={handleUpload}
                    style={{ display: 'none' }}
                  />
                  <Button
                    variant="outlined"
                    startIcon={uploading ? <CircularProgress size={14} /> : <IconUpload size={16} />}
                    onClick={() => fileInputRef.current && fileInputRef.current.click()}
                    disabled={uploading}
                    sx={{ borderColor: '#C9D2DD', color: '#1F3A5F' }}
                  >
                    {uploading ? '上传中…' : form.image_path ? '更换图片' : '上传图片'}
                  </Button>
                  {form.image_path ? (
                    <Box sx={{ mt: 0.5 }}>
                      <Button size="small" onClick={() => setField('image_path', '')} sx={{ fontSize: 12, color: '#B3261E' }}>
                        移除
                      </Button>
                    </Box>
                  ) : null}
                </Box>
              </Box>
              {errors.image_path ? (
                <Typography sx={{ fontSize: 12, color: '#B3261E', mt: 1 }}>{errors.image_path}</Typography>
              ) : null}
            </Box>
          ) : null}

          {step === 4 ? (
            <Box>
              <Typography component="h2" sx={{ fontSize: 16, fontWeight: 700, mb: 2 }}>
                ⑤ 预览确认
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75, mb: 2 }}>
                <Typography sx={{ fontSize: 14 }}>
                  <Box component="span" sx={{ color: '#5A6472' }}>标题：</Box>
                  {form.title || '—'}
                </Typography>
                <Typography sx={{ fontSize: 14 }}>
                  <Box component="span" sx={{ color: '#5A6472' }}>类别：</Box>
                  {category ? category.name : '—'}
                  {form.tag_ids.length
                    ? ` · ${tags
                        .filter((tag) => form.tag_ids.includes(Number(tag.id)))
                        .map((tag) => tag.name)
                        .join('、')}`
                    : ''}
                </Typography>
                <Typography sx={{ fontSize: 14 }}>
                  <Box component="span" sx={{ color: '#5A6472' }}>城市 / 价格：</Box>
                  {form.city} · {form.price_text || '—'}
                </Typography>
                <Typography sx={{ fontSize: 14 }}>
                  <Box component="span" sx={{ color: '#5A6472' }}>有效期：</Box>
                  {form.valid_from && form.valid_to ? formatRangeCN(form.valid_from, form.valid_to) : '—'}
                </Typography>
                <Typography sx={{ fontSize: 14, overflowWrap: 'anywhere' }}>
                  <Box component="span" sx={{ color: '#5A6472' }}>落地页：</Box>
                  {form.landing_url || '—'}
                </Typography>
                <Typography className="adx-preline" sx={{ fontSize: 14, color: '#33404F', mt: 0.5 }}>
                  {form.description || '—'}
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

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
                    {SUBMIT_POLICY_CHECK}
                    <Link component={RouterLink} to="/policy/ads" sx={{ ml: 0.5, fontSize: 13 }}>
                      查看政策
                    </Link>
                  </Typography>
                }
                sx={{ alignItems: 'flex-start', ml: 0 }}
              />
              {errors.agree ? <Typography sx={{ fontSize: 12, color: '#B3261E' }}>{errors.agree}</Typography> : null}
            </Box>
          ) : null}

          <Divider sx={{ my: 2.5 }} />

          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
            <Button
              variant="outlined"
              onClick={() => setStep((value) => Math.max(0, value - 1))}
              disabled={step === 0}
              sx={{ borderColor: '#C9D2DD', color: '#1F3A5F' }}
            >
              上一步
            </Button>
            {step < STEPS.length - 1 ? (
              <Button variant="contained" onClick={() => setStep((value) => Math.min(STEPS.length - 1, value + 1))} sx={{ bgcolor: '#1F3A5F' }}>
                下一步
              </Button>
            ) : null}
            <Box sx={{ flex: 1 }} />
            <Button
              variant="outlined"
              onClick={() => handleSave(false)}
              disabled={submitting}
              sx={{ borderColor: '#C9D2DD', color: '#5A6472' }}
            >
              保存草稿
            </Button>
            <Button
              variant="contained"
              onClick={() => handleSave(true)}
              disabled={submitting}
              startIcon={submitting ? <CircularProgress size={14} sx={{ color: '#fff' }} /> : null}
              sx={{ bgcolor: '#1F3A5F', '&:hover': { bgcolor: '#17304F' } }}
            >
              {submitting ? '提交中…' : '提交审核'}
            </Button>
          </Box>
          {errorCount > 0 ? (
            <Typography sx={{ fontSize: 12, color: '#B3261E', mt: 1 }}>
              当前有 {errorCount} 项需要修改，修改后再提交。
            </Typography>
          ) : null}
        </Box>

        {/* 实时预览 */}
        <Box sx={{ position: { md: 'sticky' }, top: { md: 88 } }}>
          <Typography sx={{ fontSize: 13, fontWeight: 700, color: '#5A6472', mb: 1 }}>实时预览（用户端视角）</Typography>
          <AdCard ad={previewAd} preview />
          <Alert severity="info" sx={{ mt: 1.5, fontSize: 12 }}>
            发布后将公开标注为「广告」，且不接受付费排序；审核通过前不会对外展示。
          </Alert>
          {originalAd && AD_STATUS[originalAd.status] ? (
            <Typography sx={{ fontSize: 12, color: '#8A8F98', mt: 1 }}>
              当前状态：{AD_STATUS[originalAd.status].label}
            </Typography>
          ) : null}
        </Box>
      </Box>

      {/* 提交条款常驻提示 */}
      <Box sx={{ mt: 2 }}>
        <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>
          {SUBMIT_BANNER}；提交后进入待审核，预计 24 小时内审核完成，通过后自动上线。
        </Typography>
      </Box>
    </Box>
  );
}
