// node render.js <svgdir> <pngdir> <fontsdir>
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [svgDir, pngDir, fontDir] = process.argv.slice(2);
fs.mkdirSync(pngDir, { recursive: true });
const ff = (fam, w, file) => `@font-face{font-family:'${fam}';font-weight:${w};src:url(data:font/woff2;base64,${fs.readFileSync(path.join(fontDir, file)).toString('base64')}) format('woff2')}`;
const css = [500, 600, 700].map(w => ff('Barlow Condensed', w, `barlow-condensed-latin-${w}-normal.woff2`)).join('');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 2400, height: 1200 }, deviceScaleFactor: 1 });
  for (const f of fs.readdirSync(svgDir).filter(f => f.endsWith('.svg')).sort()) {
    await p.setContent(`<html><head><style>${css}html,body{margin:0}</style></head><body>${fs.readFileSync(path.join(svgDir, f), 'utf8')}</body></html>`);
    await p.evaluate(() => document.fonts.ready);
    await p.screenshot({ path: path.join(pngDir, f.replace('.svg', '.png')), clip: f.includes('banner') ? { x: 0, y: 0, width: 2400, height: 800 } : { x: 0, y: 0, width: 1200, height: 1200 } });
  }
  await b.close();
})();
