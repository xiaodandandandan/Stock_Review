# -*- coding: utf-8 -*-
"""
复盘总览 HTML 生成器
将龙虎榜板块资金 + 涨跌停全景汇总为单页 HTML，
布局与交互逻辑沿用 lhb_template.html（统计色带卡 / 双向条形图 / 分板块贪心双栏卡片 /
响应式阈值：>720px 双栏、≤720px 单栏、≤375px 冻结），不再引用外部长图图片。

用法：
    from build_index_html import build_summary_page
    build_summary_page(data, out_path='index.html')

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
import json


def fmt_flow(v):
    """净流入格式化：亿/万"""
    sign = "+" if v > 0 else "-"
    a = abs(v)
    return f"{sign}{a/1e8:.2f}亿" if a >= 1e8 else f"{sign}{a/1e4:.0f}万"


def _build_sectors(D):
    """龙虎榜个股按一级行业聚合；细分板块取二级行业。
    返回模板 sectors 结构：[[板块, 净流入(万元), [[个股, 细分, 涨跌幅, 净流入(万元)], ...]], ...]
    """
    agg = {}
    for code, name, cnt, chg, flow, ind in D["lhb_stocks"]:
        parts = ind.split("-")
        l1 = parts[0]
        sub = parts[1] if len(parts) > 1 else l1
        agg.setdefault(l1, []).append([name, sub, chg, flow])
    order = sorted(agg.items(), key=lambda kv: sum(x[3] for x in kv[1]), reverse=True)
    return [
        [n, round(sum(s[3] for s in lst) / 1e4, 2),
         [[s[0], s[1], s[2], round(s[3] / 1e4, 2)] for s in lst]]
        for n, lst in order
    ]


# 龙虎榜盘面要点标题与圆点颜色（顺序与 _default_lhb_insights 一致）
LHB_INS_META = [
    ("#e0392e", "净流入最集中"),
    ("#0a9c5b", "净流出最重"),
    ("#e8c37e", "上榜个股最多"),
    ("#13294e", "领涨 / 领跌"),
]


def build_summary_page(data, out_path):
    """
    生成复盘总览 HTML 页面。

    Args:
        data: 数据字典，见模块说明
        out_path: 输出 HTML 路径
    """
    D = data
    day_cn = D.get("date_cn", D.get("day", ""))

    # ---- 龙虎榜：统计卡 + 板块聚合 + 盘面要点 ----
    lhb = D["lhb_stocks"]
    tot_in = sum(s[4] for s in lhb if s[4] > 0)
    tot_out = sum(s[4] for s in lhb if s[4] < 0)
    n_in = sum(1 for s in lhb if s[4] > 0)
    n_out = sum(1 for s in lhb if s[4] < 0)
    net = tot_in + tot_out
    max_streak = max((d for _, _, d, _ in D["streaks"]), default=0)

    stats = [
        {"bar": "v",   "k": "龙虎榜上榜",   "v": len(lhb), "unit": "只", "s": "单日 + 三日榜口径", "cls": "c-mid"},
        {"bar": "in",  "k": "主力净流入",   "v": n_in,     "unit": "只", "s": f"合计 {fmt_flow(tot_in)}", "cls": "c-up"},
        {"bar": "out", "k": "主力净流出",   "v": n_out,    "unit": "只", "s": f"合计 {fmt_flow(tot_out)}", "cls": "c-down"},
        {"bar": "net", "k": "主力资金整体", "v": fmt_flow(net), "unit": "", "s": "净流入" if net >= 0 else "净流出",
         "cls": "c-up" if net >= 0 else "c-down"},
        {"bar": "in",  "k": "收盘涨停",     "v": len(D["limit_up"]), "unit": "只", "s": f"最高连板 {max_streak}板", "cls": "c-up"},
        {"bar": "out", "k": "跌停/重挫",    "v": len(D["limit_down"]), "unit": "只", "s": f"重挫 {len(D['heavy_fall'])} 只", "cls": "c-down"},
    ]

    sectors = _build_sectors(D)
    lhb_ins = D.get("lhb_insights", _default_lhb_insights(sectors, D))
    lhb2_tips = [
        {"color": c, "title": t, "html": h}
        for (c, t), h in zip(LHB_INS_META, lhb_ins)
    ]
    payload = {
        "flowHdr": "主力净流入",
        "stats": stats,
        "sectors": sectors,
        "tips": lhb2_tips,
    }

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

    # ---- 涨停个股明细（逐股：简称 / 一级行业 / 细分板块 / 涨跌幅 / 连板天数） ----
    streak_days = {c: d for c, _n, d, _s in D["streaks"]}
    lu_detail_rows = "\n".join(
        f"<tr><td>{name}</td><td>{l1}</td><td>{sub}</td>"
        f"<td class='num up'>{chg:+.2f}%</td>"
        f"<td class='num'>{streak_days.get(code, '—')}</td></tr>"
        for code, name, chg, sub, l1 in D["limit_up"])

    # ---- 跌停/重挫 ----
    dn = {c for c, *_ in D["limit_down"]}

    def tr_fall(c, n, chg, ind):
        status = '<b class="badge dn">跌停</b>' if c in dn else "重挫"
        return (f"<tr><td>{n}</td><td class='num down'>{chg:+.2f}%</td>"
                f"<td>{ind}</td><td class='num'>{status}</td></tr>")

    hf_rows = "\n".join(tr_fall(c, n, chg, ind) for c, n, chg, ind in D["heavy_fall"])

    limit_ins = D.get("limit_insights", _default_limit_insights(D))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{day_cn} A股复盘 · 龙虎榜板块资金 & 涨跌停全景</title>
<style>__CSS__</style>
</head>
<body>
<div class="page">

  <div class="hero">
    <span class="tag">同花顺 iFinD</span><span class="tag dark">龙虎榜数据</span><span class="tag dark">{day_cn} · 收盘后</span>
    <h1>A股每日复盘 <span class="accent">·</span> 龙虎榜板块资金与涨跌停全景</h1>
    <div class="sub">收盘数据全景复盘 ｜ 龙虎榜板块资金 · 分板块个股明细 · 涨跌停分布</div>
    <div class="hero-line"></div>
  </div>

  <div class="stats" id="stats"></div>

  <div class="sec">
    <div class="sec-head"><span class="sec-no">01</span><span class="sec-title">龙虎榜 · 板块资金分布</span><span class="sec-note">单位：亿元 ｜ 按主力净流入排序 ｜ 红流入绿流出</span></div>
    <div class="chart" id="chart"></div>
    <div class="chart-legend">
      <span class="lg"><i style="background:linear-gradient(90deg,#f06a5e,#e0392e)"></i>净流入（右）</span>
      <span class="lg"><i style="background:linear-gradient(270deg,#3ec58a,#0a9c5b)"></i>净流出（左）</span>
    </div>
  </div>

  <div class="sec">
    <div class="sec-head"><span class="sec-no">02</span><span class="sec-title">龙虎榜 · 分板块个股明细</span><span class="sec-note">组内按主力净流入排序 ｜ 红涨绿跌</span></div>
    <div class="cards" id="cards"></div>
  </div>

  <div class="sec">
    <div class="sec-head"><span class="sec-no">03</span><span class="sec-title">龙虎榜 · 盘面要点</span></div>
    <div class="tips" id="tips"></div>
  </div>

  <div class="sec">
    <div class="sec-head"><span class="sec-no">04</span><span class="sec-title">涨停板块分布与连板梯队</span><span class="sec-note">{len(D['limit_up'])} 只收盘涨停 ｜ 按申万一级归集</span></div>
    <div class="tbox"><table>
      <tr><th>申万一级行业</th><th class="num">涨停数</th><th>个股</th></tr>
      {lu_rows}
    </table></div>
    <div class="tbox"><table>
      <tr><th>连板梯队</th><th class="num">数量</th><th>个股</th></tr>
      {lad_rows}
    </table></div>
    <div class="g-hdr">涨停个股明细 ｜ 共 {len(D['limit_up'])} 只</div>
    <div class="tbox"><table>
      <tr><th>简称</th><th>一级行业</th><th>细分板块</th><th class="num">涨跌幅</th><th class="num">连板</th></tr>
      {lu_detail_rows}
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
    <div class="sec-head"><span class="sec-no">05</span><span class="sec-title">跌停与重挫阵营</span><span class="sec-note">跌幅 ≤ -9% 共 {len(D['heavy_fall'])} 只，其中跌停 {len(D['limit_down'])} 只</span></div>
    <div class="tbox"><table>
      <tr><th>简称</th><th class="num">涨跌幅</th><th>所属行业</th><th class="num">状态</th></tr>
      {hf_rows}
    </table></div>
  </div>

  <div class="foot">
    <div class="ft">口径说明</div>
    <p>① 数据为 {day_cn} 交易日收盘后维度；② 龙虎榜口径为当日上榜（单日+三日榜），主力资金为主力资金净流入额（正=流入，负=流出），涨跌幅为前复权口径；③ 涨停/跌停为当日收盘价触及涨跌停价（含一字板、ST 5% 板），重挫为跌幅 ≤ -9%；④ 行业为同花顺（申万）分类；⑤ 连板为连续涨停天数。</p>
    <p class="disc">数据来源：同花顺 iFinD ｜ 以上内容基于公开数据，不构成投资建议。</p>
  </div>

</div>
<script id="lhb2-data" type="application/json">__LHB2_DATA__</script>
<script>__LHB2_JS__</script>
</body>
</html>
"""
    html = (html.replace("__CSS__", CSS)
                .replace("__LHB2_DATA__", json.dumps(payload, ensure_ascii=False))
                .replace("__LHB2_JS__", LHB2_JS))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[build_summary_page] saved {out_path}")
    return out_path


# 全站样式：深蓝金视觉体系 + lhb_template.html 布局逻辑
CSS = """
  * { margin:0; padding:0; box-sizing:border-box; }
  html { -webkit-text-size-adjust:100%; }
  body { background:#eef1f5; font-family:'Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif; color:#1c2430; font-variant-numeric:tabular-nums; -webkit-font-smoothing:antialiased; }
  .page { width:100%; max-width:960px; margin:0 auto; background:#eef1f5; padding:0 0 60px; }

  /* ---------- header ---------- */
  .hero { background:linear-gradient(135deg,#ffffff 0%,#f6f8fb 55%,#edf1f8 100%); padding:44px 48px 36px; border-bottom:1px solid #e6e9ef; }
  .tag { font-size:13px; letter-spacing:2px; color:#b8862f; border:1px solid rgba(217,178,95,.55); background:rgba(217,178,95,.07); padding:4px 12px; border-radius:3px; margin-right:8px; display:inline-block; margin-bottom:6px; }
  .tag.dark { color:#68758a; border-color:rgba(104,117,138,.32); background:rgba(104,117,138,.05); }
  h1 { font-size:38px; font-weight:900; letter-spacing:2px; margin:18px 0 10px; color:#13294e; line-height:1.25; }
  h1 .accent { color:#c9974a; }
  .sub { font-size:15px; color:#5a6778; letter-spacing:1px; line-height:1.6; }
  .hero-line { width:64px; height:5px; background:linear-gradient(90deg,#e8c37e,#e0392e); border-radius:3px; margin-top:20px; }

  /* ---------- stats（模板逻辑：顶部色带统计卡） ---------- */
  .stats { display:flex; gap:14px; padding:22px 32px 6px; }
  .stat { flex:1; background:#fff; border-radius:10px; padding:16px 14px; border:1px solid #e6e9ef; box-shadow:0 2px 8px rgba(16,32,64,.05); position:relative; overflow:hidden; }
  .stat::before { content:''; position:absolute; top:0; left:0; right:0; height:4px; }
  .stat.v::before { background:#7c8aa0; }
  .stat.in::before { background:#e0392e; }
  .stat.out::before { background:#0a9c5b; }
  .stat.net::before { background:#13294e; }
  .stat .k { font-size:12px; color:#8a93a3; margin-bottom:8px; }
  .stat .v { font-size:24px; font-weight:900; line-height:1; }
  .stat .v small { font-size:12px; font-weight:500; color:#8a93a3; margin-left:4px; }
  .stat .s { font-size:11px; color:#9aa3b2; margin-top:7px; }
  .c-up { color:#d92c20; } .c-down { color:#06894f; } .c-mid { color:#13294e; }

  /* ---------- section ---------- */
  .sec { padding:26px 32px 8px; }
  .sec-head { display:flex; align-items:baseline; gap:12px; margin-bottom:14px; flex-wrap:wrap; }
  .sec-no { font-size:13px; font-weight:900; color:#d9b25f; letter-spacing:1px; }
  .sec-title { font-size:21px; font-weight:900; color:#13294e; }
  .sec-note { font-size:12px; color:#9aa3b2; margin-left:auto; }

  /* ---------- diverging bars（模板逻辑：双向条形图） ---------- */
  .chart { background:#fff; border-radius:10px; border:1px solid #e6e9ef; padding:16px 20px 10px; box-shadow:0 2px 8px rgba(16,32,64,.05); }
  .crow { display:flex; align-items:center; height:29px; }
  .crow .name { width:96px; font-size:13px; font-weight:700; color:#2a3648; flex:none; }
  .crow .cnt { width:34px; flex:none; font-size:11px; color:#9aa3b2; }
  .crow .zone { flex:1; height:100%; position:relative; }
  .zone .axis { position:absolute; left:50%; top:3px; bottom:3px; width:1px; background:#e3e7ee; }
  .zone .bar { position:absolute; top:8px; height:13px; border-radius:2px; }
  .zone .bar.pos { left:50%; background:linear-gradient(90deg,#f06a5e,#e0392e); }
  .zone .bar.neg { right:50%; background:linear-gradient(270deg,#3ec58a,#0a9c5b); }
  .zone .bar.pos, .zone .bar.neg { max-width:calc(50% - 2px); }
  .crow .val { width:86px; flex:none; text-align:right; font-size:13px; font-weight:700; }
  .chart-legend { display:flex; justify-content:center; gap:26px; padding:8px 0 6px; font-size:12px; color:#8a93a3; }
  .lg { display:flex; align-items:center; gap:6px; }
  .lg i { width:18px; height:8px; border-radius:2px; display:inline-block; }

  /* ---------- sector cards（模板逻辑：分板块个股明细） ---------- */
  .cards { display:flex; gap:14px; align-items:flex-start; }
  .cards .col { flex:1; min-width:0; display:flex; flex-direction:column; gap:14px; }
  .card { background:#fff; border-radius:10px; border:1px solid #e6e9ef; box-shadow:0 2px 8px rgba(16,32,64,.05); overflow:hidden; }
  .card-h { display:flex; align-items:center; gap:10px; padding:13px 18px; background:#f7f9fc; border-bottom:1px solid #edf0f5; }
  .card-h.pin { border-left:4px solid #e0392e; }
  .card-h.nin { border-left:4px solid #0a9c5b; }
  .card-h .sname { font-size:17px; font-weight:900; color:#13294e; letter-spacing:1px; }
  .card-h .scnt { font-size:11px; color:#68758a; background:#eef1f6; border-radius:10px; padding:2px 9px; }
  .card-h .sflow { margin-left:auto; font-size:16px; font-weight:900; }
  .cols { display:grid; grid-template-columns:88px 1fr 72px 118px; padding:7px 18px; font-size:11px; color:#9aa3b2; border-bottom:1px solid #f0f2f6; }
  .cols div:nth-child(1) { padding-right:14px; }
  .cols div:nth-child(3), .cols div:nth-child(4) { text-align:right; }
  .row { display:grid; grid-template-columns:88px 1fr 72px 118px; align-items:center; padding:9px 18px; border-bottom:1px solid #f4f6f9; }
  .row:nth-child(even) { background:#fafbfd; }
  .row:last-child { border-bottom:none; }
  .row .nm { line-height:1.25; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding-right:14px; }
  .row .nm b { font-size:15px; font-weight:700; color:#1c2430; }
  .row .sub { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-size:12px; color:#8a93a3; min-width:0; }
  .row .pct { text-align:right; white-space:nowrap; }
  .row .pct i { font-style:normal; font-size:13px; font-weight:700; }
  .i-up { color:#d92c20; }
  .i-down { color:#06894f; }
  .row .fl { text-align:right; font-size:14px; font-weight:900; white-space:nowrap; }

  /* 单栏模式（JS 添加 .single）：≤720px 切单栏，>720px 贪心流双栏 */
  .cards.single { display:block; }
  .cards.single .card { margin-bottom:14px; }
  .cards.single .card:last-child { margin-bottom:0; }

  /* 窄窗口（≤820px）压缩列宽与字体，保证细分板块 / 龙虎榜数据不换行（721–820px 仍双栏） */
  @media (max-width:820px) {
    html,body { overflow-x:hidden; }
    .stats { flex-wrap:wrap; }
    .stat { flex:1 1 42%; min-width:150px; }
    .stat .k { font-size:12px; }
    .stat .v { font-size:22px; }
    .stat .v small { font-size:12px; }
    .tips { grid-template-columns:1fr; }
    .sec { padding:18px 14px 8px; }
    .card-h { padding:11px 14px; }
    .card-h .sname { font-size:15px; }
    .card-h .sflow { font-size:15px; }
    .cols, .row { grid-template-columns:62px 1fr 56px 74px; padding:7px 12px; }
    .row { padding:8px 12px; }
    .cols { font-size:10px; }
    .cols div:nth-child(1) { padding-right:10px; }
    .row .nm { padding-right:10px; }
    .row .nm b { font-size:13px; }
    .row .sub { font-size:11px; }
    .row .pct i { font-size:12px; }
    .row .fl { font-size:12px; }
  }

  /* ≤720px 单栏（>720px 由 JS 贪心流双栏） */
  @media (max-width:720px) {
    .cards { display:block; }
    .cards .card { margin-bottom:14px; }
    .cards .card:last-child { margin-bottom:0; }
  }

  /* ≤375px 冻结：页面按 375px 宽度渲染，不再随窗口缩小而改动布局 */
  @media (max-width:375px) {
    html,body { overflow-x:hidden; }
    .page { min-width:375px; }
  }

  /* ---------- 涨跌停表格 ---------- */
  .tbox { background:#fff; border-radius:10px; border:1px solid #e6e9ef; box-shadow:0 2px 8px rgba(16,32,64,.05); padding:8px 0 4px; overflow:hidden; }
  .tbox + .tbox { margin-top:14px; }
  .g-hdr { font-size:13px; font-weight:700; color:#13294e; margin:18px 0 6px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { text-align:left; font-size:12px; color:#8a93a3; font-weight:600; padding:9px 16px; border-bottom:1px solid #edf0f5; white-space:nowrap; }
  td { padding:8px 16px; border-bottom:1px solid #f4f6f9; color:#2a3648; }
  tr:last-child td { border-bottom:none; }
  tr:nth-child(even) td { background:#fafbfd; }
  td.num, th.num { text-align:right; font-weight:700; white-space:nowrap; }
  td.names { color:#68758a; word-break:break-all; }
  .up { color:#d92c20; } .down { color:#06894f; }
  .badge { display:inline-block; font-size:12px; color:#8a6417; background:#fdf3dd; border-radius:8px; padding:2px 8px; font-weight:700; white-space:nowrap; }
  .badge.dn { color:#06894f; background:#e6f5ec; }

  /* ---------- insights ---------- */
  .tips { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:14px; }
  .tip { background:#fff; border-radius:10px; border:1px solid #e6e9ef; box-shadow:0 2px 8px rgba(16,32,64,.05); padding:16px 18px; }
  .tip .t { font-size:14px; font-weight:900; margin-bottom:7px; color:#13294e; display:flex; align-items:center; gap:8px; }
  .tip .t .dot { width:8px; height:8px; border-radius:50%; flex:none; }
  .tip p { font-size:12.5px; line-height:1.75; color:#4a5568; }
  .tip p b.r { color:#d92c20; } .tip p b.g { color:#06894f; }

  /* ---------- footer ---------- */
  .foot { margin:26px 32px 0; background:#fff; border:1px solid #e6e9ef; border-radius:10px; color:#4a5568; padding:18px 22px; }
  .foot .ft { font-size:13px; font-weight:700; color:#b8862f; margin-bottom:6px; }
  .foot p { font-size:11.5px; line-height:1.8; color:#68758a; }
  .foot .disc { margin-top:8px; padding-top:8px; border-top:1px solid #e6e9ef; color:#9aa3b2; }

  /* ---------- 移动端（≤640px）缩字号 ---------- */
  @media (max-width:640px) {
    .page { padding:0 0 40px; }
    .hero { padding:28px 20px 24px; }
    h1 { font-size:26px; letter-spacing:1px; margin:14px 0 8px; }
    .sub { font-size:13px; letter-spacing:0; }
    .tag { font-size:11px; letter-spacing:1px; padding:3px 10px; margin-right:6px; }
    .sec-head { gap:8px; margin-bottom:10px; }
    .sec-no { font-size:11px; }
    .sec-title { font-size:17px; }
    .sec-note { font-size:10px; margin-left:0; width:100%; order:3; }
    .tip { padding:12px 14px; border-radius:8px; }
    .tip .t { font-size:13px; margin-bottom:5px; }
    .tip p { font-size:12px; line-height:1.7; }
    table { font-size:12px; }
    th, td { padding:7px 10px; }
    th { font-size:11px; }
    .foot { margin:18px 14px 0; padding:14px 16px; border-radius:8px; }
    .foot p { font-size:11px; }
  }
  @media (max-width:380px) {
    h1 { font-size:22px; }
    table { font-size:11px; }
    th, td { padding:6px 8px; }
  }
"""


# 龙虎榜两部分渲染逻辑（对照 lhb_template.html）：统计卡 / 双向条形图 / 贪心双栏卡片
LHB2_JS = """(function(){
  const LHB2 = JSON.parse(document.getElementById('lhb2-data').textContent);
  const $ = id => document.getElementById(id);
  function fmtFlow(v){
    const s = v>0?'+':(v<0?'-':''), a = Math.abs(v);
    return s + (a>=10000 ? (a/10000).toFixed(2)+'亿' : Math.round(a)+'万');
  }
  function pctCls(p){ return p>=0?'i-up':'i-down'; }
  function pctTxt(p){ return (p>0?'+':'')+p.toFixed(2)+'%'; }
  function flowCls(v){ return v>=0?'c-up':'c-down'; }

  /* ---- 统计卡 ---- */
  LHB2.stats.forEach(s => {
    const el = document.createElement('div');
    el.className = 'stat ' + s.bar;
    el.innerHTML = '<div class="k">'+s.k+'</div><div class="v '+s.cls+'">'+s.v
      + (s.unit ? '<small>'+s.unit+'</small>' : '') + '</div><div class="s">'+s.s+'</div>';
    $('stats').appendChild(el);
  });

  /* ---- 01 板块资金分布：双向条形图 ---- */
  const MAXABS = Math.max(1, ...LHB2.sectors.map(s => Math.abs(s[1])));
  LHB2.sectors.forEach(([name, flow, stocks]) => {
    const w = Math.max(3, Math.abs(flow)/MAXABS*172);
    const r = document.createElement('div'); r.className = 'crow';
    r.innerHTML = '<div class="name">'+name+'</div><div class="cnt">'+stocks.length+'只</div>'
      + '<div class="zone"><div class="axis"></div>'
      + (flow>=0 ? '<div class="bar pos" style="width:'+w+'px"></div>' : '<div class="bar neg" style="width:'+w+'px"></div>')
      + '</div><div class="val '+flowCls(flow)+'">'+fmtFlow(flow)+'</div>';
    $('chart').appendChild(r);
  });

  /* ---- 02 分板块个股明细：贪心双栏卡片 ---- */
  const cardsEl = $('cards');
  const sectorCards = [];
  LHB2.sectors.forEach(([name, flow, stocks]) => {
    const card = document.createElement('div'); card.className = 'card';
    const rows = stocks.map(([n, sub, chg, f]) =>
      '<div class="row"><div class="nm"><b>'+n+'</b></div><div class="sub">'+sub+'</div>'
      + '<div class="pct"><i class="'+pctCls(chg)+'">'+pctTxt(chg)+'</i></div>'
      + '<div class="fl '+flowCls(f)+'">'+fmtFlow(f)+'</div></div>').join('');
    card.innerHTML = '<div class="card-h '+(flow>=0?'pin':'nin')+'">'
      + '<span class="sname">'+name+'</span><span class="scnt">'+stocks.length+' 只上榜</span>'
      + '<span class="sflow '+flowCls(flow)+'">'+fmtFlow(flow)+'</span></div>'
      + '<div class="cols"><div>个股</div><div>细分板块</div><div>当日涨跌幅</div><div>'+LHB2.flowHdr+'</div></div>'
      + rows;
    sectorCards.push(card);
  });
  /* 布局：宽视口（>720px）→ 双栏贪心均衡；窄视口（≤720px）→ 单栏按原顺序 */
  const mqNarrow = window.matchMedia('(max-width: 720px)');
  const cardsVisible = () => cardsEl.offsetParent !== null;
  function layoutCards(){
    if (!cardsVisible()) return;   // 明细区被 display:none 隐藏时 offsetHeight 全为 0，跳过避免全挤进第一列
    cardsEl.innerHTML = '';
    if (mqNarrow.matches) {
      cardsEl.classList.add('single');
      sectorCards.forEach(c => cardsEl.appendChild(c));
    } else {
      cardsEl.classList.remove('single');
      const cols = [0,1].map(() => {
        const c = document.createElement('div'); c.className = 'col'; cardsEl.appendChild(c); return c;
      });
      sectorCards.forEach(card => {
        const [l, r] = cols;
        (l.offsetHeight <= r.offsetHeight ? l : r).appendChild(card);
      });
    }
  }
  window.addEventListener('load', layoutCards);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(layoutCards);
  mqNarrow.addEventListener('change', layoutCards);
  /* 明细区被外部切走 display 再切回（如渲染脚本切图）时，重新分流 */
  new MutationObserver(() => { if (cardsVisible()) layoutCards(); })
    .observe(cardsEl, { attributes: true, attributeFilter: ['style'] });

  /* ---- 03 盘面要点 ---- */
  LHB2.tips.forEach(t => {
    const el = document.createElement('div'); el.className = 'tip';
    el.innerHTML = '<div class="t"><span class="dot" style="background:'+t.color+'"></span>'+t.title+'</div><p>'+t.html+'</p>';
    $('tips').appendChild(el);
  });
})();
"""


def _default_lhb_insights(sectors, D):
    """默认龙虎榜盘面要点（4 条），按数据自动生成"""
    if not sectors or not D.get("lhb_stocks"):
        return ["当日无龙虎榜上榜个股数据。"] * 4
    # 净流入第一板块
    top_name, _, top_stocks = sectors[0]
    top_total = sum(s[3] for s in top_stocks)
    top_buy = max(top_stocks, key=lambda x: x[3])
    # 净流出最后板块
    bot_name, _, bot_stocks = sectors[-1]
    bot_total = sum(s[3] for s in bot_stocks)
    bot_sell = min(bot_stocks, key=lambda x: x[3])
    # 上榜最多板块
    most = max(sectors, key=lambda kv: len(kv[2]))
    most_name, most_up = most[0], sum(1 for s in most[2] if s[2] > 0)
    most_out = sum(1 for s in most[2] if s[3] < 0)
    # 领涨领跌
    best = max(D["lhb_stocks"], key=lambda s: s[3])
    worst = min(D["lhb_stocks"], key=lambda s: s[3])

    return [
        f"{top_name} <b class='r'>{fmt_flow(top_total * 1e4)}</b>：{top_buy[0]} {top_buy[2]:+.2f}% 获主力 <b class='r'>{fmt_flow(top_buy[3] * 1e4)}</b>，为净买入主力。",
        f"{bot_name} <b class='g'>{fmt_flow(bot_total * 1e4)}</b>：{bot_sell[0]} {bot_sell[2]:+.2f}% 主力 <b class='g'>{fmt_flow(bot_sell[3] * 1e4)}</b>，为主要砸盘方向。",
        f"{most_name} <b>{len(most[2])}</b> 只上榜为今日最大群体，其中 {most_up} 只上涨但 {most_out} 只主力净流出，板块内部分化。",
        f"领涨：{best[1]} <b class='r'>{best[3]:+.2f}%</b>，主力 {fmt_flow(best[4])}；领跌：{worst[1]} <b class='g'>{worst[3]:+.2f}%</b>，主力 {fmt_flow(worst[4])}。",
    ]


def _default_limit_insights(D):
    """默认涨跌停要点（4 条），按数据自动生成"""
    # 涨停行业 top3
    lu = {}
    for code, name, chg, sub, l1 in D["limit_up"]:
        lu.setdefault(l1, []).append(name)
    if not lu:
        return ["当日无涨停个股数据。"] * 4
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