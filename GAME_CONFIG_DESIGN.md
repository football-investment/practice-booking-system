# Game Configuration Architecture - Design Document

**Date:** 2026-01-28
**Status:** 🚧 IN PROGRESS
**Priority:** HIGH - Critical for consistency and maintainability

## Problem Statement

Currently, tournament simulation and ranking configuration is **scattered and implicit**:

### Current Issues

1. **Hardcoded Defaults**: Match probabilities (draw: 20%, home_win: 40%) are hardcoded in orchestrator
2. **Parameter Passing**: Configuration passed as function parameters, not persisted
3. **Inconsistency Risk**: Different tournaments may use different implicit rules
4. **No Audit Trail**: Can't reproduce past tournament simulations
5. **No UI Control**: Streamlit can't expose advanced settings (users stuck with defaults)
6. **Skill Weights Separation**: skill_weights stored in reward_config, not with game rules

### Example Problem

```python
# Tournament 1 (implicit defaults)
orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control", "stamina"]
    # draw_probability defaults to 0.20
    # home_win_probability defaults to 0.40
)

# Tournament 2 (explicit config - but NOT saved!)
orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control", "stamina"],
    draw_probability=0.30,  # Custom value
    home_win_probability=0.35
    # ❌ These values are NOT saved to database!
    # ❌ Can't reproduce this tournament later!
)
```

**Question**: "Why does tournament 165 have different results than tournament 166?"
**Answer**: "Unknown - config wasn't saved" ❌

## Proposed Solution: `game_config` JSONB Column

Add a new JSONB column to `semesters` table to store **all tournament-specific game rules and simulation parameters**.

### Schema Design

```json
{
  "version": "1.0",
  "format_config": {
    "HEAD_TO_HEAD": {
      "match_simulation": {
        "draw_probability": 0.20,
        "home_win_probability": 0.40,
        "away_win_probability": 0.40,
        "score_ranges": {
          "draw": {"min": 0, "max": 3},
          "win": {"winner_max": 5, "loser_max": 4}
        }
      },
      "ranking_rules": {
        "primary": "points",
        "tiebreakers": ["goal_difference", "goals_for", "user_id"],
        "points_system": {
          "win": 3,
          "draw": 1,
          "loss": 0
        }
      }
    },
    "INDIVIDUAL_RANKING": {
      "performance_variation": "MEDIUM",
      "ranking_distribution": "NORMAL",
      "placement_calculation": "skill_weighted_average"
    }
  },
  "skill_config": {
    "skills_tested": ["ball_control", "stamina"],
    "skill_weights": {
      "ball_control": 2.0,
      "stamina": 1.5
    },
    "skill_impact_on_matches": true,
    "skill_decay_enabled": false
  },
  "simulation_config": {
    "random_seed": null,
    "deterministic_mode": false,
    "player_selection": "random",
    "performance_noise": {
      "enabled": true,
      "range": 0.1
    }
  },
  "tournament_type_overrides": {
    "league": {
      "parallel_matches": true,
      "max_concurrent_matches": 3
    }
  },
  "metadata": {
    "config_source": "sandbox_ui",
    "created_at": "2026-01-28T18:00:00Z",
    "created_by_user_id": 1,
    "schema_version": "1.0"
  }
}
```

### Key Sections

#### 1. Format-Specific Configuration

**HEAD_TO_HEAD**:
- Match simulation parameters (draw%, home_win%, score ranges)
- Ranking rules (points system, tiebreakers)
- Match pairing algorithm

**INDIVIDUAL_RANKING**:
- Performance variation (LOW/MEDIUM/HIGH)
- Ranking distribution (NORMAL/TOP_HEAVY/BOTTOM_HEAVY)
- Placement calculation method

#### 2. Skill Configuration

- List of skills being tested
- Skill weights (for reward distribution)
- Whether skills affect match outcomes
- Skill decay settings (future)

#### 3. Simulation Configuration

- Random seed (for deterministic mode)
- Player selection strategy
- Performance noise settings
- Debug options

#### 4. Tournament Type Overrides

- Tournament-type-specific tweaks
- Parallel match settings
- Round scheduling

#### 5. Metadata

- Config source (sandbox_ui, api, admin_panel)
- Creation timestamp
- Creator user
- Schema version (for future migrations)

## Implementation Plan

### Phase 1: Database Schema ✅

**File**: New Alembic migration

```sql
ALTER TABLE semesters ADD COLUMN game_config JSONB;
CREATE INDEX ix_semesters_game_config ON semesters USING GIN (game_config);
```

### Phase 2: Sandbox Orchestrator Update

**File**: [app/services/sandbox_test_orchestrator.py](app/services/sandbox_test_orchestrator.py)

**Changes**:
1. Build `game_config` JSON from parameters
2. Save to `tournament.game_config` on creation
3. Load from `tournament.game_config` when needed
4. Use loaded config instead of hardcoded defaults

**Example**:

```python
def execute_test(
    self,
    tournament_type_code: str,
    skills_to_test: List[str],
    skill_weights: Optional[Dict[str, float]] = None,
    player_count: int = 16,
    campus_id: int = 1,
    draw_probability: float = 0.20,
    home_win_probability: float = 0.40,
    random_seed: Optional[int] = None,
    performance_variation: str = "MEDIUM",
    ranking_distribution: str = "NORMAL",
    # ... other params
) -> Dict[str, Any]:
    """Execute test with explicit game configuration"""

    # Build game_config
    game_config = self._build_game_config(
        format=tournament.format,
        draw_probability=draw_probability,
        home_win_probability=home_win_probability,
        skills_to_test=skills_to_test,
        skill_weights=skill_weights,
        random_seed=random_seed,
        performance_variation=performance_variation,
        ranking_distribution=ranking_distribution
    )

    # Save to database
    tournament.game_config = game_config
    self.db.commit()

    # Use config for simulation
    self._generate_rankings_from_config(tournament.game_config)
```

### Phase 3: Streamlit UI Update

**File**: [streamlit_sandbox_v3_admin_aligned.py](streamlit_sandbox_v3_admin_aligned.py)

**Changes**:
1. Add "Advanced Game Settings" expander
2. Expose match probability sliders
3. Expose performance variation options
4. Expose random seed input (deterministic mode)
5. Show config summary before tournament creation

**UI Mockup**:

```
### 🎮 Advanced Game Settings (Optional)

[Expander: "⚙️ Match Simulation (HEAD_TO_HEAD only)"]
  Draw Probability: [======|===] 20%
  Home Win Probability: [==========|] 40%
  Away Win Probability: 40% (calculated)

  Score Ranges:
  - Draw scores: 0-0 to 3-3
  - Win margin: 1-5 goals

[Expander: "🎯 Performance Variation (INDIVIDUAL_RANKING only)"]
  Variation Level: ○ LOW ● MEDIUM ○ HIGH
  Distribution: ○ NORMAL ○ TOP_HEAVY ○ BOTTOM_HEAVY

[Expander: "🧪 Testing Options"]
  ☐ Deterministic Mode (use random seed)
  Random Seed: [_____] (e.g., 42)

  ☑ Skills affect match outcomes
  ☐ Enable performance noise

📋 Configuration Summary:
- Match probabilities: 20% draw, 40% home, 40% away
- Ranking: Points → Goal Diff → Goals For
- Skills: ball_control (2.0x), stamina (1.5x)
- Mode: Random (non-deterministic)
```

### Phase 4: API Updates

**File**: [app/api/api_v1/endpoints/sandbox/run_test.py](app/api/api_v1/endpoints/sandbox/run_test.py)

**Changes**:
1. Accept `game_config` in request body (optional)
2. Pass to orchestrator
3. Return `game_config` in response

**Request Schema**:

```python
class RunTestRequest(BaseModel):
    tournament_type: str
    skills_to_test: list[str]
    skill_weights: Optional[dict[str, float]] = None
    player_count: Optional[int] = None
    campus_id: int

    # NEW: Optional game configuration
    game_config: Optional[dict] = None

    # OR individual parameters (backwards compatible)
    draw_probability: Optional[float] = 0.20
    home_win_probability: Optional[float] = 0.40
    random_seed: Optional[int] = None
    performance_variation: Optional[str] = "MEDIUM"
    ranking_distribution: Optional[str] = "NORMAL"
```

### Phase 5: Documentation

**Files**:
- [GAME_CONFIG_SCHEMA.md](GAME_CONFIG_SCHEMA.md) - JSON schema reference
- [GAME_CONFIG_MIGRATION.md](GAME_CONFIG_MIGRATION.md) - Migration guide
- Update [SANDBOX_TOURNAMENT_COMPLETE.md](SANDBOX_TOURNAMENT_COMPLETE.md)

## Benefits

### 1. Reproducibility ✅
```python
# Replay tournament 165 exactly
tournament_165 = db.query(Semester).filter(Semester.id == 165).first()
config = tournament_165.game_config

orchestrator.execute_test_with_config(
    tournament_type_code=tournament_165.tournament_type,
    game_config=config  # ✅ Exact same settings!
)
```

### 2. Auditability ✅
```sql
-- Query: "Which tournaments used deterministic mode?"
SELECT id, name, game_config->'simulation_config'->>'random_seed' as seed
FROM semesters
WHERE game_config->'simulation_config'->>'random_seed' IS NOT NULL;

-- Query: "Which tournaments had high draw probability?"
SELECT id, name,
       (game_config->'format_config'->'HEAD_TO_HEAD'->'match_simulation'->>'draw_probability')::float as draw_prob
FROM semesters
WHERE (game_config->'format_config'->'HEAD_TO_HEAD'->'match_simulation'->>'draw_probability')::float > 0.25;
```

### 3. Flexibility ✅
```python
# Test different configurations easily
configs = [
    {"draw_probability": 0.10, "home_win_probability": 0.50},  # Low draws
    {"draw_probability": 0.30, "home_win_probability": 0.35},  # High draws
    {"draw_probability": 0.20, "home_win_probability": 0.60},  # Home advantage
]

for config in configs:
    result = orchestrator.execute_test(tournament_type_code="league", **config)
    print(f"Config {config}: {result['verdict']}")
```

### 4. Consistency ✅
- No more "works on my machine" - config is saved
- No more implicit defaults - everything explicit
- No more parameter hell - one JSON object

### 5. Extensibility ✅
- Add new settings without changing function signatures
- Versioned schema (migration path for future changes)
- Backwards compatible (NULL = use defaults)

## Migration Strategy

### Existing Tournaments

**Option A: Backfill with defaults**
```sql
UPDATE semesters
SET game_config = '{
  "version": "1.0",
  "format_config": {
    "HEAD_TO_HEAD": {
      "match_simulation": {
        "draw_probability": 0.20,
        "home_win_probability": 0.40
      }
    }
  },
  "metadata": {
    "config_source": "backfill_defaults",
    "created_at": "2026-01-28T00:00:00Z"
  }
}'::jsonb
WHERE game_config IS NULL AND format = 'HEAD_TO_HEAD';
```

**Option B: Leave NULL, use defaults at runtime**
```python
def get_game_config(tournament):
    if tournament.game_config:
        return tournament.game_config
    else:
        # Use defaults for old tournaments
        return DEFAULT_GAME_CONFIG
```

**Recommendation**: Option B (less invasive, preserves history)

### Backwards Compatibility

```python
# OLD CODE (still works)
orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control"]
    # No game_config - uses defaults
)

# NEW CODE (explicit config)
orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control"],
    game_config={
        "format_config": {
            "HEAD_TO_HEAD": {
                "match_simulation": {
                    "draw_probability": 0.25
                }
            }
        }
    }
)
```

## Schema Versioning

**Version 1.0** (Initial):
- Match simulation config
- Skill configuration
- Basic simulation settings

**Version 2.0** (Future):
- Player fatigue simulation
- Weather effects
- Home field advantage per campus
- Dynamic skill evolution

**Migration**:
```python
def migrate_game_config(config):
    version = config.get("version", "1.0")

    if version == "1.0":
        # Migrate to 2.0
        config["version"] = "2.0"
        config["simulation_config"]["fatigue_enabled"] = False
        config["simulation_config"]["weather_enabled"] = False

    return config
```

## Testing Strategy

### Unit Tests
- Test config building
- Test config loading
- Test config validation
- Test defaults fallback

### Integration Tests
- Test tournament creation with config
- Test tournament replay from config
- Test config querying (JSONB queries)

### Regression Tests
- Update baseline tests to include game_config
- Verify deterministic mode still works
- Verify old tournaments (NULL config) still work

## Rollout Plan

1. **Week 1**: Database migration + model updates
2. **Week 2**: Orchestrator updates + unit tests
3. **Week 3**: Streamlit UI updates + integration tests
4. **Week 4**: Documentation + regression tests + release

## Success Criteria

- ✅ All tournament configurations are persisted to database
- ✅ Tournaments can be reproduced exactly using saved config
- ✅ Streamlit UI exposes advanced settings
- ✅ Backwards compatibility maintained (old code still works)
- ✅ Documentation complete
- ✅ Tests passing (unit + integration + regression)

---

**Status**: 🚧 Design Complete, Ready for Implementation
**Next Step**: Create Alembic migration for `game_config` column
**Assigned To**: Development Team
**Target Completion**: 2026-02-04
