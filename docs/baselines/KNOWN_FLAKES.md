# Known Test Flakes (Backlog)

## test_complete_onboarding_user1 - 10% failure rate

**Status:** 90% pass rate (9/10), intermittent failures

**Symptom:** Random test failures, no consistent pattern (failed on RUN 3 in last 10x)

**Root Cause Hypothesis:**
1. **Browser startup timing** - Chromium headless cold start variability
2. **Streamlit rerun race condition** - st.switch_page redirect timing in headless mode
3. **Network latency spikes** - Local API calls occasionally slow
4. **Session state race** - Concurrent DB writes during license creation

**Temporary Mitigation:**
- Increased timeouts (confirm button: 10s, redirect: 5s)
- DB verification instead of UI message checks
- Test isolation via setup_onboarding_coupons.py

**Next Steps (Backlog):**
- [ ] Add retry logic (pytest-rerunfailures)
- [ ] Profile slow runs to identify bottleneck
- [ ] Consider headful mode for CI stability
- [ ] Implement exponential backoff on critical waits

**Priority:** P2 (Nice to have - test provides value at 90%)

**Last Updated:** 2026-02-08
