# -*- coding: utf-8 -*-
"""
小红书版 龙虎榜·板块分布两日对比 静态长图

数据来源（v4）：
  - 读取两个 data_YYYYMMDD.json（run_pipeline 产出），各自聚合"申万一级行业净买入额(亿元)"后对比；
  - 任一日期 JSON 缺失/为空 → 对应侧回退内置演示快照（2026.09.07 vs 09.08），保证单独运行仍可出图。

用法：
    python render_lhb_compare.py [day1 day2] [--json1 PATH] [--json2 PATH] [--out PATH]
    例：python render_lhb_compare.py 20260907 20260908
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageFont

from render_common import (
    make_F, load_data, data_day, short_date, sector_totals,
    compare_meta, build_compare_insights,
    BG, CARD, INK, INK2, GRAY, LINE, XRED, UP, UPBG, DOWN, AMB,
)

SS = 2
W = 1080
CW = W * SS

FD = os.path.dirname(os.path.abspath(__file__))
F = make_F(FD, SS)

MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

def FM(sz):
    return ImageFont.truetype(MONO_BOLD, int(sz * SS))

MX = 40
CWX = W - 2 * MX

BARBG = (240, 240, 235)  # 两日对比表 bar 底衬，本图版式专属

# ---------------- 演示数据（两 JSON 缺失时的回退快照，2026.09.07 vs 09.08） ----------------
DEMO = {
    "d1day": "20260907",
    "d2day": "20260908",
    "n1": 65,
    "n2": 55,
    "headline": "AI退潮 · 周期接力",
    "subline": "电子+通信两日净买缩水93% · 化工地产成新主线",
    "d7": {
        "电子": 49.23, "通信": 10.97, "农林牧渔": 4.70, "电力设备": 3.29,
        "机械设备": 2.72, "轻工制造": 1.99, "食品饮料": 1.46, "有色金属": 0.92,
        "商贸零售": 0.74, "社会服务": 0.61, "纺织服饰": 0.44, "基础化工": 0.06,
        "汽车": -0.16, "美容护理": -0.19, "公用事业": -0.30, "煤炭": -0.41,
        "建筑材料": -0.54, "医药生物": -0.89, "房地产": -1.27, "计算机": -2.03,
        "传媒": -3.04,
    },
    "d8": {
        "基础化工": 5.68, "房地产": 4.20, "电子": 4.14, "传媒": 2.77,
        "农林牧渔": 1.59, "建筑材料": 0.72, "商贸零售": 0.54, "社会服务": 0.51,
        "通信": 0.26, "煤炭": 0.06, "食品饮料": 0.04, "建筑装饰": -0.05,
        "汽车": -0.09, "交通运输": -0.16, "医药生物": -0.26, "有色金属": -0.42,
        "机械设备": -0.44, "计算机": -0.73, "电力设备": -0.81, "家用电器": -1.07,
        "国防军工": -3.01,
    },
    "insights": [
        "① AI算力硬件两天净买 -52亿：电子-45.1、通信-10.7，资金撤离最猛的方向",
        "② 涨价周期接力：基础化工+5.6亿登顶，化肥+民爆成新主线",
        "③ 地产单票反转：盈新发展+4.24亿扛起地产，从净卖转净买",
        "④ 军工获弃：博云新材-3.01亿机构出逃，新晋净卖出之首",
        "⑤ 资金总量缩水80%：情绪从亢奋转向观望，赚钱效应消退",
    ],
}


def _load(day, path):
    """尝试加载某日数据；缺失或不含龙虎榜明细返回 None（调用方回退演示数据）。"""
    data = load_data(day, path)
    if not (data and data.get('lhb_stocks')):
        return None
    return data


def _top_sec(d):
    return max(d, key=d.get) if d else '—'


def main():
    ap = argparse.ArgumentParser(description="龙虎榜板块分布两日对比长图")
    ap.add_argument("day1", nargs="?", help="前一交易日 YYYYMMDD，匹配 data_{day}.json")
    ap.add_argument("day2", nargs="?", help="后一交易日 YYYYMMDD，匹配 data_{day}.json")
    ap.add_argument("--json1", default=None, help="选择前一日的 data JSON 路径")
    ap.add_argument("--json2", default=None, help="选择后一日的 data JSON 路径")
    ap.add_argument("--out", default=None, help="输出 PNG 路径")
    args = ap.parse_args()

    d1 = _load(args.day1, args.json1)
    d2 = _load(args.day2, args.json2)
    d7 = sector_totals(d1) if d1 else dict(DEMO['d7'])
    d8 = sector_totals(d2) if d2 else dict(DEMO['d8'])
    lbl1 = short_date(data_day(d1)) if d1 else short_date(DEMO['d1day'])
    lbl2 = short_date(data_day(d2)) if d2 else short_date(DEMO['d2day'])
    n1 = len(d1['lhb_stocks']) if d1 else DEMO['n1']
    n2 = len(d2['lhb_stocks']) if d2 else DEMO['n2']
    if d1 and d2:
        headline, sub = compare_meta(d7, d8)
        ins = build_compare_insights(d7, d8)
    else:
        headline, sub = DEMO['headline'], DEMO['subline']
        ins = list(DEMO['insights'])

    # ---------------- 数据派生（板块排序：按两日变化绝对值降序） ----------------
    boards = sorted(set(d7) | set(d8))

    def delta(b):
        return d8.get(b, 0.0) - d7.get(b, 0.0)

    boards.sort(key=lambda b: -abs(delta(b)))

    def col(v):
        if v > 0.02:
            return UP
        if v < -0.02:
            return DOWN
        return GRAY

    def fmt(v):
        return "%+6.2f" % v

    # ---------------- 列坐标（数值等宽字体右对齐，小数点严格对齐） ----------------
    CX_NAME = MX + 22                 # 板块名 左对齐
    BAR1_X = MX + 170                 # 前一日（lbl1）bar 起点
    BAR1_W = 150                      # bar 最大宽
    CX_V1 = MX + 400                  # 前一日 数值 右对齐 x
    BAR2_X = MX + 460                 # 后一日（lbl2）bar 起点
    BAR2_W = 150
    CX_V2 = MX + 690                  # 后一日 数值 右对齐 x
    CX_DV = MX + CWX - 8              # 变化 右对齐 x

    # ---------------- 布局 ----------------
    HEADER = 260
    TOTAL_TITLE = 56
    TOTAL_H = 150
    COMP_TITLE = 56
    THEAD_H = 38
    ROW_H = 50
    N = len(boards)
    COMP_H = COMP_TITLE + THEAD_H + N * ROW_H + 16
    INS_TITLE = 56
    INS_H = 48 + 5 * 40 + 50
    FOOT = 64
    BOTTOM = 44

    H = int(HEADER + TOTAL_TITLE + TOTAL_H + 24 + COMP_H + 24 + INS_TITLE + INS_H + FOOT + BOTTOM)
    CH = H * SS
    print('canvas', W, H, 'boards', N)

    img = Image.new('RGBA', (CW, CH), BG + (255,))
    d = ImageDraw.Draw(img)

    def sec_title(y, color, title, sub=''):
        d.ellipse([MX * SS, (y + 10) * SS, (MX + 20) * SS, (y + 30) * SS], fill=color + (255,))
        d.text(((MX + 36) * SS, (y + 2) * SS), title, font=F(32), fill=INK + (255,))
        if sub:
            tw = d.textlength(sub, font=F(20, False))
            d.text(((MX + CWX - int(tw / SS) - 6) * SS, (y + 10) * SS), sub,
                   font=F(20, False), fill=GRAY + (255,))
        return y + 56

    # ---------- 标题区 ----------
    d.rounded_rectangle([MX * SS, 42 * SS, (MX + 360) * SS, 94 * SS], radius=26 * SS, fill=XRED + (255,))
    d.text(((MX + 26) * SS, 55 * SS), '龙虎榜 · 板块分布对比', font=F(27), fill=(255, 255, 255, 255))
    d.rounded_rectangle([812 * SS, 42 * SS, 1040 * SS, 94 * SS], radius=26 * SS,
                        outline=GRAY + (200,), width=2 * SS)
    d.text((920 * SS, 55 * SS), '%s → %s' % (lbl1, lbl2), font=F(25, False), fill=GRAY + (255,))
    d.text((MX * SS, 112 * SS), headline, font=F(56), fill=INK + (255,))
    d.rectangle([(MX + 2) * SS, 190 * SS, (MX + 196) * SS, 196 * SS], fill=XRED + (255,))
    d.text((MX * SS, 204 * SS), sub, font=F(27, False), fill=GRAY + (255,))

    # ---------- 总量对比卡 ----------
    y = HEADER
    y = sec_title(y, AMB, '上榜资金总量', '全市场净买入额(亿)')
    t7 = sum(d7.values())
    t8 = sum(d8.values())
    cw2 = (CWX - 20) // 2
    card_y = y
    card_h = TOTAL_H
    top1, top2 = _top_sec(d7), _top_sec(d8)
    d.rounded_rectangle([MX * SS, card_y * SS, (MX + cw2) * SS, (card_y + card_h) * SS],
                        radius=14 * SS, fill=UPBG + (255,), outline=LINE + (255,), width=2 * SS)
    d.text(((MX + 24) * SS, (card_y + 22) * SS), '%s 净买入' % lbl1, font=F(24, False), fill=GRAY + (255,))
    d.text(((MX + 24) * SS, (card_y + 52) * SS), '%+.1f亿' % t7, font=F(52), fill=UP + (255,))
    d.text(((MX + 24) * SS, (card_y + 112) * SS), '%d只上榜 · %s领跑' % (n1, top1), font=F(20, False), fill=GRAY + (255,))
    rx = MX + cw2 + 20
    d.rounded_rectangle([rx * SS, card_y * SS, (MX + CWX) * SS, (card_y + card_h) * SS],
                        radius=14 * SS, fill=CARD + (255,), outline=LINE + (255,), width=2 * SS)
    d.text(((rx + 24) * SS, (card_y + 22) * SS), '%s 净买入' % lbl2, font=F(24, False), fill=GRAY + (255,))
    d.text(((rx + 24) * SS, (card_y + 52) * SS), '%+.1f亿' % t8, font=F(52), fill=UP + (255,))
    if t7:
        shrink = round((1 - t8 / t7) * 100)
        note2 = '%d只上榜 · 总量%s约%d%%' % (n2, '缩水' if shrink >= 0 else '放量', abs(shrink))
    else:
        note2 = '%d只上榜' % n2
    d.text(((rx + 24) * SS, (card_y + 112) * SS), note2, font=F(20, False), fill=AMB + (255,))
    y += TOTAL_H + 24

    # ---------- 板块对比表 ----------
    y = sec_title(y, XRED, '板块净买入两日对比', '单位：亿元 · 红流入/绿流出')
    d.rectangle([MX * SS, y * SS, (MX + CWX) * SS, (y + THEAD_H) * SS], fill=INK + (255,))
    d.text((CX_NAME * SS, (y + 10) * SS), '板块', font=F(22), fill=(255, 255, 255, 255))
    d.text((CX_V1 * SS, (y + 10) * SS), lbl1, font=F(22), fill=(255, 255, 255, 255), anchor='rm')
    d.text((CX_V2 * SS, (y + 10) * SS), lbl2, font=F(22), fill=(255, 255, 255, 255), anchor='rm')
    d.text((CX_DV * SS, (y + 10) * SS), '变化', font=F(22), fill=(255, 255, 255, 255), anchor='rm')
    yy = y + THEAD_H

    maxv = max(abs(v) for v in list(d7.values()) + list(d8.values()))

    for i, b in enumerate(boards):
        v7 = d7.get(b, 0.0)
        v8 = d8.get(b, 0.0)
        dv = delta(b)
        bg = CARD if i % 2 == 0 else (245, 245, 242)
        d.rectangle([MX * SS, yy * SS, (MX + CWX) * SS, (yy + ROW_H) * SS], fill=bg + (255,))
        if i < N - 1:
            d.line([MX * SS, (yy + ROW_H) * SS, (MX + CWX) * SS, (yy + ROW_H) * SS], fill=LINE + (255,), width=1 * SS)
        d.text((CX_NAME * SS, (yy + 14) * SS), b, font=F(24), fill=INK + (255,))
        hy = (yy + 17) * SS
        d.rounded_rectangle([BAR1_X * SS, hy, (BAR1_X + BAR1_W) * SS, hy + 12 * SS], radius=6 * SS, fill=BARBG + (255,))
        if v7 != 0:
            l = int(BAR1_W * (abs(v7) / maxv))
            d.rounded_rectangle([BAR1_X * SS, hy, (BAR1_X + l) * SS, hy + 12 * SS], radius=6 * SS, fill=col(v7) + (255,))
        d.text((CX_V1 * SS, (yy + 13) * SS), fmt(v7), font=FM(20), fill=col(v7) + (255,), anchor='rm')
        d.rounded_rectangle([BAR2_X * SS, hy, (BAR2_X + BAR2_W) * SS, hy + 12 * SS], radius=6 * SS, fill=BARBG + (255,))
        if v8 != 0:
            l = int(BAR2_W * (abs(v8) / maxv))
            d.rounded_rectangle([BAR2_X * SS, hy, (BAR2_X + l) * SS, hy + 12 * SS], radius=6 * SS, fill=col(v8) + (255,))
        d.text((CX_V2 * SS, (yy + 13) * SS), fmt(v8), font=FM(20), fill=col(v8) + (255,), anchor='rm')
        d.text((CX_DV * SS, (yy + 13) * SS), fmt(dv), font=FM(21), fill=col(dv) + (255,), anchor='rm')
        yy += ROW_H

    # ---------- 核心结论 ----------
    y = yy + 14
    y = sec_title(y, XRED, '两日变化 · 核心结论')
    d.rounded_rectangle([MX * SS, y * SS, (MX + CWX) * SS, (y + INS_H) * SS],
                        radius=16 * SS, fill=CARD + (255,), outline=LINE + (255,), width=2 * SS)
    d.rectangle([MX * SS, (y + 18) * SS, (MX + 6) * SS, (y + INS_H - 18) * SS], fill=XRED + (255,))
    iy = y + 34
    for s in ins:
        d.text(((MX + 32) * SS, iy * SS), s, font=F(25, False), fill=INK2 + (255,))
        iy += 40

    # ---------- 底部 ----------
    fy = y + INS_H + 26
    d.text((MX * SS, fy * SS),
           '口径：申万一级行业 · 龙虎榜当日上榜净买入额(单日+三日榜) ｜ 数据：同花顺 iFinD ｜ 仅供学习参考，不构成投资建议',
           font=F(20, False), fill=GRAY + (230,))

    out = img.resize((W, H), Image.LANCZOS).convert('RGB')
    out_path = args.out or os.path.join(FD, 'lhb_compare_%s_%s.png' % (lbl1.replace('.', ''), lbl2.replace('.', '')))
    out.save(out_path, quality=95)
    print('saved', out_path, out.size)


if __name__ == '__main__':
    main()