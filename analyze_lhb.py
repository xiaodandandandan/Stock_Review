# -*- coding: utf-8 -*-
"""
龙虎榜个股 · 板块资金整合分析（数据来源：同花顺 iFinD MCP）

分析流程（与 2026-09-08 复盘一致）：
  1. search_stocks 智能选股：获取指定交易日龙虎榜上榜个股名单（上榜次数>0）
  2. search_stocks 分两组查询：主力净流入组 / 主力净流出组的当日涨跌幅与主力资金流向
     （净流入与净流出需分开问，引擎对"净流入"问句会自动过滤掉流出个股）
  3. search_stocks 查询上榜个股所属同花顺行业（一/二/三级）
  4. 个别缺失数据的个股，用 get_stock_performance 单指标问句补足（每批≤5只）
  5. 按同花顺一级行业聚合主力资金，输出 Markdown 报告（板块汇总 + 个股明细）
  6. 数据注入 lhb_template.html 生成数据页，调用 puppeteer 渲染两张长图：
     ① 板块资金分布（统计 + 分布图 + 盘面要点） ② 分板块个股明细

依赖：pip install requests ｜ 长图另需 node + npm install（puppeteer、中文字体）
认证：export IFIND_AUTH_TOKEN=<同花顺MCP密钥>
用法：python analyze_lhb.py [YYYYMMDD]（默认今天）

注：search_stocks 为自然语言取数，偶发解析失败时返回空表，
    可微调问句表达后重试；涨跌幅为前复权口径，资金单位为元。
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import urllib3
from datetime import date

import requests

urllib3.disable_warnings()

BASE = "https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-stock-mcp"
SESSION_ID = None
_REQ_ID = 0


# ---------------- MCP HTTP 客户端 ----------------

def _headers():
    token = os.getenv("IFIND_AUTH_TOKEN")
    if not token:
        raise RuntimeError("请先设置环境变量 IFIND_AUTH_TOKEN（同花顺MCP密钥）")
    h = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": token,
    }
    if SESSION_ID:
        h["Mcp-Session-Id"] = SESSION_ID
    return h


def _init():
    global SESSION_ID
    if SESSION_ID:
        return
    payload = {
        "jsonrpc": "2.0",
        "id": _next_id(),
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "lhb-analyzer", "version": "1.0.0"},
        },
    }
    resp = requests.post(BASE, json=payload, headers=_headers(), verify=False, timeout=30)
    resp.raise_for_status()
    SESSION_ID = resp.headers.get("Mcp-Session-Id")
    if not SESSION_ID:
        raise RuntimeError("initialize 未返回 Mcp-Session-Id")
    requests.post(
        BASE,
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers=_headers(), verify=False, timeout=10,
    )


def _next_id():
    global _REQ_ID
    _REQ_ID += 1
    return _REQ_ID


def call_tool(tool_name, query):
    """调用 stock 服务 MCP 工具，返回 answer 文本（内含 Markdown 表格）"""
    _init()
    payload = {
        "jsonrpc": "2.0",
        "id": _next_id(),
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": {"query": query}},
    }
    resp = requests.post(BASE, json=payload, headers=_headers(), verify=False, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"MCP 调用失败: {data['error']}")
    text = data["result"]["content"][0]["text"]      # {"code":1,"msg":..,"data":"{...}"}
    outer = json.loads(text)
    if outer.get("code") != 1:
        raise RuntimeError(f"接口返回异常: {outer.get('msg')}")
    return json.loads(outer["data"]).get("answer", "")


# ---------------- 表格与数值解析 ----------------

def parse_md_table(answer):
    """解析 answer 中的 Markdown 表格为 [dict, ...]，以表头为键"""
    table = [l.strip() for l in answer.splitlines() if l.strip().startswith("|")]
    if len(table) < 3:
        return []
    headers = [c.strip() for c in table[0].strip("|").split("|")]
    rows = []
    for line in table[2:]:                          # 跳过表头与分隔行
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def _col(row, *keywords):
    """按关键字模糊匹配列名取值（跳过'排名'类干扰列）"""
    for k, v in row.items():
        if all(kw in k for kw in keywords) and "排名" not in k:
            return v
    for k, v in row.items():
        if all(kw in k for kw in keywords):
            return v
    return ""


def parse_cn_number(s):
    """解析 '8333.99万' / '-845760.69' / '-1.42亿' 等中文单位数值，统一返回元"""
    s = (s or "").strip()
    if not s:
        return None
    neg = s.startswith("-")
    s = s.lstrip("+-")
    mult = 1.0
    if s.endswith("万"):
        mult, s = 1e4, s[:-1]
    elif s.endswith("亿"):
        mult, s = 1e8, s[:-1]
    try:
        v = float(s) * mult
    except ValueError:
        return None
    return -v if neg else v


# ---------------- 取数步骤 ----------------

def cn_date(day):
    return f"{int(day[:4])}年{int(day[4:6])}月{int(day[6:8])}日"


def fetch_lhb_list(day):
    """步骤1：龙虎榜上榜个股名单（上榜次数>0）"""
    q = f"{cn_date(day)}龙虎榜上榜次数大于0的股票，显示当日上榜次数，按上榜次数降序"
    stocks = {}
    for r in parse_md_table(call_tool("search_stocks", q)):
        cnt = _col(r, "上榜次数")
        try:
            cnt = int(cnt)
        except (TypeError, ValueError):
            continue                                  # 次数为空 = 未上榜，跳过
        code = _col(r, "股票代码")
        stocks[code] = {"代码": code, "简称": _col(r, "股票简称"), "上榜次数": cnt}
    return stocks


def fetch_flows(day, stocks):
    """步骤2：分净流入/净流出两组查询涨跌幅与主力资金流向（单位：元）"""
    d = cn_date(day)
    queries = [
        f"{d}龙虎榜上榜次数大于0的股票，显示{d}的涨跌幅、主力资金净流入额，按主力资金净流入额降序",
        f"{d}龙虎榜上榜次数大于0且当日主力资金净流出的股票，显示{d}的涨跌幅、主力资金净流出额，按主力资金净流出额降序",
    ]
    got = set()
    for q in queries:
        for r in parse_md_table(call_tool("search_stocks", q)):
            code = _col(r, "股票代码")
            chg, flow = _col(r, "涨跌幅"), _col(r, "主力资金")
            if code in stocks and chg and flow:
                try:
                    stocks[code]["涨跌幅"] = float(chg)
                    stocks[code]["净流入"] = float(flow)   # 接口返回元（科学计数法）
                    got.add(code)
                except ValueError:
                    pass

    # 步骤2补充：分组问句遗漏的个股，用 get_stock_performance 每批≤5只补足
    missing = [c for c in stocks if c not in got]
    for i in range(0, len(missing), 5):
        batch = missing[i:i + 5]
        names = "、".join(stocks[c]["简称"] for c in batch)
        q = f"{names}{d}的涨跌幅与主力资金净流入额"
        for r in parse_md_table(call_tool("get_stock_performance", q)):
            code = _col(r, "证券代码")
            if code in stocks:
                flow = parse_cn_number(_col(r, "主力净流入"))
                try:
                    chg = float(_col(r, "涨跌幅"))
                except ValueError:
                    chg = None
                if flow is not None:
                    stocks[code]["净流入"] = flow
                if chg is not None:
                    stocks[code]["涨跌幅"] = chg
    return stocks


def fetch_industries(day, stocks):
    """步骤3：所属同花顺行业（如 '煤炭-煤炭开采加工-焦炭加工'）"""
    q = f"{cn_date(day)}龙虎榜上榜次数大于0的股票，显示所属同花顺行业"
    for r in parse_md_table(call_tool("search_stocks", q)):
        code = _col(r, "股票代码")
        if code in stocks:
            stocks[code]["行业"] = _col(r, "所属同花顺行业") or "未分类"
    for s in stocks.values():
        s.setdefault("行业", "未分类")
        s.setdefault("涨跌幅", None)
        s.setdefault("净流入", None)
    return stocks


# ---------------- 聚合与输出 ----------------

def fmt_flow(v):
    """元 → 中文单位字符串（+/-）"""
    if v is None:
        return "暂无数据"
    sign = "+" if v > 0 else ("-" if v < 0 else "")
    a = abs(v)
    if a >= 1e8:
        return f"{sign}{a / 1e8:.2f}亿"
    return f"{sign}{a / 1e4:.0f}万"


def aggregate(stocks):
    """按同花顺一级行业聚合：板块内按主力净流入降序，板块间按净流入合计降序"""
    sectors = {}
    for s in stocks.values():
        sectors.setdefault(s["行业"].split("-")[0], []).append(s)
    for lst in sectors.values():
        lst.sort(key=lambda x: (x["净流入"] is None, -(x["净流入"] or 0)))
    return sorted(
        sectors.items(),
        key=lambda kv: sum(x["净流入"] or 0 for x in kv[1]),
        reverse=True,
    )


def build_report(day, stocks, source="同花顺 iFinD"):
    """步骤4-5：按一级行业聚合，生成 Markdown 报告（source 标注数据来源）"""
    em = source.startswith("东方财富")
    ordered = aggregate(stocks)

    inflow = [s for s in stocks.values() if (s["净流入"] or 0) > 0]
    outflow = [s for s in stocks.values() if (s["净流入"] or 0) < 0]
    tot_in = sum(s["净流入"] for s in inflow)
    tot_out = sum(s["净流入"] for s in outflow)

    in_k = "净买入" if em else "主力净流入"
    out_k = "净卖出" if em else "主力净流出"
    lines = [
        f"# 龙虎榜个股按板块整合（{cn_date(day)}）",
        "",
        f"共 **{len(stocks)}** 只个股上榜。{in_k} **{len(inflow)}** 只，合计 "
        f"**{fmt_flow(tot_in)}**；{out_k} **{len(outflow)}** 只，合计 "
        f"**{fmt_flow(tot_out)}**；整体 **{fmt_flow(tot_in + tot_out)}**。",
        "",
        "## 板块汇总（按%s排序）" % in_k,
        "",
        "| 板块（%s） | 上榜数 | %s合计 |" % ("东财一级" if em else "同花顺一级", in_k),
        "|---|---|---|",
    ]
    for name, lst in ordered:
        total = sum(x["净流入"] or 0 for x in lst)
        lines.append(f"| {name} | {len(lst)} | {fmt_flow(total)} |")

    lines += ["", "## 个股明细（按板块分组，组内按%s排序）" % in_k, "",
              "| 板块 | 细分板块 | 简称 | 当日涨跌幅 | %s |" % in_k,
              "|---|---|---|---|---|"]
    for name, lst in ordered:
        for s in lst:
            chg = "暂无数据" if s["涨跌幅"] is None else f"{s['涨跌幅']:+.2f}%"
            lines.append(
                f"| {name} | {s['行业']} | {s['简称']}"
                f" | {chg} | {fmt_flow(s['净流入'])} |"
            )

    flow_note = ("净流入为龙虎榜净买入额（正=净买入，负=净卖出）；板块为东财一级行业。"
                 if em else "主力资金净流入额（正=流入，负=流出）；")
    lines += [
        "",
        "---",
        "口径说明：涨跌幅为%s口径；%s" % ("当日" if em else "前复权", flow_note),
        "数据为当日收盘后维度。数据来源：%s。" % source,
        "以上内容基于公开数据，不构成投资建议。",
    ]
    return "\n".join(lines)


# ---------------- 长图生成（模板注入 + puppeteer 渲染两张图） ----------------

WEEKDAYS = "一二三四五六日"


def _find_chrome():
    """定位无头浏览器：环境变量优先，其次探测 puppeteer 缓存"""
    exe = os.getenv("PUPPETEER_EXECUTABLE_PATH")
    if exe and os.path.exists(exe):
        return exe
    for pat in (
        "~/.cache/puppeteer/chrome-headless-shell/*/chrome-headless-shell-linux64/chrome-headless-shell",
        "~/.cache/puppeteer/chrome/*/chrome-linux64/chrome",
    ):
        hits = glob.glob(os.path.expanduser(pat))
        if hits:
            return sorted(hits)[-1]
    return None


def _sector_total(lst):
    """板块资金合计（元）"""
    return sum(x["净流入"] or 0 for x in lst)


def build_tips(ordered, stocks, source="同花顺 iFinD"):
    """自动生成盘面要点（富文本 HTML，颜色/标题/内容）"""
    em = source.startswith("东方财富")
    in_k = "净买入" if em else "主力净流入"
    out_k = "净卖出" if em else "主力净流出"
    flow_tag = "净买入" if em else "主力"
    sell_tag = "净卖出" if em else "主力"

    def chg(s):
        return "暂无数据" if s["涨跌幅"] is None else f"{s['涨跌幅']:+.2f}%"

    def flow(s):
        return fmt_flow(s["净流入"])

    def flow_abs(s):                       # 卖出侧纯绝对值（东财：'净卖出 1.28亿'，不带符号/双重否定）
        v = s["净流入"]
        if v is None:
            return "暂无数据"
        a = abs(v)
        return f"{a / 1e8:.2f}亿" if a >= 1e8 else f"{a / 1e4:.0f}万"

    sell_disp = flow_abs if em else flow   # iFinD 保持 '主力 -1.28亿' 原口径
    total = _sector_total
    tips = []
    # 1) 资金集中度最高：前两大板块及其领头个股
    pos = [(n, l) for n, l in ordered if total(l) > 0]
    if pos:
        n1, l1 = pos[0]
        lead = l1[0]
        seg = (f"{n1} <b class=\"r\">{fmt_flow(total(l1))}</b>：{lead['简称']} {chg(lead)}"
               f" 获{flow_tag} <b class=\"r\">{flow(lead)}</b>")
        if len(pos) > 1:
            n2, l2 = pos[1]
            lead2 = l2[0]
            seg += f"；{n2} <b class=\"r\">{fmt_flow(total(l2))}</b>：{lead2['简称']} {flow(lead2)}"
        tips.append({"color": "#e0392e", "title": f"{in_k}最集中", "html": seg + "。"})
    # 2) 资金流出最重：流出最重板块及其压力最大的两只个股
    neg = [(n, l) for n, l in reversed(ordered) if total(l) < 0]
    if neg:
        n1, l1 = neg[0]
        heavy = l1[-1]
        seg = (f"{n1} <b class=\"g\">{fmt_flow(total(l1))}</b>：{heavy['简称']} {chg(heavy)}"
               f" 遭{sell_tag} <b class=\"g\">{sell_disp(heavy)}</b>")
        if len(l1) > 1:
            second = l1[-2]
            seg += f"；{second['简称']} {chg(second)} 且{out_k} {sell_disp(second)}"
        tips.append({"color": "#0a9c5b", "title": f"{out_k}最重", "html": seg + "。"})
    # 3) 上榜个股最多：数量、板块整体资金、上涨但流出的家数提示
    if ordered:
        n, l = max(ordered, key=lambda kv: len(kv[1]))
        t = total(l)
        up_out = sum(1 for x in l if (x["涨跌幅"] or 0) > 0 and (x["净流入"] or 0) < 0)
        cls = "g" if t < 0 else "r"
        tail = "警惕高位派发" if t < 0 else "整体获资金净增持"
        seg = f"{n} <b>{len(l)}</b> 只上榜，板块整体 <b class=\"{cls}\">{fmt_flow(t)}</b>"
        if up_out:
            seg += f"，其中 {up_out} 只上涨但{out_k}"
        tips.append({"color": "#e8c37e", "title": "上榜个股最多", "html": seg + f"，{tail}。"})
    # 4) 领涨 / 领跌焦点
    ranked = [s for s in stocks.values() if s["涨跌幅"] is not None]
    if ranked:
        top = max(ranked, key=lambda x: x["涨跌幅"])
        low = min(ranked, key=lambda x: x["涨跌幅"])
        tips.append({
            "color": "#13294e", "title": "领涨 / 领跌",
            "html": (f"{top['简称']} 大涨 {top['涨跌幅']:+.2f}%，{flow_tag} {flow(top)}；"
                     f"{low['简称']} 领跌 {low['涨跌幅']:+.2f}%，{sell_tag} {sell_disp(low)}。"),
        })
    return tips


def build_page_data(day, stocks, source="同花顺 iFinD"):
    """构造注入模板的页面数据（JSON 结构与 lhb_template.html 约定一致，资金单位：万元）"""
    em = source.startswith("东方财富")
    in_k = "净买入" if em else "主力净流入"
    out_k = "净卖出" if em else "主力净流出"
    d = date(int(day[:4]), int(day[4:6]), int(day[6:8]))
    ordered = aggregate(stocks)
    inflow = [s for s in stocks.values() if (s["净流入"] or 0) > 0]
    outflow = [s for s in stocks.values() if (s["净流入"] or 0) < 0]
    tot_in = sum(s["净流入"] for s in inflow)
    tot_out = sum(s["净流入"] for s in outflow)
    net = tot_in + tot_out

    note = "收盘后口径"

    def sub_of(s):
        parts = s["行业"].split("-")[1:]
        return "-".join(parts) if parts else s["行业"]

    if em:
        foot = ("① 数据为 {d} 交易日收盘后维度；② 涨跌幅为当日口径；③ 资金列为龙虎榜净买入额"
                "（正 = 净买入，负 = 净卖出）；④ 板块归类采用东方财富行业分类（一级）；"
                "⑤ 金额单位：亿元 / 万元。")
    else:
        foot = ("① 数据为 {d} 交易日收盘后维度；② 涨跌幅为前复权口径；③ 资金列为主力资金净流入额"
                "（正 = 净流入，负 = 净流出）；④ 板块归类采用同花顺行业分类（展示至二级/三级细分）；"
                "⑤ 金额单位：亿元 / 万元。")
    sectors = []
    for name, lst in ordered:
        rows = [
            [s["简称"], sub_of(s),
             round(s["涨跌幅"] or 0.0, 2), round((s["净流入"] or 0) / 1e4)]
            for s in lst
        ]
        sectors.append([name, round(_sector_total(lst) / 1e4), rows])

    return {
        "meta": {
            "day": day,
            "dateHyphen": f"{day[:4]}-{day[4:6]}-{day[6:8]}",
            "dateTag": f"{day[:4]}-{day[4:6]}-{day[6:8]} · 星期{WEEKDAYS[d.weekday()]} · 收盘后",
            "nStocks": len(stocks),
            "nSectors": len(ordered),
            "source": source,
            "flowK": in_k,
            "footNote": foot.format(d=f"{day[:4]}-{day[4:6]}-{day[6:8]}"),
        },
        "stats": [
            {"bar": "v", "k": "上榜个股", "v": len(stocks), "unit": "只", "s": note, "cls": "c-mid"},
            {"bar": "in", "k": f"{in_k}个股", "v": len(inflow), "unit": "只",
             "s": f"合计 {fmt_flow(tot_in)}", "cls": "c-up"},
            {"bar": "out", "k": f"{out_k}个股", "v": len(outflow), "unit": "只",
             "s": f"合计 {fmt_flow(tot_out)}", "cls": "c-down"},
            {"bar": "net", "k": ("龙虎榜整体" if em else "主力资金整体"),
             "v": round(net / 1e8, 2), "unit": "亿元",
             "s": (out_k if net < 0 else in_k), "cls": "c-down" if net < 0 else "c-up"},
        ],
        "sectors": sectors,
        "tips": build_tips(ordered, stocks, source),
    }


def write_page(day, stocks, source="同花顺 iFinD"):
    """依据模板生成数据页 HTML（内嵌 JSON），返回文件路径；source 用于来源徽标/口径说明"""
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "lhb_template.html"), encoding="utf-8") as f:
        tpl = f.read()
    html = tpl.replace("__LHB_DATA__", json.dumps(build_page_data(day, stocks, source), ensure_ascii=False))
    html = html.replace("__LHB_SOURCE__", source)
    in_k = "净买入" if source.startswith("东方财富") else "主力净流入"
    html = html.replace("__FLOW_SORT__", in_k).replace("__FLOW_HDR__", in_k)
    out = os.path.join(base, f"lhb_page_{day}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out


def render_images(day, page_html):
    """调用 puppeteer 把数据页渲染为两张长图，返回 (图1, 图2) 路径"""
    base = os.path.dirname(os.path.abspath(__file__))
    out1 = os.path.join(base, f"lhb_sector_flow_{day}.png")
    out2 = os.path.join(base, f"lhb_stock_detail_{day}.png")
    env = os.environ.copy()
    exe = _find_chrome()
    if exe:
        env.setdefault("PUPPETEER_EXECUTABLE_PATH", exe)
    r = subprocess.run(
        ["node", os.path.join(base, "render_lhb_panorama.js"), page_html, out1, out2],
        capture_output=True, text=True, env=env, timeout=300,
    )
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:500])
    return out1, out2


def main():
    """入口：python analyze_lhb.py [YYYYMMDD] [--source ifind|eastmoney]

    自动选择取数源：iFinD（默认，需 IFIND_AUTH_TOKEN）/ 东方财富公开接口。
    报告 | 数据页 | 长图生成后自动跑排版自检（lhb_qa），全过写 qa_YYYYMMDD.txt。
    """
    ap = argparse.ArgumentParser(description="龙虎榜个股·板块资金整合分析")
    ap.add_argument("day", nargs="?", default=None, help="YYYYMMDD，缺省为今天")
    ap.add_argument("--source", choices=("ifind", "eastmoney"), default="ifind",
                    help="数据源：ifind（默认）/ eastmoney")
    a = ap.parse_args()
    day = a.day or date.today().strftime("%Y%m%d")

    if a.source == "eastmoney":
        from lhb_eastmoney import fetch_lhb_stocks as em_fetch
        source_label = "东方财富"
        stocks = em_fetch(day)
    else:
        source_label = "同花顺 iFinD"
        stocks = fetch_lhb_list(day)
        if not stocks:
            print(f"{day} 龙虎榜名单为空：可能数据尚未发布，或问句解析失败")
            return 1
        stocks = fetch_flows(day, stocks)
        stocks = fetch_industries(day, stocks)

    if not stocks:
        print(f"{day} 龙虎榜名单为空（来源：{source_label}）")
        return 1

    report = build_report(day, stocks, source_label)
    base = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(base, f"lhb_report_{day}.md")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(report)
    print(f"\n已保存至 {out_file}")

    # 步骤6：生成数据页并渲染两张长图（板块资金分布 + 分板块个股明细）
    try:
        page_html = write_page(day, stocks, source_label)
        img1, img2 = render_images(day, page_html)
        print(f"长图已生成：\n  {img1}\n  {img2}")
    except Exception as e:
        print(f"长图渲染失败：{e}（Markdown 报告不受影响）")

    # 步骤7：排版自检（数据数学一致性 + 来源徽标 + 口径词 + 占位符），违规仅告警不阻断产物
    try:
        from lhb_qa import verify_lhb
        if verify_lhb(day, stocks, source=source_label):
            print(f"排版自检通过：数据自洽、来源「{source_label}」、无占位符残留 → qa_{day}.txt")
        else:
            print(f"[warn] 排版自检未通过：存在数学不一致 / 来源口径误标 / 占位符残留（qa_{day}.txt 未生成）")
    except Exception as e:
        print(f"[warn] 排版自检执行异常：{e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
