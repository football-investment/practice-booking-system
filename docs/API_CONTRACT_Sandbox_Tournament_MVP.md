# API Contract: Sandbox Tournament (MVP)

**Version**: 1.0.0
**Status**: FROZEN (MVP Scope Only)
**Purpose**: Enable Product Owner "Ship It" decision via visual verdict

---

## Overview

This API contract defines the **MVP endpoint** for the Sandbox Tournament feature. The contract is **strictly scoped** to support the "Ship It" screen wireframe:

- ✅ Single test run (no history, no comparison)
- ✅ Auto-generated tournament with configurable parameters
- ✅ Visual verdict (WORKING ✓ / NOT WORKING ✗)
- ✅ Before/after skill comparison
- ✅ Top/bottom performers
- ✅ Key insights summary
- ✅ Export-ready data (for PDF generation)

**Out of Scope (MVP)**:
- ❌ Test run history
- ❌ Side-by-side comparison
- ❌ QA test suite runner
- ❌ Manual data input
- ❌ Replay/re-run with same data

---

## Endpoint: Run Sandbox Test

```
POST /api/v1/sandbox/run-test
```

**Description**: Creates a temporary tournament, generates synthetic test data, runs the full tournament lifecycle, distributes rewards, and returns a verdict with detailed results.

**Authentication**: Admin only (role: `ADMIN`)

**Timeout**: 30 seconds (estimated execution: 10-15s)

---

## Request

### Headers

```
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json
```

### Body Schema

```json
{
  "tournament_type": "LEAGUE",
  "skills_to_test": ["passing", "dribbling"],
  "player_count": 8,
  "test_config": {
    "performance_variation": "MEDIUM",
    "ranking_distribution": "NORMAL"
  }
}
```

### Field Descriptions

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| `tournament_type` | `string` | ✅ | Tournament format | `LEAGUE`, `KNOCKOUT`, `HYBRID` |
| `skills_to_test` | `string[]` | ✅ | Skills to validate | 1-4 skills, valid skill names |
| `player_count` | `integer` | ✅ | Number of synthetic players | 4-16 players |
| `test_config.performance_variation` | `string` | ❌ | Ranking spread | `LOW`, `MEDIUM`, `HIGH` (default: `MEDIUM`) |
| `test_config.ranking_distribution` | `string` | ❌ | Ranking pattern | `NORMAL`, `TOP_HEAVY`, `BOTTOM_HEAVY` (default: `NORMAL`) |

### Validation Rules

1. **tournament_type**: Must match existing tournament type in database
2. **skills_to_test**: Must be valid skill names from `reward_config.skill_mappings`
3. **player_count**: Must satisfy tournament type's `min_players` and `max_players`
4. **performance_variation**:
   - `LOW`: All players within 10 points (tight race)
   - `MEDIUM`: Players within 30 points (default)
   - `HIGH`: Wide spread, clear winner/loser (50+ points)
5. **ranking_distribution**:
   - `NORMAL`: Even distribution across ranks
   - `TOP_HEAVY`: Top 3 get 70% of total points
   - `BOTTOM_HEAVY`: Bottom half gets clustered scores

---

## Response

### Success Response (HTTP 200)

```json
{
  "verdict": "WORKING",
  "test_run_id": "sandbox-2026-01-27-14-23-45-abc123",
  "tournament": {
    "id": 9999,
    "name": "SANDBOX-TEST-LEAGUE-2026-01-27",
    "type": "LEAGUE",
    "status": "REWARDS_DISTRIBUTED",
    "player_count": 8,
    "skills_tested": ["passing", "dribbling"]
  },
  "execution_summary": {
    "duration_seconds": 12.4,
    "steps_completed": [
      "Tournament created (DRAFT)",
      "Participants enrolled (8 players)",
      "Rankings generated",
      "Status transitioned to COMPLETED",
      "Rewards distributed (REWARDS_DISTRIBUTED)"
    ]
  },
  "skill_progression": {
    "passing": {
      "before": {
        "average": 75.2,
        "min": 60.0,
        "max": 90.0
      },
      "after": {
        "average": 77.8,
        "min": 61.5,
        "max": 92.0
      },
      "change": "+2.6 avg"
    },
    "dribbling": {
      "before": {
        "average": 50.0,
        "min": 50.0,
        "max": 50.0
      },
      "after": {
        "average": 51.2,
        "min": 49.0,
        "max": 54.0
      },
      "change": "+1.2 avg"
    }
  },
  "top_performers": [
    {
      "user_id": 4,
      "username": "test_user_4",
      "rank": 1,
      "points": 95,
      "skills_changed": {
        "passing": {
          "before": 90.0,
          "after": 92.0,
          "change": "+2.0"
        },
        "dribbling": {
          "before": 50.0,
          "after": 54.0,
          "change": "+4.0"
        }
      },
      "total_skill_gain": 6.0
    },
    {
      "user_id": 5,
      "username": "test_user_5",
      "rank": 2,
      "points": 85,
      "skills_changed": {
        "passing": {
          "before": 80.0,
          "after": 83.0,
          "change": "+3.0"
        },
        "dribbling": {
          "before": 50.0,
          "after": 52.0,
          "change": "+2.0"
        }
      },
      "total_skill_gain": 5.0
    },
    {
      "user_id": 6,
      "username": "test_user_6",
      "rank": 3,
      "points": 75,
      "skills_changed": {
        "passing": {
          "before": 75.0,
          "after": 78.0,
          "change": "+3.0"
        },
        "dribbling": {
          "before": 50.0,
          "after": 51.0,
          "change": "+1.0"
        }
      },
      "total_skill_gain": 4.0
    }
  ],
  "bottom_performers": [
    {
      "user_id": 16,
      "username": "test_user_16",
      "rank": 8,
      "points": 25,
      "skills_changed": {
        "passing": {
          "before": 60.0,
          "after": 61.5,
          "change": "+1.5"
        },
        "dribbling": {
          "before": 50.0,
          "after": 49.0,
          "change": "-1.0"
        }
      },
      "total_skill_gain": 0.5
    },
    {
      "user_id": 15,
      "username": "test_user_15",
      "rank": 7,
      "points": 35,
      "skills_changed": {
        "passing": {
          "before": 65.0,
          "after": 66.0,
          "change": "+1.0"
        },
        "dribbling": {
          "before": 50.0,
          "after": 49.5,
          "change": "-0.5"
        }
      },
      "total_skill_gain": 0.5
    }
  ],
  "insights": [
    {
      "category": "VERDICT",
      "severity": "SUCCESS",
      "message": "All 8 participants received rewards successfully"
    },
    {
      "category": "SKILL_PROGRESSION",
      "severity": "INFO",
      "message": "Average passing skill increased by 2.6 points (expected: 2-4)"
    },
    {
      "category": "SKILL_PROGRESSION",
      "severity": "INFO",
      "message": "Average dribbling skill increased by 1.2 points (expected: 1-3)"
    },
    {
      "category": "IDEMPOTENCY",
      "severity": "SUCCESS",
      "message": "No duplicate TournamentParticipation records created"
    },
    {
      "category": "STATUS_TRANSITION",
      "severity": "SUCCESS",
      "message": "Status transition: DRAFT → COMPLETED → REWARDS_DISTRIBUTED"
    }
  ],
  "export_data": {
    "pdf_ready": true,
    "export_url": "/api/v1/sandbox/export-pdf/sandbox-2026-01-27-14-23-45-abc123"
  }
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `verdict` | `string` | Overall test result: `WORKING` or `NOT_WORKING` |
| `test_run_id` | `string` | Unique identifier for this sandbox run |
| `tournament.id` | `integer` | Database ID of temporary tournament |
| `tournament.name` | `string` | Generated tournament name (includes timestamp) |
| `tournament.status` | `string` | Final status (should be `REWARDS_DISTRIBUTED`) |
| `execution_summary.duration_seconds` | `float` | Total execution time |
| `execution_summary.steps_completed` | `string[]` | Ordered list of lifecycle steps executed |
| `skill_progression` | `object` | Before/after stats for each tested skill |
| `top_performers` | `array` | Top 3 players (rank 1-3) with skill changes |
| `bottom_performers` | `array` | Bottom 2 players with skill changes |
| `insights` | `array` | Key observations and validation results |
| `export_data.pdf_ready` | `boolean` | Whether PDF export is available |

---

## Error Responses

### HTTP 400 - Bad Request

**Cause**: Invalid input parameters

```json
{
  "detail": "Invalid tournament type: INVALID_TYPE. Must be one of: LEAGUE, KNOCKOUT, HYBRID"
}
```

**Common Causes**:
- Unknown tournament type
- Invalid skill names
- Player count outside min/max bounds
- Empty skills_to_test array

---

### HTTP 403 - Forbidden

**Cause**: Non-admin user attempting to run sandbox test

```json
{
  "detail": "Sandbox tests can only be run by admin users"
}
```

---

### HTTP 500 - Internal Server Error

**Cause**: Unexpected failure during test execution

```json
{
  "verdict": "NOT_WORKING",
  "error": {
    "stage": "REWARD_DISTRIBUTION",
    "message": "Failed to distribute rewards: IntegrityError (duplicate key)",
    "details": "tournament_participations_pkey: Key (user_id, semester_id) already exists"
  },
  "partial_results": {
    "tournament_id": 9999,
    "status_before_failure": "COMPLETED",
    "participants_enrolled": 8,
    "rankings_generated": true
  }
}
```

**Verdict**: If ANY step fails, verdict = `NOT_WORKING`

**Partial Results**: Includes all successfully completed steps before failure

---

## Implementation Notes

### 1. Test Data Generation

**Synthetic Users**: Use existing test users (IDs 4-16) with known baseline skills:
- User 4: passing ~80.0, dribbling ~50.0
- User 5: passing ~60.0, dribbling ~50.0
- User 6: passing ~70.0, dribbling ~50.0
- Users 7-16: Random baseline (60-90 passing, 50 dribbling)

**Rankings Generation**:
```python
def generate_rankings(player_count: int, variation: str, distribution: str):
    if distribution == "NORMAL":
        points = [100 - (i * (100 / player_count)) for i in range(player_count)]
    elif distribution == "TOP_HEAVY":
        points = [100, 90, 80, 40, 35, 30, 25, 20][:player_count]
    elif distribution == "BOTTOM_HEAVY":
        points = [100, 50, 45, 40, 35, 30, 25, 20][:player_count]

    # Apply variation (add noise)
    if variation == "LOW":
        noise_range = 5
    elif variation == "MEDIUM":
        noise_range = 10
    elif variation == "HIGH":
        noise_range = 20

    return add_random_noise(points, noise_range)
```

### 2. Execution Flow

```
1. Create tournament (status: DRAFT)
   ↓
2. Enroll N synthetic participants
   ↓
3. Generate rankings (INSERT INTO tournament_rankings)
   ↓
4. Transition to COMPLETED
   ↓
5. Call POST /api/v1/tournaments/{id}/rewards/distribute
   ↓
6. Validate status = REWARDS_DISTRIBUTED
   ↓
7. Query skill progression (BEFORE/AFTER from tournament_participations)
   ↓
8. Calculate verdict + insights
   ↓
9. Return response (DO NOT cleanup - leave for manual inspection)
```

### 3. Verdict Calculation Logic

```python
def calculate_verdict(tournament_id: int, expected_participant_count: int) -> str:
    # Check 1: Status = REWARDS_DISTRIBUTED
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if tournament.status != "REWARDS_DISTRIBUTED":
        return "NOT_WORKING"

    # Check 2: All participants have TournamentParticipation records
    participation_count = db.query(TournamentParticipation).filter(
        TournamentParticipation.semester_id == tournament_id
    ).count()
    if participation_count != expected_participant_count:
        return "NOT_WORKING"

    # Check 3: No duplicate participation records (unique constraint validation)
    try:
        # If we got here, unique constraint held during insertion
        pass
    except IntegrityError:
        return "NOT_WORKING"

    # Check 4: Skills changed (at least some non-zero deltas)
    participations = db.query(TournamentParticipation).filter(
        TournamentParticipation.semester_id == tournament_id
    ).all()

    total_skill_change = sum(
        abs(p.skills_after.get(skill, 0) - p.skills_before.get(skill, 0))
        for p in participations
        for skill in p.skills_after.keys()
    )

    if total_skill_change == 0:
        return "NOT_WORKING"

    # All checks passed
    return "WORKING"
```

### 4. Cleanup Strategy (MVP)

**NO automatic cleanup**: Sandbox tournaments are left in database for manual inspection.

**Reasoning**:
- Product Owner may want to inspect DB state after "NOT_WORKING" verdict
- Admin can manually delete via: `DELETE FROM semesters WHERE name LIKE 'SANDBOX-TEST-%'`
- Future enhancement: Add cleanup endpoint or TTL-based cleanup

### 5. Performance Expectations

| Metric | Target | Acceptable | Unacceptable |
|--------|--------|------------|--------------|
| Total execution time | < 10s | < 20s | > 30s |
| Reward distribution | < 3s | < 5s | > 10s |
| Skill calculation | < 2s | < 3s | > 5s |
| Database queries | < 50 | < 100 | > 150 |

---

## Testing the API

### cURL Example

```bash
# Login as admin
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@lfa.com","password":"admin123"}' \
  | jq -r '.access_token')

# Run sandbox test
curl -X POST http://localhost:8000/api/v1/sandbox/run-test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tournament_type": "LEAGUE",
    "skills_to_test": ["passing", "dribbling"],
    "player_count": 8,
    "test_config": {
      "performance_variation": "MEDIUM",
      "ranking_distribution": "NORMAL"
    }
  }' | jq .
```

### Expected Output (Success)

```json
{
  "verdict": "WORKING",
  "execution_summary": {
    "duration_seconds": 11.2
  },
  "insights": [
    {
      "category": "VERDICT",
      "severity": "SUCCESS",
      "message": "All 8 participants received rewards successfully"
    }
  ]
}
```

---

## Security Considerations

1. **Admin-only access**: Sandbox tests can modify database state
2. **Rate limiting**: Max 10 runs per minute per admin user
3. **Resource limits**: Max 16 players per test (prevent excessive DB load)
4. **Isolation**: Sandbox tournaments use separate name prefix (`SANDBOX-TEST-*`)

---

## Future Enhancements (Out of MVP Scope)

1. **History**: Store test run results for comparison
2. **Comparison**: Side-by-side comparison of two test runs
3. **Cleanup**: Auto-cleanup or manual cleanup endpoint
4. **Export**: PDF generation endpoint
5. **QA Runner**: Batch execution of predefined test cases
6. **Replay**: Re-run exact same configuration

---

## API Contract Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-27 | Initial MVP contract (frozen) |

---

## Approval

**Status**: ✅ FROZEN (MVP)
**Approved By**: Product Owner
**Implementation Ready**: YES

This contract is **implementation-ready** and should NOT be modified until MVP is shipped and validated.
