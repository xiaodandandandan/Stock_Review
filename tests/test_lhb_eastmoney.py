# -*- coding: utf-8 -*-
"""龙虎榜数据源回退相关测试：东财行解析 + run_pipeline 源选择（不触网，全 mock）"""
import os
import sys

import pytest

FD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(FD)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import lhb_eastmoney  # noqa: E402
import run_pipeline as rp  # noqa: E402


# ---------------- 东财行解析（纯函数） ----------------

def test_rows_to_stocks_basic():
    rows = [
        {"SECURITY_CODE": "000620", "SECURITY_NAME_ABBR": "盈新发展",
         "CHANGE_RATE": 9.9338, "BILLBOARD_NET_AMT": 423718411.12,
         "EXPLAIN": "日涨幅偏离值7%"},
        {"SECURITY_CODE": "002579", "SECURITY_NAME_ABBR": "中京电子",
         "CHANGE_RATE": 9.9936, "BILLBOARD_NET_AMT": 354246855.83,
         "EXPLAIN": "连续三日涨幅偏离20%"},
    ]
    s = lhb_eastmoney.rows_to_stocks(rows)
    assert set(s) == {"000620", "002579"}
    assert s["000620"]["简称"] == "盈新发展"
    assert s["000620"]["涨跌幅"] == 9.93          # 四舍五入保留两位
    assert s["000620"]["净流入"] == 423718411.12   # 净买入额（元）
    assert s["000620"]["上榜次数"] == 1
    assert s["000620"]["行业"] == "未分类"


def test_rows_to_stocks_dedup():
    """同一股票多条上榜记录（多原因）→ 仅保留一条"""
    rows = [
        {"SECURITY_CODE": "000620", "SECURITY_NAME_ABBR": "盈新发展",
         "CHANGE_RATE": 9.9, "BILLBOARD_NET_AMT": 1e8},
        {"SECURITY_CODE": "000620", "SECURITY_NAME_ABBR": "盈新发展",
         "CHANGE_RATE": 9.9, "BILLBOARD_NET_AMT": 1.5e8},   # 应被忽略
    ]
    s = lhb_eastmoney.rows_to_stocks(rows)
    assert len(s) == 1
    assert s["000620"]["净流入"] == 1e8            # 首个记录为准


def test_rows_to_stocks_bad_values():
    rows = [
        {"SECURITY_CODE": "000001", "SECURITY_NAME_ABBR": "平安银行", "CHANGE_RATE": None, "BILLBOARD_NET_AMT": None},
        {"SECURITY_CODE": "300001", "SECURITY_NAME_ABBR": "特锐德", "CHANGE_RATE": "abc", "BILLBOARD_NET_AMT": "x"},
    ]
    s = lhb_eastmoney.rows_to_stocks(rows)
    assert s["000001"]["涨跌幅"] is None and s["000001"]["净流入"] is None
    assert s["300001"]["涨跌幅"] is None and s["300001"]["净流入"] is None


def test_rows_to_stocks_empty():
    assert lhb_eastmoney.rows_to_stocks([]) == {}


# ---------------- fetch_lhb_rows 分页（mock _get_json，不触网） ----------------

def test_fetch_lhb_rows_single_page(monkeypatch):
    rows = [{"SECURITY_CODE": "000620"}, {"SECURITY_CODE": "002579"}]
    seen = {}

    def fake_get(url, params):
        seen["params"] = params
        return {"result": {"data": rows, "pages": 1}}

    monkeypatch.setattr(lhb_eastmoney, "_get_json", fake_get)
    out = lhb_eastmoney.fetch_lhb_rows("20260908")
    assert out == rows
    # 交易日被转为 YYYY-MM-DD 过滤，且首屏 500 条
    assert seen["params"]["filter"] == "(TRADE_DATE='2026-09-08')"
    assert seen["params"]["pageNumber"] == 1 and seen["params"]["pageSize"] == 500


def test_fetch_lhb_rows_paginates(monkeypatch):
    """满页 500 条时继续翻页，直到不足一页为止"""
    page1 = [{"SECURITY_CODE": "000%03d" % i} for i in range(500)]
    page2 = [{"SECURITY_CODE": "600000"}]
    calls = []

    def fake_get(url, params):
        calls.append(params)
        if params["pageNumber"] == 1:
            return {"result": {"data": page1, "pages": 2}}
        return {"result": {"data": page2, "pages": 2}}

    monkeypatch.setattr(lhb_eastmoney, "_get_json", fake_get)
    out = lhb_eastmoney.fetch_lhb_rows("20260908")
    assert len(out) == 501
    assert [c["pageNumber"] for c in calls] == [1, 2]


def test_fetch_lhb_rows_empty_result(monkeypatch):
    """接口无 result（如无榜单）→ 空列表，不抛异常"""
    monkeypatch.setattr(lhb_eastmoney, "_get_json", lambda url, params: {})
    assert lhb_eastmoney.fetch_lhb_rows("20260908") == []


# ---------------- fetch_industry 行业映射（mock _get_json，不触网） ----------------

def _industry_code(monkeypatch, code, payload):
    seen = {}

    def fake_get(url, params):
        seen["url"] = url
        seen["secu"] = params["code"]
        return payload

    monkeypatch.setattr(lhb_eastmoney, "_get_json", fake_get)
    return lhb_eastmoney.fetch_industry(code), seen


def test_fetch_industry_prefix_mapping(monkeypatch):
    """代码前缀 → 市场代码：0/3→SZ，4/8→BJ，其余→SH"""
    for code, secu in [("000001", "SZ000001"), ("300001", "SZ300001"),
                       ("600000", "SH600000"), ("830001", "BJ830001")]:
        ind, seen = _industry_code(monkeypatch, code, {"ssbk": [{"BOARD_NAME": "银行"}]})
        assert seen["secu"] == secu
        assert ind == "银行"


def test_fetch_industry_first_nonempty_board(monkeypatch):
    """ssbk 中跳过空名称，取第一个非空行业"""
    ind, seen = _industry_code(monkeypatch, "000001",
                               {"ssbk": [{"BOARD_NAME": ""}, {"BOARD_NAME": "银行"}]})
    assert ind == "银行"


def test_fetch_industry_missing_falls_back(monkeypatch):
    """无 ssbk / 接口异常 → 返回 ''（由调用方回退未分类）"""
    ind, _ = _industry_code(monkeypatch, "000001", {})
    assert ind == ""

    def boom(*a, **k):
        raise RuntimeError("timeout")
    monkeypatch.setattr(lhb_eastmoney, "_get_json", boom)
    assert lhb_eastmoney.fetch_industry("000001") == ""


# ---------------- fetch_lhb_stocks 组装 ----------------

def test_fetch_lhb_stocks_assembles(monkeypatch):
    rows = [
        {"SECURITY_CODE": "000620", "SECURITY_NAME_ABBR": "盈新发展",
         "CHANGE_RATE": 9.93, "BILLBOARD_NET_AMT": 1e8},
        {"SECURITY_CODE": "600000", "SECURITY_NAME_ABBR": "浦发银行",
         "CHANGE_RATE": 1.2, "BILLBOARD_NET_AMT": None},
    ]
    monkeypatch.setattr(lhb_eastmoney, "fetch_lhb_rows", lambda day: rows)
    monkeypatch.setattr(lhb_eastmoney, "fetch_industry",
                        lambda code: "银行" if code == "600000" else "")  # 600000 有行业，000620 保留未分类
    stocks = lhb_eastmoney.fetch_lhb_stocks("20260908")
    assert stocks["000620"]["行业"] == "未分类"
    assert stocks["600000"]["行业"] == "银行"
    assert stocks["600000"]["净流入"] is None     # 缺失如实标注


# ---------------- 回退链路健壮性 ----------------

def test_lhb_fallback_propagates_eastmoney_error(monkeypatch):
    """iFinD 失败且东财也异常 → 异常向上传播，不静默产出空榜单"""
    monkeypatch.setattr(rp, "fetch_lhb_list", lambda day: {})
    def boom(*a, **k):
        raise RuntimeError("东财接口无响应")
    monkeypatch.setattr(lhb_eastmoney, "fetch_lhb_stocks", boom)
    with pytest.raises(RuntimeError, match="东财接口无响应"):
        rp.fetch_lhb_stocks("20260908")


# ---------------- run_pipeline 源选择（mock，不触网） ----------------

def test_lhb_fallback_on_ifind_failure(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("请先设置环境变量 IFIND_AUTH_TOKEN")

    fake = {"000620": {"代码": "000620", "简称": "盈新发展", "行业": "房地产"}}
    monkeypatch.setattr(rp, "fetch_lhb_list", boom)
    monkeypatch.setattr(lhb_eastmoney, "fetch_lhb_stocks", lambda day: dict(fake))
    stocks, source = rp.fetch_lhb_stocks("20260908")
    assert source == "eastmoney"
    assert stocks == fake


def test_lhb_fallback_on_empty_list(monkeypatch):
    """iFinD 返回空名单也应切东财（如当日榜单未发布/问句解析失败）"""
    monkeypatch.setattr(rp, "fetch_lhb_list", lambda day: {})
    monkeypatch.setattr(lhb_eastmoney, "fetch_lhb_stocks", lambda day: {"000620": {}})
    stocks, source = rp.fetch_lhb_stocks("20260908")
    assert source == "eastmoney"
    assert "000620" in stocks


def test_lhb_keeps_ifind_when_ok(monkeypatch):
    s0 = {"000620": {"代码": "000620", "简称": "盈新发展"}}
    monkeypatch.setattr(rp, "fetch_lhb_list", lambda day: dict(s0))
    monkeypatch.setattr(rp, "fetch_flows", lambda day, s: s)
    monkeypatch.setattr(rp, "fetch_industries", lambda day, s: s)
    stocks, source = rp.fetch_lhb_stocks("20260908")
    assert source == "iFinD"
    assert "000620" in stocks


def test_build_data_marks_source(monkeypatch):
    monkeypatch.setattr(rp, "fetch_lhb_list", lambda day: {})          # 空 → 回退
    monkeypatch.setattr(lhb_eastmoney, "fetch_lhb_stocks",
                        lambda day: {"000620": {"代码": "000620", "简称": "盈新发展",
                                                "上榜次数": 1, "涨跌幅": 9.93,
                                                "净流入": 4.2e8, "行业": "房地产"}})
    monkeypatch.setattr(rp, "fetch_limit_up", lambda day: [])
    monkeypatch.setattr(rp, "fetch_limit_down", lambda day: [])
    monkeypatch.setattr(rp, "fetch_heavy_fall", lambda day: [])
    monkeypatch.setattr(rp, "fetch_streaks", lambda day: [])
    data = rp.build_data("20260908")
    assert data["lhb_source"] == "eastmoney"
    assert data["lhb_stocks"][0] == ["000620", "盈新发展", 1, 9.93, 420000000, "房地产"]