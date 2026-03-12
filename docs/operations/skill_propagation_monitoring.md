# Skill Propagation Monitoring Checklist

> **Status**: ACTIVE — propagation live since 2026-03-12
> **Flag**: `ENABLE_TOURNAMENT_SKILL_PROPAGATION = True` (`app/config.py`)
> **Next phase**: enable `ENABLE_SKILL_TIER_NOTIFICATIONS` once stable data collected

---

## Overview

After every tournament reward distribution, `record_tournament_participation()` runs
three phases:

| Phase | What happens |
|-------|-------------|
| 1 | Upsert `TournamentParticipation` row (placement + XP + credits) |
| 2 | Compute V3 EMA skill delta via `compute_single_tournament_skill_delta()` |
| 3 | Write delta into `FootballSkillAssessment` rows via `update_skill_assessments()` |

This document covers monitoring Phase 3.

---

## Log Patterns

All log lines are emitted by `app.services.tournament.tournament_participation_service`.
Metric lines use the separate logger `app.metrics.skill_propagation`.

### Per-skill line (one per skill per player per tournament)

```
INFO skill_propagation skill=<name> user=<id> license=<id> old_pct=<n> delta=<±n> new_pct=<n> clamped=<True|False>
```

**Example — normal:**
```
INFO skill_propagation skill=dribbling user=42 license=7 old_pct=50.0 delta=+10.0 new_pct=60.0 clamped=False
INFO skill_propagation skill=passing user=42 license=7 old_pct=55.0 delta=+8.0 new_pct=63.0 clamped=False
```

**Example — clamped at upper bound:**
```
INFO skill_propagation skill=heading user=42 license=7 old_pct=97.0 delta=+10.0 new_pct=99.0 clamped=True
```

### Summary / metric line (once per player per tournament)

```
INFO skill_propagation_complete user=<id> license=<id> skills_written=<n>
```

**Example:**
```
INFO skill_propagation_complete user=42 license=7 skills_written=3
```

### Guard / skip lines

```
DEBUG update_skill_assessments: propagation disabled by flag (user=<id>)
DEBUG update_skill_assessments: no active LFA_FOOTBALL_PLAYER license for user=<id> — skipping
```

---

## Expected Delta Ranges

Deltas are computed by the V3 EMA formula. The key parameters:

| Parameter | Value |
|-----------|-------|
| Learning rate | 0.20 |
| Skill weight (typical) | 1.0 |
| EMA step at weight=1.0 | 0.20 × log(2)/log(2) = **0.20** |
| Baseline (no prior tournaments) | 50.0 |
| Hard floor / ceiling | 40.0 / 99.0 |

**Typical delta ranges by placement (solo tournament, weight=1.0):**

| Placement | Field size | Expected delta |
|-----------|-----------|---------------|
| 1st / 1 | 1 player | +10.0 (solo tournament) |
| 1st / 4 | 4 players | ~+8.5 to +10.0 |
| 2nd / 4 | 4 players | ~+3.0 to +6.0 |
| 3rd / 4 | 4 players | ~−2.0 to +1.0 |
| 4th / 4 | 4 players | ~−5.0 to −8.0 |

Opponent factor (ELO-inspired) adjusts these up (stronger field) or down (weaker field)
by up to ×2 / ÷2. Match performance modifier (win rate + score ratio) adjusts by
up to ±100% of the raw delta. Both are applied after the raw EMA step.

**Normal bounds:** `|delta| ≤ ~20` for any single tournament at standard weight=1.0.
Weighted skills (weight > 1.0) produce proportionally larger steps.

---

## Normal Behaviour Checklist

After each tournament reward distribution, verify:

- [ ] `skill_propagation_complete` line appears for **every rewarded player**
- [ ] `skills_written` matches the number of skills mapped to the tournament
      (check `TournamentSkillMapping` rows for that semester)
- [ ] All per-skill `delta` values fall within expected range for the placement
- [ ] No `clamped=True` lines unless player was already near 40 or 99
- [ ] `FootballSkillAssessment` rows visible for each player under the
      `/api/v1/lfa-player/{user_id}/assessments` endpoint

---

## Red Flags

### `skills_written=0` in metric line

**Meaning:** Phase 3 ran but wrote nothing.

**Causes and checks:**

| Cause | How to verify | Fix |
|-------|--------------|-----|
| No `TournamentSkillMapping` rows for this tournament | `SELECT * FROM tournament_skill_mappings WHERE semester_id = <id>` | Add skill mappings or populate `reward_config.skill_mappings` |
| All deltas computed as 0.0 | Check per-skill lines — delta=0.0 is skipped | Verify `TournamentParticipation.placement` is set (not NULL) |
| EMA replay found no participations | `SELECT * FROM tournament_participations WHERE user_id = <id>` | Participation must exist before Phase 3 runs; flush may have failed |

### `clamped=True` appearing frequently

**Meaning:** Players are repeatedly hitting the 40 or 99 boundary.

**Interpretation:**
- `new_pct=99.0 clamped=True` — elite player with no room to grow further; expected for top performers
- `new_pct=40.0 clamped=True` — persistent last-place results; expected for struggling players
- More than ~20% of lines showing `clamped=True` — review skill weight configuration; weights > 1.5 amplify steps significantly

### Large unexpected deltas (`|delta| > 20`)

**Causes:**
- Skill weight set abnormally high (> 2.0) in `TournamentSkillMapping` or `reward_config`
- Opponent factor hit upper bound (2.0) — player consistently facing much stronger field
- Check: `SELECT weight FROM tournament_skill_mappings WHERE semester_id = <id>`

### `no active LFA_FOOTBALL_PLAYER license` debug lines

**Meaning:** A non-LFA-Football-Player user received tournament rewards. Expected for
instructors, coaches, or students without this specialization. Not an error.

If seen for users who **should** have the license:
- `SELECT * FROM user_licenses WHERE user_id = <id> AND specialization_type = 'LFA_FOOTBALL_PLAYER'`
- Check `is_active` — license may have been deactivated or expired

---

## Troubleshooting Steps

### Step 1 — Confirm Phase 3 ran

```bash
# In application logs, search for the summary line for a specific user:
grep "skill_propagation_complete user=42" app.log

# Or search for any propagation activity in the last tournament window:
grep "skill_propagation" app.log | grep "2026-03-12"
```

### Step 2 — Verify DB state

```sql
-- Check TournamentParticipation has skill_rating_delta set
SELECT id, user_id, semester_id, placement, skill_rating_delta
FROM tournament_participations
WHERE semester_id = <tournament_id>
ORDER BY id;

-- Check FootballSkillAssessment rows were created
SELECT fsa.skill_name, fsa.percentage, fsa.status, fsa.notes, fsa.assessed_at
FROM football_skill_assessments fsa
JOIN user_licenses ul ON fsa.user_license_id = ul.id
WHERE ul.user_id = <user_id>
  AND fsa.status = 'ASSESSED'
ORDER BY fsa.assessed_at DESC
LIMIT 10;

-- Check archived assessments (confirms old rows were archived)
SELECT skill_name, percentage, status, archived_reason
FROM football_skill_assessments
WHERE user_license_id = <license_id>
  AND status = 'ARCHIVED'
  AND archived_reason LIKE 'tournament_progression_delta%'
ORDER BY archived_at DESC;
```

### Step 3 — Instant rollback if needed

Disable propagation without a code deploy:

```bash
# In .env or environment config:
ENABLE_TOURNAMENT_SKILL_PROPAGATION=false
```

Restart the application. All subsequent reward distributions will skip Phase 3.
Existing `FootballSkillAssessment` rows are unaffected.

### Step 4 — Manual re-run after fix

If propagation was disabled and rewards were distributed without Phase 3 running,
call `update_skill_assessments()` directly for each affected user via a migration
script, passing the stored `TournamentParticipation.skill_rating_delta`.

---

## Periodic Review (every 3–5 tournaments)

Run these checks after each batch of 3–5 tournaments to confirm thresholds remain reasonable.

### SQL — delta distribution

```sql
-- Distribution of skill_rating_delta values across recent participations
SELECT
    placement,
    COUNT(*)                                    AS players,
    ROUND(AVG((skill_rating_delta->>'dribbling')::numeric), 2) AS avg_delta,
    ROUND(MIN((skill_rating_delta->>'dribbling')::numeric), 2) AS min_delta,
    ROUND(MAX((skill_rating_delta->>'dribbling')::numeric), 2) AS max_delta
FROM tournament_participations
WHERE skill_rating_delta IS NOT NULL
  AND created_at >= NOW() - INTERVAL '90 days'
GROUP BY placement
ORDER BY placement;
```

**Healthy range:** average deltas match the expected range table in this doc (±20%).
If averages drift consistently above or below, review `LEARNING_RATE` in
`app/services/skill_progression_service.py`.

### SQL — clamped rate

```sql
-- Fraction of assessments that hit the 40/99 boundary
SELECT
    COUNT(*) FILTER (WHERE archived_reason LIKE 'tournament_progression_delta%') AS total_written,
    COUNT(*) FILTER (
        WHERE archived_reason LIKE 'tournament_progression_delta%'
          AND percentage IN (40.0, 99.0)
    )                                                                            AS clamped_count
FROM football_skill_assessments
WHERE status = 'ARCHIVED'
  AND archived_at >= NOW() - INTERVAL '90 days';
```

**Action threshold:** if `clamped_count / total_written > 0.20`, review skill weight
configuration — weights above 1.5 amplify steps significantly.

### Log — skills_written=0 frequency

```bash
grep "skill_propagation_complete" app.log | awk -F'skills_written=' '{print $2}' | sort | uniq -c
```

**Expected:** all entries show `skills_written >= 1` for LFA Football Player users.
Any `skills_written=0` line should be investigated (see Red Flags section above).

### Checklist (post-review)

- [ ] Average deltas match expected range table (±20% tolerance)
- [ ] Clamped rate ≤ 20% of all written assessments
- [ ] No unexplained `skills_written=0` lines in logs
- [ ] `|delta| > 20` occurrences — if any, verify `TournamentSkillMapping.weight` values
- [ ] Top-10 skill percentiles: confirm elite players approach 99.0, not plateau at 99.0 repeatedly

If all five pass → no tuning needed.
If any fail → log findings in a GitHub issue and tag `@football-investment/backend-leads`.

---

## Next Phase: Enabling Tier Notifications

Once 2–3 tournament cycles have been observed without anomalies:

1. Set `ENABLE_SKILL_TIER_NOTIFICATIONS = True` in `app/config.py`
2. Implement tier-crossing detection in `update_skill_assessments()`:
   - Compare `current_pct` and `new_pct` against tier thresholds
   - Emit a `Notification` row when a tier boundary is crossed
3. Run full test suite — expected baseline: 8932 passed, 1 xfailed

**Tier thresholds (reference):**

| Tier | Range |
|------|-------|
| Beginner | 40–49 |
| Developing | 50–64 |
| Competent | 65–74 |
| Proficient | 75–84 |
| Advanced | 85–92 |
| Elite | 93–99 |

---

## Alert Mechanism & Team Access

### How alerts reach the team

The `skill-propagation-review.yml` workflow (every Monday 07:00 UTC) exits 1
when an error invariant fires. GitHub converts a failed workflow run into:

1. **Email notification** — sent automatically to anyone subscribed to
   workflow notifications for this repository
   (`Settings → Notifications → GitHub Actions`).
2. **GitHub Actions badge** — red on the Actions tab; visible to all
   collaborators with at least Read access.
3. **Step summary + artifact** — full check report posted to the run summary
   and uploaded as a 90-day artifact (`skill-propagation-report-<run_number>`).

To receive email on **every** failed scheduled run:
> Repository → `Watch` → `Custom` → tick **Workflow runs** → `Apply`

### Team access checklist (run after onboarding a new member)

```bash
# 1. Confirm permission level (≥ read for ops, write for backend-leads):
gh api repos/football-investment/practice-booking-system/collaborators/<username>/permission \
  --jq '.permission'

# 2. List recent review runs:
gh run list --workflow=skill-propagation-review.yml --limit 5

# 3. Trigger a manual dry-run (1-day window — near-zero data, just validates plumbing):
gh workflow run skill-propagation-review.yml -f since_days=1 -f strict=false
gh run watch   # follow live output
```

### Smoke-testing the exit-1 alert path

```bash
# --strict promotes warnings to errors — confirms the escalation path is wired:
python scripts/validate_skill_propagation.py --since-days 90 --strict
# Expected: exits 1 if any INV-SP-02/04 warnings exist (normal with --strict).
# Remove --strict to restore production behaviour (errors-only).
```

### Audit trail for script/workflow modifications

Append a line to the `## Changelog` block at the top of each file before merging:

```
# YYYY-MM-DD  <what changed>  Author: <name>  Ref: <issue/PR link>
```

Files with changelog headers:
- `scripts/validate_skill_propagation.py`
- `.github/workflows/skill-propagation-review.yml`

No separate change-log document is needed — the header block is the audit trail.

---

## Related Files

| File | Role |
|------|------|
| `app/services/tournament/tournament_participation_service.py` | Phase 3 implementation (`update_skill_assessments`) |
| `app/services/skill_progression_service.py` | Phase 2 EMA computation (`compute_single_tournament_skill_delta`) |
| `app/models/football_skill_assessment.py` | Assessment lifecycle state machine |
| `app/config.py` | Feature flags: `ENABLE_TOURNAMENT_SKILL_PROPAGATION`, `ENABLE_SKILL_TIER_NOTIFICATIONS` |
| `tests/unit/services/test_skill_propagation.py` | Unit tests PROP-U-01–14 |
| `tests/integration/tournament/test_skill_propagation_integration.py` | Integration tests PROP-I-01–04 |
| `scripts/validate_skill_propagation.py` | Weekly health-check script (INV-SP-01–04) |
| `.github/workflows/skill-propagation-review.yml` | Scheduled CI runner (Monday 07:00 UTC) |
| `.github/CODEOWNERS` | Review enforcement for this file and the pipeline |
