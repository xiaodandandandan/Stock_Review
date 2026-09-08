// 龙虎榜长图渲染脚本：把数据页拆为两张图
//   图1 板块资金分布（hero + 统计 + 分布图 + 盘面要点）
//   图2 分板块个股明细（hero + 明细卡片）
// 用法：node render_lhb_panorama.js <page.html> [图1输出.png] [图2输出.png]
//   page.html 由 analyze_lhb.py 依据 lhb_template.html 生成（内嵌 JSON 数据）
// 可通过环境变量 PUPPETEER_EXECUTABLE_PATH 指定 Chrome / chrome-headless-shell 路径
const path = require('path');
const puppeteer = require('puppeteer');

(async () => {
  const [, , pagePath, argOut1, argOut2] = process.argv;
  if (!pagePath) {
    console.error('用法: node render_lhb_panorama.js <page.html> [图1输出.png] [图2输出.png]');
    process.exit(1);
  }
  const pageHtml = path.resolve(pagePath);

  const browser = await puppeteer.launch({
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--force-color-profile=srgb', '--hide-scrollbars']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 900, height: 1200, deviceScaleFactor: 2 });
  await page.goto('file://' + pageHtml, { waitUntil: 'networkidle0', timeout: 60000 });
  await page.evaluate(() => document.fonts.ready);
  await new Promise(r => setTimeout(r, 800));

  // 从页面内嵌 JSON 读取元信息（个股数 / 板块数 / 日期）
  const meta = await page.evaluate(() =>
    JSON.parse(document.getElementById('lhb-data').textContent).meta);
  const { nStocks: N_STOCKS, nSectors: N_SECTORS, day } = meta;
  const out1 = path.resolve(argOut1 || path.join(path.dirname(pageHtml), `lhb_sector_flow_${day}.png`));
  const out2 = path.resolve(argOut2 || path.join(path.dirname(pageHtml), `lhb_stock_detail_${day}.png`));

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
  await page.evaluate(([n, m]) => {
    document.querySelector('h1').innerHTML = '龙虎榜 <span class="accent">·</span> 板块资金分布';
    document.querySelector('.hero-sub').innerHTML =
      `<b>${n}</b> 只上榜个股按同花顺行业整合为 <b>${m}</b> 个板块 ｜ 主力资金净流向一览`;
    document.querySelector('#sec-flow .sec-no').textContent = '01';
    document.querySelector('#sec-tips .sec-no').textContent = '02';
    document.querySelector('#sec-cards').style.display = 'none';  // 隐藏个股明细
  }, [N_STOCKS, N_SECTORS]);
  await new Promise(r => setTimeout(r, 300));
  let i1 = await info();
  console.log('sector-flow img:', JSON.stringify(i1));
  if (i1.bars !== N_SECTORS || !i1.visFlow || !i1.visTips || !i1.visStats || i1.visCards) {
    console.error('CONTENT MISMATCH (img1)!'); process.exit(2);
  }
  await page.screenshot({ path: out1, fullPage: true });
  console.log('saved:', out1);

  // ---------- 图2：分板块个股明细（hero + 明细卡片） ----------
  await page.evaluate(n => {
    document.querySelector('h1').innerHTML = '龙虎榜 <span class="accent">·</span> 分板块个股明细';
    document.querySelector('.hero-sub').innerHTML =
      `<b>${n}</b> 只上榜个股 ｜ 标注当日涨幅与主力资金流向 ｜ 组内按主力净流入排序`;
    document.querySelector('#sec-cards .sec-no').textContent = '01';
    document.querySelector('#sec-cards').style.display = '';    // 显示个股明细
    document.querySelector('#stats').style.display = 'none';    // 隐藏统计卡片
    document.querySelector('#sec-flow').style.display = 'none';  // 隐藏板块资金分布
    document.querySelector('#sec-tips').style.display = 'none';  // 隐藏盘面要点
  }, N_STOCKS);
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
