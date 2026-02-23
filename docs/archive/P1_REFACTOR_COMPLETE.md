# P1 Refactoring Complete ✅

**Branch**: `refactor/p0-architecture-clean`
**Date**: 2026-01-29
**Scope**: Separate reward_config to own table (TournamentRewardConfig)
**Goal**: Clean separation of concerns, auditability, reusability

---

## Summary

Successfully completed P1 refactoring to extract reward configuration from the Semester model into a dedicated `TournamentRewardConfig` table. This achieves **clean layer separation** while maintaining 100% backward compatibility via property-based access.

---

## Changes Made

### 1. New Model: TournamentRewardConfig

#### File: `app/models/tournament_reward_config.py`

**New table structure:**
```python
class TournamentRewardConfig(Base):
    __tablename__ = "tournament_reward_configs"

    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey('semesters.id'), unique=True, nullable=False)
    reward_policy_name = Column(String(100), nullable=False, default="default")
    reward_policy_snapshot = Column(JSONB, nullable=True)
    reward_config = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
```

**Benefits:**
- ✅ Separate entity for reward policies
- ✅ 1:1 relationship with Semester (via FK)
- ✅ Audit timestamps (created_at, updated_at)
- ✅ Cascade delete (removed when semester deleted)

---

### 2. Database Migration

#### Migration: `alembic/versions/2026_01_29_1500-82956292b4e4_p1_separate_reward_config_to_own_table.py`

**Steps:**
1. **Create** `tournament_reward_configs` table
2. **Migrate** existing data from `semesters` table (70 records migrated)
3. **Drop** old columns from `semesters`:
   - `reward_config` (JSONB)
   - `reward_policy_name` (String)
   - `reward_policy_snapshot` (JSONB)

**Data Safety:**
- ✅ All existing reward configs preserved
- ✅ 70 records successfully migrated
- ✅ Zero data loss

---

### 3. Model Updates

#### File: `app/models/semester.py`

**Removed columns:**
```python
# REMOVED (P1):
reward_policy_name = Column(String(100), ...)
reward_policy_snapshot = Column(JSONB, ...)
reward_config = Column(JSONB, ...)
```

**Added relationship:**
```python
# NEW (P1):
reward_config_obj = relationship(
    "TournamentRewardConfig",
    uselist=False,
    back_populates="tournament",
    cascade="all, delete-orphan"
)
```

**Backward-compatible properties:**
```python
@property
def reward_config(self) -> dict:
    """Transparent access to reward_config via relationship"""
    if self.reward_config_obj:
        return self.reward_config_obj.reward_config or {}
    return {}

@property
def reward_policy_name(self) -> str:
    """Backward compatible property"""
    if self.reward_config_obj:
        return self.reward_config_obj.reward_policy_name
    return "default"

@property
def reward_policy_snapshot(self) -> dict:
    """Backward compatible property"""
    if self.reward_config_obj:
        return self.reward_config_obj.reward_policy_snapshot or {}
    return {}
```

---

### 4. Code Updates

#### File: `app/services/sandbox_test_orchestrator.py`

**Before (P0):**
```python
tournament = Semester(
    code=f"SANDBOX-{self.test_run_id}",
    name=f"SANDBOX-TEST-...",
    reward_config=reward_config_data  # Direct assignment
)
```

**After (P1):**
```python
tournament = Semester(
    code=f"SANDBOX-{self.test_run_id}",
    name=f"SANDBOX-TEST-...",
    # No reward_config here
)
self.db.add(tournament)
self.db.commit()

# Create separate TournamentRewardConfig
reward_config_obj = TournamentRewardConfig(
    semester_id=tournament.id,
    reward_policy_name="sandbox_test",
    reward_config=reward_config_data
)
self.db.add(reward_config_obj)
self.db.commit()
```

---

#### File: `app/api/api_v1/endpoints/tournaments/reward_config.py`

**Before (P0):**
```python
tournament.reward_config = config_dict
tournament.reward_policy_name = reward_config.template_name or "Custom"
db.commit()
```

**After (P1):**
```python
from app.models.tournament_reward_config import TournamentRewardConfig as TournamentRewardConfigModel

reward_config_obj = db.query(TournamentRewardConfigModel).filter(
    TournamentRewardConfigModel.semester_id == tournament_id
).first()

if reward_config_obj:
    # Update existing
    reward_config_obj.reward_policy_name = reward_config.template_name or "Custom"
    reward_config_obj.reward_config = config_dict
else:
    # Create new
    reward_config_obj = TournamentRewardConfigModel(
        semester_id=tournament_id,
        reward_policy_name=reward_config.template_name or "Custom",
        reward_config=config_dict
    )
    db.add(reward_config_obj)

db.commit()
```

---

#### File: `app/models/__init__.py`

**Added imports:**
```python
from .tournament_reward_config import TournamentRewardConfig  # P1: Separate reward config table
from .game_preset import GamePreset  # Missing import (fixed)

# In __all__:
"TournamentRewardConfig",
"GamePreset",
```

---

### 5. Code Compatibility

**Zero changes required** in reward orchestrator and most services:
- ✅ All existing code reads `semester.reward_config` (works via @property)
- ✅ No code was directly assigning to `semester.reward_config` (except sandbox/API, updated)
- ✅ Backward-compatible properties ensure transparent access

---

## Verification Results

### 1. Migration Success ✅
```bash
INFO  [alembic.runtime.migration] Running upgrade 562a39020263 -> 82956292b4e4, p1_separate_reward_config_to_own_table
```

### 2. Database Structure ✅
```sql
-- tournament_reward_configs table created:
\d tournament_reward_configs

-- Columns:
id, semester_id, reward_policy_name, reward_policy_snapshot, reward_config, created_at, updated_at

-- Indexes:
PRIMARY KEY (id)
UNIQUE (semester_id)
FK (semester_id) -> semesters(id) ON DELETE CASCADE
```

### 3. Data Migration ✅
```sql
SELECT COUNT(*) FROM tournament_reward_configs;
-- Result: 70 records migrated
```

### 4. Backward Compatibility ✅
```python
semester = db.query(Semester).filter(Semester.id == 160).first()

# Properties work transparently:
print(semester.reward_config)  # ✅ Returns dict from relationship
print(semester.reward_policy_name)  # ✅ Returns "default"
print(semester.reward_config_obj)  # ✅ Returns TournamentRewardConfig object
```

### 5. Model Import Test ✅
```python
from app.models import TournamentRewardConfig, Semester, GamePreset
# ✅ All models import successfully
# ✅ Semester has reward_config_obj relationship
```

---

## Benefits Achieved

### 1. Clean Separation of Concerns ✅
**Before:**
- Semester model: 150+ lines, mixing tournament info + config + game config + reward config

**After:**
- Semester model: Cleaner, focused on tournament info and configuration
- TournamentRewardConfig: Dedicated model for reward policies
- Clear boundaries between layers

### 2. Auditability ✅
**Before:**
- No timestamps for reward config changes
- Updates overwrite previous config

**After:**
- `created_at`: When reward config was first created
- `updated_at`: When reward config was last modified
- Future: Can add versioning for full audit trail

### 3. Reusability ✅
**Architecture enables (future):**
- Shared reward policies across multiple tournaments
- Reward policy templates (Standard, Championship, Friendly)
- Admin UI for managing reward policies separately

### 4. Data Integrity ✅
**Before:**
- Reward config could be NULL or inconsistent
- No FK constraints

**After:**
- 1:1 relationship enforced (UNIQUE constraint on semester_id)
- Cascade delete (reward config removed when tournament deleted)
- Default values (reward_policy_name defaults to "default")

### 5. Backward Compatibility ✅
- ✅ Existing code works without changes
- ✅ Property-based access is transparent
- ✅ No API contract changes
- ✅ No orchestrator changes

---

## Architecture Layers (After P1)

```
┌─────────────────────────────────────────────┐
│  TOURNAMENT INFORMATION LAYER               │  ← Semester (location, dates, theme)
├─────────────────────────────────────────────┤
│  CONFIGURATION LAYER                        │  ← Semester (type, max_players, status)
├─────────────────────────────────────────────┤
│  GAME CONFIGURATION LAYER                   │  ← game_config, game_preset_id (skills, weights)
├─────────────────────────────────────────────┤
│  REWARD CONFIGURATION LAYER (P1)            │  ← TournamentRewardConfig (separate table!) ✅
└─────────────────────────────────────────────┘
```

**Progress:**
- ✅ P0: Remove deprecated fields, derive format from tournament_type
- ✅ **P1: Separate reward_config to own table** (THIS REFACTOR)
- ⏳ P2: Separate tournament configuration to own table (future)
- ⏳ P3: Separate game configuration to own table (future)

---

## Next Steps (Optional)

### P2: Separate Tournament Configuration
**Estimated effort**: 6-8 hours
**Priority**: Medium
**Benefit**: Full separation of tournament info vs configuration

### P3: Separate Game Configuration
**Estimated effort**: 4-6 hours
**Priority**: Low
**Benefit**: Versioning, audit trail for game config changes

---

## Rollback Plan

If issues are discovered:

```bash
# Downgrade migration
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" alembic downgrade -1

# This will:
# 1. Re-add reward_config, reward_policy_name, reward_policy_snapshot columns to semesters
# 2. Migrate data back from tournament_reward_configs
# 3. Drop tournament_reward_configs table
```

---

## Testing Checklist

- [x] Migration runs without errors
- [x] Database schema correct (new table created, old columns removed)
- [x] Data migration successful (70 records migrated)
- [x] Backward-compatible properties work
- [x] Models import without errors
- [x] Existing tournaments load correctly
- [x] Reward config accessible via property
- [x] Sandbox orchestrator creates separate reward config
- [x] API endpoints create/update separate reward config

---

## Files Changed

### New Files:
1. `app/models/tournament_reward_config.py` - New model
2. `alembic/versions/2026_01_29_1500-82956292b4e4_p1_separate_reward_config_to_own_table.py` - P1 migration
3. `P1_REFACTOR_COMPLETE.md` - This documentation

### Modified Files:
1. `app/models/semester.py` - Removed columns, added relationship + properties
2. `app/models/__init__.py` - Added TournamentRewardConfig and GamePreset imports
3. `app/services/sandbox_test_orchestrator.py` - Create separate reward config
4. `app/api/api_v1/endpoints/tournaments/reward_config.py` - Create/update separate reward config

---

## Commits

Branch: `refactor/p0-architecture-clean`

Proposed commits:
1. `feat(models): P1 - Add TournamentRewardConfig model for reward policy separation`
2. `feat(db): P1 - Migrate reward_config to separate table (tournament_reward_configs)`
3. `refactor(api): P1 - Update API endpoints to use TournamentRewardConfig table`
4. `refactor(services): P1 - Update orchestrators to create separate reward config records`

---

## References

- **Architecture Audit**: `TOURNAMENT_ARCHITECTURE_AUDIT.md`
- **P0 Documentation**: `P0_REFACTOR_COMPLETE.md`
- **Migration**: `alembic/versions/2026_01_29_1500-82956292b4e4_p1_separate_reward_config_to_own_table.py`
- **Model**: `app/models/tournament_reward_config.py`
- **Semester Model**: `app/models/semester.py`

---

**Status**: ✅ COMPLETE - Ready for review and merge

**Migration Impact**:
- 70 existing tournament reward configs migrated successfully
- Zero data loss
- 100% backward compatible
- Zero production issues expected
