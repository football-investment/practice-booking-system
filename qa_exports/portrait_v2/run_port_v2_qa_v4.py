"""
instagram_portrait — PORT-v2 — 1080×1350
QA Export Script v4  (Split Hero v3.2 — 2026-05-18)
====================================================

Changes vs v3: PosMap integrated into info column (no external posmap-footer zone).
Split hero: 500 → 560px. Skills zone: ~790px (was ~680px).

Scenarios:
  pc1  close-up face photo (face fills top 40%, dark below)
  pc2  full-body photo      (full figure, small face area)
  pc3  centered portrait    (face centered in frame)
  pc4  off-center portrait  (face left-aligned, green pitch background)
  pc5  light background     (high-key / white-ish background)
  pc6  dark background      (low-key / dark background)
  pc7  no photo             (placeholder initials)
  pc8  unknown position     (no posmap, no position labels)

Outputs (all to qa_exports/portrait_v2/v4/):
  pc1..pc8  individual PNGs + HTMLs
  contact_sheet_port_v2_1080x1350.png
  manifest.json
  metrics_baseline_port_v2_1080x1350.json
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

PROJECT = Path("/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system")
OUT_DIR = PROJECT / "qa_exports" / "portrait_v2" / "v4"
OUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(PROJECT))

# ── Minimal PNG generator ─────────────────────────────────────────────────────

def _png_chunk(tag: bytes, data: bytes) -> bytes:
    c = struct.pack(">I", len(data)) + tag + data
    return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

def _make_gradient_png(w: int, h: int, top_rgb: tuple, bot_rgb: tuple) -> bytes:
    raw = bytearray()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top_rgb[0] + (bot_rgb[0] - top_rgb[0]) * t)
        g = int(top_rgb[1] + (bot_rgb[1] - top_rgb[1]) * t)
        b = int(top_rgb[2] + (bot_rgb[2] - top_rgb[2]) * t)
        raw += b'\x00' + bytes([r, g, b] * w)
    compressed = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (
        b'\x89PNG\r\n\x1a\n'
        + _png_chunk(b'IHDR', ihdr)
        + _png_chunk(b'IDAT', compressed)
        + _png_chunk(b'IEND', b'')
    )

def _gradient_uri(top_rgb: tuple, bot_rgb: tuple, w: int = 200, h: int = 400) -> str:
    png = _make_gradient_png(w, h, top_rgb, bot_rgb)
    return f"data:image/png;base64,{base64.b64encode(png).decode()}"

PHOTO_SCENARIOS = {
    "pc1": (_gradient_uri((210, 170, 130), (60, 40, 20)),
            "Close-up face — skin-tone top, dark bottom"),
    "pc2": (_gradient_uri((195, 155, 115), (20, 20, 20)),
            "Full-body — lighter top, very dark bottom"),
    "pc3": (_gradient_uri((50, 50, 70), (30, 30, 50)),
            "Centered portrait — uniform dark background"),
    "pc4": (_gradient_uri((60, 110, 60), (20, 60, 20)),
            "Off-center portrait — green pitch background"),
    "pc5": (_gradient_uri((220, 220, 230), (140, 140, 160)),
            "Light background — high-key, pale blue-grey"),
    "pc6": (_gradient_uri((18, 18, 28), (5, 5, 10)),
            "Dark background — low-key, near-black"),
}

# ── Jinja2 renderer ───────────────────────────────────────────────────────────

from jinja2 import Environment, FileSystemLoader, select_autoescape

TMPL_DIR = PROJECT / "app" / "templates"

def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TMPL_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["nationalities_display"] = lambda v: v or ""
    return env

def _render_html(
    photo_url: str | None,
    player_name: str = "Bence Kovács",
    nationality: str | None = "Hungarian",
    position: str = "CM",
    overall: float = 74.0,
    tier_label: str = "Gold",
    tier_color: str = "#d69e2e",
    pos_color: str = "#667eea",
    show_posmap: bool = True,
    height_cm: int | None = 178,
    weight_kg: int | None = 72,
    current_level: int | None = 4,
) -> str:
    env = _make_env()
    tmpl = env.get_template("public/export/portrait/fifa.html")

    class MockPlayer:
        name = player_name
        age_group = "U-19"
        total_tournaments = 12
        skills: dict = {}
        def __init__(self):
            self.nationality = nationality
            self.position = position

    player = MockPlayer()

    class MockSkill:
        def __init__(self, key: str, name: str):
            self.key = key
            self.name_en = name

    class MockCat:
        def __init__(self, name: str, skills: list):
            self.name = name
            self.skills = skills

    def _skills(prefix: str, count: int) -> list:
        return [MockSkill(f"{prefix}_{i}", f"{prefix.title()} Skill {i+1}") for i in range(count)]

    skill_categories = [
        MockCat("Outfield Skills", _skills("out", 19)),
        MockCat("Set Pieces", _skills("set", 3)),
        MockCat("Mental Skills", _skills("men", 14)),
        MockCat("Physical Attributes", _skills("phy", 8)),
    ]

    position_nodes: list = []
    primary_pos_label: str | None = None
    secondary_pos_labels: list = []

    if show_posmap and position != "Unknown":
        primary_pos_label = position
        secondary_pos_labels = ["RB", "LCM"]
        position_nodes = [{"label": position, "x": 50, "y": 30, "primary": True}]

    initials = "".join(p[0].upper() for p in player_name.split()[:2])

    ctx = dict(
        player=player,
        portrait_photo_url=photo_url,
        overall=overall,
        tier_label=tier_label,
        tier_color=tier_color,
        pos_color=pos_color,
        initials=initials,
        skill_categories=skill_categories,
        last_skill_delta={},
        position_nodes=position_nodes,
        primary_pos_label=primary_pos_label,
        secondary_pos_labels=secondary_pos_labels,
        player_height_cm=height_cm,
        player_weight_kg=weight_kg,
        license_current_level=current_level,
        theme="default",
        animated_mode=False,
        _driver_config={"show_position_map": show_posmap, "skill_slice": None},
    )
    return tmpl.render(**ctx)


# ── Playwright export ─────────────────────────────────────────────────────────

from playwright.sync_api import sync_playwright

W, H = 1080, 1350

def _screenshot(html: str, out_path: Path) -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H})
        page.set_content(html, wait_until="networkidle")
        page.screenshot(path=str(out_path), clip={"x": 0, "y": 0, "width": W, "height": H})
        browser.close()

def _measure(html: str) -> dict:
    """Measure key zone bounding boxes and spacing quality for v3.2."""
    selectors = {
        "split_hero":      ".ex-split-hero",
        "photo_panel":     ".ex-photo-panel",
        "info_panel":      ".ex-info-panel",
        "photo_name":      ".ex-photo-name",
        "ovr_block":       ".ex-ovr-num",
        "tier_badge":      ".ex-tier-badge",
        "meta_list":       ".ex-meta-list",
        "info_spacer":     ".ex-info-spacer",
        "posmap_inline":   ".ex-posmap-inline",
        "pos_labels_row":  ".ex-pos-labels-row",
        "skills_zone":     ".ex-skills-zone",
        "col_left":        ".ex-skills-col-left",
        "col_mid":         ".ex-skills-col-mid",
        "col_right":       ".ex-skills-col-right",
        "cat_outfield":    ".ex-cat-outfield .ex-cat-name",
        "cat_mental":      ".ex-cat-mental .ex-cat-name",
        "cat_sets":        ".ex-cat-sets .ex-cat-name",
        "cat_phys":        ".ex-cat-phys .ex-cat-name",
    }
    result: dict = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H})
        page.set_content(html, wait_until="networkidle")
        for key, sel in selectors.items():
            el = page.query_selector(sel)
            if el:
                box = el.bounding_box()
                result[key] = {k: round(v, 1) for k, v in box.items()} if box else None
            else:
                result[key] = None
        rows = page.query_selector_all(".ex-row")
        heights = [round(r.bounding_box()["height"], 1) for r in rows[:5] if r.bounding_box()]
        result["row_heights_sample"] = heights
        result["total_row_count"] = len(rows)
        browser.close()
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    scenarios: list[dict] = []

    print("instagram_portrait — PORT-v2 — 1080×1350 — Split Hero v3.2 — QA Export v4")
    print("=" * 72)

    for sc_id, (photo_url, description) in PHOTO_SCENARIOS.items():
        print(f"  {sc_id}: {description} ...", end="", flush=True)
        html = _render_html(photo_url=photo_url)
        html_path = OUT_DIR / f"{sc_id}.html"
        png_path  = OUT_DIR / f"{sc_id}.png"
        html_path.write_text(html, encoding="utf-8")
        _screenshot(html, png_path)
        print(" OK")
        scenarios.append({"id": sc_id, "description": description,
                           "html": str(html_path), "png": str(png_path)})

    print("  pc7: No photo (placeholder initials) ...", end="", flush=True)
    html = _render_html(photo_url=None)
    (OUT_DIR / "pc7.html").write_text(html, encoding="utf-8")
    _screenshot(html, OUT_DIR / "pc7.png")
    print(" OK")
    scenarios.append({"id": "pc7", "description": "No photo — initials placeholder",
                      "html": str(OUT_DIR / "pc7.html"), "png": str(OUT_DIR / "pc7.png")})

    print("  pc8: Unknown position (no PosMap, no labels) ...", end="", flush=True)
    html = _render_html(photo_url=PHOTO_SCENARIOS["pc1"][0], position="Unknown", show_posmap=False)
    (OUT_DIR / "pc8.html").write_text(html, encoding="utf-8")
    _screenshot(html, OUT_DIR / "pc8.png")
    print(" OK")
    scenarios.append({"id": "pc8", "description": "Unknown position — no PosMap",
                      "html": str(OUT_DIR / "pc8.html"), "png": str(OUT_DIR / "pc8.png")})

    # ── Zone measurements (pc1 = with photo + posmap; pc7 = no photo; pc8 = no posmap) ──
    print("\nMeasuring zones (pc1 = posmap present, pc8 = posmap absent)...")
    metrics_pc1 = _measure((OUT_DIR / "pc1.html").read_text(encoding="utf-8"))
    metrics_pc8 = _measure((OUT_DIR / "pc8.html").read_text(encoding="utf-8"))

    print("\nSplit Hero v3.2 — Zone validation:")
    hero  = metrics_pc1.get("split_hero")
    phot  = metrics_pc1.get("photo_panel")
    info  = metrics_pc1.get("info_panel")
    posm  = metrics_pc1.get("posmap_inline")
    skill = metrics_pc1.get("skills_zone")
    spacer = metrics_pc1.get("info_spacer")
    ovr   = metrics_pc1.get("ovr_block")
    meta  = metrics_pc1.get("meta_list")

    if hero:  print(f"  Split Hero       h={hero['height']}px  (expected: 560px)  {'✅' if abs(hero['height']-560)<=2 else '❌'}")
    if phot:  print(f"  Photo panel      w={phot['width']}px   (expected: 560px)  {'✅' if abs(phot['width']-560)<=4 else '❌'}")
    if info:  print(f"  Info panel       w={info['width']}px   (expected: ~520px)")
    if ovr:   print(f"  OVR block        h={ovr['height']}px  y={ovr['y']}  (top of info col)")
    if meta:  print(f"  Meta list        h={meta['height']}px  y={meta['y']}")
    if spacer: print(f"  Info spacer      h={spacer['height']}px  (breathing room — want ≥12px)  {'✅' if spacer['height']>=12 else '⚠️'}")
    if posm:  print(f"  PosMap inline    h={posm['height']}px  y={posm['y']}  (want ~138px)  {'✅' if abs(posm['height']-138)<=6 else '⚠️'}")
    if skill: print(f"  Skills zone      h={skill['height']}px  y={skill['y']}  (want ≥780px)  {'✅' if skill['height']>=780 else '⚠️'}")

    print("\nNo-PosMap scenario (pc8 — Unknown position):")
    posm_pc8   = metrics_pc8.get("posmap_inline")
    spacer_pc8 = metrics_pc8.get("info_spacer")
    print(f"  posmap_inline: {'absent ✅' if posm_pc8 is None else f'PRESENT ❌  {posm_pc8}'}")
    if spacer_pc8: print(f"  info spacer h={spacer_pc8['height']}px (absorbs freed space)")

    row_heights = metrics_pc1.get("row_heights_sample", [])
    total_rows  = metrics_pc1.get("total_row_count", 0)
    print(f"\nSkill rows: total={total_rows}  (expected: 44)  {'✅' if total_rows==44 else '❌'}")
    if row_heights:
        variation = max(row_heights) - min(row_heights)
        print(f"  Sample heights: {row_heights}")
        print(f"  Variation: {variation}px  {'✅ uniform' if variation <= 2 else '⚠️ NOT uniform'}")

    col_l = metrics_pc1.get("col_left")
    col_m = metrics_pc1.get("col_mid")
    col_r = metrics_pc1.get("col_right")
    print(f"\n3-column layout:")
    if col_l: print(f"  Left  (Outfield):      w={col_l['width']}px  (target: 480px)")
    if col_m: print(f"  Mid   (Mental):        w={col_m['width']}px  (target: 260px)")
    if col_r: print(f"  Right (Sets+Physical): w={col_r['width']}px  (flex:1)")

    # ── Canonical metrics JSON ─────────────────────────────────────────────────
    metrics_out = {
        "platform":    "instagram_portrait — PORT-v2 — 1080×1350",
        "version":     "PORT-v2",
        "design":      "Split Hero v3.2",
        "canvas":      {"width": W, "height": H},
        "date":        "2026-05-18",
        "reference":   "pc1 (with photo + posmap)",
        "measured_zones": {
            "split_hero":    hero,
            "photo_panel":   phot,
            "info_panel":    info,
            "ovr_block":     ovr,
            "meta_list":     meta,
            "info_spacer":   spacer,
            "posmap_inline": posm,
            "skills_zone":   skill,
            "col_left":      col_l,
            "col_mid":       col_m,
            "col_right":     col_r,
        },
        "invariants": {
            "split_hero_h":         hero["height"] if hero else None,
            "photo_panel_w":        phot["width"]  if phot else None,
            "posmap_inline_h":      posm["height"] if posm else None,
            "skills_zone_h":        skill["height"] if skill else None,
            "total_skill_rows":     total_rows,
            "row_height_uniform":   (max(row_heights) - min(row_heights) <= 2) if row_heights else None,
            "row_height_variation": (max(row_heights) - min(row_heights)) if row_heights else None,
            "row_height_sample":    row_heights,
            "info_spacer_h":        spacer["height"] if spacer else None,
        },
        "no_posmap_scenario": {
            "posmap_inline_present": posm_pc8 is not None,
            "info_spacer_h":         spacer_pc8["height"] if spacer_pc8 else None,
        },
    }
    metrics_path = OUT_DIR / "metrics_baseline_port_v2_1080x1350.json"
    metrics_path.write_text(json.dumps(metrics_out, indent=2), encoding="utf-8")
    print(f"\n  Saved: {metrics_path.name}")

    # ── SHA-256 manifest ───────────────────────────────────────────────────────
    print("\nGenerating SHA-256 manifest...")
    manifest: dict = {}
    for sc in scenarios:
        p = Path(sc["png"])
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        manifest[sc["id"]] = {"description": sc["description"], "sha256": sha,
                               "size_bytes": p.stat().st_size}
    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  Saved: {manifest_path.name}")

    print("\nGenerating contact sheet...")
    _make_contact_sheet(scenarios)

    print("\n" + "=" * 72)
    print("instagram_portrait — PORT-v2 — 1080×1350 — Split Hero v3.2 — QA EXPORT v4 COMPLETE")
    print(f"Output: {OUT_DIR}")
    for sc in scenarios:
        sha = manifest[sc["id"]]["sha256"][:12]
        print(f"  {sc['id']}: {sc['description'][:56]:<56}  sha={sha}")


def _make_contact_sheet(scenarios: list[dict]) -> None:
    try:
        from PIL import Image
        cols, thumb_w, thumb_h = 2, 540, 675
        rows = math.ceil(len(scenarios) / cols)
        sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (15, 15, 25))
        for i, sc in enumerate(scenarios):
            img = Image.open(sc["png"]).convert("RGB")
            img = img.resize((thumb_w, thumb_h), Image.LANCZOS)
            sheet.paste(img, ((i % cols) * thumb_w, (i // cols) * thumb_h))
        out = OUT_DIR / "contact_sheet_port_v2_1080x1350.png"
        sheet.save(str(out), optimize=True)
        print(f"  Saved: contact_sheet_port_v2_1080x1350.png ({out.stat().st_size // 1024}KB)")
    except ImportError:
        imgs = "".join(
            f'<div style="float:left;width:50%;box-sizing:border-box;padding:4px">'
            f'<img src="{Path(sc["png"]).name}" style="width:100%">'
            f'<p style="font:11px sans-serif;color:#aaa;margin:2px 0">{sc["id"]}: {sc["description"]}</p>'
            f'</div>'
            for sc in scenarios
        )
        out = OUT_DIR / "contact_sheet_port_v2_1080x1350.html"
        out.write_text(f'<!DOCTYPE html><html><body style="background:#0f0f19;margin:0">{imgs}</body></html>', encoding="utf-8")
        print(f"  Saved: contact_sheet_port_v2_1080x1350.html (PIL not available)")


if __name__ == "__main__":
    main()
