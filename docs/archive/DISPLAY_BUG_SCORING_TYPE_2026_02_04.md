# Display Bug: scoring_type Shows PLACEMENT for HEAD_TO_HEAD Tournaments

**Date**: 2026-02-04
**Priority**: P2 (Display issue, not functional blocker)
**Affected**: Tournament 1069 (and potentially all HEAD_TO_HEAD tournaments)

---

## 🐛 Bug Description

The frontend displays `Format: INDIVIDUAL_RANKING` for HEAD_TO_HEAD tournaments (e.g., Tournament 1069) instead of showing the correct `HEAD_TO_HEAD` format.

**Observed Behavior**:
```
Format: INDIVIDUAL_RANKING
Participants: 0
```

**Expected Behavior**:
```
Format: HEAD_TO_HEAD (or GROUP_KNOCKOUT)
Participants: 7
```

---

## 🔍 Root Cause

### Backend Issue

**File**: `app/services/sandbox_test_orchestrator.py:239`

```python
# Extract INDIVIDUAL scoring config from game_config_overrides if present
scoring_type = "PLACEMENT"  # default ⚠️ WRONG - always sets PLACEMENT
number_of_rounds = 1  # default
```

**Problem**: The backend unconditionally sets `scoring_type = "PLACEMENT"` for ALL tournaments, including HEAD_TO_HEAD tournaments where this field should be `NULL` or not set.

### Database State

**Tournament 1069 Configuration**:
```sql
SELECT
    participant_type,
    scoring_type,
    tournament_type_id
FROM tournament_configurations
WHERE semester_id = 1069;
```

**Result**:
```
participant_type | scoring_type | tournament_type_id
-----------------+--------------+-------------------
INDIVIDUAL       | PLACEMENT    | (group_knockout type)
```

**Issue**: `scoring_type = "PLACEMENT"` is set even though this is a HEAD_TO_HEAD tournament.

### Frontend Display Logic

The frontend reads `scoring_type` from the API response and interprets:
- `scoring_type = "PLACEMENT"` → Display: "INDIVIDUAL_RANKING"
- `scoring_type = NULL` → Display: tournament format from `tournament_types.format`

**API Response** (`GET /api/v1/semesters/1069`):
```json
{
  "participant_type": "INDIVIDUAL",
  "scoring_type": "PLACEMENT",  // ⚠️ WRONG for HEAD_TO_HEAD
  "tournament_format": null
}
```

---

## ✅ Correct Behavior

### For HEAD_TO_HEAD Tournaments

**tournament_configurations** table should have:
```sql
participant_type = 'INDIVIDUAL'
scoring_type = NULL  -- ✅ or not set for HEAD_TO_HEAD
tournament_type_id = (id of group_knockout type)
```

**tournament_types** table (correctly set):
```sql
code = 'group_knockout'
format = 'HEAD_TO_HEAD'  -- ✅ Correct
display_name = 'Group Stage + Knockout'
```

### For INDIVIDUAL Tournaments

**tournament_configurations** table should have:
```sql
participant_type = 'INDIVIDUAL'
scoring_type = 'PLACEMENT'  -- ✅ Correct for INDIVIDUAL mode
tournament_type_id = (id of multi_round_ranking type)
```

---

## 🔧 Proposed Fix

### Option 1: Backend Logic Fix (Recommended)

**File**: `app/services/sandbox_test_orchestrator.py:236-252`

**Current Code**:
```python
# Extract INDIVIDUAL scoring config from game_config_overrides if present
scoring_type = "PLACEMENT"  # default ⚠️ WRONG
number_of_rounds = 1  # default
measurement_unit = None
ranking_direction = None

# Only override if individual_config is explicitly provided
if (game_config_overrides and
    "individual_config" in game_config_overrides and
    game_config_overrides["individual_config"] is not None):
    individual_config = game_config_overrides["individual_config"]
    scoring_type = individual_config.get("scoring_type", "PLACEMENT")
    number_of_rounds = individual_config.get("number_of_rounds", 1)
    measurement_unit = individual_config.get("measurement_unit")
    ranking_direction = individual_config.get("ranking_direction")
```

**Proposed Fix**:
```python
# Extract INDIVIDUAL scoring config from game_config_overrides if present
scoring_type = None  # ✅ Default to None for HEAD_TO_HEAD
number_of_rounds = None  # ✅ Default to None
measurement_unit = None
ranking_direction = None

# Only set these if individual_config is explicitly provided
if (game_config_overrides and
    "individual_config" in game_config_overrides and
    game_config_overrides["individual_config"] is not None):
    individual_config = game_config_overrides["individual_config"]
    scoring_type = individual_config.get("scoring_type", "PLACEMENT")  # Only for INDIVIDUAL mode
    number_of_rounds = individual_config.get("number_of_rounds", 1)
    measurement_unit = individual_config.get("measurement_unit")
    ranking_direction = individual_config.get("ranking_direction")
```

**Impact**: HEAD_TO_HEAD tournaments will have `scoring_type = NULL`, and the frontend will correctly display the format from `tournament_types.format`.

---

### Option 2: Frontend Display Logic Fix

**Alternative**: Update frontend to prioritize `tournament_types.format` over `scoring_type` when displaying tournament format.

**Pseudocode**:
```python
if tournament.tournament_type and tournament.tournament_type.format:
    display_format = tournament.tournament_type.format  # e.g., "HEAD_TO_HEAD"
elif tournament.scoring_type:
    display_format = "INDIVIDUAL_RANKING"
else:
    display_format = "Unknown"
```

**Trade-off**: This doesn't fix the backend data issue, just the display.

---

## 📊 Impact Assessment

### Functional Impact
- ✅ **No functional impact** - Tournament workflow works correctly
- ✅ Matches are played correctly (HEAD_TO_HEAD scoring works)
- ✅ Results are processed correctly
- ✅ Rewards are distributed correctly

### Display Impact
- ❌ **Incorrect format display** - Shows "INDIVIDUAL_RANKING" instead of "HEAD_TO_HEAD"
- ❌ **Participant count shows 0** - May be related to wrong format interpretation

### User Experience
- ⚠️ Users see incorrect tournament format
- ⚠️ May cause confusion when setting up tournaments
- ⚠️ Not a blocker for production, but should be fixed

---

## 🧪 Validation

### Test Cases to Verify Fix

**1. Create HEAD_TO_HEAD Tournament (League)**
```python
scoring_mode = "HEAD_TO_HEAD"
tournament_format = "league"
```

**Expected**:
```sql
scoring_type = NULL
tournament_type.format = "HEAD_TO_HEAD"
```

**Frontend Display**: `Format: HEAD_TO_HEAD`

---

**2. Create HEAD_TO_HEAD Tournament (Knockout)**
```python
scoring_mode = "HEAD_TO_HEAD"
tournament_format = "knockout"
```

**Expected**:
```sql
scoring_type = NULL
tournament_type.format = "HEAD_TO_HEAD"
```

**Frontend Display**: `Format: HEAD_TO_HEAD`

---

**3. Create INDIVIDUAL Tournament**
```python
scoring_mode = "INDIVIDUAL"
scoring_type = "PLACEMENT"
```

**Expected**:
```sql
scoring_type = "PLACEMENT"
tournament_type.format = "INDIVIDUAL_RANKING"
```

**Frontend Display**: `Format: INDIVIDUAL_RANKING`

---

## 📁 Related Files

### Backend
1. **`app/services/sandbox_test_orchestrator.py:236-252`** - Sets default scoring_type
2. **`app/models/tournament_configuration.py`** - TournamentConfiguration model
3. **`app/api/api_v1/endpoints/_semesters_main.py`** - API response serialization

### Database
4. **`tournament_configurations`** table - Stores scoring_type
5. **`tournament_types`** table - Stores format (HEAD_TO_HEAD, etc.)

### Frontend
6. **Streamlit admin panel** - Displays tournament format

---

## 🎯 Recommendation

**Priority**: P2 (Non-blocking display bug)

**Recommended Fix**: **Option 1 (Backend Logic Fix)**

**Reason**:
- Fixes root cause in data layer
- More maintainable long-term
- Prevents similar issues in future

**Timeline**:
- Can be fixed in next sprint
- Not a blocker for current production deployment

---

## 📝 Workaround

For existing tournaments with incorrect `scoring_type`:

```sql
-- Fix Tournament 1069
UPDATE tournament_configurations
SET scoring_type = NULL
WHERE semester_id = 1069
  AND tournament_type_id IN (
    SELECT id FROM tournament_types WHERE format = 'HEAD_TO_HEAD'
  );
```

**Note**: This only fixes display, doesn't affect functionality.

---

**Reported By**: User observation during validation
**Issue Created**: 2026-02-04
**Status**: DOCUMENTED (Not yet fixed)
**Priority**: P2
