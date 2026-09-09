# Stock_Review · 每日复盘

A 股每日复盘可视化工具集：从同花顺 iFinD 自动取数，聚合龙虎榜、涨跌停、板块资金流动等维度，产出一键可发的竖版长图、Markdown 报告与移动端自适应的总览 HTML。

> 数据来源：同花顺 iFinD ｜ 仅供学习参考，不构成投资建议。

## 功能概览

| 能力 | 说明 | 主要脚本 |
|------|------|---------|
| 龙虎榜自动化流水线 | iFinD 取数 → 行业聚合 → Markdown 报告 + 两张长图 | `analyze_lhb.py` |
| 龙虎榜板块分析图 | 净买入/净卖出板块榜 + 个股明细 + 关键信号（PIL） | `render_lhb.py` |
| 龙虎榜个股明细图 | 分板块卡片式展示，精简无代码列，字号更大（PIL） | `render_lhb_stock_detail.py` |
| 涨跌停板块全景图 | 行业分布 / 题材主线 / 连板梯队 / 跌停阵营 / 核心结论（PIL，1440px 宽幅） | `render_limit.py` |
| 全市场板块资金流 | 31 个申万行业双向条形图（PIL） | `render_sector_flow.py` |
| 龙虎榜两日对比 | 今日 vs 昨日板块分布对比（PIL） | `render_lhb_compare.py` |
| 复盘总览 HTML | 单页汇总龙虎榜 + 涨跌停 + 三张长图，**移动端自适应**，支持**图片 base64 内嵌** | `build_index_html.py` |

## 目录结构

```
Stock_Review/
├── analyze_lhb.py             # 龙虎榜主流程：iFinD 取数 + 聚合 + 报告 + 调渲染
├── build_index_html.py        # 复盘总览 HTML 生成器（响应式 + base64 内嵌）
├── render_lhb.py              # 龙虎榜·板块分析长图（PIL）
├── render_lhb_stock_detail.py # 龙虎榜·分板块个股明细长图（PIL，精简版）
├── render_limit.py            # 涨跌停·板块全景长图（PIL，宽幅 1440px）
├── render_sector_flow.py      # 全市场·板块资金流动长图（PIL）
├── render_lhb_compare.py      # 龙虎榜·板块分布两日对比长图（PIL）
├── render_lhb_panorama.js     # puppeteer 渲染：从模板截出两张长图
├── lhb_template.html          # 龙虎榜长图 HTML 模板（内嵌 JSON 数据）
├── preview_sector_flow.html   # 板块资金流动交互式预览（浏览器直接打开）
├── package.json               # Node 依赖（puppeteer、@fontsource/noto-sans-sc）
└── fonts/                     # PIL 脚本所需字体（.gitignore 排除）
    ├── NotoSansSC-Bold.otf
    └── NotoSansSC-Regular.otf
```

## 快速开始

### 1. 安装依赖

```bash
# Python
pip install requests Pillow

# Node（龙虎榜自动化流水线需要，可选）
npm install
```

### 2. 准备字体（仅 PIL 静态脚本需要）

将 `NotoSansSC-Bold.otf`、`NotoSansSC-Regular.otf` 放入 `fonts/`（已 gitignore）。
可从 [Noto Sans SC（Google Fonts）](https://fonts.google.com/noto/specimen/Noto+Sans+SC) 或 [noto-cjk 仓库](https://github.com/notofonts/noto-cjk) 下载。

> 龙虎榜自动化流水线（`lhb_template.html`）的中文字体由 npm 包 `@fontsource/noto-sans-sc` 自动提供，无需手动放置。

### 3. 配置认证

```bash
export IFIND_AUTH_TOKEN=<同花顺 MCP 密钥>
# 可选：指定无头浏览器路径（默认探测 puppeteer 缓存）
export PUPPETEER_EXECUTABLE_PATH=/path/to/chrome-headless-shell
```

## 使用方式

### 龙虎榜自动化流水线（推荐）

一条命令完成取数、聚合、报告与两张长图：

```bash
python analyze_lhb.py 20260908      # 缺省日期则取今天
```

产物：

- `lhb_report_YYYYMMDD.md` — 板块汇总 + 个股明细 Markdown 报告
- `lhb_page_YYYYMMDD.html` — 注入数据后的中间页面
- `lhb_sector_flow_YYYYMMDD.png` — 图1：板块资金分布
- `lhb_stock_detail_YYYYMMDD.png` — 图2：分板块个股明细

### PIL 静态长图

数据已预置在脚本顶部，直接运行即可出图（适合小红书/公众号等固定版式发布）：

```bash
python render_lhb.py              # 龙虎榜板块分析
python render_lhb_stock_detail.py # 龙虎榜分板块个股明细（精简版）
python render_limit.py            # 涨跌停板块全景
python render_sector_flow.py      # 全市场板块资金流动
python render_lhb_compare.py      # 龙虎榜两日对比
```

> 静态脚本内数据为对应日期快照，更新时需同步修改脚本顶部数据、标题日期与输出文件名。

### 复盘总览 HTML（手机分享推荐）

将龙虎榜 + 涨跌停 + 三张长图汇总为单页 HTML，**移动端自适应**，支持**图片 base64 内嵌**（单文件自包含，发到手机直接打开）。

```python
from build_index_html import build_summary_page
import json

with open('data.json', encoding='utf-8') as f:
    data = json.load(f)

build_summary_page(
    data,
    out_path='index.html',
    lhb_sector_img='lhb_sector_flow.png',
    lhb_detail_img='lhb_stock_detail.png',
    limit_img='limit_panorama.png',
    embed_images=True,   # 开启 base64 内嵌：单文件，手机分享首选
)
```

**数据结构**（与 `analyze_lhb.py` 产出一致）：

```python
{
  "day": "20260909",
  "date_cn": "2026年9月9日",
  "lhb_stocks":   [[code, name, cnt, chg, flow, industry], ...],
  "limit_up":     [[code, name, chg, sub_industry, level1], ...],
  "limit_down":   [[code, name, chg, industry], ...],
  "heavy_fall":   [[code, name, chg, industry], ...],
  "streaks":      [[code, name, days, sub], ...],
  # 可选：自定义盘面要点（4 条龙虎榜 + 4 条涨跌停）
  "lhb_insights":   ["...", "...", "...", "..."],
  "limit_insights": ["...", "...", "...", "..."],
}
```

**响应式断点：**

| 断点 | 适配 |
|------|------|
| ≤ 640px | 统计卡片 6 列 → 3 列，要点卡片 2 列 → 1 列，字号整体缩小，边距收紧 |
| ≤ 380px | 超小屏二次缩放（标题 22px、表格 11px） |

## 设计要点

### 视觉体系

- **PIL 静态脚本**：米白背景 `#fafaf7` + 白卡片 + 红涨绿跌（`#d93a3f` / `#2b8a5a`）+ 品牌红点缀
- **自动化模板**：深蓝 `#13294e` + 金色分隔线 `#d9b25f` + `tabular-nums` 等宽数字
- **复盘总览页**：深蓝金体系 + 响应式栅格 + 移动端单列布局

### 渲染质量

- **基线对齐**：v2 版本所有文字统一使用基线（`anchor='ls' / 'rs'`）而非居中锚点，数字与汉字不再高低错位（像素级偏差 ≤ 2px）
- **超采样输出**：PIL 脚本全部采用 2× 超采样（`SS=2`）再 LANCZOS 缩小，边缘更平滑
- **宽幅画布**：涨跌停全景图宽 1440px，条形图与数量文字分离，避免遮挡

### 一张模板两张图

`render_lhb_panorama.js` 通过切换各区块 `display` 与标题，从同一数据页截出「板块资金分布」「个股明细」两张长图，并校验区块数量防漏截。

## 数据口径

- 行业统一映射到 **同花顺（申万）一级行业**。
- 龙虎榜口径为当日上榜净买入额（单日 + 三日榜）；涨跌幅为前复权口径。
- 资金流动口径为全市场 / 龙虎榜个股的主力资金净流入额（正 = 流入，负 = 流出）。
- 涨停/跌停为当日收盘价触及涨跌停价（含一字板、ST 5% 板）；重挫为跌幅 ≤ -9%。
- 自动化流水线所需数据均由脚本实时从 iFinD 获取。

## 免责声明

本项目仅用于个人学习与研究，所有数据与结论不构成任何投资建议。
