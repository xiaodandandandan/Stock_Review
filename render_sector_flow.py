# -*- coding: utf-8 -*-
"""小红书版 全市场·板块资金流动 静态长图（2026.09.08）"""
import os
from PIL import Image, ImageDraw, ImageFont

SS = 2
W = 1080
CW = W*SS

FD = os.path.dirname(os.path.abspath(__file__))
F_BOLD = os.path.join(FD, 'fonts', 'NotoSansSC-Bold.otf')
F_REG  = os.path.join(FD, 'fonts', 'NotoSansSC-Regular.otf')

BG   = (250, 250, 247)
CARD = (255, 255, 255)
INK  = (26, 26, 26)
INK2 = (51, 51, 51)
GRAY = (112, 120, 132)
LINE = (232, 232, 227)
XRED = (255, 36, 66)
UP   = (217, 58, 63)
UPBG = (253, 232, 232)
DOWN = (43, 138, 90)
DNBG = (227, 244, 235)
AMB  = (217, 119, 6)
BAR_BG = (238, 238, 233)

def F(sz, bold=True):
    return ImageFont.truetype(F_BOLD if bold else F_REG, int(sz*SS))

MX = 40
CWX = W - 2*MX

# ---------------- 数据（申万一级行业，净主动买入额合计，单位：亿元） ----------------
# 正值=净流入（红），负值=净流出（绿）
DATA = [
    ("基础化工", 44.18, "化肥/民爆/磷化工/有机硅涨价周期"),
    ("有色金属", 41.23, "铜/铝/锂/稀土·资源品抢筹"),
    ("石油石化", 31.09, "油服/炼化·油价上行+改革预期"),
    ("公用事业", 25.42, "电力/燃气·防御属性受捧"),
    ("医药生物", 23.52, "原料药/中药/生物·估值修复"),
    ("钢铁", 18.02, "钢材涨价+并购重组"),
    ("银行", 15.39, "国有大行/城商行·高股息防御"),
    ("国防军工", 13.03, "航天/兵器·板块轮动补涨"),
    ("建筑装饰", 12.79, "基建央企/地方国企"),
    ("房地产", 11.77, "地产服务+开发·政策修复"),
    ("煤炭", 8.62, "动力煤/焦煤·高分红"),
    ("环保", 4.37, "水处理/固废"),
    ("建筑材料", 2.95, "水泥/玻纤"),
    ("纺织服饰", 2.61, "出口链+品牌"),
    ("交通运输", 1.89, "港口/公路"),
    ("美容护理", -0.07, "化妆品/医美微跌"),
    ("社会服务", -0.08, "旅游/教育微跌"),
    ("轻工制造", -0.16, "造纸/家居小幅流出"),
    ("商贸零售", -0.22, "百货/超市微跌"),
    ("综合", -0.52, "综合类小幅流出"),
    ("家用电器", -0.94, "白电/厨电回调"),
    ("食品饮料", -1.29, "白酒/食品回调"),
    ("农林牧渔", -1.32, "养殖/种植流出"),
    ("传媒", -1.48, "出版/影视获利了结"),
    ("汽车", -2.16, "整车/零部件分化"),
    ("通信", -3.14, "光通信/射频流出"),
    ("非银金融", -4.01, "券商/保险调整"),
    ("电力设备", -5.02, "光伏/风电/储能失血"),
    ("机械设备", -5.31, "通用/专用设备流出"),
    ("计算机", -9.02, "软件/IT服务大幅流出"),
    ("电子", -19.48, "半导体/消费电子重挫·科技最大失血"),
]

INSIGHTS = [
    "① 资源周期称霸：化工+有色+石化合计净流入116亿，涨价主线全市场共识",
    "② 科技成长失血：电子-19.5+计算机-9.0+通信-3.1合计-31.6亿，为最大流出区",
    "③ 防御+高股息受捧：公用事业+25.4、银行+15.4、煤炭+8.6，避险情绪升温",
    "④ 风格切换信号：周期/资源净流入 vs 科技成长净流出，市场风格从成长转向价值",
]

# ---------------- 布局 ----------------
HEADER = 270
SEC1_TITLE = 64
N_SECTORS = len(DATA)
BAR_ROW_H = 54
SEC1_PAD = 18
SEC1_H = SEC1_TITLE + N_SECTORS * BAR_ROW_H + SEC1_PAD

SEC2_TITLE = 64
SEC2_H = 40 + len(INSIGHTS) * 42 + 60

FOOT = 80
BOTTOM = 48

H = HEADER + SEC1_TITLE + SEC1_H + 30 + SEC2_TITLE + SEC2_H + FOOT + BOTTOM
H = int(H)
CH = H * SS
print('canvas', W, H)

img = Image.new('RGBA', (CW, CH), BG+(255,))
d = ImageDraw.Draw(img)

def draw_section_title(y, color, title, sub=''):
    d.ellipse([MX*SS, (y+12)*SS, (MX+20)*SS, (y+32)*SS], fill=color+(255,))
    d.text(((MX+36)*SS, (y+4)*SS), title, font=F(34), fill=INK+(255,))
    if sub:
        tw = d.textlength(sub, font=F(20, False))
        d.text(((MX+CWX-int(tw/SS)-10)*SS, (y+12)*SS), sub, font=F(20, False), fill=GRAY+(255,))
    return y + 64

# ---------- 标题区 ----------
d.rounded_rectangle([MX*SS, 48*SS, (MX+380)*SS, 100*SS], radius=26*SS, fill=XRED+(255,))
d.text(((MX+26)*SS, 61*SS), '全市场 · 板块资金流', font=F(27), fill=(255,255,255,255))
d.rounded_rectangle([812*SS, 48*SS, 1040*SS, 100*SS], radius=26*SS, outline=GRAY+(200,), width=2*SS)
d.text((926*SS, 61*SS), '2026.09.08 收盘', font=F(25, False), fill=GRAY+(255,))
d.text((MX*SS, 118*SS), '周期流入 · 科技失血', font=F(56), fill=INK+(255,))
d.rectangle([(MX+2)*SS, 196*SS, (MX+200)*SS, 202*SS], fill=XRED+(255,))
d.text((MX*SS, 208*SS), '31个申万一级行业 · 化工+44亿居首 · 电子-19.5亿垫底', font=F(27, False), fill=GRAY+(255,))

# ---------- Sec1 板块资金流 ----------
y = HEADER
d.rounded_rectangle([MX*SS, y*SS, (MX+CWX)*SS, (y+SEC1_H)*SS],
                    radius=16*SS, fill=CARD+(255,), outline=LINE+(255,), width=2*SS)
y = draw_section_title(y, UP, '板块资金净流入排行', '31板块 · 净主动买入额(亿元)')

# 计算条形图参数
yy = y
# 中心线位置（0值线）
BAR_NAME_W = 120   # 名称区宽
BAR_NOTE_X = MX + BAR_NAME_W + 24  # 备注起始x
BAR_AREA_X0 = MX + BAR_NAME_W + 24  # 条形区起始
BAR_AREA_W = CWX - BAR_NAME_W - 24 - 80  # 条形区宽，右边留80给数值
CENTER_X = BAR_AREA_X0 + BAR_AREA_W // 2  # 中心线
HALF_W = BAR_AREA_W // 2 - 6  # 半宽

max_abs = max(abs(v) for _, v, _ in DATA)

for name, val, note in DATA:
    color = UP if val >= 0 else DOWN
    # 板块名称
    d.text(((MX+4)*SS, (yy+16)*SS), name, font=F(22), fill=INK+(255,))
    # 备注说明
    d.text(((MX+BAR_NAME_W+28)*SS, (yy+20)*SS), note, font=F(18, False), fill=GRAY+(255,))

    # 条形
    bar_y = (yy + 8) * SS
    bar_h = 22 * SS
    # 背景条
    d.rounded_rectangle([BAR_AREA_X0*SS, bar_y, (BAR_AREA_X0+BAR_AREA_W-80)*SS, bar_y+bar_h],
                        radius=6*SS, fill=BAR_BG+(255,))

    ratio = abs(val) / max_abs
    bar_len = int(HALF_W * ratio * SS)

    if val >= 0:
        x0 = CENTER_X * SS
        x1 = (CENTER_X + int(HALF_W * ratio)) * SS
        d.rounded_rectangle([x0, bar_y, x1, bar_y+bar_h],
                            radius=6*SS, fill=color+(255,))
    else:
        x1 = CENTER_X * SS
        x0 = (CENTER_X - int(HALF_W * ratio)) * SS
        d.rounded_rectangle([x0, bar_y, x1, bar_y+bar_h],
                            radius=6*SS, fill=color+(255,))

    # 中心线
    d.line([CENTER_X*SS, bar_y, CENTER_X*SS, bar_y+bar_h], fill=GRAY+(160,), width=1*SS)

    # 数值标签
    sign = '+' if val >= 0 else ''
    val_text = sign + ("%.2f" % val) + '亿'
    val_color = color
    if val >= 0:
        d.text(((CENTER_X + HALF_W + 8)*SS, (yy+14)*SS), val_text, font=F(22, True), fill=val_color+(255,), anchor='lm')
    else:
        d.text(((CENTER_X - HALF_W - 8)*SS, (yy+14)*SS), val_text, font=F(22, True), fill=val_color+(255,), anchor='rm')

    yy += BAR_ROW_H

y = HEADER + SEC1_TITLE + SEC1_H + 30

# ---------- Sec2 核心结论 ----------
d.rounded_rectangle([MX*SS, y*SS, (MX+CWX)*SS, (y+SEC2_H)*SS],
                    radius=16*SS, fill=CARD+(255,), outline=LINE+(255,), width=2*SS)
d.rectangle([MX*SS, (y+18)*SS, (MX+6)*SS, (y+54)*SS], fill=XRED+(255,))
d.text(((MX+26)*SS, (y+10)*SS), '核心结论', font=F(32), fill=INK+(255,))
yy = y + 70
for s in INSIGHTS:
    d.text(((MX+26)*SS, yy*SS), s, font=F(25, False), fill=INK2+(255,))
    yy += 42

# ---------- 底部 ----------
fy = y + SEC2_H + 28
d.text((MX*SS, fy*SS),
       '口径：申万一级行业 · 净主动买入额(合计) · 全市场全量A股',
       font=F(20, False), fill=GRAY+(230,))
d.text((MX*SS, (fy+30)*SS),
       '数据：同花顺 iFinD ｜ 仅供学习参考，不构成投资建议',
       font=F(20, False), fill=GRAY+(230,))

out = img.resize((W, H), Image.LANCZOS).convert('RGB')
out_path = os.path.join(FD, 'sector_flow_0908.png')
out.save(out_path, quality=95)
print('saved', out_path, out.size)
