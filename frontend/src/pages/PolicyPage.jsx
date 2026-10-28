import React, { useEffect, useMemo } from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import Box from '@mui/material/Box';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';

/**
 * 四篇静态正文（P0-B-08）：/policy/ads、/policy/privacy、/policy/report、/about。
 * 内容要求：运营主体、联系方式、数据保存与删除途径、排序不接受付费影响（#why 锚点）。
 */
const CONTENT = {
  ads: {
    title: '广告政策',
    updatedAt: '2026-10-27',
    intro:
      '本站是商家付费推广信息的公开目录。所有内容均逐条标注「广告」，平台不参与交易，不对商品或服务本身作出担保。',
    sections: [
      {
        id: 'mark',
        heading: '广告标识规则',
        paragraphs: [
          '列表与收藏页的每张卡片，图片区左上角固定显示实底橙色「广告」角标，字号 12px 加粗，间距 8px，不随滚动或悬停消失；即使图片加载失败，角标仍然渲染。',
          '详情页标题上方固定显示「广告 · 由 {商家名} 提供」，并给出「为什么看到这条」入口。',
          '全站不使用「赞助内容」「推广阅读」「猜你喜欢」「为您推荐」等易与普通内容混淆的措辞指代广告。',
        ],
      },
      {
        id: 'why',
        heading: '排序不接受付费影响',
        paragraphs: [
          '列表排序只有三种：最新发布（published_at 倒序，默认）、即将结束（valid_to 升序）、最多收藏（近 30 天收藏数倒序）。',
          '排序算法不接受任何商家付费影响，不存在「付费置顶」「竞价排名」「加权曝光」。商家支付的费用只与其广告是否被展示有关，与展示位置、排序先后无关。',
          '同一请求内排序带唯一键兜底，保证结果稳定，不会因翻页出现重复或漏项。',
        ],
      },
      {
        id: 'review',
        heading: '审核与下架',
        paragraphs: [
          '所有广告在公开前都经过人工审核，审核不通过会给出具体原因并回显给商家；商家可修改后重新提交。',
          '出现下列情形将被下架：虚假宣传或夸大功效、信息不完整或不实、链接不可访问或可疑、图片与内容不符、禁投行业或违禁品。',
          '用户举报成立的广告会被下架或要求整改；下架后用户端立即不可见。',
        ],
      },
      {
        id: 'banned',
        heading: '禁投行业',
        paragraphs: [
          '医疗诊疗与处方药、金融放贷与虚拟货币、博彩与赌博、成人内容、烟草与电子烟、军警装备与管制器具、代开发票与办证、传销与拉人头返利等，一律不接受投放。',
          '提交时平台会做关键词预检，命中禁投词或危险链接将直接被拒。',
        ],
      },
      {
        id: 'limits',
        heading: '有效期与数量限制',
        paragraphs: [
          '每条广告必须填写结束日期，单条有效期不超过 90 天，到期自动下线。',
          '单商家每日新建广告不超过 5 条，同时在架不超过 20 条。',
          '单设备收藏上限 200 条、隐藏上限 500 条，达到上限会提示清理。',
        ],
      },
    ],
  },
  privacy: {
    title: '隐私说明',
    updatedAt: '2026-10-27',
    intro:
      '浏览本站不需要注册、不需要手机号或邮箱。我们只采集让「收藏/隐藏/举报」能正常工作所必需的最小信息。',
    sections: [
      {
        id: 'what',
        heading: '我们采集什么',
        paragraphs: [
          '匿名访客标识：一个随机生成并签名的 Cookie（adx_vid），仅用于把你的收藏、隐藏、偏好、举报关联起来，180 天有效。',
          '行为事件：广告曝光、详情查看、外链点击、收藏、隐藏、举报，以及页面标识与列表位置；不含姓名、手机号、邮箱，不含 IP 明文，不含设备指纹。',
          '商家账号信息：注册时填写的商家名、联系人、手机号、邮箱、城市、主营类别与密码哈希（不可逆、加盐）。',
        ],
      },
      {
        id: 'why',
        heading: '为什么采集',
        paragraphs: [
          '向商家提供合规的效果统计（展示量、详情查看量、外链点击量），这些统计只能看到汇总数字，看不到个人。',
          '识别刷量与恶意点击：同一访客单日对同一广告的外链点击超过 20 次会被标记为异常并单独记录，标记只出现在后台报表中。',
          '满足举报处理需要：举报码用于查询处理进度，查询结果不包含举报人信息与处理人信息。',
        ],
      },
      {
        id: 'keep',
        heading: '保存多久',
        paragraphs: [
          '匿名访客记录保留 180 天；事件流水只增不改，用于指标复算；用于风控的 IP 哈希最多保留 7 天并到期清理。',
          '举报记录在处理结束后保留，用于合规审计与重复问题识别。',
          '数据库每日快照保留 7 天（本版本由运营者手动触发，后续改为自动）。',
        ],
      },
      {
        id: 'delete',
        heading: '如何删除你的数据',
        paragraphs: [
          '在「偏好设置」页底部点「清除全部偏好」，可一次清空本设备的收藏、隐藏记录与偏好设置，即时生效。',
          '举报记录为完成处理需要保留，但删除后不再与本设备关联。',
          '清除浏览器 Cookie 等同于换一台新设备：你会得到新的匿名标识，原有收藏将不可见（数据本身仍在库中，只是无法再关联到你）。',
          '如需彻底删除某条举报关联信息，可通过「关于与联系我们」页的方式提出，我们会在合理期限内处理。',
        ],
      },
      {
        id: 'third',
        heading: '我们不做什么',
        paragraphs: [
          '不接入任何第三方分析脚本、统计像素或广告联盟，页面不发起任何跨站请求。',
          '不出售、不交换、不对外提供访客数据。',
          '不使用暗黑模式诱导授权：不弹注册墙、不做自动播放、不做倒计时遮罩。',
        ],
      },
    ],
  },
  report: {
    title: '举报说明',
    updatedAt: '2026-10-27',
    intro:
      '每张卡片与每个详情页都有举报入口，三次点击内即可提交。举报不需要登录，也不要求填写个人信息。',
    sections: [
      {
        id: 'how',
        heading: '怎么举报',
        paragraphs: [
          '卡片右下角「更多」菜单 →「举报」；或进入详情页点「举报」。',
          '选择 6 项原因之一：虚假宣传、过期信息、价格不实、链接可疑、不当内容、其他；可补充不超过 200 字的说明。',
          '提交成功后会得到一个形如 RP-XXXXXXXX 的举报码，请留存。',
        ],
      },
      {
        id: 'status',
        heading: '状态怎么变',
        paragraphs: [
          '待处理：已收到，我们会在 48 小时内处理。',
          '处理中：正在核查该广告。',
          '已处理：经核查，该广告已被下架或整改。',
          '不成立：经核查，暂未发现违反平台规则的情况。',
        ],
      },
      {
        id: 'merge',
        heading: '重复提交与上限',
        paragraphs: [
          '同一条广告在 24 小时内重复举报会被合并，返回同一个举报码，不会产生多条记录。',
          '单设备每日最多提交 3 条举报，避免恶意占用处理资源。',
        ],
      },
      {
        id: 'next',
        heading: '处理之后仍有疑问',
        paragraphs: [
          '处理结束（已处理/不成立）后的 7 天内，可以在「举报进度查询」页对某条举报点「仍有疑问」追加一条说明。',
          '追加说明不会改变当前状态，但会再次进入运营核查队列。',
          '同一举报码的查询结果不包含举报人信息，也不包含处理人信息。',
        ],
      },
    ],
  },
  about: {
    title: '关于与联系我们',
    updatedAt: '2026-10-27',
    intro: '广告发现站是一个「广告自主浏览」工具：让用户在不被营销压迫的前提下，主动发现商家公开的付费推广信息。',
    sections: [
      {
        id: 'who',
        heading: '运营主体',
        paragraphs: [
          '本站在中国大陆境内自有服务器运行，由个人运营者负责内容审核与举报处理（一人公司试点项目）。',
          '运营者：广告发现站项目组（一人公司试点，境内自有服务器）；联系方式：通过站内「举报」入口留言，或从「商家登录」页联系运营者；服务时间：工作日 10:00–19:00（北京时间）。',
        ],
      },
      {
        id: 'principle',
        heading: '我们的四条原则',
        paragraphs: [
          '第一，广告必须可识别：每条内容都有「广告」角标，措辞不玩文字游戏。',
          '第二，排序不卖位置：只按时间、有效期、收藏数排序，付费不能买到更靠前的位置。',
          '第三，浏览不需要注册：从进入首页到点开商家页面，全链路没有注册墙。',
          '第四，数据只要最小集：不采集姓名、手机号、邮箱，不做跨站追踪。',
        ],
      },
      {
        id: 'contact',
        heading: '联系方式与响应时效',
        paragraphs: [
          '内容举报：在站内提交，48 小时内首次响应。',
          '商家入驻与合作：通过「商家登录」页注册后提交广告，审核预计 24 小时内完成。',
          '数据删除与隐私问题：邮件联系，7 个工作日内答复。',
        ],
      },
      {
        id: 'tech',
        heading: '技术说明',
        paragraphs: [
          '前端 React + Vite，后端 FastAPI + SQLite，前后端同源部署在同一端口。',
          '全站不加载任何第三方脚本、字体或图片资源；广告封面由服务端生成的 SVG 提供。',
        ],
      },
    ],
  },
};

/**
 * @param {{kind: 'ads'|'privacy'|'report'|'about'}} props
 */
export default function PolicyPage({ kind = 'ads' }) {
  const location = useLocation();
  const page = CONTENT[kind] || CONTENT.ads;

  // 支持 /policy/ads#why 这类锚点直达
  useEffect(() => {
    if (!location.hash) return;
    const targetId = location.hash.replace('#', '');
    const timer = window.setTimeout(() => {
      const element = document.getElementById(targetId);
      if (element && typeof element.scrollIntoView === 'function') {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 60);
    return () => window.clearTimeout(timer);
  }, [location.hash, kind]);

  const toc = useMemo(() => page.sections.map((section) => ({ id: section.id, heading: section.heading })), [page]);

  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 220px' }, gap: { xs: 2, md: 3 }, alignItems: 'start' }}>
      <Box component="article" sx={{ bgcolor: '#FFFFFF', border: '1px solid #E2E6EC', borderRadius: '12px', p: { xs: 2, sm: 3 } }}>
        <Typography component="h1" sx={{ fontSize: { xs: 22, sm: 26 }, fontWeight: 700, mb: 0.5 }}>
          {page.title}
        </Typography>
        <Typography sx={{ fontSize: 12, color: '#8A8F98', mb: 2 }}>最后更新：{page.updatedAt}</Typography>

        <Typography sx={{ fontSize: 15, color: '#33404F', lineHeight: 1.85, mb: 2 }}>{page.intro}</Typography>
        <Divider sx={{ mb: 2.5 }} />

        {page.sections.map((section) => (
          <Box key={section.id} id={section.id} className="adx-anchor" sx={{ mb: 3 }}>
            <Typography component="h2" sx={{ fontSize: 17, fontWeight: 700, mb: 1 }}>
              {section.heading}
            </Typography>
            {section.paragraphs.map((paragraph, index) => (
              <Typography
                key={`${section.id}-p-${index}`}
                sx={{ fontSize: 15, color: '#33404F', lineHeight: 1.9, mb: 1.25 }}
              >
                {paragraph}
              </Typography>
            ))}
          </Box>
        ))}

        <Divider sx={{ mb: 2 }} />
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Link component={RouterLink} to="/policy/ads" sx={{ fontSize: 13 }}>
            广告政策
          </Link>
          <Link component={RouterLink} to="/policy/privacy" sx={{ fontSize: 13 }}>
            隐私说明
          </Link>
          <Link component={RouterLink} to="/policy/report" sx={{ fontSize: 13 }}>
            举报说明
          </Link>
          <Link component={RouterLink} to="/about" sx={{ fontSize: 13 }}>
            关于与联系我们
          </Link>
        </Box>
      </Box>

      <Box
        component="nav"
        aria-label="本页目录"
        sx={{
          position: { md: 'sticky' },
          top: { md: 96 },
          bgcolor: '#FFFFFF',
          border: '1px solid #E2E6EC',
          borderRadius: '12px',
          p: 2,
        }}
      >
        <Typography sx={{ fontSize: 13, fontWeight: 700, mb: 1 }}>本页目录</Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
          {toc.map((item) => (
            <Link key={item.id} href={`#${item.id}`} underline="hover" sx={{ fontSize: 13, color: '#5A6472' }}>
              {item.heading}
            </Link>
          ))}
        </Box>
      </Box>
    </Box>
  );
}
