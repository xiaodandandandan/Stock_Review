# -*- coding: utf-8 -*-
"""lhb_qa 自检模块与 build_tips 符号方向测试（纯内存构造，不触网）"""
import analyze_lhb as al
import lhb_qa as qa


def _mk(code, flow=None, ind="电子", chg=5.0, name=None):
    return {code: {"代码": code, "简称": name or f"股{code}", "上榜次数": 1,
                   "涨跌幅": chg, "净流入": flow, "行业": ind}}


def _stocks_ok():
    stocks = _mk("000001", 1e8, "电子", 5.0)
    stocks.update(_mk("600001", -5e7, "农林", 3.0))
    stocks.update(_mk("830101", None, "医药", -2.0))   # 流量缺失（字段仍齐全）
    return stocks


EM_TEXT = "# 龙虎榜 净买入 净卖出 龙虎榜净买入额 东财一级 东方财富行业分类 东方财富\n"
IFIND_TEXT = "# 主力净流入 同花顺一级 同花顺行业分类 同花顺 iFinD\n"


# ---------------- run_qa 主体 ----------------

def test_run_qa_all_pass():
    r = qa.run_qa(_stocks_ok(), EM_TEXT, EM_TEXT, "东方财富")
    assert all(x["ok"] for x in r), [x for x in r if not x["ok"]]


def test_run_qa_ifind_pass():
    r = qa.run_qa(_stocks_ok(), IFIND_TEXT, IFIND_TEXT, "同花顺 iFinD")
    assert all(x["ok"] for x in r), [x for x in r if not x["ok"]]


def test_run_qa_missing_field_fails():
    stocks = _mk("000001", None)
    del stocks["000001"]["行业"]
    r = {x["name"]: x for x in qa.run_qa(stocks, EM_TEXT, EM_TEXT, "东方财富")}
    assert not r["stocks-字段完整"]["ok"]


def test_run_qa_count_balance_records():
    """计数平衡（买入+卖出+无数据=总数）通过，且明细写入 detail"""
    stocks = _mk("000001", None)
    r = {x["name"]: x for x in qa.run_qa(stocks, EM_TEXT, EM_TEXT, "东方财富")}
    c = r["stocks-计数平衡"]
    assert c["ok"] and "净买入 0 + 净卖出 0 + 无数据 1 = 总数 1" in c["detail"]


def test_run_qa_uncat_threshold():
    stocks = _mk("000001", None, "未分类")
    assert not {x["name"]: x for x in qa.run_qa(stocks, EM_TEXT, EM_TEXT, "东方财富")}["stocks-行业未分类"]["ok"]
    assert {x["name"]: x for x in qa.run_qa(stocks, EM_TEXT, EM_TEXT, "东方财富", max_uncat=1)}["stocks-行业未分类"]["ok"]


def test_run_qa_badge_mismatch_fails():
    """东财数据 + iFinD 徽标文案 → 来源徽标违规"""
    r = {x["name"]: x for x in qa.run_qa(_stocks_ok(), IFIND_TEXT, IFIND_TEXT, "东方财富")}
    assert not r["数据页-来源徽标"]["ok"] and not r["报告-来源徽标"]["ok"]


def test_run_qa_placeholder_leftover_fails():
    """最终模板 4 个占位符任一残留都应被检出（__LHB_SOURCE__/__LHB_DATA__/__FLOW_SORT__/__FLOW_HDR__）"""
    for bad in ("__LHB_SOURCE__ 东方财富 净买入",
                "__LHB_DATA__ 东方财富 净买入",
                "__FLOW_SORT__ 东方财富 净买入",
                "__FLOW_HDR__ 东方财富 净买入"):
        r = {x["name"]: x for x in qa.run_qa(_stocks_ok(), bad, bad, "东方财富")}
        assert not r["报告-占位符残留"]["ok"], f"未检出残留占位符: {bad}"


def test_run_qa_cross_source_word_fails():
    """东财数据中出现 iFinD 专属口径词（如 主力净流入）→ 口径词违规"""
    bad = EM_TEXT.replace("净买入", "主力净流入")
    r = {x["name"]: x for x in qa.run_qa(_stocks_ok(), bad, bad, "东方财富")}
    assert not r["产物-口径词"]["ok"]


# ---------------- verify_lhb 一站式 ----------------

def test_verify_lhb_ok_writes_qa_file(tmp_path):
    day = "20260910"
    md = tmp_path / f"lhb_report_{day}.md"
    page = tmp_path / f"lhb_page_{day}.html"
    md.write_text(EM_TEXT, encoding="utf-8")
    page.write_text(EM_TEXT, encoding="utf-8")
    ok = qa.verify_lhb(day, _stocks_ok(), "东方财富",
                       md_path=str(md), page_path=str(page), out_dir=str(tmp_path))
    assert ok
    assert (tmp_path / f"qa_{day}.txt").exists()


def test_verify_lhb_fail_without_qa_file(tmp_path):
    day = "20260910"
    md = tmp_path / "md.md"
    page = tmp_path / "page.html"
    md.write_text("同花顺 iFinD\n", encoding="utf-8")   # 东财数据误标 iFinD
    page.write_text("同花顺 iFinD\n", encoding="utf-8")
    assert not qa.verify_lhb(day, _stocks_ok(), "东方财富", md_path=str(md), page_path=str(page))
    assert not (tmp_path / f"qa_{day}.txt").exists()


# ---------------- build_tips 符号方向（口径相关） ----------------

def _ordered(stocks):
    """与 build_page_data 一致：按板块资金总额倒序（最末端=净卖出最重板块）"""
    groups = {}
    for s in stocks.values():
        groups.setdefault(s["行业"].split("-")[0], []).append(s)
    return [(n, g) for n, g in sorted(
        groups.items(), key=lambda kv: sum(x["净流入"] or 0 for x in kv[1]), reverse=True)]


def test_tips_em_sell_side_no_double_negative():
    """东财口径：'遭净卖出 1.28亿'，无负号叠加、无误用'主力'"""
    stocks = {
        "000001": {"代码": "000001", "简称": "盈新发展", "上榜次数": 1,
                   "涨跌幅": 9.93, "净流入": 5.00e8, "行业": "电子"},
        "600001": {"代码": "600001", "简称": "中粮糖业", "上榜次数": 1,
                   "涨跌幅": -10.00, "净流入": -1.28e8, "行业": "农林牧渔"},
        "830111": {"代码": "830111", "简称": "*ST清越", "上榜次数": 1,
                   "涨跌幅": -20.55, "净流入": -1.9e5, "行业": "医药"},
    }
    tips = al.build_tips(_ordered(stocks), stocks, "东方财富")
    html = " ".join(t["html"] for t in tips)
    assert '获净买入 <b class="r">+5.00亿</b>' in html
    assert '遭净卖出 <b class="g">1.28亿</b>' in html   # 卖出侧为绝对值，无"负号 + 方向词"双重否定
    assert "净卖出 -" not in html and "净买入 -" not in html   # 板块总额负号合法，方向词后负号非法
    assert "获主力" not in html and "遭主力" not in html and "遭净买入" not in html
    assert "净卖出 19万" in html and "净买入 -19万" not in html


def test_tips_ifind_keeps_original_wording():
    stocks = {
        "000001": {"代码": "000001", "简称": "盈新发展", "上榜次数": 1,
                   "涨跌幅": 9.93, "净流入": 5.00e8, "行业": "电子"},
        "600001": {"代码": "600001", "简称": "中粮糖业", "上榜次数": 1,
                   "涨跌幅": -10.00, "净流入": -1.28e8, "行业": "农林牧渔"},
    }
    tips = al.build_tips(_ordered(stocks), stocks, "同花顺 iFinD")
    html = " ".join(t["html"] for t in tips)
    assert '获主力 <b class="r">+5.00亿</b>' in html
    assert '遭主力 <b class="g">-1.28亿</b>' in html   # iFinD 口径保留负号
    assert "净卖出" not in html            # iFinD 口径不引入东财词