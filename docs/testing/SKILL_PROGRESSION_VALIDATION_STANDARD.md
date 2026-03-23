# Skill Progression Validation Standard

> **Status**: Active | **Owner**: Engineering | **Last updated**: 2026-03-19

This document defines the canonical test coverage for the LFA Skill Progression system.
It is the authoritative reference for what "the skill system works" means in this codebase.

---

## What we are validating

The student skill progression system has three layers, each of which must be validated:

| Layer | What it does | Validated by |
|-------|-------------|-------------|
| **EMA formula** | Converts tournament placement into a skill delta | `tests/unit/test_skill_progression_service.py` |
| **API** | Exposes per-tournament timeline as JSON | `STU-JOURNEY-07`, `STU-JOURNEY-MS-*`, `STU-JOURNEY-EC-01a/02a` |
| **UI** | Renders Chart.js EMA curve + audit table | `STU-JOURNEY-05`, `STU-JOURNEY-06`, `STU-JOURNEY-EC-01b/02b` |

All three layers must pass for the system to be considered valid.

---

## The causal chain

This is the property the tests prove:

```
Tournament placement → placement_skill signal → EMA delta → skill_value_after
```

Concretely:

- **Placing last** (e.g., 2nd of 2): `placement_skill` = 40.0 → delta is **negative** → skill drops
- **Placing 1st** (e.g., 1st of 2): `placement_skill` = 99.0 → delta is **positive** → skill rises
- **Compounding**: after a loss then a win, `T2.skill_value_after > T1.skill_value_after`
- **Net positive arc** (2nd → 1st): `total_delta > 0` even after the dip in T1

This causal chain is verified for 3 different skills (different EMA weights):

| Skill | EMA weight | T1 delta (2nd/2) | T2 delta (1st/2) | Net delta |
|-------|-----------|-----------------|-----------------|-----------|
| `passing` | 1.0 | −6.0 | +7.2 | +1.2 |
| `ball_control` | 0.8 | −5.1 | +6.0 | +0.9 |
| `dribbling` | 0.7 | −4.6 | +5.3 | +0.7 |

---

## DB scenarios

Three dedicated E2E scenarios in `scripts/reset_e2e_web_db.py`:

### `student_skill_history` (primary)
- Student `rdias@manchestercity.com`: LFA license, all 29 skills @ 70.0 baseline
- **T1** `TOURN-E2E-HIST-1` (COMPLETED, 2 months ago): student 2nd/2, instructor 1st/2
- **T2** `TOURN-E2E-HIST-2` (COMPLETED, 1 month ago):  student 1st/2, instructor 2nd/2
- Both tournaments: `TournamentRewardConfig.reward_config.skill_mappings` = `passing`, `ball_control`, `dribbling`

### `student_1tournament` (single-entry edge case)
- Same student + license, **T1 only** (student 2nd/2)
- Verifies EMA formula does not produce NaN/Infinity with `tournament_count=1`

### `tournament_e2e` (no-tournament edge case)
- Student has active LFA license but **zero** `TournamentParticipation` records
- Verifies empty-state UI path renders correctly

---

## Test inventory

All tests live in:
`cypress/cypress/e2e/web/student/student_journey.cy.js`

### Suite A — Core Journey + Multi-Skill [`student_skill_history`]

| ID | What it proves |
|----|---------------|
| `STU-JOURNEY-01` | `/dashboard` renders student layout, no 500 |
| `STU-JOURNEY-02` | `/dashboard/LFA_FOOTBALL_PLAYER` accessible after onboarding (not 403/500) |
| `STU-JOURNEY-03` | `/skills` page loads — `has_lfa_license=True` |
| `STU-JOURNEY-04` | `GET /skills/data` → 29 skills present, `average_level > 0` |
| `STU-JOURNEY-05` | `/skills/history` chart **actually renders** — canvas dims > 0, empty state hidden, `#sh-count='2'`, `#sh-delta` has `.sh-delta-pos` |
| `STU-JOURNEY-06` | **Causal DOM**: each table row maps `tournament_name → placement badge → delta CSS class` |
| `STU-JOURNEY-07` | **Causal API** (`passing`): `t1.delta_from_previous < 0`, `t2.delta_from_previous > 0`, `t2.skill_value_after > t1.skill_value_after`, `total_delta > 0` |
| `STU-JOURNEY-MS-ball_control` | Same causal proof for `ball_control` (weight 0.8) |
| `STU-JOURNEY-MS-dribbling` | Same causal proof for `dribbling` (weight 0.7) |

### Suite B — Edge Case: No Tournaments [`tournament_e2e`]

| ID | What it proves |
|----|---------------|
| `STU-JOURNEY-EC-01a` | `GET /skills/history/data` returns `timeline=[]`, `total_delta=0` (not 404/500) |
| `STU-JOURNEY-EC-01b` | `/skills/history` page shows `#sh-empty` visible, chart hidden, table hidden, `#sh-count='0'` |

### Suite C — Edge Case: Single Tournament [`student_1tournament`]

| ID | What it proves |
|----|---------------|
| `STU-JOURNEY-EC-02a` | `timeline.length=1`, `skill_value_after ∈ [40, 99]`, value is finite, `delta_from_previous < 0` (placed last) |
| `STU-JOURNEY-EC-02b` | `/skills/history` chart renders with 1 entry — not empty state, canvas drawn, `#sh-count='1'` |

---

## Running the tests locally

```bash
# Prerequisites: FastAPI backend running on :8000, PostgreSQL migrated
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run the full student journey suite
cd cypress
npx cypress run --spec "cypress/e2e/web/student/student_journey.cy.js" \
  --config baseUrl=http://localhost:8000 \
  --browser chrome

# Run with GUI (interactive)
npx cypress open
```

The `cy.resetDb()` calls in each `before()` block handle DB state automatically —
no manual seeding needed before running.

---

## Invariants that must never regress

These are the system-level correctness guarantees:

1. **Placement direction is monotone**: placing in the top half of a field always produces
   `delta_from_previous > 0`; placing in the bottom half always produces `delta_from_previous < 0`.

2. **EMA is bounded**: `skill_value_after` is always in `[MIN_SKILL_VALUE=40, MAX_SKILL_CAP=99]`.
   No NaN, no Infinity, for any `tournament_count ≥ 1`.

3. **Empty state is explicit**: zero tournaments → `timeline=[]` → `#sh-empty` shown → no chart drawn.
   The system does not crash or show a broken chart on first use.

4. **Multi-skill consistency**: the directional invariants above hold regardless of `skill_weight`
   (currently verified for weights 1.0, 0.8, 0.7).

5. **Causal traceability**: every delta in the UI table is traceable to a specific tournament
   via `tournament_name` + placement badge + delta CSS class.

---

## Architecture reference

| Component | File |
|-----------|------|
| EMA formula | `app/services/skill_progression_service.py` → `calculate_skill_value_from_placement()` |
| Timeline builder | `app/services/skill_progression_service.py` → `get_skill_timeline()` |
| Web JSON endpoint | `app/api/web_routes/student_features.py` → `GET /skills/history/data` |
| Page template | `app/templates/skill_history.html` |
| Chart rendering | `skill_history.html` → `renderChart()` + `renderTable()` (inline IIFE) |
| Seed helper | `scripts/reset_e2e_web_db.py` → `_upsert_hist_tournament()` |
| Skill keys (29) | `app/skills_config.py` → `get_all_skill_keys()` |

---

## When to update this document

Update this standard when:
- A new skill is added to `skills_config.py`
- `PLACEMENT_SKILL_FLOOR` or `MIN_SKILL_VALUE` / `MAX_SKILL_CAP` constants change
- The EMA formula is revised (e.g., learning rate, opponent factor weights)
- New edge cases are discovered in production
