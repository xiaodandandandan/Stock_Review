// 龙虎榜长图渲染脚本（数据日期：2026-09-08）
// 拆分为两张图：① 板块资金分布（hero+统计+分布图+要点） ② 分板块个股明细
// 用法：npm install 后执行  node render_lhb_panorama.js [图1输出.png] [图2输出.png]
// 可通过环境变量 PUPPETEER_EXECUTABLE_PATH 指定 Chrome / chrome-headless-shell 路径
// 数据来源：同花顺 iFinD（龙虎榜上榜个股、当日涨跌幅、主力资金净流入、同花顺行业分类）
const path = require('path');
const puppeteer = require('puppeteer');

const N_STOCKS = 55;   // 上榜个股数
const N_SECTORS = 23;  // 板块数

(async () => {
  const html = path.join(__dirname, 'render_lhb_panorama.html');
  const out1 = process.argv[2] || path.join(__dirname, 'lhb_sector_flow_20260908.png');
  const out2 = process.argv[3] || path.join(__dirname, 'lhb_stock_detail_20260908.png');
  const exe = process.env.PUPPETEER_EXECUTABLE_PATH;

  const browser = await puppeteer.launch({
    ...(exe ? { executablePath: exe } : {}),
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--force-color-profile=srgb', '--hide-scrollbars']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 900, height: 1200, deviceScaleFactor: 2 });
  await page.goto('file://' + html, { waitUntil: 'networkidle0', timeout: 60000 });
  await page.evaluate(() => document.fonts.ready);
  await new Promise(r => setTimeout(r, 800));

  const info = () => page.evaluate(() => {
    const vis = id => {
      const el = document.getElementById(id);
      return !!el && el.offsetParent !== null;   // display:none 时为 null
    };
    return {
      rows: document.querySelectorAll('.row').length,
      bars: document.querySelectorAll('.crow').length,
      cards: document.querySelectorAll('.card').length,
      visFlow: vis('sec-flow'), visCards: vis('sec-cards'),
      visTips: vis('sec-tips'), visStats: vis('stats'),
      h: document.body.scrollHeight
    };
  });

  // ---------- 图1：板块资金分布（hero + 统计 + 分布图 + 盘面要点） ----------
  await page.evaluate(() => {
    document.querySelector('h1').innerHTML = '龙虎榜 <span class="accent">·</span> 板块资金分布';
    document.querySelector('.hero-sub').innerHTML =
      '<b>55</b> 只上榜个股按同花顺行业整合为 <b>23</b> 个板块 ｜ 主力资金净流向一览';
    document.querySelector('#sec-flow .sec-no').textContent = '01';
    document.querySelector('#sec-tips .sec-no').textContent = '02';
    document.querySelector('#sec-cards').style.display = 'none';  // 隐藏个股明细
  });
  await new Promise(r => setTimeout(r, 300));
  let i1 = await info();
  console.log('sector-flow img:', JSON.stringify(i1));
  if (i1.bars !== N_SECTORS || !i1.visFlow || !i1.visTips || !i1.visStats || i1.visCards) {
    console.error('CONTENT MISMATCH (img1)!'); process.exit(2);
  }
  await page.screenshot({ path: out1, fullPage: true });
  console.log('saved:', out1);

  // ---------- 图2：分板块个股明细（hero + 明细卡片） ----------
  await page.evaluate(() => {
    document.querySelector('h1').innerHTML = '龙虎榜 <span class="accent">·</span> 分板块个股明细';
    document.querySelector('.hero-sub').innerHTML =
      '<b>55</b> 只上榜个股 ｜ 标注当日涨幅与主力资金流向 ｜ 组内按主力净流入排序';
    document.querySelector('#sec-cards .sec-no').textContent = '01';
    document.querySelector('#sec-cards').style.display = '';    // 显示个股明细
    document.querySelector('#stats').style.display = 'none';    // 隐藏统计卡片
    document.querySelector('#sec-flow').style.display = 'none';  // 隐藏板块资金分布
    document.querySelector('#sec-tips').style.display = 'none';  // 隐藏盘面要点
  });
  await new Promise(r => setTimeout(r, 300));
  let i2 = await info();
  console.log('stock-detail img:', JSON.stringify(i2));
  if (i2.rows !== N_STOCKS || i2.cards !== N_SECTORS || !i2.visCards || i2.visFlow || i2.visTips || i2.visStats) {
    console.error('CONTENT MISMATCH (img2)!'); process.exit(2);
  }
  await page.screenshot({ path: out2, fullPage: true });
  console.log('saved:', out2);

  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
