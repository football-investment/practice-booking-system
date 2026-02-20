# External CI Migration: Technical Comparison

**Context**: GitHub Actions is unavailable at account level (footballinvestment). This proposal compares three external CI options for automated E2E validation.

**Decision Criteria**: Cost, setup complexity, maintenance overhead, integration with GitHub, execution time.

---

## Option A: GitLab CI

### Overview
- **Cost**: Free tier: 400 CI/CD minutes/month (shared runners)
- **Setup**: Mirror GitHub repo to GitLab, configure `.gitlab-ci.yml`
- **Integration**: GitHub webhook triggers GitLab pipeline

### Pros
- ✅ Generous free tier (400 minutes/month)
- ✅ Built-in Docker support (docker-in-docker)
- ✅ Mature platform with extensive documentation
- ✅ Can post status checks back to GitHub via API
- ✅ YAML config similar to GitHub Actions (easy migration)

### Cons
- ❌ Requires maintaining mirror between GitHub ↔ GitLab
- ❌ External dependency (another platform to manage)
- ❌ Status checks require custom GitHub API integration

### Implementation Effort
- **Setup**: 2-3 hours (repo mirror + pipeline config)
- **Maintenance**: Low (automatic sync via webhook)

### Example `.gitlab-ci.yml`
```yaml
smoke_test:
  image: cypress/browsers:node20.11.0-chrome121.0.6167.85-1-ff121.0-edge121.0.2277.83-1
  stage: test
  only:
    - merge_requests
  script:
    - cd tests_cypress && npm ci
    - npm run cy:run:critical
```

**Verdict**: ✅ **Recommended for quick MVP** — free, fast setup, minimal GitHub disruption.

---

## Option B: CircleCI

### Overview
- **Cost**: Free tier: 6,000 build minutes/month (30,000 credits)
- **Setup**: Connect GitHub account, configure `.circleci/config.yml`
- **Integration**: Native GitHub app integration

### Pros
- ✅ **Highest free tier** (6,000 minutes vs GitLab 400)
- ✅ Native GitHub integration (automatic status checks)
- ✅ No repository mirroring required
- ✅ Excellent Docker support (Docker layer caching)
- ✅ Mature E2E testing workflows (Cypress orb available)

### Cons
- ❌ Requires CircleCI account + GitHub app authorization
- ❌ Different YAML syntax from GitHub Actions (steeper learning curve)
- ❌ Free tier limited to 1 concurrent job

### Implementation Effort
- **Setup**: 1-2 hours (GitHub app authorization + config)
- **Maintenance**: Very low (fully automated)

### Example `.circleci/config.yml`
```yaml
version: 2.1
orbs:
  cypress: cypress-io/cypress@3
workflows:
  test:
    jobs:
      - cypress/run:
          filters:
            branches:
              only: [main, develop]
          start-command: 'npm run cy:run:critical'
          working-directory: tests_cypress
```

**Verdict**: ✅ **Recommended for production** — best free tier, native GitHub integration, zero maintenance.

---

## Option C: Self-Hosted GitHub Actions Runner

### Overview
- **Cost**: Infrastructure cost (VPS/EC2 instance: ~$10-20/month)
- **Setup**: Deploy runner on VPS, register with GitHub account
- **Integration**: Native GitHub Actions (uses existing `.github/workflows/*.yml`)

### Pros
- ✅ **Zero code changes** — existing workflows work as-is
- ✅ Full control over environment (custom dependencies, caching)
- ✅ No account-level Actions restriction (runner bypasses it)
- ✅ Unlimited minutes (infrastructure permitting)
- ✅ No vendor lock-in (can run anywhere: AWS, DigitalOcean, Hetzner)

### Cons
- ❌ Infrastructure cost (~$10-20/month for small VPS)
- ❌ Requires server management (security patches, uptime monitoring)
- ❌ No official support for personal accounts (designed for organizations)
- ⚠️ **May still be blocked** if account-level Actions restriction applies to self-hosted runners

### Implementation Effort
- **Setup**: 3-4 hours (VPS provisioning + runner installation + testing)
- **Maintenance**: Medium (server maintenance, runner updates)

### Example Setup (DigitalOcean Droplet)
```bash
# On Ubuntu 22.04 VPS ($12/month, 2GB RAM)
$ curl -o actions-runner-linux.tar.gz -L https://github.com/actions/runner/releases/download/v2.314.1/actions-runner-linux-x64-2.314.1.tar.gz
$ tar xzf actions-runner-linux.tar.gz
$ ./config.sh --url https://github.com/footballinvestment/practice-booking-system --token <TOKEN>
$ sudo ./svc.sh install
$ sudo ./svc.sh start
```

**Verdict**: ⚠️ **Risk: Uncertain if account restriction applies** — Test on free Oracle Cloud instance first before committing.

---

## Decision Matrix

| Criteria | GitLab CI | CircleCI | Self-Hosted Runner |
|----------|-----------|----------|--------------------|
| **Setup Time** | 2-3 hours | 1-2 hours | 3-4 hours |
| **Monthly Cost** | $0 | $0 | $10-20 |
| **Free Minutes** | 400 | 6,000 | Unlimited |
| **GitHub Integration** | API-based | Native | Native |
| **Maintenance** | Low | Very Low | Medium |
| **Reuses Existing Workflows** | No | No | Yes ✅ |
| **Risk** | Low | Low | **Medium** (may be blocked) |

---

## Recommendation

### 🥇 **Primary Recommendation: CircleCI**

**Rationale**:
- **Highest free tier** (6,000 minutes = ~200 critical suite runs/month)
- **Native GitHub integration** (status checks work out-of-the-box)
- **Lowest maintenance** (fully managed, no infrastructure)
- **Fast setup** (1-2 hours to production-ready)

**Execution Plan**:
1. Create CircleCI account (free tier)
2. Authorize CircleCI GitHub app for `footballinvestment/practice-booking-system`
3. Migrate `.github/workflows/cypress-e2e.yml` to `.circleci/config.yml`
4. Test on feature branch → merge to main
5. **Total: 1-2 hours**

---

### 🥈 **Fallback: GitLab CI** (if CircleCI blocked)

Use if CircleCI authorization fails or GitHub app permissions denied.

**Setup**:
1. Create GitLab account (free tier)
2. Import GitHub repo as mirror (auto-sync enabled)
3. Create `.gitlab-ci.yml` with critical suite job
4. Configure GitHub webhook to trigger GitLab pipeline
5. **Total: 2-3 hours**

---

### ⚠️ **Not Recommended: Self-Hosted Runner**

**Reason**: Unclear if account-level Actions restriction applies to self-hosted runners. Risk of infrastructure investment ($10-20/month) with no guarantee of success.

**Only pursue if**:
1. CircleCI and GitLab both fail
2. GitHub Support confirms self-hosted runners bypass account restriction
3. Free testing on Oracle Cloud Always Free tier (2 AMD VMs, 24GB RAM total)

---

## Next Steps

1. **Immediate** (Day 1): Create CircleCI account + test critical suite
2. **Week 1**: Full migration if CircleCI succeeds
3. **Fallback** (Week 2): GitLab CI if CircleCI blocked
4. **Long-term**: Monitor GitHub Support ticket for native Actions re-enablement

---

**Document Version**: 1.0
**Author**: Claude Sonnet 4.5
**Date**: 2026-02-20
**Status**: Proposal — Awaiting approval
