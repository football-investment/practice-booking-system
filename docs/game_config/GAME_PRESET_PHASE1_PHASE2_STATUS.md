# Game Preset Architecture - Phase 1 & 2 Status

## ✅ Phase 1: Database Schema - COMPLETE

### Created Files:
- `alembic/versions/2026_01_28_2013-f5c8522cfe5e_create_game_presets_table.py` - Migration
- `app/models/game_preset.py` - SQLAlchemy model
- Updated `app/models/semester.py` - Added game_preset_id, game_config_overrides
- Updated `app/models/__init__.py` - Registered GamePreset model

### Database Changes:
```sql
-- New table
CREATE TABLE game_presets (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    game_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id)
);

-- Indexes
CREATE INDEX ix_game_presets_code ON game_presets(code);
CREATE INDEX ix_game_presets_active ON game_presets(is_active);
CREATE INDEX ix_game_presets_config ON game_presets USING GIN (game_config);

-- Semesters updates
ALTER TABLE semesters ADD COLUMN game_preset_id INTEGER REFERENCES game_presets(id);
ALTER TABLE semesters ADD COLUMN game_config_overrides JSONB;
```

### Seed Data - 3 Presets Created:
1. **gan_footvolley** - GanFootvolley (beach sports, intermediate)
   - Skills: ball_control (50%), agility (30%), stamina (20%)
   - Draw: 15%, Home: 45%, Away: 40%

2. **gan_foottennis** - GanFoottennis (racquet sports, advanced)
   - Skills: technique (45%), agility (35%), game_sense (20%)
   - Draw: 10%, Home: 50%, Away: 40%

3. **stole_my_goal** - Stole My Goal (small sided, beginner)
   - Skills: finishing (40%), defending (35%), stamina (25%)
   - Draw: 25%, Home: 40%, Away: 35%

### Verification:
```bash
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c \
  "SELECT id, code, name, is_active FROM game_presets;"
```

Output:
```
 id |      code      |     name      | is_active
----+----------------+---------------+-----------
  1 | gan_footvolley | GanFootvolley | t
  2 | gan_foottennis | GanFoottennis | t
  3 | stole_my_goal  | Stole My Goal | t
```

## 🚧 Phase 2: API Endpoints - IN PROGRESS

### Created Files:
- `app/api/api_v1/endpoints/game_presets/crud.py` - CRUD operations ✅
- `app/api/api_v1/endpoints/game_presets/schemas.py` - Pydantic schemas ✅
- `app/api/api_v1/endpoints/game_presets/router.py` - API router ✅
- `app/api/api_v1/endpoints/game_presets/__init__.py` - Package init ✅
- Updated `app/api/api_v1/api.py` - Registered router ✅

### API Endpoints:
```
GET    /api/v1/game-presets/          - List all active presets
GET    /api/v1/game-presets/{id}      - Get preset by ID
GET    /api/v1/game-presets/code/{code} - Get preset by code
POST   /api/v1/game-presets/          - Create preset (admin)
PATCH  /api/v1/game-presets/{id}      - Update preset (admin)
DELETE /api/v1/game-presets/{id}      - Delete preset (admin)
```

### Current Issues:
1. ❌ Backend crashes on GET /api/v1/game-presets/
   - Error: `'str' object has no attribute 'get'`
   - Location: router.py list_game_presets() → GamePresetSummary conversion
   - Root cause: Trying to use model properties (skills_tested, game_category, etc.) which return str/list but Pydantic expects different processing

### Fix Applied (Partial):
- Removed `from_attributes = True` from GamePresetSummary
- Changed fields to Optional with default=None
- **Still needs**: Router logic update to manually extract metadata from game_config JSONB

### Next Steps:
1. Update router.py `list_game_presets()` to manually extract metadata:
   ```python
   skills_tested=preset.game_config.get("skill_config", {}).get("skills_tested", [])
   game_category=preset.game_config.get("metadata", {}).get("game_category")
   # etc.
   ```

2. Restart backend and test API

3. Test all endpoints:
   - GET /api/v1/game-presets/ (list)
   - GET /api/v1/game-presets/1 (by ID)
   - GET /api/v1/game-presets/code/gan_footvolley (by code)

## 📋 Next Phases:

### Phase 3: Orchestrator Integration
- Add `game_preset_id` parameter to `execute_test()`
- Load preset config from database
- Merge preset + overrides
- Save both to tournament

### Phase 4: Streamlit UI
- Add Section 1: Game Type Selection (dropdown)
- Show preset details (skills, weights, probabilities)
- Optional Section 7: Override preset values
- Show configuration diff (preset vs final)

---

**Status**: Phase 1 ✅ Complete | Phase 2 🚧 Debugging | Phase 3-4 ⏳ Pending

**Current Blocker**: API router needs fixing to properly extract nested JSONB fields

**Time Spent**: ~45 minutes (migration, models, API scaffolding)
