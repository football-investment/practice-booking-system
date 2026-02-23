# Next Phase Plan — Post-Stabilization Strategy

**Status:** ✅ Test Infrastructure Stable (333 passed, 0 failed, 0 errors)
**Date:** 2026-02-15
**Baseline Tag:** `test-infra-stable-baseline`

---

## 🎯 Strategic Objective

**Phase Goal:** Consolidate API client architecture WITHOUT destabilizing the codebase.

**Core Principle:** Incremental, risk-controlled improvements with continuous validation.

---

## 📋 Recommended Next Step: APIClient Unification

### Scope (IN SCOPE)

✅ **Consolidate 10 fragmented API helper files into unified APIClient**
- `streamlit_app/api_helpers_*.py` (3,780 lines) → `streamlit_app/api_client.py` (~300 lines)
- Centralized error handling
- Consistent timeout/retry logic
- Type-safe response handling

✅ **Backward compatibility maintained**
- Existing code continues to work
- Gradual migration path
- No breaking changes

✅ **Test coverage**
- Unit tests for APIClient methods
- Integration tests for critical endpoints
- Regression suite validation

### Scope (OUT OF SCOPE)

❌ **NOT in this phase:**
- Tournament Monitor refactoring (2,678 lines) — deferred to Iteration 5
- Database schema changes
- Model refactoring
- Business logic changes
- New feature development

### Why APIClient First?

1. **Low Risk:** Pure infrastructure change, no business logic
2. **High Value:** Eliminates duplicated error handling across 10 files
3. **Fast Validation:** Existing E2E tests validate correctness
4. **Measurable:** Clear before/after comparison (lines of code, duplication metrics)

---

## 🚨 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Breaking existing Streamlit pages | Medium | High | Backward-compatible wrapper, gradual migration |
| API timeout inconsistencies | Low | Medium | Centralized config, comprehensive tests |
| Test suite regression | Low | Critical | **Mandatory:** 0 failed, 0 errors before merge |
| Scope creep (wizard refactor) | High | Critical | **HARD BOUNDARY:** APIClient only, no UI changes |

---

## ✅ Success Criteria (Measurable)

### **Must-Have (Merge Blockers)**

1. **Test Suite Stability**
   - ✅ `pytest tests/unit/ -q` → 0 failed, 0 errors
   - ✅ `pytest tests_e2e/ -m smoke` → All passing
   - ✅ No new xfail markers introduced

2. **Code Quality**
   - ✅ APIClient implementation < 400 lines
   - ✅ 100% type hints on public methods
   - ✅ Docstrings on all public methods

3. **Backward Compatibility**
   - ✅ Existing `api_helpers_*` imports still work
   - ✅ No changes required in calling code for Phase 1

### **Nice-to-Have (Optional)**

- 🎯 Reduce total API helper code by >60% (3,780 → <1,500 lines)
- 🎯 Centralized logging/metrics
- 🎯 Request/response interceptors

---

## 📐 Implementation Strategy

### **Phase A: Foundation (1-2 days)**

1. Create `streamlit_app/api_client.py` with core structure
   ```python
   class APIClient:
       def __init__(self, base_url, token, timeout=30)
       def get(self, path, **kwargs) -> APIResponse
       def post(self, path, **kwargs) -> APIResponse

   class TournamentAPI:
       def get_rankings(self, tid) -> APIResponse[list]
       def submit_result(self, tid, sid, payload) -> APIResponse[dict]
   ```

2. Write unit tests for APIClient
   - Mock HTTP layer
   - Test timeout handling
   - Test error responses

3. **Validation:** Unit tests pass, no code uses new client yet

### **Phase B: Migration (2-3 days)**

1. Create backward-compatible wrappers in `api_helpers_*.py`
   ```python
   # Old code continues to work
   def get_tournament_rankings(token, tid):
       client = APIClient.from_config(token)
       return client.tournaments.get_rankings(tid)
   ```

2. Migrate 1-2 critical endpoints first (e.g., tournament rankings, session submission)

3. Run full E2E smoke tests after each endpoint migration

4. **Validation:** E2E tests pass, Streamlit pages load correctly

### **Phase C: Cleanup (1 day)**

1. Remove duplicated helper functions
2. Consolidate error handling logic
3. Update documentation

4. **Validation:** Full test suite passes, code metrics improved

---

## 🛡️ Merge Requirements (Non-Negotiable)

**Before merging to `feature/performance-card-option-a`:**

```bash
# 1. Full unit test suite
pytest tests/unit/ -q
# Required: 0 failed, 0 errors

# 2. E2E smoke tests
pytest tests_e2e/ -m smoke --tb=short
# Required: All passing

# 3. Manual verification
streamlit run streamlit_app/Home.py
# Required: Tournament Monitor loads without errors
```

**If any check fails → DO NOT MERGE. Fix first.**

---

## 🚫 Anti-Patterns to Avoid

1. ❌ **Scope Creep:** "While we're here, let's also refactor the wizard..."
   - **Rule:** APIClient only. Nothing else.

2. ❌ **Big Bang Migration:** "Let's migrate all 10 files at once..."
   - **Rule:** Incremental. One endpoint at a time. Validate continuously.

3. ❌ **Breaking Changes:** "The old way is ugly, let's force everyone to migrate..."
   - **Rule:** Backward compatibility. Migration is gradual, not forced.

4. ❌ **Test Skipping:** "The tests are slow, let's skip them..."
   - **Rule:** 100% test coverage. No shortcuts.

---

## 📊 Progress Tracking

Use this checklist to track progress:

### Phase A: Foundation
- [ ] Create `api_client.py` with core APIClient class
- [ ] Implement `TournamentAPI` namespace
- [ ] Write unit tests for APIClient
- [ ] Validate: Unit tests pass

### Phase B: Migration
- [ ] Migrate `get_tournament_rankings()` endpoint
- [ ] Migrate `submit_result()` endpoint
- [ ] Run E2E smoke tests
- [ ] Validate: E2E tests pass

### Phase C: Cleanup
- [ ] Remove duplicated error handling
- [ ] Update documentation
- [ ] Final validation: Full test suite

### Merge Checklist
- [ ] `pytest tests/unit/ -q` → 0 failed, 0 errors
- [ ] `pytest tests_e2e/ -m smoke` → All passing
- [ ] Manual verification: Streamlit pages load
- [ ] Code review approved
- [ ] Merge to feature branch

---

## 🔄 Rollback Plan

**If anything goes wrong:**

1. **Immediate:** `git revert` to `test-infra-stable-baseline` tag
2. **Analysis:** Identify root cause (test failure, runtime error, etc.)
3. **Fix:** Address issue in isolation
4. **Re-validate:** Full test suite before retry

**DO NOT:**
- Push forward with broken tests
- Skip validation steps
- Accumulate technical debt

---

## 📅 Timeline Estimate

| Phase | Duration | Risk Level |
|-------|----------|-----------|
| Phase A: Foundation | 1-2 days | Low |
| Phase B: Migration | 2-3 days | Medium |
| Phase C: Cleanup | 1 day | Low |
| **Total** | **4-6 days** | **Controlled** |

**Note:** These are conservative estimates. Quality > speed.

---

## 🎓 Lessons from Stabilization Phase

**What worked well:**
- ✅ Atomic commits with clear scope
- ✅ Test-driven validation at each step
- ✅ xfail markers for pre-existing issues
- ✅ Clear success metrics (0 failed, 0 errors)

**Apply to APIClient phase:**
- Small, incremental changes
- Test validation after each change
- Document decisions in commit messages
- Clear rollback points

---

## 📝 Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-15 | Defer Tournament Monitor refactor | Too risky immediately after stabilization |
| 2026-02-15 | APIClient first | Low risk, high value, measurable outcome |
| 2026-02-15 | Backward compatibility required | Gradual migration safer than big bang |

---

## 🚀 After APIClient: Future Work

**Deferred to Iteration 5+ (after APIClient is stable):**

1. Tournament Monitor decomposition (2,678 lines → modular components)
2. Ops Wizard extraction
3. Session grid refactoring
4. Additional test coverage for edge cases

**Priority order:**
1. Consolidate infrastructure (APIClient) ← **YOU ARE HERE**
2. Validate stability (full test suite)
3. Decompose UI components (wizard, monitor)
4. Add features (only after foundation is solid)

---

## ✍️ Approval

**Proceed with APIClient unification when:**
- [ ] This plan is reviewed and approved
- [ ] Current test baseline is stable (verified with fresh run)
- [ ] Development environment is clean (no uncommitted changes)

**Approved by:** _[Your approval here]_
**Start date:** _[When you're ready]_

---

**Remember:** The goal is not speed. The goal is **sustainable, high-quality progress**.

🎯 **Stay focused. Stay disciplined. Stay stable.**
