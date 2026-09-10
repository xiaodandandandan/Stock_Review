# -*- coding: utf-8 -*-
"""
涨跌停 · 板块全景 静态长图
展示涨停行业分布 / 题材主线 / 连板梯队 / 跌停阵营 / 核心结论。

数据来源（v3）：
  - 优先读取 data_YYYYMMDD.json（run_pipeline 产出），自动归集行业 / 连板 / 重挫；
  - 缺省回退内置演示数据（人工快照，可能滞后，仅供单独出图演练）。

用法：
    python render_limit.py [YYYYMMDD] [--json PATH] [--out PATH]
"""
import argparse
import os
from PIL import Image, ImageDraw

from render_common import (
    SS, BG, CARD, INK, INK2, GRAY, LINE, XRED, UP, UPBG, DOWN, DNBG, AMB,
    make_F, load_data, data_day, date_label,
    limit_industry_counts, limit_themes, build_ladders, build_downlist,
    build_limit_signals, limit_summary,
)

FD = os.path.dirname(os.path.abspath(__file__))
W = 1440
CW = W * SS
F = make_F(FD, SS)

MX = 40
CWX = W - 2 * MX


# ---------------- 演示数据（无 JSON 时的回退快照，2026.09.08） ----------------
DEMO = {
    "day": "20260908",
    "headline": "74涨停 vs 10跌超9%",
    "subline": "普涨但化工极端占优 · 高标仅4板",
    "industry": [
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
    ],
    "themes": [
        ("① 化工涨价周期", 14, "化肥·纯碱·磷化工·有机硅"),
        ("② 传媒/出版", 8, "出版 + 影视主升"),
        ("③ 农业/种业/制糖", 8, "糖价 + 种业 + 种植"),
        ("④ 房地产链", 5, "地产政策修复"),
        ("⑤ 消费/零售/食品", 9, "商超百货 + 食品饮料"),
    ],
    "ladders": [
        ("4板", ["爱仕达", "亚盛集团", "百大集团"], "3只 · 情绪最高标"),
        ("3板", ["海欣食品", "敦煌种业", "中国出版"], "3只 · 食品/农业/出版"),
        ("2板", ["中京电子", "百合花", "华盛昌", "读者传媒", "金正大", "中百集团",
                 "集泰股份", "华体科技", "上海电影", "桂林旅游", "澳洋健康", "华脉科技"],
         "12只 · 梯队扩容"),
    ],
    "downlist": [
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
    ],
    "signals": [
        '① 普涨vs分化：74只涨停 vs 10只跌超9%，指数偏暖但内部高低切',
        '② 化工主升回归：14只化工涨停，化肥·民爆·磷化工涨价周期启动',
        '③ 高标降温：最高仅4板(爱仕达/亚盛/百大)，较昨日情绪明显回落',
        '④ 跌停无板块性：重挫股分散汽车/电子/机械，多为高位补跌',
        '⑤ 单票定多空：龙虎榜盈新发展+4.2亿、博云新材-3亿主导方向',
    ],
    "footnote": "口径：收盘涨停74只(含一字) / 跌超9%重挫10只 · 涨停家数按申万一级行业归集",
}


def sec_card_h(n_rows, row_h, title_h=64, pad=18):
    return title_h + n_rows * row_h + pad


def render(date_lbl, headline, subline, industry, themes, ladders,
           downlist, signals, footnote, limit_up_total, out_path):
    # ---------------- 布局计算 ----------------
    HEADER = 252
    GAP = 30

    # Sec1 行业分布
    R1 = 58
    H1 = sec_card_h(len(industry), R1)
    # Sec2 题材主线
    R2 = 80
    H2 = sec_card_h(len(themes), R2)
    # Sec3 连板梯队
    R3 = 92
    H3 = sec_card_h(len(ladders), R3)
    # Sec4 跌停阵营
    R4 = 58
    H4 = sec_card_h(len(downlist), R4)
    # Sec5 结论
    H5 = 70 + len(signals) * 40 + 26

    H = int(HEADER + H1 + GAP + H2 + GAP + H3 + GAP + H4 + GAP + H5 + 96)
    CH = H * SS
    print('canvas', W, H)

    img = Image.new('RGBA', (CW, CH), BG + (255,))
    d = ImageDraw.Draw(img)

    def sec_header(y, color, title, sub):
        d.rectangle([MX * SS, (y + 18) * SS, (MX + 6) * SS, (y + 54) * SS],
                    fill=color + (255,))
        d.text(((MX + 26) * SS, (y + 36) * SS), title,
               font=F(34), fill=INK + (255,), anchor='lm')
        d.text(((MX + CWX - 10) * SS, (y + 36) * SS), sub,
               font=F(24, False), fill=color + (255,), anchor='rm')

    # ---------- 标题区 ----------
    d.rounded_rectangle([MX * SS, 40 * SS, (MX + 346) * SS, 92 * SS],
                        radius=26 * SS, fill=XRED + (255,))
    d.text(((MX + 26) * SS, 66 * SS), '涨跌停 · 板块全景',
           font=F(27), fill=(255, 255, 255, 255), anchor='lm')
    d.rounded_rectangle([(W - 228) * SS, 40 * SS, (W - 40) * SS, 92 * SS],
                        radius=26 * SS, outline=GRAY + (200,), width=2 * SS)
    d.text(((W - 134) * SS, 66 * SS), date_lbl,
           font=F(24, False), fill=GRAY + (255,), anchor='mm')
    d.text((MX * SS, 128 * SS), headline,
           font=F(58), fill=INK + (255,), anchor='ls')
    d.rectangle([(MX + 2) * SS, 190 * SS, (MX + 186) * SS, 196 * SS], fill=XRED + (255,))
    d.text((MX * SS, 218 * SS), subline,
           font=F(28, False), fill=GRAY + (255,), anchor='ls')

    # ---------- Sec1 涨停行业分布 ----------
    y = HEADER
    d.rounded_rectangle([MX * SS, y * SS, (MX + CWX) * SS, (y + H1) * SS],
                        radius=16 * SS, fill=CARD + (255,),
                        outline=LINE + (255,), width=2 * SS)
    sec_header(y, UP, '涨停板块分布', '%d只 · 按申万行业' % limit_up_total)
    yy = y + 64
    maxv = max(v for _, v, _ in industry)
    BAR_X0, BAR_X1 = MX + 260, MX + 620
    for name, v, note in industry:
        d.text(((MX + 24) * SS, (yy + 36) * SS), name,
               font=F(26), fill=INK + (255,), anchor='ls')
        bwid = int((BAR_X1 - BAR_X0) * (v / maxv) * SS)
        if bwid > 0:
            d.rounded_rectangle([BAR_X0 * SS, (yy + 10) * SS,
                                 BAR_X0 * SS + bwid, (yy + 40) * SS],
                                radius=7 * SS, fill=UP + (220,))
        d.text(((MX + 690) * SS, (yy + 36) * SS), "%d只" % v,
               font=F(28), fill=UP + (255,), anchor='rs')
        d.text(((MX + 720) * SS, (yy + 36) * SS), note,
               font=F(20, False), fill=GRAY + (255,), anchor='ls')
        yy += R1
    y += H1 + GAP

    # ---------- Sec2 题材主线 ----------
    d.rounded_rectangle([MX * SS, y * SS, (MX + CWX) * SS, (y + H2) * SS],
                        radius=16 * SS, fill=CARD + (255,),
                        outline=LINE + (255,), width=2 * SS)
    sec_header(y, XRED, '涨停题材主线', '按概念归集')
    yy = y + 64
    for name, v, note in themes:
        d.rounded_rectangle([(MX + 24) * SS, (yy + 14) * SS,
                             (MX + 240) * SS, (yy + 62) * SS],
                            radius=10 * SS, fill=UPBG + (255,))
        d.text(((MX + 132) * SS, (yy + 38) * SS), name,
               font=F(24), fill=UP + (255,), anchor='mm')
        d.text(((MX + 290) * SS, (yy + 50) * SS), "%d只" % v,
               font=F(34), fill=INK + (255,), anchor='rs')
        d.text(((MX + 310) * SS, (yy + 50) * SS), note,
               font=F(24, False), fill=GRAY + (255,), anchor='ls')
        yy += R2
    y += H2 + GAP

    # ---------- Sec3 连板梯队 ----------
    d.rounded_rectangle([MX * SS, y * SS, (MX + CWX) * SS, (y + H3) * SS],
                        radius=16 * SS, fill=CARD + (255,),
                        outline=LINE + (255,), width=2 * SS)
    sec_header(y, AMB, '连板梯队', '情绪标尺')
    yy = y + 64
    for lb, names, note in ladders:
        d.rounded_rectangle([(MX + 24) * SS, (yy + 16) * SS,
                             (MX + 108) * SS, (yy + 64) * SS],
                            radius=10 * SS, fill=AMB + (255,))
        d.text(((MX + 66) * SS, (yy + 40) * SS), lb,
               font=F(28), fill=(255, 255, 255, 255), anchor='mm')
        if len(names) > 6:
            line1 = "、".join(names[:6])
            line2 = "、".join(names[6:12])
            d.text(((MX + 128) * SS, (yy + 38) * SS), line1,
                   font=F(24), fill=INK + (255,), anchor='ls')
            d.text(((MX + 128) * SS, (yy + 66) * SS), line2,
                   font=F(24), fill=INK + (255,), anchor='ls')
        else:
            d.text(((MX + 128) * SS, (yy + 50) * SS), "、".join(names),
                   font=F(26), fill=INK + (255,), anchor='ls')
        d.text(((MX + CWX - 14) * SS, (yy + 48) * SS), note,
               font=F(21, False), fill=GRAY + (255,), anchor='rs')
        yy += R3
    y += H3 + GAP

    # ---------- Sec4 跌停阵营 ----------
    d.rounded_rectangle([MX * SS, y * SS, (MX + CWX) * SS, (y + H4) * SS],
                        radius=16 * SS, fill=CARD + (255,),
                        outline=LINE + (255,), width=2 * SS)
    sec_header(y, DOWN, '跌停/重挫阵营', '%d只 · 按跌幅排序' % len(downlist))
    yy = y + 64
    for name, pct, board, note in downlist:
        d.text(((MX + 24) * SS, (yy + 38) * SS), name,
               font=F(26), fill=INK + (255,), anchor='ls')
        d.text(((MX + 250) * SS, (yy + 38) * SS), "%.1f%%" % pct,
               font=F(28), fill=DOWN + (255,), anchor='rs')
        d.rounded_rectangle([(MX + 270) * SS, (yy + 11) * SS,
                             (MX + 470) * SS, (yy + 41) * SS],
                            radius=8 * SS, fill=DNBG + (255,))
        d.text(((MX + 280) * SS, (yy + 26) * SS), board[:10],
               font=F(20), fill=DOWN + (255,), anchor='lm')
        d.text(((MX + 486) * SS, (yy + 38) * SS), note,
               font=F(21, False), fill=GRAY + (255,), anchor='ls')
        yy += R4
    y += H4 + GAP

    # ---------- Sec5 核心结论 ----------
    d.rounded_rectangle([MX * SS, y * SS, (MX + CWX) * SS, (y + H5) * SS],
                        radius=16 * SS, fill=CARD + (255,),
                        outline=LINE + (255,), width=2 * SS)
    d.rectangle([MX * SS, (y + 18) * SS, (MX + 6) * SS, (y + 54) * SS],
                fill=XRED + (255,))
    d.text(((MX + 26) * SS, (y + 36) * SS), '核心结论',
           font=F(32), fill=INK + (255,), anchor='lm')
    yy = y + 70
    for s in signals:
        d.text(((MX + 26) * SS, yy * SS), s,
               font=F(25, False), fill=INK2 + (255,), anchor='ls')
        yy += 40
    y += H5

    # ---------- 底部 ----------
    d.text((MX * SS, (y + 30) * SS), footnote,
           font=F(20, False), fill=GRAY + (230,))
    d.text((MX * SS, (y + 60) * SS),
           '数据：同花顺 iFinD ｜ 仅供学习参考，不构成投资建议',
           font=F(20, False), fill=GRAY + (230,))

    out = img.resize((W, H), Image.LANCZOS).convert('RGB')
    out.save(out_path, quality=95)
    print('saved', out_path, out.size)


def main():
    ap = argparse.ArgumentParser(description='涨跌停板块全景长图（数据优先取 data_YYYYMMDD.json）')
    ap.add_argument('day', nargs='?', default=None, help='YYYYMMDD，缺省找 data.json')
    ap.add_argument('--json', default=None, help='显式指定数据 JSON 路径')
    ap.add_argument('--out', default=None, help='输出 PNG 路径')
    args = ap.parse_args()

    data = load_data(args.day, args.json, FD)
    if data and data.get('limit_up'):
        n_up = len(data['limit_up'])
        n_dn = len(data['limit_down'])
        n_fall9 = len(data['heavy_fall'])
        industry = limit_industry_counts(data['limit_up'])
        themes = limit_themes(industry)
        ladders = build_ladders(data['streaks'])
        downlist = build_downlist(data['heavy_fall'], data['limit_down'])
        signals = build_limit_signals(data['limit_up'], data['limit_down'],
                                      data['heavy_fall'], data['streaks'])
        head, sub = limit_summary(data['limit_up'], data['limit_down'],
                                  data['streaks'], data['heavy_fall'])
        date_lbl = date_label(data_day(data))
        fname = data_day(data)
        footnote = '口径：收盘涨停%d只(含一字) / 跌超9%%重挫%d只 · 涨停家数按申万一级行业归集' % (n_up, n_fall9)
        print('[data] 使用 JSON 数据源（涨停 %d 只 / 跌停 %d 只）' % (n_up, n_dn))
    else:
        if data is not None:
            print('[warn] JSON 中无 limit_up，回退内置演示数据')
        else:
            print('[info] 未找到数据 JSON，使用内置演示数据（人工快照）')
        industry = DEMO['industry']
        themes, ladders = DEMO['themes'], DEMO['ladders']
        downlist, signals = DEMO['downlist'], DEMO['signals']
        head, sub = DEMO['headline'], DEMO['subline']
        date_lbl = date_label(DEMO['day'])
        fname = DEMO['day']
        footnote = DEMO['footnote']
        n_up = sum(c for _, c, _ in industry)

    out = args.out or os.path.join(FD, 'limit_panorama_%s.png' % fname)
    render(date_lbl, head, sub, industry, themes, ladders, downlist,
           signals, footnote, n_up, out)


if __name__ == '__main__':
    main()