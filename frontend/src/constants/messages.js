/**
 * 精确文案常量 —— 逐字照 PRD §6.3 / §5.1，禁止改写措辞。
 * 评审项：不得出现"赞助内容/推广阅读/猜你喜欢/为您推荐"指代广告；
 * 外链按钮不得为"了解更多/立即购买/马上抢"。
 */

/** 列表/收藏卡片角标 */
export const AD_BADGE = '广告';

/** 详情页标题上方（商家名用 DETAIL_ATTRIBUTION 拼接） */
export const DETAIL_ATTRIBUTION_PREFIX = '广告 · 由';
export const DETAIL_ATTRIBUTION_SUFFIX = '提供';

/**
 * @param {string} merchantName
 * @returns {string} `广告 · 由 {商家名} 提供`
 */
export function detailAttribution(merchantName) {
  return `${DETAIL_ATTRIBUTION_PREFIX} ${merchantName || '未提供'} ${DETAIL_ATTRIBUTION_SUFFIX}`;
}

/** 首页顶部说明条（首屏可见） */
export const NOTICE_BAR_TEXT =
  '本站所有内容均为商家付费推广，已标注「广告」。平台不参与交易，请自行判断。';

/** 外链主按钮 */
export const CTA_GO = '前往商家页面';

/** 外链按钮旁注小字 */
export const LEAVE_HINT = '即将离开本平台';

/** 详情页外链按钮下方说明 */
export const LEAVE_NOTE = '即将离开本平台，请自行判断网站安全性';

/** 中间页标题 */
export const GO_TITLE = '您即将离开本站';

/** 中间页域名行（函数） */
export function goDomainLine(domain) {
  return `目标网站：${domain || '未知域名'}`;
}

/** 中间页免责声明 */
export const GO_DISCLAIMER = '本站不对该网站内容负责';

/** 中间页倒计时提示 */
export function goCountdownHint(seconds) {
  return `${seconds} 秒后可继续前往`;
}

/** 中间页继续按钮 */
export const GO_CONTINUE = '继续前往';

/** 中间页返回按钮 */
export const GO_BACK = '返回详情';

/** 外链阻断 */
export const GO_BLOCKED_TITLE = '该链接已被阻断';
export const GO_BLOCKED_FALLBACK = '该链接不符合平台安全规则，已停止跳转。';

/** 详情页「为什么看到这条」 */
export const WHY_LINK = '为什么看到这条';

/** 限制条款为空时 */
export const NO_RESTRICTION = '商家未提供额外限制条款';

/** 广告不可见 */
export const AD_NOT_VISIBLE = '该广告已结束或暂不可见';

/** 商家端提交页顶部提示 */
export const SUBMIT_BANNER = '提交即表示该内容将公开标注为「广告」';
export const SUBMIT_POLICY_CHECK = '我已阅读《广告政策》并保证信息真实有效';
export const SUBMIT_PENDING_HINT = '已提交，等待审核（预计 24 小时内审核完成，通过后自动上线）';
export const SUBMIT_EDIT_ACTIVE_HINT = '修改核心字段将重新审核并暂时下线';

/** 收藏页常驻提示 */
export const FAVORITES_DEVICE_TIP = '收藏保存在本设备，清理浏览器或换设备将看不到';

/** 降噪 toast（不夸大、不承诺永久屏蔽） */
export const HIDE_TOAST = '已生效：该类广告将少出现在你的列表';
export const REPORT_TOAST = '已收到，我们会在 48 小时内处理';

/** 空态文案（PRD §5.1 表） */
export const EMPTY = {
  home: {
    title: '首批广告正在审核中',
    desc: '内容上架后会出现在这里，你也可以先看看其他类别。',
  },
  category: {
    title: '该类别暂无广告',
    desc: '首批商家正在审核中，换看其他类别 →',
  },
  search: {
    title: '没有找到相关广告',
    desc: '试试更简短的关键词，或直接按类别浏览。',
  },
  favorites: {
    title: '还没有收藏，去找找看',
    desc: '在卡片或详情页点收藏，就会出现在这里。',
  },
  preferencesEmpty: {
    title: '未设置，当前按最新发布排序',
    desc: '选择感兴趣的类别后，首页会优先展示这些类别。',
  },
  hidesEmpty: {
    title: '你没有隐藏任何广告',
    desc: '在卡片更多菜单里点「不感兴趣」即可隐藏。',
  },
  reportStatus: {
    title: '输入举报码查询，或先浏览广告进行举报',
    desc: '举报码形如 RP-XXXXXXXX，提交举报后会自动生成。',
  },
  merchantAds: {
    title: '还没有广告，提交第一条',
    desc: '广告提交后需人工审核，通过后自动上线。',
  },
  adminReview: {
    title: '当前无待审广告',
    desc: '新提交的广告会自动出现在这里。',
  },
  adminAds: {
    title: '没有符合条件的广告',
    desc: '试试清除筛选条件后重新查看。',
  },
  adminReports: {
    title: '没有待处理举报',
    desc: '近 7 天处理情况见上方统计。',
  },
  adminMerchants: {
    title: '还没有商家入驻',
    desc: '商家注册后会出现在这里。',
  },
  adminCategories: {
    title: '该类别暂无二级标签',
    desc: '可在下方新增标签。',
  },
  adminStats: {
    title: '该区间没有事件记录',
    desc: '换一个日期区间再试。',
  },
  merchantReport: {
    title: '广告上线后开始统计',
    desc: '仅统计广告处于可展示状态期间产生的事件。',
  },
};

/** 通用操作文案 */
export const COMMON = {
  loading: '加载中…',
  retry: '重试',
  backHome: '返回首页',
  backList: '返回列表',
  clearFilters: '清除筛选',
  clearAllFilters: '清除全部筛选',
  noMore: '没有更多了',
  loadMore: '加载更多',
  cancel: '取消',
  confirm: '确定',
  save: '保存',
  submit: '提交',
  logout: '退出登录',
  network: '网络异常，请稍后重试',
};

/** 举报说明时限（PRD P0-K-04） */
export const REPORT_SLA_TEXT = '我们会在 48 小时内首次响应';
