/**
 * Playwright capture script — all 7 FIFA Classic export formats
 * Usage: node qa_exports/capture_all_formats.js
 * Requires: npx playwright install chromium (once)
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE_URL = 'http://localhost:8000';
const USER_ID  = 19310;
const OUT_DIR  = path.join(__dirname);

const FORMATS = [
  { bucket: 'portrait',  platform: 'instagram_portrait',  w: 1080, h: 1350 },
  { bucket: 'story',     platform: 'instagram_story',     w: 1080, h: 1920 },
  { bucket: 'square',    platform: 'instagram_square',    w: 1080, h: 1080 },
  { bucket: 'landscape', platform: 'facebook_landscape',  w: 1200, h: 630  },
  { bucket: 'tiktok',    platform: 'tiktok',              w: 1080, h: 1920 },
  { bucket: 'banner',    platform: 'banner_custom',       w: 1500, h: 500  },
  { bucket: 'og',        platform: 'og',                  w: 1200, h: 630  },
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];

  for (const fmt of FORMATS) {
    const url = `${BASE_URL}/players/${USER_ID}/card?platform=${fmt.platform}&export=1`;
    const outFile = path.join(OUT_DIR, `${fmt.bucket}_${fmt.platform}.png`);

    const page = await browser.newPage();
    await page.setViewportSize({ width: fmt.w, height: fmt.h });
    const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    const status = resp.status();

    // Wait for fonts (font-display:block) to render
    await page.waitForTimeout(800);

    await page.screenshot({ path: outFile, fullPage: false, clip: { x: 0, y: 0, width: fmt.w, height: fmt.h } });
    await page.close();

    const size = fs.statSync(outFile).size;
    results.push({ bucket: fmt.bucket, platform: fmt.platform, status, file: path.basename(outFile), bytes: size });
    console.log(`✅  ${fmt.bucket.padEnd(10)} HTTP ${status}  →  ${path.basename(outFile)}  (${(size/1024).toFixed(1)} KB)`);
  }

  await browser.close();

  console.log('\n── Summary ──');
  const allOk = results.every(r => r.status === 200 && r.bytes > 10_000);
  console.log(allOk ? '✅  All 7 exports OK' : '❌  Some exports failed');
  if (!allOk) {
    results.filter(r => r.status !== 200 || r.bytes <= 10_000)
           .forEach(r => console.error(`  FAIL: ${r.bucket} — HTTP ${r.status}, ${r.bytes} bytes`));
    process.exit(1);
  }
})();
