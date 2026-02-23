# Game Preset Architecture Design

## 🎯 Objective

Transform game configuration from manual parameter tuning to **preset-based selection** with optional fine-tuning.

## 🏗️ Architecture Overview

```
User Flow:
1. Select Game Type (preset) → Auto-fills game_config
2. (Optional) Fine-tune parameters
3. Create Tournament → Saves preset_id + overrides
```

## 📊 Data Model

### New Table: `game_presets`

```sql
CREATE TABLE game_presets (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,  -- 'gan_footvolley', 'gan_foottennis', 'stole_my_goal'
    name VARCHAR(100) NOT NULL,        -- 'GanFootvolley', 'GanFoottennis', 'Stole My Goal'
    description TEXT,

    -- Game Configuration (JSONB)
    game_config JSONB NOT NULL,

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id),

    -- Constraints
    CONSTRAINT unique_active_code UNIQUE (code) WHERE is_active = TRUE
);

CREATE INDEX idx_game_presets_code ON game_presets(code);
CREATE INDEX idx_game_presets_active ON game_presets(is_active);
CREATE INDEX idx_game_presets_config ON game_presets USING GIN (game_config);
```

### Updated `semesters` Table

```sql
ALTER TABLE semesters ADD COLUMN game_preset_id INTEGER REFERENCES game_presets(id);
ALTER TABLE semesters ADD COLUMN game_config_overrides JSONB;

-- Indexes
CREATE INDEX idx_semesters_preset ON semesters(game_preset_id);
CREATE INDEX idx_semesters_overrides ON semesters USING GIN (game_config_overrides);
```

### Data Relationship

```
game_presets (template)
    ↓ selected
semesters.game_preset_id (reference)
    + game_config (full merged config)
    + game_config_overrides (user customizations)
```

## 🎮 Game Preset Structure

### Example: GanFootvolley

```json
{
  "code": "gan_footvolley",
  "name": "GanFootvolley",
  "description": "Beach volleyball with feet - emphasizes agility, stamina, and ball control",
  "game_config": {
    "version": "1.0",
    "format_config": {
      "HEAD_TO_HEAD": {
        "match_simulation": {
          "draw_probability": 0.15,
          "home_win_probability": 0.45,
          "away_win_probability": 0.40,
          "score_ranges": {
            "draw": {"min": 0, "max": 2},
            "win": {"winner_max": 3, "loser_max": 2}
          }
        },
        "ranking_rules": {
          "primary": "points",
          "tiebreakers": ["goal_difference", "goals_for", "user_id"],
          "points_system": {"win": 3, "draw": 1, "loss": 0}
        }
      }
    },
    "skill_config": {
      "skills_tested": ["ball_control", "agility", "stamina"],
      "skill_weights": {
        "ball_control": 0.50,
        "agility": 0.30,
        "stamina": 0.20
      },
      "skill_impact_on_matches": true
    },
    "simulation_config": {
      "performance_variation": "MEDIUM",
      "ranking_distribution": "NORMAL",
      "player_selection": "auto"
    },
    "metadata": {
      "game_category": "beach_sports",
      "recommended_player_count": {"min": 4, "max": 16},
      "difficulty_level": "intermediate"
    }
  }
}
```

### Example: GanFoottennis

```json
{
  "code": "gan_foottennis",
  "name": "GanFoottennis",
  "description": "Tennis with a football - emphasizes technique, agility, and game sense",
  "game_config": {
    "version": "1.0",
    "format_config": {
      "HEAD_TO_HEAD": {
        "match_simulation": {
          "draw_probability": 0.10,
          "home_win_probability": 0.50,
          "away_win_probability": 0.40,
          "score_ranges": {
            "draw": {"min": 0, "max": 1},
            "win": {"winner_max": 4, "loser_max": 3}
          }
        }
      }
    },
    "skill_config": {
      "skills_tested": ["technique", "agility", "game_sense"],
      "skill_weights": {
        "technique": 0.45,
        "agility": 0.35,
        "game_sense": 0.20
      }
    },
    "simulation_config": {
      "performance_variation": "LOW",
      "ranking_distribution": "NORMAL"
    },
    "metadata": {
      "game_category": "racquet_sports",
      "recommended_player_count": {"min": 4, "max": 12},
      "difficulty_level": "advanced"
    }
  }
}
```

### Example: Stole My Goal

```json
{
  "code": "stole_my_goal",
  "name": "Stole My Goal",
  "description": "Small-sided game focusing on finishing and defensive skills",
  "game_config": {
    "version": "1.0",
    "format_config": {
      "HEAD_TO_HEAD": {
        "match_simulation": {
          "draw_probability": 0.25,
          "home_win_probability": 0.40,
          "away_win_probability": 0.35,
          "score_ranges": {
            "draw": {"min": 0, "max": 3},
            "win": {"winner_max": 6, "loser_max": 5}
          }
        }
      }
    },
    "skill_config": {
      "skills_tested": ["finishing", "defending", "stamina"],
      "skill_weights": {
        "finishing": 0.40,
        "defending": 0.35,
        "stamina": 0.25
      }
    },
    "simulation_config": {
      "performance_variation": "HIGH",
      "ranking_distribution": "NORMAL"
    },
    "metadata": {
      "game_category": "small_sided_games",
      "recommended_player_count": {"min": 6, "max": 20},
      "difficulty_level": "beginner"
    }
  }
}
```

## 🔄 Implementation Phases

### Phase 1: Database Schema ✅ (Ready to implement)

**Files to create:**
- `alembic/versions/YYYY_MM_DD_HHMM-<hash>_create_game_presets_table.py`
- `app/models/game_preset.py`

**Tasks:**
1. Create `game_presets` table with JSONB config
2. Add `game_preset_id` and `game_config_overrides` to `semesters`
3. Create SQLAlchemy models
4. Seed initial presets (GanFootvolley, GanFoottennis, Stole My Goal)

### Phase 2: API Endpoints ✅ (Ready to implement)

**Files to create/modify:**
- `app/api/api_v1/endpoints/game_presets/` (new directory)
  - `crud.py` - CRUD operations
  - `schemas.py` - Pydantic models
  - `router.py` - API endpoints
- `app/api/api_v1/api.py` - Register router

**Endpoints:**
```
GET    /api/v1/game-presets           - List all active presets
GET    /api/v1/game-presets/{id}      - Get preset details
POST   /api/v1/game-presets           - Create preset (admin only)
PATCH  /api/v1/game-presets/{id}      - Update preset (admin only)
DELETE /api/v1/game-presets/{id}      - Soft delete preset (admin only)
```

### Phase 3: Orchestrator Integration ✅ (Ready to implement)

**Files to modify:**
- `app/services/sandbox_test_orchestrator.py`

**Changes:**
1. Add `game_preset_id` parameter to `execute_test()`
2. Load preset from database if provided
3. Merge preset config with overrides
4. Save both `game_preset_id` and merged `game_config`

**New methods:**
```python
def _load_preset_config(self, game_preset_id: int) -> Dict[str, Any]:
    """Load game_config from game_preset"""

def _merge_config_overrides(
    self,
    base_config: Dict[str, Any],
    overrides: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Deep merge overrides into base config"""

def _extract_overrides(
    self,
    base_config: Dict[str, Any],
    final_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Extract differences as overrides"""
```

### Phase 4: Streamlit UI Redesign ✅ (Ready to implement)

**Files to modify:**
- `streamlit_sandbox_v3_admin_aligned.py`

**UI Changes:**

**NEW Section 1️⃣: Game Type Selection**
```python
st.markdown("### 1️⃣ Select Game Type")

# Fetch presets from API
presets = fetch_game_presets()

selected_preset = st.selectbox(
    "Choose a game preset",
    options=presets,
    format_func=lambda p: f"{p['name']} - {p['description']}"
)

# Display preset details
with st.expander("📄 Preset Configuration", expanded=True):
    st.json(selected_preset['game_config'])
```

**UPDATED Section 7️⃣: Configuration Override (Optional)**
```python
st.markdown("### 7️⃣ Advanced Settings (Override Preset)")

enable_overrides = st.checkbox(
    "🔧 Customize game configuration",
    value=False,
    help="Override preset defaults with custom values"
)

if enable_overrides:
    # Show current preset values as defaults
    # Allow slider overrides
    # Show diff preview
```

**Configuration Summary:**
```python
with st.expander("📋 Final Configuration Summary"):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Preset (Base):**")
        st.json(preset_config)

    with col2:
        st.markdown("**Overrides (Custom):**")
        if overrides:
            st.json(overrides)
        else:
            st.info("No overrides - using preset defaults")
```

## 🎯 Benefits

### 1. Consistency
- All GanFootvolley tournaments use same skill weights
- Reproducible results across tournaments
- Clear expectation per game type

### 2. Scalability
- Add new game types via database (no code changes)
- Admin UI for preset management
- Version control for game configurations

### 3. Flexibility
- Sandbox can still override for testing
- Fine-tuning available when needed
- Clear audit trail (preset + overrides)

### 4. Maintenance
- Single source of truth per game type
- Easy to update game balance globally
- Historical tournaments preserve their config

## 📝 Migration Strategy

### Backwards Compatibility

**Old tournaments (game_config without preset):**
```sql
-- game_preset_id = NULL
-- game_config = {...}  (custom config)
-- game_config_overrides = NULL
```

**New tournaments (preset-based):**
```sql
-- game_preset_id = 1  (GanFootvolley)
-- game_config = {...}  (merged config)
-- game_config_overrides = {"skill_config": {"skill_weights": {...}}}  (if customized)
```

### Data Migration

```sql
-- No migration needed for old tournaments
-- They continue to work with existing game_config

-- New tournaments automatically use preset system
-- Old behavior still available via "Custom" preset option
```

## 🧪 Testing Strategy

### Unit Tests
- Preset CRUD operations
- Config merge logic
- Override extraction

### Integration Tests
- Tournament creation with preset
- Tournament creation with preset + overrides
- Backwards compatibility with old tournaments

### UI Tests
- Preset selection workflow
- Override toggles and sliders
- Configuration preview accuracy

## 📅 Implementation Timeline

### Phase 1: Database (Day 1)
- Create migration
- Create models
- Seed initial presets

### Phase 2: API (Day 1-2)
- Create CRUD operations
- Create API endpoints
- Add permissions/validation

### Phase 3: Orchestrator (Day 2)
- Integrate preset loading
- Implement config merging
- Update tournament creation

### Phase 4: Streamlit UI (Day 2-3)
- Redesign Section 1 (preset selection)
- Update Section 7 (overrides)
- Add configuration summary
- Manual testing

## ✅ Success Criteria

- [ ] Admin selects "GanFootvolley" → auto-fills all config
- [ ] Admin can optionally fine-tune parameters
- [ ] Tournament saves both preset_id and final config
- [ ] Old tournaments continue to work
- [ ] New game types can be added via database
- [ ] Configuration changes are auditable (preset vs override)

---

**Status:** Design Complete - Ready for Phase 1 Implementation
**Next Step:** Create database migration and models
