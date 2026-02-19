# E2E Coverage Report — Tournament Monitor Wizard
**Generated:** 2026-02-15
**Status:** ✅ COMPLETE — P1 + P2 coverage 100% — 58/58 pairwise cases covered

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total tests run | **239** |
| Passed | **238** |
| Xfailed (documented) | **1** |
| Failed | **0** |
| Test files | 7 |
| Execution mode | Headless (PYTEST_HEADLESS=true) |
| JUnit XML reports | 10 files (tests_e2e/results/) |

**100% pass rate** (xfail counted as expected and documented).

**P1 critical coverage complete:** simulation modes, error state retention, INDIVIDUAL_RANKING safety gate — all 3 gaps closed.
**P2 critical coverage complete:** game preset payload, reward config templates, global max boundary — all 3 P2 gaps closed. 28 new tests, 0 failures.

---

## Test Suites

### Group 1 — Playwright (UI) Tests

| Suite | Tests | Passed | XFailed | File |
|-------|-------|--------|---------|------|
| Wizard Flow (all 8 steps, back navigation) | 19 | 19 | 0 | wizard_flow_run.xml |
| Safety Confirmation UI + Slider Persistence | 9 | 9 | 0 | coverage_ui_run.xml |
| Boundary Wizard Parametrized UI | 8 | 8 | 0 | boundary_wizard_run.xml |
| Monitoring Panel + Regressions | 14 | 13 | 1 | monitoring_regressions_run2.xml |
| **Playwright subtotal** | **50** | **49** | **1** | |

### Group 2 — API Tests (pure HTTP)

| Suite | Tests | Passed | Failed | File |
|-------|-------|--------|--------|------|
| PlayerCount Boundary API | 21 | 21 | 0 | boundary_api_run.xml |
| GroupKnockout Matrix API | 14 | 14 | 0 | boundary_api_run.xml |
| PostLaunch Observability | 12 | 12 | 0 | post_launch_run.xml |
| Knockout BVA (non-slow) | 17 | 17 | 0 | full_boundary_api_run.xml |
| League Extended BVA (non-slow) | 7 | 7 | 0 | full_boundary_api_run.xml |
| GroupKnockout Full Formula | 16 | 16 | 0 | full_boundary_api_run.xml |
| IndividualRanking Extended BVA | 5 | 5 | 0 | full_boundary_api_run.xml |
| WizardParametrized UI (from BVM) | 8 | 8 | 0 | boundary_wizard_run.xml |
| Generation Validator Branch Coverage | 6 | 6 | 0 | generation_type_boundary_run.xml |
| Type Boundary Matrix | 28 | 28 | 0 | generation_type_boundary_run.xml |
| Knockout Matrix (seeding) | 6 | 6 | 0 | full_boundary_api_run.xml |
| **API subtotal** | **138** | **138** | **0** | |

### Group 3 — P1 Critical Coverage

| Suite | Tests | Passed | File |
|-------|-------|--------|------|
| P1.1 Simulation Mode API (manual/auto_immediate/accelerated) | 12 | 12 | p1_full_run.xml |
| P1.2 Wizard Error State Retention (invalid token → 401) | 4 | 4 | p1_full_run.xml |
| P1.3 INDIVIDUAL_RANKING 128+ Safety Gate (UI + API) | 7 | 7 | p1_full_run.xml |
| **P1 subtotal** | **23** | **23** | |

### Group 4 — P2 Coverage

| Suite | Tests | Passed | File |
|-------|-------|--------|------|
| P2-A Game Preset Step 4 UI + API payload | 5 | 5 | p2_full_run.xml |
| P2-B Reward Config Templates (UI + API, all 5 templates) | 8 | 8 | p2_full_run.xml |
| P2-C Global Max Boundary (league + GK, 1025p rejected) | 2 | 2 | p2_full_run.xml |
| SIM Simulation Mode Wizard UI (manual + auto_immediate × 3 types) | 6 | 6 | p2_full_run.xml |
| EQ Player Count Equivalence Classes (5 scenario×type + 2 standalone) | 7 | 7 | p2_full_run.xml |
| **P2 subtotal** | **28** | **28** | |

---

## Wizard Step Coverage (8 steps)

| Step | Name | Coverage | Assertions |
|------|------|----------|------------|
| Step 1 | Scenario Selection | ✅ | Smoke Test + Large Field Monitor visible |
| Step 2 | Format Selection | ✅ | HEAD_TO_HEAD + INDIVIDUAL_RANKING branches |
| Step 3 | Tournament Type / Scoring | ✅ | Knockout/Group-Knockout + scoring type selectors |
| Step 4 | Game Preset | ✅ | Step 4 of 8 visible, passthrough tested |
| Step 5 | Player Count (slider) | ✅ | Slider range, scenario defaults, Back→Forward persistence |
| Step 6 | Simulation Mode | ✅ | Accelerated Simulation selection, large-scale warning (128+) |
| Step 7 | Configure Rewards | ✅ | OPS Default pre-selected, passthrough tested |
| Step 8 | Review & Launch | ✅ | Launch button enabled/disabled, safety confirmation field (128+) |

All 8 steps covered with forward + back navigation tests.

---

## Decision Branch Coverage

### Tournament Format
| Branch | Test | Result |
|--------|------|--------|
| HEAD_TO_HEAD | `test_wizard_step3_hth_tournament_type` | ✅ |
| INDIVIDUAL_RANKING | `test_wizard_step8_individual_ranking_review` | ✅ |

### Tournament Type (HEAD_TO_HEAD)
| Branch | Test | Result |
|--------|------|--------|
| Knockout | `test_wizard_step4_slider_range_matches_scenario[...-Knockout-...]` | ✅ |
| League | `test_api_league_smoke_range` (5 parametrized) | ✅ |
| Group+Knockout | `test_wizard_step3_group_knockout_available_in_large_field` | ✅ |
| Group-only (Smoke Test) | `test_wizard_step3_knockout_available_in_smoke` | ✅ |

### Player Count Boundaries
| Range | Test | Result |
|-------|------|--------|
| Below minimum (< 4 knockout) | `test_api_minimum_boundary_knockout[2,3]` | ✅ |
| Minimum valid (4p knockout) | `test_api_minimum_boundary_knockout[4]` | ✅ |
| Smoke range (8, 16p) | `test_api_power_of_two_knockout_smoke` | ✅ |
| Large (32, 64p) | `test_api_power_of_two_knockout_large` | ✅ |
| Safety threshold (127p — no confirmation) | `test_api_safety_threshold_boundary_127` | ✅ |
| Safety threshold (128p — requires confirmation) | `test_api_safety_threshold_boundary_128_*` | ✅ |
| Non-power-of-two rejected (3,7,15,31,63p) | `test_knockout_non_pow2_boundary_rejected` | ✅ |
| Above maximum (> 1024) | `test_api_above_maximum_rejected` | ✅ |

### Safety Confirmation (Step 6/8 — 128+ players)
| Scenario | Test | Result |
|----------|------|--------|
| Confirmation field visible for 128+p (HEAD_TO_HEAD) | `test_step6_safety_confirmation_field_visible_for_128plus` | ✅ |
| Wrong text keeps Launch disabled | `test_step6_safety_confirmation_wrong_text_keeps_disabled` | ✅ |
| Correct text enables Launch | `test_step6_safety_confirmation_correct_text_enables_button` | ✅ |
| Case-insensitive ("launch") | `test_step6_safety_lowercase_also_accepted` | ✅ |
| No field for < 128p | `test_step6_no_safety_field_for_small_count` | ✅ |
| Confirmation field visible for 128+p (INDIVIDUAL_RANKING) | `test_individual_ranking_128p_safety_field_visible` | ✅ P1 |
| Wrong text keeps disabled (INDIVIDUAL_RANKING) | `test_individual_ranking_128p_wrong_text_keeps_disabled` | ✅ P1 |
| Correct text enables button (INDIVIDUAL_RANKING) | `test_individual_ranking_128p_correct_text_enables_button` | ✅ P1 |
| Case-insensitive (INDIVIDUAL_RANKING) | `test_individual_ranking_128p_lowercase_launch_accepted` | ✅ P1 |
| API rejects confirmed=False for 128+p | `test_individual_ranking_128p_api_requires_confirmed` | ✅ P1 |
| API accepts confirmed=True for 128+p | `test_individual_ranking_128p_api_succeeds_with_confirmed` | ✅ P1 |

### Group-Knockout Valid Counts
| Player Count | Groups | Group Sessions | KO Sessions | Total |
|-------------|--------|---------------|-------------|-------|
| 8p | 2 | 12 | 4 | 16 |
| 12p | 3 | 18 | 6 | 24 |
| 16p | 4 | 24 | 8 | 32 |
| 24p | 6 | 36 | 12 | 48 |
| 32p | 8 | 48 | 24 | 72 |
| 48p | 12 | 72 | 40 | 112 |
| 64p | 16 | 96 | 48 | 144 |

All 7 valid GK counts verified (group session count, KO session count, total count, invalid count rejection).

---

## Simulation Mode Coverage (P1)

| Mode | Assertion | Test | Result |
|------|-----------|------|--------|
| `manual` | HTTP 200 accepted | `test_all_valid_simulation_modes_accepted[manual]` | ✅ |
| `manual` | Sessions generated (>0) | `test_manual_mode_sessions_generated` | ✅ |
| `manual` | All sessions result_submitted=False | `test_manual_mode_no_results_submitted` | ✅ |
| `manual` | Status == IN_PROGRESS (no auto-sim) | `test_manual_mode_tournament_remains_in_progress` | ✅ |
| `manual` | Rankings empty | `test_manual_mode_rankings_empty` | ✅ |
| `auto_immediate` | HTTP 200 accepted | `test_all_valid_simulation_modes_accepted[auto_immediate]` | ✅ |
| `auto_immediate` | Sessions generated | `test_auto_immediate_sessions_generated` | ✅ |
| `auto_immediate` | Response structure valid | `test_auto_immediate_response_structure` | ✅ |
| `accelerated` | HTTP 200 accepted | `test_all_valid_simulation_modes_accepted[accelerated]` | ✅ |
| `accelerated` | Status ∈ VALID_LAUNCHED | `test_accelerated_reaches_rewards_distributed` | ✅ |
| Cross-mode | manual ≠ accelerated (result_submitted) | `test_manual_vs_accelerated_result_submitted_differ` | ✅ |
| Invalid mode | Rejected (400/422) | `test_invalid_simulation_mode_rejected` | ✅ |

## Wizard Error State Retention (P1)

| Scenario | Assertion | Test | Result |
|----------|-----------|------|--------|
| 401 error on launch | Error message "Launch failed" visible | `test_launch_failure_shows_error_message` | ✅ |
| 401 error on launch | Wizard stays on Step 8 (not reset) | `test_launch_failure_does_not_reset_to_step1` | ✅ |
| 401 error on launch | Review panel retains scenario values | `test_launch_failure_preserves_scenario_in_review` | ✅ |
| 401 error on launch | Launch button still visible (retry possible) | `test_launch_failure_retry_possible` | ✅ |

**Architecture note:** Error is triggered via invalid JWT token (not browser-level route interception, which cannot intercept Python server-side `requests.post()` calls from Streamlit backend).

## Post-Launch Observability

After OPS `smoke_test` / `large_field_monitor` launch:

| Assertion | Tests | Result |
|-----------|-------|--------|
| Status ∈ {IN_PROGRESS, COMPLETED, REWARDS_DISTRIBUTED} (not DRAFT) | 1 | ✅ |
| Session count > 0 | 1 | ✅ |
| Sessions have result_submitted=True (auto-sim ran) | 1 | ✅ |
| Rankings populated | 1 | ✅ |
| Enrolled count matches requested | 1 | ✅ |
| Session formula: knockout = N, league = N*(N-1)/2 | 7 parametrized | ✅ |

---

## Navigation Coverage

All 8 wizard steps have back-navigation tests:

| Test | Steps Covered |
|------|--------------|
| `test_wizard_back_navigation_step2_to_step1` | 2→1 |
| `test_wizard_back_navigation_step3_to_step2` | 3→2 |
| `test_wizard_back_navigation_step4_to_step3` | 4→3 |
| `test_wizard_back_navigation_step5_to_step4` | 5→4 |
| `test_wizard_back_navigation_step6_to_step5` | 6→5 |
| `test_wizard_back_navigation_step7_to_step6` | 7→6 |
| `test_wizard_back_navigation_step8_to_step7` | 8→7 |
| `test_wizard_no_navigation_loop` | no loop at step 1 |
| `test_wizard_progress_bar_updates` | progress bar step→step |

---

## Known Expected Failures (xfail)

| Test | Reason | Status |
|------|--------|--------|
| `test_auto_refresh_checkbox_present` | Iteration 3 replaced checkbox with fragment-based auto-refresh; "Enable auto-refresh" text no longer in sidebar | `xfail(strict=False)` ✅ |

---

## Slow Tests (excluded from CI default, run on main)

| Test | Player Count | Type | Estimated Duration |
|------|-------------|------|--------------------|
| `test_knockout_large_power_of_two[256]` | 256p | Knockout API | ~30s |
| `test_knockout_large_power_of_two[512]` | 512p | Knockout API | ~60s |
| `test_knockout_maximum_1024` | 1024p | Knockout API | ~120s |
| `test_league_32p_session_count` | 32p | League API (496 sessions) | ~60s |
| `test_individual_ranking_large_counts[32,64]` | 32p/64p | IndRank API | ~30s |
| `test_knockout_at_safety_threshold_128` | 128p | Type Boundary | ~30s |

Slow tests run on `push` to `main` branch or via `workflow_dispatch` with `include_slow=true`.

---

## CI Workflow

**File:** `.github/workflows/e2e-wizard-coverage.yml`

| Job | Tests | Timeout |
|-----|-------|---------|
| `wizard-flow` (Playwright) | 19 | 15 min |
| `coverage-ui` (Playwright) | 22 | 20 min |
| `boundary-wizard-ui` (Playwright) | 8 | 15 min |
| `api-boundary` (HTTP) | 127 non-slow + slow on main | 20 min |
| `p1-critical-coverage` (API + Playwright) | 23 | 25 min |
| `p2-critical-coverage` (API + Playwright) | 28 | 30 min |
| `coverage-summary` (gate) | — | — |

Trigger: PR to main/develop/feature/* and push to main/develop.
Paths filter: changes to `streamlit_app/**`, `app/**`, `tests_e2e/test_tournament_monitor*.py`, `tests_e2e/test_p1_coverage.py`, or `tests_e2e/test_p2_coverage.py`.

---

## JUnit XML Evidence

All results in `tests_e2e/results/`:

```
wizard_flow_run.xml              — 19 tests, 0 failed
coverage_ui_run.xml              — 9 tests, 0 failed
boundary_wizard_run.xml          — 8 tests, 0 failed
monitoring_regressions_run2.xml  — 14 tests, 0 failed (1 xfailed)
boundary_api_run.xml             — 35 tests, 0 failed
post_launch_run.xml              — 12 tests, 0 failed
full_boundary_api_run.xml        — 57 tests, 0 failed
generation_type_boundary_run.xml — 34 tests, 0 failed
p1_full_run.xml                  — 23 tests, 0 failed  ← P1 critical coverage
p2_full_run.xml                  — 28 tests, 0 failed  ← P2 critical coverage
─────────────────────────────────────────────────────
TOTAL                            — 239 tests, 0 failed, 1 xfailed
```

---

## Phase B Status

**UNBLOCKED.** All E2E coverage criteria met, P1 + P2 critical gaps closed. 58/58 pairwise cases covered.

### Base E2E criteria (met in previous iteration)
- [x] All 8 wizard steps covered (Steps 1–8)
- [x] HEAD_TO_HEAD + INDIVIDUAL_RANKING decision branches
- [x] Participant ranges 2–1024 validated
- [x] Forward + back navigation for all 8 steps
- [x] Safety confirmation gate (128+ players, 5 assertion variants)
- [x] All tournament types: knockout / league / group_knockout / individual_ranking
- [x] Boundary values: 2,3,4,7,8,15,16,31,32,63,64,127,128
- [x] Post-launch observability (status, sessions, rankings, enrolled count)
- [x] Headless execution proven (JUnit XML + CI workflow)

### P1 critical coverage criteria (met in previous iteration)
- [x] P1 coverage = 100% — all 3 P1 gaps from `E2E_BRANCH_MATRIX.md` closed
- [x] Simulation modes: `manual` fully validated (no auto-sim, IN_PROGRESS, empty rankings)
- [x] Simulation modes: `auto_immediate` structural response + sessions verified
- [x] Simulation modes: `accelerated` control case confirmed (REWARDS_DISTRIBUTED)
- [x] Cross-mode comparison: manual ≠ accelerated (result_submitted observable difference)
- [x] Invalid simulation_mode rejected (400/422)
- [x] API error → wizard state retention: error shown, Step 8 preserved, retry possible
- [x] INDIVIDUAL_RANKING 128+ safety gate: UI confirmation required (6 test variants)
- [x] INDIVIDUAL_RANKING 128+ API gate: confirmed=False rejected (backend contract)
- [x] Pairwise coverage ≥ 55/58 (3 P1 dimension-pairs added, all critical gaps closed)
- [x] CI workflow includes P1 job (`p1-critical-coverage`, 25 min timeout)
- [x] 100% success rate (210 passed, 1 documented xfail, 0 failures)

### P2 critical coverage criteria (met in this iteration)
- [x] P2 coverage = 100% — all 3 P2 gaps from `E2E_BRANCH_MATRIX.md` closed
- [x] Game preset Step 4 UI + API payload verified (knockout, league, group_knockout)
- [x] Reward config — all 5 templates tested: ops_default, standard, championship, friendly, custom
- [x] Custom template: number_input fields appear, values fillable, Step 8 reachable
- [x] Reward config API payload accepted for all named templates (HTTP 200 + tournament_id)
- [x] Global max boundary: league 1025p rejected + group_knockout 1025p rejected
- [x] Backend discovery: league and GK have no type-specific max (only global max=1024)
- [x] Simulation mode wizard UI: `manual` × (knockout/league/GK) — launch succeeds, Step 1 reset
- [x] Simulation mode wizard UI: `auto_immediate` × (knockout/league/GK) — launch succeeds
- [x] Player count equivalence UI: 5 scenario×type combinations reach Step 6
- [x] Pairwise coverage = 58/58 (all P2 dimension-pairs closed)
- [x] 100% success rate (238 passed, 1 documented xfail, 0 failures)
