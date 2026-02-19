# Game Configuration - Implementation Complete (Phase 1)

**Date:** 2026-01-28
**Status:** ✅ Phase 1 COMPLETE - Database Schema Ready
**Next Phase:** Orchestrator Integration

## Summary

Successfully implemented **Phase 1** of the game configuration architecture:
- ✅ Database schema (game_config JSONB column)
- ✅ Migration created and executed
- ✅ Semester model updated
- ✅ GIN index for efficient querying

**Remaining work:** Orchestrator integration + Streamlit UI (Phase 2-3)

## Problem Solved

### Before (Scattered Configuration)

```python
# Configuration was scattered across multiple places
orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control", "stamina"],
    skill_weights={"ball_control": 2.0},  # ← In reward_config (separate)
    draw_probability=0.20,                  # ← Hardcoded default
    home_win_probability=0.40,              # ← Hardcoded default
    random_seed=42                           # ← Not saved!
)
# ❌ Problem: Can't reproduce tournament 165 - config not saved!
```

### After (Centralized Configuration)

```python
# All configuration in one place, saved to database
tournament.game_config = {
    "version": "1.0",
    "format_config": {
        "HEAD_TO_HEAD": {
            "match_simulation": {
                "draw_probability": 0.20,
                "home_win_probability": 0.40
            },
            "ranking_rules": {"points_system": {"win": 3, "draw": 1, "loss": 0}}
        }
    },
    "skill_config": {
        "skills_tested": ["ball_control", "stamina"],
        "skill_weights": {"ball_control": 2.0, "stamina": 1.5}
    },
    "simulation_config": {
        "random_seed": 42,
        "deterministic_mode": true
    }
}
# ✅ Solution: Exact config saved, can reproduce anytime!
```

## Phase 1: Database Schema ✅ COMPLETE

### Migration File

**File:** [alembic/versions/2026_01_28_1947-47ebca7dc3a8_add_game_config_to_semesters.py](alembic/versions/2026_01_28_1947-47ebca7dc3a8_add_game_config_to_semesters.py)

```python
def upgrade() -> None:
    """Add game_config JSONB column to semesters table"""
    # Add game_config column
    op.add_column(
        'semesters',
        sa.Column('game_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )

    # Create GIN index for efficient JSONB queries
    op.create_index(
        'ix_semesters_game_config',
        'semesters',
        ['game_config'],
        postgresql_using='gin'
    )
```

**Executed:**
```bash
$ DATABASE_URL="postgresql://..." alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade 3ae0c3d15363 -> 47ebca7dc3a8, add_game_config_to_semesters
```

**Verification:**
```sql
\d semesters
...
 game_config            | jsonb                       |           |          |
...
Indexes:
    "ix_semesters_game_config" gin (game_config)
```

### Model Update

**File:** [app/models/semester.py:143-146](app/models/semester.py#L143-L146)

```python
# 🎮 GAME CONFIGURATION FIELDS (tournament simulation rules)
game_config = Column(JSONB, nullable=True,
                    comment="Tournament-specific game rules, simulation parameters, and configuration settings. Includes match probabilities, ranking rules, skill weights, and simulation options. Enables reproducible simulations and explicit configuration.")
```

## Game Config Schema

### Structure

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
    "skill_impact_on_matches": true
  },
  "simulation_config": {
    "random_seed": 42,
    "deterministic_mode": true,
    "player_selection": "specific",
    "performance_noise": {
      "enabled": true,
      "range": 0.1
    }
  },
  "metadata": {
    "config_source": "sandbox_ui",
    "created_at": "2026-01-28T19:00:00Z",
    "created_by_user_id": 1,
    "schema_version": "1.0"
  }
}
```

### Key Sections

| Section | Purpose | Example Fields |
|---------|---------|----------------|
| `format_config` | Format-specific rules | match_simulation, ranking_rules |
| `skill_config` | Skill testing setup | skills_tested, skill_weights |
| `simulation_config` | Simulation parameters | random_seed, deterministic_mode |
| `metadata` | Audit trail | config_source, created_at |

## Use Cases Enabled

### 1. Reproducibility ✅

```python
# Reproduce tournament 165 exactly
tournament_165 = db.query(Semester).filter(Semester.id == 165).first()
saved_config = tournament_165.game_config

# Replay with exact same settings
new_tournament = orchestrator.execute_test_with_config(
    tournament_type_code="league",
    game_config=saved_config  # ✅ Exact reproduction!
)
```

### 2. Auditability ✅

```sql
-- Query: "Which tournaments used deterministic mode?"
SELECT id, name,
       game_config->'simulation_config'->>'random_seed' as seed
FROM semesters
WHERE game_config->'simulation_config'->>'deterministic_mode' = 'true';

-- Query: "Which tournaments had high draw probability?"
SELECT id, name,
       (game_config->'format_config'->'HEAD_TO_HEAD'->'match_simulation'->>'draw_probability')::float as draw_prob
FROM semesters
WHERE (game_config->'format_config'->'HEAD_TO_HEAD'->'match_simulation'->>'draw_probability')::float > 0.25;
```

### 3. A/B Testing ✅

```python
# Test different configurations
configs = [
    {
        "format_config": {
            "HEAD_TO_HEAD": {
                "match_simulation": {"draw_probability": 0.10, "home_win_probability": 0.50}
            }
        }
    },  # Low draws, high home advantage
    {
        "format_config": {
            "HEAD_TO_HEAD": {
                "match_simulation": {"draw_probability": 0.30, "home_win_probability": 0.35}
            }
        }
    },  # High draws, balanced
]

for i, config in enumerate(configs):
    result = orchestrator.execute_test(
        tournament_type_code="league",
        skills_to_test=["ball_control"],
        game_config=config
    )
    print(f"Config {i}: {result['verdict']}")
```

### 4. Regression Testing ✅

```python
# Test baseline config
baseline_tournament = db.query(Semester).filter(Semester.id == 165).first()
baseline_config = baseline_tournament.game_config

# Verify regression test still works
def test_deterministic_baseline():
    result = orchestrator.execute_test(
        tournament_type_code="league",
        skills_to_test=["ball_control"],
        user_ids=[4, 5, 6, 7],
        game_config=baseline_config  # ✅ Use exact saved config
    )

    rankings = get_rankings(db, result["tournament"]["id"])
    assert rankings[0].points == 9  # Expected with baseline config
```

## Next Steps (Phase 2-3)

### Phase 2: Orchestrator Integration

**Files to update:**
1. [app/services/sandbox_test_orchestrator.py](app/services/sandbox_test_orchestrator.py)
   - Add `_build_game_config()` method
   - Save `game_config` to tournament on creation
   - Load `game_config` and use for simulation
   - Add `execute_test_with_config()` method

**Implementation:**
```python
def _build_game_config(
    self,
    format: str,
    tournament_type_code: str,
    draw_probability: float = 0.20,
    home_win_probability: float = 0.40,
    skills_to_test: List[str] = [],
    skill_weights: Optional[Dict[str, float]] = None,
    random_seed: Optional[int] = None,
    performance_variation: str = "MEDIUM",
    ranking_distribution: str = "NORMAL",
    user_id: Optional[int] = None
) -> Dict:
    """Build game_config JSON from parameters"""
    return {
        "version": "1.0",
        "format_config": {
            format: self._build_format_config(
                format, draw_probability, home_win_probability,
                performance_variation, ranking_distribution
            )
        },
        "skill_config": {
            "skills_tested": skills_to_test,
            "skill_weights": skill_weights or {},
            "skill_impact_on_matches": True
        },
        "simulation_config": {
            "random_seed": random_seed,
            "deterministic_mode": random_seed is not None,
            "player_selection": "specific" if user_ids else "random",
            "performance_noise": {"enabled": True, "range": 0.1}
        },
        "metadata": {
            "config_source": "sandbox_orchestrator",
            "created_at": datetime.now().isoformat(),
            "created_by_user_id": user_id,
            "schema_version": "1.0"
        }
    }
```

### Phase 3: Streamlit UI

**File:** [streamlit_sandbox_v3_admin_aligned.py](streamlit_sandbox_v3_admin_aligned.py)

**Add section:**
```python
st.markdown("### 🎮 Advanced Game Settings (Optional)")

with st.expander("⚙️ Match Simulation (HEAD_TO_HEAD only)", expanded=False):
    draw_probability = st.slider(
        "Draw Probability",
        min_value=0.0,
        max_value=1.0,
        value=0.20,
        step=0.05,
        format="%.0%",
        help="Probability of matches ending in a draw (default: 20%)"
    )

    home_win_probability = st.slider(
        "Home Win Probability",
        min_value=0.0,
        max_value=1.0 - draw_probability,
        value=0.40,
        step=0.05,
        format="%.0%",
        help="Probability of home team winning (default: 40%)"
    )

    away_win_probability = 1.0 - draw_probability - home_win_probability
    st.metric("Away Win Probability", f"{away_win_probability:.0%}")

with st.expander("🧪 Testing Options", expanded=False):
    deterministic_mode = st.checkbox(
        "Deterministic Mode (reproducible results)",
        value=False,
        help="Use random seed for reproducible simulations"
    )

    random_seed = None
    if deterministic_mode:
        random_seed = st.number_input(
            "Random Seed",
            min_value=1,
            max_value=999999,
            value=42,
            help="Seed value for random number generator (e.g., 42)"
        )
```

## Benefits Summary

| Benefit | Before | After |
|---------|--------|-------|
| **Reproducibility** | ❌ Can't reproduce old tournaments | ✅ Exact config saved |
| **Auditability** | ❌ No way to query by config | ✅ JSONB queries enabled |
| **Flexibility** | ❌ Hardcoded defaults only | ✅ Custom configs per tournament |
| **Consistency** | ❌ Implicit rules, varies | ✅ Explicit, saved rules |
| **Extensibility** | ❌ Change function signatures | ✅ Add JSON fields |

## Testing Strategy

### Unit Tests

```python
def test_build_game_config():
    """Test game_config builder"""
    config = orchestrator._build_game_config(
        format="HEAD_TO_HEAD",
        tournament_type_code="league",
        draw_probability=0.25,
        skills_to_test=["ball_control"],
        random_seed=42
    )

    assert config["version"] == "1.0"
    assert config["format_config"]["HEAD_TO_HEAD"]["match_simulation"]["draw_probability"] == 0.25
    assert config["simulation_config"]["random_seed"] == 42
    assert config["simulation_config"]["deterministic_mode"] == True
```

### Integration Tests

```python
def test_tournament_saves_game_config(db):
    """Test tournament creation saves game_config"""
    result = orchestrator.execute_test(
        tournament_type_code="league",
        skills_to_test=["ball_control"],
        draw_probability=0.30,
        random_seed=99
    )

    tournament_id = result["tournament"]["id"]
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    assert tournament.game_config is not None
    assert tournament.game_config["format_config"]["HEAD_TO_HEAD"]["match_simulation"]["draw_probability"] == 0.30
    assert tournament.game_config["simulation_config"]["random_seed"] == 99
```

### Regression Tests

```python
def test_regression_with_saved_config(db):
    """Test regression baseline works with saved config"""
    # Tournament 165 (baseline)
    baseline = db.query(Semester).filter(Semester.id == 165).first()
    config = baseline.game_config

    # Replay
    result = orchestrator.execute_test_with_config(
        tournament_type_code="league",
        skills_to_test=["ball_control"],
        user_ids=[4, 5, 6, 7],
        game_config=config
    )

    # Verify
    rankings = get_rankings(db, result["tournament"]["id"])
    assert rankings[0].points == 9  # Expected from baseline
```

## Schema Versioning Strategy

**Version 1.0** (Current):
- Basic match simulation
- Skill configuration
- Simulation settings

**Version 2.0** (Future):
```json
{
  "version": "2.0",
  "format_config": {
    "HEAD_TO_HEAD": {
      "match_simulation": {
        "draw_probability": 0.20,
        "home_field_advantage": 0.10,  // NEW
        "fatigue_enabled": false,       // NEW
        "weather_impact": false         // NEW
      }
    }
  }
}
```

**Migration function:**
```python
def migrate_game_config_to_v2(config: dict) -> dict:
    """Migrate v1.0 config to v2.0"""
    if config.get("version") == "1.0":
        config["version"] = "2.0"
        if "HEAD_TO_HEAD" in config.get("format_config", {}):
            config["format_config"]["HEAD_TO_HEAD"]["match_simulation"]["home_field_advantage"] = 0.0
            config["format_config"]["HEAD_TO_HEAD"]["match_simulation"]["fatigue_enabled"] = False
            config["format_config"]["HEAD_TO_HEAD"]["match_simulation"]["weather_impact"] = False
    return config
```

## Documentation

- ✅ [GAME_CONFIG_DESIGN.md](GAME_CONFIG_DESIGN.md) - Design document
- ✅ [GAME_CONFIG_IMPLEMENTED.md](GAME_CONFIG_IMPLEMENTED.md) - This file
- 🚧 [GAME_CONFIG_SCHEMA.md](GAME_CONFIG_SCHEMA.md) - JSON schema reference (TODO)
- 🚧 [GAME_CONFIG_MIGRATION_GUIDE.md](GAME_CONFIG_MIGRATION_GUIDE.md) - For developers (TODO)

## Related Files

| File | Purpose | Status |
|------|---------|--------|
| [alembic/versions/2026_01_28_1947-47ebca7dc3a8_add_game_config_to_semesters.py](alembic/versions/2026_01_28_1947-47ebca7dc3a8_add_game_config_to_semesters.py) | Migration | ✅ Complete |
| [app/models/semester.py](app/models/semester.py) | Model | ✅ Complete |
| [app/services/sandbox_test_orchestrator.py](app/services/sandbox_test_orchestrator.py) | Orchestrator | 🚧 TODO |
| [streamlit_sandbox_v3_admin_aligned.py](streamlit_sandbox_v3_admin_aligned.py) | UI | 🚧 TODO |
| [app/api/api_v1/endpoints/sandbox/run_test.py](app/api/api_v1/endpoints/sandbox/run_test.py) | API | 🚧 TODO |

---

**Phase 1 Status:** ✅ COMPLETE
**Phase 2 Status:** 🚧 Ready to implement (Orchestrator)
**Phase 3 Status:** 🚧 Waiting (Streamlit UI)

**Next Action:** Implement `_build_game_config()` method in sandbox orchestrator

**Last Updated:** 2026-01-28 19:47
**Maintainer:** Development Team
