# Release Policy & CI Governance

> **Owner:** Engineering Team  
> **Last Updated:** 2026-02-24  
> **Version:** 1.0.0

---

## 🎯 Purpose

This document defines the CI/CD governance model for the `practice-booking-system` repository, establishing clear boundaries between **blocking gates** (merge-critical) and **informational suites** (regression monitoring).

**Strategic Goal:**  
- **Main branch:** Deterministic, fast, backend-core stability  
- **Nightly suites:** Comprehensive regression coverage (UI/Playwright/Cypress)

---

## 🚦 Blocking vs Informational Workflows

### ✅ BLOCKING Workflows (Required Status Checks)

These workflows **MUST pass** before merging to `main`. Failure blocks PR merge and direct pushes.

| Workflow | Purpose | Performance Target | Ownership |
|----------|---------|-------------------|-----------|
| **Test Baseline Check** | Full lifecycle E2E coverage (13 gates) | <5 min total | Backend Team |
| **Skill Weight Pipeline** | Skill progression regression (28+ tests) | <2 min | Game Logic Team |

**Enforcement:**  
- GitHub branch protection: `main` branch requires these checks  
- Admin override: **Available via PR approval**, NOT protection disable

---

### ℹ️ INFORMATIONAL Workflows (Nightly Regression)

These workflows provide **comprehensive coverage** but do NOT block merges. Failures trigger alerts but allow main branch progress.

| Workflow | Schedule | Purpose | Alert Policy |
|----------|----------|---------|--------------|
| **E2E Fast Suite** | 2 AM UTC daily | Playwright UI tests (52 tests) | Slack alert on failure |
| **E2E Wizard Coverage** | 3 AM UTC daily | Tournament wizard flows (P1 critical) | Slack alert on failure |
| **Cypress E2E Tests** | 4 AM UTC daily | Core user flows (auth, error states) | Slack alert on failure |
| **Cross-Platform Testing** | 5 AM UTC daily | Multi-platform validation | Slack alert on failure |
| **E2E Integration Critical** | 2 AM UTC daily | Nightly integration suite | Email report |
| **E2E Live Suite** | 2 AM UTC daily | Live environment smoke tests | PagerDuty on critical failure |
| **E2E Scale Suite** | 3 AM UTC Sunday | Capacity validation (512p+) | Weekly report |

**Rationale:**  
UI/Playwright/Cypress tests are **flaky in CI headless environments**. Moving to nightly schedule:
- Prevents main branch blockage from transient UI failures  
- Maintains regression coverage without sacrificing velocity  
- Allows focused debugging of UI issues in isolation

---

## 🌙 Nightly Regression Suite Role

**Purpose:**  
- **Comprehensive coverage** beyond blocking gates  
- **UI/frontend validation** (Playwright, Cypress, Streamlit)  
- **Cross-platform compatibility** (macOS, Windows, Linux)  
- **Performance benchmarking** (scale tests, capacity validation)

**Alert Workflow:**
1. Nightly suite failure → Slack #ci-alerts channel  
2. Triage within 24 hours (assign owner)  
3. Fix within 48 hours OR document known issue  
4. Critical failures (Live Suite) → PagerDuty escalation

**Success Metrics:**
- Nightly pass rate: **≥90%** (monthly average)  
- Time to fix: **<48 hours** (P1 failures)  
- Known issues: **Documented in GitHub Issues** with `ci:known-failure` label

---

## 🔥 Hotfix Bypass Process

**When to Use Hotfix Process:**  
- **Production incident** requiring immediate rollback  
- **Security vulnerability** patch (CVE mitigation)  
- **Data integrity issue** requiring urgent schema fix

**CRITICAL:** Hotfix uses **PR-based process with admin approval**, NOT branch protection disable.

---

### Hotfix Workflow (PR-Based)

**Approval Required:**
- **Tech Lead + 1 Senior Engineer** approval  
- **Document in #engineering-hotfix** Slack channel  
- **Create post-mortem issue** within 24 hours

**Procedure:**

1. **Create hotfix branch:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b hotfix/YYYY-MM-DD-description
   ```

2. **Implement fix** with **minimal scope** (single concern only)

3. **Request bypass approval in Slack:**
   ```
   🔥 HOTFIX REQUEST
   - Incident: [brief description]
   - Root cause: [summary]
   - Risk: [rollback plan if needed]
   - PR: [link when created]
   - Approvers needed: @tech-lead @senior-engineer
   ```

4. **Create PR to main:**
   ```bash
   git push origin hotfix/YYYY-MM-DD-description
   gh pr create --title "🔥 HOTFIX: [description]" \
     --body "## Incident
   [Severity] [Description]
   
   ## Fix
   [What changed]
   
   ## Risk Assessment
   [Rollback plan]
   
   ## Approvers
   - [ ] Tech Lead: @xxx
   - [ ] Senior Engineer: @xxx"
   ```

5. **Admin approval overrides blocking checks:**
   - Tech Lead/Admin uses **"Merge without waiting for requirements"** button
   - This requires **Admin** role on repository
   - **Blocking gates may be bypassed** ONLY with documented approval

6. **Merge hotfix** (admin can override failed checks)

7. **Post-mortem issue:**
   - Create within 24 hours: `[HOTFIX] YYYY-MM-DD - Description`
   - Use template below

---

### Post-Mortem Template

```markdown
# Hotfix Post-Mortem: YYYY-MM-DD

## Incident
- **Severity:** P0 / P1 / P2
- **Trigger:** [What caused the need for hotfix]
- **Impact:** [User-facing impact, revenue loss, etc.]
- **Detection:** [How discovered]

## Fix
- **PR:** #XXX
- **Commits:** [SHA list]
- **Bypass Approvers:** [@tech-lead, @senior-engineer]
- **Blocking checks status:** [PASS/FAILED - which ones]

## Root Cause
[5 Whys analysis]

## Prevention
- [ ] Action item 1 (owner: @xxx, due: YYYY-MM-DD)
- [ ] Action item 2 (owner: @xxx, due: YYYY-MM-DD)

## Lessons Learned
[What we learned, process improvements]
```

---

## 🔄 Rollback Strategy

### Scenario 1: Bad Deploy (Main Branch)

**Detection:**
- Monitoring alert (Sentry, DataDog)  
- User reports via support  
- Nightly suite regression (>5 tests fail)

**Rollback Process:**
1. **Identify bad commit:** `git log --oneline main -10`  
2. **Create revert branch:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b revert/YYYY-MM-DD-description
   git revert <bad-commit-sha>
   ```
3. **Create PR:** `gh pr create --title "revert: [original PR title]"`
4. **Fast-track review:** Tag @tech-lead for immediate approval  
5. **Merge revert:** Blocking gates MUST pass (standard process)  
6. **Monitor post-rollback:** Check Sentry for error rate drop

**Exception:** If blocking gates fail due to bad commit, use **Hotfix Process** above to revert.

---

### Scenario 2: Database Migration Failure

**Detection:**
- Alembic migration fails in production  
- Data corruption detected

**Rollback Process:**
1. **Database snapshot restore:** Use latest pre-migration backup  
2. **Downgrade migration:** `alembic downgrade -1`  
3. **Verify data integrity:** Run validation queries  
4. **Block further deploys:** Halt CI/CD pipeline  
5. **Post-mortem:** Migration review, add safety checks

**Prevention:**
- Dry-run migrations in staging  
- Backward-compatible schema changes  
- Blue-green deployment for risky migrations

---

### Scenario 3: Dependency Regression

**Detection:**
- Nightly suite fails after `pip install` update  
- Breaking change in transitive dependency

**Rollback Process:**
1. **Pin dependency version:** `requirements.txt` exact pin  
2. **Revert dependency update commit**  
3. **Document issue:** Create GitHub issue for upgrade path  
4. **Monitor for security patches:** Track CVE for pinned version

---

## 👥 CI Ownership & Responsibility

### 🔧 Backend Team
**Workflows:**
- Test Baseline Check (13/13 gates)  
- Skill Weight Pipeline  
- API Module Integrity  
- Cascade Delete Tests

**Responsibilities:**
- Maintain **0 flake tolerance** on blocking gates  
- Fix failures within **4 hours** (business hours)  
- Review and approve backend-related CI changes

---

### 🎨 Frontend Team
**Workflows:**
- E2E Fast Suite (Playwright)  
- E2E Wizard Coverage  
- Layout Validation

**Responsibilities:**
- Triage nightly UI failures within **24 hours**  
- Maintain Playwright test stability (>90% pass rate)  
- Update tests for UI changes within same PR

---

### 🧪 QA Team
**Workflows:**
- Cypress E2E Tests  
- E2E Live Suite  
- Cross-Platform Testing

**Responsibilities:**
- Monitor nightly regression suite  
- Report critical failures to engineering  
- Maintain test data integrity

---

### 🛠️ DevOps Team
**Workflows:**
- All workflows (infrastructure)  
- GitHub Actions runner health  
- PostgreSQL service stability

**Responsibilities:**
- CI/CD pipeline uptime **>99.5%**  
- Resolve infrastructure failures within **2 hours**  
- Maintain workflow concurrency groups

---

## 📊 CI Health Metrics

### Key Performance Indicators (KPIs)

| Metric | Target | Measurement | Owner |
|--------|--------|-------------|-------|
| Blocking gate pass rate | **100%** | Weekly | Backend Team |
| Nightly suite pass rate | **≥90%** | Monthly avg | QA Team |
| Mean time to fix (MTTF) | **<4 hours** | P1 failures | Engineering |
| CI pipeline uptime | **>99.5%** | Monthly | DevOps |
| Flake rate (blocking) | **0%** | Per-test | Backend Team |

---

## 🔍 Audit & Review

**Quarterly CI Review:**
- **Q1, Q2, Q3, Q4:** Engineering All-Hands meeting  
- **Agenda:**
  - Review nightly failure trends  
  - Discuss blocking gate stability  
  - Evaluate new test coverage needs  
  - Update RELEASE_POLICY.md if needed

**Change Management:**
- Any changes to **blocking gates** require Tech Lead approval  
- RELEASE_POLICY.md updates require **PR review + 2 approvals**  
- Version bump on policy changes (semantic versioning)

---

## 📚 References

- **GitHub Branch Protection:** [Settings → Branches → main](https://github.com/football-investment/practice-booking-system/settings/branches)  
- **CI Workflow Directory:** `.github/workflows/`  
- **Test Coverage Report:** `docs/TEST_COVERAGE.md`  
- **Technical Debt Tracker:** `docs/TECHNICAL_DEBT.md`

---

## ✅ Approval & Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-24 | Claude Sonnet 4.5 | Initial release policy |

**Approved by:**
- [ ] Tech Lead: _________________  
- [ ] Engineering Manager: _________________  
- [ ] Date: _________________

---

**END OF POLICY**
