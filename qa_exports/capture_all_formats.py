"""
Playwright capture — all 7 FIFA Classic export formats
Usage: python qa_exports/capture_all_formats.py
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8000"
USER_ID  = 19310
OUT_DIR  = Path(__file__).parent

FORMATS = [
    ("portrait",  "instagram_portrait",  1080, 1350),
    ("story",     "instagram_story",     1080, 1920),
    ("square",    "instagram_square",    1080, 1080),
    ("landscape", "facebook_landscape",  1200,  630),
    ("tiktok",    "tiktok",             1080, 1920),
    ("banner",    "banner_custom",       1500,  500),
    ("og",        "og",                 1200,  630),
]

results = []

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)

    for bucket, platform, w, h in FORMATS:
        url = f"{BASE_URL}/players/{USER_ID}/card?platform={platform}&export=1"
        out = OUT_DIR / f"{bucket}_{platform}.png"

        page = browser.new_page()
        page.set_viewport_size({"width": w, "height": h})
        resp = page.goto(url, wait_until="networkidle", timeout=15_000)
        status = resp.status
        # Let font-display:block fonts paint
        page.wait_for_timeout(800)
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": w, "height": h})
        page.close()

        size_kb = out.stat().st_size / 1024
        ok = status == 200 and size_kb > 10
        results.append((bucket, platform, status, out.name, size_kb, ok))
        icon = "✅" if ok else "❌"
        print(f"{icon}  {bucket:<10}  HTTP {status}  →  {out.name}  ({size_kb:.1f} KB)")

    browser.close()

print("\n── Summary ──")
all_ok = all(r[5] for r in results)
print("✅  All 7 exports OK" if all_ok else "❌  Some exports failed")
if not all_ok:
    for r in results:
        if not r[5]:
            print(f"   FAIL: {r[0]} — HTTP {r[2]}, {r[3]:.1f} KB")
    sys.exit(1)
