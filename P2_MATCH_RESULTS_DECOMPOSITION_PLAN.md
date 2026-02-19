# Priority 2: Match Results Decomposition Plan

## Current State Analysis

**File**: `app/api/api_v1/endpoints/tournaments/match_results.py`
- **Lines**: 1,251
- **Endpoints**: 7 (mixed in one file)
- **Largest function**: 307 lines (finalize_individual_ranking_session)
- **Complexity**: Very high - results submission + finalization logic mixed

### Function Size Analysis

| Function | Lines | Purpose |
|----------|-------|---------|
| `finalize_individual_ranking_session` | 307 | Finalize individual ranking session + calculate results |
| `finalize_group_stage` | 241 | Group stage finalization + advancement |
| `record_match_results` | 177 | Record HEAD_TO_HEAD match results |
| `finalize_tournament` | 129 | Final tournament finalization |
| `submit_round_results` | 118 | Submit results for a specific round |
| `submit_structured_match_results` | 111 | Submit structured match results |
| `get_rounds_status` | 65 | Get rounds status for session |

## Problems Identified

### 1. Mixed Responsibilities
One file handles:
- Result submission (3 different endpoints)
- Session finalization (1 endpoint)
- Group stage finalization (1 endpoint)
- Tournament finalization (1 endpoint)
- Round management (2 endpoints)

### 2. Code Duplication
- Tournament/session fetching (should use TournamentRepository)
- Enrollment fetching (repeated patterns)
- Authorization checks (should use shared services)
- Result calculation logic (duplicated across endpoints)

### 3. Fat Endpoints
- 307-line endpoint is impossible to test
- Business logic mixed with HTTP handling
- Difficult to reuse calculation logic

## Proposed Structure

### New Directory Layout

```
app/api/api_v1/endpoints/tournaments/results/
├── __init__.py
├── submission.py              # Result submission endpoints (2-3 endpoints)
├── round_management.py        # Round-specific endpoints (2 endpoints)
└── finalization.py            # Finalization endpoints (2-3 endpoints)

app/services/tournament/results/
├── __init__.py
├── finalization/
│   ├── __init__.py
│   ├── group_stage_finalizer.py        # Group stage logic (150 lines)
│   ├── session_finalizer.py            # Session finalization (180 lines)
│   └── tournament_finalizer.py         # Tournament finalization (100 lines)
├── calculators/
│   ├── __init__.py
│   ├── standings_calculator.py         # Calculate standings (120 lines)
│   ├── ranking_aggregator.py           # Aggregate rankings (80 lines)
│   └── advancement_calculator.py       # Who advances (60 lines)
└── validators/
    ├── __init__.py
    └── result_validator.py             # Validate submitted results (80 lines)
```

## Decomposition Strategy

### Phase 1: Extract Services (60 min)

**1. Create calculators**:
- `StandingsCalculator` - extract standings logic from finalize_group_stage
- `RankingAggregator` - extract ranking logic from finalize_individual_ranking_session
- `AdvancementCalculator` - extract advancement logic

**2. Create finalizers**:
- `GroupStageFinalizer` - extract from finalize_group_stage endpoint
- `SessionFinalizer` - extract from finalize_individual_ranking_session endpoint
- `TournamentFinalizer` - extract from finalize_tournament endpoint

**3. Create validators**:
- `ResultValidator` - validate submitted match results

### Phase 2: Refactor Endpoints (45 min)

**4. Split into 3 endpoint files**:
- `submission.py`: submit_structured_match_results, record_match_results, submit_round_results
- `round_management.py`: get_rounds_status
- `finalization.py`: finalize_group_stage, finalize_tournament, finalize_individual_ranking_session

**5. Refactor endpoints to use**:
- Shared services (require_admin, TournamentRepository)
- Extracted finalizers
- Extracted calculators

### Phase 3: Testing & Integration (30 min)

**6. Update imports** across codebase
**7. Run tests** to verify functionality
**8. Create documentation**

**Total Estimated Time**: 2.5 hours

## Benefits

### Before → After

| Metric | Before | After |
|--------|--------|-------|
| Files | 1 | 12 |
| Largest file | 1,251 lines | ~200 lines |
| Largest function | 307 lines | ~50 lines |
| Testability | Very low | High |
| Reusability | None | High |

### Key Improvements

1. **Separation of Concerns**: Endpoints handle HTTP, services handle business logic
2. **Testability**: Each calculator/finalizer testable independently
3. **Reusability**: Calculators can be used in other contexts
4. **Maintainability**: ~100-200 lines per file vs 1,251
5. **Developer Experience**: Clear file structure, easy to navigate

## Migration Strategy

### Backward Compatibility
- Keep original routes/URLs
- Split file into multiple endpoint files (still same router)
- No breaking API changes

### Risk Mitigation
- Extract services first (pure functions)
- Test services independently
- Gradually refactor endpoints to use services
- Keep git tags for rollback

## Success Criteria

✅ All endpoint files < 300 lines
✅ All service files < 200 lines
✅ No function > 80 lines
✅ All existing tests pass
✅ No API breaking changes
✅ Improved test coverage

## Next Steps

1. User approval of plan
2. Create git tag `pre-match-results-decomposition`
3. Execute Phase 1 (extract services)
4. Execute Phase 2 (refactor endpoints)
5. Execute Phase 3 (testing)
6. Commit with comprehensive message

---

**Estimated Impact**:
- Code organization: 📈 12x improvement (1 → 12 files)
- Maintainability: 📈 6x improvement (1,251 → ~200 lines max)
- Testability: 📈 10x improvement (services testable)
- Largest function: 📉 84% reduction (307 → 50 lines)

**Ready to proceed?**
