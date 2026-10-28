import React from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import { NOTICE_BAR_TEXT } from '../constants/messages.js';
import { resetNoticeDismissed } from './NoticeBar.jsx';

const POLICY_LINKS = [
  { to: '/policy/ads', label: '广告政策' },
  { to: '/policy/privacy', label: '隐私说明' },
  { to: '/policy/report', label: '举报说明' },
  { to: '/about', label: '关于与联系我们' },
];

/**
 * 页脚：政策/关于链接 + 「本站不参与交易」常驻说明 + 说明条重开入口。
 */
export default function Footer() {
  const navigate = useNavigate();

  const reopenNotice = () => {
    resetNoticeDismissed();
    navigate('/');
  };

  return (
    <Box
      component="footer"
      sx={{
        mt: { xs: 5, sm: 8 },
        borderTop: '1px solid #E2E6EC',
        bgcolor: '#FFFFFF',
      }}
    >
      <Box sx={{ maxWidth: 1200, mx: 'auto', px: { xs: 2, sm: 3 }, py: { xs: 3, sm: 4 } }}>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', md: '1.4fr 1fr 1fr' },
            gap: { xs: 2.5, sm: 3 },
            alignItems: 'start',
          }}
        >
          <Box>
            <Typography sx={{ fontSize: 15, fontWeight: 700, color: '#1F3A5F', mb: 1 }}>
              广告发现站
            </Typography>
            <Typography sx={{ fontSize: 13, color: '#5A6472', lineHeight: 1.75 }}>
              本站为商家付费推广信息的公开目录。所有内容均明确标注「广告」，排序不接受任何付费影响。
            </Typography>
          </Box>

          <Box>
            <Typography sx={{ fontSize: 14, fontWeight: 700, mb: 1 }}>平台规则</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
              {POLICY_LINKS.map((item) => (
                <Link
                  key={item.to}
                  component={RouterLink}
                  to={item.to}
                  underline="hover"
                  sx={{ fontSize: 14, color: '#5A6472', '&:hover': { color: '#1F3A5F' } }}
                >
                  {item.label}
                </Link>
              ))}
            </Box>
          </Box>

          <Box>
            <Typography sx={{ fontSize: 14, fontWeight: 700, mb: 1 }}>我的</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
              <Link component={RouterLink} to="/favorites" underline="hover" sx={{ fontSize: 14, color: '#5A6472' }}>
                收藏夹
              </Link>
              <Link component={RouterLink} to="/preferences" underline="hover" sx={{ fontSize: 14, color: '#5A6472' }}>
                偏好设置
              </Link>
              <Link
                component={RouterLink}
                to="/report-status"
                underline="hover"
                sx={{ fontSize: 14, color: '#5A6472' }}
              >
                举报进度查询
              </Link>
              <Link component={RouterLink} to="/merchant/login" underline="hover" sx={{ fontSize: 14, color: '#5A6472' }}>
                商家登录
              </Link>
            </Box>
          </Box>
        </Box>

        <Box
          sx={{
            mt: 3,
            pt: 2,
            borderTop: '1px solid #E2E6EC',
            display: 'flex',
            flexWrap: 'wrap',
            gap: 1,
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Typography sx={{ fontSize: 13, color: '#5A6472' }}>
            本站不参与交易，所有价格与优惠以商家页面为准；请在离开本站前自行判断网站安全性。
          </Typography>
          <Box
            component="button"
            type="button"
            onClick={reopenNotice}
            sx={{
              border: 0,
              bgcolor: 'transparent',
              color: '#1F3A5F',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
              p: 0,
              textDecoration: 'underline',
            }}
          >
            平台说明
          </Box>
        </Box>

        <Box sx={{ mt: 1.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          <Typography sx={{ fontSize: 12, color: '#8A8F98', lineHeight: 1.7 }}>
            声明：{NOTICE_BAR_TEXT}
          </Typography>
          <Typography sx={{ fontSize: 12, color: '#8A8F98' }}>
            © 2026 广告发现站 · 运营主体与联系方式见「关于与联系我们」 · 全部数据保存在境内自有服务器
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
