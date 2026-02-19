# FIX LOG: INDIVIDUAL Tournament Session Generation

**Date**: 2026-01-31
**Sprint**: P3 Week 3
**Status**: ✅ RESOLVED
**Affected Tournaments**: 202-210 (failed), 211+ (working)

---

## Problem Summary

INDIVIDUAL tournaments were failing during session generation with various errors:
1. **500 Internal Server Error** - Format dispatch to wrong generator
2. **400 Bad Request** - Validation rejecting tournaments with tournament_type_id
3. **AttributeError** - Read-only property `sessions_generated`
4. **405 Method Not Allowed** - Missing GET sessions endpoint

---

## Root Causes

### Issue #1: Format Override from Game Preset
**File**: `app/services/sandbox_test_orchestrator.py`
**Lines**: 340-348 (before fix)

**Problem**:
- INDIVIDUAL tournaments were using `game_preset_id=3` ("Stole My Goal")
- Game preset contained `format_config: {"HEAD_TO_HEAD": {...}}`
- `Semester.format` property fallback chain:
  1. `tournament_type.format` (NULL for INDIVIDUAL)
  2. `game_preset.format_config` ← **Found HEAD_TO_HEAD here!**
  3. Default: "INDIVIDUAL_RANKING" (never reached)
- Session generator dispatched to HEAD_TO_HEAD generator instead of INDIVIDUAL_RANKING generator → crash

**Evidence**:
```
Tournament 209 config:
  tournament_type_id = NULL ✅
  game_preset_id = 3 ❌
  format = "HEAD_TO_HEAD" ❌ (from game_preset)

Error: "HEAD_TO_HEAD tournaments require a tournament type (Swiss, League, Knockout, etc.)"
```

---

### Issue #2: Tournament Type ID Should Be NULL
**File**: `app/services/sandbox_test_orchestrator.py`
**Lines**: 240-254

**Problem**:
- Initial fix attempted to set `tournament_type_id=5` (multi_round_ranking)
- Validation layer explicitly rejects INDIVIDUAL_RANKING tournaments with tournament_type_id:
  ```python
  # generation_validator.py:45-46
  if tournament.format == "INDIVIDUAL_RANKING":
      if tournament.tournament_type_id is not None:
          return False, "INDIVIDUAL_RANKING tournaments cannot have a tournament type"
  ```

**Evidence**:
```
Tournament 206 config:
  tournament_type_id = 5 ❌
  format = "INDIVIDUAL_RANKING" ✅

Error: "INDIVIDUAL_RANKING tournaments cannot have a tournament type"
```

---

### Issue #3: Read-Only Property sessions_generated
**File**: `app/services/tournament/session_generation/session_generator.py`
**Lines**: 244-246 (before fix)

**Problem**:
- Code tried: `tournament.sessions_generated = True`
- `sessions_generated` is a `@property` with no setter:
  ```python
  @property
  def sessions_generated(self) -> bool:
      if self.tournament_config_obj:
          return self.tournament_config_obj.sessions_generated
      return False
  ```
- Actual data lives in `TournamentConfiguration.sessions_generated`

**Evidence**:
```
Tournament 210 logs:
  ✅ Session 1411 created successfully
  ❌ AttributeError: property 'sessions_generated' of 'Semester' object has no setter
  🔄 Database rolled back
```

---

### Issue #4: Missing GET Sessions Endpoint
**File**: `app/api/api_v1/endpoints/tournaments/generate_sessions.py`

**Problem**:
- Streamlit calls `GET /api/v1/tournaments/{id}/sessions`
- Endpoint didn't exist → 405 Method Not Allowed
- Sessions were created successfully but couldn't be fetched

**Evidence**:
```
Tournament 211:
  POST /api/v1/tournaments/211/generate-sessions → 200 OK ✅
  GET /api/v1/tournaments/211/sessions → 405 Method Not Allowed ❌
```

---

## Solutions Implemented

### Fix #1: Disable game_preset_id for INDIVIDUAL Tournaments
**File**: `app/services/sandbox_test_orchestrator.py:340-355`

```python
# 🎯 CRITICAL FIX: INDIVIDUAL_RANKING tournaments should NOT have game_preset_id
# because game presets contain format_config that might override the format property
# to HEAD_TO_HEAD instead of INDIVIDUAL_RANKING
if is_individual_ranking:
    logger.info(f"🔄 Setting game_preset_id=NULL for INDIVIDUAL_RANKING tournament (to avoid format override)")
    game_preset_id_value = None
else:
    game_preset_id_value = game_preset_id

game_config_obj = GameConfiguration(
    semester_id=tournament.id,
    game_preset_id=game_preset_id_value,  # NULL for INDIVIDUAL
    game_config=final_game_config,
    game_config_overrides=game_config_overrides
)
```

**Result**: `Semester.format` now correctly returns "INDIVIDUAL_RANKING" via default fallback

---

### Fix #2: Keep tournament_type_id=NULL for INDIVIDUAL
**File**: `app/services/sandbox_test_orchestrator.py:240-254`

```python
# 🎯 CRITICAL FIX: INDIVIDUAL_RANKING tournaments MUST NOT have tournament_type_id
# The Semester.format property has a fallback chain:
# 1. tournament_type.format (if tournament_type_id is set)
# 2. game_preset.format_config (if game_preset_id is set)
# 3. Default: "INDIVIDUAL_RANKING"
# For INDIVIDUAL tournaments, we use the default fallback (tournament_type_id=NULL)
# For HEAD_TO_HEAD tournaments, we use the requested tournament type (league, knockout, etc.)
if is_individual_ranking:
    tournament_type_id_value = None  # NULL for INDIVIDUAL_RANKING
    logger.info(f"🔄 Setting tournament_type_id=NULL for INDIVIDUAL_RANKING tournament (format will use default fallback)")
else:
    tournament_type_id_value = tournament_type.id  # Set for HEAD_TO_HEAD tournaments

tournament_config_obj = TournamentConfiguration(
    semester_id=tournament.id,
    tournament_type_id=tournament_type_id_value,
    # ...
)
```

**Result**: Validation passes, format correctly set to INDIVIDUAL_RANKING

---

### Fix #3: Update TournamentConfiguration Directly
**File**: `app/services/tournament/session_generation/session_generator.py:243-251`

```python
# Mark tournament as sessions_generated
# 🎯 FIX: sessions_generated is a read-only property, update the config object directly
if tournament.tournament_config_obj:
    tournament.tournament_config_obj.sessions_generated = True
    tournament.tournament_config_obj.sessions_generated_at = datetime.utcnow()
    logger.info(f"✅ Marked tournament as sessions_generated at {tournament.tournament_config_obj.sessions_generated_at}")
else:
    logger.error(f"❌ No tournament_config_obj found for tournament {tournament_id}")
    raise ValueError(f"Tournament {tournament_id} has no TournamentConfiguration object")
```

**Result**: sessions_generated flag properly set in database

---

### Fix #4: Add GET Sessions Endpoint
**File**: `app/api/api_v1/endpoints/tournaments/generate_sessions.py:298-343`

```python
@router.get("/{tournament_id}/sessions", response_model=List[Dict[str, Any]])
def get_tournament_sessions(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> List[Dict[str, Any]]:
    """Get all sessions for a tournament"""
    sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id
    ).order_by(SessionModel.date_start).all()

    # Convert to dict format with all session details
    sessions_list = []
    for session in sessions:
        sessions_list.append({
            "id": session.id,
            "title": session.title,
            "description": session.description,
            # ... all session fields
        })
    return sessions_list
```

**Result**: Streamlit can now fetch and display sessions

---

### Bonus: Detailed Debug Logging Added
**Files**:
- `app/services/tournament/session_generation/session_generator.py`
- `app/services/tournament/session_generation/formats/individual_ranking_generator.py`

**Added**:
- ✅ Try-catch blocks around critical sections
- ✅ Detailed logging for every step (tournament config, player count, format dispatch, session creation)
- ✅ Full stack trace on exceptions
- ✅ Database rollback on errors

**Example logs**:
```
🔍 SESSION GENERATION START - Tournament ID: 211
🏆 Tournament fetched: id=211, name=LFA Sandbox Tournament
📋 Tournament format property: INDIVIDUAL_RANKING
🎯 INDIVIDUAL_RANKING tournament detected
👥 Enrolled player count: 8
🔧 Calling individual_ranking_generator.generate() with:
   - tournament_id: 211
   - player_count: 8
   - number_of_rounds: 3
✅ individual_ranking_generator.generate() returned 1 sessions
📝 Creating session 1/1: LFA Sandbox Tournament
✅ Session 1 created successfully with ID: 1412
✅ Marked tournament as sessions_generated
✅ Database commit successful
🎉 SESSION GENERATION COMPLETE - Generated 1 sessions for 8 players
```

---

## Verification

### Test Tournament 211 (Successful)
```
Configuration:
  tournament_type_id: NULL ✅
  game_preset_id: NULL ✅
  format: INDIVIDUAL_RANKING ✅
  scoring_type: SCORE_BASED ✅
  number_of_rounds: 3 ✅

Session Created:
  id: 1412 ✅
  title: LFA Sandbox Tournament ✅
  game_type: Individual Ranking Competition ✅
  tournament_phase: INDIVIDUAL_RANKING ✅
  match_format: INDIVIDUAL_RANKING ✅
  scoring_type: SCORE_BASED ✅
  participant_user_ids: [6, 4, 16, 13, 5, 7, 14, 15] (8 players) ✅
  rounds_data: {"total_rounds": 3, "completed_rounds": 0, "round_results": {}} ✅

API Endpoints:
  POST /api/v1/tournaments/211/generate-sessions → 200 OK ✅
  GET /api/v1/tournaments/211/sessions → 200 OK ✅

Streamlit UI:
  Step 1: Tournament created ✅
  Step 2: Session fetched and displayed ✅
  Step 3: Attendance tracking ready ✅
```

---

## Impact

### Before Fixes
- ❌ All INDIVIDUAL tournaments failed session generation
- ❌ 500 errors, 400 errors, or database rollbacks
- ❌ No sessions created
- ❌ Streamlit couldn't display sessions

### After Fixes
- ✅ INDIVIDUAL tournaments successfully generate sessions
- ✅ Correct format dispatch (INDIVIDUAL_RANKING generator)
- ✅ Sessions properly created in database
- ✅ Streamlit displays sessions correctly
- ✅ Full debug visibility for troubleshooting

---

## Related Files Changed

1. `app/services/sandbox_test_orchestrator.py` (2 fixes)
2. `app/services/tournament/session_generation/session_generator.py` (1 fix + logging)
3. `app/services/tournament/session_generation/formats/individual_ranking_generator.py` (logging)
4. `app/api/api_v1/endpoints/tournaments/generate_sessions.py` (1 new endpoint)

---

## Lessons Learned

1. **Property Fallback Chains**: Be aware of property fallback logic - intermediate values can override defaults
2. **Read-Only Properties**: Always check if properties have setters before assignment
3. **Validation Layer**: Understand validation constraints before implementing fixes
4. **Debug Logging**: Comprehensive logging is essential for distributed systems debugging
5. **API Completeness**: Ensure all CRUD operations have corresponding endpoints

---

## Next Steps

1. ✅ Document fixes (this file)
2. 🔄 Clarify INDIVIDUAL score entry flow (Step 4)
3. 🔄 Test complete tournament workflow (Steps 3-6)
4. 🔄 Update CHANGELOG with milestone completion
