import React from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '@mui/material/Button';
import EmptyState from '../components/EmptyState.jsx';
import { IconWarn } from '../components/icons.jsx';

/** 404 兜底：保留回到首页与搜索入口，不显示技术栈信息 */
export default function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <EmptyState
      title="页面不存在（404）"
      description="链接可能已失效，或者广告已下线。你可以回到首页按类别浏览。"
      actionText="返回首页"
      onAction={() => navigate('/')}
      icon={<IconWarn size={34} />}
      suggestions={[
        { label: '搜索广告', onClick: () => navigate('/search') },
        { label: '我的收藏', onClick: () => navigate('/favorites') },
        { label: '举报进度查询', onClick: () => navigate('/report-status') },
      ]}
    />
  );
}
