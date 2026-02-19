# Game Preset Architecture - Phase 1 & 2 COMPLETE ✅

## 🎯 Objective Achieved

Transformed game configuration from **manual parameter tuning** to **preset-based selection** with optional fine-tuning.

**Before:** Admin manually sets every skill, weight, probability for each tournament
**After:** Admin selects "GanFootvolley" → auto-fills all config → optional override

---

## ✅ Phase 1: Database Schema - COMPLETE

### Database Changes

```sql
-- New table: game_presets
CREATE TABLE game_presets (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    game_config JSONB NOT NULL,  -- Complete game configuration
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id)
);

-- Indexes
CREATE INDEX ix_game_presets_code ON game_presets(code);
CREATE INDEX ix_game_presets_active ON game_presets(is_active);
CREATE INDEX ix_game_presets_config ON game_presets USING GIN (game_config);

-- Semesters table updates
ALTER TABLE semesters ADD COLUMN game_preset_id INTEGER REFERENCES game_presets(id);
ALTER TABLE semesters ADD COLUMN game_config_overrides JSONB;
CREATE INDEX ix_semesters_game_preset ON semesters(game_preset_id);
CREATE INDEX ix_semesters_overrides ON semesters USING GIN (game_config_overrides);
```

### Seed Data - 3 Game Presets

**1. GanFootvolley** (`gan_footvolley`)
- Category: Beach Sports | Difficulty: Intermediate
- Skills: ball_control (50%), agility (30%), stamina (20%)
- Match Probs: Draw 15%, Home 45%, Away 40%
- Players: 4-16

**2. GanFoottennis** (`gan_foottennis`)
- Category: Racquet Sports | Difficulty: Advanced
- Skills: technique (45%), agility (35%), game_sense (20%)
- Match Probs: Draw 10%, Home 50%, Away 40%
- Players: 4-12

**3. Stole My Goal** (`stole_my_goal`)
- Category: Small Sided Games | Difficulty: Beginner
- Skills: finishing (40%), defending (35%), stamina (25%)
- Match Probs: Draw 25%, Home 40%, Away 35%
- Players: 6-20

### Files Created/Modified

- ✅ `alembic/versions/2026_01_28_2013-f5c8522cfe5e_create_game_presets_table.py`
- ✅ `app/models/game_preset.py` - SQLAlchemy model with properties
- ✅ `app/models/semester.py` - Added game_preset_id, game_config_overrides
- ✅ `app/models/__init__.py` - Registered GamePreset

---

## ✅ Phase 2: API Endpoints - COMPLETE

### API Endpoints

```
GET    /api/v1/game-presets/           - List all active presets (summary)
GET    /api/v1/game-presets/{id}       - Get preset by ID (full config)
GET    /api/v1/game-presets/code/{code} - Get preset by code (full config)
POST   /api/v1/game-presets/           - Create preset (admin only)
PATCH  /api/v1/game-presets/{id}       - Update preset (admin only)
DELETE /api/v1/game-presets/{id}       - Delete preset (admin only, soft/hard)
```

### Example Responses

**List Presets** (`GET /api/v1/game-presets/`):
```json
{
  "presets": [
    {
      "id": 1,
      "code": "gan_footvolley",
      "name": "GanFootvolley",
      "description": "Beach volleyball with feet...",
      "is_active": true,
      "skills_tested": ["ball_control", "agility", "stamina"],
      "game_category": "beach_sports",
      "difficulty_level": "intermediate",
      "recommended_player_count": {"min": 4, "max": 16}
    }
  ],
  "total": 3,
  "active_count": 3
}
```

**Get Preset** (`GET /api/v1/game-presets/1`):
```json
{
  "id": 1,
  "code": "gan_footvolley",
  "name": "GanFootvolley",
  "description": "Beach volleyball with feet...",
  "game_config": {
    "version": "1.0",
    "format_config": {
      "HEAD_TO_HEAD": {
        "match_simulation": {
          "draw_probability": 0.15,
          "home_win_probability": 0.45,
          ...
        },
        "ranking_rules": {...}
      }
    },
    "skill_config": {
      "skills_tested": ["ball_control", "agility", "stamina"],
      "skill_weights": {"ball_control": 0.5, "agility": 0.3, "stamina": 0.2}
    },
    ...
  },
  "is_active": true,
  "created_at": "2026-01-28T20:13:25",
  "updated_at": "2026-01-28T20:13:25"
}
```

### Files Created

- ✅ `app/api/api_v1/endpoints/game_presets/crud.py` - CRUD operations
- ✅ `app/api/api_v1/endpoints/game_presets/schemas.py` - Pydantic models
- ✅ `app/api/api_v1/endpoints/game_presets/router.py` - FastAPI router
- ✅ `app/api/api_v1/endpoints/game_presets/__init__.py` - Package init
- ✅ `app/api/api_v1/api.py` - Registered router

---

## 🐛 Bugs Fixed

### Bug 1: Double JSON Encoding
**Issue:** Migration used `json.dumps()` on dict before passing to JSONB field
**Result:** Database stored `"{\\"version\\": ...}"` instead of `{"version": ...}`
**Error:** `AttributeError: 'str' object has no attribute 'get'`

**Fix:**
1. Updated migration to pass dict directly (SQLAlchemy handles serialization)
2. Fixed existing data with SQL: `UPDATE game_presets SET game_config = (game_config#>>'{}')::jsonb`

**Migration Before:**
```python
'game_config': json.dumps(gan_footvolley_config),  # ❌ Double encoding
```

**Migration After:**
```python
'game_config': gan_footvolley_config,  # ✅ Direct dict
```

### Bug 2: Model Properties in Pydantic Schema
**Issue:** Tried to use GamePreset model properties (skills_tested, game_category) directly in Pydantic schema
**Result:** Properties return values but Pydantic expects different processing

**Fix:** Manually extract from JSONB in router:
```python
game_config = preset.game_config or {}
skill_config = game_config.get("skill_config", {})
metadata = game_config.get("metadata", {})

preset_summaries.append(
    schemas.GamePresetSummary(
        ...
        skills_tested=skill_config.get("skills_tested", []),
        game_category=metadata.get("game_category"),
        ...
    )
)
```

---

## ✅ Verification

### API Tests

```bash
# List all presets
curl http://localhost:8000/api/v1/game-presets/ | jq

# Get GanFootvolley details
curl http://localhost:8000/api/v1/game-presets/1 | jq

# Get preset by code
curl http://localhost:8000/api/v1/game-presets/code/stole_my_goal | jq
```

### Database Verification

```sql
-- Check presets exist
SELECT id, code, name, is_active FROM game_presets;

-- Check config format (should start with {, not ")
SELECT substring(game_config::text, 1, 50) FROM game_presets;

-- Verify JSONB query works
SELECT code,
       game_config->'skill_config'->'skills_tested' as skills
FROM game_presets;
```

---

## 📋 Next Steps

### Phase 3: Orchestrator Integration

**Goal:** Tournament creation uses preset + optional overrides

**Implementation:**
1. Add `game_preset_id` parameter to `execute_test()`
2. Load preset config from database
3. Merge preset + overrides → final game_config
4. Save preset_id, final config, and overrides to tournament

**Key Methods:**
```python
def _load_preset_config(preset_id: int) -> Dict[str, Any]:
    """Load game_config from game_preset"""

def _merge_config_overrides(base: Dict, overrides: Dict) -> Dict:
    """Deep merge overrides into base config"""

def _extract_overrides(base: Dict, final: Dict) -> Dict:
    """Extract differences as overrides for audit"""
```

### Phase 4: Streamlit UI Redesign

**Goal:** Preset picker → optional fine-tuning → tournament creation

**UI Flow:**
1. **Section 1: Game Type Selection** (NEW)
   - Dropdown with all active presets
   - Show preset details (skills, weights, probabilities)
   - Live preview of preset config

2. **Section 7: Advanced Settings (Override Preset)** (UPDATED)
   - Checkbox: "Customize game configuration"
   - If enabled: Show sliders with preset values as defaults
   - Display diff: preset vs customized

3. **Workflow Step 1: Configuration Summary** (UPDATED)
   - Show selected preset name
   - Show final configuration
   - Show overrides (if any)

**Benefits:**
- Admin selects preset in seconds
- Consistency across same game type
- Fine-tuning available but optional
- Full auditability (preset + overrides)

---

## 🎉 Summary

**Phase 1 & 2 Status:** ✅ **COMPLETE**

- ✅ Database schema created and seeded with 3 presets
- ✅ API endpoints working and tested
- ✅ Bugs fixed (double JSON encoding, property extraction)
- ✅ Migration corrected for future deployments

**API Fully Functional:**
- GET /api/v1/game-presets/ → Returns 3 presets with metadata ✅
- GET /api/v1/game-presets/1 → Returns full config ✅
- GET /api/v1/game-presets/code/gan_footvolley → Works ✅

**Next:** Phase 3 (Orchestrator) + Phase 4 (Streamlit UI)

**Time Investment:** ~1.5 hours (migration, models, API, debugging)
