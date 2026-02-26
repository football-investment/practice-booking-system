# Option B Execution Plan: Test Re-Scope (Phased Approach)

**Date**: 2026-02-26
**Strategy**: Controlled, phased migration - NOT "big bang"
**Goal**: Clean separation: Smoke (endpoint correctness) vs E2E (workflow validation)

---

## Architectural Vision

### Target State

```
tests/integration/api_smoke/          (Smoke Suite - Endpoint Correctness)
├── 99 PASSED (stable baseline)       ✅ RBAC validated
├── 14 FIXED (Phase 1)                ✅ Lifecycle + Infrastructure
└── Baseline: 22F/113P/75S            ✅ Endpoint validation complete

tests_e2e/integration_workflows/      (E2E Suite - Workflow Validation)
├── 22 MIGRATED (Pattern 1+3)         ✅ Full fixture infrastructure
├── Baseline: 0F/22P                  ✅ E2E workflow coverage
└── Separate CI gate (non-blocking)   ✅ Isolated from smoke stability
```

**Strategic Benefit**: Smoke suite stays **stable, deterministic, fast** (endpoint validation). E2E suite handles **complex workflow validation** with proper infrastructure.

---

## Phase Breakdown

### Phase 1: Low Risk Fixes (14 tests → ~2-3 days)

**Goal**: Quick wins within existing smoke suite - NO structural changes

#### Phase 1.1: Pattern 4 Fix (7 tests, ~4-6 hours)

**Scope**: Add missing infrastructure files/resources

**Tests** (7):
1. test_get_reward_policy_details_happy_path → Add `default_policy.json`
2. test_preview_tournament_rewards_happy_path → Ensure reward config exists
3. test_preview_tournament_sessions_happy_path → Ensure tournament_type config
4. test_get_generation_status_happy_path → Add generation task tracking fixture
5. test_get_generation_status_auth_required → (same as #4)
6. test_get_rounds_status_happy_path → Add rounds state tracking fixture
7. test_get_rounds_status_auth_required → (same as #6)

**Execution**:
- Create missing policy files (app/data/reward_policies/default_policy.json)
- Add generation/rounds tracking fixtures (conftest.py or test setup)
- Validate: 1 test at a time, smoke run + 3x determinism, commit

**Expected Outcome**: 36F → 29F (+7 PASS, 19% improvement)

**ACTUALS (2026-02-26)**:
- ✅ **Result**: 36F → 31F (+5 PASS, 14% improvement)
- ✅ **Tests Fixed**: 5/7 (71%)
  - #1: default_policy.json created ✅
  - #4-5: test_generation_task_id fixture ✅ (2 tests)
  - #6-7: test_rounds_session_id fixture ✅ (2 tests)
- ⚠️ **CASCADE STOP**: 2/7 tests (29%)
  - #2: test_preview_tournament_rewards → Requires reward_config DB record (not file)
  - #3: test_preview_tournament_sessions → Requires tournament_type config (not file)
- **Pattern 4 Taxonomy Correction**: 71% pure infrastructure, 29% cascade overlap
- **Time**: ~2.5 hours (within estimate)
- **Commit**: 4fcea87

---

#### Phase 1.2: Pattern 2 Stabilization (7 tests, ~8-12 hours)

**Scope**: Integrate lifecycle helpers (already documented in Category 3)

**Tests** (7):
8. test_transition_tournament_status_happy_path → Use lifecycle helper
9. test_instructor_accept_assignment_happy_path → Setup PENDING_INSTRUCTOR_ACCEPTANCE state
10. test_instructor_decline_assignment_happy_path → (same as #9)
11. test_approve_instructor_application_happy_path → Setup SEEKING_INSTRUCTOR + application
12. test_approve_instructor_application_auth_required → (same as #11)
13. test_decline_instructor_application_happy_path → (same as #11)
14. test_decline_instructor_application_auth_required → (same as #11)

**Execution**:
- Leverage existing `lifecycle_helpers.py` (Category 3)
- Create additional helper: `create_instructor_application_with_state()`
- Update test fixtures to use helpers
- Validate: 1 test at a time, smoke run + 3x determinism, commit

**Expected Outcome**: 29F → 22F (+7 PASS, 39% total improvement from Phase 1)

**REVISED TARGET** (based on Phase 1.1 actuals): 31F → 24F (+7 PASS if all succeed)

**Stop Rule**: If lifecycle setup becomes complex cascade, **STOP** and move to Phase 2 (E2E migration).

**ACTUALS (2026-02-26)**:
- ✅ **Result**: 31F → 30F (+1 PASS, 14%)
- ✅ **Tests Fixed**: 1/7 (14%)
  - #8: test_transition_tournament_status_happy_path → DRAFT→CANCELLED transition ✅
- ⚠️ **CASCADE STOP**: 6/7 tests (86%)
  - #9-10: Instructor accept/decline → Requires PENDING_INSTRUCTOR_ACCEPTANCE + assignment
  - #11-14: Approve/decline application → Requires SEEKING_INSTRUCTOR + sessions infrastructure
  - Root cause: All need TournamentType, GamePreset, multi-step lifecycle (CASCADE)
- **Pattern 2 Taxonomy Correction**: 14% simple lifecycle, 86% cascade overlap
- **Time**: ~1 hour (stopped early per STOP rule)
- **Phase 2 Revised Scope**: +6 tests migrated from Pattern 2
- **Commit**: a3a7537

---

### Phase 2: Structural Migration (28 tests → ~1-2 weeks)

**Goal**: Migrate Pattern 1 + Pattern 3 + Cascade overlap tests to dedicated E2E suite

**REVISED SCOPE** (post Phase 1 actuals):
- Original: 22 tests (Pattern 1: 9, Pattern 3: 13)
- Added from Pattern 4 cascade: 2 tests (#2-3 preview endpoints)
- Added from Pattern 2 cascade: 6 tests (#9-14 instructor assignment)
- **Total: 28 tests**

#### Phase 2.1: E2E Suite Scaffold (~8-12 hours)

**Scope**: Create `tests_e2e/integration_workflows/` infrastructure

**Deliverables**:
1. **Directory structure**:
   ```
   tests_e2e/
   ├── __init__.py
   ├── integration_workflows/
   │   ├── __init__.py
   │   ├── conftest.py          (E2E fixtures - comprehensive DB seed)
   │   ├── payload_builders.py  (Business-aware payload generation)
   │   └── test_tournament_workflows.py (migrated tests)
   ```

2. **E2E conftest.py** features:
   - Comprehensive DB seed (TournamentType, GamePreset, User profiles complete)
   - Lifecycle state management utilities
   - Full tournament setup (READY_FOR_ENROLLMENT state by default)
   - Business-aware payload builders (NOT schema-based)

3. **CI/CD integration**:
   - New gate: `integration-workflows-tests`
   - **Non-blocking initially** (warning-only)
   - Separate from smoke test gate

**Validation**: Run empty suite, verify fixture load time (<5s), determinism check

---

#### Phase 2.2: Pattern 1 + Pattern 3 Migration (22 tests, ~20-30 hours)

**Scope**: Move Fixture Cascade + Payload Generator tests to E2E suite

**Pattern 1 - Fixture Cascade** (9 tests):
1. test_create_tournament_happy_path
2. test_enroll_in_tournament_happy_path
3. test_generate_tournament_happy_path
4. test_generate_tournament_sessions_happy_path
5. test_run_ops_scenario_happy_path
6. test_complete_tournament_happy_path
7. test_distribute_tournament_rewards_happy_path
8. test_distribute_tournament_rewards_v2_happy_path
9. test_get_user_tournament_rewards_happy_path

**Pattern 3 - Payload Generator** (13 tests):
10. test_save_tournament_reward_config_happy_path
11. test_update_tournament_reward_config_happy_path
12. test_upsert_campus_schedule_happy_path
13. test_update_schedule_config_happy_path
14. test_record_match_results_happy_path
15. test_record_match_results_auth_required
16. test_submit_round_results_happy_path
17. test_submit_round_results_auth_required
18. test_submit_structured_match_results_happy_path
19. test_submit_structured_match_results_auth_required
20. test_submit_tournament_rankings_happy_path
21. test_finalize_individual_ranking_session_happy_path
22. test_finalize_individual_ranking_session_auth_required

**Execution**:
- Batch 1: Pattern 1 (9 tests) - fixture-heavy, full DB seed
- Batch 2: Pattern 3 (13 tests) - payload-heavy, business builders
- Replace `payload_factory` with `business_payload_builder`
- Validate: Batch at a time, 0 flake, determinism, commit

**Expected Outcome**:
- Smoke suite: **22F/113P/75S** → Stabilize to **0F/135P/75S** (Phase 1 complete)
- **REVISED** (post Phase 1.1): **31F/104P/75S** → Target **24F/111P/75S** (if Phase 1.2 complete)
- E2E suite: **0F/22P** (new baseline)

---

## Timeline & Effort

| Phase | Scope | Effort | Duration | Risk | Status |
|-------|-------|--------|----------|------|--------|
| **Phase 1.1** | Pattern 4 (5/7 tests) | 4-6 hours | 1 day | LOW | ✅ DONE (+5 PASS) |
| **Phase 1.2** | Pattern 2 (1/7 tests) | 8-12 hours | 1-2 days | LOW-MODERATE | ✅ DONE (+1 PASS, 6 CASCADE) |
| **Phase 2.1** | E2E Scaffold | 8-12 hours | 1-2 days | MODERATE | ⏭️ NEXT |
| **Phase 2.2** | Pattern 1+3 (22 tests) | 20-30 hours | 3-5 days | MODERATE |
| **TOTAL** | **36 tests** | **40-60 hours** | **~2 weeks** | **Managed** |

**Parallel Work Possible**: Phase 1.1 + 1.2 can run concurrently with Plan file E2E tests (student/instructor/refund lifecycles).

---

## Stop Rules

### Phase 1 Stop Rules

**STOP Phase 1.1 if**:
- Missing file fix → reveals deeper infrastructure issue
- >2 hours per test (should be <1h for file addition)

**STOP Phase 1.2 if**:
- Lifecycle helper → triggers fixture cascade (e.g., need GamePreset for INSTRUCTOR_CONFIRMED state)
- >3 hours per test (should be 1-2h with existing helpers)

**Pivot to Phase 2** if stopped - don't force in-place fixes.

### Phase 2 Stop Rules

**STOP Phase 2.1 if**:
- E2E fixture setup > 15s load time (performance issue)
- Non-deterministic behavior in E2E suite

**STOP Phase 2.2 if**:
- Test migration reveals endpoint bugs (not infrastructure issues)
- Payload builder complexity > 5h per test type (architectural issue)

---

## Success Metrics

### Phase 1 Success (Low Risk)

**PLANNED**:
- 14/36 tests fixed (39% improvement)
- Smoke baseline: 22F/113P/75S

**ACTUALS** (2026-02-26):
- ✅ 6/36 tests fixed (17% improvement) → 30F/105P/75S
- ✅ Pattern 4: 5/7 (71% success), 2 cascade
- ✅ Pattern 2: 1/7 (14% success), 6 cascade
- ✅ 100% deterministic (all fixes stable)
- ✅ No regressions in existing PASS tests
- ✅ 0 ERROR maintained
- ✅ Time: ~4 hours (vs 2-3 days estimated)
- ⚠️ **Revised understanding**: 57% of "Pattern 2+4" tests are cascade overlap → Phase 2

### Phase 2 Success (Structural)

- ✅ E2E suite created: `tests_e2e/integration_workflows/`
- ✅ 22 tests migrated (Pattern 1+3)
- ✅ E2E baseline: **0F/22P**
- ✅ Smoke suite clean: **0F/135P/75S** (if Phase 1.1+1.2 complete)
- ✅ CI/CD: Separate gates (smoke BLOCKING, E2E warning-only initially)
- ✅ Clear separation: Smoke (endpoint) vs E2E (workflow)

---

## Rollback Strategy

### Phase 1 Rollback

- Remove added files (Pattern 4)
- Revert lifecycle helper integration (Pattern 2)
- Restore baseline: **36F/99P/75S**
- **Low risk** - smoke suite structure unchanged

### Phase 2 Rollback

- Delete `tests_e2e/integration_workflows/` directory
- Keep smoke suite unchanged (Phase 1 fixes remain)
- Baseline: **22F/113P/75S** (Phase 1 complete)
- **Moderate risk** - new directory, easy to remove

---

## Next Action: Phase 1.1 Start

**Immediate Task**: Pattern 4 Fix (7 tests, infrastructure/file)

**First Test**: `test_get_reward_policy_details_happy_path`
- Error: "Policy file not found: default_policy.json"
- Fix: Create `app/data/reward_policies/default_policy.json`
- Validation: Smoke run + 3x determinism + commit

**Execute**: Start Phase 1.1 now.
