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

依赖：pip install requests
认证：export IFIND_AUTH_TOKEN=<同花顺MCP密钥>
用法：python analyze_lhb.py [YYYYMMDD]（默认今天）

注：search_stocks 为自然语言取数，偶发解析失败时返回空表，
    可微调问句表达后重试；涨跌幅为前复权口径，资金单位为元。
"""

import json
import os
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


def build_report(day, stocks):
    """步骤4-5：按一级行业聚合，生成 Markdown 报告"""
    sectors = {}
    for s in stocks.values():
        top = s["行业"].split("-")[0]
        sectors.setdefault(top, []).append(s)
    # 板块内按主力净流入降序；板块间按净流入合计降序
    for lst in sectors.values():
        lst.sort(key=lambda x: (x["净流入"] is None, -(x["净流入"] or 0)))
    ordered = sorted(
        sectors.items(),
        key=lambda kv: sum(x["净流入"] or 0 for x in kv[1]),
        reverse=True,
    )

    inflow = [s for s in stocks.values() if (s["净流入"] or 0) > 0]
    outflow = [s for s in stocks.values() if (s["净流入"] or 0) < 0]
    tot_in = sum(s["净流入"] for s in inflow)
    tot_out = sum(s["净流入"] for s in outflow)

    lines = [
        f"# 龙虎榜个股按板块整合（{cn_date(day)}）",
        "",
        f"共 **{len(stocks)}** 只个股上榜。净流入 **{len(inflow)}** 只，合计 "
        f"**{fmt_flow(tot_in)}**；净流出 **{len(outflow)}** 只，合计 "
        f"**{fmt_flow(tot_out)}**；主力资金整体 **{fmt_flow(tot_in + tot_out)}**。",
        "",
        "## 板块汇总（按主力净流入排序）",
        "",
        "| 板块（同花顺一级） | 上榜数 | 主力净流入合计 |",
        "|---|---|---|",
    ]
    for name, lst in ordered:
        total = sum(x["净流入"] or 0 for x in lst)
        lines.append(f"| {name} | {len(lst)} | {fmt_flow(total)} |")

    lines += ["", "## 个股明细（按板块分组，组内按主力净流入排序）", "",
              "| 板块 | 细分板块 | 代码 | 简称 | 当日涨跌幅 | 主力净流入 |",
              "|---|---|---|---|---|---|"]
    for name, lst in ordered:
        for s in lst:
            chg = "暂无数据" if s["涨跌幅"] is None else f"{s['涨跌幅']:+.2f}%"
            lines.append(
                f"| {name} | {s['行业']} | {s['代码']} | {s['简称']}"
                f"{'（' + str(s['上榜次数']) + '次上榜）' if s['上榜次数'] > 1 else ''}"
                f" | {chg} | {fmt_flow(s['净流入'])} |"
            )

    lines += [
        "",
        "---",
        "口径说明：涨跌幅为前复权口径；主力资金净流入额（正=流入，负=流出）；",
        "数据为当日收盘后维度。数据来源：同花顺 iFinD。",
        "以上内容基于公开数据，不构成投资建议。",
    ]
    return "\n".join(lines)


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else date.today().strftime("%Y%m%d")
    stocks = fetch_lhb_list(day)
    if not stocks:
        print(f"{day} 龙虎榜名单为空：可能数据尚未发布，或问句解析失败")
        return 1
    stocks = fetch_flows(day, stocks)
    stocks = fetch_industries(day, stocks)
    report = build_report(day, stocks)
    out_file = f"lhb_report_{day}.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(report)
    print(f"\n已保存至 {out_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
