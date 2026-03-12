# Sprint Summary — P1 Technical Debt Cleanup (2026-03-12)

**Date:** 2026-03-12
**Branch:** `main`
**Merge commit:** `3ab390e`
**Risk level:** LOW — no breaking API or schema changes for callers

---

## What shipped

| Item | Summary | Release note |
|------|---------|--------------|
| **Remove `Semester.is_active`** | Deprecated boolean column replaced with `status != CANCELLED` at 17 filter sites + model + Alembic migration | — |
| **Remove legacy CouponType values** | `PERCENT / FIXED / CREDITS` removed from enum, DB, and application branches | — |
| **Worker liveness check** | `GET /health/worker` endpoint; Redis + Celery ping via `HealthChecker.get_worker_health()` | — |
| **Remove `Location.venue`** | Deprecated column removed from model, schemas, and migration utility script | — |
| **Tournament skill propagation** | V3 EMA delta now written to `FootballSkillAssessment` after every tournament reward distribution | [2026-03-12_skill-propagation.md](2026-03-12_skill-propagation.md) |
| **Streamlit decommission** | Archive + dependency removal; 0 Streamlit imports in active code | — |

---

## Test baseline

| Metric | Before sprint | After sprint |
|--------|--------------|--------------|
| Tests passing | 8870 | **8932** |
| xfailed | 1 | 1 |
| Routes | 537 | 538 |
| Coverage stmt | ≥ 88% | ≥ 88% |

---

## Ops team: what to action

### Skill propagation (new — requires monitoring)

The most operationally significant change is the **tournament skill propagation
pipeline** — player `FootballSkillAssessment` rows are now updated automatically
after every tournament reward distribution.

**Read before the next tournament:**
[docs/operations/skill_propagation_monitoring.md](../operations/skill_propagation_monitoring.md)

Key points:
- Feature is live: `ENABLE_TOURNAMENT_SKILL_PROPAGATION = True`
- Instant rollback: set env var to `false` + restart (no migration needed)
- Log pattern to grep after each tournament: `skill_propagation_complete user=<id>`
- Scheduled health check: `skill-propagation-review.yml` runs every Monday 07:00 UTC
- Manual spot-check: `python scripts/validate_skill_propagation.py`

### Health endpoint

New endpoint available for load balancer / monitoring probes:
```
GET /health/worker
→ {"status":"degraded","redis":"healthy","workers":[]}   # no workers running
→ {"status":"healthy","redis":"healthy","workers":[...]} # workers active
```
`"degraded"` (no workers) is non-critical — the app functions; only tournament
generation is affected. `"unhealthy"` (Redis down) should alert immediately.

---

## Deploy checklist

```
□ 1. Pull latest main and restart application server
□ 2. Run migrations (3 new migrations in this sprint):
      alembic upgrade head
      # 2026_03_12_1000-drop_semester_is_active
      # 2026_03_12_1100-remove_legacy_coupon_types
      # 2026_03_12_1200-drop_location_venue
□ 3. Verify health endpoints
      curl http://localhost:8000/health
      curl http://localhost:8000/health/worker
□ 4. After the next tournament reward distribution, confirm propagation ran:
      grep "skill_propagation_complete" app.log | tail -5
```

---

## CODEOWNERS

A `.github/CODEOWNERS` file was added this sprint. For it to enforce reviews:

1. Go to **GitHub → Settings → Branches → Branch protection rules → `main`**
2. Enable **"Require review from Code Owners"**
3. Set **"Required approving reviews" ≥ 1**

This ensures any future change to the skill propagation service, its tests,
or the monitoring doc triggers a mandatory review by `@football-investment/backend-leads`.

---

## Related documents

- [Skill propagation release note](2026-03-12_skill-propagation.md)
- [Skill propagation monitoring guide](../operations/skill_propagation_monitoring.md)
- [CI enforcement](../../.github/CI_ENFORCEMENT.md)
