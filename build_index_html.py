# -*- coding: utf-8 -*-
"""
复盘总览 HTML 生成器
将龙虎榜板块资金 + 涨跌停全景 + 长图引用汇总为单页 HTML，
样式沿用 lhb_template.html 的深蓝金视觉体系。

用法：
    from build_index_html import build_summary_page
    build_summary_page(data, out_path='index.html',
                       lhb_sector_img='lhb_sector_flow.png',
                       lhb_detail_img='lhb_stock_detail.png',
                       limit_img='limit_panorama.png')

data 结构（与 analyze_lhb.py / run_pipeline 产出一致）：
    {
      "day": "20260909",
      "date_cn": "2026年9月9日",
      "lhb_stocks": [[code, name, cnt, chg, flow, industry], ...],
      "limit_up":   [[code, name, chg, sub_industry, level1], ...],
      "limit_down": [[code, name, chg, industry], ...],
      "heavy_fall": [[code, name, chg, industry], ...],
      "streaks":    [[code, name, days, sub], ...],
      # 可选：自定义盘面要点（4 条，龙虎榜用）
      "lhb_insights": ["...", "...", "...", "..."],
      # 可选：自定义涨停要点（4 条）
      "limit_insights": ["...", "...", "...", "..."],
    }
"""
import os


def fmt_flow(v):
    """净流入格式化：亿/万"""
    sign = "+" if v > 0 else "-"
    a = abs(v)
    return f"{sign}{a/1e8:.2f}亿" if a >= 1e8 else f"{sign}{a/1e4:.0f}万"


def build_summary_page(data, out_path,
                       lhb_sector_img='lhb_sector_flow.png',
                       lhb_detail_img='lhb_stock_detail.png',
                       limit_img='limit_panorama.png'):
    """
    生成复盘总览 HTML 页面。

    Args:
        data: 数据字典，见模块说明
        out_path: 输出 HTML 路径
        lhb_sector_img: 龙虎榜板块资金分布长图文件名
        lhb_detail_img: 龙虎榜分板块个股明细长图文件名
        limit_img: 涨跌停板块全景长图文件名
    """
    D = data
    day_cn = D.get("date_cn", D.get("day", ""))

    # ---- 聚合：龙虎榜按一级行业 ----
    sectors = {}
    for code, name, cnt, chg, flow, ind in D["lhb_stocks"]:
        sectors.setdefault(ind.split("-")[0], []).append((name, chg, flow, ind, cnt))
    order = sorted(sectors.items(), key=lambda kv: sum(x[2] for x in kv[1]), reverse=True)
    tot_in = sum(s[4] for s in D["lhb_stocks"] if s[4] > 0)
    tot_out = sum(s[4] for s in D["lhb_stocks"] if s[4] < 0)
    n_in = sum(1 for s in D["lhb_stocks"] if s[4] > 0)
    n_out = sum(1 for s in D["lhb_stocks"] if s[4] < 0)

    def flow_cls(v):
        return "up" if v >= 0 else "down"

    def tr_sector(n, lst):
        t = sum(x[2] for x in lst)
        return (f"<tr><td>{n}</td><td class='num'>{len(lst)}</td>"
                f"<td class='num {flow_cls(t)}'>{fmt_flow(t)}</td></tr>")

    rows = "\n".join(tr_sector(n, lst) for n, lst in order)

    # ---- 涨停行业分布 ----
    lu = {}
    for code, name, chg, sub, l1 in D["limit_up"]:
        lu.setdefault(l1, []).append(name)
    lu_rows = "\n".join(
        f"<tr><td>{n}</td><td class='num'>{len(lst)}</td>"
        f"<td class='names'>{'、'.join(lst)}</td></tr>"
        for n, lst in sorted(lu.items(), key=lambda kv: -len(kv[1])))

    # ---- 连板梯队 ----
    lad = {}
    for code, name, days, sub in D["streaks"]:
        lad.setdefault(days, []).append(name)
    lad_rows = "\n".join(
        f"<tr><td><b class='badge'>{d}板</b></td><td class='num'>{len(ns)}</td>"
        f"<td class='names'>{'、'.join(ns)}</td></tr>"
        for d, ns in sorted(lad.items(), key=lambda kv: -kv[0]))

    # ---- 跌停/重挫 ----
    dn = {c for c, *_ in D["limit_down"]}

    def tr_fall(c, n, chg, ind):
        status = '<b class="badge dn">跌停</b>' if c in dn else "重挫"
        return (f"<tr><td>{n}</td><td class='num down'>{chg:+.2f}%</td>"
                f"<td>{ind}</td><td class='num'>{status}</td></tr>")

    hf_rows = "\n".join(tr_fall(c, n, chg, ind) for c, n, chg, ind in D["heavy_fall"])

    # ---- 龙虎榜盘面要点（可自定义）----
    lhb_ins = D.get("lhb_insights", _default_lhb_insights(order, D))
    limit_ins = D.get("limit_insights", _default_limit_insights(D))

    # ---- 最高连板 ----
    max_streak = max((d for d in lad.keys()), default=0)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{day_cn} A股复盘 · 龙虎榜板块资金 & 涨跌停全景</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#eef1f5; font-family:'Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif; color:#1c2430; font-variant-numeric:tabular-nums; }}
  .page {{ max-width:960px; margin:0 auto; padding:0 0 60px; }}
  .hero {{ background:linear-gradient(135deg,#ffffff 0%,#f6f8fb 55%,#edf1f8 100%); padding:44px 48px 36px; border-bottom:1px solid #e6e9ef; }}
  .tag {{ font-size:13px; letter-spacing:2px; color:#b8862f; border:1px solid rgba(217,178,95,.55); background:rgba(217,178,95,.07); padding:4px 12px; border-radius:3px; margin-right:8px; }}
  .tag.dark {{ color:#68758a; border-color:rgba(104,117,138,.32); background:rgba(104,117,138,.05); }}
  h1 {{ font-size:38px; font-weight:900; letter-spacing:2px; margin:18px 0 10px; color:#13294e; }}
  h1 .accent {{ color:#c9974a; }}
  .sub {{ font-size:15px; color:#5a6778; letter-spacing:1px; }}
  .hero-line {{ width:64px; height:5px; background:linear-gradient(90deg,#e8c37e,#e0392e); border-radius:3px; margin-top:20px; }}
  .stats {{ display:grid; grid-template-columns:repeat(6,1fr); gap:12px; padding:22px 24px 6px; }}
  .stat {{ background:#fff; border-radius:10px; padding:16px 12px; border:1px solid #e6e9ef; box-shadow:0 2px 8px rgba(16,32,64,.05); }}
  .stat .k {{ font-size:12px; color:#8a93a3; margin-bottom:8px; }}
  .stat .v {{ font-size:24px; font-weight:900; }}
  .stat .s {{ font-size:11px; color:#9aa3b2; margin-top:6px; }}
  .c-up {{ color:#d92c20; }} .c-down {{ color:#06894f; }} .c-mid {{ color:#13294e; }}
  .sec {{ padding:26px 24px 8px; }}
  .sec-head {{ display:flex; align-items:baseline; gap:12px; margin-bottom:14px; }}
  .sec-no {{ font-size:13px; font-weight:900; color:#d9b25f; letter-spacing:1px; }}
  .sec-title {{ font-size:21px; font-weight:900; color:#13294e; }}
  .sec-note {{ font-size:12px; color:#9aa3b2; margin-left:auto; }}
  .card {{ background:#fff; border-radius:10px; border:1px solid #e6e9ef; box-shadow:0 2px 8px rgba(16,32,64,.05); padding:8px 0 4px; overflow:hidden; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ text-align:left; font-size:12px; color:#8a93a3; font-weight:600; padding:9px 16px; border-bottom:1px solid #edf0f5; }}
  td {{ padding:8px 16px; border-bottom:1px solid #f4f6f9; color:#2a3648; }}
  tr:last-child td {{ border-bottom:none; }}
  tr:nth-child(even) td {{ background:#fafbfd; }}
  td.num, th.num {{ text-align:right; font-weight:700; }}
  td.names {{ color:#68758a; }}
  .up {{ color:#d92c20; }} .down {{ color:#06894f; }}
  .badge {{ display:inline-block; font-size:12px; color:#8a6417; background:#fdf3dd; border-radius:8px; padding:2px 8px; font-weight:700; }}
  .badge.dn {{ color:#06894f; background:#e6f5ec; }}
  .imgbox {{ background:#fff; border-radius:10px; border:1px solid #e6e9ef; box-shadow:0 2px 8px rgba(16,32,64,.05); padding:14px; margin-top:14px; }}
  .imgbox img {{ width:100%; display:block; border-radius:6px; }}
  .imgbox .cap {{ font-size:12px; color:#9aa3b2; text-align:center; padding:8px 0 2px; }}
  .tips {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:14px; }}
  .tip {{ background:#fff; border-radius:10px; border:1px solid #e6e9ef; box-shadow:0 2px 8px rgba(16,32,64,.05); padding:16px 18px; }}
  .tip .t {{ font-size:14px; font-weight:900; margin-bottom:7px; color:#13294e; display:flex; align-items:center; gap:8px; }}
  .tip .dot {{ width:8px; height:8px; border-radius:50%; flex:none; }}
  .tip p {{ font-size:12.5px; line-height:1.75; color:#4a5568; }}
  .tip p b.r {{ color:#d92c20; }} .tip p b.g {{ color:#06894f; }}
  .foot {{ margin:26px 24px 0; background:#fff; border:1px solid #e6e9ef; border-radius:10px; color:#4a5568; padding:18px 22px; }}
  .foot .ft {{ font-size:13px; font-weight:700; color:#b8862f; margin-bottom:6px; }}
  .foot p {{ font-size:11.5px; line-height:1.8; color:#68758a; }}
  .foot .disc {{ margin-top:8px; padding-top:8px; border-top:1px solid #e6e9ef; color:#9aa3b2; }}
</style>
</head>
<body>
<div class="page">

  <div class="hero">
    <span class="tag">同花顺 iFinD</span><span class="tag dark">龙虎榜数据</span><span class="tag dark">{day_cn} · 收盘后</span>
    <h1>A股每日复盘 <span class="accent">·</span> 龙虎榜板块资金与涨跌停全景</h1>
    <div class="sub">收盘数据全景复盘 ｜ 龙虎榜板块资金 · 分板块个股明细 · 涨跌停分布</div>
    <div class="hero-line"></div>
  </div>

  <div class="stats">
    <div class="stat"><div class="k">龙虎榜上榜</div><div class="v c-mid">{len(D['lhb_stocks'])}<small style="font-size:13px">只</small></div><div class="s">单日 + 三日榜口径</div></div>
    <div class="stat"><div class="k">主力净流入</div><div class="v c-up">{n_in}<small style="font-size:13px">只</small></div><div class="s">合计 {fmt_flow(tot_in)}</div></div>
    <div class="stat"><div class="k">主力净流出</div><div class="v c-down">{n_out}<small style="font-size:13px">只</small></div><div class="s">合计 {fmt_flow(tot_out)}</div></div>
    <div class="stat"><div class="k">主力资金整体</div><div class="v c-{'up' if tot_in+tot_out>=0 else 'down'}">{fmt_flow(tot_in + tot_out)}</div><div class="s">{'净流入' if tot_in+tot_out>=0 else '净流出'}</div></div>
    <div class="stat"><div class="k">收盘涨停</div><div class="v c-up">{len(D['limit_up'])}<small style="font-size:13px">只</small></div><div class="s">最高连板 {max_streak}板</div></div>
    <div class="stat"><div class="k">跌停/重挫</div><div class="v c-down">{len(D['limit_down'])}<small style="font-size:13px">/{len(D['heavy_fall'])}只</small></div><div class="s">跌停/跌超9%</div></div>
  </div>

  <div class="sec">
    <div class="sec-head"><span class="sec-no">01</span><span class="sec-title">龙虎榜 · 板块资金分布</span><span class="sec-note">单位：元 ｜ 按主力净流入排序 ｜ 红流入绿流出</span></div>
    <div class="card"><table>
      <tr><th>板块（同花顺一级）</th><th class="num">上榜数</th><th class="num">主力净流入合计</th></tr>
      {rows}
    </table></div>

    <div class="tips">
      <div class="tip"><div class="t"><span class="dot" style="background:#e0392e"></span>净流入最集中</div>
        <p>{lhb_ins[0]}</p></div>
      <div class="tip"><div class="t"><span class="dot" style="background:#0a9c5b"></span>净流出最重</div>
        <p>{lhb_ins[1]}</p></div>
      <div class="tip"><div class="t"><span class="dot" style="background:#e8c37e"></span>上榜个股最多</div>
        <p>{lhb_ins[2]}</p></div>
      <div class="tip"><div class="t"><span class="dot" style="background:#13294e"></span>领涨 / 领跌</div>
        <p>{lhb_ins[3]}</p></div>
    </div>

    <div class="imgbox"><img src="{lhb_sector_img}" alt="龙虎榜板块资金分布长图"><div class="cap">图1 ｜ 龙虎榜 · 板块资金分布（板块汇总 + 双向条形图 + 盘面要点）</div></div>
    <div class="imgbox"><img src="{lhb_detail_img}" alt="龙虎榜分板块个股明细长图"><div class="cap">图2 ｜ 龙虎榜 · 分板块个股明细（组内按主力净流入排序）</div></div>
  </div>

  <div class="sec">
    <div class="sec-head"><span class="sec-no">02</span><span class="sec-title">涨停板块分布与连板梯队</span><span class="sec-note">{len(D['limit_up'])} 只收盘涨停 ｜ 按申万一级归集</span></div>
    <div class="card"><table>
      <tr><th>申万一级行业</th><th class="num">涨停数</th><th>个股</th></tr>
      {lu_rows}
    </table></div>
    <div class="card" style="margin-top:14px"><table>
      <tr><th>连板梯队</th><th class="num">数量</th><th>个股</th></tr>
      {lad_rows}
    </table></div>

    <div class="tips">
      <div class="tip"><div class="t"><span class="dot" style="background:#e0392e"></span>主线一</div>
        <p>{limit_ins[0]}</p></div>
      <div class="tip"><div class="t"><span class="dot" style="background:#e8c37e"></span>主线二</div>
        <p>{limit_ins[1]}</p></div>
      <div class="tip"><div class="t"><span class="dot" style="background:#13294e"></span>情绪高标</div>
        <p>{limit_ins[2]}</p></div>
      <div class="tip"><div class="t"><span class="dot" style="background:#0a9c5b"></span>退潮方向</div>
        <p>{limit_ins[3]}</p></div>
    </div>
  </div>

  <div class="sec">
    <div class="sec-head"><span class="sec-no">03</span><span class="sec-title">跌停与重挫阵营</span><span class="sec-note">跌幅 ≤ -9% 共 {len(D['heavy_fall'])} 只，其中跌停 {len(D['limit_down'])} 只</span></div>
    <div class="card"><table>
      <tr><th>简称</th><th class="num">涨跌幅</th><th>所属行业</th><th class="num">状态</th></tr>
      {hf_rows}
    </table></div>

    <div class="imgbox"><img src="{limit_img}" alt="涨跌停板块全景长图"><div class="cap">图3 ｜ 涨跌停 · 板块全景（行业分布 / 题材主线 / 连板梯队 / 重挫阵营 / 核心结论）</div></div>
  </div>

  <div class="foot">
    <div class="ft">口径说明</div>
    <p>① 数据为 {day_cn} 交易日收盘后维度；② 龙虎榜口径为当日上榜（单日+三日榜），主力资金为主力资金净流入额（正=流入，负=流出），涨跌幅为前复权口径；③ 涨停/跌停为当日收盘价触及涨跌停价（含一字板、ST 5% 板），重挫为跌幅 ≤ -9%；④ 行业为同花顺（申万）分类；⑤ 连板为连续涨停天数。</p>
    <p class="disc">数据来源：同花顺 iFinD ｜ 以上内容基于公开数据，不构成投资建议。</p>
  </div>

</div>
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[build_summary_page] saved {out_path}")
    return out_path


def _default_lhb_insights(order, D):
    """默认龙虎榜盘面要点（4 条），按数据自动生成"""
    # 净流入第一板块
    top_name, top_stocks = order[0]
    top_total = sum(s[2] for s in top_stocks)
    top_buy = max(top_stocks, key=lambda x: x[2])
    # 净流出最后板块
    bot_name, bot_stocks = order[-1]
    bot_total = sum(s[2] for s in bot_stocks)
    bot_sell = min(bot_stocks, key=lambda x: x[2])
    # 上榜最多板块
    most_name, most_stocks = max(order, key=lambda kv: len(kv[1]))
    most_up = sum(1 for s in most_stocks if s[1] > 0)
    most_out = sum(1 for s in most_stocks if s[2] < 0)
    # 领涨领跌
    best = max(D["lhb_stocks"], key=lambda s: s[3])
    worst = min(D["lhb_stocks"], key=lambda s: s[3])

    return [
        f"{top_name} <b class='r'>{fmt_flow(top_total)}</b>：{top_buy[0]} {top_buy[1]:+.2f}% 获主力 <b class='r'>{fmt_flow(top_buy[2])}</b>，为净买入主力。",
        f"{bot_name} <b class='g'>{fmt_flow(bot_total)}</b>：{bot_sell[0]} {bot_sell[1]:+.2f}% 主力 <b class='g'>{fmt_flow(bot_sell[2])}</b>，为主要砸盘方向。",
        f"{most_name} <b>{len(most_stocks)}</b> 只上榜为今日最大群体，其中 {most_up} 只上涨但 {most_out} 只主力净流出，板块内部分化。",
        f"领涨：{best[1]} <b class='r'>{best[3]:+.2f}%</b>，主力 {fmt_flow(best[4])}；领跌：{worst[1]} <b class='g'>{worst[3]:+.2f}%</b>，主力 {fmt_flow(worst[4])}。",
    ]


def _default_limit_insights(D):
    """默认涨跌停要点（4 条），按数据自动生成"""
    # 涨停行业 top3
    lu = {}
    for code, name, chg, sub, l1 in D["limit_up"]:
        lu.setdefault(l1, []).append(name)
    top3 = sorted(lu.items(), key=lambda kv: -len(kv[1]))[:3]
    # 连板最高
    max_d = max((d for _, _, d, _ in D["streaks"]), default=0)
    max_names = [n for _, n, d, _ in D["streaks"] if d == max_d]
    # 跌停行业分布
    dn_ind = set(ind.split("-")[0] for _, _, _, ind in D["heavy_fall"])

    top_names = " ".join(n for n, _ in top3)
    top_counts = "/".join(str(len(lst)) for _, lst in top3)
    return [
        f"{top_names} 方向涨停最多，各 {top_counts} 只，呈多点开花格局。" if len(top3) > 1 else f"{top_names} 一枝独秀，{top_counts} 只涨停。",
        f"涨停分布于 {len(lu)} 个申万一级行业，无极端单一主线，板块轮动特征明显。",
        f"最高连板 {max_d} 板（{'、'.join(max_names[:3])}{'…' if len(max_names)>3 else ''}），为情绪最高标。" if max_d > 0 else "今日无连板个股。",
        f"重挫股分散于 {len(dn_ind)} 个行业，无板块性跌停，多为前期高位股派发，属于情绪退潮期个股层面调整。" if dn_ind else "今日无跌超9%个股。",
    ]


# ---------------- 示例（独立运行时输出 demo） ----------------
if __name__ == "__main__":
    demo_data = {
        "day": "20260909",
        "date_cn": "2026年9月9日",
        "lhb_stocks": [
            ["002155.SZ", "湖南黄金", 1, 10.02, 6.11e8, "有色金属-贵金属-贵金属Ⅲ"],
            ["000759.SZ", "中百集团", 2, 10.00, -6.10e7, "商贸零售-零售-百货零售"],
            ["600865.SH", "百大集团", 1, 10.04, 3.2e7, "商贸零售-零售-百货零售"],
            ["301699.SZ", "洛轴股份", 1, 101.45, 3.87e8, "电力设备-风电设备-风电零部件"],
        ],
        "limit_up": [
            ["601890.SH", "亚星锚链", 10.04, "军工装备", "国防军工"],
            ["002155.SZ", "湖南黄金", 10.02, "贵金属", "有色金属"],
        ],
        "limit_down": [
            ["603123.SH", "翠微股份", -10.02, "非银金融-多元金融-多元金融Ⅲ"],
        ],
        "heavy_fall": [
            ["603123.SH", "翠微股份", -10.02, "非银金融-多元金融-多元金融Ⅲ"],
            ["002084.SZ", "海鸥住工", -10.00, "轻工制造-家居用品-其他家居用品"],
        ],
        "streaks": [
            ["600865.SH", "百大集团", 5, "零售"],
            ["000759.SZ", "中百集团", 3, "零售"],
        ],
    }
    build_summary_page(
        demo_data,
        out_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "index_demo.html"),
    )
