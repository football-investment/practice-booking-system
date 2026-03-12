# Release Note — Tournament Skill Propagation (V3 EMA)

**Date:** 2026-03-12
**Branch:** `main` (P1 technical debt cleanup sprint)
**Commits:** `3ab390e` (p1-debt)
**Alembic migration:** none — all changes are application-layer only
**Risk level:** LOW — feature-flagged, existing assessment rows are never deleted

---

## Summary

After every tournament reward distribution, each LFA Football Player's
`FootballSkillAssessment` rows are now automatically updated using the V3 EMA
(Exponential Moving Average) skill delta.

The feature is **live** behind `ENABLE_TOURNAMENT_SKILL_PROPAGATION = True`
(set in `app/config.py`, overridable via env var).

---

## Changes

### New behaviour (Phase 3 of `record_tournament_participation`)

| Phase | What runs | Since |
|-------|-----------|-------|
| 1 | Upsert `TournamentParticipation` row (XP + credits) | pre-existing |
| 2 | Compute V3 EMA skill delta | pre-existing |
| **3** | **Write delta → `FootballSkillAssessment` rows** | **2026-03-12** |

Phase 3 (`update_skill_assessments`) behaviour per skill:

1. Finds the player's most recent `ASSESSED` or `VALIDATED` assessment row
2. Archives it (`status = ARCHIVED`, `archived_reason = "tournament_progression_delta=±N.N"`)
3. Inserts a new `ASSESSED` row at `clamp(current_pct + delta, 40.0, 99.0)`

Players without an active `LFA_FOOTBALL_PLAYER` license are silently skipped
(debug log line emitted). Non-LFA users (coaches, instructors) are unaffected.

### Observability

Structured log lines are emitted by
`app.services.tournament.tournament_participation_service`:

```
INFO skill_propagation skill=<name> user=<id> license=<id> old_pct=<n> delta=<±n> new_pct=<n> clamped=<True|False>
INFO skill_propagation_complete user=<id> license=<id> skills_written=<n>
```

See [docs/operations/skill_propagation_monitoring.md](../operations/skill_propagation_monitoring.md)
for full monitoring guidance, expected delta ranges, red flags, and rollback procedure.

---

## Deploy Checklist

```
□ 1. No migration required
      (Phase 3 writes to the existing football_skill_assessments table)

□ 2. Verify feature flag is set
      grep ENABLE_TOURNAMENT_SKILL_PROPAGATION .env
      # Expected: ENABLE_TOURNAMENT_SKILL_PROPAGATION=true  (or not set → defaults True)

□ 3. Run full test suite
      pytest tests/unit/ tests/integration/ -q --tb=short
      # Expected: 8932 passed, 1 xfailed

□ 4. After the first tournament reward distribution, verify propagation ran:
      grep "skill_propagation_complete" app.log | tail -20
      # Expect one line per rewarded LFA Football Player

□ 5. Spot-check one player's assessments:
      curl -s http://localhost:8000/api/v1/lfa-player/<user_id>/assessments | python3 -m json.tool
      # New ASSESSED rows should appear; old rows status=ARCHIVED
```

---

## Rollback

Disable without a code deploy (takes effect immediately after restart):

```bash
# In .env or environment config:
ENABLE_TOURNAMENT_SKILL_PROPAGATION=false

# Restart app — all subsequent reward distributions skip Phase 3.
# Existing FootballSkillAssessment rows are UNAFFECTED.
```

To re-enable after a fix, set the flag back to `true` and restart.
Any tournaments distributed while the flag was off can be replayed manually
via `update_skill_assessments()` passing the stored
`TournamentParticipation.skill_rating_delta`.

---

## Monitoring

**Monitoring doc (ops team):**
[docs/operations/skill_propagation_monitoring.md](../operations/skill_propagation_monitoring.md)

Key sections:
- **Log patterns** — what to grep for per tournament window
- **Expected delta ranges** — normal bounds by placement × field size
- **Red flags** — `skills_written=0`, frequent `clamped=True`, `|delta| > 20`
- **Troubleshooting SQL** — verify DB state in `tournament_participations` and `football_skill_assessments`
- **Next phase** — enabling `ENABLE_SKILL_TIER_NOTIFICATIONS` after 2–3 stable cycles

**Alert threshold (immediate escalation):**
- Any tournament where `skill_propagation_complete` is NOT emitted for every rewarded LFA player
- `skills_written=0` for a player who has a valid license

---

## Test Coverage

| File | Tests | Result |
|------|-------|--------|
| `tests/unit/services/test_skill_propagation.py` | 14 (PROP-U-01–14) | ✅ GREEN |
| `tests/integration/tournament/test_skill_propagation_integration.py` | 4 (PROP-I-01–04) | ✅ GREEN |
| Full suite | 8932 | ✅ 0 failed, 1 xfailed |

---

## Related Documents

- Monitoring guide: `docs/operations/skill_propagation_monitoring.md`
- Skill progression service: `app/services/skill_progression_service.py`
- Feature flag: `app/config.py` (`ENABLE_TOURNAMENT_SKILL_PROPAGATION`)
- Unit tests: `tests/unit/services/test_skill_propagation.py`
- Integration tests: `tests/integration/tournament/test_skill_propagation_integration.py`
