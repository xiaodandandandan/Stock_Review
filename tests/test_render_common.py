# -*- coding: utf-8 -*-
"""render_common 纯逻辑函数回归测试（解析 / 聚合 / 空数据防御 / 文案生成）。
不依赖字体与出图，适合无字体环境（CI / 新机器）运行。
"""
import json
import os
import sys

import pytest

FD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(FD)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import render_common as rc  # noqa: E402

# ---------------- 数据加载 ----------------

def test_load_data_prefers_path(tmp_path):
    p1 = tmp_path / "a.json"
    p2 = tmp_path / "b.json"
    p1.write_text('{"day": "20260901", "x": 1}', encoding="utf-8")
    p2.write_text('{"day": "20260902", "x": 2}', encoding="utf-8")
    data = rc.load_data(day=None, path=str(p1), base=str(tmp_path))
    assert data["x"] == 1
    # day 匹配 data_{day}.json
    (tmp_path / "data_20260902.json").write_text('{"day": "20260902", "x": 2}', encoding="utf-8")
    data = rc.load_data(day="20260902", path=None, base=str(tmp_path))
    assert data["x"] == 2


def test_load_data_infers_day_from_filename(tmp_path):
    # JSON 缺 day 字段时从文件名 data_YYYYMMDD.json 推断
    (tmp_path / "data_20260915.json").write_text('{"x": 3}', encoding="utf-8")
    data = rc.load_data(day=None, path=str(tmp_path / "data_20260915.json"), base=str(tmp_path))
    assert data["day"] == "20260915"


def test_data_day_missing_raises():
    with pytest.raises(ValueError):
        rc.data_day({})
    # 显式 fallback 仍可用（调用方主动指定时）
    assert rc.data_day({}, fallback="20260908") == "20260908"


def test_load_data_missing_returns_none(tmp_path):
    assert rc.load_data(day="20990101", path=None, base=str(tmp_path)) is None
    assert rc.load_data(day=None, path="/no/such.json", base=str(tmp_path)) is None


# ---------------- 日期 / 格式化 ----------------

def test_date_helpers():
    assert rc.data_day({"day": "20260908"}) == "20260908"
    assert rc.data_day({}, fallback="20260908") == "20260908"
    assert rc.date_label("20260908") == "2026.09.08 收盘"
    assert rc.short_date("20260908") == "09.08"


def test_fmt_yi():
    assert rc.fmt_yi(5.68e8) == "+5.68亿"
    assert rc.fmt_yi(-3.01e8) == "-3.01亿"
    assert rc.fmt_yi_short(2.32e8) == "+2.32"


# ---------------- 龙虎榜板块聚合 ----------------

def test_lhb_sector_flow_agg_and_sort():
    rows = [
        ["600001", "A股", 1, 9.9, 49.23e8, "电子-半导体"],
        ["600002", "B股", 1, 5.0, 10.97e8, "通信-设备"],
        ["600003", "C股", 1, 3.0, -4.7e8, "电子-消费电子"],
        ["600004", "D股", 2, 1.0, None, None],          # None 金额与行业 → 未分类
    ]
    sf = rc.lhb_sector_flow(rows)
    # 金额降序：电子(44.53) > 通信(10.97) > 未分类(0.0)
    assert [s for s, _, _ in sf] == ["电子", "通信", "未分类"]
    e_total = dict((s, t) for s, t, _ in sf)["电子"]
    assert abs(e_total - (49.23 - 4.7) * 1e8) < 1
    assert rc.lhb_sector_flow([]) == []


def test_lhb_cards_split():
    sf = [("电子", 44.53e8, [("A", 44.53e8)]), ("通信", -3.01e8, [("B", -3.01e8)])]
    buy, sell = rc.lhb_cards(sf)
    assert buy[0][0] == "电子"
    assert sell[0][0] == "通信"


def test_build_lhb_insights_empty():
    assert len(rc.build_lhb_insights([], [])) == 4
    assert "无" in rc.build_lhb_insights([], [])[0]


def test_build_lhb_meta_basic():
    rows = [["600001", "A股", 1, 9.9, 49.23e8, "电子-半导体"]]
    sf = rc.lhb_sector_flow(rows)
    head, sub = rc.build_lhb_meta(sf, rows)
    assert "电子" in head
    assert "1只上榜" in sub
    assert rc.build_lhb_meta([], []) == ("龙虎榜 · 板块分析", "0只上榜")


# ---------------- 涨跌停 / 连板 ----------------

def test_limit_industry_counts_topn_rest():
    rows = [[f"6000{i}", f"股{i}", 10.0, f"细分{i}", f"行{i}"] for i in range(15)]
    out = rc.limit_industry_counts(rows, top_n=3)
    assert len(out) == 4                       # 3 个一级行业 + 1 个"其他行业"
    assert out[-1][0] == "其他行业"
    assert out[-1][1] == 12                    # 15 - 3


def test_limit_industry_counts_empty():
    assert rc.limit_industry_counts([]) == []


def test_build_ladders_tiers_and_empty():
    streaks = [["600001", "甲", 4, "x"], ["600002", "乙", 2, "y"], ["600003", "丙", 2, "z"]]
    lads = rc.build_ladders(streaks)
    assert lads[0][0] == "4板"
    assert lads[0][1] == ["甲"]
    # 空数据 → 占位
    lads = rc.build_ladders([])
    assert lads[0][0] == "2板"
    assert lads[0][1] == ["—"]


def test_build_downlist_sorted_and_label():
    heavy = [["600001", "甲", -9.5, "电子-半导体"], ["600002", "乙", -7.0, "化工"]]
    dn = [["600001", "甲", -9.5, "电子-半导体"]]
    rows = rc.build_downlist(heavy, dn)
    assert rows[0][0] == "甲"                  # 跌幅更深在前
    assert rows[0][3] == "收盘跌停"
    assert rows[1][3] == "跌幅超9%"


def test_limit_summary():
    head, sub = rc.limit_summary([], [], [], [])
    assert "0涨停" in head


def test_build_limit_signals_empty():
    sigs = rc.build_limit_signals([], [], [], [])
    assert len(sigs) == 5
    assert "0只涨停" in sigs[0]


# ---------------- 全市场资金流 ----------------

def test_build_flow_insights():
    data = [("基础化工", 44.18, ""), ("电子", -19.48, "")]
    ins = rc.build_flow_insights(data)
    assert "44.2" in ins[0]                   # 文案精度 %.1f
    assert len(ins) == 4
    ins = rc.build_flow_insights([])
    assert len(ins) == 4
    ins = rc.build_flow_insights([("电子", -1.0, "")])
    assert "流出" in ins[3]


# ---------------- 两日对比 ----------------

def test_sector_totals():
    data = {"lhb_stocks": [
        ["600001", "A", 1, 9.9, 49.23e8, "电子-半导体"],
        ["600002", "B", 1, 2.0, -3.01e8, "电子-消费电子"],
    ]}
    d = rc.sector_totals(data)
    assert abs(d["电子"] - (49.23 - 3.01)) < 1e-6
    assert rc.sector_totals({}) == {}
    assert rc.sector_totals({"lhb_stocks": []}) == {}


def test_compare_meta():
    d7 = {"电子": 49.23}
    d8 = {"化工": 5.68}
    head, sub = rc.compare_meta(d7, d8)
    assert "电子退潮" in head and "化工接力" in head
    assert "亿" in sub


def test_build_compare_insights():
    d7 = {"电子": 49.23, "通信": 10.97, "汽车": -0.16}
    d8 = {"电子": 4.14, "通信": 0.26, "化工": 5.68, "汽车": -0.10}
    ins = rc.build_compare_insights(d7, d8)
    assert len(ins) == 5
    assert "电子" in ins[1]                    # 榜首
    assert "化工" in ins[2]                    # 环比增量最大
    assert rc.build_compare_insights({}, {}) == ["两日均无板块数据。"] * 5
    # 仅当日有数据不抛异常
    assert len(rc.build_compare_insights({}, {"电子": 1.0})) == 5


# ---------------- 渲染脚本导入冒烟（不含绘图执行） ----------------

def test_compare_script_importable():
    import render_lhb_compare
    assert hasattr(render_lhb_compare, "DEMO")
    assert hasattr(render_lhb_compare, "main")