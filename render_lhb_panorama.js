// 龙虎榜板块资金全景长图渲染脚本（数据日期：2026-09-08）
// 用法：npm install 后执行  node render_lhb_panorama.js [输出路径.png]
// 可通过环境变量 PUPPETEER_EXECUTABLE_PATH 指定 Chrome / chrome-headless-shell 路径
// 数据来源：同花顺 iFinD（龙虎榜上榜个股、当日涨跌幅、主力资金净流入、同花顺行业分类）
const path = require('path');
const puppeteer = require('puppeteer');

(async () => {
  const html = path.join(__dirname, 'render_lhb_panorama.html');
  const out = process.argv[2] || path.join(__dirname, 'lhb_panorama_20260908.png');
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

  // 内容完整性校验：55 只个股 / 23 个板块
  const info = await page.evaluate(() => ({
    rows: document.querySelectorAll('.row').length,
    bars: document.querySelectorAll('.crow').length,
    cards: document.querySelectorAll('.card').length,
    h: document.body.scrollHeight
  }));
  console.log('render info:', JSON.stringify(info));
  if (info.rows !== 55 || info.bars !== 23 || info.cards !== 23) {
    console.error('CONTENT MISMATCH!'); process.exit(2);
  }

  await page.screenshot({ path: out, fullPage: true });
  await browser.close();
  console.log('saved:', out);
})().catch(e => { console.error(e); process.exit(1); });
