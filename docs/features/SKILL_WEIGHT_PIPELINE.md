# Skill Weight Pipeline

**How `game_preset.skill_weights` flow from configuration through to `skill_rating_delta`.**

---

## Overview

Two separate reward mechanisms read the same preset weights:

| Mechanism | Formula | Output field |
|-----------|---------|-------------|
| **EMA delta** (rating change) | Log-normalised step | `TournamentParticipation.skill_rating_delta` |
| **Skill points** (bonus XP) | Linear proportional | `TournamentParticipation.skill_points_awarded` |

---

## Stage 1 — Preset definition (`GamePreset.game_config`)

Fractional weights are stored in `game_config.skill_config.skill_weights`.
They **must sum to 1.0** (enforced by `_build_game_config` in `game_presets_tab.py`).

```json
{
  "skill_config": {
    "skills_tested": ["acceleration", "sprint_speed", "agility"],
    "skill_weights": {
      "acceleration": 0.60,
      "sprint_speed":  0.25,
      "agility":       0.15
    }
  }
}
```

---

## Stage 2 — Reactivity conversion (`create.py`)

When a tournament is created with a `game_preset_id`, the fractional weights are
converted to **reactivity** values and stored in `TournamentSkillMapping.weight`.

```
avg_w      = sum(fractionals) / count(fractionals)   # = 1/3 for 3 skills
reactivity = fractional / avg_w                       # clamped to [0.1, 5.0]
```

**Example (3-skill preset, sum=1.0):**

| Skill | Fractional | avg\_w | Reactivity |
|-------|-----------|--------|-----------|
| acceleration | 0.60 | 0.333 | **1.80** (dominant) |
| sprint\_speed | 0.25 | 0.333 | **0.75** (mid) |
| agility | 0.15 | 0.333 | **0.45** (minor) |

**Key property:** Reactivity > 1.0 means the skill dominates; < 1.0 means it is a
supporting skill. The average reactivity over all skills is always 1.0.

**Code location:** `app/api/api_v1/endpoints/tournaments/create.py`

---

## Stage 3a — EMA delta (`skill_progression_service.py`)

### V3 formula

```
step       = lr × log(1 + weight) / log(2)
raw_delta  = step × (placement_skill − prev_value)
```

Where:
- `lr` = 0.20 (learning rate, anchored so that `step = lr` when `weight = 1.0`)
- `weight` = reactivity value from `TournamentSkillMapping.weight`
- `placement_skill` = linear percentile mapping: 100 (1st) → 40 (last)
- `prev_value` = running EMA level (starts at `DEFAULT_BASELINE = 50.0`)

### Asymmetric modifiers

```
opponent_factor  = avg_opponent_baseline / player_baseline_avg   [0.5, 2.0]
match_modifier   = confidence-weighted win/score signal          [-1.0, +1.0]

if raw_delta ≥ 0 (positive outcome):
    adjusted = raw_delta × opponent_factor × (1 + match_modifier)
else (negative outcome):
    adjusted = raw_delta / opponent_factor × (1 − match_modifier)

new_value = clamp(prev_value + adjusted, 40.0, 99.0)
```

### Mathematical guarantee

The **ratio of deltas between two skills is constant** (independent of placement,
prev_value, and opponent_factor):

```
delta_dom / delta_min = step_dom / step_min
                      = log(1 + w_dom) / log(1 + w_min)
```

This is **sub-linear** — doubling the weight does not double the delta.
Example: `log(2.80) / log(1.45) ≈ 2.77` (not 4.0 which would be the linear ratio 1.80/0.45).

### Output

`compute_single_tournament_skill_delta` returns `{skill_key: delta}` which is stored as
`TournamentParticipation.skill_rating_delta` (JSONB). Only skills with non-zero delta
are included.

**Code location:** `app/services/skill_progression_service.py`

---

## Stage 3b — Skill points (`tournament_participation_service.py`)

Skill points use a **linear proportional** formula — no log normalisation.

```
base_points = {1: 10, 2: 7, 3: 5, None: 1}[placement]
points_skill = (weight / total_weight) × base_points
```

Where `weight` is the reactivity from `TournamentSkillMapping.weight`.

**Example (1st place, 3-skill preset):**

| Skill | Reactivity | total\_w | Points |
|-------|-----------|---------|--------|
| acceleration | 1.80 | 3.00 | **6.0** |
| sprint\_speed | 0.75 | 3.00 | **2.5** |
| agility | 0.45 | 3.00 | **1.5** |
| **Total** | | | **10.0** ✓ |

Points ratio = 1.80 / 0.45 = **4.0** (linear — different from the EMA ratio of 2.77).

Skill points are converted to bonus XP via `SkillPointConversionRate` (per skill category)
and recorded as `TournamentParticipation.xp_awarded`.

**Code location:** `app/services/tournament/tournament_participation_service.py`

---

## Fallback chain

Both Stage 3a and 3b share the same fallback order when resolving skill weights:

1. **`reward_config.skill_mappings`** (V2 config stored on `Semester.reward_config`) — weights
   from the Ops Wizard reward step, already in reactivity form.
2. **`TournamentSkillMapping` table** — created by `create.py` from the preset reactivity
   conversion (Stage 2).
3. **Empty** → no skill delta / no skill points awarded.

---

## Clamp bounds

| Bound | Value | Rule |
|-------|-------|------|
| Floor | 40.0 | `MIN_SKILL_VALUE` — worst possible rating |
| Ceiling | 99.0 | `MAX_SKILL_CAP` — hard business cap |

---

## Regression test

`tests/unit/tournament/test_skill_weight_pipeline.py` verifies all stages:

- `TestReactivityConversion` — pure math, no DB
- `TestEMAStepMath` — pure function (`calculate_skill_value_from_placement`)
- `TestSkillPointsDistribution` — DB-backed (`postgres_db` fixture, SAVEPOINT rollback)
- `TestSkillDeltaPipeline` — full pipeline (`compute_single_tournament_skill_delta`)
