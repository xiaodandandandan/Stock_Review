# -*- coding: utf-8 -*-
"""
龙虎榜数据源：东方财富（无 iFinD 接口时的自动回退）

通过东财公开接口（无需令牌）抓取龙虎榜，归一化为与 analyze_lhb 同构的 stocks 结构：
    {
      "代码": "000620", "简称": "盈新发展", "上榜次数": 1,
      "涨跌幅": 9.93, "净流入": 423718411.12, "行业": "房地产"
    }

口径差异（相对 iFinD，均在 data["lhb_source"] 标注）：
  - "净流入" = 龙虎榜净买入额 BILLBOARD_NET_AMT（iFinD 为当日主力资金净流入）
  - "行业" = 东财一级行业（iFinD 为同花顺行业）

数据来源：
  1. datacenter-web.eastmoney.com 龙虎榜详情 RPT_DAILYBILLBOARD_DETAILSNEW（按交易日过滤）
  2. emweb F10 逐股查询东财一级行业（ssbk），失败回退"未分类"

依赖：requests（已锁定于 requirements.txt）
用法：
    from lhb_eastmoney import fetch_lhb_stocks
    stocks = fetch_lhb_stocks("20260908")
"""

import requests
from concurrent.futures import ThreadPoolExecutor

LHB_API = "https://datacenter-web.eastmoney.com/api/data/v1/get"
F10_API = "https://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/PageAjax"

_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://quote.eastmoney.com/",
}
_MAX_WORKERS = 8


def _get_json(url, params):
    r = requests.get(url, params=params, headers=_HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch_lhb_rows(day):
    """东财龙虎榜详情（日榜）原始行列表；接口异常抛出由调用方处理"""
    d = "%s-%s-%s" % (day[:4], day[4:6], day[6:8])
    rows, page = [], 1
    while True:
        data = _get_json(LHB_API, {
            "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
            "columns": "ALL",
            "filter": "(TRADE_DATE='%s')" % d,
            "pageNumber": page, "pageSize": 500,
            "sortTypes": "-1", "sortColumns": "BILLBOARD_NET_AMT",
            "source": "WEB", "client": "WEB",
        })
        res = data.get("result") or {}
        batch = res.get("data") or []
        rows += batch
        if len(batch) < 500 or page >= (res.get("pages") or 1):
            break
        page += 1
    return rows


def rows_to_stocks(rows):
    """东财原始行 → stocks 字典（按代码去重，首个记录为准）"""
    stocks = {}
    for r in rows:
        code = r.get("SECURITY_CODE")
        if not code or code in stocks:
            continue
        raw_chg, raw_flow = r.get("CHANGE_RATE"), r.get("BILLBOARD_NET_AMT")
        if raw_chg is None:
            chg = None                                # 缺失如实标注，不编造 0
        else:
            try:
                chg = round(float(raw_chg), 2)
            except (TypeError, ValueError):
                chg = None
        if raw_flow is None:
            flow = None
        else:
            try:
                flow = float(raw_flow)
            except (TypeError, ValueError):
                flow = None
        stocks[code] = {
            "代码": code,
            "简称": r.get("SECURITY_NAME_ABBR") or code,
            "上榜次数": 1,                  # 东财日榜每股记 1 次上榜
            "涨跌幅": chg,
            "净流入": flow,
            "行业": "未分类",
        }
    return stocks


def fetch_industry(code):
    """东财 F10 一级行业（东财口径，如'房地产'），失败返回 ''（调用方回退未分类）"""
    if code.startswith(("4", "8", "920")):       # 北交所：4/8 老段 + 920 新段
        secu = "BJ" + code
    elif code.startswith(("0", "3")):
        secu = "SZ" + code
    else:
        secu = "SH" + code
    try:
        data = _get_json(F10_API, {"code": secu})
        for b in (data.get("ssbk") or [])[:3]:
            name = b.get("BOARD_NAME")
            if name:
                return name
    except Exception:
        pass
    return ""


def fetch_lhb_stocks(day):
    """组装与 analyze_lhb 同构的 stocks 字典（含行业）"""
    stocks = rows_to_stocks(fetch_lhb_rows(day))
    codes = list(stocks)
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as ex:
        for code, ind in zip(codes, ex.map(fetch_industry, codes)):
            if ind:
                stocks[code]["行业"] = ind
    return stocks