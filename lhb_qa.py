# -*- coding: utf-8 -*-
"""
龙虎榜排版自检（不触网、不渲染）

跑完整条取数→报告→长图链路后，对产物做一致性校验，直接给出"合规/违规"结论，
免去人工逐图比对：
  1. 数据数学一致性（stocks 内部自洽：去重/字段完整/未分类阈值/买入卖出计数平衡）
  2. 文本口径一致性（来源徽标与数据源匹配、口径词与来源匹配、无残留占位符）

用法：
    from lhb_qa import verify_lhb
    ok = verify_lhb("20260910", stocks, source="东方财富")   # 读产物文本自动校验，全过写 qa_YYYYMMDD.txt
    # 或仅取校验结果：
    from lhb_qa import run_qa
    results = run_qa(stocks, report_md=..., page_html=..., source="东方财富")

说明：数据源 source ∈ {"东方财富", "同花顺 iFinD"}，后缀匹配（"东方财富..."）亦可。
"""

EM_WORDS = ("净买入", "龙虎榜净买入额", "东财一级", "东方财富行业分类")
EM_BAD = ("主力净流入", "同花顺行业", "同花顺一级")       # 东财产物不应出现（iFinD 专属）
IFIND_WORDS = ("主力净流入", "同花顺一级", "同花顺行业分类")
IFIND_BAD = ("东方财富", "龙虎榜净买入额", "东财一级", "东方财富行业分类")
PLACEHOLDERS = ("__LHB_SOURCE__", "__LHB_DATA__", "__FLOW_SORT__", "__FLOW_HDR__")   # 与 lhb_template.html 中的占位符一一对应
REQUIRED_FIELDS = ("代码", "简称", "涨跌幅", "净流入", "行业")


def run_qa(stocks, report_md="", page_html="", source="东方财富", max_uncat=0):
    """执行全部自检，返回 [{name, ok, detail}]；文本缺省时相关项跳过（不算违规）"""
    em = source.startswith("东方财富")
    checks = []

    # ---- 1) 数据数学一致性 ----
    codes = list(stocks)

    missing = {c: [k for k in REQUIRED_FIELDS if k not in stocks[c]] for c in codes}
    missing = {c: k for c, k in missing.items() if k}
    checks.append(_check("stocks-字段完整", not missing,
                         "全部字段齐全" if not missing else f"缺字段：{missing}"))

    uncat = [c for c, s in stocks.items() if s.get("行业") in (None, "", "未分类")]
    checks.append(_check("stocks-行业未分类", len(uncat) <= max_uncat,
                         f"未分类 {len(uncat)} 只（阈值 {max_uncat}）" if len(uncat) <= max_uncat
                         else f"未分类 {len(uncat)} 只超出阈值：{uncat}"))

    n_in = sum(1 for s in stocks.values() if (s.get("净流入") or 0) > 0)
    n_out = sum(1 for s in stocks.values() if (s.get("净流入") or 0) < 0)
    n_none = sum(1 for s in stocks.values() if s.get("净流入") is None)
    balance = n_in + n_out + n_none == len(codes)
    checks.append(_check("stocks-计数平衡", balance,
                         f"净买入 {n_in} + 净卖出 {n_out} + 无数据 {n_none} = 总数 {len(codes)}"
                         if balance else f"计数失衡：{n_in}+{n_out}+{n_none} != {len(codes)}"))

    # ---- 2) 文本口径一致性（徽标/占位符按载体分别检查） ----
    checks += _text_checks(report_md, "报告", source, em)
    checks += _text_checks(page_html, "数据页", source, em)

    # 口径词按"报告+数据页"整体检查：两类词元分布在两个载体上，各载体验证会互为缺口
    combined = report_md + "\n" + page_html
    if combined:
        checks.append(_combined_word_check(combined, "产物", source, em))
    return checks


def _combined_word_check(text, label, source, em):
    words, bad = (EM_WORDS, EM_BAD) if em else (IFIND_WORDS, IFIND_BAD)
    miss = [w for w in words if w not in text]
    hit = [w for w in bad if w in text]
    ok = not miss and not hit
    detail = (f"口径词齐备（{source}）" if ok
              else (("缺口径词：" + "、".join(miss)) if miss else "") + (
                  (("；" if miss else "") + "误出现他源词：" + "、".join(hit)) if hit else ""))
    return _check(f"{label}-口径词", ok, detail)


def _text_checks(text, label, source, em):
    out = []
    if not text:
        out.append(_check(f"{label}-来源徽标", True, "跳过：无文本"))
        out.append(_check(f"{label}-占位符残留", True, "跳过：无文本"))
        return out

    bad_src = "同花顺 iFinD" if em else "东方财富"
    good_src = "东方财富" if em else "同花顺 iFinD"
    out.append(_check(f"{label}-来源徽标", bad_src not in text and good_src in text,
                      f"来源标注为 {good_src}，无 {bad_src} 误标"
                      if (bad_src not in text and good_src in text)
                      else f"来源标注不符：应含「{good_src}」且不含「{bad_src}」"))

    left = [p for p in PLACEHOLDERS if p in text]
    out.append(_check(f"{label}-占位符残留", not left,
                      "无占位符残留" if not left else f"残留占位符：{left}"))

    return out


def _check(name, ok, detail):
    return {"name": name, "ok": bool(ok), "detail": detail}


def verify_lhb(day, stocks, source="东方财富", md_path=None, page_path=None, max_uncat=0,
               out_dir=None):
    """一站式自检：读产物文本跑 run_qa；全过写 qa_{day}.txt 并返回 True，否则返回 False。

    不抛异常——违规只影响"排版合规"结论，产物文件仍有效。"""
    import os
    base = os.path.dirname(os.path.abspath(__file__)) if out_dir is None else out_dir
    md = ""
    if md_path is None:
        md_path = os.path.join(base, f"lhb_report_{day}.md")
    page = ""
    if page_path is None:
        page_path = os.path.join(base, f"lhb_page_{day}.html")
    for p in (md_path, page_path):
        try:
            with open(p, encoding="utf-8") as f:
                if p.endswith(".md"):
                    md = f.read()
                else:
                    page = f.read()
        except FileNotFoundError:
            pass

    results = run_qa(stocks, md, page, source, max_uncat)
    failed = [r for r in results if not r["ok"]]
    ok = not failed

    if ok:
        with open(os.path.join(base, f"qa_{day}.txt"), "w", encoding="utf-8") as f:
            f.write(f"# 龙虎榜排版自检 {day}（来源：{source}）\n")
            for r in results:
                f.write(f"[通过] {r['name']}：{r['detail']}\n")
    return ok