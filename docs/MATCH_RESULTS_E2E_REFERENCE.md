# Match Results E2E Technical Reference

**Version**: 1.0
**Date**: 2026-01-22
**Status**: Production Ready (INDIVIDUAL_RANKING only)

## Purpose

This document provides a comprehensive technical reference for the **Match Structure / Performance Results** flow in the tournament system. Use this as the reference pattern when implementing new match formats (HEAD_TO_HEAD, TEAM_MATCH, etc.).

---

## Architecture Overview

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ UI Layer (Streamlit)                                                    │
│ - Match Command Center                                                  │
│ - Attendance marking                                                    │
│ - Dynamic result entry forms (format-specific)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ POST /submit-results
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ API Layer (FastAPI)                                                     │
│ - /active-match: Returns match_format, scoring_type, structure_config  │
│ - /submit-results: Receives structured performance data                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Validate + Process
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ ResultProcessor Service                                                 │
│ - Validates result format                                               │
│ - Converts performance data → derived rankings                          │
│ - Format-specific processors (INDIVIDUAL_RANKING, HEAD_TO_HEAD, etc.)  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ (user_id, rank) tuples
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PointsCalculatorService                                                 │
│ - Applies base points (1st=3, 2nd=2, 3rd=1)                            │
│ - Applies tier multipliers (TIERED mode)                               │
│ - Applies pod modifiers (PERFORMANCE_POD mode)                          │
│ - Returns points_map: {user_id: points}                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Update DB
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Database Layer                                                          │
│ - tournament_rankings: total_points updated                             │
│ - sessions.game_results: Raw performance data stored                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Refresh UI
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Leaderboard Update                                                      │
│ - Rankings recalculated                                                 │
│ - UI shows updated standings                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Concepts

1. **Performance Data**: Raw match results (scores, times, placements, ratings)
2. **Derived Ranking**: Rankings calculated FROM performance data
3. **Points Calculation**: Points awarded based on rankings + modifiers
4. **Match Format**: HOW participants compete (INDIVIDUAL_RANKING, HEAD_TO_HEAD, etc.)
5. **Scoring Type**: HOW performance is measured (PLACEMENT, SCORE_BASED, TIME_BASED, etc.)

---

## E2E Flow: INDIVIDUAL_RANKING

This is the **reference implementation** for all match formats.

### Step 1: Session Generation (Backend)

**Location**: `app/services/tournament_session_generator.py`

```python
# League tournament session generation
sessions.append({
    'title': f'{tournament.name} - Ranking Round {round_num}',
    'semester_id': tournament.id,
    'instructor_id': tournament.master_instructor_id,
    # ... datetime, location, etc.

    # ✅ RANKING METADATA
    'ranking_mode': 'ALL_PARTICIPANTS',
    'expected_participants': player_count,
    'participant_filter': None,
    'group_identifier': None,
    'pod_tier': None,

    # ✅ MATCH STRUCTURE METADATA
    'match_format': 'INDIVIDUAL_RANKING',
    'scoring_type': 'PLACEMENT',
    'structure_config': {
        'expected_participants': player_count,
        'ranking_criteria': 'final_placement'
    }
})
```

**Key Points**:
- `match_format` and `scoring_type` are set during session generation
- `structure_config` contains format-specific metadata (JSONB)
- All new fields are nullable for backward compatibility

---

### Step 2: Frontend Fetches Active Match

**Location**: `streamlit_app/components/tournaments/instructor/match_command_center.py`

**API Call**:
```python
GET /api/v1/tournaments/{tournament_id}/active-match
```

**Response**:
```json
{
  "active_match": {
    "session_id": 123,
    "match_name": "Test Tournament - Ranking Round 1",
    "participants": [...],
    "ranking_mode": "ALL_PARTICIPANTS",
    "match_format": "INDIVIDUAL_RANKING",       // ✅ NEW
    "scoring_type": "PLACEMENT",                // ✅ NEW
    "structure_config": {                       // ✅ NEW
      "expected_participants": 8,
      "ranking_criteria": "final_placement"
    }
  }
}
```

**Frontend Usage**:
```python
match_format = match.get('match_format', 'INDIVIDUAL_RANKING')
scoring_type = match.get('scoring_type', 'PLACEMENT')
structure_config = match.get('structure_config', {})
```

---

### Step 3: Attendance Marking

**UI**: 2-button interface (Present/Absent)

**API Call**:
```python
POST /api/v1/attendance/
{
  "user_id": 1,
  "session_id": 123,
  "booking_id": 456,
  "status": "present"
}
```

**Frontend Code**:
```python
def render_attendance_step(token: str, match: Dict[str, Any]):
    for participant in participants:
        if st.button("✅ Present"):
            mark_attendance(token, session_id, user_id, booking_id, "present")
        if st.button("❌ Absent"):
            mark_attendance(token, session_id, user_id, booking_id, "absent")
```

---

### Step 4: Dynamic Result Form Rendering

**Location**: `streamlit_app/components/tournaments/instructor/match_command_center.py:340-386`

**Dispatch Logic**:
```python
def render_results_step(token, tournament_id, match):
    match_format = match.get('match_format', 'INDIVIDUAL_RANKING')

    # Dispatch to format-specific UI
    if match_format == 'INDIVIDUAL_RANKING':
        render_individual_ranking_form(...)
    elif match_format == 'HEAD_TO_HEAD':
        render_head_to_head_form(...)  # Future
    elif match_format == 'SKILL_RATING':
        st.error("❌ SKILL_RATING not implemented")
    else:
        st.error(f"❌ Format '{match_format}' not supported")
```

**INDIVIDUAL_RANKING Form**:
```python
def render_individual_ranking_form(token, tournament_id, match, present_participants):
    # Dropdown for each present participant
    for participant in present_participants:
        placement = st.selectbox(
            "Placement",
            options=["Not Ranked"] + ["1", "2", "3", ..., "N"]
        )

        # Store in structured format
        if placement != "Not Ranked":
            results_dict[participant['user_id']] = {
                "user_id": participant['user_id'],
                "placement": int(placement)
            }

    # Submit button
    if st.button("🏅 Submit Results"):
        results_list = list(results_dict.values())
        submit_match_results(token, tournament_id, session_id, results_list, notes)
```

**Data Format**:
```python
results = [
    {"user_id": 1, "placement": 1},
    {"user_id": 2, "placement": 2},
    {"user_id": 3, "placement": 3},
    {"user_id": 4, "placement": 4}
]
```

---

### Step 5: Submit Results to API

**API Call**:
```python
POST /api/v1/tournaments/{tournament_id}/sessions/{session_id}/submit-results
{
  "results": [
    {"user_id": 1, "placement": 1},
    {"user_id": 2, "placement": 2},
    {"user_id": 3, "placement": 3},
    {"user_id": 4, "placement": 4}
  ],
  "notes": "Great match! All players showed excellent sportsmanship."
}
```

**Frontend Helper**:
```python
def submit_match_results(token, tournament_id, session_id, results, notes=None):
    url = f"http://localhost:8000/api/v1/tournaments/{tournament_id}/sessions/{session_id}/submit-results"
    payload = {"results": results, "notes": notes}
    response = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload)
    return response.status_code in [200, 201], response.json().get("detail", "")
```

---

### Step 6: API Processing (Backend)

**Location**: `app/api/api_v1/endpoints/tournaments/instructor.py:1973-2186`

**Flow**:

#### 6.1 Authorization Check
```python
# Check user is instructor assigned to tournament or admin
if current_user.role == UserRole.INSTRUCTOR:
    if tournament.master_instructor_id != current_user.id:
        raise HTTPException(403, "Not assigned to tournament")
```

#### 6.2 Get Session & Validate
```python
session = db.query(SessionModel).filter(
    SessionModel.id == session_id,
    SessionModel.semester_id == tournament_id
).first()

if session.game_results is not None:
    raise HTTPException(400, "Results already recorded")
```

#### 6.3 Validate Results Format
```python
from app.services.tournament.result_processor import ResultProcessor

result_processor = ResultProcessor(db)
match_format = session.match_format or 'INDIVIDUAL_RANKING'

is_valid, error_msg = result_processor.validate_results(
    match_format=match_format,
    results=result_data.results,
    expected_participants=session.expected_participants
)

if not is_valid:
    raise HTTPException(400, f"Invalid results: {error_msg}")
```

**Validation for INDIVIDUAL_RANKING**:
- ✅ All results have `user_id` and `placement` fields
- ✅ No duplicate placements
- ✅ Placements start from 1
- ✅ Participant count matches expected (optional)

#### 6.4 Process Results → Derive Rankings
```python
try:
    derived_rankings = result_processor.process_results(
        session_id=session_id,
        match_format=match_format,
        results=result_data.results,
        structure_config=session.structure_config
    )
except NotImplementedError as e:
    # SKILL_RATING not implemented
    raise HTTPException(501, str(e))
```

**Output**: `[(user_id, rank), ...]`
```python
derived_rankings = [
    (1, 1),  # user_id=1, rank=1
    (2, 2),
    (3, 3),
    (4, 4)
]
```

**ResultProcessor Logic** (`app/services/tournament/result_processor.py:183-205`):
```python
def _process_individual_ranking(self, results):
    rankings = []
    for result in results:
        user_id = result.get("user_id")
        placement = result.get("placement")
        rankings.append((user_id, placement))

    # Sort by placement (ascending)
    rankings.sort(key=lambda x: x[1])
    return rankings
```

#### 6.5 Calculate Points
```python
from app.services.tournament.points_calculator_service import PointsCalculatorService

points_calculator = PointsCalculatorService(db)
tournament_config = points_calculator.get_tournament_type_config(tournament_id)

points_map = points_calculator.calculate_points_batch(
    session_id=session_id,
    rankings=derived_rankings,
    tournament_type_config=tournament_config
)
```

**Output**: `{user_id: points}`
```python
points_map = {
    1: 3.0,  # 1st place: 3 pts
    2: 2.0,  # 2nd place: 2 pts
    3: 1.0,  # 3rd place: 1 pt
    4: 0.0   # 4th place: 0 pts
}
```

**Points Calculation Logic**:
1. Get base points from tournament config or default (1st=3, 2nd=2, 3rd=1)
2. Apply tier multiplier if `ranking_mode='TIERED'`:
   - Tier 1: 1.0x (Quarter-Finals)
   - Tier 2: 1.5x (Semi-Finals)
   - Tier 3: 2.0x (Finals)
3. Apply pod modifier if `ranking_mode='PERFORMANCE_POD'`:
   - Pod 1 (Top): 1.2x
   - Pod 2 (Middle): 1.0x
   - Pod 3 (Bottom): 0.8x

**Example with Tier**:
```python
# Finals session (tier=3, multiplier=2.0)
# 1st place: 3 * 2.0 = 6.0 pts
# 2nd place: 2 * 2.0 = 4.0 pts
# 3rd place: 1 * 2.0 = 2.0 pts
```

#### 6.6 Update Tournament Rankings
```python
for user_id, rank in derived_rankings:
    points_earned = points_map.get(user_id, 0.0)

    # Check if ranking exists
    ranking = db.execute(
        text("SELECT id FROM tournament_rankings WHERE tournament_id = :tid AND user_id = :uid"),
        {"tid": tournament_id, "uid": user_id}
    ).fetchone()

    if ranking:
        # Update existing
        db.execute(
            text("""
            UPDATE tournament_rankings
            SET total_points = total_points + :points,
                matches_played = matches_played + 1
            WHERE tournament_id = :tid AND user_id = :uid
            """),
            {"points": points_earned, "tid": tournament_id, "uid": user_id}
        )
    else:
        # Create new
        db.execute(
            text("""
            INSERT INTO tournament_rankings (tournament_id, user_id, total_points, matches_played)
            VALUES (:tid, :uid, :points, 1)
            """),
            {"tid": tournament_id, "uid": user_id, "points": points_earned}
        )
```

#### 6.7 Store Results in Session
```python
results_dict = {
    "match_format": match_format,
    "submitted_at": datetime.utcnow().isoformat(),
    "submitted_by": current_user.id,
    "raw_results": result_data.results,           # Original performance data
    "derived_rankings": [{"user_id": uid, "rank": rank} for uid, rank in derived_rankings],
    "points_awarded": {str(uid): pts for uid, pts in points_map.items()},
    "notes": result_data.notes
}

session.game_results = json.dumps(results_dict)
db.commit()
```

#### 6.8 Return Success Response
```python
return {
    "success": True,
    "message": "Results recorded successfully for 4 participants",
    "session_id": session_id,
    "match_format": match_format,
    "rankings": [
        {"user_id": 1, "rank": 1, "points_earned": 3.0},
        {"user_id": 2, "rank": 2, "points_earned": 2.0},
        {"user_id": 3, "rank": 3, "points_earned": 1.0},
        {"user_id": 4, "rank": 4, "points_earned": 0.0}
    ],
    "total_points_awarded": 6.0
}
```

---

### Step 7: UI Update

**Frontend Action**:
```python
if success:
    st.success("✅ Results recorded! Advancing to next match...")
    del st.session_state[f"results_{session_id}"]  # Clear form state
    st.rerun()  # Refresh UI → fetch next active match
```

**Leaderboard Refresh**:
- `/active-match` returns next session (or "All matches completed")
- `/leaderboard` returns updated standings with new points

---

## File Reference Map

### Backend Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| `app/models/match_structure.py` | Domain models for match formats | `MatchFormat`, `ScoringType`, `MatchStructure`, `MatchResult` |
| `app/services/tournament/result_processor.py` | Converts performance → rankings | `process_results()`, `validate_results()`, `_process_individual_ranking()` |
| `app/services/tournament/points_calculator_service.py` | Calculates points from rankings | `calculate_points_batch()`, `_get_base_points()`, `_apply_tier_multiplier()` |
| `app/services/tournament_session_generator.py` | Generates tournament sessions | `_generate_league_sessions()`, `_generate_knockout_sessions()` |
| `app/api/api_v1/endpoints/tournaments/instructor.py` | API endpoints | `get_active_match()`, `submit_structured_match_results()` |
| `alembic/versions/2026_01_22_1227-*.py` | Database migration | Adds `match_format`, `scoring_type`, `structure_config` to sessions |

### Frontend Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| `streamlit_app/components/tournaments/instructor/match_command_center.py` | Tournament UI | `render_match_command_center()`, `render_results_step()`, `render_individual_ranking_form()` |

### Test Files

| File | Purpose | Coverage |
|------|---------|----------|
| `app/tests/test_result_processor.py` | ResultProcessor unit tests | 25 tests covering all formats + validation |
| `app/tests/test_points_calculator_service.py` | Points calculation tests | Base points, tier multipliers, pod modifiers |
| `app/tests/test_tournament_session_generation_api.py` | Session generation tests | 9 tests for all tournament types |

---

## Extension Pattern: Adding New Match Formats

### Example: HEAD_TO_HEAD Format

#### 1. Update Session Generator
```python
# app/services/tournament_session_generator.py
sessions.append({
    'title': f'{tournament.name} - Semi-Final 1',
    'match_format': 'HEAD_TO_HEAD',
    'scoring_type': 'SCORE_BASED',
    'structure_config': {
        'pairing': [player_a_id, player_b_id],
        'bracket_position': 'Semi-Final 1'
    }
})
```

#### 2. Add Frontend UI Form
```python
# streamlit_app/components/tournaments/instructor/match_command_center.py
def render_head_to_head_form(token, tournament_id, match, present_participants):
    """
    HEAD_TO_HEAD: Winner selection or score entry
    Output: [{"user_id": X, "score": Y}, ...]
    """
    st.markdown("#### Enter Match Scores")

    player_a = present_participants[0]
    player_b = present_participants[1]

    score_a = st.number_input(f"{player_a['name']} Score", min_value=0, step=1)
    score_b = st.number_input(f"{player_b['name']} Score", min_value=0, step=1)

    if st.button("Submit Results"):
        results = [
            {"user_id": player_a['user_id'], "score": score_a},
            {"user_id": player_b['user_id'], "score": score_b}
        ]
        submit_match_results(token, tournament_id, session_id, results)
```

#### 3. ResultProcessor Already Implemented
```python
# app/services/tournament/result_processor.py:207-248
# HEAD_TO_HEAD processor already exists:
def _process_head_to_head(self, results):
    # Supports both WIN_LOSS and SCORE_BASED
    if "score" in results[0]:
        score_a = results[0]["score"]
        score_b = results[1]["score"]
        if score_a > score_b:
            return [(results[0]["user_id"], 1), (results[1]["user_id"], 2)]
        # ... etc
```

#### 4. Points Calculation Works Automatically
- ResultProcessor returns `[(winner_id, 1), (loser_id, 2)]`
- PointsCalculatorService applies base points + modifiers
- No changes needed!

#### 5. Add Tests
```python
# app/tests/test_result_processor.py
def test_head_to_head_score_based(self, result_processor):
    results = [
        {"user_id": 1, "score": 3},
        {"user_id": 2, "score": 1}
    ]
    rankings = result_processor.process_results(
        session_id=1,
        match_format='HEAD_TO_HEAD',
        results=results
    )
    assert rankings == [(1, 1), (2, 2)]
```

---

## SKILL_RATING Extension Point

### Current Status: NOT IMPLEMENTED

**Backend**: Raises `NotImplementedError`
**API**: Returns HTTP 501 Not Implemented
**Frontend**: Shows error message

### Implementation Pattern

#### 1. Define Business Logic
```python
# Future: app/services/tournament/skill_rating_processor.py
class LFASkillRatingProcessor:
    def derive_rankings(self, results, structure_config=None):
        """
        Custom business logic for SKILL_RATING

        Input: [{"user_id": 1, "rating": 9.5, "criteria_scores": {...}}, ...]
        Output: [(user_id, rank), ...]
        """
        # Define rating criteria (technique, speed, accuracy)
        # Define scoring scale (1-10)
        # Apply weighting
        # Calculate final scores
        # Derive rankings

        weighted_scores = []
        for result in results:
            technique_weight = 0.4
            speed_weight = 0.3
            accuracy_weight = 0.3

            score = (
                result["criteria_scores"]["technique"] * technique_weight +
                result["criteria_scores"]["speed"] * speed_weight +
                result["criteria_scores"]["accuracy"] * accuracy_weight
            )
            weighted_scores.append((result["user_id"], score))

        # Sort by score (descending)
        weighted_scores.sort(key=lambda x: x[1], reverse=True)
        return [(uid, rank+1) for rank, (uid, _) in enumerate(weighted_scores)]
```

#### 2. Inject into ResultProcessor
```python
# app/api/api_v1/endpoints/tournaments/instructor.py
from app.services.tournament.skill_rating_processor import LFASkillRatingProcessor

result_processor = ResultProcessor(db)
result_processor.set_skill_rating_processor(LFASkillRatingProcessor())
```

#### 3. Add Frontend UI
```python
def render_skill_rating_form(token, tournament_id, match, present_participants):
    st.markdown("#### Rate Each Participant")

    for participant in present_participants:
        st.markdown(f"**{participant['name']}**")
        technique = st.slider("Technique", 1, 10, key=f"tech_{participant['user_id']}")
        speed = st.slider("Speed", 1, 10, key=f"speed_{participant['user_id']}")
        accuracy = st.slider("Accuracy", 1, 10, key=f"acc_{participant['user_id']}")

        results_dict[participant['user_id']] = {
            "user_id": participant['user_id'],
            "criteria_scores": {
                "technique": technique,
                "speed": speed,
                "accuracy": accuracy
            }
        }
```

---

## Error Handling

### Common Errors

| Error | HTTP Code | Cause | Solution |
|-------|-----------|-------|----------|
| Invalid results format | 400 | Missing required fields | Check result structure matches format |
| Duplicate placements | 400 | Two players with same rank | Ensure unique placements |
| Results already recorded | 400 | Session already complete | Cannot re-submit results |
| SKILL_RATING not implemented | 501 | Extension point not injected | Implement processor first |
| Unauthorized | 403 | User not assigned to tournament | Check instructor assignment |

### Validation Examples

#### ✅ Valid INDIVIDUAL_RANKING
```json
{
  "results": [
    {"user_id": 1, "placement": 1},
    {"user_id": 2, "placement": 2},
    {"user_id": 3, "placement": 3}
  ]
}
```

#### ❌ Invalid: Missing placement
```json
{
  "results": [
    {"user_id": 1},  // ❌ Missing 'placement'
    {"user_id": 2, "placement": 2}
  ]
}
```

#### ❌ Invalid: Duplicate placements
```json
{
  "results": [
    {"user_id": 1, "placement": 1},
    {"user_id": 2, "placement": 1}  // ❌ Duplicate
  ]
}
```

#### ❌ Invalid: Placements don't start from 1
```json
{
  "results": [
    {"user_id": 1, "placement": 2},  // ❌ Should start from 1
    {"user_id": 2, "placement": 3}
  ]
}
```

---

## Testing Checklist

### Unit Tests
- [x] ResultProcessor: INDIVIDUAL_RANKING (5 tests)
- [x] ResultProcessor: HEAD_TO_HEAD (4 tests)
- [x] ResultProcessor: TEAM_MATCH (3 tests)
- [x] ResultProcessor: TIME_BASED (3 tests)
- [x] ResultProcessor: SKILL_RATING extension point (2 tests)
- [x] ResultProcessor: Validation (6 tests)
- [x] ResultProcessor: Edge cases (2 tests)
- [x] PointsCalculatorService: Base points, tier multipliers, pod modifiers

### Integration Tests
- [x] Session generation with match_format metadata (9 tests)
- [x] Points recording with tier multipliers

### E2E Tests (Manual)
- [ ] Create tournament → generate sessions → verify match_format set
- [ ] Fetch active match → verify format metadata returned
- [ ] Mark attendance → verify present/absent status
- [ ] Submit INDIVIDUAL_RANKING results → verify rankings derived
- [ ] Check leaderboard → verify points updated correctly
- [ ] Complete all matches → verify tournament complete

---

## Performance Considerations

### Database Queries
- Session fetch: Single query with `joinedload(participants)`
- Ranking update: Batch upsert with transaction
- Leaderboard: Single query with sorting

### Optimization Tips
1. Use `joinedload()` to avoid N+1 queries
2. Batch point calculations in single transaction
3. Cache tournament config (reduces DB hits)
4. Index on `tournament_id` + `user_id` for rankings table

---

## Backward Compatibility

### Nullable Fields
All new fields are nullable:
- `sessions.match_format` → defaults to 'INDIVIDUAL_RANKING'
- `sessions.scoring_type` → defaults to 'PLACEMENT'
- `sessions.structure_config` → defaults to NULL

### Legacy Sessions
Sessions created before this feature:
- `match_format` is NULL → API defaults to 'INDIVIDUAL_RANKING'
- ResultProcessor handles gracefully
- Points calculation works as before

---

## Future Work

### Planned Features
1. HEAD_TO_HEAD UI implementation
2. TEAM_MATCH UI implementation
3. TIME_BASED UI implementation
4. SKILL_RATING business logic definition + implementation
5. Integration tests for /submit-results endpoint
6. E2E Playwright tests for full flow

### Extension Points
- [ ] Custom point schemes per tournament type
- [ ] Custom tier multipliers
- [ ] Custom pod modifiers
- [ ] Multi-judge skill ratings
- [ ] Video replay integration

---

## Troubleshooting

### "Results already recorded" error
**Cause**: Session's `game_results` field is not NULL
**Solution**: Results can only be submitted once per session. To re-submit, manually clear `game_results` field in database (admin only).

### "Invalid results format" error
**Cause**: Result structure doesn't match match_format requirements
**Solution**: Check API error message for specific field validation failures. Ensure results match expected format.

### Points not updating on leaderboard
**Cause**: Transaction not committed or ranking record not created
**Solution**: Check DB transaction commit. Verify `tournament_rankings` table has record for user.

### Frontend shows "Format not supported"
**Cause**: match_format from API is not yet implemented in UI
**Solution**: Add format-specific UI form following the extension pattern above.

---

## Contact & Support

**Documentation Owner**: LFA Development Team
**Last Updated**: 2026-01-22
**Version**: 1.0 (Production Ready)

For questions or issues, refer to:
- Test files: `app/tests/test_result_processor.py`
- Source code: `app/services/tournament/result_processor.py`
- API docs: `app/api/api_v1/endpoints/tournaments/instructor.py`
