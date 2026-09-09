# -*- coding: utf-8 -*-
"""
龙虎榜 · 分板块个股明细 长图（精简版）
按板块分组展示上榜个股，组内按主力净流入排序。
去掉股票代码列，仅保留 简称 / 涨跌幅 / 主力净流入，字号更大更清晰。

用法：
    from render_lhb_stock_detail import render_stock_detail
    # sectors: [(板块名, [(简称, 涨跌幅%, 净流入(元), 上榜次数), ...]), ...]
    # 板块按净流入合计降序排列
    render_stock_detail(sectors, date_str='2026.09.09', out_path='lhb_stock_detail.png')
"""
import os
from PIL import Image, ImageDraw, ImageFont

SS = 2          # 超采样倍率
W = 1080        # 输出宽度
CW = W * SS

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


def _f(sz, bold=True):
    return ImageFont.truetype(F_BOLD if bold else F_REG, int(sz * SS))


MX = 40         # 左右留白
CWX = W - 2 * MX  # 内容宽 = 1000
ROW_H = 52      # 单行高
SECT_PAD = 18   # 板块底部内边距
SECT_TITLE = 60  # 板块标题高


def _fmt_flow(v):
    """净流入格式化：亿/万"""
    a = abs(v)
    if a >= 1e8:
        return f"{v/1e8:+.2f}亿"
    elif a >= 1e4:
        return f"{v/1e4:+.0f}万"
    else:
        return f"{v:+.0f}"


def _sector_card_h(n_stocks):
    """单个板块卡片高度"""
    return SECT_TITLE + n_stocks * ROW_H + SECT_PAD


def _total_height(sectors):
    HEADER = 220
    total = HEADER + 24  # 标题 + 首板块前间距
    for _, stocks in sectors:
        total += _sector_card_h(len(stocks)) + 18  # 板块间距
    total += 60  # 底部
    return int(total)


def render_stock_detail(sectors, date_str, title='龙虎榜 · 分板块个股明细',
                        subtitle='', out_path=None):
    """
    生成分板块个股明细长图。

    Args:
        sectors: list of (sector_name, stocks)，stocks 为 list of
                 (name, chg_pct, net_flow_yuan, appear_count)
                 已按板块净流入合计降序、组内按净流入降序排列。
        date_str: 日期字符串，如 '2026.09.09'
        title: 主标题
        subtitle: 副标题（统计口径）
        out_path: 输出路径，默认脚本目录下 lhb_stock_detail.png
    """
    H = _total_height(sectors)
    CH = H * SS
    img = Image.new('RGBA', (CW, CH), BG + (255,))
    d = ImageDraw.Draw(img)

    # ---------- 标题区 ----------
    d.rounded_rectangle([MX * SS, 48 * SS, (MX + 332) * SS, 100 * SS],
                        radius=26 * SS, fill=XRED + (255,))
    d.text(((MX + 26) * SS, 74 * SS), title,
           font=_f(27), fill=(255, 255, 255, 255), anchor='lm')
    d.rounded_rectangle([(W - 228) * SS, 48 * SS, (W - 40) * SS, 100 * SS],
                        radius=26 * SS, outline=GRAY + (200,), width=2 * SS)
    d.text(((W - 134) * SS, 74 * SS), f'{date_str} 收盘',
           font=_f(24, False), fill=GRAY + (255,), anchor='mm')

    # 统计
    n_total = sum(len(s) for _, s in sectors)
    n_in = sum(1 for _, stks in sectors for _, _, f, _ in stks if f > 0)
    n_out = sum(1 for _, stks in sectors for _, _, f, _ in stks if f < 0)
    total_flow = sum(f for _, stks in sectors for _, _, f, _ in stks)
    sub = subtitle or f'{n_total}只上榜  ·  净流入{n_in}只  ·  净流出{n_out}只  ·  合计{_fmt_flow(total_flow)}'
    d.text((MX * SS, 132 * SS), sub, font=_f(28, False), fill=INK + (255,))
    d.rectangle([(MX + 2) * SS, 186 * SS, (MX + 170) * SS, 192 * SS], fill=XRED + (255,))
    d.text((MX * SS, 204 * SS), '板块按主力净流入排序  ·  组内个股同序',
           font=_f(24, False), fill=GRAY + (255,))

    # ---------- 板块卡片 ----------
    y = 220
    for sector, stocks in sectors:
        ch = _sector_card_h(len(stocks))
        # 卡片背景
        d.rounded_rectangle([MX * SS, y * SS, (MX + CWX) * SS, (y + ch) * SS],
                            radius=16 * SS, fill=CARD + (255,),
                            outline=LINE + (255,), width=2 * SS)

        # 板块合计净流入
        total = sum(f for _, _, f, _ in stocks)
        total_color = UP if total >= 0 else DOWN
        # 左侧色条
        d.rectangle([MX * SS, (y + 16) * SS, (MX + 6) * SS, (y + ch - 16) * SS],
                    fill=total_color + (255,))

        # 板块名
        d.text(((MX + 26) * SS, (y + 36) * SS), sector,
               font=_f(28), fill=INK + (255,), anchor='lm')
        # 家数
        d.text(((MX + 300) * SS, (y + 36) * SS), f'{len(stocks)}只',
               font=_f(22, False), fill=GRAY + (255,), anchor='lm')
        # 合计净流入（右对齐）
        d.text(((MX + CWX - 24) * SS, (y + 36) * SS),
               f'合计 {_fmt_flow(total)}',
               font=_f(26), fill=total_color + (255,), anchor='rm')

        # 分隔线
        d.line([(MX + 20) * SS, (y + SECT_TITLE - 4) * SS,
                (MX + CWX - 20) * SS, (y + SECT_TITLE - 4) * SS],
               fill=LINE + (255,), width=2 * SS)

        # 个股行
        yy = y + SECT_TITLE
        for name, chg, flow, cnt in stocks:
            # 简称
            d.text(((MX + 24) * SS, (yy + 26) * SS), name,
                   font=_f(26), fill=INK + (255,), anchor='lm')
            # 2次上榜标记
            if cnt >= 2:
                # 琥珀色小角标
                label = f'{cnt}次'
                tw = d.textlength(label, font=_f(18))
                bx0 = int((MX + 24) * SS + d.textlength(name, font=_f(26)) + 12 * SS)
                by0 = (yy + 14) * SS
                bx1 = bx0 + int(tw) + 16 * SS
                by1 = (yy + 38) * SS
                d.rounded_rectangle([bx0, by0, bx1, by1],
                                    radius=8 * SS, fill=AMB + (255,))
                d.text(((bx0 + bx1) // 2, (yy + 26) * SS), label,
                       font=_f(18), fill=(255, 255, 255, 255), anchor='mm')

            # 涨跌幅（中列右对齐）
            chg_color = UP if chg >= 0 else DOWN
            d.text(((MX + 500) * SS, (yy + 26) * SS), f'{chg:+.2f}%',
                   font=_f(26), fill=chg_color + (255,), anchor='rm')

            # 主力净流入（右列右对齐）
            flow_color = UP if flow >= 0 else DOWN
            d.text(((MX + CWX - 24) * SS, (yy + 26) * SS), _fmt_flow(flow),
                   font=_f(26), fill=flow_color + (255,), anchor='rm')

            yy += ROW_H

        y += ch + 18  # 板块间距

    # ---------- 底部 ----------
    d.text((MX * SS, (y + 16) * SS),
           '数据：同花顺 iFinD 龙虎榜（当日上榜净额，单日+三日榜口径） ｜ 仅供学习参考，不构成投资建议',
           font=_f(20, False), fill=GRAY + (230,))

    # ---------- 输出 ----------
    out = img.resize((W, H), Image.LANCZOS).convert('RGB')
    if out_path is None:
        out_path = os.path.join(FD, 'lhb_stock_detail.png')
    out.save(out_path, quality=95)
    print(f'[render_stock_detail] saved {out_path} ({W}x{H})')
    return out_path


# ---------------- 示例数据（独立运行时使用） ----------------
if __name__ == '__main__':
    demo_sectors = [
        ("有色金属", [
            ("湖南黄金", 10.02, 6.11e8, 1),
            ("金钛股份", 5.56, 9.14e6, 1),
            ("精艺股份", 9.97, -3.27e7, 1),
        ]),
        ("电力设备", [
            ("洛轴股份", 101.45, 3.87e8, 1),
        ]),
        ("电子", [
            ("崇达技术", 5.74, 1.27e8, 1),
            ("迅", 3.20, 8.5e7, 1),
            ("大港股份", 10.01, -5.2e7, 1),
        ]),
    ]
    render_stock_detail(demo_sectors, '2026.09.09',
                        out_path=os.path.join(FD, 'lhb_stock_detail_demo.png'))
