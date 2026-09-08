# -*- coding: utf-8 -*-
"""小红书版 龙虎榜·板块概念 静态长图（2026.09.08）"""
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
GRAY = (112, 120, 132)
LINE = (232, 232, 227)
XRED = (255, 36, 66)
UP   = (217, 58, 63)
UPBG = (253, 232, 232)
DOWN = (43, 138, 90)
DNBG = (227, 244, 235)
AMB  = (217, 119, 6)

def F(sz, bold=True):
    return ImageFont.truetype(F_BOLD if bold else F_REG, int(sz*SS))

MX = 40                        # 左右留白
CWX = W - 2*MX                 # 内容宽 = 1000

# ---------------- 数据 ----------------
BUY = [
    ("基础化工（化肥/民爆/磷化工）", "+5.68亿", UP,
     ["高争民爆+2.32 · 金正大+2.05 · 百合花+0.87",
      "潞化科技+0.51 · 肯特股份+0.47",
      "（红四方-0.53 · 集泰股份-0.02）"]),
    ("房地产", "+4.20亿", UP,
     ["盈新发展+4.24 · 我爱我家-0.04"]),
    ("电子（PCB/结构件）", "+4.14亿", UP,
     ["中京电子+3.54 · 领先股份+2.63 · 科森科技+1.04",
      "华体科技+0.26 · 中石科技-3.33"]),
    ("传媒（出版/影视）", "+2.77亿", UP,
     ["中信出版+1.09 · 上海电影+1.04 · 读者传媒+0.40",
      "博瑞传播+0.34 · 欢瑞世纪-0.10"]),
    ("农林牧渔（种业/制糖/种植）", "+1.59亿", UP,
     ["金健米业+1.56 · 粤桂股份+1.45 · 亚盛集团+0.34",
      "万向德农+0.01 · 播恩集团-0.73 · 神农种业-0.67 · 新赛股份-0.37"]),
    ("建筑材料（水泥）", "+0.72亿", UP,
     ["亚泰集团+0.72"]),
    ("商贸零售（百货）", "+0.54亿", UP,
     ["百大集团+0.59 · 翠微股份-0.05"]),
    ("社会服务（旅游）", "+0.51亿", UP,
     ["桂林旅游+0.51"]),
    ("通信（光通信）", "+0.26亿", UP,
     ["华脉科技+0.26"]),
    ("煤炭", "+0.06亿", UP,
     ["云煤能源+0.06"]),
    ("食品饮料（蛋品）", "+0.04亿", UP,
     ["欧福蛋业+0.04"]),
]

SELL = [
    ("国防军工", "-3.01亿", DOWN,
     ["博云新材-3.01（换手率20%·机构出逃）"]),
    ("家用电器（滤材）", "-1.07亿", DOWN,
     ["金海高科-1.07"]),
    ("电力设备（电源）", "-0.81亿", DOWN,
     ["中远通-0.82 · 华汇智能+0.01"]),
    ("计算机", "-0.73亿", DOWN,
     ["竞业达-0.45 · 新炬网络-0.28"]),
    ("机械设备（仪器/农机）", "-0.44亿", DOWN,
     ["华盛昌-0.37 · 花溪科技-0.07"]),
    ("有色金属", "-0.42亿", DOWN,
     ["*ST沐邦-0.21 · 金钛股份-0.13 · 马矿股份-0.08"]),
    ("医药生物（原料药/中药）", "-0.26亿", DOWN,
     ["千金药业-0.62 · 万邦医药-0.19 · 百花医药-0.09 · 维琪科技-0.10",
      "（东亚药业+0.35 · 奥浦迈+0.24 · 近岸蛋白+0.15）"]),
    ("交通运输（港口）", "-0.16亿", DOWN,
     ["北部湾港-0.16"]),
    ("汽车", "-0.09亿", DOWN,
     ["杰锋动力-0.09"]),
    ("建筑装饰", "-0.05亿", DOWN,
     ["ST富煌-0.10 · *ST美芝+0.05"]),
]

INSIGHTS = [
    "① 化工净买居首：化肥(金正大)+民爆(高争民爆)合力，净买入5.68亿登顶",
    "② 电子冰火两重天：中京电子+3.54、领先股份+2.63抢筹PCB，中石科技-3.33逆势巨量出逃",
    "③ 地产单票定方向：盈新发展+4.24亿一家独大，扛起地产净买",
    "④ 净卖双雄：中石科技-3.33亿、博云新材-3.01亿为两大砸盘主力",
]

def card_h(lines):
    return 84 + len(lines)*32 + 14

def section_h(items):
    h = 0
    for name, total, color, lines in items:
        h += card_h(lines) + 18
    return h

# 预计算总高度
HEADER = 270
BUY_TITLE = 64
SELL_TITLE = 64
INSIGHT_TITLE = 64
BUY_H = section_h(BUY)
SELL_H = section_h(SELL)
INS_H = 40 + len(INSIGHTS)*42 + 60    # 洞察卡
FOOT = 80
BOTTOM = 48

H = HEADER + BUY_TITLE + BUY_H + SELL_TITLE + SELL_H + INSIGHT_TITLE + INS_H + FOOT + BOTTOM
H = int(H)
CH = H*SS
print('canvas', W, H)

img = Image.new('RGBA', (CW, CH), BG+(255,))
d = ImageDraw.Draw(img)

def draw_section_title(y, color, title):
    d.ellipse([MX*SS, (y+12)*SS, (MX+20)*SS, (y+32)*SS], fill=color+(255,))
    d.text(((MX+36)*SS, (y+4)*SS), title, font=F(34), fill=INK+(255,))
    d.text(((MX+CWX-80)*SS, (y+12)*SS), '单位：亿元', font=F(20, False), fill=GRAY+(255,))
    return y + 64

def draw_card(y, name, total, color, lines):
    ch = card_h(lines)
    d.rounded_rectangle([MX*SS, y*SS, (MX+CWX)*SS, (y+ch)*SS],
                        radius=16*SS, fill=CARD+(255,), outline=LINE+(255,), width=2*SS)
    d.rectangle([MX*SS, (y+18)*SS, (MX+6)*SS, (y+ch-18)*SS], fill=color+(255,))
    # 概念名
    d.text(((MX+30)*SS, (y+26)*SS), name, font=F(30), fill=INK+(255,))
    # 总净额（右对齐）
    d.text(((MX+CWX-30)*SS, (y+16)*SS), total, font=F(36), fill=color+(255,), anchor='rm')
    # 个股明细
    yy = y + 84
    for ln in lines:
        d.text(((MX+30)*SS, yy*SS), ln, font=F(23, False), fill=GRAY+(255,))
        yy += 32
    return y + ch + 18

# ---------- 标题区 ----------
d.rounded_rectangle([MX*SS, 48*SS, (MX+332)*SS, 100*SS], radius=26*SS, fill=XRED+(255,))
d.text(((MX+26)*SS, 61*SS), '龙虎榜 · 板块分析', font=F(27), fill=(255,255,255,255))
d.rounded_rectangle([(812)*SS, 48*SS, 1040*SS, 100*SS], radius=26*SS, outline=GRAY+(200,), width=2*SS)
d.text((926*SS, 61*SS), '2026.09.08 收盘', font=F(25, False), fill=GRAY+(255,))
d.text((MX*SS, 118*SS), '化工称霸 · 军工弃子', font=F(56), fill=INK+(255,))
d.rectangle([(MX+2)*SS, 196*SS, (MX+178)*SS, 202*SS], fill=XRED+(255,))
d.text((MX*SS, 208*SS), '55只上榜 · 基础化工净买5.6亿居首 · 博云新材-3亿遭弃', font=F(27, False), fill=GRAY+(255,))

# ---------- 净买入榜 ----------
y = HEADER
y = draw_section_title(y, UP, '净买入板块榜 · 游资吸筹方向')
for name, total, color, lines in BUY:
    y = draw_card(y, name, total, color, lines)

# ---------- 净卖出榜 ----------
y = draw_section_title(y, DOWN, '净卖出板块榜 · 出货方向')
for name, total, color, lines in SELL:
    y = draw_card(y, name, total, color, lines)

# ---------- 洞察卡 ----------
y = draw_section_title(y, XRED, '今日关键信号')
d.rounded_rectangle([MX*SS, y*SS, (MX+CWX)*SS, (y+INS_H)*SS],
                    radius=20*SS, fill=CARD+(255,), outline=LINE+(255,), width=2*SS)
d.rectangle([MX*SS, (y+20)*SS, (MX+6)*SS, (y+INS_H-20)*SS], fill=XRED+(255,))
yy = y + 32
for s in INSIGHTS:
    d.text(((MX+34)*SS, yy*SS), s, font=F(26, False), fill=(51,51,51,255))
    yy += 42

# ---------- 底部免责 ----------
fy = y + INS_H + 28
d.text((MX*SS, fy*SS), '数据：同花顺 iFinD 龙虎榜（当日上榜净额，单日+三日榜口径） ｜ 仅供学习参考，不构成投资建议',
       font=F(20, False), fill=GRAY+(230,))

out = img.resize((W, H), Image.LANCZOS).convert('RGB')
out_path = os.path.join(FD, 'lhb_concept_0908.png')
out.save(out_path, quality=95)
print('saved', out_path, out.size)