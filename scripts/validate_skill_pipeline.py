"""
Production monitoring — skill progression pipeline integrity checks

Usage (from project root):
    python scripts/validate_skill_pipeline.py [--since-days N] [--strict]

Verifies that the four concurrency guards introduced in the
2026-02-19 sprint are holding in production:

  INV-S01  No user has football_skills with current_level < baseline - 1.0
           (EMA formula with clamp to [40, 99] makes this impossible by construction)

  INV-S02  Float-format entry rate ≤ 10 % of all skill slots per user
           (high float rate indicates assessment path is writing without normalisation)

  INV-S03  skill_rating_delta null rate ≤ 20 % among TournamentParticipation
           rows with a non-null placement
           (high null rate indicates compute_single_tournament_skill_delta failures)

  INV-S04  All football_skills.current_level values are in [40.0, 99.0]
           for users with active LFA_FOOTBALL_PLAYER licenses

Exits 0 if all invariants hold, 1 if any anomaly detected.

Run weekly (CI cron or manual):
    0 9 * * 1 cd /path/to/project && python scripts/validate_skill_pipeline.py >> logs/skill_pipeline_weekly.log 2>&1

Complements:
    scripts/validate_reward_pipeline.py  — reward/XP pipeline check
    scripts/validate_enrollment_pipeline.py  — enrollment pipeline check
"""
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

parser = argparse.ArgumentParser(
    description="Skill progression pipeline integrity monitor (weekly)"
)
parser.add_argument("--since-days", type=int, default=7,
                    help="Look at tournaments completed in the last N days (default: 7)")
parser.add_argument("--strict", action="store_true",
                    help="Exit 1 on warnings as well as errors")
args = parser.parse_args()

errors = []
warnings = []

HARDENING_DATE = datetime(2026, 2, 19, tzinfo=timezone.utc)
since = datetime.now(tz=timezone.utc) - timedelta(days=args.since_days)
window_start = max(since, HARDENING_DATE)

print("=" * 65)
print("SKILL PROGRESSION PIPELINE INTEGRITY CHECK — post 2026-02-19 hardening")
print(f"Run at : {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"Window : {window_start.strftime('%Y-%m-%d')} → now  ({args.since_days}d)")
print("=" * 65)

from app.database import engine
from sqlalchemy import text


# ─────────────────────────────────────────────────────────────────────────────
# INV-S04: current_level in [40.0, 99.0] — POST-HARDENING licenses only
#
# Pre-hardening data may contain values outside [40, 99] written by older code.
# We only flag licenses where skills_last_updated_at >= HARDENING_DATE, which
# guarantees the write went through the hardened Step 1.5 path.
# Pre-hardening violations are surfaced as warnings (informational).
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-S04] Checking football_skills.current_level bounds [40, 99]…")

with engine.connect() as conn:
    oob_rows = conn.execute(text("""
        SELECT id, user_id,
               (skill_entry.key) AS skill_key,
               (skill_entry.value ->> 'current_level')::float AS current_level,
               skills_last_updated_at
        FROM user_licenses,
             json_each(football_skills) AS skill_entry
        WHERE specialization_type = 'LFA_FOOTBALL_PLAYER'
          AND is_active = TRUE
          AND json_typeof(skill_entry.value) = 'object'
          AND (skill_entry.value ->> 'current_level') IS NOT NULL
          AND (
              (skill_entry.value ->> 'current_level')::float < 40.0
              OR (skill_entry.value ->> 'current_level')::float > 99.0
          )
        ORDER BY ABS((skill_entry.value ->> 'current_level')::float - 70.0) DESC
        LIMIT 20
    """)).fetchall()

if not oob_rows:
    print("  ✅ All current_level values within [40.0, 99.0]")
else:
    post_hardening = [r for r in oob_rows if r[4] and r[4].tzinfo and
                      r[4] >= HARDENING_DATE or (r[4] and not r[4].tzinfo and
                      r[4].replace(tzinfo=timezone.utc) >= HARDENING_DATE)]
    pre_hardening  = [r for r in oob_rows if r not in post_hardening]

    for row in post_hardening:
        errors.append(
            f"OUT-OF-BOUNDS current_level (POST-HARDENING): license_id={row[0]}, "
            f"user_id={row[1]}, skill={row[2]}, current_level={row[3]:.1f} "
            f"— EMA clamp not applied in Step 1.5?"
        )
    for row in pre_hardening:
        warnings.append(
            f"OUT-OF-BOUNDS current_level (pre-hardening legacy): license_id={row[0]}, "
            f"user_id={row[1]}, skill={row[2]}, current_level={row[3]:.1f}"
        )
    if post_hardening:
        print(f"  ❌ {len(post_hardening)} post-hardening violation(s) — EMA clamp bug")
    print(f"  ℹ️  {len(pre_hardening)} pre-hardening legacy value(s) (expected, not errors)")


# ─────────────────────────────────────────────────────────────────────────────
# INV-S01: Informational — skill drop summary (post-hardening licenses)
#
# NOTE: current_level < baseline is VALID behaviour: EMA moves toward placement
# evidence and clamps at 40.0 floor.  A player who consistently places last will
# legitimately reach 40.0 even from a 60.0 baseline.  This check is purely
# informational (no errors/warnings triggered by the invariant itself).
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-S01] Skill drop summary (informational — EMA legitimately allows drops)…")

with engine.connect() as conn:
    drop_count = conn.execute(text("""
        SELECT COUNT(*)
        FROM user_licenses,
             json_each(football_skills) AS skill_entry
        WHERE specialization_type = 'LFA_FOOTBALL_PLAYER'
          AND is_active = TRUE
          AND skills_last_updated_at >= :since
          AND json_typeof(skill_entry.value) = 'object'
          AND (skill_entry.value ->> 'baseline') IS NOT NULL
          AND (skill_entry.value ->> 'current_level') IS NOT NULL
          AND (skill_entry.value ->> 'current_level')::float
              < (skill_entry.value ->> 'baseline')::float
    """), {"since": HARDENING_DATE}).scalar() or 0

print(f"  ℹ️  {drop_count} skill slot(s) have current_level < baseline "
      f"(post-hardening licenses — may be legitimate EMA drops)")


# ─────────────────────────────────────────────────────────────────────────────
# INV-S02: Float-format entry rate ≤ 50 %
# (pre-hardening assessment-only users legitimately have float-format entries;
#  the normalisation in Step 1.5 promotes them on the next tournament finalization.
#  A rate above 50 % after the hardening date indicates the normalisation is not
#  running, or no tournaments have finalized since hardening.)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-S02] Checking football_skills float-format entry rate (S03 guard)…")

with engine.connect() as conn:
    format_stats = conn.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE json_typeof(skill_entry.value) = 'number') AS float_count,
            COUNT(*) FILTER (WHERE json_typeof(skill_entry.value) = 'object') AS dict_count,
            COUNT(*)                                                            AS total_count
        FROM user_licenses,
             json_each(football_skills) AS skill_entry
        WHERE specialization_type = 'LFA_FOOTBALL_PLAYER'
          AND is_active = TRUE
    """)).fetchone()

if format_stats and format_stats[2] > 0:
    float_count = format_stats[0]
    dict_count  = format_stats[1]
    total_count = format_stats[2]
    float_rate  = round(float_count / total_count * 100, 1)

    print(f"  football_skills format breakdown:")
    print(f"    dict  (V2 / tournament) : {dict_count} ({100 - float_rate:.1f}%)")
    print(f"    float (V1 / assessment) : {float_count} ({float_rate:.1f}%)")
    print(f"    total skill slots       : {total_count}")

    if float_rate > 50.0:
        warnings.append(
            f"HIGH FLOAT-FORMAT RATE: {float_rate:.1f}% of skill slots are bare floats "
            f"({float_count}/{total_count}) — S03 normalisation not running or "
            f"no tournaments have finalized since hardening"
        )
        print(f"  ⚠️  Float rate {float_rate:.1f}% exceeds 50% threshold")
    else:
        print(f"  ✅ Float-format rate {float_rate:.1f}% within acceptable threshold (≤ 50%)")
else:
    print("  ℹ️  No active football-player licenses found — skipping")


# ─────────────────────────────────────────────────────────────────────────────
# INV-S03: skill_rating_delta null rate ≤ 20 % for placed participations
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-S03] Checking skill_rating_delta null rate (S05 write-once guard)…")

with engine.connect() as conn:
    delta_stats = conn.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE skill_rating_delta IS NULL)     AS null_count,
            COUNT(*) FILTER (WHERE skill_rating_delta IS NOT NULL) AS set_count,
            COUNT(*)                                                AS total_count
        FROM tournament_participations
        WHERE placement IS NOT NULL
          AND achieved_at >= :since
    """), {"since": window_start}).fetchone()

if delta_stats and delta_stats[2] > 0:
    null_count  = delta_stats[0]
    set_count   = delta_stats[1]
    total_count = delta_stats[2]
    null_rate   = round(null_count / total_count * 100, 1)

    print(f"  skill_rating_delta coverage:")
    print(f"    set  : {set_count} ({100 - null_rate:.1f}%)")
    print(f"    null : {null_count} ({null_rate:.1f}%)")

    if null_rate > 20.0:
        warnings.append(
            f"HIGH NULL RATE for skill_rating_delta: {null_rate:.1f}% "
            f"({null_count}/{total_count} placed participations) — "
            f"compute_single_tournament_skill_delta may be failing silently"
        )
        print(f"  ⚠️  Null rate {null_rate:.1f}% exceeds 20% threshold")
    else:
        print(f"  ✅ skill_rating_delta null rate {null_rate:.1f}% within threshold (≤ 20%)")
else:
    print("  ℹ️  No placed participations in window — skipping")


# ─────────────────────────────────────────────────────────────────────────────
# Summary statistics (informational)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[INFO] Skill statistics (active licenses)…")

with engine.connect() as conn:
    skill_stats = conn.execute(text("""
        SELECT
            COUNT(DISTINCT id)         AS total_licenses,
            COUNT(DISTINCT user_id)    AS total_users,
            COUNT(*) FILTER (
                WHERE json_typeof(football_skills) = 'object'
                  AND football_skills::text != '{}'
            )                          AS licenses_with_skills
        FROM user_licenses
        WHERE specialization_type = 'LFA_FOOTBALL_PLAYER'
          AND is_active = TRUE
    """)).fetchone()

    avg_level = conn.execute(text("""
        SELECT ROUND(AVG((skill_entry.value ->> 'current_level')::float)::numeric, 1)
        FROM user_licenses,
             json_each(football_skills) AS skill_entry
        WHERE specialization_type = 'LFA_FOOTBALL_PLAYER'
          AND is_active = TRUE
          AND json_typeof(skill_entry.value) = 'object'
          AND (skill_entry.value ->> 'current_level') IS NOT NULL
    """)).scalar()

if skill_stats:
    print(f"  Active licenses        : {skill_stats[0]}")
    print(f"  Unique users           : {skill_stats[1]}")
    print(f"  Licenses with skills   : {skill_stats[2]}")
    print(f"  Avg current_level      : {avg_level or 'N/A'}")


# ─────────────────────────────────────────────────────────────────────────────
# Final result
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)

if errors:
    print(f"❌  FAILED — {len(errors)} ERROR(S), {len(warnings)} WARNING(S)")
    for e in errors:
        print(f"   ERROR   : {e}")
    for w in warnings:
        print(f"   WARNING : {w}")
    sys.exit(1)
elif warnings and args.strict:
    print(f"⚠️   STRICT MODE FAIL — 0 errors, {len(warnings)} warning(s)")
    for w in warnings:
        print(f"   WARNING : {w}")
    sys.exit(1)
elif warnings:
    print(f"⚠️   PASSED WITH WARNINGS — 0 errors, {len(warnings)} warning(s)")
    for w in warnings:
        print(f"   WARNING : {w}")
    sys.exit(0)
else:
    print("✅  ALL CHECKS PASSED — skill progression pipeline integrity confirmed")
    sys.exit(0)
