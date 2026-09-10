# -*- coding: utf-8 -*-
"""渲染公共模块：数据源加载、板块聚合、格式化、自动文案生成 + 共享画布常量。

设计目标：
  - 渲染脚本的数据优先从 data_YYYYMMDD.json（run_pipeline 产出）读取并计算，
    缺省回退脚本内置演示数据，保证单独运行仍可出图；
  - 纯逻辑函数（无绘制依赖）可单元测试。
"""

import json
import os
import re

# ---------------- 共享画布常量（render_*.py 均一致） ----------------
SS = 2
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
# 注：sector_flow 的 BAR_BG(238,238,233) 与 compare 的 BARBG(240,240,235)
#     值不同，属各自版式，保留在各脚本内


def make_F(fd, ss=SS):
    """构建字体工厂：F(sz, bold=True) → PIL 字体。字体缺失延续原报错行为。"""
    from PIL import ImageFont
    f_bold = os.path.join(fd, 'fonts', 'NotoSansSC-Bold.otf')
    f_reg = os.path.join(fd, 'fonts', 'NotoSansSC-Regular.otf')

    def F(sz, bold=True):
        return ImageFont.truetype(f_bold if bold else f_reg, int(sz * ss))

    return F


# ---------------- 数据加载 ----------------
def load_data(day=None, path=None, base=None):
    """定位并读取数据 JSON（run_pipeline 产出）。

    优先级：显式 path > data_{day}.json > data.json。
    找不到返回 None（调用方回退演示数据）。
    """
    fd = base or os.path.dirname(os.path.abspath(__file__))
    cands = []
    if path:
        cands.append(path)
    if day:
        cands.append(os.path.join(fd, 'data_%s.json' % day))
    cands.append(os.path.join(fd, 'data.json'))
    for c in cands:
        if os.path.isfile(c):
            with open(c, encoding='utf-8') as f:
                data = json.load(f)
            if not data.get('day'):
                # JSON 缺 day 时从文件名 data_YYYYMMDD.json 推断，避免过期日期静默混入
                m = re.search(r'(\d{8})\.json$', c)
                if m:
                    data['day'] = m.group(1)
            return data
    return None


def data_day(data, fallback=None):
    """取 JSON 中的交易日，用于文件名与日期徽章。
    缺 day 且未提供 fallback 时报错——拒绝过期日期静默混入产物。"""
    day = data.get('day') or fallback
    if not day:
        raise ValueError('JSON 缺少交易日字段 day，且未提供 fallback')
    return str(day)


def date_label(day):
    """交易日 'YYYYMMDD' → 'YYYY.MM.DD 收盘'"""
    d = str(day)
    return '%s.%s.%s 收盘' % (d[:4], d[4:6], d[6:8])


# ---------------- 半屏日期标签（两日对比用） ----------------
def short_date(day):
    d = str(day)
    return '%s.%s' % (d[4:6], d[6:8])


# ---------------- 金额格式化 ----------------
def fmt_yi(v):
    """元 → '+5.68亿' / '-3.01亿'（两位小数）"""
    return '%+.2f亿' % (v / 1e8)


def fmt_yi_short(v):
    """个股明细内的金额：'+2.32' / '-0.53'（亿，两位）"""
    return '%+.2f' % (v / 1e8)


# ---------------- 龙虎榜板块聚合 ----------------
def lhb_sector_flow(lhb_stocks):
    """lhb_stocks: [[code, name, cnt, chg, flow(元), industry], ...]
    → [(sector, total(元), [(name, flow(元)), ...]), ...] 按净额降序
    """
    agg = {}
    for code, name, cnt, chg, flow, ind in lhb_stocks:
        sec = (ind or '未分类').split('-')[0]
        agg.setdefault(sec, []).append((name, flow or 0.0))
    out = []
    for sec, items in agg.items():
        items.sort(key=lambda x: -x[1])
        out.append((sec, sum(f for _, f in items), items))
    out.sort(key=lambda x: -x[1])
    return out


def _wrap_lines(items, per_line=3):
    """个股明细分行：非负额在前，负额个股用括号包裹放在行尾（贴近原版版式）。"""
    pos = [(n, f) for n, f in items if f >= 0]
    neg = [(n, f) for n, f in items if f < 0]
    seq = pos + neg
    lines = []
    for i in range(0, len(seq), per_line):
        grp = seq[i:i + per_line]
        parts = []
        for n, f in grp:
            txt = '%s%s' % (n[:8], fmt_yi_short(f))
            parts.append('(%s)' % txt if f < 0 and i + len(grp) > len(pos) else txt)
        lines.append(' · '.join(parts))
    return lines or ['—']


def lhb_cards(sector_flow):
    """→ (buy, sell)：板块卡片 [(sector, total_text, [个股行...]), ...]"""
    buy, sell = [], []
    for sec, total, items in sector_flow:
        card = (sec, fmt_yi(total), _wrap_lines(items))
        (buy if total >= 0 else sell).append(card)
    return buy, sell


def build_lhb_insights(sector_flow, lhb_stocks):
    """自动生成 4 条关键信号（贴近原版句式）。"""
    if not sector_flow or not lhb_stocks:
        return ['当日无上榜个股数据。'] * 4
    top = sector_flow[0]
    sec2 = sector_flow[1] if len(sector_flow) > 1 else None
    worst = sector_flow[-1]
    worst_stock = min(lhb_stocks, key=lambda s: s[4])
    n_pos = sum(1 for _, t, _ in sector_flow if t > 0)
    n_neg = sum(1 for _, t, _ in sector_flow if t < 0)
    if sec2:
        ins2 = '② %s净买居次：%s等个股抢筹' % (sec2[0], sec2[2][0][0])
    else:
        ins2 = '② 净买集中度极高，仅一个板块为正'
    return [
        '① %s净买居首：净买入%s登顶' % (top[0], fmt_yi(top[1])),
        ins2,
        '③ %s净流出最重：%s%s单票抛压最大' % (worst[0], worst_stock[1], fmt_yi_short(worst_stock[4])),
        '④ 上榜%d只 · 净买为正板块%d个 / 净卖%d个，多空分化' % (len(lhb_stocks), n_pos, n_neg),
    ]


def build_lhb_meta(sector_flow, lhb_stocks):
    """标题大字与副标题。"""
    top = sector_flow[0] if sector_flow else (None, 0, [])
    worst = sector_flow[-1] if sector_flow else (None, 0, [])
    worst_stock = min(lhb_stocks, key=lambda s: s[4]) if lhb_stocks else None
    head = '%s称霸 · %s流出' % (top[0], worst[0]) if top[0] else '龙虎榜 · 板块分析'
    if worst_stock and top[0]:
        sub = '%d只上榜 · %s净买%s居首 · %s%s遭弃' % (
            len(lhb_stocks), top[0], fmt_yi(top[1]), worst_stock[1], fmt_yi_short(worst_stock[4]))
    else:
        sub = '%d只上榜' % len(lhb_stocks)
    return head, sub


# ---------------- 涨跌停 / 连板 ----------------
def limit_industry_counts(limit_up, top_n=12):
    """limit_up: [[code, name, chg, sub, level1], ...]
    → [(level1, 家数, 子行业注), ...] 降序，超出 top_n 归入'其他行业'。
    """
    lu = {}
    for code, name, chg, sub, l1 in limit_up:
        item = lu.setdefault(l1, {'n': 0, 'subs': []})
        item['n'] += 1
        if sub and sub != l1 and len(item['subs']) < 4:
            item['subs'].append(sub)
    order = sorted(lu.items(), key=lambda kv: -kv[1]['n'])
    out = []
    rest = 0
    for l1, item in order:
        if len(out) >= top_n:
            rest += item['n']
            continue
        note = '/'.join(item['subs']) if item['subs'] else '—'
        out.append((l1, item['n'], note))
    if rest:
        out.append(('其他行业', rest, '—'))
    return out


def limit_themes(industry_counts, top_n=5):
    """题材主线：取行业分布前 top_n，加序号前缀。"""
    return [('① %s' % n, c, note) for n, c, note in industry_counts[:top_n]]


def build_ladders(streaks, max_tiers=3):
    """streaks: [[code, name, days, sub], ...] → [(f'{d}板', [names], note), ...]
    取最高 max_tiers 档；无数据时给占位行。个股名最多显示 12 只。
    """
    by = {}
    for code, name, days, sub in streaks:
        by.setdefault(int(days), []).append(name)
    if not by:
        return [('2板', ['—'], '当日无 2 板以上连板')]
    lads = sorted(by.items(), reverse=True)[:max_tiers]
    out = []
    for days, names in lads:
        shown = names[:12]
        note = '%d只 · %s' % (len(names), '、'.join(names[:3]))
        out.append(('%d板' % days, shown, note))
    return out


def build_downlist(heavy_fall, limit_down):
    """heavy_fall: [[code, name, chg, industry], ...]; limit_down 同构
    → [(name, pct, board, note), ...] 跌幅升序（跌更多在前），前 10。
    """
    dn = {c for c, *_ in limit_down}
    rows = []
    for code, name, chg, ind in heavy_fall:
        board = (ind or '未分类').split('-')[0]
        note = '收盘跌停' if code in dn else '跌幅超9%'
        rows.append((name, float(chg), board, note))
    rows.sort(key=lambda r: r[1])
    return rows[:10]


def limit_summary(limit_up, limit_down, streaks, heavy_fall):
    """头部大字 / 副标题。"""
    n_up = len(limit_up)
    n_fall9 = len(heavy_fall)
    n_dn = len(limit_down)
    max_days = max((s[2] for s in streaks), default=0)
    head = '%d涨停 vs %d跌超9%%' % (n_up, n_fall9)
    if max_days:
        sub = '高标%d板 · 跌停%d只' % (max_days, n_dn)
    else:
        sub = '跌停%d只 · 无连板梯队' % n_dn
    return head, sub


def build_limit_signals(limit_up, limit_down, heavy_fall, streaks):
    """核心结论 5 条。"""
    lu = {}
    for code, name, chg, sub, l1 in limit_up:
        lu.setdefault(l1, []).append(name)
    top1 = sorted(lu.items(), key=lambda kv: -len(kv[1]))[0] if lu else ('—', [])
    tg = {}
    for code, name, days, sub in streaks:
        tg.setdefault(int(days), []).append(name)
    max_days = max(tg) if tg else 0
    top_names = '、'.join(tg[max_days][:3]) if max_days else '—'
    dn_boards = {(ind or '').split('-')[0] for _, _, _, ind in heavy_fall}
    lads = len(tg)
    total_streak = sum(len(v) for v in tg.values())
    return [
        '① 普涨vs分化：%d只涨停 vs %d只跌超9%%，指数偏暖但内部高低切' % (len(limit_up), len(heavy_fall)),
        '② %s涨停居首：%d只，%s' % (top1[0], len(top1[1]), top1[1][:3]),
        '③ 高标降温：最高仅%d板（%s），情绪明显回落' % (max_days, top_names) if max_days else '③ 高标缺席：当日无 2 板以上连板，情绪冰点',
        '④ 跌停%d只 · 重挫股分散于%d个行业，多为高位补跌' % (len(limit_down), len(dn_boards)),
        '⑤ 连板梯队：%d档 · 共%d只，%d板为最高标' % (lads, total_streak, max_days) if max_days else '⑤ 连板梯队空窗，市场无高度',
    ]


# ---------------- 全市场板块资金流（sector_flow） ----------------
def build_flow_insights(data):
    """sector_flow: [(name, val(亿), note), ...] → 4 条核心结论"""
    n = len(data)
    pos = [x for x in data if x[1] > 0]
    neg = [x for x in data if x[1] < 0]
    p_top = sorted(pos, key=lambda x: -x[1])[:3]
    n_bot = sorted(neg, key=lambda x: x[1])[:3]
    p_sum = sum(x[1] for x in pos)
    n_sum = sum(x[1] for x in neg)
    p_names = '+'.join('%s%.1f' % (x[0], x[1]) for x in p_top)
    n_names = '+'.join('%s%.1f' % (x[0], x[1]) for x in n_bot)
    return [
        '① 流入居前：%s合计净流入%.1f亿' % (p_names, p_sum),
        '② 流出居前：%s合计净流出%.1f亿' % (n_names, -n_sum),
        '③ 净流入为正板块%d个 / 净流出%d个' % (len(pos), len(neg)),
        '④ 资金聚焦：%s（+%.1f亿）为全市场最强方向' % (pos[0][0], pos[0][1]) if pos else '④ 当日全市场资金以流出为主',
    ]


# ---------------- 两日对比（render_lhb_compare） ----------------
def sector_totals(data):
    """data['lhb_stocks'] → {一级行业: 净买入(亿)}，供两日对比。
    复用 lhb_sector_flow 聚合，金额从元换算为亿。"""
    sf = lhb_sector_flow(data.get('lhb_stocks') or [])
    return {sec: t / 1e8 for sec, t, _ in sf}


def compare_meta(d7, d8):
    """两日对比大标题与副标题（数据驱动）。"""
    top7, top8 = _top_sec(d7), _top_sec(d8)
    if top7 == top8:
        head = '%s仍领跑净买' % top7
    else:
        head = '%s退潮 · %s接力' % (top7, top8)
    t7, t8 = sum(d7.values()), sum(d8.values())
    if t7:
        ratio = (t8 - t7) / abs(t7) * 100
        trend = '放量净流入' if ratio >= 0 else '退潮缩水'
        sub = '两日上榜净买合计 %.1f→%.1f 亿（%+.0f%%）· %s' % (t7, t8, ratio, trend)
    else:
        sub = '两日上榜净买合计 %.1f / %.1f 亿' % (t7, t8)
    return head, sub


def _top_sec(d):
    return max(d, key=d.get) if d else '—'


def build_compare_insights(d7, d8):
    """两日对比核心结论 5 条（自动生成，贴近原版句式；空数据给占位）。"""
    if not d7 and not d8:
        return ['两日均无板块数据。'] * 5
    t7, t8 = sum(d7.values()), sum(d8.values())
    b7, b8 = _top_sec(d7), _top_sec(d8)
    n7, n8 = len(d7), len(d8)
    pos7 = sum(1 for v in d7.values() if v > 0.02)
    pos8 = sum(1 for v in d8.values() if v > 0.02)
    deltas = [(b, d8.get(b, 0.0) - d7.get(b, 0.0)) for b in sorted(set(d7) | set(d8))]
    g_b, g_v = max(deltas, key=lambda x: x[1])
    l_b, l_v = min(deltas, key=lambda x: x[1])
    if t7:
        i1 = '① 资金总量 %.1f→%.1f亿（%+.0f%%），资金%s' % (
            t7, t8, (t8 - t7) / abs(t7) * 100, '回流放量' if t8 >= t7 else '退潮缩水')
    else:
        i1 = '① 前一日无净买数据，本次仅统计当日（合计%.1f亿）' % t8
    return [
        i1,
        '② 净买榜首%s：%s(%+.1f亿) → %s(%+.1f亿)' % (
            '未变' if b7 == b8 else '易主', b7, d7.get(b7, 0.0), b8, d8.get(b8, 0.0)),
        '③ 环比增量最大：%s %+.1f亿，%s' % (g_b, g_v, '逆势加仓' if g_v > 0 else '相对抗跌'),
        '④ 环比减量最大：%s %+.1f亿，%s' % (l_b, l_v, '资金撤离最猛' if l_v < 0 else '修复最弱'),
        '⑤ 净买为正板块 %d→%d 个（占比 %d%%→%d%%），多空气氛%s' % (
            pos7, pos8, pos7 * 100 // n7 if n7 else 0,
            pos8 * 100 // n8 if n8 else 0, '扩散' if pos8 > pos7 else '收敛'),
    ]