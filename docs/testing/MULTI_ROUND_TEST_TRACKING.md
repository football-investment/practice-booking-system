# Multi-Round E2E Test Tracking - 2026-02-03

**Purpose**: Track multi-round tournament testing across all scoring types
**Goal**: Validate system stability with 1, 2, and 3 round configurations

---

## Test Matrix Overview

| Scoring Type | 1 Round | 2 Rounds | 3 Rounds | Total Tests |
|--------------|---------|----------|----------|-------------|
| SCORE_BASED | 2 configs | 2 configs | 2 configs | **6 tests** |
| TIME_BASED | 2 configs | 2 configs | 2 configs | **6 tests** |
| DISTANCE_BASED | 2 configs | 2 configs | 2 configs | **6 tests** |
| PLACEMENT | 2 configs | 2 configs | 2 configs | **6 tests** |
| ROUNDS_BASED | 2 configs | 2 configs | 2 configs | **6 tests** |
| **TOTAL** | **10** | **10** | **10** | **30 tests** |

**Test Formats**: League (L) and Knockout (K) for each configuration

---

## 🎯 SCORE_BASED Configurations

### T1: League + INDIVIDUAL + SCORE_BASED

| Rounds | Config ID | Test Mode | Status | Duration | Notes |
|--------|-----------|-----------|--------|----------|-------|
| **1** | T1_League_Ind_Score_1R | 🎬 Headed | ✅ PASSED | 134.69s | Ranking display ✅, Status ✅, Skills ✅ |
| **2** | T1_League_Ind_Score_2R | ⏳ Pending | - | - | - |
| **3** | T1_League_Ind_Score_3R | ⏳ Pending | - | - | - |

**Validation Checklist**:
- [ ] 2R: Rankings displayed correctly per round
- [ ] 2R: Skill rewards aggregated across rounds
- [ ] 2R: Tournament status = REWARDS_DISTRIBUTED
- [ ] 3R: Rankings displayed correctly per round
- [ ] 3R: Skill rewards aggregated across rounds
- [ ] 3R: Tournament status = REWARDS_DISTRIBUTED

---

### T2: Knockout + INDIVIDUAL + SCORE_BASED

| Rounds | Config ID | Test Mode | Status | Duration | Notes |
|--------|-----------|-----------|--------|----------|-------|
| **1** | T2_Knockout_Ind_Score_1R | 🤖 Headless | ✅ PASSED | 59.94s | Status validation ✅ |
| **2** | T2_Knockout_Ind_Score_2R | ⏳ Pending | - | - | - |
| **3** | T2_Knockout_Ind_Score_3R | ⏳ Pending | - | - | - |

**Validation Checklist**:
- [ ] 2R: Knockout bracket progression works
- [ ] 2R: Skill rewards correct for multi-round knockout
- [ ] 2R: Tournament status = REWARDS_DISTRIBUTED
- [ ] 3R: Knockout bracket progression works
- [ ] 3R: Skill rewards correct for multi-round knockout
- [ ] 3R: Tournament status = REWARDS_DISTRIBUTED

---

## ⏱️ TIME_BASED Configurations

### T3: League + INDIVIDUAL + TIME_BASED

| Rounds | Config ID | Test Mode | Status | Duration | Notes |
|--------|-----------|-----------|--------|----------|-------|
| **1** | T3_League_Ind_Time_1R | ⏳ Pending | - | - | ASC ranking (lower is better) |
| **2** | T3_League_Ind_Time_2R | ⏳ Pending | - | - | - |
| **3** | T3_League_Ind_Time_3R | ⏳ Pending | - | - | - |

**Validation Checklist**:
- [ ] 1R: ASC ranking works (fastest time = 1st)
- [ ] 1R: Time measurement unit displayed
- [ ] 2R: Multi-round time aggregation
- [ ] 3R: Multi-round time aggregation

---

### T4: Knockout + INDIVIDUAL + TIME_BASED

| Rounds | Config ID | Test Mode | Status | Duration | Notes |
|--------|-----------|-----------|--------|----------|-------|
| **1** | T4_Knockout_Ind_Time_1R | ⏳ Pending | - | - | ASC ranking (lower is better) |
| **2** | T4_Knockout_Ind_Time_2R | ⏳ Pending | - | - | - |
| **3** | T4_Knockout_Ind_Time_3R | ⏳ Pending | - | - | - |

**Validation Checklist**:
- [ ] 1R: ASC ranking works
- [ ] 2R: Knockout + time-based works
- [ ] 3R: Knockout + time-based works

---

## 📏 DISTANCE_BASED Configurations

### T5: League + INDIVIDUAL + DISTANCE_BASED

| Rounds | Config ID | Test Mode | Status | Duration | Notes |
|--------|-----------|-----------|--------|----------|-------|
| **1** | T5_League_Ind_Distance_1R | ⏳ Pending | - | - | DESC ranking (higher is better) |
| **2** | T5_League_Ind_Distance_2R | ⏳ Pending | - | - | - |
| **3** | T5_League_Ind_Distance_3R | ⏳ Pending | - | - | - |

**Validation Checklist**:
- [ ] 1R: DESC ranking works (longest distance = 1st)
- [ ] 1R: Distance measurement unit displayed
- [ ] 2R: Multi-round distance aggregation
- [ ] 3R: Multi-round distance aggregation

---

### T6: Knockout + INDIVIDUAL + DISTANCE_BASED

| Rounds | Config ID | Test Mode | Status | Duration | Notes |
|--------|-----------|-----------|--------|----------|-------|
| **1** | T6_Knockout_Ind_Distance_1R | ⏳ Pending | - | - | DESC ranking (higher is better) |
| **2** | T6_Knockout_Ind_Distance_2R | ⏳ Pending | - | - | - |
| **3** | T6_Knockout_Ind_Distance_3R | ⏳ Pending | - | - | - |

**Validation Checklist**:
- [ ] 1R: DESC ranking works
- [ ] 2R: Knockout + distance-based works
- [ ] 3R: Knockout + distance-based works

---

## 🏆 PLACEMENT Configurations

### T7: League + INDIVIDUAL + PLACEMENT

| Rounds | Config ID | Test Mode | Status | Duration | Notes |
|--------|-----------|-----------|--------|----------|-------|
| **1** | T7_League_Ind_Placement_1R | ⏳ Pending | - | - | ASC ranking (lower is better) |
| **2** | T7_League_Ind_Placement_2R | ⏳ Pending | - | - | - |
| **3** | T7_League_Ind_Placement_3R | ⏳ Pending | - | - | - |

**Validation Checklist**:
- [ ] 1R: ASC ranking works (1st place = rank 1)
- [ ] 1R: Placement logic correct
- [ ] 2R: Multi-round placement aggregation
- [ ] 3R: Multi-round placement aggregation

---

### T8: Knockout + INDIVIDUAL + PLACEMENT

| Rounds | Config ID | Test Mode | Status | Duration | Notes |
|--------|-----------|-----------|--------|----------|-------|
| **1** | T8_Knockout_Ind_Placement_1R | ⏳ Pending | - | - | ASC ranking (lower is better) |
| **2** | T8_Knockout_Ind_Placement_2R | ⏳ Pending | - | - | - |
| **3** | T8_Knockout_Ind_Placement_3R | ⏳ Pending | - | - | - |

**Validation Checklist**:
- [ ] 1R: ASC ranking works
- [ ] 2R: Knockout + placement works
- [ ] 3R: Knockout + placement works

---

## 🔄 ROUNDS_BASED Configurations

### T9: League + INDIVIDUAL + ROUNDS_BASED

| Rounds | Config ID | Test Mode | Status | Duration | Notes |
|--------|-----------|-----------|--------|----------|-------|
| **1** | T9_League_Ind_Rounds_1R | ⏳ Pending | - | - | DESC ranking (higher is better) |
| **2** | T9_League_Ind_Rounds_2R | ⏳ Pending | - | - | - |
| **3** | T9_League_Ind_Rounds_3R | ⏳ Pending | - | - | - |

**Validation Checklist**:
- [ ] 1R: DESC ranking works (most rounds = 1st)
- [ ] 1R: Rounds measurement unit displayed
- [ ] 2R: Multi-round rounds aggregation
- [ ] 3R: Multi-round rounds aggregation

---

### T10: Knockout + INDIVIDUAL + ROUNDS_BASED

| Rounds | Config ID | Test Mode | Status | Duration | Notes |
|--------|-----------|-----------|--------|----------|-------|
| **1** | T10_Knockout_Ind_Rounds_1R | ⏳ Pending | - | - | DESC ranking (higher is better) |
| **2** | T10_Knockout_Ind_Rounds_2R | ⏳ Pending | - | - | - |
| **3** | T10_Knockout_Ind_Rounds_3R | ⏳ Pending | - | - | - |

**Validation Checklist**:
- [ ] 1R: DESC ranking works
- [ ] 2R: Knockout + rounds-based works
- [ ] 3R: Knockout + rounds-based works

---

## Summary Statistics

### Overall Progress

| Metric | Value |
|--------|-------|
| **Total Configurations** | 30 (10 scoring types × 3 round variants) |
| **Completed Tests** | 2/30 (6.7%) |
| **Pending Tests** | 28/30 (93.3%) |
| **Pass Rate** | 2/2 (100%) |
| **Average Duration** | 97.3s (headed: 134.69s, headless: 59.94s) |

### By Round Count

| Rounds | Total Configs | Completed | Pass Rate |
|--------|---------------|-----------|-----------|
| **1 Round** | 10 | 2/10 (20%) | 100% (2/2) |
| **2 Rounds** | 10 | 0/10 (0%) | - |
| **3 Rounds** | 10 | 0/10 (0%) | - |

### By Scoring Type

| Scoring Type | Total Configs | Completed | Pass Rate |
|--------------|---------------|-----------|-----------|
| SCORE_BASED | 6 (2×3 rounds) | 2/6 (33.3%) | 100% (2/2) |
| TIME_BASED | 6 (2×3 rounds) | 0/6 (0%) | - |
| DISTANCE_BASED | 6 (2×3 rounds) | 0/6 (0%) | - |
| PLACEMENT | 6 (2×3 rounds) | 0/6 (0%) | - |
| ROUNDS_BASED | 6 (2×3 rounds) | 0/6 (0%) | - |

### By Test Mode

| Mode | Tests Run | Pass Rate | Avg Duration |
|------|-----------|-----------|--------------|
| 🎬 Headed | 1 | 100% (1/1) | 134.69s |
| 🤖 Headless | 1 | 100% (1/1) | 59.94s |

---

## Testing Strategy

### Phase 1: SCORE_BASED Stabilization ✅ (In Progress)
**Goal**: Validate multi-round behavior with simplest scoring type

**Tests**:
1. ✅ T1_League_Ind_Score_1R (headed) - PASSED
2. ✅ T2_Knockout_Ind_Score_1R (headless) - PASSED
3. ⏳ T1_League_Ind_Score_2R (headed) - PENDING
4. ⏳ T2_Knockout_Ind_Score_2R (headless) - PENDING
5. ⏳ T1_League_Ind_Score_3R (headed) - PENDING
6. ⏳ T2_Knockout_Ind_Score_3R (headless) - PENDING

**Success Criteria**:
- All 6 SCORE_BASED tests pass
- Rankings display correctly across all rounds
- Skill rewards aggregated correctly
- Tournament status = REWARDS_DISTRIBUTED

---

### Phase 2: TIME_BASED Expansion (After Phase 1)
**Goal**: Validate ASC ranking (lower is better) logic

**Tests**:
1. T3_League_Ind_Time_1R (headed)
2. T4_Knockout_Ind_Time_1R (headless)
3. T3_League_Ind_Time_2R
4. T4_Knockout_Ind_Time_2R
5. T3_League_Ind_Time_3R
6. T4_Knockout_Ind_Time_3R

**Critical Validations**:
- ASC ranking works (fastest time = 1st place)
- Time measurement unit displayed correctly
- Multi-round time aggregation correct

---

### Phase 3: DISTANCE_BASED Expansion (After Phase 2)
**Goal**: Validate DESC ranking with distance metric

**Tests**: Same structure as Phase 2 (6 tests)

**Critical Validations**:
- DESC ranking works (longest distance = 1st place)
- Distance measurement unit displayed correctly
- Multi-round distance aggregation correct

---

### Phase 4: PLACEMENT Expansion (After Phase 3)
**Goal**: Validate ASC ranking with placement logic

**Tests**: Same structure as Phase 2 (6 tests)

**Critical Validations**:
- ASC ranking works (1st place = rank 1)
- Placement logic correct
- Multi-round placement aggregation correct

---

### Phase 5: ROUNDS_BASED Expansion (After Phase 4)
**Goal**: Validate DESC ranking with rounds metric

**Tests**: Same structure as Phase 2 (6 tests)

**Critical Validations**:
- DESC ranking works (most rounds = 1st place)
- Rounds measurement unit displayed correctly
- Multi-round rounds aggregation correct

---

## Known Issues & Observations

### Issue #1: Multi-Round Result Submission
**Status**: ⚠️ **TO BE VALIDATED**

**Question**: How does the UI handle multiple rounds?
- Does it show "Round 1 of 3", "Round 2 of 3", etc.?
- Does it require separate result submission per round?
- Does it finalize after each round or only at the end?

**Validation Needed**: Run 2R and 3R tests to confirm UI behavior

---

### Issue #2: Skill Rewards Aggregation
**Status**: ⚠️ **TO BE VALIDATED**

**Question**: How are skill rewards distributed in multi-round tournaments?
- Are rewards distributed after each round?
- Are rewards aggregated at the end?
- Does the top 3 XP bonus apply per round or per tournament?

**Validation Needed**: Check skill_rewards and xp_transactions tables after 2R/3R tests

---

### Issue #3: Performance with Multiple Rounds
**Status**: ⚠️ **TO BE VALIDATED**

**Hypothesis**: 3-round tests may take 3× longer than 1-round tests

**Expected Durations**:
- 1R headed: ~135s
- 2R headed: ~270s (4.5 min)
- 3R headed: ~405s (6.75 min)

**Mitigation**: Use headless mode for 2R/3R tests to reduce duration

---

## Test Execution Plan

### Immediate Next Steps (This Session)

1. **✅ Verify 1R stability** (T1, T2) - DONE
2. **⏳ Run T1_League_Ind_Score_2R (headed)** - IN PROGRESS
3. **⏳ Run T2_Knockout_Ind_Score_2R (headless)** - NEXT
4. **⏳ Observe multi-round UI behavior**
5. **⏳ Run T1_League_Ind_Score_3R (headed)**
6. **⏳ Run T2_Knockout_Ind_Score_3R (headless)**

### After SCORE_BASED Complete

7. Run TIME_BASED 1R tests (T3, T4)
8. Run TIME_BASED 2R tests
9. Run TIME_BASED 3R tests
10. Continue with DISTANCE_BASED, PLACEMENT, ROUNDS_BASED

---

## Tracking Legend

### Test Status
- ✅ **PASSED**: Test completed successfully
- ❌ **FAILED**: Test failed, see notes for details
- ⏳ **PENDING**: Test not yet run
- 🔄 **RUNNING**: Test in progress
- ⚠️ **FLAKY**: Test passed but with warnings

### Test Modes
- 🎬 **Headed**: Browser visible (for visual validation)
- 🤖 **Headless**: Browser hidden (for speed)

### Validation Types
- **Ranking Display**: Proper ranks (🥇 1st, 🥈 2nd, 🥉 3rd, #4...) without 0-based index
- **Status Update**: Tournament status = REWARDS_DISTRIBUTED
- **Skill Rewards**: Skill points distributed correctly
- **XP Transactions**: Top 3 get 100/75/50 XP
- **UI Behavior**: Forms, buttons, tables display correctly

---

**Document Created**: 2026-02-03 22:45
**Last Updated**: 2026-02-03 22:45
**Next Review**: After SCORE_BASED Phase 1 complete (6/6 tests)
