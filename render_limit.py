# -*- coding: utf-8 -*-
"""小红书版 涨跌停·板块全景 静态长图（2026.09.08）"""
import math, os
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
GNBG = (254, 243, 217)

def F(sz, bold=True):
    return ImageFont.truetype(F_BOLD if bold else F_REG, int(sz*SS))

MX = 40
CWX = W - 2*MX

# ---------------- 数据 ----------------
# (行业, 家数, 备注)
INDUSTRY = [
    ("基础化工", 14, "化肥/纯碱/磷化工/有机硅"),
    ("传媒", 8, "出版+影视全线"),
    ("农林牧渔", 8, "种业+制糖+种植"),
    ("房地产", 5, "地产服务+开发"),
    ("商贸零售", 5, "百货+超市"),
    ("医药生物", 5, "原料药+中药+生物"),
    ("食品饮料", 4, "糖/功能糖/食品"),
    ("电子", 3, "PCB+LED"),
    ("通信", 3, "光通信+射频"),
    ("石油石化", 3, "油服+炼化"),
    ("家用电器", 3, "炊具+卫浴+热管理"),
    ("其他行业", 13, "汽车/机械/公用/建筑等"),
]

THEMES = [
    ("① 化工涨价周期", 14, "化肥·纯碱·磷化工·有机硅"),
    ("② 传媒/出版", 8, "出版 + 影视主升"),
    ("③ 农业/种业/制糖", 8, "糖价 + 种业 + 种植"),
    ("④ 房地产链", 5, "地产政策修复"),
    ("⑤ 消费/零售/食品", 9, "商超百货 + 食品饮料"),
]

LADDERS = [
    ("4板", ["爱仕达", "亚盛集团", "百大集团"], "3只 · 情绪最高标"),
    ("3板", ["海欣食品", "敦煌种业", "中国出版"], "3只 · 食品/农业/出版"),
    ("2板", ["中京电子", "百合花", "华盛昌", "读者传媒", "金正大", "中百集团",
             "集泰股份", "华体科技", "上海电影", "桂林旅游", "澳洋健康", "华脉科技"],
     "12只 · 梯队扩容"),
]

DOWNLIST = [
    ("中石科技", -15.46, "电子·散热", "龙虎榜净卖3.3亿"),
    ("天博智能", -16.14, "汽车·热管理", "高位重挫"),
    ("金钟股份", -13.01, "汽车", "高位补跌"),
    ("杰锋动力", -13.09, "汽车·北交所", "次新回落"),
    ("爱克股份", -10.00, "电子·LED", "闪崩"),
    ("高争民爆", -9.71, "基础化工·民爆", "龙虎榜净买2.3亿抄底"),
    ("深水海纳", -9.61, "环保", "高位补跌"),
    ("新炬网络", -9.32, "计算机", "龙虎榜净卖0.28亿"),
    ("思看科技", -9.19, "机械设备·机器视觉", "高位回落"),
    ("ST富煌", -10.02, "建筑装饰", "ST退市风险"),
]

SIGNALS = [
    '① 普涨vs分化：74只涨停 vs 10只跌超9%，指数偏暖但内部高低切',
    '② 化工主升回归：14只化工涨停，化肥·民爆·磷化工涨价周期启动',
    '③ 高标降温：最高仅4板(爱仕达/亚盛/百大)，较昨日情绪明显回落',
    '④ 跌停无板块性：重挫股分散汽车/电子/机械，多为高位补跌',
    '⑤ 单票定多空：龙虎榜盈新发展+4.2亿、博云新材-3亿主导方向',
]

# ---------------- 布局计算 ----------------
HEADER = 252
GAP = 30

def sec_card_h(n_rows, row_h, title_h=64, pad=18):
    return title_h + n_rows*row_h + pad

# Sec1 行业分布
R1 = 58
H1 = sec_card_h(len(INDUSTRY), R1)
# Sec2 题材主线
R2 = 80
H2 = sec_card_h(len(THEMES), R2)
# Sec3 连板梯队
R3 = 92
H3 = sec_card_h(3, R3)
# Sec4 跌停阵营
R4 = 58
H4 = sec_card_h(len(DOWNLIST), R4)
# Sec5 结论
H5 = 70 + len(SIGNALS)*40 + 26

H = HEADER + H1 + GAP + H2 + GAP + H3 + GAP + H4 + GAP + H5 + 96
H = int(H)
CH = H*SS
print('canvas', W, H)

img = Image.new('RGBA', (CW, CH), BG+(255,))
d = ImageDraw.Draw(img)

def sec_header(y, color, title, sub):
    d.rectangle([MX*SS, (y+18)*SS, (MX+6)*SS, (y+54)*SS], fill=color+(255,))
    d.text(((MX+26)*SS, (y+10)*SS), title, font=F(34), fill=INK+(255,))
    tw = d.textlength(sub, font=F(24, False))
    d.text(((MX+CWX-10-int(tw/SS))*SS, (y+24)*SS), sub, font=F(24, False), fill=color+(255,))

# ---------- 标题区 ----------
d.rounded_rectangle([MX*SS, 40*SS, (MX+346)*SS, 92*SS], radius=26*SS, fill=XRED+(255,))
d.text(((MX+26)*SS, 53*SS), '涨跌停 · 板块全景', font=F(27), fill=(255,255,255,255))
d.rounded_rectangle([812*SS, 40*SS, 1040*SS, 92*SS], radius=26*SS, outline=GRAY+(200,), width=2*SS)
d.text((926*SS, 53*SS), '2026.09.08 收盘', font=F(24, False), fill=GRAY+(255,))
d.text((MX*SS, 112*SS), '74涨停 vs 10跌超9%', font=F(58), fill=INK+(255,))
d.rectangle([(MX+2)*SS, 190*SS, (MX+186)*SS, 196*SS], fill=XRED+(255,))
d.text((MX*SS, 212*SS), '普涨但化工极端占优 · 高标仅4板', font=F(28, False), fill=GRAY+(255,))

# ---------- Sec1 涨停行业分布 ----------
y = HEADER
d.rounded_rectangle([MX*SS, y*SS, (MX+CWX)*SS, (y+H1)*SS], radius=16*SS,
                    fill=CARD+(255,), outline=LINE+(255,), width=2*SS)
sec_header(y, UP, '涨停板块分布', '74只 · 按申万行业')
yy = y + 64
maxv = max(v for _, v, _ in INDUSTRY)
BAR_X0, BAR_X1 = MX+250, MX+780
for name, v, note in INDUSTRY:
    d.text(((MX+24)*SS, (yy+10)*SS), name, font=F(26), fill=INK+(255,))
    bwid = int((BAR_X1-BAR_X0) * (v/maxv) * SS)
    if bwid > 0:
        d.rounded_rectangle([BAR_X0*SS, (yy+12)*SS, BAR_X0*SS+bwid, (yy+42)*SS],
                            radius=7*SS, fill=UP+(220,))
    d.text(((MX+798)*SS, (yy+8)*SS), "%d只" % v, font=F(28), fill=UP+(255,), anchor='rm')
    d.text(((MX+812)*SS, (yy+16)*SS), note, font=F(20, False), fill=GRAY+(255,))
    yy += R1
y += H1 + GAP

# ---------- Sec2 题材主线 ----------
d.rounded_rectangle([MX*SS, y*SS, (MX+CWX)*SS, (y+H2)*SS], radius=16*SS,
                    fill=CARD+(255,), outline=LINE+(255,), width=2*SS)
sec_header(y, XRED, '涨停题材主线', '按概念归集')
yy = y + 64
for name, v, note in THEMES:
    d.rounded_rectangle([(MX+24)*SS, (yy+14)*SS, (MX+240)*SS, (yy+62)*SS],
                        radius=10*SS, fill=UPBG+(255,))
    d.text(((MX+132)*SS, (yy+24)*SS), name, font=F(24), fill=UP+(255,), anchor='ma')
    d.text(((MX+290)*SS, (yy+8)*SS), "%d只" % v, font=F(34), fill=INK+(255,), anchor='rm')
    d.text(((MX+310)*SS, (yy+22)*SS), note, font=F(24, False), fill=GRAY+(255,))
    yy += R2
y += H2 + GAP

# ---------- Sec3 连板梯队 ----------
d.rounded_rectangle([MX*SS, y*SS, (MX+CWX)*SS, (y+H3)*SS], radius=16*SS,
                    fill=CARD+(255,), outline=LINE+(255,), width=2*SS)
sec_header(y, AMB, '连板梯队', '情绪标尺')
yy = y + 64
for lb, names, note in LADDERS:
    d.rounded_rectangle([(MX+24)*SS, (yy+16)*SS, (MX+108)*SS, (yy+64)*SS],
                        radius=10*SS, fill=AMB+(255,))
    d.text(((MX+66)*SS, (yy+28)*SS), lb, font=F(28), fill=(255,255,255,255), anchor='ma')
    if len(names) > 6:
        line1 = "、".join(names[:6])
        line2 = "、".join(names[6:])
        d.text(((MX+128)*SS, (yy+4)*SS), line1, font=F(24), fill=INK+(255,))
        d.text(((MX+128)*SS, (yy+38)*SS), line2, font=F(24), fill=INK+(255,))
    else:
        d.text(((MX+128)*SS, (yy+18)*SS), "、".join(names), font=F(26), fill=INK+(255,))
    tw = d.textlength(note, font=F(21, False))
    d.text(((MX+CWX-14-int(tw/SS))*SS, (yy+18)*SS), note, font=F(21, False), fill=GRAY+(255,))
    yy += R3
y += H3 + GAP

# ---------- Sec4 跌停阵营 ----------
d.rounded_rectangle([MX*SS, y*SS, (MX+CWX)*SS, (y+H4)*SS], radius=16*SS,
                    fill=CARD+(255,), outline=LINE+(255,), width=2*SS)
sec_header(y, DOWN, '跌停/重挫阵营', '10只 · 无板块性跌停')
yy = y + 64
for name, pct, board, note in DOWNLIST:
    d.text(((MX+24)*SS, (yy+12)*SS), name, font=F(26), fill=INK+(255,))
    d.text(((MX+250)*SS, (yy+10)*SS), "%.1f%%" % pct, font=F(28), fill=DOWN+(255,), anchor='rm')
    d.rounded_rectangle([(MX+270)*SS, (yy+14)*SS, (MX+470)*SS, (yy+44)*SS],
                        radius=8*SS, fill=DNBG+(255,))
    d.text(((MX+280)*SS, (yy+16)*SS), board, font=F(20), fill=DOWN+(255,))
    d.text(((MX+486)*SS, (yy+16)*SS), note, font=F(21, False), fill=GRAY+(255,))
    yy += R4
y += H4 + GAP

# ---------- Sec5 核心结论 ----------
d.rounded_rectangle([MX*SS, y*SS, (MX+CWX)*SS, (y+H5)*SS], radius=16*SS,
                    fill=CARD+(255,), outline=LINE+(255,), width=2*SS)
d.rectangle([MX*SS, (y+18)*SS, (MX+6)*SS, (y+54)*SS], fill=XRED+(255,))
d.text(((MX+26)*SS, (y+10)*SS), '核心结论', font=F(32), fill=INK+(255,))
yy = y + 70
for s in SIGNALS:
    d.text(((MX+26)*SS, yy*SS), s, font=F(25, False), fill=INK2+(255,))
    yy += 40
y += H5

# ---------- 底部 ----------
d.text((MX*SS, (y+30)*SS),
       '口径：收盘涨停74只(含一字) / 跌超9%重挫10只 · 涨停家数按申万一级行业归集',
       font=F(20, False), fill=GRAY+(230,))
d.text((MX*SS, (y+60)*SS),
       '数据：同花顺 iFinD ｜ 仅供学习参考，不构成投资建议',
       font=F(20, False), fill=GRAY+(230,))

out = img.resize((W, H), Image.LANCZOS).convert('RGB')
out_path = os.path.join(FD, 'limit_panorama_0908.png')
out.save(out_path, quality=95)
print('saved', out_path, out.size)