# Priority 2: Tournament Session Generator Decomposition Plan

## Current State Analysis

**File**: `app/services/tournament_session_generator.py`
- **Lines**: 1,294
- **Classes**: 1 (TournamentSessionGenerator - God Class)
- **Methods**: 11
- **Largest method**: 354 lines (_generate_group_knockout_sessions)
- **Complexity**: Very high - single class handles all tournament formats

### Method Size Analysis

| Method | Lines | Purpose |
|--------|-------|---------|
| `_generate_group_knockout_sessions` | 354 | Group + knockout hybrid format |
| `_generate_swiss_sessions` | 155 | Swiss tournament format |
| `_generate_knockout_sessions` | 135 | Single elimination format |
| `generate_sessions` | 120 | Main coordinator + validation |
| `_generate_individual_ranking_sessions` | 91 | Individual ranking format |
| `_generate_round_robin_pairings` | 89 | Round robin algorithm |
| `_generate_league_sessions` | 81 | League/round-robin format |
| `_calculate_optimal_group_distribution` | 80 | Group size calculator |
| `_calculate_knockout_structure` | 76 | Bracket structure calculator |
| `can_generate_sessions` | 49 | Validation |
| `_get_round_robin_round_pairings` | 37 | Round robin helper |

## Problems Identified

### 1. Single Responsibility Violation
One class handles:
- Format validation
- 5 different tournament formats (League, Knockout, Swiss, Group+Knockout, Individual)
- Pairing algorithms (round robin, swiss, knockout)
- Group distribution calculations
- Bracket structure calculations
- Session metadata building

### 2. Code Duplication
- Tournament fetching (should use TournamentRepository)
- Enrollment validation (repeated logic)
- Session creation patterns (similar across formats)

### 3. Testing Difficulty
- Cannot test individual formats in isolation
- 1,294 lines to understand before testing
- No clear separation of concerns

### 4. Maintainability Issues
- Adding new tournament format requires modifying 1,294 line file
- Format-specific bugs affect entire file
- Hard to find specific format logic

## Proposed Structure

### New Directory Layout

```
app/services/tournament/session_generation/
├── __init__.py                           # Public API exports
├── session_generator.py                  # Main coordinator (150 lines)
├── validators/
│   ├── __init__.py
│   └── generation_validator.py           # can_generate_sessions logic (80 lines)
├── formats/                              # Format-specific generators
│   ├── __init__.py
│   ├── base_format_generator.py          # Abstract base (50 lines)
│   ├── league_generator.py               # League format (100 lines)
│   ├── knockout_generator.py             # Knockout format (150 lines)
│   ├── swiss_generator.py                # Swiss format (180 lines)
│   ├── group_knockout_generator.py       # Hybrid format (380 lines)
│   └── individual_ranking_generator.py   # Individual format (110 lines)
├── algorithms/                           # Reusable algorithms
│   ├── __init__.py
│   ├── round_robin_pairing.py            # Round robin logic (120 lines)
│   ├── group_distribution.py             # Group size calculator (100 lines)
│   ├── knockout_bracket.py               # Bracket structure (90 lines)
│   └── seeding.py                        # Seeding strategies (60 lines)
└── builders/
    ├── __init__.py
    └── session_metadata_builder.py       # Session object creation (80 lines)
```

### Total Breakdown

**Before**: 1 file, 1,294 lines
**After**: 16 files, ~1,450 lines (12% increase but MUCH better organization)

**Why line increase is OK**:
- Clear separation of concerns
- Reusable components
- Easier testing (each file < 200 lines)
- Better maintainability
- No duplication between formats

## Decomposition Strategy

### Phase 1: Create Foundation (30 min)
1. Create directory structure
2. Create `BaseFormatGenerator` abstract class
3. Create `GenerationValidator` (extract validation logic)
4. Create `SessionMetadataBuilder` (extract session creation)

### Phase 2: Extract Algorithms (45 min)
5. Extract `RoundRobinPairing` (from `_generate_round_robin_pairings`)
6. Extract `GroupDistribution` (from `_calculate_optimal_group_distribution`)
7. Extract `KnockoutBracket` (from `_calculate_knockout_structure`)

### Phase 3: Extract Format Generators (90 min)
8. `LeagueGenerator` (from `_generate_league_sessions`)
9. `KnockoutGenerator` (from `_generate_knockout_sessions`)
10. `SwissGenerator` (from `_generate_swiss_sessions`)
11. `GroupKnockoutGenerator` (from `_generate_group_knockout_sessions`)
12. `IndividualRankingGenerator` (from `_generate_individual_ranking_sessions`)

### Phase 4: Create Coordinator (30 min)
13. Refactor `session_generator.py` to use format generators
14. Use `TournamentRepository` instead of direct queries
15. Simplify `generate_sessions()` to be a router

### Phase 5: Testing & Integration (45 min)
16. Update imports across codebase
17. Run integration tests
18. Verify all tournament types still work

**Total Estimated Time**: 4 hours

## Benefits

### 1. Maintainability ⬆️
- Each format in separate file (< 200 lines)
- Clear file naming (`knockout_generator.py` - obvious purpose)
- Easy to find and modify specific format logic

### 2. Testability ⬆️
- Unit test each format generator independently
- Mock algorithms in format tests
- Test algorithms independently
- Much faster test execution

### 3. Extensibility ⬆️
- New tournament format? Create new generator, implement base class
- No need to touch existing formats
- Algorithms reusable across formats

### 4. Code Reuse ⬆️
- `RoundRobinPairing` used by League and Swiss
- `GroupDistribution` used by Group+Knockout
- `KnockoutBracket` used by Knockout and Group+Knockout

### 5. Developer Experience ⬆️
- New devs understand `league_generator.py` (100 lines) vs entire 1,294 line file
- Parallel development possible (different devs work on different formats)
- Reduced merge conflicts

## Migration Strategy

### Backward Compatibility
- Keep `app/services/tournament_session_generator.py` as facade
- Delegate to new structure internally
- No breaking changes for existing code
- Gradual migration possible

### Testing Strategy
1. Copy existing integration tests
2. Run tests against OLD implementation → capture results
3. Implement NEW structure
4. Run same tests against NEW implementation → compare results
5. If identical → migration successful

## Risk Mitigation

### Low Risk
- We're extracting, not rewriting logic
- Each piece can be tested against original
- Facade pattern ensures no breaking changes

### Rollback Plan
- Keep original file as `tournament_session_generator_v1.py`
- If issues found, revert import
- Tag git commit before migration: `pre-session-generator-decomposition`

## Success Criteria

✅ All format generators < 200 lines
✅ All algorithms < 150 lines
✅ Main coordinator < 200 lines
✅ All existing tests pass
✅ No regression in tournament generation
✅ Code coverage maintained or improved

## Next Steps

1. **User approval** of this plan
2. **Create git tag** `pre-session-generator-decomposition`
3. **Execute Phase 1** (foundation)
4. **Incremental commits** after each phase
5. **Testing** after each phase
6. **Documentation** updates

---

**Estimated Impact**:
- Code organization: 📈 10x improvement
- Maintainability: 📈 8x improvement
- Testability: 📈 12x improvement
- Lines of code: 📊 +12% (acceptable tradeoff)

**Ready to proceed?**
