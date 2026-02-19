# Unified Multi-Player Ranking System - Implementation Guide

**Status**: Phase 1 ✅ | Phase 2 ✅ | Phase 3 ✅
**Last Updated**: 2026-01-22
**Version**: 1.0.0

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Phase 1: Backend Foundation](#phase-1-backend-foundation)
4. [Phase 2: Points System Refinement](#phase-2-points-system-refinement)
5. [Phase 3: Frontend Updates](#phase-3-frontend-updates)
6. [API Reference](#api-reference)
7. [Testing](#testing)
8. [Usage Examples](#usage-examples)
9. [Configuration](#configuration)

---

## Overview

### Problem Statement

The original tournament system generated "round robin" session structures but the frontend implemented "multi-player ranking" where ALL players ranked in EVERY session. This created inconsistencies, particularly in Group Stage tournaments where all 8 players appeared in group sessions instead of just the 4 group members.

### Solution

Implement a **Unified Multi-Player Ranking System** that:
- Preserves the current multi-player ranking approach
- Extends it consistently across all tournament types
- Supports both individual and team rankings
- Adds metadata to sessions for proper participant filtering
- Implements tier-based and pod-based point multipliers

### Key Concepts

- **Ranking Mode**: Determines which participants compete in a session
- **Participant Filtering**: Dynamic filtering based on session metadata
- **Tier/Pod Multipliers**: Progressive point scaling based on tournament stage
- **Unified Points System**: Consistent point calculation across all tournament types

---

## Architecture

### 3-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ L1: Configuration Layer                                      │
│ - Tournament Types (JSON config)                            │
│ - Point Schemes (customizable per type)                     │
│ - Tier/Pod Multipliers                                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ L2: Service Layer                                            │
│ - TournamentSessionGenerator                                │
│ - ParticipantFilterService                                  │
│ - PointsCalculatorService                                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ L3: Entity Layer                                             │
│ - Session (with ranking metadata)                           │
│ - Tournament Rankings                                       │
│ - Bookings & Attendance                                     │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema

**New Fields in `sessions` Table**:
```sql
ranking_mode VARCHAR(50)          -- ALL_PARTICIPANTS, GROUP_ISOLATED, etc.
group_identifier VARCHAR(10)      -- A, B, C, D (for group stage)
expected_participants INTEGER     -- Validation: expected player count
participant_filter VARCHAR(50)    -- Filter logic: group_membership, etc.
pod_tier INTEGER                  -- Performance tier (1=top, 2=middle, etc.)
```

---

## Phase 1: Backend Foundation

### 1.1 Session Model Extension

**File**: `app/models/session.py`

Added 5 new fields for ranking metadata:

```python
class Session(Base):
    # ... existing fields ...

    # 🎯 MULTI-PLAYER RANKING METADATA
    ranking_mode = Column(String(50), nullable=True)
    group_identifier = Column(String(10), nullable=True)
    expected_participants = Column(Integer, nullable=True)
    participant_filter = Column(String(50), nullable=True)
    pod_tier = Column(Integer, nullable=True)
```

**Migration**: `2026_01_22_1058-618a1eb1eea8_add_session_ranking_metadata`

### 1.2 ParticipantFilterService

**File**: `app/services/tournament/participant_filter_service.py`

**Purpose**: Determines which users participate in a session based on `ranking_mode`.

**Key Methods**:

```python
class ParticipantFilterService:
    def get_session_participants(session_id: int) -> List[int]:
        """Get eligible user_ids for a session based on ranking_mode"""

    def _filter_by_group(session, all_user_ids) -> List[int]:
        """Filter to only group members (round-robin assignment)"""

    def _filter_qualified_players(session, all_user_ids) -> List[int]:
        """Filter to top N performers from previous rounds"""

    def _filter_by_performance_pod(session, all_user_ids) -> List[int]:
        """Filter to performance-based pod (Swiss System)"""
```

**Ranking Modes**:

| Mode | Description | Used In |
|------|-------------|---------|
| `ALL_PARTICIPANTS` | All enrolled players | League |
| `GROUP_ISOLATED` | Only group members | Group Stage |
| `QUALIFIED_ONLY` | Top N qualifiers | Knockout Stage |
| `TIERED` | All players with tier multipliers | Knockout (all rounds) |
| `PERFORMANCE_POD` | Performance-based pods | Swiss System |

### 1.3 Session Generators

**File**: `app/services/tournament_session_generator.py`

Updated all 4 generators with ranking metadata:

#### League Generator
```python
'ranking_mode': 'ALL_PARTICIPANTS',
'expected_participants': player_count,
'participant_filter': None,
'group_identifier': None,
'pod_tier': None
```

#### Group+Knockout Generator
```python
# Group Stage
'ranking_mode': 'GROUP_ISOLATED',
'group_identifier': 'A',  # or B, C, D
'expected_participants': 4,
'participant_filter': 'group_membership',

# Knockout Stage
'ranking_mode': 'QUALIFIED_ONLY',
'expected_participants': qualified_count,
'participant_filter': 'top_group_qualifiers',
```

#### Knockout Generator
```python
'ranking_mode': 'TIERED',
'expected_participants': player_count,
'pod_tier': round_num  # 1, 2, 3 (higher = finals)
```

#### Swiss Generator
```python
'ranking_mode': 'PERFORMANCE_POD',
'expected_participants': pod_size,
'participant_filter': 'dynamic_swiss_pairing',
'pod_tier': pod_num  # 1=top, 2=middle, 3=bottom
```

### 1.4 API Endpoint Integration

**File**: `app/api/api_v1/endpoints/tournaments/instructor.py`

**Endpoint**: `GET /api/v1/tournaments/{tournament_id}/active-match`

**Updated Response**:
```json
{
  "active_match": {
    "session_id": 123,
    "match_name": "Group A - Round 1",
    "participants": [...],

    // ✅ NEW: Ranking metadata
    "ranking_mode": "GROUP_ISOLATED",
    "group_identifier": "A",
    "expected_participants": 4,
    "participant_filter": "group_membership",
    "pod_tier": null,
    "tournament_phase": "Group Stage",
    "tournament_round": 1
  }
}
```

**Participant Filtering**:
```python
from app.services.tournament.participant_filter_service import ParticipantFilterService

participant_filter = ParticipantFilterService(db)
eligible_user_ids = participant_filter.get_session_participants(active_session.id)

# Get bookings ONLY for eligible participants
bookings = db.query(Booking).filter(
    Booking.user_id.in_(eligible_user_ids)
).all()
```

---

## Phase 2: Points System Refinement

### 2.1 PointsCalculatorService

**File**: `app/services/tournament/points_calculator_service.py`

**Purpose**: Unified point calculation with tier/pod multiplier support.

**Key Methods**:

```python
class PointsCalculatorService:
    def calculate_points(
        session_id: int,
        user_id: int,
        rank: int,
        tournament_type_config: Optional[Dict] = None
    ) -> float:
        """Calculate points with tier/pod multipliers"""

    def calculate_points_batch(
        session_id: int,
        rankings: List[Tuple[int, int]],
        tournament_type_config: Optional[Dict] = None
    ) -> Dict[int, float]:
        """Batch calculation for multiple players"""

    def validate_ranking(
        session_id: int,
        rankings: List[Tuple[int, int]]
    ) -> Tuple[bool, str]:
        """Validate rankings (no duplicates, sequential)"""

    def get_points_summary(
        session_id: int,
        rankings: List[Tuple[int, int]]
    ) -> Dict:
        """Get detailed points breakdown"""
```

### 2.2 Point Schemes

**Default Scheme**:
```python
{
    1: 3,  # 1st place
    2: 2,  # 2nd place
    3: 1   # 3rd place
}
```

**Custom Scheme** (configurable per tournament type):
```json
{
  "point_scheme": {
    "1": 5,
    "2": 3,
    "3": 2,
    "4": 1
  }
}
```

### 2.3 Tier Multipliers (Knockout)

```python
TIER_MULTIPLIERS = {
    1: 1.0,   # Quarter-finals
    2: 1.5,   # Semi-finals
    3: 2.0,   # Finals
    4: 2.5    # Special rounds
}
```

**Example**:
- Finals (tier=3): 1st place = 3 pts × 2.0 = **6.0 pts**
- Semi-finals (tier=2): 1st place = 3 pts × 1.5 = **4.5 pts**

### 2.4 Pod Modifiers (Swiss System)

```python
POD_MODIFIERS = {
    1: 1.2,   # Top pod (top performers)
    2: 1.0,   # Middle pod
    3: 0.8    # Bottom pod
}
```

**Example**:
- Top Pod (pod=1): 1st place = 3 pts × 1.2 = **3.6 pts**
- Bottom Pod (pod=3): 1st place = 3 pts × 0.8 = **2.4 pts**

### 2.5 API Integration

**Endpoint**: `POST /api/v1/tournaments/{tournament_id}/sessions/{session_id}/results`

**Updated Implementation**:
```python
from app.services.tournament.points_calculator_service import PointsCalculatorService

points_calculator = PointsCalculatorService(db)
tournament_config = points_calculator.get_tournament_type_config(tournament_id)

rankings = [(r.user_id, r.rank) for r in result_data.results]
points_map = points_calculator.calculate_points_batch(
    session_id=session_id,
    rankings=rankings,
    tournament_type_config=tournament_config
)

# Update tournament rankings with calculated points
for result in result_data.results:
    points_earned = points_map.get(result.user_id, 0.0)
    # ... update database
```

---

## Phase 3: Frontend Updates

### 3.1 Match Command Center UI

**File**: `streamlit_app/components/tournaments/instructor/match_command_center.py`

#### Added Ranking Metadata Display

**Location**: Active Match Card

```python
# Display ranking mode badges
metadata_badges = []

if tournament_phase:
    metadata_badges.append(f"📌 {tournament_phase}")

if group_identifier:
    metadata_badges.append(f"🔤 Group {group_identifier}")

if ranking_mode == 'TIERED' and pod_tier:
    tier_names = {1: "Quarter-Finals", 2: "Semi-Finals", 3: "Finals"}
    metadata_badges.append(f"🏆 {tier_names.get(pod_tier)}")

if ranking_mode == 'PERFORMANCE_POD' and pod_tier:
    pod_names = {1: "Top Pod 🔥", 2: "Middle Pod ⚡", 3: "Bottom Pod 💪"}
    metadata_badges.append(f"🎯 {pod_names.get(pod_tier)}")
```

#### Match Type Explanation

Added collapsible info box:

```python
with st.expander("ℹ️ Match Type & Scoring", expanded=False):
    if ranking_mode == 'ALL_PARTICIPANTS':
        st.info("**League Format**: All enrolled players compete together...")
    elif ranking_mode == 'GROUP_ISOLATED':
        st.info(f"**Group Stage Format**: Only Group {group_identifier} members...")
    # ... etc
```

#### Points Preview

Added real-time points calculation preview:

```python
def calculate_points_preview(rank: int) -> float:
    base = base_points.get(rank, 0)
    if ranking_mode == 'TIERED':
        return base * tier_multipliers.get(pod_tier, 1.0)
    elif ranking_mode == 'PERFORMANCE_POD':
        return base * pod_modifiers.get(pod_tier, 1.0)
    return float(base)

# Display next to rank dropdown
st.caption(f"💎 {points:.1f} pts")
```

#### Points Distribution Summary

Added before submit button:

```python
st.markdown("#### 📊 Points Distribution Preview")

for result in sorted_results:
    rank = result['rank']
    points = calculate_points_preview(rank)

    if ranking_mode in ['TIERED', 'PERFORMANCE_POD']:
        base = base_points.get(rank, 0)
        multiplier = ...
        st.caption(f"**{points:.1f}** pts ({base} × {multiplier:.1f})")
    else:
        st.caption(f"**{points:.0f}** pts")

st.caption(f"Total points awarded: **{total_points:.1f}** pts")
```

---

## API Reference

### GET /api/v1/tournaments/{tournament_id}/active-match

Returns the current active match with ranking metadata.

**Response**:
```json
{
  "active_match": {
    "session_id": 123,
    "match_name": "Group A - Round 1",
    "ranking_mode": "GROUP_ISOLATED",
    "group_identifier": "A",
    "expected_participants": 4,
    "participant_filter": "group_membership",
    "pod_tier": null,
    "tournament_phase": "Group Stage",
    "tournament_round": 1,
    "participants": [...]
  },
  "tournament_id": 456,
  "tournament_name": "Test Tournament",
  "total_matches": 9,
  "completed_matches": 3
}
```

### POST /api/v1/tournaments/{tournament_id}/sessions/{session_id}/results

Records match results with unified points calculation.

**Request**:
```json
{
  "results": [
    {"user_id": 1, "rank": 1, "score": null, "notes": null},
    {"user_id": 2, "rank": 2, "score": null, "notes": null}
  ],
  "match_notes": "Great match!"
}
```

**Point Calculation**:
- Automatically applies tier/pod multipliers based on session metadata
- Uses tournament type custom point scheme if configured
- Updates `tournament_rankings` table

---

## Testing

### Unit Tests

**ParticipantFilterService** (`test_participant_filter_service.py`): 11 tests
```
✅ test_all_participants_mode
✅ test_group_isolated_mode_group_a
✅ test_group_isolated_mode_group_b
✅ test_qualified_only_mode
✅ test_performance_pod_mode_top_pod
✅ test_performance_pod_mode_bottom_pod
✅ test_tiered_mode
✅ test_nonexistent_session
✅ test_session_with_no_enrollments
✅ test_get_group_assignment
✅ test_get_group_assignment_nonexistent_user
```

**PointsCalculatorService** (`test_points_calculator_service.py`): 8 tests
```
✅ test_standard_ranking_points
✅ test_custom_point_scheme_from_config
✅ test_tier_based_multipliers
✅ test_pod_based_modifiers
✅ test_batch_points_calculation
✅ test_ranking_validation_duplicate_ranks
✅ test_ranking_validation_missing_first_rank
✅ test_points_summary
```

### API Integration Tests

**TournamentSessionGenerationAPI** (`test_tournament_session_generation_api.py`): 6 tests
```
✅ test_league_tournament_session_generation
✅ test_group_knockout_tournament_session_generation
✅ test_active_match_endpoint_group_isolation
✅ test_session_generation_requires_in_progress_status
✅ test_session_generation_idempotency
✅ test_session_generation_creates_bookings_and_attendance
```

### Running Tests

```bash
# All unified ranking tests
pytest app/tests/test_participant_filter_service.py \
       app/tests/test_points_calculator_service.py \
       app/tests/test_tournament_session_generation_api.py -v

# Result: 25/25 tests passed (100%)
```

---

## Usage Examples

### Example 1: League Tournament (8 Players)

**Session Generation**:
```
Round 1: All 8 players compete (ranking_mode=ALL_PARTICIPANTS)
Round 2: All 8 players compete
Round 3: All 8 players compete
...
```

**Points Calculation**:
```
Round 1:
  Player A (1st): 3 points
  Player B (2nd): 2 points
  Player C (3rd): 1 point
  Player D-H (4th-8th): 0 points
```

### Example 2: Group+Knockout Tournament (8 Players)

**Session Generation**:
```
Group Stage:
  Group A Round 1: Players 1,3,5,7 (ranking_mode=GROUP_ISOLATED, group=A)
  Group A Round 2: Players 1,3,5,7
  Group A Round 3: Players 1,3,5,7
  Group B Round 1: Players 2,4,6,8 (ranking_mode=GROUP_ISOLATED, group=B)
  Group B Round 2: Players 2,4,6,8
  Group B Round 3: Players 2,4,6,8

Knockout Stage:
  Semi-Final 1: Top 4 qualifiers (ranking_mode=QUALIFIED_ONLY)
  Semi-Final 2: Top 4 qualifiers
  Finals: Top 4 qualifiers
```

**Points Calculation**:
```
Group A Round 1:
  Player 1 (1st in Group A): 3 points
  Player 3 (2nd in Group A): 2 points
  Player 5 (3rd in Group A): 1 point
  Player 7 (4th in Group A): 0 points

Semi-Finals (tier=2, multiplier=1.5):
  Player 1 (1st): 3 × 1.5 = 4.5 points
  Player 3 (2nd): 2 × 1.5 = 3.0 points

Finals (tier=3, multiplier=2.0):
  Player 1 (1st): 3 × 2.0 = 6.0 points 🏆
  Player 3 (2nd): 2 × 2.0 = 4.0 points
```

### Example 3: Swiss System (8 Players)

**Session Generation**:
```
Round 1: All 8 players (ranking_mode=ALL_PARTICIPANTS)
Round 2:
  Pod 1 (Top 4 performers): ranking_mode=PERFORMANCE_POD, pod_tier=1
  Pod 2 (Bottom 4 performers): ranking_mode=PERFORMANCE_POD, pod_tier=2
Round 3:
  Pod 1 (Top 4): Re-calculated based on Round 2
  Pod 2 (Bottom 4): Re-calculated based on Round 2
```

**Points Calculation**:
```
Round 2 - Pod 1 (Top pod, modifier=1.2):
  Player A (1st in pod): 3 × 1.2 = 3.6 points
  Player B (2nd in pod): 2 × 1.2 = 2.4 points

Round 2 - Pod 2 (Bottom pod, modifier=0.8):
  Player F (1st in pod): 3 × 0.8 = 2.4 points
  Player G (2nd in pod): 2 × 0.8 = 1.6 points
```

---

## Configuration

### Tournament Type Configuration

**File**: Database table `tournament_types`

**Example Configuration**:
```json
{
  "code": "league",
  "display_name": "League - Multi-Player Ranking",
  "config": {
    "ranking_rounds": 7,
    "point_scheme": {
      "1": 5,
      "2": 3,
      "3": 2,
      "4": 1
    }
  }
}
```

### Point Scheme Customization

**Standard Scheme** (default):
```python
{1: 3, 2: 2, 3: 1}
```

**Top-Heavy Scheme**:
```python
{1: 5, 2: 3, 3: 2, 4: 1}
```

**Participation Scheme** (everyone gets points):
```python
{1: 5, 2: 4, 3: 3, 4: 2, 5: 1}
```

### Tier/Pod Multipliers

**Tier Multipliers** (Knockout):
```python
TIER_MULTIPLIERS = {
    1: 1.0,   # Early rounds
    2: 1.5,   # Semi-finals
    3: 2.0,   # Finals
    4: 2.5    # Special rounds (3rd place playoff)
}
```

**Pod Modifiers** (Swiss):
```python
POD_MODIFIERS = {
    1: 1.2,   # Top pod bonus
    2: 1.0,   # Middle pod neutral
    3: 0.8    # Bottom pod penalty
}
```

---

## Migration Guide

### Existing Tournaments

**Backward Compatibility**: Existing sessions with `ranking_mode=NULL` will default to `ALL_PARTICIPANTS` mode.

**Migration Steps**:
1. Run migration: `alembic upgrade head`
2. Existing tournaments continue to work with default behavior
3. New tournaments automatically get ranking metadata

### Data Migration (Optional)

To retroactively add metadata to existing sessions:

```sql
-- Set ranking_mode for existing league sessions
UPDATE sessions
SET ranking_mode = 'ALL_PARTICIPANTS'
WHERE is_tournament_game = true
  AND ranking_mode IS NULL
  AND tournament_phase LIKE '%League%';

-- Set ranking_mode for group stage sessions
UPDATE sessions
SET ranking_mode = 'GROUP_ISOLATED',
    group_identifier = SUBSTRING(title FROM 'Group ([A-D])')
WHERE is_tournament_game = true
  AND ranking_mode IS NULL
  AND tournament_phase = 'Group Stage';
```

---

## Future Enhancements (Phase 4+)

### Phase 4: Team Support
- Team ranking aggregation
- Team-based point distribution
- Mixed individual/team tournaments
- Team leaderboards

### Phase 5: Advanced Analytics
- Points trend analysis
- Performance metrics per tier/pod
- Win rate analysis
- Player progression tracking

### Phase 6: Mobile Support
- Mobile-optimized Match Command Center
- Push notifications for match start
- Quick attendance marking
- Mobile leaderboard

---

## Troubleshooting

### Issue: Group stage shows all 8 players

**Cause**: Session missing `group_identifier` or `ranking_mode`

**Solution**:
```python
# Check session metadata
session = db.query(Session).filter(Session.id == session_id).first()
print(session.ranking_mode, session.group_identifier)

# Should be: GROUP_ISOLATED, A (or B, C, D)
```

### Issue: Points not applying multipliers

**Cause**: `pod_tier` or `ranking_mode` not set correctly

**Solution**:
```python
# Check session configuration
session = db.query(Session).filter(Session.id == session_id).first()
print(session.ranking_mode, session.pod_tier)

# For finals: TIERED, 3
# For top pod: PERFORMANCE_POD, 1
```

### Issue: Participant count mismatch

**Cause**: `expected_participants` doesn't match `participant_filter` result

**Solution**:
```python
# Debug participant filtering
from app.services.tournament.participant_filter_service import ParticipantFilterService

filter_service = ParticipantFilterService(db)
participants = filter_service.get_session_participants(session_id)
print(f"Expected: {session.expected_participants}, Actual: {len(participants)}")
```

---

## Support

For issues or questions:
- **GitHub Issues**: [Report bug](https://github.com/your-repo/issues)
- **Documentation**: See `docs/` folder
- **Tests**: Run `pytest app/tests/test_*ranking*.py -v`

---

**End of Documentation**
