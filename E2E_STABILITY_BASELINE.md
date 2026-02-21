# E2E Test Stability Baseline

> **Purpose:** Track stable feature blocks and prevent regression.
> **Last updated:** 2026-02-21
> **Methodology:** Block-based stabilization (not firefighting)

---

## ✅ Stable Feature Blocks

### 1. Game Preset Admin (7/7 stable)

**Commit:** `2396aba` — fix(e2e): per-test unique preset names + backend behavior workarounds

**Tests:**
- `test_gp01_create_preset_domain_consistency` ✅
- `test_gpv1_no_skills_blocked` ✅
- `test_gpv2_empty_name_blocked` ✅
- `test_gp02_edit_name_persists` ✅
- `test_gp03_deactivate_preset` ✅
- `test_gp04_activate_preset` ✅
- `test_gp05_delete_with_confirmation` ✅

**Key fixes:**
- Per-test unique names (`test_preset_names` fixture) → test data pollution eliminated
- Soft-delete business logic identified (DELETE → `is_active=False`)
- Backend bug workaround: POST ignores `is_active=False` (PATCH works)
- Deterministic assertions (form state change, not transient toast messages)

**Backend issues documented:**
- POST `/api/v1/game-presets/` ignores `is_active=False` (workaround: PATCH after create)
- DELETE `/api/v1/game-presets/{id}` is soft-delete (business logic, not bug)

**Stability verified:**
- Sequential order: 7/7 pass
- Reverse order: 7/7 pass
- Test isolation: confirmed (unique names per test)

---

### 2. Instructor Dashboard (10/10 stable)

**Commit:** `23976ec` — fix(e2e): deterministic instructor auth via fixture authority

**Tests:**
- `test_t1_today_upcoming_tab` ✅
- `test_t2_my_jobs_tab` ✅
- `test_t3_tournament_applications_tab` ✅
- `test_t4_my_students_tab` ✅
- `test_t5_checkin_groups_tab` ✅
- `test_t6_inbox_tab` ✅
- `test_t7_my_profile_tab` ✅
- `test_s1_sidebar_tournament_manager_button` ✅
- `test_s2_sidebar_refresh_button` ✅
- `test_s3_sidebar_logout_button` ✅

**Key fix:**
- Fixture authority: existing users now UPDATED (password_hash, role, flags)
- No seed/manual setup dependency
- No environment variable dependency
- E2E tests own their preconditions

**Complexity:**
- Low (navigation smoke tests)
- No data mutation
- No backend interaction beyond auth
- UI state checks only

**Stability verified:**
- Single run: 10/10 pass (33.64s)
- No flaky behavior
- No test isolation issues

---

### 3. Tournament Manager Sidebar Nav (5/5 stable)

**Commit:** `8225c63` — fix(e2e): Remove legacy Tournament Monitor sidebar button

**Tests:**
- `test_a1_admin_sidebar_has_tournament_manager_button` ✅
- `test_a2_admin_sidebar_tournament_manager_navigates` ✅
- `test_i1_instructor_sidebar_has_tournament_manager_button` ✅
- `test_i2_instructor_sidebar_tournament_manager_navigates` ✅
- `test_l1_admin_sidebar_no_legacy_monitor_button` ✅

**Key fix:**
- Removed broken `st.switch_page("pages/Tournament_Monitor.py")` from admin sidebar
- Legacy button pointed to archived/deprecated page
- Clean UI code (no dead imports, no unreachable references)

**Complexity:**
- Low (navigation smoke tests)
- UI presence checks only
- No data mutation
- No backend interaction

**Stability verified:**
- Sequential order: 5/5 pass (28.49s)
- Reverse order: 5/5 pass (26.40s)
- Test isolation: confirmed (no state dependencies)

---

## 🔬 E2E Test Principles (Established)

1. **Fixture = Authority**
   - Tests don't rely on seed data
   - Tests don't rely on manual setup
   - Fixture enforces deterministic state

2. **Test Isolation**
   - Per-test unique data (e.g., `test_preset_names` fixture)
   - Function-scoped fixtures (no state leakage)
   - Cleanup before AND after each test

3. **Deterministic Assertions**
   - Avoid transient UI elements (`st.success()` toast disappears on `st.rerun()`)
   - Use state changes (form closed, button gone, etc.)
   - API assertions for persistence verification

4. **Backend Behavior Validation**
   - Investigate business logic vs bugs
   - Document intentional behavior (soft-delete)
   - Workaround backend bugs when needed (document in test)

5. **Block-based Stabilization**
   - Baseline → Fix → Verify → Commit → Next block
   - No firefighting, no batch fixes
   - Each block fully stable before moving on

---

## 📊 Overall Progress

| Feature Block | Tests | Status | Commit |
|---|---|---|---|
| **Game Preset Admin** | 7 smoke | ✅ 7/7 stable | `2396aba` |
| **Instructor Dashboard** | 10 smoke | ✅ 10/10 stable | `23976ec` |
| **Tournament Manager Sidebar** | 5 smoke | ✅ 5/5 stable | `8225c63` |
| **TOTAL** | **22** | **22/22 (100%)** | — |

---

## 🎯 Next Block Candidates

- Tournament Monitor (check-in, seeding, progression)
- Student Dashboard
- Other admin tabs (users, locations, etc.)

**Process for next block:**
1. Run smoke tests in isolation
2. Create baseline report (pass/fail/error breakdown)
3. Categorize: auth / UI / business logic
4. Fix systematically (one blocker at a time)
5. Verify stability (sequential + reverse order)
6. Commit + update this baseline doc
7. Move to next block

**No firefighting. Controlled, block-based stabilization.**
