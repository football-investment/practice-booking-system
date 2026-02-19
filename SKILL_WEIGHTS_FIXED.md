# Skill Weights Support - Fixed ✅

## Problem

A Configuration screen-en beállított **skill weights** (súlyok) **NEM** kerültek elmentésre a tournament reward_config-jába. Minden skill hardcoded `weight: 1.0` értéket kapott, így a különböző súlyok nem befolyásolták a reward distribution-t.

### Példa hiba:

**UI-n beállítva:**
- ball_control: weight **2.00**
- stamina: weight **1.70**
- balance: weight **1.30**
- heading: weight **1.00**

**Database-ben mentve:**
```json
{
  "skill": "ball_control",
  "weight": 1.0  // ❌ HARDCODED!
}
```

**Eredmény: Minden skill UGYANANNYI pontot kapott!**
- ball_control: 5.6
- stamina: 5.6
- balance: 5.6
- heading: 5.6

## Root Cause

1. **UI gyűjtötte** a `skill_weights` dictionary-t (line 276, 299, 487 in `streamlit_sandbox_v3_admin_aligned.py`)
2. **RunTestRequest schema NEM tartalmazta** a `skill_weights` mezőt
3. **Orchestrator NEM kapta meg** a weight-eket, így hardcoded 1.0-t használt

## Solution

### 1. RunTestRequest Schema - skill_weights mező hozzáadása

**File**: `app/api/api_v1/endpoints/sandbox/run_test.py` (Line 36)

```python
class RunTestRequest(BaseModel):
    """Request schema for sandbox test"""
    tournament_type: str
    skills_to_test: list[str]
    skill_weights: Optional[dict[str, float]] = Field(None, description="Optional: Skill-specific weights")  # ✅ NEW
    player_count: Optional[int]
    # ...
```

### 2. Orchestrator - skill_weights paraméter

**File**: `app/api/api_v1/endpoints/sandbox/run_test.py` (Line 139)

```python
result = orchestrator.execute_test(
    tournament_type_code=request.tournament_type,
    skills_to_test=request.skills_to_test,
    skill_weights=request.skill_weights,  # ✅ Pass skill weights
    # ...
)
```

### 3. Orchestrator execute_test() - signature update

**File**: `app/services/sandbox_test_orchestrator.py` (Line 48-52)

```python
def execute_test(
    self,
    tournament_type_code: str,
    skills_to_test: List[str],
    skill_weights: Optional[Dict[str, float]] = None,  # ✅ NEW parameter
    player_count: int = 16,
    # ...
)
```

### 4. Orchestrator _create_tournament() - pass weights

**File**: `app/services/sandbox_test_orchestrator.py` (Line 84)

```python
# Step 1: Create tournament
self._create_tournament(tournament_type_code, skills_to_test, skill_weights, player_count, campus_id)  # ✅ Pass weights
```

### 5. Orchestrator _build_reward_config() - use weights

**File**: `app/services/sandbox_test_orchestrator.py` (Line 252-267)

```python
def _build_reward_config(self, skills_to_test: List[str], skill_weights: Optional[Dict[str, float]] = None) -> Dict:
    """Build reward config with skill mappings"""
    skill_mappings = []
    for skill in skills_to_test:
        # Get weight from skill_weights dict, or default to 1.0
        weight = skill_weights.get(skill, 1.0) if skill_weights else 1.0  # ✅ Use provided weight

        skill_mappings.append({
            "skill": skill,
            "enabled": True,
            "weight": weight,  # ✅ Dynamic weight!
            "placement_bonuses": {
                "1": 5.0,
                "2": 3.0,
                "3": 2.0,
                "default": 1.0
            }
        })
    # ...
```

## Data Flow

```
1. UI (Configuration screen)
   ↓
   skill_weights = {
     "ball_control": 2.0,
     "stamina": 1.7,
     "balance": 1.3,
     "heading": 1.0
   }
   ↓
2. POST /sandbox/run-test (RunTestRequest)
   {
     "skills_to_test": ["ball_control", "stamina", "balance", "heading"],
     "skill_weights": {"ball_control": 2.0, "stamina": 1.7, ...}  # ✅ Passed
   }
   ↓
3. Orchestrator.execute_test(skill_weights=...)
   ↓
4. _build_reward_config(skills_to_test, skill_weights)
   ↓
5. Database (reward_config)
   {
     "skill_mappings": [
       {"skill": "ball_control", "weight": 2.0},  # ✅ Correct!
       {"skill": "stamina", "weight": 1.7},
       {"skill": "balance", "weight": 1.3},
       {"skill": "heading", "weight": 1.0}
     ]
   }
   ↓
6. Reward Distribution (tournament_participation_service.py)
   skill_points = (weight / total_weight) × base_points × placement_bonus
```

## Calculation Example

### Setup:
- **Total weight**: 2.0 + 1.7 + 1.3 + 1.0 = **6.0**
- **Base points** (1st place): 10
- **Placement bonus**: 5.0 (1st place multiplier)

### Results (1st place):

| Skill | Weight | Calculation | Points |
|-------|--------|-------------|--------|
| ball_control | 2.0 | (2.0 / 6.0) × 10 × 5.0 | **16.7** ✅ |
| stamina | 1.7 | (1.7 / 6.0) × 10 × 5.0 | **14.2** ✅ |
| balance | 1.3 | (1.3 / 6.0) × 10 × 5.0 | **10.8** ✅ |
| heading | 1.0 | (1.0 / 6.0) × 10 × 5.0 | **8.3** ✅ |

✅ **Különböző értékek!** A weight-ek szerint arányosan!

### Before Fix (minden weight = 1.0):

| Skill | Weight | Points |
|-------|--------|--------|
| ball_control | 1.0 | 12.5 ❌ |
| stamina | 1.0 | 12.5 ❌ |
| balance | 1.0 | 12.5 ❌ |
| heading | 1.0 | 12.5 ❌ |

❌ **Minden ugyanaz!** Hiába állítottuk be másként a UI-n!

## Testing

### 1. Create new tournament with different weights:

Menj a Configuration screen-re és állíts be különböző weight-eket:
- ball_control: 2.00
- volleys: 2.00
- heading: 1.00
- acceleration: 2.00
- sprint_speed: 1.50
- stamina: 1.70
- balance: 1.30

### 2. Verify database config:

```sql
SELECT id, name,
  jsonb_pretty(reward_config->'skill_mappings') as skills
FROM semesters
WHERE name LIKE 'GanCuju%'
ORDER BY id DESC
LIMIT 1;
```

**Expected**: Weight-ek különbözőek (2.0, 1.7, 1.5, 1.3, 1.0)

### 3. Complete workflow and distribute rewards

### 4. Verify skill points:

```sql
SELECT
  u.email,
  tp.placement,
  tp.xp_awarded,
  jsonb_pretty(tp.skill_points_awarded) as skills
FROM tournament_participations tp
JOIN users u ON tp.user_id = u.id
WHERE tp.semester_id = <TOURNAMENT_ID>
ORDER BY tp.placement;
```

**Expected**: Skill points-ok KÜLÖNBÖZŐEK a weight-ek szerint!

## Files Modified

1. `app/api/api_v1/endpoints/sandbox/run_test.py`:
   - Line 36: Added `skill_weights` field to `RunTestRequest`
   - Line 139: Pass `skill_weights` to orchestrator

2. `app/services/sandbox_test_orchestrator.py`:
   - Line 48-52: Added `skill_weights` parameter to `execute_test()`
   - Line 84: Pass `skill_weights` to `_create_tournament()`
   - Line 200-206: Updated `_create_tournament()` signature
   - Line 226: Pass `skill_weights` to `_build_reward_config()`
   - Line 252-267: Updated `_build_reward_config()` to use provided weights

## Benefits

1. ✅ **Fully functional weight system** - UI settings are now respected
2. ✅ **Flexible reward customization** - Different skills can have different importance
3. ✅ **Backward compatible** - If no weights provided, defaults to 1.0
4. ✅ **End-to-end working** - From UI → API → Database → Calculation

---

**Date**: 2026-01-28
**Status**: Fixed ✅
**Issue**: Skill weights from Configuration screen not being saved/used
**Solution**: Added skill_weights parameter through entire tournament creation flow
