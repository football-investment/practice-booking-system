# P4 - Code Complexity & Quality Audit Report

**Dátum:** 2026-01-18
**Audit Típus:** Cyclomatic Complexity + Code Quality (Linting)
**Eszközök:** Radon 6.0.1, Ruff (latest)
**Státusz:** ⚠️ ACTION REQUIRED - Refactoring + Linter Fixes Needed

---

## 📊 Executive Summary

**Scan Scope:** `app/` directory (production code only)

### Complexity Analysis (Radon)
- **Total functions analyzed:** 500+
- **Functions with complexity ≥ C (11+):** 48
- **Functions with complexity ≥ D (21+):** 3
- **Functions with complexity ≥ E (31+):** 2
- **Average complexity:** A-B (healthy)
- **Highest complexity:** E (34) - `AuditMiddleware._determine_action`

### Code Quality Analysis (Ruff)
- **Total issues found:** 1,197
- **Critical issues (syntax/logic):** 201 invalid syntax errors
- **Code style issues:** 423 unused imports, 320 undefined names
- **Auto-fixable:** 466 issues (39%)
- **Bare except blocks:** 13 (dangerous)
- **True/False comparisons:** 136 (style issue)

### Type Checking (MyPy)
- **Status:** ❌ NO CONFIGURATION FOUND
- **Recommendation:** Add mypy.ini or [tool.mypy] in pyproject.toml

---

## 🔴 TOP 20 Most Complex Functions (Refactor Targets)

### ⚠️ CRITICAL (E: 31-40) - IMMEDIATE REFACTORING NEEDED

| Rank | Function | File | Complexity | Priority |
|------|----------|------|------------|----------|
| 1 | `list_sessions` | app/api/api_v1/endpoints/sessions.py:28 | **E (39)** | P1 |
| 2 | `AuditMiddleware._determine_action` | app/middleware/audit_middleware.py:161 | **E (34)** | P1 |

**Impact:** These functions are EXTREMELY complex and hard to maintain/test.

**Recommended Action:**
- Break into smaller functions (max 10-15 complexity)
- Extract logic into service layer
- Add comprehensive unit tests

---

### ⚠️ HIGH (D: 21-30) - REFACTORING STRONGLY RECOMMENDED

| Rank | Function | File | Complexity | Priority |
|------|----------|------|------------|----------|
| 3 | `get_lfa_player_profile` | app/api/api_v1/endpoints/lfa_player/dashboard.py:20 | **D (24)** | P1 |
| 4 | `TestCompleteWorkflow.test_admin_complete_workflow` | app/tests/test_e2e_age_validation.py:9 | **D (24)** | P2 (test) |
| 5 | `EnrollmentConflictService.check_session_time_conflict` | app/services/enrollment_conflict_service.py:42 | **D (22)** | P1 |

---

### 🟡 MEDIUM (C: 11-20) - REFACTORING RECOMMENDED

| Rank | Function | File | Complexity | Lines | Priority |
|------|----------|------|------------|-------|----------|
| 6 | `list_available_tournaments` | app/api/api_v1/endpoints/tournaments/enrollment.py:30 | C (20) | ~150 | P2 |
| 7 | `instructor_student_skills_v2_submit` | app/api/web_routes/instructor.py:142 | C (19) | ~120 | P2 |
| 8 | `apply_coupon` | app/api/api_v1/endpoints/coupons.py:494 | C (16) | ~100 | P2 |
| 9 | `get_system_stats` | app/api/web_routes/admin.py:161 | C (16) | ~100 | P2 |
| 10 | `export_sessions_csv` | app/api/web_routes/admin.py:52 | C (16) | ~80 | P3 |
| 11 | `submit_tournament_rankings` | app/api/api_v1/endpoints/tournaments/ranking.py:85 | C (16) | ~90 | P2 |
| 12 | `get_lesson_progress` | app/api/api_v1/endpoints/curriculum/lessons.py:170 | C (15) | ~80 | P3 |
| 13 | `get_project_progress` | app/api/api_v1/endpoints/projects/student.py:271 | C (15) | ~80 | P3 |
| 14 | `create_assignment` | app/api/api_v1/endpoints/instructor_assignments/assignments.py:37 | C (15) | ~90 | P2 |
| 15 | `instructor_promote_belt` | app/api/web_routes/instructor.py:101 | C (15) | ~85 | P3 |
| 16 | `distribute_tournament_rewards` | app/api/api_v1/endpoints/tournaments/rewards.py:201 | C (14) | ~85 | P2 |
| 17 | `get_instructor_profile` | app/api/api_v1/endpoints/instructor/dashboard.py:265 | C (14) | ~90 | P3 |
| 18 | `submit_motivation_assessment` | app/api/api_v1/endpoints/onboarding.py:23 | C (14) | ~75 | P3 |
| 19 | `register_with_invitation` | app/api/api_v1/endpoints/auth.py:256 | C (14) | ~80 | P3 |
| 20 | `get_project_enrollment_status` | app/api/api_v1/endpoints/projects/enrollment/status.py:141 | C (14) | ~70 | P3 |

**Additional C-complexity functions:** 28 more (ranks 21-48)

---

## 🐛 Code Quality Issues (Ruff Linter)

### 🔴 CRITICAL - Must Fix (P1)

#### 1. Invalid Syntax Errors (201 occurrences)

**Files with syntax errors:**
```
app/api/api_v1/endpoints/adaptive_learning.py - 4 errors
app/api/api_v1/endpoints/attendance.py - 7 errors
app/api/api_v1/endpoints/audit.py - 4 errors
app/api/api_v1/endpoints/gamification.py - 2 errors
app/api/api_v1/endpoints/instructor_assignments/*.py - 30+ errors
```

**Root Cause:** Likely incomplete refactoring or merge conflicts

**Action:** Fix syntax errors IMMEDIATELY - these files won't run correctly

---

#### 2. Bare Except Blocks (13 occurrences) - DANGEROUS

**Locations:**
```python
app/api/api_v1/endpoints/analytics.py:63
app/api/api_v1/endpoints/curriculum/exercises.py:38, 85
app/api/api_v1/endpoints/curriculum/lessons.py:68, 146
app/api/api_v1/endpoints/coach/licenses.py:288
app/api/api_v1/endpoints/gancuju/licenses.py:266
... (7 more)
```

**Problem:**
```python
try:
    # some code
except:  # ❌ BAD - catches ALL exceptions including SystemExit, KeyboardInterrupt
    pass
```

**Fix:**
```python
try:
    # some code
except Exception as e:  # ✅ GOOD - catches only application exceptions
    logger.error(f"Error: {e}")
```

**Impact:** Can hide critical bugs and make debugging impossible

**Priority:** P1 - Fix ASAP

---

### 🟡 HIGH PRIORITY - Should Fix (P2)

#### 3. True/False Comparisons (136 occurrences)

**Pattern:**
```python
# ❌ BAD
if user.is_active == True:
if semester.is_active == False:

# ✅ GOOD
if user.is_active:
if not semester.is_active:
```

**Impact:** Code style - not a bug, but verbose and unpythonic

**Auto-fix:** `ruff check --fix --select E712`

**Priority:** P2 - Fix in batches

---

#### 4. Unused Imports (423 occurrences)

**Status:** ✅ MOSTLY CLEANED (P1-P3 cleanup removed many)

**Remaining:** Likely in files not yet audited

**Action:** Run `ruff check --fix --select F401` to auto-remove

**Priority:** P2 - Batch cleanup

---

#### 5. Undefined Names (320 occurrences)

**Root Cause:** Missing imports, typos, or refactoring artifacts

**Sample Files:**
```
app/api/api_v1/endpoints/*.py - Various missing imports
```

**Action:** Review each case - may indicate real bugs

**Priority:** P2 - Manual review needed

---

### 🟢 LOW PRIORITY - Nice to Fix (P3)

#### 6. F-strings Without Placeholders (38 occurrences)

```python
# ❌ Inefficient
message = f"Hello world"

# ✅ Better
message = "Hello world"
```

**Auto-fix:** `ruff check --fix --select F541`

**Priority:** P3 - Performance optimization

---

#### 7. Code Style Issues (E501, W291, W293)

- **Line too long (E501):** ~200 occurrences
- **Trailing whitespace (W291):** ~50 occurrences
- **Blank line whitespace (W293):** ~30 occurrences

**Auto-fix:** `ruff check --fix --select E501,W`

**Priority:** P3 - Code formatting

---

## 🎯 Refactoring Targets - Priority Matrix

### Priority 1 (URGENT) - Within 1 Sprint

| Function | Reason | Estimated Effort |
|----------|--------|-----------------|
| `list_sessions` (E39) | Extremely complex, API critical path | 4-6 hours |
| `AuditMiddleware._determine_action` (E34) | Middleware - affects all requests | 3-4 hours |
| `get_lfa_player_profile` (D24) | Dashboard endpoint - user-facing | 2-3 hours |
| `EnrollmentConflictService.check_session_time_conflict` (D22) | Business logic critical | 2-3 hours |

**Total Effort:** ~2-3 days

**Strategy:**
1. Extract helper functions for each logical block
2. Move business logic to service layer
3. Add unit tests for extracted functions
4. Refactor main function to orchestrate calls

---

### Priority 2 (HIGH) - Within 2-3 Sprints

**Targets:** Functions with complexity C (16-20)
- `list_available_tournaments` (C20)
- `instructor_student_skills_v2_submit` (C19)
- `apply_coupon` (C16)
- `submit_tournament_rankings` (C16)
- `get_system_stats` (C16)

**Total Functions:** 10
**Estimated Effort:** 1-2 days per function = 2-3 weeks total

---

### Priority 3 (MEDIUM) - Ongoing Improvement

**Targets:** Functions with complexity C (11-15)
- All remaining C-complexity functions (28 total)
- Focus on frequently modified files first
- Refactor during feature work (boy scout rule)

---

## 🔧 Type Checking (MyPy)

**Status:** ❌ NO MYPY CONFIGURATION FOUND

**Missing:**
- No `mypy.ini` file
- No `[tool.mypy]` section in `pyproject.toml`
- No type checking in CI/CD

**Recommendation:** Add MyPy configuration

**Suggested Config:**
```ini
# mypy.ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False  # Start lenient
check_untyped_defs = True
ignore_missing_imports = True

# Gradually enable stricter checks
[mypy-app.api.*]
disallow_untyped_defs = True

[mypy-app.services.*]
disallow_untyped_defs = True
```

**Benefits:**
- Catch type errors before runtime
- Better IDE autocomplete
- Self-documenting code
- Easier refactoring

**Priority:** P2 - Add in next sprint

---

## 📋 Action Plan

### Phase 1: Fix Critical Issues (Week 1)

**Tasks:**
1. ✅ Fix 201 invalid syntax errors
   - Review files in `app/api/api_v1/endpoints/`
   - Fix merge conflicts / incomplete refactorings
   - Test affected endpoints

2. ✅ Fix 13 bare except blocks
   - Replace with `except Exception as e:`
   - Add proper logging
   - Consider specific exception types

3. ✅ Refactor 2 E-complexity functions
   - `list_sessions` (E39)
   - `AuditMiddleware._determine_action` (E34)

**Deliverables:**
- All syntax errors resolved
- No bare except blocks
- 2 critical functions refactored
- Unit tests added

---

### Phase 2: High Priority Cleanup (Weeks 2-3)

**Tasks:**
1. Auto-fix code style issues
   ```bash
   ruff check app/ --fix --select E712,F541,E501,W
   ```

2. Refactor 3 D-complexity functions
   - `get_lfa_player_profile` (D24)
   - `EnrollmentConflictService.check_session_time_conflict` (D22)
   - `TestCompleteWorkflow.test_admin_complete_workflow` (D24)

3. Clean remaining unused imports
   ```bash
   ruff check app/ --fix --select F401
   ```

4. Add MyPy configuration
   - Create `mypy.ini`
   - Add to pre-commit hooks
   - Fix initial type errors

**Deliverables:**
- Code style clean
- 3 more complex functions refactored
- MyPy configured and passing

---

### Phase 3: Ongoing Improvement (Continuous)

**Tasks:**
1. Refactor C-complexity functions during feature work
2. Add type hints to new code
3. Increase mypy strictness gradually
4. Monitor complexity in code reviews

**Goal:** Keep average complexity at B or lower

---

## 📊 Metrics & Tracking

### Before Cleanup

| Metric | Value |
|--------|-------|
| Functions with E complexity | 2 |
| Functions with D complexity | 3 |
| Functions with C complexity | 43 |
| Ruff errors | 1,197 |
| Critical issues (syntax + bare except) | 214 |
| MyPy coverage | 0% |

### Target After Cleanup

| Metric | Target |
|--------|--------|
| Functions with E complexity | 0 |
| Functions with D complexity | 0 |
| Functions with C complexity | <20 |
| Ruff errors | <100 |
| Critical issues | 0 |
| MyPy coverage | 30%+ |

---

## 🛠️ Tools & Commands

### Radon Commands
```bash
# Scan for complexity
radon cc app/ -s -a -n C  # Show C+ complexity

# Generate report
radon cc app/ -s -a --total-average > complexity_report.txt
```

### Ruff Commands
```bash
# Check all issues
ruff check app/

# Auto-fix safe issues
ruff check app/ --fix

# Auto-fix unsafe issues (review carefully)
ruff check app/ --fix --unsafe-fixes

# Check specific rules
ruff check app/ --select E712,E722,F401

# Statistics
ruff check app/ --statistics
```

### MyPy Commands (after setup)
```bash
# Type check all files
mypy app/

# Type check specific module
mypy app/api/

# Generate report
mypy app/ --html-report mypy-report/
```

---

## 📎 Recommendations

### Short Term (1 month)
1. ✅ Fix all syntax errors (blocking)
2. ✅ Fix all bare except blocks (security/stability)
3. ✅ Refactor 5 highest complexity functions (E + D)
4. ✅ Add MyPy configuration
5. ✅ Auto-fix code style issues with ruff

### Medium Term (3 months)
1. Refactor remaining C-complexity functions
2. Add type hints to 30% of codebase
3. Add complexity checks to CI/CD
4. Set up pre-commit hooks (ruff + mypy)

### Long Term (6 months)
1. Maintain average complexity at B
2. 50%+ type hint coverage
3. Zero critical linter issues
4. Automated code quality gates in CI/CD

---

**Készítette:** Claude Code (Sonnet 4.5)
**Utolsó frissítés:** 2026-01-18
**Következő lépés:** P4.1 - Fix Critical Syntax Errors & Bare Excepts
