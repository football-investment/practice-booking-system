"""
instagram_portrait — PORT-v2 — 1080×1350
QA Export Script v5  (Split Hero v3.2b — 2026-05-18)
=====================================================

Fix vs v4: posmap SVG height:auto → native 1.54:1 aspect, no slice clipping.
Split hero: 560 → 660px. Skills zone: ~790 → ~690px.

Scenarios: pc1..pc8 (same as v4).
Outputs to: qa_exports/portrait_v2/v5/
  - pc1..pc8 individual PNGs + HTMLs
  - contact_sheet_port_v2_1080x1350.png
  - manifest.json
  - metrics_baseline_port_v2_1080x1350.json
  - comparison_v32_vs_v32b.json  (v4 vs v5 delta)
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
OUT_DIR = PROJECT / "qa_exports" / "portrait_v2" / "v5"
V4_DIR  = PROJECT / "qa_exports" / "portrait_v2" / "v4"
OUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(PROJECT))

# ── PNG generator ─────────────────────────────────────────────────────────────

def _png_chunk(tag: bytes, data: bytes) -> bytes:
    c = struct.pack(">I", len(data)) + tag + data
    return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

def _make_gradient_png(w: int, h: int, top: tuple, bot: tuple) -> bytes:
    raw = bytearray()
    for y in range(h):
        t = y / max(h - 1, 1)
        r, g, b = [int(top[i] + (bot[i] - top[i]) * t) for i in range(3)]
        raw += b'\x00' + bytes([r, g, b] * w)
    comp = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (
        b'\x89PNG\r\n\x1a\n'
        + _png_chunk(b'IHDR', ihdr)
        + _png_chunk(b'IDAT', comp)
        + _png_chunk(b'IEND', b'')
    )

def _uri(top: tuple, bot: tuple, w: int = 200, h: int = 400) -> str:
    return f"data:image/png;base64,{base64.b64encode(_make_gradient_png(w, h, top, bot)).decode()}"

PHOTO_SCENARIOS = {
    "pc1": (_uri((210,170,130),(60,40,20)),  "Close-up face — skin-tone top, dark bottom"),
    "pc2": (_uri((195,155,115),(20,20,20)),  "Full-body — lighter top, very dark bottom"),
    "pc3": (_uri((50,50,70),(30,30,50)),     "Centered portrait — uniform dark background"),
    "pc4": (_uri((60,110,60),(20,60,20)),    "Off-center portrait — green pitch background"),
    "pc5": (_uri((220,220,230),(140,140,160)),"Light background — high-key, pale blue-grey"),
    "pc6": (_uri((18,18,28),(5,5,10)),       "Dark background — low-key, near-black"),
}

# ── Jinja2 renderer ───────────────────────────────────────────────────────────

from jinja2 import Environment, FileSystemLoader, select_autoescape

def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(PROJECT / "app" / "templates")),
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
    tmpl = _make_env().get_template("public/export/portrait/fifa.html")

    class MockPlayer:
        name = player_name; age_group = "U-19"; total_tournaments = 12; skills: dict = {}
        def __init__(self): self.nationality = nationality; self.position = position

    class MockSkill:
        def __init__(self, k, n): self.key = k; self.name_en = n

    class MockCat:
        def __init__(self, n, s): self.name = n; self.skills = s

    def _skills(p, c):
        return [MockSkill(f"{p}_{i}", f"{p.title()} Skill {i+1}") for i in range(c)]

    position_nodes, primary_pos_label, secondary_pos_labels = [], None, []
    if show_posmap and position != "Unknown":
        primary_pos_label = position
        secondary_pos_labels = ["RB", "LCM"]
        position_nodes = [{"label": position, "x": 50, "y": 30, "primary": True}]

    return tmpl.render(
        player=MockPlayer(),
        portrait_photo_url=photo_url,
        overall=overall, tier_label=tier_label, tier_color=tier_color, pos_color=pos_color,
        initials="".join(p[0].upper() for p in player_name.split()[:2]),
        skill_categories=[
            MockCat("Outfield Skills", _skills("out", 19)),
            MockCat("Set Pieces",      _skills("set",  3)),
            MockCat("Mental Skills",   _skills("men", 14)),
            MockCat("Physical Attributes", _skills("phy", 8)),
        ],
        last_skill_delta={},
        position_nodes=position_nodes,
        primary_pos_label=primary_pos_label,
        secondary_pos_labels=secondary_pos_labels,
        player_height_cm=height_cm, player_weight_kg=weight_kg,
        license_current_level=current_level,
        theme="default", animated_mode=False,
        _driver_config={"show_position_map": show_posmap, "skill_slice": None},
    )


# ── Playwright export + measurement ───────────────────────────────────────────

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
    """Full v3.2b measurement suite — zone boxes, SVG internals, clipping audit."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H})
        page.set_content(html, wait_until="networkidle")

        def box(sel):
            el = page.query_selector(sel)
            if not el: return None
            b = el.bounding_box()
            return {k: round(v, 1) for k, v in b.items()} if b else None

        result = {
            "split_hero":     box(".ex-split-hero"),
            "photo_panel":    box(".ex-photo-panel"),
            "info_panel":     box(".ex-info-panel"),
            "ovr_block":      box(".ex-ovr-num"),
            "tier_badge":     box(".ex-tier-badge"),
            "meta_list":      box(".ex-meta-list"),
            "info_spacer":    box(".ex-info-spacer"),
            "posmap_inline":  box(".ex-posmap-inline"),
            "pos_labels_row": box(".ex-pos-labels-row"),
            "skills_zone":    box(".ex-skills-zone"),
            "col_left":       box(".ex-skills-col-left"),
            "col_mid":        box(".ex-skills-col-mid"),
            "col_right":      box(".ex-skills-col-right"),
            "cat_outfield":   box(".ex-cat-outfield .ex-cat-name"),
            "cat_mental":     box(".ex-cat-mental .ex-cat-name"),
            "cat_sets":       box(".ex-cat-sets .ex-cat-name"),
            "cat_phys":       box(".ex-cat-phys .ex-cat-name"),
        }

        # SVG internals — the critical posmap audit
        svg_data = page.evaluate("""() => {
            const svgs = document.querySelectorAll('.ex-posmap-inline svg');
            return Array.from(svgs).map(svg => {
                const rect = svg.getBoundingClientRect();
                const vb = svg.viewBox.baseVal;
                const par = svg.preserveAspectRatio.baseVal;
                const parStr = svg.getAttribute('preserveAspectRatio');
                return {
                    viewBox_w: vb ? Math.round(vb.width) : null,
                    viewBox_h: vb ? Math.round(vb.height) : null,
                    preserveAspectRatio: parStr,
                    rendered_w: Math.round(rect.width),
                    rendered_h: Math.round(rect.height),
                    rendered_y: Math.round(rect.top),
                };
            });
        }""")
        result["svg_internals"] = svg_data

        # Clipping check: does any SVG content extend beyond its container?
        clip_check = page.evaluate("""() => {
            const container = document.querySelector('.ex-posmap-inline');
            if (!container) return {container_absent: true};
            const cRect = container.getBoundingClientRect();
            const svg = container.querySelector('svg');
            if (!svg) return {svg_absent: true};
            const sRect = svg.getBoundingClientRect();
            // Check all SVG child rects
            const children = svg.querySelectorAll('*');
            let maxBottom = 0, minTop = 9999;
            children.forEach(c => {
                const r = c.getBoundingClientRect();
                if (r.height > 0) {
                    maxBottom = Math.max(maxBottom, r.bottom);
                    minTop = Math.min(minTop, r.top);
                }
            });
            return {
                container_top:    Math.round(cRect.top),
                container_bottom: Math.round(cRect.bottom),
                svg_top:          Math.round(sRect.top),
                svg_bottom:       Math.round(sRect.bottom),
                content_top:      Math.round(minTop),
                content_bottom:   Math.round(maxBottom),
                clips_above: minTop < cRect.top,
                clips_below: maxBottom > cRect.bottom,
                overflow_above_px: Math.round(cRect.top - minTop),
                overflow_below_px: Math.round(maxBottom - cRect.bottom),
            };
        }""")
        result["posmap_clip_check"] = clip_check

        # Row count and uniformity
        rows = page.query_selector_all(".ex-row")
        heights = [round(r.bounding_box()["height"], 1) for r in rows[:5] if r.bounding_box()]
        result["row_heights_sample"] = heights
        result["total_row_count"] = len(rows)

        # Photo dominance: photo panel vs info panel area
        photo = result.get("photo_panel")
        info  = result.get("info_panel")
        if photo and info:
            photo_area = photo["width"] * photo["height"]
            info_area  = info["width"]  * info["height"]
            result["photo_info_area_ratio"] = round(photo_area / info_area, 3)

        browser.close()
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    scenarios: list[dict] = []
    print("instagram_portrait — PORT-v2 — 1080×1350 — Split Hero v3.2b — QA Export v5")
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

    for sc_id, desc in [("pc7", "No photo — initials placeholder"),
                        ("pc8", "Unknown position — no PosMap")]:
        print(f"  {sc_id}: {desc} ...", end="", flush=True)
        if sc_id == "pc7":
            html = _render_html(photo_url=None)
        else:
            html = _render_html(photo_url=PHOTO_SCENARIOS["pc1"][0],
                                position="Unknown", show_posmap=False)
        (OUT_DIR / f"{sc_id}.html").write_text(html, encoding="utf-8")
        _screenshot(html, OUT_DIR / f"{sc_id}.png")
        print(" OK")
        scenarios.append({"id": sc_id, "description": desc,
                           "html": str(OUT_DIR / f"{sc_id}.html"),
                           "png": str(OUT_DIR / f"{sc_id}.png")})

    # ── Full measurement suite ─────────────────────────────────────────────────
    print("\nMeasuring v3.2b zones (pc1 reference)...")
    metrics = _measure((OUT_DIR / "pc1.html").read_text(encoding="utf-8"))

    print("\nMeasuring no-posmap scenario (pc8)...")
    metrics_pc8 = _measure((OUT_DIR / "pc8.html").read_text(encoding="utf-8"))

    # ── Zone validation ────────────────────────────────────────────────────────
    print("\n" + "─" * 64)
    print("ZONE VALIDATION — v3.2b")
    print("─" * 64)

    hero  = metrics.get("split_hero")
    phot  = metrics.get("photo_panel")
    info  = metrics.get("info_panel")
    posm  = metrics.get("posmap_inline")
    skill = metrics.get("skills_zone")
    spc   = metrics.get("info_spacer")

    if hero:  print(f"  Split Hero    h={hero['height']}px  (target: 660px)  {'✅' if abs(hero['height']-660)<=2 else '❌'}")
    if phot:  print(f"  Photo Panel   w={phot['width']}px × h={phot['height']}px  {'✅' if abs(phot['width']-560)<=2 else '⚠️'}")
    if info:  print(f"  Info Panel    w={info['width']}px × h={info['height']}px")
    if spc:   print(f"  Info Spacer   h={spc['height']}px  (want ≥12px breathing room)  {'✅' if spc['height']>=12 else '⚠️'}")
    if posm:  print(f"  PosMap inline h={posm['height']}px  (auto-height from SVG)")
    if skill: print(f"  Skills Zone   h={skill['height']}px  (target: ~690px)  {'✅' if skill['height']>=680 else '⚠️'}")

    # ── PosMap SVG audit ───────────────────────────────────────────────────────
    print("\n" + "─" * 64)
    print("POSMAP SVG AUDIT")
    print("─" * 64)

    svgs = metrics.get("svg_internals", [])
    for s in svgs:
        vb_w, vb_h = s.get("viewBox_w"), s.get("viewBox_h")
        rw, rh = s.get("rendered_w"), s.get("rendered_h")
        par = s.get("preserveAspectRatio", "?")
        print(f"  viewBox:     {vb_w} × {vb_h}  (native ratio: {vb_w/vb_h:.3f}:1)" if vb_w and vb_h else "  viewBox: N/A")
        print(f"  rendered:    {rw} × {rh}px  (ratio: {rw/rh:.3f}:1)" if rw and rh else "  rendered: N/A")
        print(f"  preserveAR:  {par}")
        if vb_w and vb_h and rw and rh:
            native_ratio = vb_w / vb_h
            rendered_ratio = rw / rh
            ratio_match = abs(native_ratio - rendered_ratio) < 0.05
            print(f"  Ratio match: {'✅ native = rendered (no clipping)' if ratio_match else f'⚠️  MISMATCH native={native_ratio:.2f} rendered={rendered_ratio:.2f}'}")
            expected_h = rw * (vb_h / vb_w)
            print(f"  Expected h at {rw}px width: {expected_h:.1f}px — rendered: {rh}px  {'✅' if abs(expected_h-rh)<4 else '⚠️'}")

    clip = metrics.get("posmap_clip_check", {})
    print(f"\n  Clip check:")
    print(f"    container y={clip.get('container_top')}..{clip.get('container_bottom')}")
    print(f"    svg       y={clip.get('svg_top')}..{clip.get('svg_bottom')}")
    print(f"    content   y={clip.get('content_top')}..{clip.get('content_bottom')}")
    clips_above = clip.get("clips_above", False)
    clips_below = clip.get("clips_below", False)
    ov_above = clip.get("overflow_above_px", 0)
    ov_below = clip.get("overflow_below_px", 0)
    if not clips_above and not clips_below:
        print(f"    ✅ NO CLIPPING — pitch fully visible within container")
    else:
        if clips_above: print(f"    ⚠️  CLIPS ABOVE by {ov_above}px")
        if clips_below: print(f"    ⚠️  CLIPS BELOW by {ov_below}px")

    # ── Skills zone readability ────────────────────────────────────────────────
    print("\n" + "─" * 64)
    print("SKILLS ZONE READABILITY")
    print("─" * 64)

    rows_total = metrics.get("total_row_count", 0)
    row_h      = metrics.get("row_heights_sample", [])
    col_l = metrics.get("col_left")
    col_m = metrics.get("col_mid")
    col_r = metrics.get("col_right")

    print(f"  Total skill rows: {rows_total}  (expected: 44)  {'✅' if rows_total == 44 else '❌'}")
    if row_h:
        var = max(row_h) - min(row_h)
        print(f"  Row heights sample: {row_h}")
        print(f"  Height variation:   {var}px  {'✅ uniform' if var<=2 else '⚠️'}")
    if col_l: print(f"  Left  (Outfield):      w={col_l['width']}px  h={col_l['height']}px")
    if col_m: print(f"  Mid   (Mental):        w={col_m['width']}px  h={col_m['height']}px")
    if col_r: print(f"  Right (Sets+Physical): w={col_r['width']}px  h={col_r['height']}px")

    # Cat-name positions (sanity check: within skills zone)
    if skill and col_l:
        col_bottom = col_l["y"] + col_l["height"]
        skills_bottom = skill["y"] + skill["height"]
        print(f"  Skills zone bottom: y={skills_bottom:.0f}px  col_left bottom: y={col_bottom:.0f}px  {'✅' if col_bottom <= skills_bottom+2 else '⚠️'}")

    # ── Photo dominance ────────────────────────────────────────────────────────
    ratio = metrics.get("photo_info_area_ratio")
    if ratio:
        print(f"\n  Photo/Info area ratio: {ratio:.2f}  (>1 = photo dominates)  {'✅' if ratio >= 1.0 else '⚠️'}")

    # ── No-posmap scenario ─────────────────────────────────────────────────────
    posm_pc8 = metrics_pc8.get("posmap_inline")
    spc_pc8  = metrics_pc8.get("info_spacer")
    pc8_posmap_status = "absent ✅" if posm_pc8 is None else f"PRESENT ❌ h={posm_pc8['height']}px"
    print(f"\n  pc8 (no PosMap): posmap_inline={pc8_posmap_status}")
    if spc_pc8: print(f"  pc8 info_spacer: h={spc_pc8['height']}px (absorbs freed space)")

    # ── v3.2 vs v3.2b comparison ───────────────────────────────────────────────
    print("\n" + "─" * 64)
    print("COMPARISON: v3.2 (v4/) vs v3.2b (v5/)")
    print("─" * 64)
    v4_metrics_path = V4_DIR / "metrics_baseline_port_v2_1080x1350.json"
    if v4_metrics_path.exists():
        v4 = json.loads(v4_metrics_path.read_text())
        v4z = v4.get("measured_zones", {})
        v5z = metrics

        def compare(key, label, unit="px"):
            v4v = v4z.get(key)
            v5v = v5z.get(key)
            h4 = v4v["height"] if v4v else "N/A"
            h5 = v5v["height"] if v5v else "N/A"
            delta = (h5 - h4) if isinstance(h4, (int, float)) and isinstance(h5, (int, float)) else "?"
            sign = f"+{delta}" if isinstance(delta, (int, float)) and delta > 0 else str(delta)
            print(f"  {label:<22} v3.2={h4}{unit}  →  v3.2b={h5}{unit}  ({sign})")

        compare("split_hero",    "split_hero h")
        compare("posmap_inline", "posmap_inline h")
        compare("info_spacer",   "info_spacer h")
        compare("skills_zone",   "skills_zone h")

        # SVG comparison
        v4_svg = v4.get("invariants", {})
        print(f"\n  SVG clipping (v3.2):  pitch only 44% visible (127/290px)")
        posm_v5 = metrics.get("posmap_inline")
        svgs_v5 = metrics.get("svg_internals", [])
        if svgs_v5:
            s = svgs_v5[0]
            rh = s.get("rendered_h", 0)
            vb_h = s.get("viewBox_h", 68)
            rw = s.get("rendered_w", 0)
            vb_w = s.get("viewBox_w", 105)
            expected = rw * (vb_h / vb_w) if vb_w else 0
            visible_pct = (rh / expected * 100) if expected else 0
            print(f"  SVG clipping (v3.2b): pitch {visible_pct:.0f}% visible ({rh}/{expected:.0f}px)  {'✅ NO CLIPPING' if visible_pct >= 99 else '⚠️'}")
    else:
        print("  (v4 metrics not found — skipping comparison)")

    # ── Build canonical metrics JSON ───────────────────────────────────────────
    metrics_out = {
        "platform": "instagram_portrait — PORT-v2 — 1080×1350",
        "version": "PORT-v2", "design": "Split Hero v3.2b",
        "canvas": {"width": W, "height": H},
        "date": "2026-05-18", "reference": "pc1 (with photo + posmap)",
        "measured_zones": {k: metrics.get(k) for k in [
            "split_hero", "photo_panel", "info_panel", "ovr_block", "tier_badge",
            "meta_list", "info_spacer", "posmap_inline", "pos_labels_row",
            "skills_zone", "col_left", "col_mid", "col_right",
        ]},
        "posmap_svg_audit": {
            "svg_internals": metrics.get("svg_internals"),
            "clip_check":    metrics.get("posmap_clip_check"),
        },
        "invariants": {
            "split_hero_h":       hero["height"] if hero else None,
            "photo_panel_w":      phot["width"]  if phot else None,
            "posmap_inline_h":    posm["height"] if posm else None,
            "skills_zone_h":      skill["height"] if skill else None,
            "total_skill_rows":   rows_total,
            "row_height_uniform": (max(row_h) - min(row_h) <= 2) if row_h else None,
            "row_height_variation": (max(row_h) - min(row_h)) if row_h else None,
            "info_spacer_h":      spc["height"] if spc else None,
            "svg_clips_above":    clip.get("clips_above"),
            "svg_clips_below":    clip.get("clips_below"),
        },
        "no_posmap_scenario": {
            "posmap_inline_present": posm_pc8 is not None,
            "info_spacer_h":         spc_pc8["height"] if spc_pc8 else None,
        },
    }
    metrics_path = OUT_DIR / "metrics_baseline_port_v2_1080x1350.json"
    metrics_path.write_text(json.dumps(metrics_out, indent=2), encoding="utf-8")
    print(f"\n  Saved: {metrics_path.name}")

    # ── SHA-256 manifest ───────────────────────────────────────────────────────
    manifest: dict = {}
    for sc in scenarios:
        p = Path(sc["png"])
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        manifest[sc["id"]] = {"description": sc["description"], "sha256": sha,
                               "size_bytes": p.stat().st_size}
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  Saved: manifest.json")

    # ── Contact sheet ──────────────────────────────────────────────────────────
    _make_contact_sheet(scenarios)

    print("\n" + "=" * 72)
    print("instagram_portrait — PORT-v2 — 1080×1350 — Split Hero v3.2b — QA EXPORT v5 COMPLETE")
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
