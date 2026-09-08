# Stock_Review · 每日复盘

A 股每日复盘可视化工具集：从同花顺 iFinD 自动取数，聚合龙虎榜、涨跌停、板块资金流动等维度，产出一键可发的竖版长图与 Markdown 报告。

> 数据来源：同花顺 iFinD ｜ 仅供学习参考，不构成投资建议。

## 两条渲染流水线

仓库包含两套方案，一套是纯 Python(PIL) 的静态脚本，一套是「iFinD 取数 → 模板注入 → puppeteer 截图」的自动化流水线。

| 输入 | 脚本 / 文件 | 功能 | 输出 |
|------|------------|------|------|
| 静态 | `analyze_lhb.py` | 龙虎榜全流程：iFinD 取数 → 行业聚合 → 报告 + 长图 | `lhb_report_*.md` + 2 张 PNG |
| 静态 | `lhb_template.html` | 长图 HTML 模板（内嵌 JSON 数据 + 富文本要点） | — |
| 静态 | `render_lhb_panorama.js` | puppeteer 渲染：拆分为「板块资金分布」「个股明细」两张图 | 2 张 PNG |
| 静态 | `render_lhb.py` | 龙虎榜·板块分析长图（净买入/卖出榜 + 关键信号） | `lhb_concept_0908.png` |
| 静态 | `render_limit.py` | 涨跌停·板块全景长图（行业分布 / 题材 / 连板梯队 / 重挫） | `limit_panorama_0908.png` |
| 静态 | `render_sector_flow.py` | 全市场·板块资金流动长图（31 个申万行业双向条形图） | `sector_flow_0908.png` |
| 静态 | `render_lhb_compare.py` | 龙虎榜·板块分布两日对比长图 | `lhb_compare_0908.png` |
| 静态 | `preview_sector_flow.html` | 板块资金流动交互式预览（浏览器直接打开） | — |

## 目录结构

```
stock-image-scripts/
├── analyze_lhb.py             # 主流程：iFinD 取数 + 聚合 + 报告 + 调渲染
├── render_lhb_panorama.js     # puppeteer 渲染两张长图
├── lhb_template.html          # 长图模板（@fontsource 中文字体）
├── render_lhb.py              # 龙虎榜板块分析长图（PIL）
├── render_limit.py            # 涨跌停板块全景长图（PIL）
├── render_sector_flow.py      # 全市场板块资金流动长图（PIL）
├── render_lhb_compare.py      # 龙虎榜两日对比长图（PIL）
├── preview_sector_flow.html   # 板块资金流动动态预览
├── package.json               # Node 依赖（puppeteer、@fontsource/noto-sans-sc）
├── lhb_report_20260908.md     # 输出报告样例
└── fonts/                     # PIL 脚本所需字体（.gitignore 排除）
    ├── NotoSansSC-Bold.otf
    └── NotoSansSC-Regular.otf
```

## 快速开始

### 1. 安装依赖

```bash
# Python
pip install requests Pillow

# Node（龙虎榜自动化流水线需要）
npm install
```

### 2. 准备字体（仅 PIL 静态脚本需要）

将 `NotoSansSC-Bold.otf`、`NotoSansSC-Regular.otf` 放入 `fonts/`（已 gitignore）。可从 [Noto Sans SC（Google Fonts）](https://fonts.google.com/noto/specimen/Noto+Sans+SC) 或 [noto-cjk 仓库](https://github.com/notofonts/noto-cjk) 下载。

> 龙虎榜自动化流水线（`lhb_template.html`）的中文字体由 npm 包 `@fontsource/noto-sans-sc` 自动提供，无需手动放置。

### 3. 配置认证

```bash
export IFIND_AUTH_TOKEN=<同花顺 MCP 密钥>
# 可选：指定无头浏览器路径（默认探测 puppeteer 缓存）
export PUPPETEER_EXECUTABLE_PATH=/path/to/chrome-headless-shell
```

## 使用方式

**龙虎榜自动化流水线（推荐）**——一条命令完成取数、聚合、报告与两张长图：

```bash
python analyze_lhb.py 20260908      # 缺省日期则取今天
```

产物：

- `lhb_report_20260908.md` —— 板块汇总 + 个股明细 Markdown 报告
- `lhb_page_20260908.html` —— 注入数据后的中间页面
- `lhb_sector_flow_20260908.png` —— 图1：板块资金分布
- `lhb_stock_detail_20260908.png` —— 图2：分板块个股明细

**PIL 静态脚本**——数据已硬编码在脚本顶部，直接运行即可出图：

```bash
python render_lhb.py
python render_limit.py
python render_sector_flow.py
python render_lhb_compare.py
```

> 静态脚本内数据为 2026.09.08 快照，更新时需同步修改脚本顶部数据、标题日期与输出文件名。

## 实现说明

- **自动化流水线**：`analyze_lhb.py` 通过 MCP HTTP 协议调用 iFinD 的 `search_stocks` / `get_stock_performance`，按同花顺一级行业聚合主力资金，生成 Markdown 报告，再把数据注入 `lhb_template.html` 交由 `render_lhb_panorama.js` 用 puppeteer 截图。
- **一张模板两张图**：`render_lhb_panorama.js` 通过切换各区块 `display` 与标题，从同一数据页截出「板块资金分布」「个股明细」两张长图，并校验区块数量防漏截。
- **统一视觉体系**：PIL 脚本共用米白背景 / 白卡片 / 红涨绿跌 / 品牌红点缀；自动化模板采用深蓝 + 金色分隔线 + `tabular-nums` 等宽数字。
- **数值对齐**：对比图（`render_lhb_compare.py`）用等宽字体 + `%+6.2f` 固定宽度，保证小数点垂直对齐；模板用 `font-variant-numeric: tabular-nums` 对齐数字。

## 数据口径

- 行业统一映射到**同花顺（申万）一级行业**。
- 龙虎榜口径为当日上榜净买入额（单日 + 三日榜）；涨跌幅为前复权口径。
- 资金流动口径为全市场 / 龙虎榜个股的主力资金净流入额（正 = 流入，负 = 流出）。
- 自动化流水线所需数据均由脚本实时从 iFinD 获取，`lhb_report_20260908.md` 为当日输出样例。

## 免责声明

本项目仅用于个人学习与研究，所有数据与结论不构成任何投资建议。