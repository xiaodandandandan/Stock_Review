# -*- coding: utf-8 -*-
"""
全市场 · 板块资金流 静态长图（申万一级行业 · 净主动买入额）

数据来源（v3）：
  - 优先读取 data_YYYYMMDD.json 的 sector_flow 字段（[[行业, 净额亿, 备注?], ...]，由外部查询产出）；
  - 缺省回退内置演示数据（人工快照，2026.09.08，需手工同步）。

用法：
    python render_sector_flow.py [--json PATH] [--out PATH]
"""
import argparse
import os
from PIL import Image, ImageDraw

from render_common import (
    SS, BG, CARD, INK, INK2, GRAY, LINE, XRED, UP, DOWN,
    make_F, load_data, data_day, date_label, build_flow_insights,
)

FD = os.path.dirname(os.path.abspath(__file__))
W = 1080
CW = W * SS
F = make_F(FD, SS)

MX = 40
CWX = W - 2 * MX
BAR_BG = (238, 238, 233)   # 与 compare 的 BARBG 不同，属本图版式


# ---------------- 演示数据（无 JSON 时的回退快照，2026.09.08） ----------------
DEMO = {
    "day": "20260908",
    "headline": "周期流入 · 科技失血",
    "subline": "31个申万一级行业 · 化工+44亿居首 · 电子-19.5亿垫底",
    "data": [
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
    ],
    "insights": [
        "① 资源周期称霸：化工+有色+石化合计净流入116亿，涨价主线全市场共识",
        "② 科技成长失血：电子-19.5+计算机-9.0+通信-3.1合计-31.6亿，为最大流出区",
        "③ 防御+高股息受捧：公用事业+25.4、银行+15.4、煤炭+8.6，避险情绪升温",
        "④ 风格切换信号：周期/资源净流入 vs 科技成长净流出，市场风格从成长转向价值",
    ],
}


def normalize_sf(raw):
    """sector_flow 字段归一化为 [(name, val_亿, note), ...]"""
    out = []
    for item in raw:
        if len(item) == 3:
            out.append((item[0], float(item[1]), item[2]))
        else:
            out.append((item[0], float(item[1]), ''))
    return out


def render(date_lbl, headline, subline, data, insights, out_path):
    # ---------------- 布局 ----------------
    HEADER = 270
    SEC1_TITLE = 64
    N_SECTORS = len(data)
    BAR_ROW_H = 54
    SEC1_PAD = 18
    SEC1_H = SEC1_TITLE + N_SECTORS * BAR_ROW_H + SEC1_PAD

    SEC2_TITLE = 64
    SEC2_H = 40 + len(insights) * 42 + 60

    FOOT = 80
    BOTTOM = 48

    H = int(HEADER + SEC1_TITLE + SEC1_H + 30 + SEC2_TITLE + SEC2_H + FOOT + BOTTOM)
    CH = H * SS
    print('canvas', W, H)

    img = Image.new('RGBA', (CW, CH), BG + (255,))
    d = ImageDraw.Draw(img)

    def draw_section_title(y, color, title, sub=''):
        d.ellipse([MX * SS, (y + 12) * SS, (MX + 20) * SS, (y + 32) * SS], fill=color + (255,))
        d.text(((MX + 36) * SS, (y + 4) * SS), title, font=F(34), fill=INK + (255,))
        if sub:
            tw = d.textlength(sub, font=F(20, False))
            d.text(((MX + CWX - int(tw / SS) - 10) * SS, (y + 12) * SS),
                   sub, font=F(20, False), fill=GRAY + (255,))
        return y + 64

    # ---------- 标题区 ----------
    d.rounded_rectangle([MX * SS, 48 * SS, (MX + 380) * SS, 100 * SS],
                        radius=26 * SS, fill=XRED + (255,))
    d.text(((MX + 26) * SS, 61 * SS), '全市场 · 板块资金流', font=F(27), fill=(255, 255, 255, 255))
    d.rounded_rectangle([812 * SS, 48 * SS, 1040 * SS, 100 * SS],
                        radius=26 * SS, outline=GRAY + (200,), width=2 * SS)
    d.text((926 * SS, 61 * SS), date_lbl, font=F(25, False), fill=GRAY + (255,))
    d.text((MX * SS, 118 * SS), headline, font=F(56), fill=INK + (255,))
    d.rectangle([(MX + 2) * SS, 196 * SS, (MX + 200) * SS, 202 * SS], fill=XRED + (255,))
    d.text((MX * SS, 208 * SS), subline, font=F(27, False), fill=GRAY + (255,))

    # ---------- Sec1 板块资金流 ----------
    y = HEADER
    d.rounded_rectangle([MX * SS, y * SS, (MX + CWX) * SS, (y + SEC1_H) * SS],
                        radius=16 * SS, fill=CARD + (255,), outline=LINE + (255,), width=2 * SS)
    y = draw_section_title(y, UP, '板块资金净流入排行', '%d板块 · 净主动买入额(亿元)' % N_SECTORS)

    yy = y
    BAR_NAME_W = 120
    BAR_NOTE_X = MX + BAR_NAME_W + 24
    BAR_AREA_X0 = MX + BAR_NAME_W + 24
    BAR_AREA_W = CWX - BAR_NAME_W - 24 - 80
    CENTER_X = BAR_AREA_X0 + BAR_AREA_W // 2
    HALF_W = BAR_AREA_W // 2 - 6

    max_abs = max(abs(v) for _, v, _ in data)

    for name, val, note in data:
        color = UP if val >= 0 else DOWN
        d.text(((MX + 4) * SS, (yy + 16) * SS), name, font=F(22), fill=INK + (255,))
        d.text(((MX + BAR_NAME_W + 28) * SS, (yy + 20) * SS),
               note, font=F(18, False), fill=GRAY + (255,))

        bar_y = (yy + 8) * SS
        bar_h = 22 * SS
        d.rounded_rectangle([BAR_AREA_X0 * SS, bar_y,
                             (BAR_AREA_X0 + BAR_AREA_W - 80) * SS, bar_y + bar_h],
                            radius=6 * SS, fill=BAR_BG + (255,))

        ratio = abs(val) / max_abs
        bar_len = int(HALF_W * ratio * SS)

        if val >= 0:
            x0 = CENTER_X * SS
            x1 = (CENTER_X + int(HALF_W * ratio)) * SS
            d.rounded_rectangle([x0, bar_y, x1, bar_y + bar_h],
                                radius=6 * SS, fill=color + (255,))
        else:
            x1 = CENTER_X * SS
            x0 = (CENTER_X - int(HALF_W * ratio)) * SS
            d.rounded_rectangle([x0, bar_y, x1, bar_y + bar_h],
                                radius=6 * SS, fill=color + (255,))

        d.line([CENTER_X * SS, bar_y, CENTER_X * SS, bar_y + bar_h],
               fill=GRAY + (160,), width=1 * SS)

        sign = '+' if val >= 0 else ''
        val_text = sign + ("%.2f" % val) + '亿'
        if val >= 0:
            d.text(((CENTER_X + HALF_W + 8) * SS, (yy + 14) * SS),
                   val_text, font=F(22, True), fill=color + (255,), anchor='lm')
        else:
            d.text(((CENTER_X - HALF_W - 8) * SS, (yy + 14) * SS),
                   val_text, font=F(22, True), fill=color + (255,), anchor='rm')

        yy += BAR_ROW_H

    y = HEADER + SEC1_TITLE + SEC1_H + 30

    # ---------- Sec2 核心结论 ----------
    d.rounded_rectangle([MX * SS, y * SS, (MX + CWX) * SS, (y + SEC2_H) * SS],
                        radius=16 * SS, fill=CARD + (255,), outline=LINE + (255,), width=2 * SS)
    d.rectangle([MX * SS, (y + 18) * SS, (MX + 6) * SS, (y + 54) * SS], fill=XRED + (255,))
    d.text(((MX + 26) * SS, (y + 10) * SS), '核心结论', font=F(32), fill=INK + (255,))
    yy = y + 70
    for s in insights:
        d.text(((MX + 26) * SS, yy * SS), s, font=F(25, False), fill=INK2 + (255,))
        yy += 42

    # ---------- 底部 ----------
    fy = y + SEC2_H + 28
    d.text((MX * SS, fy * SS),
           '口径：申万一级行业 · 净主动买入额(合计) · 全市场全量A股',
           font=F(20, False), fill=GRAY + (230,))
    d.text((MX * SS, (fy + 30) * SS),
           '数据：同花顺 iFinD ｜ 仅供学习参考，不构成投资建议',
           font=F(20, False), fill=GRAY + (230,))

    out = img.resize((W, H), Image.LANCZOS).convert('RGB')
    out.save(out_path, quality=95)
    print('saved', out_path, out.size)


def main():
    ap = argparse.ArgumentParser(description='全市场板块资金流长图（可选 --json 的 sector_flow 字段）')
    ap.add_argument('--json', default=None, help='数据 JSON 路径（需含 sector_flow 字段，缺省找 data.json）')
    ap.add_argument('--out', default=None, help='输出 PNG 路径')
    args = ap.parse_args()

    data = load_data(path=args.json, base=FD)
    if data and data.get('sector_flow'):
        sf = normalize_sf(data['sector_flow'])
        ins = build_flow_insights(sf)
        date_lbl = date_label(data_day(data))
        fname = data_day(data)
        pos = [x for x in sf if x[1] > 0]
        neg = [x for x in sf if x[1] < 0]
        top, worst = pos[0], neg[-1]
        head = '%s流入 · %s流出' % (top[0], worst[0])
        sub = '%d个行业 · %s%+.1f亿居首 · %s%+.1f亿垫底' % (
            len(sf), top[0], top[1], worst[0], worst[1])
        print('[data] 使用 JSON 数据源（%d 个行业）' % len(sf))
    else:
        if data is not None:
            print('[warn] JSON 中无 sector_flow 字段，回退内置演示数据（该数据维度不在 run_pipeline 范围内）')
        else:
            print('[info] 未找到数据 JSON，使用内置演示数据（人工快照）')
        sf = DEMO['data']
        ins = DEMO['insights']
        head, sub = DEMO['headline'], DEMO['subline']
        date_lbl = date_label(DEMO['day'])
        fname = DEMO['day']

    out = args.out or os.path.join(FD, 'sector_flow_%s.png' % fname)
    render(date_lbl, head, sub, sf, ins, out)


if __name__ == '__main__':
    main()