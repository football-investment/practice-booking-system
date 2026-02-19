# Release Note — Skill Weight Form (Mandatory % Input)

**Date:** 2026-02-18
**Branch:** `feature/performance-card-option-a`
**Type:** UX / Feature / ⚠️ Breaking UX Change

---

## Summary

The Admin → Game Presets form now requires **explicit integer % weights** for every
selected skill before a preset can be created or edited.  The former implicit
fallback (`weight = 1.0` per skill) is replaced by a live-validated %-budget system.

---

## What Changed

### Create / Edit form (`game_presets_tab.py`)

| Before | After |
|--------|-------|
| No weight inputs shown on the Create form | A `% spinbutton (1–100)` appears for every ticked skill |
| Weight defaulted to `1.0` per skill; normalisation happened silently in `_build_game_config` | Default shows `10%` per skill; the form is **blocked** until skills sum to exactly 100% |
| Save button always enabled once a skill was provided | Save button is **disabled** (`disabled=True`) when `sum ≠ 100%` or `len(skills) == 0` |
| Edit mode silently displayed no weight spinbuttons | Edit mode converts stored fractional weights → int % via `_fractional_to_pct()` and pre-fills every spinbutton |
| No feedback about weight distribution | Live ✅/❌ sum indicator + `Dominant skill: …` badge when valid |

### New helpers

| Function | Location | Purpose |
|----------|----------|---------|
| `_fractional_to_pct(fractional_weights)` | `game_presets_tab.py` | Converts stored `{skill: 0.4}` → `{skill: 40}` summing to exactly 100 (rounding residual absorbed by largest skill) |

### Backend (`_build_game_config`)

The function already normalised by sum (`÷ total`) — this is unchanged and acts as a
safety net.  With `total = 100` the stored fractional values equal `pct / 100` exactly.

---

## ⚠️ Breaking UX Change

> **Old workflow**: Admin fills Name + ticks Skills → clicks Save → weights silently default to equal.
>
> **New workflow**: Admin fills Name + ticks Skills → **must set weights summing to 100%** → Save becomes enabled → clicks Save.

The **10% default** shown in every new spinbutton is only a placeholder.  For `n ≠ 10`
skills the initial sum is `n × 10% ≠ 100%`, so the Save button starts disabled.
Admins must consciously allocate the budget.

This change is **intentional**: the former silent equal-weight assumption masked the skill
economy configuration entirely.  Explicit weights make the decision visible and auditable.

**No data migration is required** — all existing presets already have explicit
`skill_weights` in their `game_config` JSONB (see Audit Results below).

---

## Audit Results — Existing Presets (2026-02-18)

Run: `python scripts/maintenance/audit_preset_weights.py`

```
Presets audited : 8
  [OK]   OK          : 8
  [1.0]  Fallback 1.0: 0
  [WARN] Warnings    : 0

✅ All presets pass the weight consistency check.
```

All 8 production presets carry explicit fractional weights summing to ≈ 1.0.
No preset relied on the legacy `1.0` fallback path.
The `gan_footvolley` preset has `ball_control` at `reactivity=5.00 (CLAMPED)` —
this is expected and documented in `docs/features/SKILL_WEIGHT_PIPELINE.md`.

---

## E2E Test Coverage

14 tests in `tests_e2e/test_game_presets_admin.py`:

| Tag | Scenario |
|-----|----------|
| GP-01 | Create 3 skills, equal 34/33/33%, schema validation |
| GP-07 | Edit 50/50 → 75/25%; ratio ≈ 3.0 confirmed via API |
| GP-08 | Create 5 skills × 20% = 100%, normalisation invariant |
| GP-V1 | No skills → Create button disabled |
| GP-V2 | Empty name → validation fires (button was enabled, 50+50=100%) |
| GP-V3 | Invalid code → validation fires (button was enabled, 100%) |
| **GP-W1** | Create with explicit 40/35/25% → API stores 0.40/0.35/0.25 |
| **GP-W2** | Edit 60/40 → 30/70 (dominance flip) → API confirmed |
| **GP-W3** | Over-budget (120%) and under-budget (80%) both keep button disabled |

---

## Pipeline Documentation

See `docs/features/SKILL_WEIGHT_PIPELINE.md` for the full 4-stage pipeline:
preset `skill_weights` → reactivity conversion → EMA delta → skill points.

---

## No Feature Flag

No feature flag was used.  The UX change ships atomically on branch merge.
All CI gates pass; regression suite: 78 passed, 1 skipped.
