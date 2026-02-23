# Tournament Configuration Variations - E2E Test Coverage

## Configuration Dimensions

### 1. Tournament Format (2 variations)
- **INDIVIDUAL_RANKING**: Players compete individually, ranked by performance
- **HEAD_TO_HEAD**: Players compete in 1v1 matches (requires tournament_type_id)

### 2. Scoring Type (4 variations for INDIVIDUAL_RANKING)
- **ROUNDS_BASED**: Multiple rounds, performance per round (supports finalization)
- **TIME_BASED**: Fastest time wins (e.g., 100m sprint)
- **DISTANCE_BASED**: Longest distance wins (e.g., long jump)
- **SCORE_BASED**: Highest score wins (e.g., shooting accuracy)
- **PLACEMENT**: Single placement ranking (no measurements)

### 3. Ranking Direction (2 variations)
- **ASC**: Lowest value wins (for TIME_BASED: 10.5s < 11.2s)
- **DESC**: Highest value wins (for SCORE_BASED: 95pts > 80pts)

### 4. Tournament Type (for HEAD_TO_HEAD only)
Query database for available tournament types:
```sql
SELECT id, name, format FROM tournament_types;
```

Expected types:
- Swiss System (HEAD_TO_HEAD)
- Round Robin / League (HEAD_TO_HEAD)
- Single Elimination (HEAD_TO_HEAD)
- Double Elimination (HEAD_TO_HEAD)

### 5. Number of Rounds (for ROUNDS_BASED only)
- 1 round (tested)
- 2 rounds
- 3+ rounds

## Critical Test Matrix

### Priority 1: Core Variations (MUST TEST)

| Test ID | Format | Scoring Type | Ranking | Finalization | Status |
|---------|--------|--------------|---------|--------------|--------|
| T1 | INDIVIDUAL_RANKING | ROUNDS_BASED | DESC | YES | ✅ PASSED (Tournament 233) |
| T2 | INDIVIDUAL_RANKING | TIME_BASED | ASC | NO | ⏳ NOT TESTED |
| T3 | INDIVIDUAL_RANKING | SCORE_BASED | DESC | NO | ⏳ NOT TESTED |
| T4 | INDIVIDUAL_RANKING | PLACEMENT | N/A | NO | ⏳ NOT TESTED |
| T5 | HEAD_TO_HEAD | ROUNDS_BASED | N/A | YES | ⏳ NOT TESTED |

### Priority 2: Edge Cases (SHOULD TEST)

| Test ID | Format | Scoring Type | Special Config | Status |
|---------|--------|--------------|----------------|--------|
| T6 | INDIVIDUAL_RANKING | ROUNDS_BASED | 3 rounds | ⏳ NOT TESTED |
| T7 | INDIVIDUAL_RANKING | DISTANCE_BASED | ASC (reverse) | ⏳ NOT TESTED |
| T8 | HEAD_TO_HEAD | ROUNDS_BASED | Swiss System | ⏳ NOT TESTED |
| T9 | HEAD_TO_HEAD | ROUNDS_BASED | Round Robin | ⏳ NOT TESTED |

## Critical Questions

### 1. HEAD_TO_HEAD Support
- Does HEAD_TO_HEAD support finalization?
- Does HEAD_TO_HEAD require different session generation?
- Does HEAD_TO_HEAD require different result submission format?
- Does HEAD_TO_HEAD work with reward distribution?

### 2. ROUNDS_BASED vs Other Scoring Types
- Is finalization ONLY supported for ROUNDS_BASED?
- Do TIME_BASED/SCORE_BASED/DISTANCE_BASED skip step 6 (finalization)?
- Do they go straight from step 5 (results) to step 7 (complete)?

### 3. Tournament Type Dependency
- Is tournament_type_id REQUIRED for HEAD_TO_HEAD?
- Is tournament_type_id FORBIDDEN for INDIVIDUAL_RANKING?
- What happens if this rule is violated?

## Test Implementation Strategy

### Phase 1: Identify Supported Configurations
1. Query database for available tournament_types
2. Read session generation code to identify format support
3. Read finalization code to identify scoring_type support
4. Document which combinations are valid

### Phase 2: Create Parameterized E2E Tests
1. Extend `full_tournament_lifecycle_e2e.py` to accept config parameters
2. Create test runner that iterates through all valid combinations
3. Add conditional logic for format-specific steps:
   - HEAD_TO_HEAD: Different session structure
   - Non-ROUNDS_BASED: Skip finalization step

### Phase 3: Execute Full Test Suite
1. Run all Priority 1 tests (5 variations)
2. Run Priority 2 tests if time permits (4 variations)
3. Document results in test matrix
4. Identify any failing configurations

## Expected Findings

### Likely Supported
- INDIVIDUAL_RANKING + ROUNDS_BASED ✅ (proven)
- INDIVIDUAL_RANKING + TIME_BASED ✅ (common use case)
- INDIVIDUAL_RANKING + SCORE_BASED ✅ (common use case)
- INDIVIDUAL_RANKING + PLACEMENT ✅ (simplest case)

### Likely NOT Supported / Needs Investigation
- HEAD_TO_HEAD + Any scoring type (may require tournament_type_id)
- ROUNDS_BASED with > 1 round (session generation may not support)
- Mixed format tournaments

## Next Steps

1. ✅ Run database query for tournament_types
2. ⏳ Analyze session generation code for format support
3. ⏳ Analyze finalization code for scoring_type support
4. ⏳ Create parameterized test runner
5. ⏳ Execute full test suite
6. ⏳ Document results and create bug reports for any failures
