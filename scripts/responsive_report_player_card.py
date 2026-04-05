"""
Player Card — Responsive Layout Report
=======================================
Prints a text-based report of layout parameters at each CSS breakpoint.

Usage:
    python scripts/responsive_report_player_card.py
"""

BREAKPOINTS = [
    {"label": "Large Desktop",   "width": 1440, "min_width": 768,  "max_width": None},
    {"label": "Medium Desktop",  "width": 1024, "min_width": 768,  "max_width": None},
    {"label": "Small Desktop",   "width": 860,  "min_width": 768,  "max_width": None},
    {"label": "Tablet landscape","width": 720,  "min_width": None, "max_width": 767},
    {"label": "Tablet portrait", "width": 600,  "min_width": None, "max_width": 559},
    {"label": "Phone landscape", "width": 500,  "min_width": None, "max_width": 559},
    {"label": "Phone portrait",  "width": 400,  "min_width": None, "max_width": 439},
    {"label": "Small phone",     "width": 360,  "min_width": None, "max_width": 439},
    {"label": "Tiny phone",      "width": 320,  "min_width": None, "max_width": 339},
]

# CSS-derived constants per breakpoint
def card_params(screen_w: int) -> dict:
    """Compute key layout metrics from the CSS rules."""

    # ── Breakpoint selection ───────────────────────────────────────────────
    if screen_w >= 768:
        # @media (min-width: 768px)
        card_max   = min(960, screen_w - 32)   # max-width: min(960px, 100vw - 2rem)
        left_w     = 200
        avatar     = 82
        overall_fs = 3.2
        name_fs    = 1.75
        right_pad  = 24   # 1.5rem each side
        skill_pad  = 24   # 1.5rem each side (L + R)
        cat_pad_lr = 13.6 # 0.85rem each side
        cats_gap   = 12.8 # 0.8rem
        cat_fs     = 0.62
        skill_fs   = 0.68
        skill_bar  = 52
        skill_val  = 30
        n_skill_cols = 4
        skill_wrap = "allowed"
    elif screen_w <= 440:
        # @media (max-width: 440px) – stacked header
        card_max   = screen_w - 12
        left_w     = screen_w - 12  # full width stacked
        avatar     = 52
        overall_fs = 2.4
        name_fs    = 1.2
        right_pad  = 16
        skill_pad  = 14.4
        cat_pad_lr = 10.4
        cats_gap   = 10.4
        cat_fs     = 0.58
        skill_fs   = 0.62
        skill_bar  = 36
        skill_val  = 28
        n_skill_cols = 2
        skill_wrap = "nowrap"
    elif screen_w <= 560:
        # @media (max-width: 560px)
        card_max   = screen_w - 8
        left_w     = 130
        avatar     = 58
        overall_fs = 2.3
        name_fs    = 1.2
        right_pad  = 16
        skill_pad  = 14.4
        cat_pad_lr = 10.4
        cats_gap   = 10.4
        cat_fs     = 0.58
        skill_fs   = 0.62
        skill_bar  = 36
        skill_val  = 28
        n_skill_cols = 2
        skill_wrap = "nowrap"
    elif screen_w >= 561:
        # 561px – 767px: base CSS + wrapping enabled via min-width:561px rule
        card_max   = min(960, screen_w - 32)
        left_w     = 170
        avatar     = 68
        overall_fs = 2.8
        name_fs    = 1.45
        right_pad  = 20
        skill_pad  = 17.6
        cat_pad_lr = 10.4
        cats_gap   = 10.4
        cat_fs     = 0.58
        skill_fs   = 0.62
        skill_bar  = 36
        skill_val  = 28
        n_skill_cols = 4
        skill_wrap = "allowed"   # @media (min-width: 561px) enables wrapping
    else:
        # ≤560px: fallback base CSS (also covered by mobile breakpoints below)
        card_max   = screen_w - 12
        left_w     = 170
        avatar     = 68
        overall_fs = 2.8
        name_fs    = 1.45
        right_pad  = 20
        skill_pad  = 17.6
        cat_pad_lr = 10.4
        cats_gap   = 10.4
        cat_fs     = 0.58
        skill_fs   = 0.62
        skill_bar  = 36
        skill_val  = 28
        n_skill_cols = 4
        skill_wrap = "nowrap"

    # ── Derived metrics ────────────────────────────────────────────────────
    card_w       = card_max
    skills_inner = card_w - 2 * skill_pad
    cat_w        = (skills_inner - (n_skill_cols - 1) * cats_gap) / n_skill_cols
    cat_inner    = cat_w - 2 * cat_pad_lr

    # Skill row fixed widths: bar + val + delta(~10px) + 3 gaps(0.35rem*3=16.8px)
    row_fixed    = skill_bar + skill_val + 10 + 16.8
    skill_name_w = max(0, cat_inner - row_fixed)

    # Char fit: at given font-size (rem → px at 16px base), ~0.6 char-width ratio
    fs_px        = skill_fs * 16
    chars_fit    = skill_name_w / (fs_px * 0.6) if fs_px > 0 else 0

    return {
        "card_w":       round(card_w),
        "left_w":       left_w,
        "right_w":      round(card_w - left_w),
        "avatar":       avatar,
        "overall_fs":   overall_fs,
        "name_fs":      name_fs,
        "n_skill_cols": n_skill_cols,
        "cat_inner":    round(cat_inner),
        "skill_name_w": round(skill_name_w),
        "chars_fit":    round(chars_fit),
        "skill_bar":    skill_bar,
        "skill_fs":     skill_fs,
        "skill_wrap":   skill_wrap,
    }


def bar_chars(val: int, total: int, width: int = 20) -> str:
    filled = round(val / total * width)
    return "█" * filled + "░" * (width - filled)


def main():
    sep = "─" * 78
    wide_sep = "═" * 78

    print()
    print(wide_sep)
    print("  Player Card — Responsive Layout Report")
    print("  CSS breakpoints: ≥768px (desktop) / ≤560px / ≤440px / ≤340px")
    print(wide_sep)

    for bp in BREAKPOINTS:
        w = bp["width"]
        p = card_params(w)

        print()
        print(f"  ┌─ {bp['label']:25s} (screen: {w}px) {'─'*(31 - len(bp['label']))}")
        print(f"  │  Card width       : {p['card_w']}px  (max-width: {'960px' if w>=768 else '680px'})")
        print(f"  │  Left panel       : {p['left_w']}px    Right panel: {p['right_w']}px")
        print(f"  │  Avatar           : {p['avatar']}×{p['avatar']}px   Overall: {p['overall_fs']}rem   Name: {p['name_fs']}rem")
        print(f"  │  Skill columns    : {p['n_skill_cols']}  │  Col inner width: {p['cat_inner']}px")
        print(f"  │  Skill name space : {p['skill_name_w']}px  "
              f"(~{p['chars_fit']} chars @ {p['skill_fs']}rem)  "
              f"wrap={p['skill_wrap']}")

        # Visual skill-name fit indicator
        names_to_check = [
            ("Ball Control",     12),
            ("Dribbling",        9),
            ("Sprint Speed",     12),
            ("Tactical Awareness", 18),
        ]
        fits = []
        for name, chars in names_to_check:
            if p["skill_wrap"] == "allowed":
                fits.append(f"  ✓ \"{name}\"")
            elif p["chars_fit"] >= chars:
                fits.append(f"  ✓ \"{name}\"")
            else:
                truncated = name[:max(1, int(p['chars_fit']))] + "…"
                fits.append(f"  ✗ \"{name}\" → \"{truncated}\"")
        print(f"  │  Sample skill names:")
        for f in fits:
            print(f"  │    {f}")

        # Mini layout diagram
        card_visual_w = 60
        left_pct  = int(p['left_w'] / p['card_w'] * card_visual_w) if p['card_w'] > 0 else 20
        right_pct = card_visual_w - left_pct
        col_visual = max(1, card_visual_w // p['n_skill_cols'] - 1)
        skill_row = "|".join(["─" * col_visual] * p['n_skill_cols'])
        print(f"  │")
        print(f"  │  ┌{'─'*left_pct}┬{'─'*right_pct}┐")
        print(f"  │  │{'LEFT':^{left_pct}}│{'RIGHT (name, identity, clubs)':^{right_pct}}│")
        print(f"  │  │{'avatar':^{left_pct}}│{'':^{right_pct}}│")
        print(f"  │  └{'─'*left_pct}┴{'─'*right_pct}┘")
        print(f"  │  ├── Skills ({p['n_skill_cols']} cols) ─{'─'*50}┤")
        print(f"  │  │  {skill_row}  │")
        print(f"  └{'─'*77}")

    print()
    print(wide_sep)
    print("  Summary")
    print(wide_sep)
    print(f"  {'Screen':20s} {'Card':8s} {'Skill cols':12s} {'Name space':12s} {'Wrap':8s} {'Ball Control':14s}")
    print(f"  {'─'*20} {'─'*8} {'─'*12} {'─'*12} {'─'*8} {'─'*14}")
    for bp in BREAKPOINTS:
        w = bp["width"]
        p = card_params(w)
        ball_ctrl_ok = p["skill_wrap"] == "allowed" or p["chars_fit"] >= 12
        status = "✅ visible" if ball_ctrl_ok else f"✗ ~{p['chars_fit']}ch"
        print(f"  {bp['label']:20s} {str(p['card_w'])+'px':8s} {str(p['n_skill_cols'])+'-col':12s} "
              f"{str(p['skill_name_w'])+'px':12s} {p['skill_wrap']:8s} {status}")
    print()
    print("  Legend: ✅ = fully readable  ✗ = truncated (only affects phones <560px)")
    print(wide_sep)
    print()


if __name__ == "__main__":
    main()
