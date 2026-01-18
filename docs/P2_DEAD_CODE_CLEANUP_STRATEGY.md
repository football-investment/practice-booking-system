# P2 Dead Code Cleanup - Strategy
## 2026-01-18

## 📊 Scope Analysis

**Total Issues**: 1,591
**Files Affected**: 266
**Confidence**: ALL <70% (⚠️ HIGH FALSE POSITIVE RISK)

### Issues by Type

| Type | Count | % of Total | Risk Level |
|------|-------|------------|------------|
| **Unused Variables** | 765 | 48.1% | LOW-MEDIUM |
| **Unused Functions** | 384 | 24.1% | MEDIUM |
| **Unused Classes** | 249 | 15.7% | HIGH |
| **Unused Methods** | 80 | 5.0% | MEDIUM |
| **Unused Attributes** | 79 | 5.0% | HIGH |
| **Unused Imports** | 20 | 1.3% | **LOW** ✅ |
| **Unused Properties** | 12 | 0.8% | MEDIUM |
| **Unreachable Code** | 1 | 0.1% | LOW |
| **Other** | 1 | 0.1% | UNKNOWN |

### Issues by Directory

| Directory | Count | Notes |
|-----------|-------|-------|
| **app/schemas** | 398 | ⚠️ Pydantic models - likely FALSE POSITIVES |
| **app/models** | 187 | ⚠️ SQLAlchemy models - likely FALSE POSITIVES |
| **app/api/api_v1/endpoints** | 135 | Mixed - need review |
| **app/api/api_v1/endpoints/gancuju** | 107 | Specialization endpoints |
| **app/api/api_v1/endpoints/internship** | 104 | Specialization endpoints |
| **app/api/api_v1/endpoints/coach** | 98 | Specialization endpoints |
| **app/services** | 66 | Service layer - need careful review |
| **scripts** | 31 | Utility scripts - safe to clean |
| **app/tests** | 30 | Test fixtures - likely FALSE POSITIVES |

### Top 10 Files with Most Issues

| File | Issues | Risk Assessment |
|------|--------|-----------------|
| app/schemas/motivation.py | 61 | ⚠️ Pydantic - likely false positives |
| app/schemas/project.py | 48 | ⚠️ Pydantic - likely false positives |
| app/schemas/quiz.py | 43 | ⚠️ Pydantic - likely false positives |
| app/api/api_v1/endpoints/gancuju/licenses.py | 37 | 🔍 Need review |
| app/api/api_v1/endpoints/internship/licenses.py | 36 | 🔍 Need review |
| app/schemas/instructor_management.py | 36 | ⚠️ Pydantic - likely false positives |
| app/api/api_v1/endpoints/gancuju/activities.py | 35 | 🔍 Need review |
| app/api/api_v1/endpoints/gancuju/belts.py | 35 | 🔍 Need review |
| app/api/api_v1/endpoints/coach/licenses.py | 34 | 🔍 Need review |
| app/api/api_v1/endpoints/internship/credits.py | 34 | 🔍 Need review |

---

## 🎯 Cleanup Strategy

### ⚠️ Critical Understanding

**ALL issues have <70% confidence** - this means:
- Vulture doesn't understand FastAPI decorators
- Vulture doesn't understand Pydantic field usage
- Vulture doesn't understand SQLAlchemy ORM fields
- **Manual review is MANDATORY**

### Phase-Based Approach

#### **Phase 1: SAFE - Unused Imports (20 issues)** ✅

**Risk**: LOW
**Tool**: `autoflake --remove-all-unused-imports`
**Validation**: pytest after cleanup

**Action**:
1. Run autoflake on all Python files
2. Review diff manually
3. Run full test suite
4. Commit if green

**Expected Impact**: Minimal (20 imports removed)

---

#### **Phase 2: REVIEW - Unused Variables in Tests (30 issues)**

**Risk**: LOW-MEDIUM
**Files**: test_*.py files with unused fixtures

**Examples from report**:
- `test_e2e_age_validation.py`: 7x `unused variable 'setup_specializations'`
- `test_onboarding_api.py`: 5x `unused variable 'setup_test_db'`
- `test_specialization_integration.py`: 6x `unused variable 'setup_specializations'`

**Action**:
1. These are pytest fixtures - they have side effects even if "unused"
2. **DO NOT REMOVE** - these are FALSE POSITIVES
3. Add `# noqa: F841` comments if linter complains

**Expected Impact**: 0 deletions (all false positives)

---

#### **Phase 3: SKIP - Schemas (398 issues)** ⚠️

**Risk**: VERY HIGH
**Reason**: Pydantic models use fields for validation/serialization

**Why Vulture Flags These**:
```python
class UserCreate(BaseModel):
    email: str  # Vulture thinks this is "unused"
    name: str   # But Pydantic uses it for validation
```

**Action**: **SKIP ENTIRELY**
- These are NOT dead code
- Pydantic uses metaclass magic
- False positive rate: ~99%

**Expected Impact**: 0 deletions

---

#### **Phase 4: SKIP - Models (187 issues)** ⚠️

**Risk**: VERY HIGH
**Reason**: SQLAlchemy models use fields for ORM

**Why Vulture Flags These**:
```python
class User(Base):
    id = Column(Integer, primary_key=True)  # Vulture: "unused"
    email = Column(String)                  # But SQLAlchemy uses it
```

**Action**: **SKIP ENTIRELY**
- These are NOT dead code
- SQLAlchemy uses declarative metaclass
- False positive rate: ~99%

**Expected Impact**: 0 deletions

---

#### **Phase 5: REVIEW - Endpoint Variables (135 issues)**

**Risk**: MEDIUM
**Files**: app/api/api_v1/endpoints/**

**Known Issues from detailed report**:
- `locations.py`: 5x `unused variable 'current_admin'`
- `semester_generator.py`: 2x `unused variable 'current_admin'`

**These are real issues**:
```python
@router.post("/")
def create_location(
    current_admin: User = Depends(get_current_admin_user)  # ← Used for auth, not in function body
):
    # current_admin not referenced in body
    # BUT: Depends() uses it for authentication!
```

**Action**:
1. **KEEP these** - they enforce authentication
2. Rename to `_current_admin` to signal intent
3. Or add `# noqa: ARG001` (unused argument)

**Expected Impact**: 0 deletions, ~10 renames

---

#### **Phase 6: MANUAL REVIEW - Service Layer (66 issues)**

**Risk**: HIGH
**Files**: app/services/**

**Action**:
1. Review each file manually
2. Check if functions/classes are imported elsewhere
3. Use `git grep` to verify usage
4. Delete ONLY if:
   - Not imported anywhere
   - Not part of public API
   - No tests reference it

**Expected Impact**: ~20 deletions (conservative)

---

#### **Phase 7: SAFE - Scripts (31 issues)**

**Risk**: LOW
**Files**: scripts/**

**Action**:
1. These are standalone utilities
2. Safe to remove unused code
3. Check if script is still referenced in docs/README

**Expected Impact**: ~15 deletions

---

#### **Phase 8: SKIP - Functions/Classes (384 + 249 + 80 = 713 issues)**

**Risk**: VERY HIGH
**Reason**: May be part of public API, used in external code, or flagged incorrectly

**Action**:
1. **DEFER** to later phase
2. Need API usage analysis first
3. Need external caller analysis
4. Too risky for initial cleanup

**Expected Impact**: 0 deletions (deferred)

---

## 🎯 Realistic P2 Scope

### What We WILL Do

| Phase | Issues | Expected Deletions | Risk |
|-------|--------|--------------------|------|
| Phase 1: Unused Imports | 20 | 15-20 | LOW ✅ |
| Phase 5: Endpoint Renames | 10 | 0 (rename only) | LOW ✅ |
| Phase 7: Scripts | 31 | 10-15 | LOW ✅ |
| **TOTAL** | **61** | **25-35** | **LOW** |

### What We Will SKIP (False Positives)

| Category | Issues | Reason |
|----------|--------|--------|
| Schemas | 398 | Pydantic metaclass magic |
| Models | 187 | SQLAlchemy ORM magic |
| Test Fixtures | 30 | Pytest side effects |
| Functions/Classes | 713 | Need API analysis |
| **TOTAL SKIPPED** | **1,328** | **False positives or deferred** |

### What We Will DEFER (Need More Analysis)

| Category | Issues | Reason |
|----------|--------|--------|
| Service Functions | 66 | Need import analysis |
| Endpoint Methods | 125 | Need careful review |
| **TOTAL DEFERRED** | **191** | **P3 task** |

---

## 📋 Execution Plan

### Step 1: Unused Imports (autoflake)

```bash
# Backup
git add -A && git commit -m "Pre-P2 backup"

# Run autoflake
autoflake --remove-all-unused-imports --in-place --recursive app/

# Review diff
git diff

# Test
pytest app/tests/test_action_determiner.py app/tests/test_audit_*.py -v

# Commit if green
git add -A && git commit -m "P2: Remove unused imports (Phase 1)"
```

### Step 2: Rename Auth Variables

Manually rename `current_admin` → `_current_admin` where unused but needed for auth

### Step 3: Clean Scripts

Review scripts/ directory and remove dead code from standalone utilities

### Step 4: Document Results

Create P2_DEAD_CODE_CLEANUP_REPORT.md with:
- What was removed
- What was skipped (false positives)
- What was deferred (P3)
- Final metrics

---

## 🎯 Success Criteria

### Must Have

- ✅ Zero test failures after cleanup
- ✅ No production code breakage
- ✅ Git history clean (atomic commits per phase)
- ✅ Documentation complete

### Nice to Have

- ✅ 20-35 lines of dead code removed
- ✅ All unused imports removed
- ✅ Scripts cleaned up

### Out of Scope (P3)

- ❌ Remove "unused" Pydantic fields (false positives)
- ❌ Remove "unused" SQLAlchemy fields (false positives)
- ❌ Remove functions without API analysis
- ❌ Remove classes without dependency graph

---

## ⚠️ Risk Mitigation

### Before Each Phase

1. **Backup**: `git add -A && git commit`
2. **Review**: Manual review of changes
3. **Test**: Run core test suite
4. **Revert**: `git reset --hard HEAD~1` if issues

### Red Flags to STOP

- Any test failure
- Any import error
- Any runtime error in dev server
- >100 lines changed in one commit

---

## 📊 Expected Outcome

**Conservative Estimate**:
- **Removed**: 25-35 lines of actual dead code
- **Renamed**: 10-15 auth variables
- **Skipped**: 1,328 false positives
- **Deferred**: 191 to P3

**Impact**:
- Codebase size: -0.1% (minimal)
- Maintainability: +small improvement
- False positive rate: ~83% (1,328/1,591)

**Conclusion**:
P2 cleanup is **low-value, high-risk** due to Vulture's poor understanding of:
- FastAPI decorators
- Pydantic models
- SQLAlchemy ORM
- Pytest fixtures

**Recommendation**: Focus on **Phase 1 (imports)** only, defer rest to P3 with better tooling (mypy, ruff).

---

**Generated**: 2026-01-18
**Status**: STRATEGY READY
**Next**: Execute Phase 1 (unused imports)
