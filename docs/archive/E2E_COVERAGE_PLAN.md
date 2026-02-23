# E2E Test Coverage Plan — Tournament Monitor Wizard

**Status:** ⚠️ REQUIRED before Phase B continuation
**Tool:** Playwright (headless)
**Target:** Tournament Monitor 8-step wizard (streamlit_app/pages/Tournament_Monitor.py)
**Priority:** BLOCKER (Phase B migration cannot proceed without this)

---

## 🎯 Coverage Requirements

### 1. Wizard Steps Coverage (8 steps)

| Step | Functionality | Coverage Status | Critical Paths |
|------|---------------|-----------------|----------------|
| **Step 1: Scenario** | Tournament type selection (GROUPS_ONLY, GROUPS_KNOCKOUT, MULTI_STAGE, etc.) | ❌ Not covered | 6 tournament types × validation |
| **Step 2: Format** | Participant count (4-1024), enrollment type, campus selection | ❌ Not covered | 5 participant ranges × 2 enrollment types |
| **Step 3: Configuration** | Phase config, advancement rules, tiebreaker selection | ❌ Not covered | 3 phase configs × 4 tiebreaker combos |
| **Step 4: Simulation** | Session preview generation, conflict detection | ❌ Not covered | Validation logic × error states |
| **Step 5: Review** | Final confirmation, edit/back navigation | ❌ Not covered | Navigation paths × state persistence |
| **Step 6: Game Preset** | Match scoring, duration, game type selection | ❌ Not covered | 3 game types × 2 scoring modes |
| **Step 7: Reward Config** | Reward policy, distribution rules | ❌ Not covered | 2 reward types × validation |
| **Step 8: Launch** | Tournament creation, backend submission | ❌ Not covered | Success/failure states |

**Current coverage:** 0/8 steps (0%)
**Required minimum:** 8/8 steps (100%) with critical paths

---

## 🌲 Decision Branch Coverage

### Scenario Selection (Step 1)

| Scenario | Participants | Expected Behavior | Test Status |
|----------|--------------|-------------------|-------------|
| GROUPS_ONLY | 8 participants | 2 groups, no knockout | ❌ Not tested |
| GROUPS_KNOCKOUT | 16 participants | 4 groups → QF/SF/Final | ❌ Not tested |
| SINGLE_ELIMINATION | 8 participants | Direct knockout bracket | ❌ Not tested |
| DOUBLE_ELIMINATION | 16 participants | Winners + Losers bracket | ❌ Not tested |
| SWISS | 16 participants | Swiss pairing algorithm | ❌ Not tested |
| ROUND_ROBIN | 4 participants | Full round-robin grid | ❌ Not tested |

**Current coverage:** 0/6 scenarios (0%)
**Required minimum:** 6/6 scenarios (100%)

### Participant Range Validation (Step 2)

| Range | Test Cases | Expected Validation | Test Status |
|-------|------------|---------------------|-------------|
| 4-8 participants | 4, 5, 8 | Valid, power-of-2 checks | ❌ Not tested |
| 9-16 participants | 9, 16 | Group size validation | ❌ Not tested |
| 17-32 participants | 17, 24, 32 | Multi-group scenarios | ❌ Not tested |
| 33-64 participants | 33, 64 | Large tournament handling | ❌ Not tested |
| 65-1024 participants | 128, 256, 1024 | Edge case, max capacity | ❌ Not tested |

**Current coverage:** 0/5 ranges (0%)
**Required minimum:** 5/5 ranges (100%)

### Game Type & Calculation Mode (Step 6)

| Game Type | Calculation Mode | Expected Points Formula | Test Status |
|-----------|------------------|------------------------|-------------|
| HEAD_TO_HEAD | WIN_LOSS | Win=3, Draw=1, Loss=0 | ❌ Not tested |
| HEAD_TO_HEAD | GOAL_DIFFERENTIAL | Points + GD tiebreaker | ❌ Not tested |
| TEAM_VS_TEAM | WIN_LOSS | Team aggregation | ❌ Not tested |
| FREE_FOR_ALL | RANKING_POINTS | 1st=10, 2nd=7, 3rd=5, 4th=3 | ❌ Not tested |

**Current coverage:** 0/4 combinations (0%)
**Required minimum:** 4/4 combinations (100%)

---

## ✅ Assertion Policy

### UI State Transition Assertions

**Required checks per step:**
- ✅ Current step indicator highlighted
- ✅ Progress bar percentage correct
- ✅ Navigation buttons enabled/disabled correctly
- ✅ Form fields populated with previous values on "Back" navigation
- ✅ Error messages displayed for invalid inputs
- ✅ Success toast/notification after step completion

**Example Playwright assertion:**
```python
# Step 1 → Step 2 transition
await expect(page.locator('[data-testid="wizard-step-2"]')).to_have_class(/active/)
await expect(page.locator('[data-testid="progress-bar"]')).to_have_attribute("aria-valuenow", "25")
await expect(page.locator('[data-testid="participant-count"]')).to_be_visible()
```

### Computed Values Correctness

**Critical calculations to validate:**
- Group count = `ceil(participants / 4)` for GROUPS_ONLY
- Knockout rounds = `log2(qualified_teams)` for GROUPS_KNOCKOUT
- Total sessions = `sum(group_matches) + knockout_matches`
- Session duration estimate = `sessions × match_duration × buffer_factor`

**Example Playwright assertion:**
```python
# Validate computed group count
participants = 16
expected_groups = 4
await expect(page.locator('[data-testid="computed-groups"]')).to_have_text(f"{expected_groups} groups")
```

### Backend Side Effects (DB State)

**Post-launch validation:**
- ✅ Tournament record created in DB (`tournaments` table)
- ✅ Sessions generated correctly (`sessions` table)
- ✅ Participants enrolled (`tournament_enrollments` table)
- ✅ Reward policy assigned (`semesters.reward_policy_snapshot`)
- ✅ Game preset applied (`sessions.game_type`, `sessions.scoring_type`)

**Example Playwright + DB assertion:**
```python
# After wizard completion
tournament_id = await page.locator('[data-testid="tournament-id"]').text_content()

# Validate DB state (via API or direct DB query)
response = await api_get(f"/api/v1/tournaments/{tournament_id}")
assert response["status"] == "READY_FOR_ENROLLMENT"
assert len(response["sessions"]) == expected_session_count
```

### Error State Handling

**Negative test scenarios:**
- ❌ Invalid participant count (e.g., 3 participants, 1025 participants)
- ❌ Conflicting campus schedules
- ❌ Missing required fields (enrollment deadline, instructor)
- ❌ Backend failure (500 error, timeout)
- ❌ Insufficient credits for tournament creation

**Example Playwright assertion:**
```python
# Invalid participant count
await page.fill('[data-testid="participant-count"]', "3")
await page.click('[data-testid="next-button"]')
await expect(page.locator('[data-testid="error-message"]')).to_contain_text("Minimum 4 participants required")
await expect(page.locator('[data-testid="next-button"]')).to_be_disabled()
```

---

## 🧪 Test Execution Evidence

### Required Artifacts

1. **CI Integration**
   - GitHub Actions workflow: `.github/workflows/e2e-wizard-coverage.yml`
   - Triggered on: PR to main/develop, manual dispatch
   - Runs: Headless Playwright tests against test DB

2. **Test Reports**
   - JUnit XML: `test-results/junit.xml`
   - HTML Report: `playwright-report/index.html`
   - Coverage summary: `coverage-summary.json`

3. **Screenshot/Video Capture**
   - On failure: Screenshot + video trace
   - Storage: `test-results/failures/`
   - Artifact upload: GitHub Actions artifacts

4. **Assertion Metrics**
   - Total assertions: ~150+ (across all scenarios)
   - Critical path assertions: ~80
   - Edge case assertions: ~40
   - Error state assertions: ~30

---

## 📊 Coverage Matrix Template

### Test Suite Structure

```
tests_e2e/wizard/
├── test_wizard_step1_scenario.py          # Scenario selection (6 tests)
├── test_wizard_step2_format.py            # Participant range (10 tests)
├── test_wizard_step3_configuration.py     # Phase config (12 tests)
├── test_wizard_step4_simulation.py        # Preview generation (8 tests)
├── test_wizard_step5_review.py            # Navigation + state (6 tests)
├── test_wizard_step6_game_preset.py       # Game type (4 tests)
├── test_wizard_step7_reward_config.py     # Reward policy (4 tests)
├── test_wizard_step8_launch.py            # Tournament creation (8 tests)
├── test_wizard_navigation.py              # Back/forward navigation (10 tests)
├── test_wizard_edge_cases.py              # Error states (12 tests)
└── conftest.py                            # Fixtures, DB setup
```

**Total planned tests:** ~80 E2E tests
**Estimated execution time:** ~15 minutes (headless, parallel)

---

## 🚨 Blocking Criteria

**Phase B migration CANNOT proceed until:**

- [ ] All 8 wizard steps have automated Playwright tests
- [ ] All 6 tournament scenarios covered
- [ ] All 5 participant ranges validated
- [ ] All 4 game type combinations tested
- [ ] All critical assertions implemented (150+ total)
- [ ] Headless execution proven (CI log + JUnit report)
- [ ] Screenshot capture configured for failures
- [ ] DB state validation implemented (post-launch checks)
- [ ] Error state handling tested (negative scenarios)
- [ ] **100% success rate** on CI (0 flaky tests tolerated)

**Current status:** ❌ 0/10 requirements met

---

## 📅 Implementation Timeline Estimate

| Phase | Tasks | Duration | Deliverables |
|-------|-------|----------|--------------|
| **Phase 1: Infrastructure** | Playwright setup, fixtures, DB seeding | 1 day | conftest.py, base fixtures |
| **Phase 2: Core Steps** | Steps 1-5 tests (navigation + config) | 2-3 days | 44 tests |
| **Phase 3: Advanced Steps** | Steps 6-8 tests (game preset, rewards, launch) | 1-2 days | 16 tests |
| **Phase 4: Edge Cases** | Error states, negative tests, edge scenarios | 1 day | 20 tests |
| **Phase 5: CI Integration** | GitHub Actions, artifact upload, reporting | 0.5 day | e2e-wizard-coverage.yml |
| **Total** | | **5-7 days** | 80 tests, CI pipeline |

**Note:** This is a **prerequisite** for Phase B, not optional.

---

## 🎯 Success Criteria

**Definition of "E2E validated":**
- ✅ 80+ Playwright tests written
- ✅ 100% wizard step coverage
- ✅ 150+ assertions (UI state, computed values, DB state, errors)
- ✅ Headless execution successful (CI log proof)
- ✅ JUnit/HTML report generated
- ✅ Screenshot/video capture on failure
- ✅ 100% success rate (no flaky tests)
- ✅ Runs in <20 minutes (acceptable CI time)

**Only then:** Phase B migration resumes.

---

## 📝 Next Steps

1. **Immediate:** Review and approve this coverage plan
2. **Week 1:** Implement Phase 1-2 (infrastructure + core steps)
3. **Week 2:** Implement Phase 3-5 (advanced steps + CI)
4. **Checkpoint:** Validate 100% success rate on CI
5. **After approval:** Resume Phase B migration with proven E2E safety net

---

**Status:** ⏸️ Phase B BLOCKED until E2E coverage complete.

**Priority:** High (blocks migration progress, but ensures sustainable quality).

**Owner:** [Assign to E2E test engineer / QA lead]

---

**Remember:** "Measure twice, cut once." Proper E2E coverage is the foundation for safe, sustainable migration.
