# -*- coding: utf-8 -*-
"""
每日复盘数据组装层（流水线入口）

从同花顺 iFinD 实时取数，组装成 build_summary_page 所需的数据结构并生成复盘总览 HTML：
  1. 龙虎榜（优先 iFinD，无令牌/接口异常时自动回退东方财富公开接口，data 标注 lhb_source）
  2. 收盘涨停 / 收盘跌停 / 重挫（跌幅 ≤ -9%，含跌停）
  3. 连续涨停（连板梯队）

用法：
    python run_pipeline.py [YYYYMMDD] [--embed]
      --embed    图片 base64 内嵌，产出单文件自包含 HTML（手机分享推荐）
      --lhb-*    长图路径参数（配合 analyze_lhb.py 生成的日期化图片）

认证：export IFIND_AUTH_TOKEN=<同花顺MCP密钥>；未设置时龙虎榜走东方财富，涨跌停等 iFinD 指标为空表。
"""

import argparse
import json
import os
from datetime import date

from analyze_lhb import (
    call_tool, parse_md_table, _col, cn_date,
    fetch_lhb_list, fetch_flows, fetch_industries,
)
from build_index_html import build_summary_page


def _split_industry(full):
    """'电子-半导体-半导体材料' → (一级, 二级+三级)；容错返回 '未分类'"""
    parts = [p.strip() for p in (full or "").split("-") if p.strip()]
    l1 = parts[0] if parts else "未分类"
    sub = "-".join(parts[1:]) if len(parts) > 1 else l1
    return l1, sub


def _rows(tool, query):
    """调用 iFinD 工具并解析为行列表；解析失败返回空表（不中断流水线）"""
    try:
        return parse_md_table(call_tool(tool, query))
    except Exception as e:
        print(f"[warn] {tool} 取数失败：{e}")
        return []


def _industry(r):
    """行业列取值（排除排名类干扰列）：iFinD 返回的行业列名不稳定
    （所属同花顺行业 / 所属同花顺三级行业 / 行业简称），按值优先：
    先取含 '-' 的完整三级行业，否则取第一个非空行业名。"""
    vals = [str(v).strip() for k, v in r.items()
            if "行业" in k and "排名" not in k and str(v).strip()]
    if not vals:
        return ""
    for v in vals:
        if "-" in v:
            return v
    return vals[0]


def fetch_limit_up(day):
    """收盘涨停列表：[[code, name, chg, sub_industry, level1], ...]
    问句注意：勿加'一字板'等关键词，否则 iFinD 引擎会解析出错（实测返回异常名单）。"""
    rows = _rows("search_stocks",
                 f"{cn_date(day)}收盘涨停的股票（含ST），"
                 f"显示{cn_date(day)}的收盘涨跌幅、所属同花顺行业的一级二级三级行业，按涨跌幅降序")
    out = []
    for r in rows:
        code, name = _col(r, "股票代码"), _col(r, "股票简称")
        if not code or not name:
            continue
        try:
            chg = float(_col(r, "涨跌幅"))
        except (TypeError, ValueError):
            chg = 0.0
        l1, sub = _split_industry(_industry(r))
        out.append([code, name, chg, sub, l1])
    print(f"  涨停 {len(out)} 只")
    return out


def fetch_limit_down(day):
    """收盘跌停列表：[[code, name, chg, industry], ...]
    注意：勿加'（含ST）'等后缀，否则引擎解析会丢失名单（实测返回 0 行）。"""
    rows = _rows("search_stocks",
                 f"{cn_date(day)}收盘跌停的股票，"
                 f"显示{cn_date(day)}的收盘涨跌幅、所属同花顺行业，按跌幅降序")
    out = []
    for r in rows:
        code, name = _col(r, "股票代码"), _col(r, "股票简称")
        if not code or not name:
            continue
        try:
            chg = float(_col(r, "涨跌幅"))
        except (TypeError, ValueError):
            chg = 0.0
        out.append([code, name, chg, _industry(r) or "未分类"])
    print(f"  跌停 {len(out)} 只")
    return out


def fetch_heavy_fall(day):
    """重挫（跌幅 ≤ -9%，含跌停）：[[code, name, chg, industry], ...]"""
    rows = _rows("search_stocks",
                 f"{cn_date(day)}跌幅达到9%及以上的股票（含跌停），"
                 f"显示{cn_date(day)}的收盘涨跌幅、所属同花顺行业，按跌幅升序")
    out = []
    for r in rows:
        code, name = _col(r, "股票代码"), _col(r, "股票简称")
        if not code or not name:
            continue
        try:
            chg = float(_col(r, "涨跌幅"))
        except (TypeError, ValueError):
            chg = 0.0
        if chg > -9.0:                      # 口径保护：只保留跌幅 ≤ -9%
            continue
        out.append([code, name, chg, _industry(r) or "未分类"])
    print(f"  重挫(≤-9%) {len(out)} 只")
    return out


def fetch_streaks(day):
    """连板梯队：[[code, name, days, sub], ...]，按天数降序"""
    rows = _rows("search_stocks",
                 f"{cn_date(day)}连续涨停天数达到2天及以上的股票，"
                 f"显示连续涨停天数、所属概念，按连续涨停天数降序")
    out = []
    for r in rows:
        code, name = _col(r, "股票代码"), _col(r, "股票简称")
        if not code or not name:
            continue
        try:
            days = int(str(_col(r, "涨停天数")).replace("天", "").strip())
        except (TypeError, ValueError):
            continue                          # 非连板股跳过
        if days < 2:
            continue
        sub = _col(r, "概念") or _col(r, "所属同花顺行业") or "未分类"
        out.append([code, name, days, sub])
    out.sort(key=lambda x: -x[2])
    print(f"  连板 {len(out)} 只")
    return out


def fetch_lhb_stocks(day):
    """龙虎榜取数：优先 iFinD，不可用（无令牌/接口异常/名单为空）时自动回退东方财富。

    返回 (stocks, source)，source ∈ {'iFinD', 'eastmoney'}，供产物标注数据来源。
    """
    try:
        stocks = fetch_lhb_list(day)
        if not stocks:
            print("[warn] iFinD 龙虎榜名单为空，切换东方财富数据源")
        else:
            stocks = fetch_flows(day, stocks)
            stocks = fetch_industries(day, stocks)
            print(f"  龙虎榜 {len(stocks)} 只（iFinD）")
            return stocks, "iFinD"
    except Exception as e:
        print(f"[warn] iFinD 龙虎榜取数失败（{e}），切换东方财富数据源")

    from lhb_eastmoney import fetch_lhb_stocks as em_fetch
    stocks = em_fetch(day)
    print(f"  龙虎榜 {len(stocks)} 只（东方财富）")
    return stocks, "eastmoney"


def build_data(day):
    """组装 build_summary_page 所需的完整 data 字典"""
    print(f"取数日期：{cn_date(day)}")

    # 1. 龙虎榜（iFinD 优先，自动回退东方财富）
    stocks, lhb_source = fetch_lhb_stocks(day)
    lhb_stocks = [
        [s["代码"], s["简称"], s.get("上榜次数", 1),
         round(s["涨跌幅"] or 0.0, 2), round(s["净流入"] or 0.0), s["行业"]]
        for s in stocks.values()
    ]

    # 2. 涨跌停 / 重挫 / 连板
    data = {
        "day": day,
        "date_cn": cn_date(day),
        "lhb_stocks": lhb_stocks,
        "lhb_source": lhb_source,
        "limit_up": fetch_limit_up(day),
        "limit_down": fetch_limit_down(day),
        "heavy_fall": fetch_heavy_fall(day),
        "streaks": fetch_streaks(day),
    }
    return data


def main():
    ap = argparse.ArgumentParser(description="每日复盘数据组装：iFinD 取数 → data.json → 总览 HTML")
    ap.add_argument("day", nargs="?", default=None, help="YYYYMMDD，缺省为今天")
    ap.add_argument("--out", default=None, help="输出 HTML 路径，缺省 index_YYYYMMDD.html")
    args = ap.parse_args()

    day = args.day or date.today().strftime("%Y%m%d")
    if not (len(day) == 8 and day.isdigit()):
        ap.error("日期格式应为 YYYYMMDD，例如 20260908")

    data = build_data(day)

    base = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base, f"data_{day}.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已保存数据：{data_path}")

    out_path = args.out or os.path.join(base, f"index_{day}.html")
    build_summary_page(data, out_path=out_path)

    # 空数据提示（页面仍可生成，避免静默产出残缺内容）
    if not data["lhb_stocks"]:
        print("[warn] 龙虎榜数据为空：可能当日榜单未发布或 iFinD 问句解析失败")
    if not data["limit_up"]:
        print("[warn] 涨停数据为空")


if __name__ == "__main__":
    main()