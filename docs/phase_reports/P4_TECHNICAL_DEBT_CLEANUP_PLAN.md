# P4 Technical Debt Cleanup Sprint
## Scope: Deprecation Warnings & Code Quality

> **Status**: PLANNED (Not Started)
> **Baseline**: baseline-2026-02-23
> **Trigger**: After new features pass 85% pipeline gate
> **Priority**: P4 (Maintenance, non-blocking)

---

## 📊 Current State (Baseline)

**Test Results**: 228 passed, 37 skipped (86.0% pass rate)
**Warnings**: 436 total deprecation warnings
**Blocking Issues**: 0
**Flaky Tests**: 0

---

## 🎯 Sprint Objectives

### Objective 1: datetime.utcnow() → timezone-aware refactor
**Impact**: ~180 warnings → 0
**Effort**: 2-3 hours (global search & replace + audit)

**Files Affected**:
```bash
# Search pattern
grep -r "datetime.utcnow()" app/ --include="*.py"

# Replace pattern
datetime.utcnow() → datetime.now(timezone.utc)
```

**Critical Files** (manual audit required):
1. `app/api/api_v1/endpoints/tournaments/enroll.py:235,239,240,269`
2. `app/services/tournament/session_generation/session_generator.py:352`
3. `app/services/credit_service.py:92`

**Verification**:
```bash
# After refactor
pytest app/tests/ -v | grep "datetime.utcnow"
# Expected: 0 warnings
```

---

### Objective 2: Pydantic V1 → V2 migration
**Impact**: ~250 warnings → 0
**Effort**: 4-6 hours (schema refactoring + validation)

**Migration Pattern**:
```python
# Before (V1):
@validator('field_name')
def validate_field(cls, v):
    return v

# After (V2):
@field_validator('field_name')
@classmethod
def validate_field(cls, v):
    return v
```

**Files Affected**:
1. `app/schemas/message.py` (6 validators)
2. `app/schemas/instructor_management.py` (5 validators)
3. `app/schemas/motivation.py` (2 validators)
4. `app/schemas/instructor_availability.py` (2 validators)
5. `app/api/api_v1/endpoints/tournaments/generator.py` (5 validators)

**Verification**:
```bash
# After migration
pytest app/tests/ -v | grep "PydanticDeprecated"
# Expected: 0 warnings
```

---

### Objective 3: pytest config warnings cleanup
**Impact**: ~6 warnings → 0
**Effort**: 30 minutes

**Issue**: `Unknown config option: sensitive_url`

**Fix**:
```ini
# pytest.ini - remove or document unknown config options
[tool:pytest]
# Remove: sensitive_url (unknown option)
```

**Verification**:
```bash
pytest app/tests/ -v | grep "PytestConfigWarning"
# Expected: 0 warnings
```

---

## ✅ Acceptance Criteria

**Sprint Success**:
- [ ] 0 datetime.utcnow() warnings
- [ ] 0 Pydantic V1 deprecation warnings
- [ ] 0 pytest config warnings
- [ ] Test pass rate ≥ 86.0% (no regression)
- [ ] 0 new test failures introduced
- [ ] CI pipeline green

**Deliverables**:
1. Updated codebase (all warnings resolved)
2. Migration verification report
3. Updated documentation (code style guide)

---

## 🚫 Out of Scope (This Sprint)

**Not Included**:
- New feature development
- Test coverage expansion
- Performance optimization
- UI/UX improvements

**Reason**: P4 sprint focuses ONLY on technical debt cleanup

---

## 📋 Execution Checklist

### Pre-Sprint
- [ ] Create feature branch: `p4/deprecation-warnings-cleanup`
- [ ] Backup baseline: `git tag baseline-2026-02-23`
- [ ] Document current warning count: 436

### Sprint Execution
- [ ] Phase 1: datetime.utcnow() refactor (2-3h)
  - [ ] Global search & replace
  - [ ] Manual audit of critical files
  - [ ] Run tests: verify 0 datetime warnings

- [ ] Phase 2: Pydantic V1 → V2 migration (4-6h)
  - [ ] Migrate schemas/message.py
  - [ ] Migrate schemas/instructor_management.py
  - [ ] Migrate schemas/motivation.py
  - [ ] Migrate schemas/instructor_availability.py
  - [ ] Migrate api/tournaments/generator.py
  - [ ] Run tests: verify 0 Pydantic warnings

- [ ] Phase 3: pytest config cleanup (30min)
  - [ ] Update pytest.ini
  - [ ] Run tests: verify 0 config warnings

### Post-Sprint
- [ ] Full regression: `pytest app/tests/ -v`
- [ ] Verify pass rate ≥ 86.0%
- [ ] Create PR: `p4/deprecation-warnings-cleanup` → `main`
- [ ] Code review
- [ ] Merge to main
- [ ] Update baseline tag: `baseline-post-p4-cleanup`

---

## 📊 Success Metrics

| Metric | Before | Target | Status |
|--------|--------|--------|--------|
| Warnings | 436 | 0 | ⏳ Pending |
| datetime.utcnow() | ~180 | 0 | ⏳ Pending |
| Pydantic V1 | ~250 | 0 | ⏳ Pending |
| pytest config | ~6 | 0 | ⏳ Pending |
| Test pass rate | 86.0% | ≥86.0% | ⏳ Pending |
| Test failures | 0 | 0 | ⏳ Pending |

---

## 🔒 Quality Gates

**Gate 1: No Regression**
- All existing tests must still pass
- Pass rate must not drop below 86.0%

**Gate 2: Warning Reduction**
- 100% of targeted warnings must be resolved
- No new warnings introduced

**Gate 3: CI Pipeline**
- All CI checks must pass
- No breaking changes

**If any gate fails**: Roll back and investigate before proceeding

---

**Created**: 2026-02-23 15:00 CET
**Sprint Start**: TBD (after feature gate approval)
**Estimated Duration**: 8-10 hours
**Priority**: P4 (Maintenance)
**Blocking**: No (can run in parallel with feature development)
