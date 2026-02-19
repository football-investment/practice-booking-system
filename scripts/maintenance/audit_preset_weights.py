#!/usr/bin/env python3
"""
Preset Weight Consistency Audit
================================
Lists all game presets and audits their skill_weights for consistency.

Checks per preset:
  [OK]  has skill_weights (fractional, sum ≈ 1.0, no zero values)
  [1.0] no skill_weights → fallback to weight=1.0 each (expected for legacy presets)
  [WARN] skill_weights present but sum ≠ 1.0 (tolerance ±0.01)
  [WARN] skill_weights has zero or negative entries (degenerate)
  [WARN] skills_tested and skill_weights keys do not match

Exit codes:
  0 — all presets are [OK] or [1.0] (acceptable)
  1 — at least one [WARN] found (potential misconfiguration)

Usage:
    python scripts/maintenance/audit_preset_weights.py
    python scripts/maintenance/audit_preset_weights.py --db-url postgresql://...
"""

import sys
import os
import argparse
import math

# ── Bootstrap: allow running from project root without install ────────────────
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# ── ANSI colours (disabled on CI if NO_COLOR is set) ─────────────────────────
_use_colour = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(code: str, text_: str) -> str:
    return f"\033[{code}m{text_}\033[0m" if _use_colour else text_


OK    = _c("32", "  [OK] ")
BACK  = _c("36", " [1.0] ")
WARN  = _c("33", " [WARN]")
ERROR = _c("31", "[ERROR]")


def _get_db_url() -> str:
    """Resolve DATABASE_URL from environment or CLI."""
    parser = argparse.ArgumentParser(description="Audit preset skill weights")
    parser.add_argument(
        "--db-url",
        default=os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"),
        help="PostgreSQL connection URL (default: $DATABASE_URL or localhost/lfa_intern_system)",
    )
    args = parser.parse_args()
    return args.db_url


def _load_presets(session) -> list[dict]:
    rows = session.execute(
        text("""
            SELECT id, code, name, is_active, is_locked, game_config
            FROM game_presets
            ORDER BY id
        """)
    ).mappings().all()
    return [dict(r) for r in rows]


def _audit_preset(preset: dict) -> list[str]:
    """
    Returns a list of audit lines for this preset.
    Line format: f"{STATUS} {message}"
    """
    lines = []
    pid   = preset["id"]
    code  = preset["code"]
    name  = preset["name"]
    cfg   = preset.get("game_config") or {}
    hdr   = f"id={pid:<3}  {code:<35}  \"{name}\""

    skill_cfg   = cfg.get("skill_config", {})
    skills      = skill_cfg.get("skills_tested", [])
    weights     = skill_cfg.get("skill_weights", {})

    if not weights:
        # ── No skill_weights → fallback 1.0 path (expected for legacy presets) ─
        lines.append(f"{BACK} {hdr}")
        lines.append(
            f"        skills={len(skills)}  "
            f"→ no skill_weights → all TournamentSkillMapping.weight will be 1.0"
        )
        return lines

    # ── Has skill_weights — run consistency checks ────────────────────────────
    weight_sum  = sum(weights.values())
    sum_ok      = abs(weight_sum - 1.0) <= 0.01
    zero_vals   = [k for k, v in weights.items() if v <= 0]
    neg_vals    = [k for k, v in weights.items() if v < 0]
    skills_set  = set(skills)
    weights_set = set(weights.keys())
    missing_w   = skills_set - weights_set   # in skills_tested but no weight
    extra_w     = weights_set - skills_set   # in weights but not in skills_tested

    has_issues  = (not sum_ok) or zero_vals or neg_vals or missing_w or extra_w

    status = WARN if has_issues else OK
    lines.append(f"{status} {hdr}")

    # ── Weight table ──────────────────────────────────────────────────────────
    avg_w = weight_sum / len(weights) if weights else 1.0
    for skill_name, frac in sorted(weights.items(), key=lambda x: -x[1]):
        raw_react  = frac / avg_w if avg_w > 0 else 1.0
        react      = max(0.1, min(5.0, raw_react))
        clamped    = " ← CLAMPED" if abs(react - raw_react) > 0.001 else ""
        lines.append(
            f"        {skill_name:<30}  frac={frac:.4f}  reactivity={react:.2f}{clamped}"
        )

    # ── Summary line ──────────────────────────────────────────────────────────
    sum_marker = "" if sum_ok else f"  ← SUM={weight_sum:.4f} (expected 1.0±0.01)"
    lines.append(
        f"        skills={len(skills)}  weights={len(weights)}  "
        f"sum={weight_sum:.4f}{sum_marker}  avg_w={avg_w:.4f}"
    )

    # ── Issue details ─────────────────────────────────────────────────────────
    if zero_vals:
        lines.append(f"        {WARN}  Zero/negative weights: {zero_vals}")
    if missing_w:
        lines.append(f"        {WARN}  Skills with no weight entry: {sorted(missing_w)}")
    if extra_w:
        lines.append(f"        {WARN}  Weight keys not in skills_tested: {sorted(extra_w)}")

    return lines


def main() -> int:
    db_url = _get_db_url()
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)

    print()
    print("=" * 72)
    print("  GAME PRESET WEIGHT AUDIT")
    print(f"  DB: {db_url}")
    print("=" * 72)
    print()
    print("  Legend:")
    print(f"  {OK}  Weights present, sum ≈ 1.0, all checks pass")
    print(f"  {BACK}  No weights → fallback 1.0 each (legacy, acceptable)")
    print(f"  {WARN}  Configuration issue detected — review required")
    print()
    print("-" * 72)

    warnings_found = 0
    total = 0

    with Session() as session:
        presets = _load_presets(session)

        if not presets:
            print("  (no game presets found in database)")
            print()
            return 0

        ok_count  = 0
        back_count = 0

        for preset in presets:
            audit_lines = _audit_preset(preset)
            for line in audit_lines:
                print(line)
            print()

            first = audit_lines[0] if audit_lines else ""
            if "[WARN]" in first:
                warnings_found += 1
            elif "[1.0]" in first:
                back_count += 1
            else:
                ok_count += 1
            total += 1

    print("-" * 72)
    print()
    print(f"  Presets audited : {total}")
    print(f"  {OK}  OK          : {ok_count}")
    print(f"  {BACK}  Fallback 1.0: {back_count}")
    print(f"  {WARN}  Warnings    : {warnings_found}")
    print()

    if warnings_found:
        print(f"  ⚠️  {warnings_found} preset(s) have weight inconsistencies.")
        print("     Review the entries marked [WARN] above.")
        print("     Reactivity conversion at tournament creation will still")
        print("     proceed (create.py is defensive), but results may be")
        print("     mathematically unintended.")
        print()
        return 1
    else:
        print("  ✅ All presets pass the weight consistency check.")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
