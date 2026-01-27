# Technical Debt & Known Limitations

This document tracks technical debt, known limitations, and workarounds in the codebase.

---

## API Limitations

### Tournament Lifecycle API - Incomplete Tournament Field Support

**Status**: 🟡 Known Limitation
**Impact**: E2E tests must use direct SQL INSERT instead of production API
**Severity**: Medium
**Date Identified**: 2026-01-27

**Description**:
The Tournament Lifecycle API (`POST /api/v1/tournaments/`) does not support tournament-specific fields that are required for creating fully-configured tournament records.

**Missing Fields**:
- `format` (HEAD_TO_HEAD, INDIVIDUAL_RANKING)
- `scoring_type` (PLACEMENT, SCORE)
- `tournament_type_id` (foreign key to tournament_types table)
- `number_of_rounds` (for multi-round tournaments)

**Current Workaround**:
E2E test scripts ([test_league_api.sh](../tests/tournament_types/test_league_api.sh), [test_multi_round_api.sh](../tests/tournament_types/test_multi_round_api.sh)) use direct SQL INSERT statements with all required fields, including:
- `created_at` and `updated_at` timestamps for production-compatible data structure
- All tournament-specific configuration fields

**Impact**:
- ✅ E2E tests work correctly with SQL INSERT approach
- ✅ Data structure is production-compatible (includes timestamps)
- ⚠️ E2E tests bypass production API, reducing API test coverage
- ⚠️ Tournament creation via API is limited to basic fields only

**Recommended Fix** (Future):
Extend `TournamentCreateRequest` schema and `create_tournament()` endpoint in [lifecycle.py](../app/api/api_v1/endpoints/tournaments/lifecycle.py) to accept optional tournament-specific fields:

```python
class TournamentCreateRequest(BaseModel):
    # ... existing fields ...

    # Tournament-specific fields (optional)
    format: Optional[str] = Field(None, description="Tournament format")
    scoring_type: Optional[str] = Field(None, description="Scoring type")
    tournament_type_id: Optional[int] = Field(None, description="Tournament type ID")
    number_of_rounds: Optional[int] = Field(None, description="Number of rounds")
```

**Effort Estimate**: 2-4 hours
**Priority**: P3 (Enhancement - not blocking current functionality)

---

## Template for New Entries

```markdown
### [Component Name] - [Issue Title]

**Status**: 🔴 Critical / 🟡 Known Limitation / 🟢 Enhancement
**Impact**: [Brief description of impact]
**Severity**: High/Medium/Low
**Date Identified**: YYYY-MM-DD

**Description**:
[Detailed description of the technical debt or limitation]

**Current Workaround**:
[How we're currently handling this]

**Impact**:
- [Impact point 1]
- [Impact point 2]

**Recommended Fix** (Future):
[Proposed solution]

**Effort Estimate**: [Hours/Days]
**Priority**: [P0-P4]
```
