"""幂等种子数据：6 类别 + 23 标签 + 1 管理员 + 8 商家 + 51 条广告 + 封面 + 演示事件。

用法::

    python -m backend.seed            # 首次建库并灌数据（已有数据则跳过）
    python -m backend.seed --reset    # 删库重建并重灌
    python -m backend.seed --no-events  # 不生成演示事件
"""

from __future__ import annotations

import argparse
import json
import random
import uuid
from datetime import datetime, timedelta

from .config import COVERS_DIR, get_settings
from .constants import (
    AD_STATUS_ACTIVE,
    AD_STATUS_EXPIRED,
    AD_STATUS_OFFLINE,
    AD_STATUS_PENDING,
    AD_STATUS_REJECTED,
    AD_STATUS_SCHEDULED,
    COVER_URL_PREFIX,
)
from .database import Base, DB_PATH, SessionLocal, engine, init_db
from .models import (
    Ad,
    AdTag,
    AdminUser,
    Category,
    Event,
    Favorite,
    Merchant,
    Report,
    ReportFollowup,
    Tag,
    Visitor,
)
from .security import hash_password
from .services.ads import log_review
from .utils.cover import write_cover_file
from .utils.timeutil import now_utc, parse_cst_date_end, parse_cst_date_start, to_cst

# ------------------------------------------------------------------ 类别与标签
CATEGORY_SEEDS: list[dict[str, object]] = [
    {
        "slug": "local-service",
        "name": "本地生活服务",
        "intro": "餐饮到店、家政保洁、维修安装、美容美发；必须按城市服务，跨城无效。",
        "sort_order": 1,
        "tags": [("餐饮到店", "local-food"), ("家政保洁", "housekeeping"), ("维修安装", "repair"), ("美容美发", "beauty")],
    },
    {
        "slug": "deals",
        "name": "优惠与促销",
        "intro": "限时折扣、优惠券领取、满减活动、赠品活动；仅收无明确商品归属的纯促销信息。",
        "sort_order": 2,
        "tags": [("限时折扣", "flash-sale"), ("优惠券领取", "coupon"), ("满减活动", "full-reduction"), ("赠品活动", "gift")],
    },
    {
        "slug": "digital",
        "name": "数码与家电",
        "intro": "手机配件、电脑办公、家用电器、智能设备；需注明品牌型号，不收无说明的翻新机。",
        "sort_order": 3,
        "tags": [
            ("手机配件", "phone-accessory"),
            ("电脑办公", "office"),
            ("家用电器", "home-appliance"),
            ("智能设备", "smart-device"),
        ],
    },
    {
        "slug": "home",
        "name": "家居与日用",
        "intro": "家具软装、厨房餐具、清洁收纳、床品家纺；大件需注明配送范围。",
        "sort_order": 4,
        "tags": [("家具软装", "furniture"), ("厨房餐具", "kitchen"), ("清洁收纳", "storage"), ("床品家纺", "bedding")],
    },
    {
        "slug": "fashion",
        "name": "服饰与美妆",
        "intro": "服饰鞋包、护肤彩妆、配饰珠宝；化妆品需注明来源或备案信息。",
        "sort_order": 5,
        "tags": [("服饰鞋包", "apparel"), ("护肤彩妆", "skincare"), ("配饰珠宝", "jewelry")],
    },
    {
        "slug": "sports-pet",
        "name": "运动户外与宠物",
        "intro": "运动健身、户外装备、宠物用品、宠物服务；宠物医疗仅收用品与洗护寄养。",
        "sort_order": 6,
        "tags": [("运动健身", "fitness"), ("户外装备", "outdoor"), ("宠物用品", "pet-supply"), ("宠物服务", "pet-service")],
    },
]

# ------------------------------------------------------------------ 商家（8 家）
MERCHANT_SEEDS: list[dict[str, object]] = [
    {
        "name": "家享电器",
        "contact_name": "李伟",
        "phone": "13800001001",
        "email": "jiaxiang@example.com",
        "city": "深圳",
        "category_slug": "digital",
        "verified": True,
    },
    {
        "name": "华南数码小铺",
        "contact_name": "陈海",
        "phone": "13800001002",
        "email": "huanan@example.com",
        "city": "深圳",
        "category_slug": "digital",
        "verified": True,
    },
    {
        "name": "声动优选",
        "contact_name": "周敏",
        "phone": "13800001003",
        "email": "shengdong@example.com",
        "city": "广州",
        "category_slug": "digital",
        "verified": False,
    },
    {
        "name": "洁净家政",
        "contact_name": "王芳",
        "phone": "13800001004",
        "email": "jiejing@example.com",
        "city": "深圳",
        "category_slug": "local-service",
        "verified": True,
    },
    {
        "name": "布语软装",
        "contact_name": "赵晓",
        "phone": "13800001005",
        "email": "buyu@example.com",
        "city": "杭州",
        "category_slug": "home",
        "verified": False,
    },
    {
        "name": "社区团购优选",
        "contact_name": "孙洋",
        "phone": "13800001006",
        "email": "tuangou@example.com",
        "city": "上海",
        "category_slug": "deals",
        "verified": True,
    },
    {
        "name": "悦颜美妆集合",
        "contact_name": "林悦",
        "phone": "13800001007",
        "email": "yueyan@example.com",
        "city": "成都",
        "category_slug": "fashion",
        "verified": False,
    },
    {
        "name": "宠乐生活馆",
        "contact_name": "何静",
        "phone": "13800001008",
        "email": "chongle@example.com",
        "city": "北京",
        "category_slug": "sports-pet",
        "verified": True,
    },
]


def A(
    cat: str,
    tags: list[str],
    title: str,
    desc: str,
    city: str,
    price: str | None,
    promo: str | None,
    restriction: str | None,
    merchant: int,
    start: int,
    days: int,
    status: str = AD_STATUS_ACTIVE,
) -> dict[str, object]:
    """广告种子构造器（``start``/``days`` 为相对北京时间的日期偏移）。"""
    return {
        "cat": cat,
        "tags": tags,
        "title": title,
        "desc": desc,
        "city": city,
        "price": price,
        "promo": promo,
        "restriction": restriction,
        "merchant": merchant,
        "start": start,
        "days": days,
        "status": status,
    }


# ------------------------------------------------------------------ 广告（51 条）
AD_SEEDS: list[dict[str, object]] = [
    # ---- 数码与家电 12（8 在架 / 2 待审 / 1 拒 / 1 过期 / 1 待生效）----
    A("digital", ["家用电器"], "便携榨汁杯 350ml 到手 89 元",
      "USB 充电便携榨汁杯，350ml 容量，六叶刀头，出门装果汁不用带插头。整机可拆洗，随机附送杯刷与食谱卡。",
      "全国", "到手 89 元", "满 99 减 10，限前 300 名", "每单限购 2 件，不与店铺其他优惠同享", 1, -18, 34),
    A("digital", ["家用电器"], "台式净饮机 免安装 直降 400 元",
      "台式净饮机免安装，插电即用，三秒出热水，五档温度可调。滤芯寿命显示，换芯有提示，附赠一年滤芯一支。",
      "全国", "到手 1299 元", "满 1000 减 400，限前 200 名", "每个账号限购 1 台，不与其他优惠叠加", 0, -20, 21),
    A("digital", ["智能设备"], "蓝牙耳机 降噪款 券后 199 元",
      "半入耳主动降噪蓝牙耳机，单次续航 8 小时，配合充电仓可用 32 小时。支持双设备连接，通话降噪四麦克风。",
      "全国", "券后 199 元", "店铺券满 200 减 30", "非质量问题不支持七天无理由退货", 2, -14, 18),
    A("digital", ["手机配件"], "65W 氮化镓充电器 三口快充",
      "65W 氮化镓充电器，双 Type-C 加一个 USB-A，可同时给笔记本与手机供电。折叠插脚，体积比同功率产品小一档。",
      "全国", "到手 119 元", None, None, 1, -40, 20, AD_STATUS_EXPIRED),
    A("digital", ["电脑办公"], "机械键盘 87 键 热插拔 到手 249",
      "87 键紧凑机械键盘，支持热插拔换轴，出厂润轴打字音更实。三模连接，mac 与 windows 键位可切。",
      "全国", "到手 249 元", "下单赠掌托一个", "赠品数量有限，赠完即止", 1, -12, 30),
    A("digital", ["电脑办公"], "无线鼠标 静音办公 双模 79 元",
      "静音微动无线鼠标，2.4G 与蓝牙双模，一节电池可用约半年。磨砂外壳握感稳，适合长时间办公。",
      "全国", "到手 79 元", None, None, 2, -16, 26),
    A("digital", ["家用电器"], "扫地机器人 集尘款 直降 600 元",
      "激光导航扫地机器人，带自动集尘座，可存 60 天灰尘。支持划定禁扫区与分区清扫，app 内可看清扫轨迹。",
      "全国", "到手 2199 元", "满 2000 减 600", "大件发货，偏远地区需补运费，具体以下单页为准", 0, -22, 40),
    A("digital", ["智能设备"], "智能门锁 指纹+密码 含安装",
      "智能门锁支持指纹、密码、卡片与机械钥匙四种开锁方式，含上门安装。低电量会提前语音提醒，应急供电口在底部。",
      "深圳", "到手 899 元", "预约安装免工时费", "需门体厚度 40-90mm，特殊门体需先咨询", 0, 6, 30, AD_STATUS_SCHEDULED),
    A("digital", ["电脑办公"], "显示器 27 英寸 2K 高刷 1099",
      "27 英寸 2K 分辨率显示器，165Hz 刷新率，支持升降旋转支架。出厂逐台校色，附带校色报告与 DP 线。",
      "全国", "到手 1099 元", "满 1000 减 100", None, 1, -10, 28),
    A("digital", ["手机配件"], "手机钢化膜 三片装 包邮",
      "高铝钢化膜三片装，附贴膜神器与除尘贴。边缘做圆弧处理，不挡指纹识别区。",
      "全国", "到手 19.9 元", None, None, 1, -8, 24, AD_STATUS_REJECTED),
    A("digital", ["智能设备"], "电动牙刷 声波款 到手 129 元",
      "声波电动牙刷，五档模式，两分钟智能计时，压力过大有提示。整机可水洗，附赠两个刷头。",
      "全国", "到手 129 元", "第二件半价", "刷头为耗材，非质量问题不退", 0, -6, 30, AD_STATUS_PENDING),
    A("digital", ["家用电器"], "洗衣机 除螨洗 10 公斤 直降 500",
      "10 公斤滚筒洗衣机，带高温除螨洗与筒自洁程序。变频电机静音，夜间洗不打扰邻居，含免费上门安装。",
      "全国", "到手 1899 元", "满 1500 减 500", "大件商品不支持七天无理由退货", 0, -9, 13),
    # ---- 家居与日用 12（10 在架 / 1 过期 / 1 待生效）----
    A("home", ["家具软装"], "沙发套 定制款 全包防猫抓",
      "定制沙发套，按沙发尺寸量体剪裁，四面全包。面料防猫抓，可拆洗，下单前客服会核对尺寸与贵妃位方向。",
      "全国", "到手 399 元起", "满 600 减 80", "定制商品不支持无理由退货", 4, -19, 32),
    A("home", ["床品家纺"], "记忆棉枕头 一对装 到手 129",
      "慢回弹记忆棉枕头，一对装，中高两种高度可选。枕套可拆洗，外套为针织面料，四季可用。",
      "全国", "到手 129 元", None, None, 4, -11, 25),
    A("home", ["床品家纺"], "四件套 长绒棉 60 支 到手 299",
      "60 支长绒棉四件套，含被套、床单、枕套两只。活性印染不易掉色，1.5 米与 1.8 米床通用款可选。",
      "全国", "到手 299 元", "满 300 减 30", None, 4, -13, 27),
    A("home", ["厨房餐具"], "厨房置物架 免打孔 三层 89 元",
      "免打孔厨房置物架，三层结构，承重约 15 公斤。背胶加固件附送，瓷砖与玻璃面直接粘，不用打孔。",
      "全国", "到手 89 元", None, "墙面为乳胶漆或壁纸时不建议使用背胶", 4, -15, 24),
    A("home", ["厨房餐具"], "陶瓷餐具 12 件套 釉下彩 199",
      "釉下彩陶瓷餐具 12 件套，含四人份碗盘与汤勺。可进微波炉与洗碗机，花色为手绘风，每批略有差异。",
      "全国", "到手 199 元", "满 199 减 20", None, 4, -17, 30),
    A("home", ["清洁收纳"], "收纳箱 折叠布艺 大容量 两件装",
      "折叠布艺收纳箱两件装，66 升大容量，带可视窗口与侧提手。不用时可压平收纳，适合换季衣物。",
      "全国", "到手 69 元", None, None, 4, -21, 33),
    A("home", ["清洁收纳"], "拖把 免手洗 干湿两用 到手 79",
      "免手洗平板拖把，干湿两用，桶内自带刮水结构。拖布为超细纤维，可机洗，替换布单独出售。",
      "全国", "到手 79 元", None, None, 4, -45, 18, AD_STATUS_EXPIRED),
    A("home", ["家具软装"], "实木餐桌 1.4 米 可伸缩 含配送",
      "橡胶木实木餐桌，1.4 米可伸缩到 1.8 米，六人位。含送货上门与安装，桌角做圆角处理，家里有小孩也放心。",
      "全国", "到手 1299 元", "满 1200 减 150", "大件配送范围以页面城市表为准，偏远地区需补运费", 4, -24, 35),
    A("home", ["家具软装"], "遮光窗帘 定制 全遮光 两片装",
      "全遮光窗帘两片装，遮光率约 95%，含轨道与挂钩。可按窗宽定制，客服会核对褶皱倍数。",
      "杭州", "到手 259 元起", "满 300 减 40", "定制尺寸不支持退换", 4, 4, 30, AD_STATUS_SCHEDULED),
    A("home", ["厨房餐具"], "保鲜盒 套装 可微波 到手 59",
      "可微波保鲜盒六件套，盖子四扣密封，汤汁不易漏。盒身耐温 -20℃ 到 120℃，冷冻与微波都能用。",
      "全国", "到手 59 元", None, None, 4, -7, 21),
    A("home", ["床品家纺"], "羽绒被 95 白鹅绒 冬被 到手 899",
      "95 白鹅绒冬被，充绒量按尺寸分档，含防绒被套。被子可水洗，附赠收纳袋，标注了充绒量与蓬松度。",
      "全国", "到手 899 元", "满 800 减 100", None, 4, -26, 40),
    A("home", ["清洁收纳"], "浴室置物架 太空铝 免打孔 129",
      "太空铝浴室置物架，免打孔安装，三层带钩。表面阳极氧化不易锈，潮湿环境可长期使用。",
      "全国", "到手 129 元", None, None, 4, -5, 20),
    # ---- 优惠与促销 10（8 在架 / 1 待审 / 1 拒）----
    A("deals", ["满减活动"], "满 100 减 30 生鲜券 限时领",
      "生鲜满减券限时领取，满 100 减 30，可用于果蔬、肉禽与水产。券有效期七天，每个账号限领一张。",
      "全国", "满 100 减 30", "券后最低 7 折", "不与限时折扣商品叠加", 5, -4, 10),
    A("deals", ["优惠券领取"], "新客首单立减 20 元",
      "新注册用户首单立减 20 元，无门槛。下单页自动抵扣，每个账号仅一次，退款后不返还。",
      "全国", "首单减 20 元", None, "仅限首次下单账号，虚拟商品不参与", 5, -3, 25),
    A("deals", ["限时折扣"], "周末限时折扣 全场 8 折",
      "周六周日全场 8 折，覆盖日用百货与零食。折扣在结算页自动生效，不与其他券叠加。",
      "上海", "全场 8 折", None, "特价区与联营商品不参与", 5, -2, 6),
    A("deals", ["赠品活动"], "买二送一 日用品专场",
      "日用品专场买二送一，洗衣液、纸品与清洁剂均参与。赠品随单发出，数量有限赠完即止。",
      "全国", "买二送一", None, "赠品不与满减同享", 5, -1, 12, AD_STATUS_REJECTED),
    A("deals", ["限时折扣"], "社区团购 果蔬次日达 9.9 元起",
      "社区团购果蔬次日达，自提点覆盖主要社区，9.9 元起。当天 22 点前下单次日到自提点，缺货自动退款。",
      "全国", "9.9 元起", None, "生鲜类不支持无理由退货，坏果可申请赔付", 5, -12, 20),
    A("deals", ["优惠券领取"], "洗衣液 4 公斤 组合装优惠券",
      "洗衣液 4 公斤组合装可用券，满 79 减 15。券在店铺首页领取，领取后七天内有效。",
      "全国", "券后 64 元", "满 79 减 15", None, 5, -6, 22),
    A("deals", ["满减活动"], "米面粮油 满 199 减 50",
      "米面粮油专区满 199 减 50，覆盖大米、面粉与食用油。可跨品类凑单，结算页自动计算。",
      "全国", "满 199 减 50", None, "不与其他满减活动叠加", 5, -8, 18),
    A("deals", ["限时折扣"], "小家电清仓 限时 5 折",
      "小家电清仓限时 5 折，含电水壶、煮蛋器与料理机。库存有限，售完不补，均为全新未拆封。",
      "全国", "5 折起", None, "清仓商品不支持七天无理由退货", 5, -9, 11),
    A("deals", ["赠品活动"], "下单赠收纳袋 限量 500 份",
      "下单满 59 元赠折叠收纳袋一只，限量 500 份。赠品不单独发货，随主商品一起寄出。",
      "全国", "满 59 赠收纳袋", None, "赠品赠完即止，不以缺赠品为由退货", 5, -2, 15, AD_STATUS_PENDING),
    A("deals", ["满减活动"], "会员日 满 88 减 18",
      "每月 18 日会员日满 88 减 18，会员与普通用户均可参与。满减在结算页自动生效。",
      "全国", "满 88 减 18", None, None, 5, -14, 26),
    # ---- 本地生活服务 10（8 在架 / 1 过期 / 1 下架）----
    A("local-service", ["维修安装"], "空调清洗 上门 深度除菌 88 元",
      "空调深度清洗上门服务，含滤网、蒸发器与风轮除菌。师傅自带防护垫，清洗后出水检测，市区当日可约。",
      "深圳", "88 元/台", None, "仅限深圳市内，需现场有水源与电源", 3, -11, 30),
    A("local-service", ["家政保洁"], "家政保洁 4 小时 含擦玻璃",
      "家政保洁 4 小时套餐，含日常清洁、厨房卫生间重点清理与玻璃擦拭。阿姨自带工具与清洁剂。",
      "深圳", "199 元/4 小时", "首次下单立减 30 元", "仅限深圳市内，超出范围需加收交通费", 3, -13, 28),
    A("local-service", ["维修安装"], "水管漏水维修 30 分钟上门",
      "水管漏水维修，市区 30 分钟响应，含检测与常见配件更换。上门先报价，确认后再施工。",
      "深圳", "上门费 30 元", None, "夜间 22 点后加收夜间服务费", 3, -16, 24),
    A("local-service", ["维修安装"], "油烟机拆洗 免拆机 129 元",
      "油烟机免拆机深度清洗，高温蒸汽加专用清洗剂，含油杯与滤网清理。清洗过程铺防护膜，不脏厨房。",
      "深圳", "129 元/台", None, "仅限深圳市内，集成灶需另行咨询", 3, -18, 26),
    A("local-service", ["美容美发"], "美发造型 洗剪吹 49 元",
      "洗剪吹造型 49 元，含洗发、头皮按摩与吹造型。设计师一对一沟通，不含烫染项目。",
      "深圳", "49 元", "工作日到店再减 10 元", "需提前一天预约，周末不可用", 3, -10, 20),
    A("local-service", ["餐饮到店"], "火锅双人套餐 到店 128 元",
      "火锅双人套餐，含锅底、四荤四素与饮品两杯。堂食可用，节假日通用，需提前一小时预约。",
      "深圳", "128 元/双人", None, "仅限堂食，不与其他优惠同享", 3, -35, 20, AD_STATUS_EXPIRED),
    A("local-service", ["餐饮到店"], "粤式早茶 四人套餐 168 元",
      "粤式早茶四人套餐，含虾饺、烧卖、肠粉、凤爪与粥品，配茶位。早市 7 点至 11 点供应。",
      "深圳", "168 元/四人", None, "仅限早市时段，节假日需排队", 3, -7, 22),
    A("local-service", ["家政保洁"], "深度保洁 搬家前开荒 6 元/㎡",
      "搬家前开荒保洁，6 元每平方米，含除尘、除胶与玻璃清洗。按实际面积结算，先看现场再报价。",
      "深圳", "6 元/㎡", "满 300 减 30", "仅限深圳市内，家具未进场时效果最佳", 3, -20, 30),
    A("local-service", ["美容美发"], "染发护理 套餐 198 元",
      "植物染发加头皮护理套餐 198 元，含染前头皮隔离与染后护理。色板可选，深色系不加价。",
      "深圳", "198 元", None, "需提前预约，过敏体质请先做皮试", 3, -6, 18),
    A("local-service", ["维修安装"], "冰箱维修 上门检测免费",
      "冰箱不制冷、结冰、异响上门检测免费，维修配件另计。师傅持证上岗，维修后同一故障保修 90 天。",
      "深圳", "检测免费", None, "仅限深圳市内，需现场有电梯或可搬运通道", 3, -15, 25, AD_STATUS_OFFLINE),
    # ---- 服饰与美妆 4（3 在架 / 1 待审）----
    A("fashion", ["服饰鞋包"], "纯棉基础款 T 恤 两件装 99 元",
      "纯棉基础款 T 恤两件装，260 克重磅面料，领口双层包边不易变形。男女同款，颜色可自选。",
      "全国", "两件 99 元", "满 99 减 10", "贴身衣物非质量问题不支持退换", 6, -12, 26),
    A("fashion", ["护肤彩妆"], "氨基酸洁面 120ml 温和不紧绷",
      "氨基酸洁面 120ml，弱酸性配方，泡沫细腻，洗后不紧绷。国产备案，备案编号在商品详情页可查。",
      "全国", "到手 69 元", "第二件半价", "敏感肌建议先在耳后试用", 6, -9, 24),
    A("fashion", ["配饰珠宝"], "925 银项链 轻奢款 含礼盒",
      "925 银项链，镀白金工艺，含礼盒与擦银布。链长 40 加 5 厘米延长链，日常佩戴不易褪色。",
      "全国", "到手 139 元", None, None, 6, -5, 20, AD_STATUS_PENDING),
    A("fashion", ["服饰鞋包"], "轻薄羽绒服 90 绒 短款 到手 399",
      "90 白鸭绒轻薄羽绒服，短款立领，可收纳进随附收纳袋。充绒量 90 克，适合 0℃ 到 10℃ 通勤。",
      "全国", "到手 399 元", "满 399 减 40", None, 6, -8, 28),
    # ---- 运动户外与宠物 3（3 在架）----
    A("sports-pet", ["宠物用品"], "猫粮 无谷 2kg 成猫 到手 89",
      "无谷成猫粮 2kg，鲜肉添加，颗粒大小适中。包装标注完整配料表与营养成分，开封后建议一个月内吃完。",
      "全国", "到手 89 元", "买二袋减 30", "食品类拆封后不支持退换", 7, -10, 30),
    A("sports-pet", ["宠物服务"], "宠物洗护 上门接送 6 折",
      "宠物洗护含洗澡、吹干、修脚毛与挤肛门腺，市区内上门接送。一宠一巾，洗护间独立。",
      "北京", "6 折起", None, "仅限北京市内，需提供免疫记录", 7, -4, 30),
    A("sports-pet", ["运动健身"], "瑜伽垫 加厚防滑 6mm 到手 79",
      "6mm 加厚瑜伽垫，TPE 材质双面防滑，附背带。回弹好不塌陷，家用与健身房都合适。",
      "全国", "到手 79 元", None, None, 7, -14, 32),
]


def _reset_database() -> None:
    """删表重建（``--reset``），同时清掉上一轮遗留的封面文件。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    for legacy in COVERS_DIR.glob("ad-*.svg"):
        try:
            legacy.unlink()
        except OSError:
            pass


def seed(reset: bool = False, with_events: bool = True) -> dict[str, int]:
    """执行种子灌入，返回统计。"""
    if reset:
        _reset_database()
    else:
        init_db()

    settings = get_settings()
    db = SessionLocal()
    stats = {
        "categories": 0,
        "tags": 0,
        "merchants": 0,
        "ads": 0,
        "covers": 0,
        "events": 0,
        "favorites": 0,
        "reports": 0,
    }
    try:
        if db.query(Category).count() > 0 and not reset:
            print("数据库已存在种子数据，跳过。需要重灌请使用 --reset")
            return stats

        now = now_utc()
        today_cst = to_cst(now).date()

        # ---------------- 类别与标签
        category_map: dict[str, Category] = {}
        tag_map: dict[tuple[str, str], Tag] = {}
        tag_by_name: dict[tuple[str, str], Tag] = {}
        for item in CATEGORY_SEEDS:
            category = Category(
                slug=str(item["slug"]),
                name=str(item["name"]),
                intro=str(item["intro"]),
                sort_order=int(item["sort_order"]),
                is_active=True,
                created_at=now,
            )
            db.add(category)
            db.flush()
            category_map[category.slug] = category
            for order, (tag_name, tag_slug) in enumerate(item["tags"], start=1):
                tag = Tag(
                    category_id=category.id,
                    name=str(tag_name),
                    slug=str(tag_slug),
                    sort_order=order,
                    is_active=True,
                    created_at=now,
                )
                db.add(tag)
                db.flush()
                tag_map[(category.slug, str(tag_slug))] = tag
                tag_by_name[(category.slug, tag.name)] = tag
        stats["categories"] = len(category_map)
        stats["tags"] = len(tag_map)

        # ---------------- 管理员
        admin = AdminUser(
            username=settings.admin_username,
            display_name=settings.admin_display_name,
            password_hash=hash_password(settings.admin_password),
            role="admin",
            is_active=True,
            failed_attempts=0,
            created_at=now,
        )
        db.add(admin)

        # ---------------- 商家
        merchant_password = "adx-merchant-2026"
        merchants: list[Merchant] = []
        for index, item in enumerate(MERCHANT_SEEDS):
            merchant = Merchant(
                name=str(item["name"]),
                contact_name=str(item["contact_name"]),
                phone=str(item["phone"]),
                email=str(item["email"]),
                password_hash=hash_password(merchant_password),
                city=str(item["city"]),
                main_category_id=category_map[str(item["category_slug"])].id,
                status="active",
                verified=bool(item["verified"]),
                created_at=now - timedelta(days=120 - index * 9),
                updated_at=now - timedelta(days=120 - index * 9),
            )
            db.add(merchant)
            merchants.append(merchant)
        db.flush()
        stats["merchants"] = len(merchants)

        # ---------------- 广告
        for index, item in enumerate(AD_SEEDS, start=1):
            category = category_map[str(item["cat"])]
            merchant = merchants[int(item["merchant"])]
            start_day = today_cst + timedelta(days=int(item["start"]))
            end_day = start_day + timedelta(days=int(item["days"]) - 1)
            valid_from = parse_cst_date_start(start_day.isoformat())
            valid_to = parse_cst_date_end(end_day.isoformat())
            status = str(item["status"])
            submitted_at = None
            published_at = None
            if status != "draft":
                submitted_at = now - timedelta(hours=2 + index % 20)
            if status in (AD_STATUS_ACTIVE, AD_STATUS_EXPIRED, AD_STATUS_OFFLINE):
                published_at = min(valid_from + timedelta(hours=6), now)

            ad = Ad(
                merchant_id=merchant.id,
                category_id=category.id,
                title=str(item["title"]),
                description=str(item["desc"]),
                city=str(item["city"]),
                price_text=item["price"],  # type: ignore[arg-type]
                promo_condition=item["promo"],  # type: ignore[arg-type]
                restriction=item["restriction"],  # type: ignore[arg-type]
                valid_from=valid_from,
                valid_to=valid_to,
                landing_url=f"https://www.example.com/{merchant.id}/{index}",
                landing_domain="www.example.com",
                image_path="",
                status=status,
                precheck_note="预检通过：无禁投词，落地页安全",
                submitted_at=submitted_at,
                published_at=published_at,
                created_at=now - timedelta(days=3 + index % 27),
                updated_at=now - timedelta(days=1 + index % 5),
            )
            if status == AD_STATUS_REJECTED:
                ad.reject_reason_code = "incomplete"
                ad.reject_reason = "信息不完整或不实：缺少必要的规格与售后说明，请补充后重新提交"
            if status == AD_STATUS_OFFLINE:
                ad.offline_reason = "管理员下架：经核查服务范围描述与实际不符"
            db.add(ad)
            db.flush()

            ad.image_path = write_cover_file(ad.id, ad.title, category.slug)
            stats["covers"] += 1

            for tag_slug in item["tags"]:  # type: ignore[union-attr]
                tag = tag_map.get((category.slug, str(tag_slug))) or tag_by_name.get(
                    (category.slug, str(tag_slug))
                )
                if tag is not None:
                    db.add(AdTag(ad_id=ad.id, tag_id=tag.id))

            if status == AD_STATUS_PENDING:
                log_review(db, ad, "submit", "merchant", merchant.id)
            elif status == AD_STATUS_REJECTED:
                log_review(db, ad, "submit", "merchant", merchant.id)
                log_review(db, ad, "reject", "admin", 1, reason=ad.reject_reason)
            elif status == AD_STATUS_OFFLINE:
                log_review(db, ad, "submit", "merchant", merchant.id)
                log_review(db, ad, "approve", "admin", 1)
                log_review(db, ad, "offline", "admin", 1, reason=ad.offline_reason)
            elif status in (AD_STATUS_ACTIVE, AD_STATUS_EXPIRED):
                log_review(db, ad, "submit", "merchant", merchant.id)
                log_review(db, ad, "approve", "admin", 1)
            elif status == AD_STATUS_SCHEDULED:
                log_review(db, ad, "submit", "merchant", merchant.id)
                log_review(db, ad, "approve", "admin", 1, reason="开始时间在未来，置为待生效")
            stats["ads"] += 1

        db.commit()

        # ---------------- 演示访客 + 收藏（用于"最多收藏"排序与收藏页演示）
        rng = random.Random(20261027)
        demo_visitors: list[Visitor] = []
        for index in range(12):
            visitor = Visitor(
                id=f"demo-visitor-{index:02d}",
                first_seen=now - timedelta(days=20 - index),
                last_seen=now - timedelta(hours=index),
            )
            db.add(visitor)
            demo_visitors.append(visitor)
        db.commit()

        active_ads = db.query(Ad).filter(Ad.status == AD_STATUS_ACTIVE).all()
        favorite_rows: list[tuple[str, int, datetime]] = []
        for visitor in demo_visitors:
            picks = rng.sample(active_ads, k=min(6, len(active_ads)))
            for offset, ad in enumerate(picks):
                # 收藏时间落在近 7 天窗口内，保证"近 7 天"口径的收藏数/收藏率不为 0
                created = now - timedelta(days=rng.randint(0, 6), hours=offset)
                db.add(Favorite(visitor_id=visitor.id, ad_id=ad.id, created_at=created))
                favorite_rows.append((visitor.id, ad.id, created))
                stats["favorites"] += 1
        db.commit()

        # ---------------- 演示举报（覆盖 pending / reviewing / resolved / dismissed 四种状态）
        stats["reports"] = _seed_reports(db, active_ads, demo_visitors, admin.id, rng)

        # ---------------- 演示事件
        if with_events:
            favorite_events = _seed_favorite_events(db, favorite_rows)
            report_events = _seed_report_events(db, rng)
            stats["events"] = (
                _seed_events(db, active_ads, demo_visitors, rng) + favorite_events + report_events
            )

        print(
            "种子数据完成：类别 {categories} / 标签 {tags} / 商家 {merchants} / 广告 {ads} / 封面 {covers} / "
            "事件 {events} / 收藏 {favorites} / 举报 {reports}".format(**stats)
        )
        print(f"数据库文件：{DB_PATH}")
        print(f"封面目录：{COVER_URL_PREFIX}/ （{stats['covers']} 个 SVG）")
        print(f"管理员账号：{settings.admin_username} / {settings.admin_password}（首次登录后请立即修改）")
        merchants_preview = "、".join(f"{m.name}({m.phone})" for m in merchants[:3])
        print(f"商家账号示例：{merchants_preview} 密码统一为 {merchant_password}")
        return stats
    finally:
        db.close()


def _seed_favorite_events(db, rows: list[tuple[str, int, datetime]]) -> int:
    """为每条 Demo 收藏补写一条 ``favorite`` 事件（同 visitor / ad / 时间戳）。

    收藏事件是商家报告「收藏数」「收藏率」与后台总览的唯一数据来源，
    缺失会让这两个指标恒为 0，所以必须与 favorites 表一一对应。
    """
    for visitor_id, ad_id, created_at in rows:
        db.add(
            Event(
                id=str(uuid.uuid4()),
                event_type="favorite",
                ad_id=ad_id,
                visitor_id=visitor_id,
                session_id=str(uuid.uuid4()),
                ts=created_at,
                page="detail",
                position=None,
                meta=None,
            )
        )
    db.commit()
    return len(rows)


def _seed_reports(db, active_ads: list[Ad], visitors: list[Visitor], admin_id: int, rng: random.Random) -> int:
    """生成 4 条举报：1 条 SLA 超时 pending、1 条 reviewing、1 条 resolved（广告已下架）、1 条 dismissed。

    举报码规则与 ``ReportService`` 一致：``RP-`` + 8 位大写字母数字，排除 I/L/O/0/1。
    """
    now = now_utc()
    offline_ads = db.query(Ad).filter(Ad.status == AD_STATUS_OFFLINE).all()
    fallback_ad = active_ads[0]

    def snapshot(ad: Ad) -> str:
        return json.dumps(
            {
                "ad_id": ad.id,
                "title": ad.title,
                "merchant_name": ad.merchant.name if ad.merchant is not None else "",
                "status": ad.status,
                "image_path": ad.image_path,
            },
            ensure_ascii=False,
        )

    offline_target = offline_ads[0] if offline_ads else fallback_ad
    candidates = [ad for ad in active_ads if ad.id != offline_target.id] or active_ads

    plans: list[dict[str, object]] = [
        {
            "code": "RP-7X4KQ2MW",
            "ad": candidates[0],
            "reason_code": "false_claim",
            "detail": "页面写「直降 500 元」，点进去实际只降 100 元，价格前后不一致。",
            "status": "pending",
            "created_at": now - timedelta(hours=60),
            "handled_at": None,
            "admin_note": None,
        },
        {
            "code": "RP-3NP8RT5Y",
            "ad": candidates[1 % len(candidates)],
            "reason_code": "price_wrong",
            "detail": "宣传价格是到手价，结算页还有一笔运费没有提前说明。",
            "status": "reviewing",
            "created_at": now - timedelta(hours=20),
            "handled_at": None,
            "admin_note": "已受理，正在与商家核实价格口径。",
        },
        {
            "code": "RP-9WH6CZ2K",
            "ad": offline_target,
            "reason_code": "suspicious_link",
            "detail": "落地页跳转到非商家官网的收款页面，要求私下转账。",
            "status": "resolved",
            "created_at": now - timedelta(days=5),
            "handled_at": now - timedelta(days=4),
            "admin_note": "核实存在诱导私下交易，已要求整改并下架该广告。",
        },
        {
            "code": "RP-5JV2MD7Q",
            "ad": candidates[2 % len(candidates)],
            "reason_code": "inappropriate",
            "detail": "图片里有其他平台的二维码，怀疑是搬运素材。",
            "status": "dismissed",
            "created_at": now - timedelta(days=3),
            "handled_at": now - timedelta(days=2),
            "admin_note": "已核对素材授权，未发现违规，举报不成立。",
        },
    ]

    for plan in plans:
        ad = plan["ad"]
        assert isinstance(ad, Ad)
        report = Report(
            code=str(plan["code"]),
            ad_id=ad.id,
            visitor_id=visitors[rng.randint(0, len(visitors) - 1)].id,
            reason_code=str(plan["reason_code"]),
            detail=str(plan["detail"]),
            status=str(plan["status"]),
            admin_note=plan["admin_note"],
            ad_snapshot=snapshot(ad),
            handled_by=admin_id if plan["handled_at"] is not None else None,
            created_at=plan["created_at"],
            updated_at=plan["handled_at"] or plan["created_at"],
            handled_at=plan["handled_at"],
        )
        db.add(report)
        db.flush()
        if report.status == "resolved":
            db.add(
                ReportFollowup(
                    report_id=report.id,
                    visitor_id=report.visitor_id,
                    note="谢谢处理，已经看不到那条广告了。",
                    created_at=now - timedelta(days=3, hours=12),
                )
            )
    db.commit()
    return len(plans)


def _seed_report_events(db, rng: random.Random) -> int:
    """每条举报补一条 ``report`` 事件（后台总览/商家报告的举报数来源）。"""
    reports = db.query(Report).all()
    for report in reports:
        db.add(
            Event(
                id=str(uuid.uuid4()),
                event_type="report",
                ad_id=report.ad_id,
                visitor_id=report.visitor_id,
                session_id=str(uuid.uuid4()),
                ts=report.created_at,
                page="detail",
                position=None,
                meta=json.dumps({"reason_code": report.reason_code}, ensure_ascii=False),
            )
        )
    db.commit()
    return len(reports)


def _seed_events(db, active_ads: list[Ad], visitors: list[Visitor], rng: random.Random) -> int:
    """按 7 天窗口生成展示/详情/点击/收藏/举报事件，便于报告与统计页演示。"""
    now = now_utc()
    pages = ["home", "list", "search", "detail", "favorites"]
    count = 0
    total_impressions = 0
    total_detail_views = 0
    for ad in active_ads:
        impressions = rng.randint(6, 26)
        total_impressions += impressions
        for order in range(impressions):
            visitor = rng.choice(visitors)
            ts = now - timedelta(days=rng.randint(0, 6), minutes=rng.randint(0, 1400))
            db.add(
                Event(
                    id=str(uuid.uuid4()),
                    event_type="impression",
                    ad_id=ad.id,
                    visitor_id=visitor.id,
                    session_id=str(uuid.uuid4()),
                    ts=ts,
                    page=rng.choice(pages[:3]),
                    position=order % 24,
                    meta=json.dumps({"sort": "latest"}, ensure_ascii=False),
                )
            )
            count += 1
        detail_views = rng.randint(2, 9)
        total_detail_views += detail_views
        for _ in range(detail_views):
            visitor = rng.choice(visitors)
            ts = now - timedelta(days=rng.randint(0, 6), minutes=rng.randint(0, 1400))
            db.add(
                Event(
                    id=str(uuid.uuid4()),
                    event_type="detail_view",
                    ad_id=ad.id,
                    visitor_id=visitor.id,
                    session_id=str(uuid.uuid4()),
                    ts=ts,
                    page="detail",
                    position=None,
                    meta=None,
                )
            )
            count += 1
        for _ in range(rng.randint(0, 5)):
            visitor = rng.choice(visitors)
            ts = now - timedelta(days=rng.randint(0, 6), minutes=rng.randint(0, 1400))
            db.add(
                Event(
                    id=str(uuid.uuid4()),
                    event_type="link_click",
                    ad_id=ad.id,
                    visitor_id=visitor.id,
                    session_id=str(uuid.uuid4()),
                    ts=ts,
                    page="detail",
                    position=None,
                    meta=None,
                )
            )
            count += 1
    # 页面访问按曝光量等比生成，保证「首页 ≥ 列表/搜索 ≥ 详情 ≥ 外链」漏斗单调递减
    page_plan = [
        ("home", int(total_impressions * 1.25)),
        ("list", int(total_impressions * 0.45)),
        ("search", int(total_impressions * 0.12)),
        ("favorites", max(6, int(total_detail_views * 0.08))),
    ]
    for page, amount in page_plan:
        for _ in range(max(1, amount)):
            visitor = rng.choice(visitors)
            db.add(
                Event(
                    id=str(uuid.uuid4()),
                    event_type="page_view",
                    ad_id=None,
                    visitor_id=visitor.id,
                    session_id=str(uuid.uuid4()),
                    ts=now - timedelta(days=rng.randint(0, 6), minutes=rng.randint(0, 1400)),
                    page=page,
                    position=None,
                    meta=None,
                )
            )
            count += 1
    db.commit()
    return count


def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser(description="广告发现站种子数据")
    parser.add_argument("--reset", action="store_true", help="删库重建")
    parser.add_argument("--no-events", action="store_true", help="不生成演示事件")
    args = parser.parse_args()
    seed(reset=args.reset, with_events=not args.no_events)


if __name__ == "__main__":
    main()
