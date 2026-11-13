// recorte quadrado do ícone (sem legenda) a 1200x1200, a partir do SVG vetorial
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [svgDir, outDir, fontDir] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const ff = w => `@font-face{font-family:'Barlow Condensed';font-weight:${w};src:url(data:font/woff2;base64,${fs.readFileSync(path.join(fontDir, `barlow-condensed-latin-${w}-normal.woff2`)).toString('base64')}) format('woff2')}`;
const css = [500, 600, 700].map(ff).join('');
const SCALE = 1.2, CROP = { x: 100, y: 55, width: 1000, height: 1000 };
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1200, height: 1200 }, deviceScaleFactor: SCALE });
  for (const f of fs.readdirSync(svgDir).filter(f => f.endsWith('-quadrado.svg')).sort()) {
    await p.setContent(`<html><head><style>${css}html,body{margin:0}</style></head><body>${fs.readFileSync(path.join(svgDir, f), 'utf8')}</body></html>`);
    await p.evaluate(() => document.fonts.ready);
    await p.screenshot({ path: path.join(outDir, f.replace('-quadrado.svg', '.png')), clip: CROP });
  }
  await b.close();
})();
