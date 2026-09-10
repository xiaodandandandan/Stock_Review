# -*- coding: utf-8 -*-
"""
龙虎榜 · 板块分析 静态长图
按板块展示龙虎榜主力净流入 / 净流出排名 + 个股明细 + 关键信号。

数据来源（v3）：
  - 优先读取 data_YYYYMMDD.json（run_pipeline 产出），按申万一级行业自动聚合；
  - 缺省回退内置演示数据（人工快照，可能滞后，仅供单独出图演练）。

用法：
    python render_lhb.py [YYYYMMDD] [--json PATH] [--out PATH]
"""
import argparse
import os
from PIL import Image, ImageDraw

from render_common import (
    SS, BG, CARD, INK, INK2, GRAY, LINE, XRED, UP, DOWN,
    make_F, load_data, data_day, date_label,
    lhb_sector_flow, lhb_cards, build_lhb_insights, build_lhb_meta,
)

FD = os.path.dirname(os.path.abspath(__file__))
W = 1080
CW = W * SS
F = make_F(FD, SS)

MX = 40                        # 左右留白
CWX = W - 2 * MX               # 内容宽 = 1000


# ---------------- 演示数据（无 JSON 时的回退快照，2026.09.08） ----------------
DEMO = {
    "day": "20260908",
    "headline": "化工称霸 · 军工弃子",
    "subline": "55只上榜 · 基础化工净买5.6亿居首 · 博云新材-3亿遭弃",
    "buy": [
        ("基础化工（化肥/民爆/磷化工）", "+5.68亿",
         ["高争民爆+2.32 · 金正大+2.05 · 百合花+0.87",
          "潞化科技+0.51 · 肯特股份+0.47",
          "（红四方-0.53 · 集泰股份-0.02）"]),
        ("房地产", "+4.20亿", ["盈新发展+4.24 · 我爱我家-0.04"]),
        ("电子（PCB/结构件）", "+4.14亿",
         ["中京电子+3.54 · 领先股份+2.63 · 科森科技+1.04",
          "华体科技+0.26 · 中石科技-3.33"]),
        ("传媒（出版/影视）", "+2.77亿",
         ["中信出版+1.09 · 上海电影+1.04 · 读者传媒+0.40",
          "博瑞传播+0.34 · 欢瑞世纪-0.10"]),
        ("农林牧渔（种业/制糖/种植）", "+1.59亿",
         ["金健米业+1.56 · 粤桂股份+1.45 · 亚盛集团+0.34",
          "万向德农+0.01 · 播恩集团-0.73 · 神农种业-0.67 · 新赛股份-0.37"]),
        ("建筑材料（水泥）", "+0.72亿", ["亚泰集团+0.72"]),
        ("商贸零售（百货）", "+0.54亿", ["百大集团+0.59 · 翠微股份-0.05"]),
        ("社会服务（旅游）", "+0.51亿", ["桂林旅游+0.51"]),
        ("通信（光通信）", "+0.26亿", ["华脉科技+0.26"]),
        ("煤炭", "+0.06亿", ["云煤能源+0.06"]),
        ("食品饮料（蛋品）", "+0.04亿", ["欧福蛋业+0.04"]),
    ],
    "sell": [
        ("国防军工", "-3.01亿", ["博云新材-3.01（换手率20%·机构出逃）"]),
        ("家用电器（滤材）", "-1.07亿", ["金海高科-1.07"]),
        ("电力设备（电源）", "-0.81亿", ["中远通-0.82 · 华汇智能+0.01"]),
        ("计算机", "-0.73亿", ["竞业达-0.45 · 新炬网络-0.28"]),
        ("机械设备（仪器/农机）", "-0.44亿", ["华盛昌-0.37 · 花溪科技-0.07"]),
        ("有色金属", "-0.42亿", ["*ST沐邦-0.21 · 金钛股份-0.13 · 马矿股份-0.08"]),
        ("医药生物（原料药/中药）", "-0.26亿",
         ["千金药业-0.62 · 万邦医药-0.19 · 百花医药-0.09 · 维琪科技-0.10",
          "（东亚药业+0.35 · 奥浦迈+0.24 · 近岸蛋白+0.15）"]),
        ("交通运输（港口）", "-0.16亿", ["北部湾港-0.16"]),
        ("汽车", "-0.09亿", ["杰锋动力-0.09"]),
        ("建筑装饰", "-0.05亿", ["ST富煌-0.10 · *ST美芝+0.05"]),
    ],
    "insights": [
        "① 化工净买居首：化肥(金正大)+民爆(高争民爆)合力，净买入5.68亿登顶",
        "② 电子冰火两重天：中京电子+3.54、领先股份+2.63抢筹PCB，中石科技-3.33逆势巨量出逃",
        "③ 地产单票定方向：盈新发展+4.24亿一家独大，扛起地产净买",
        "④ 净卖双雄：中石科技-3.33亿、博云新材-3.01亿为两大砸盘主力",
    ],
}


def card_h(lines):
    return 84 + len(lines) * 32 + 14


def section_h(items):
    h = 0
    for name, total, lines in items:
        h += card_h(lines) + 18
    return h


def render(date_lbl, headline, subline, buy, sell, insights, out_path):
    # 预计算总高度
    HEADER = 270
    BUY_TITLE = 64
    SELL_TITLE = 64
    INSIGHT_TITLE = 64
    BUY_H = section_h(buy)
    SELL_H = section_h(sell)
    INS_H = 40 + len(insights) * 42 + 60    # 洞察卡
    FOOT = 80
    BOTTOM = 48

    H = int(HEADER + BUY_TITLE + BUY_H + SELL_TITLE + SELL_H + INSIGHT_TITLE + INS_H + FOOT + BOTTOM)
    CH = H * SS
    print('canvas', W, H)

    img = Image.new('RGBA', (CW, CH), BG + (255,))
    d = ImageDraw.Draw(img)

    def draw_section_title(y, color, title):
        d.ellipse([MX * SS, (y + 12) * SS, (MX + 20) * SS, (y + 32) * SS],
                  fill=color + (255,))
        d.text(((MX + 36) * SS, (y + 22) * SS), title,
               font=F(34), fill=INK + (255,), anchor='lm')
        d.text(((MX + CWX - 30) * SS, (y + 22) * SS), '单位：亿元',
               font=F(20, False), fill=GRAY + (255,), anchor='rm')
        return y + 64

    def draw_card(y, name, total, color, lines):
        ch = card_h(lines)
        d.rounded_rectangle([MX * SS, y * SS, (MX + CWX) * SS, (y + ch) * SS],
                            radius=16 * SS, fill=CARD + (255,),
                            outline=LINE + (255,), width=2 * SS)
        d.rectangle([MX * SS, (y + 18) * SS, (MX + 6) * SS, (y + ch - 18) * SS],
                    fill=color + (255,))
        # 板块名（基线对齐）
        d.text(((MX + 30) * SS, (y + 50) * SS), name,
               font=F(30), fill=INK + (255,), anchor='ls')
        # 总净额（右对齐，基线对齐）
        d.text(((MX + CWX - 30) * SS, (y + 50) * SS), total,
               font=F(36), fill=color + (255,), anchor='rs')
        # 个股明细
        yy = y + 84
        for ln in lines:
            d.text(((MX + 30) * SS, yy * SS), ln,
                   font=F(23, False), fill=GRAY + (255,), anchor='ls')
            yy += 32
        return y + ch + 18

    # ---------- 标题区 ----------
    d.rounded_rectangle([MX * SS, 48 * SS, (MX + 332) * SS, 100 * SS],
                        radius=26 * SS, fill=XRED + (255,))
    d.text(((MX + 26) * SS, 74 * SS), '龙虎榜 · 板块分析',
           font=F(27), fill=(255, 255, 255, 255), anchor='lm')
    d.rounded_rectangle([(W - 228) * SS, 48 * SS, (W - 40) * SS, 100 * SS],
                        radius=26 * SS, outline=GRAY + (200,), width=2 * SS)
    d.text(((W - 134) * SS, 74 * SS), date_lbl,
           font=F(25, False), fill=GRAY + (255,), anchor='mm')
    d.text((MX * SS, 138 * SS), headline,
           font=F(56), fill=INK + (255,), anchor='ls')
    d.rectangle([(MX + 2) * SS, 196 * SS, (MX + 178) * SS, 202 * SS], fill=XRED + (255,))
    d.text((MX * SS, 222 * SS), subline,
           font=F(27, False), fill=GRAY + (255,), anchor='ls')

    # ---------- 净买入榜 ----------
    y = HEADER
    y = draw_section_title(y, UP, '净买入板块榜 · 游资吸筹方向')
    for name, total, lines in buy:
        y = draw_card(y, name, total, UP, lines)

    # ---------- 净卖出榜 ----------
    y = draw_section_title(y, DOWN, '净卖出板块榜 · 出货方向')
    for name, total, lines in sell:
        y = draw_card(y, name, total, DOWN, lines)

    # ---------- 洞察卡 ----------
    y = draw_section_title(y, XRED, '今日关键信号')
    d.rounded_rectangle([MX * SS, y * SS, (MX + CWX) * SS, (y + INS_H) * SS],
                        radius=20 * SS, fill=CARD + (255,),
                        outline=LINE + (255,), width=2 * SS)
    d.rectangle([MX * SS, (y + 20) * SS, (MX + 6) * SS, (y + INS_H - 20) * SS],
                fill=XRED + (255,))
    yy = y + 40
    for s in insights:
        d.text(((MX + 34) * SS, yy * SS), s,
               font=F(26, False), fill=INK2 + (255,), anchor='ls')
        yy += 42

    # ---------- 底部免责 ----------
    fy = y + INS_H + 28
    d.text((MX * SS, fy * SS),
           '数据：同花顺 iFinD 龙虎榜（当日上榜净额，单日+三日榜口径） ｜ 仅供学习参考，不构成投资建议',
           font=F(20, False), fill=GRAY + (230,))

    out = img.resize((W, H), Image.LANCZOS).convert('RGB')
    out.save(out_path, quality=95)
    print('saved', out_path, out.size)


def main():
    ap = argparse.ArgumentParser(description='龙虎榜板块分析长图（数据优先取 data_YYYYMMDD.json）')
    ap.add_argument('day', nargs='?', default=None, help='YYYYMMDD，缺省找 data.json')
    ap.add_argument('--json', default=None, help='显式指定数据 JSON 路径')
    ap.add_argument('--out', default=None, help='输出 PNG 路径')
    args = ap.parse_args()

    data = load_data(args.day, args.json, FD)
    if data and data.get('lhb_stocks'):
        sf = lhb_sector_flow(data['lhb_stocks'])
        buy, sell = lhb_cards(sf)
        ins = build_lhb_insights(sf, data['lhb_stocks'])
        head, sub = build_lhb_meta(sf, data['lhb_stocks'])
        date_lbl = date_label(data_day(data))
        fname = data_day(data)
        print('[data] 使用 JSON 数据源（%d 只上榜）' % len(data['lhb_stocks']))
    else:
        if data is not None:
            print('[warn] JSON 中无 lhb_stocks，回退内置演示数据')
        else:
            print('[info] 未找到数据 JSON，使用内置演示数据（人工快照）')
        buy, sell = DEMO['buy'], DEMO['sell']
        ins, head, sub = DEMO['insights'], DEMO['headline'], DEMO['subline']
        date_lbl = date_label(DEMO['day'])
        fname = DEMO['day']

    out = args.out or os.path.join(FD, 'lhb_concept_%s.png' % fname)
    render(date_lbl, head, sub, buy, sell, ins, out)


if __name__ == '__main__':
    main()