# Quality Gate Architecture

> Champion Badge Regression Guard — design reference for the LFA Education Center project.

---

## 1. Overview

The quality gate is a two-layer, fully offline system that enforces one business rule:

> **CHAMPION badges must never display "No ranking data".**

It is designed to be:
- **Deterministic** — same result regardless of who runs it or on which machine
- **Self-contained** — starts and stops its own test infrastructure
- **Auditable** — every bypass is recorded with reason, branch, and author
- **Hard to circumvent** — the most common override path (`--no-verify`) is addressed at multiple levels

---

## 2. Two-layer local gate

```
git commit                     git push
     │                              │
     ▼                              ▼
┌─────────────┐             ┌──────────────────────────────┐
│ pre-commit  │             │         pre-push             │
│ (static)    │             │  (full E2E, self-managed)    │
│  < 1 s      │             │        30 – 60 s             │
└─────────────┘             └──────────────────────────────┘
```

### Layer 1 — pre-commit (static, fast)

File: `hooks/pre-commit`

| Check | What it detects |
|-------|----------------|
| Regression string | `"No ranking data"` literal present in any staged `.py` file |
| Guard removal | `performance_card.py` staged but `badge_type == "CHAMPION"` block is gone |

**Why it exists**: catches accidental removal before any test infrastructure
needs to run. Costs < 1 second. Does not require Streamlit, FastAPI, or Playwright.

**Override**: `SKIP_CHAMPION_COMMIT_CHECK=1 git commit`
(no audit log — this layer is a convenience guard, not a hard enforcement point)

### Layer 2 — pre-push (E2E, deterministic)

File: `hooks/pre-push`

**Lifecycle sequence** (every `git push`):

```
 1  Acquire lockfile /tmp/champion_guard_8599.lock
    └─ If stale PID → remove; if live PID → abort (prevents parallel runs)
 2  Activate venv  (venv/bin/activate if present)
 3  Check Playwright importable  (fail-fast, actionable error)
 4  Health-check FastAPI at $API_BASE_URL/docs or /health or /
    └─ Backend is REQUIRED but NOT managed by this hook
 5  Start Streamlit on port 8599 (background, headless)
    DATABASE_URL=$CHAMPION_DB_URL python3 -m streamlit run streamlit_app/🏠_Home.py
    --server.port 8599 --server.headless true
 6  Readiness probe: curl http://localhost:8599 every 2 s
    └─ Timeout: $CHAMPION_START_TIMEOUT seconds (default 45)
    └─ Early-exit if Streamlit process dies before becoming ready
 7  Export CHAMPION_TEST_URL=http://localhost:8599
    Run: python3 -m pytest tests_e2e/test_champion_badge_regression.py::test_...
 8  trap cleanup EXIT / INT / TERM
    └─ Kill Streamlit PID
    └─ Remove lockfile
    └─ Always runs, even on SIGINT (Ctrl-C)
```

**Override** — both env vars required, skip is audit-logged:

```bash
SKIP_CHAMPION_CHECK=1 SKIP_REASON="docs-only change" git push
# appends to .git/hooks/champion_skip_audit.log:
# 2026-02-10T14:00:00Z  SKIP  branch=...  user=...  reason=...
```

### Tunable env vars

| Variable | Default | Purpose |
|----------|---------|---------|
| `CHAMPION_TEST_PORT` | `8599` | Dedicated test port (isolated from dev `8501`) |
| `CHAMPION_START_TIMEOUT` | `45` | Seconds to wait for Streamlit readiness |
| `CHAMPION_DB_URL` | `postgresql://postgres:postgres@localhost:5432/lfa_intern_system` | DB for test Streamlit |
| `API_BASE_URL` | `http://localhost:8000` | FastAPI health-check URL |
| `CHAMPION_TEST_URL` | (set by hook) | Playwright target; override for manual runs |

---

## 3. Test strategy

File: `tests_e2e/test_champion_badge_regression.py`

**"Wide net" approach** — avoids brittle deep navigation:

```
Login → JS-click LFA Player Dashboard (sidebar is CSS-hidden)
      → Expand all Streamlit accordions
      → Collect all visible body text
      → Sliding-window assertion (±15 lines around any CHAMPION signal)
```

**Core assertion**:
```python
# For every line containing CHAMPION / 🥇 Champion / Champion:
#   If "No ranking data" appears within 15 lines → FAIL
```

**Why sliding window**: a card section spans ~5–10 lines in Streamlit's DOM text;
15 lines ensures coverage without mixing two unrelated cards.

**Evidence**: on PASS, `tests_e2e/screenshots/champion_badge_PASS.png` is written.

---

## 4. Bypassing with `--no-verify`

`git push --no-verify` skips the pre-push hook entirely on the client side.
This is the main circumvention vector for client-side hooks.

### 4a. Server-side pre-receive hook (recommended for teams)

A **bare repository** (used as the central push target — e.g. a self-hosted Gitea,
Forgejo, GitLab CE, or a plain bare git repo over SSH) can enforce the rule
server-side. `--no-verify` has no effect on server-side hooks.

**Design** for a bare-repo `hooks/pre-receive`:

```bash
#!/usr/bin/env bash
# /path/to/bare-repo.git/hooks/pre-receive
# Blocks any push that removes the CHAMPION guard from performance_card.py

set -uo pipefail
PERF_CARD="streamlit_app/components/tournaments/performance_card.py"

while read -r old_sha new_sha ref; do
    # Skip branch deletions
    [[ "${new_sha}" == "0000000000000000000000000000000000000000" ]] && continue

    # If the file is modified in this push, check the guard is still present
    if git diff --name-only "${old_sha}" "${new_sha}" 2>/dev/null \
           | grep -qF "${PERF_CARD}"; then
        content=$(git show "${new_sha}:${PERF_CARD}" 2>/dev/null || true)
        if ! echo "${content}" | grep -q 'badge_type == "CHAMPION"'; then
            echo "PUSH REJECTED: CHAMPION guard removed from ${PERF_CARD}"
            echo "The CHAMPION badge must never display 'No ranking data'."
            echo "Restore the guard before pushing."
            exit 1
        fi
        if echo "${content}" | grep -q '"No ranking data"'; then
            echo "PUSH REJECTED: hardcoded 'No ranking data' in ${PERF_CARD}"
            exit 1
        fi
    fi
done

exit 0
```

**Deployment steps** (self-hosted bare repo):

```bash
# On the server that hosts the central bare repo:
cp hooks/pre-receive /path/to/bare-repo.git/hooks/pre-receive
chmod +x /path/to/bare-repo.git/hooks/pre-receive
```

This hook:
- Runs on the server for every push, regardless of `--no-verify`
- Does not require Playwright, Streamlit, or any running service
- Performs only static checks (fast, no side effects)
- Is idempotent and stateless

**Note**: The full E2E Playwright test is intentionally NOT run server-side —
it requires a running FastAPI + DB, which a bare git server doesn't have.
The server-side hook is a static guard; the full E2E guard runs client-side.

**Layered defence summary**:

```
Developer machine:
  pre-commit  → static (< 1s)        [skippable with --no-verify]
  pre-push    → E2E  (30–60s)        [skippable with --no-verify]

Central bare repo (server):
  pre-receive → static (< 1s)        [NOT skippable — server enforced]
```

### 4b. Interim protection without a bare server

If a bare server is not yet available:

1. **Mandatory code review** — treat `performance_card.py` changes as requiring
   a second pair of eyes before merge.
2. **Audit log review** — periodically review `.git/hooks/champion_skip_audit.log`
   for undocumented skips.
3. **Post-push verification** — run the E2E test manually after any push that
   used `--no-verify`, before the next deployment.

---

## 5. Docker containerisation plan

Containerising the test environment ensures every developer runs in an identical
environment with no "works on my machine" issues.

### Proposed structure

```
docker/
  Dockerfile.test          # Playwright + Python test image
  Dockerfile.streamlit     # Streamlit app image
  Dockerfile.api           # FastAPI app image
docker-compose.test.yml    # Orchestrated test environment
```

### `docker/Dockerfile.test`

```dockerfile
FROM python:3.13-slim

# System deps for Playwright/Chromium
RUN apt-get update && apt-get install -y \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgtk-3-0 \
    libgbm1 libasound2 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt streamlit_requirements.txt ./
RUN pip install --no-cache-dir \
    -r requirements.txt \
    -r streamlit_requirements.txt \
    playwright pytest-playwright pytest

# Install Chromium once (baked into image)
RUN playwright install chromium --with-deps

COPY . .

ENV PYTHONPATH=/app
```

### `docker-compose.test.yml`

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: lfa_intern_system_test
    ports: ["5433:5432"]        # 5433 to avoid clashing with local PG
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 3s
      timeout: 5s
      retries: 10

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.test
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/lfa_intern_system_test
    depends_on:
      db:
        condition: service_healthy
    ports: ["8000:8000"]
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8000/docs"]
      interval: 5s
      timeout: 10s
      retries: 12

  streamlit:
    build:
      context: .
      dockerfile: docker/Dockerfile.test
    command: >
      python3 -m streamlit run streamlit_app/🏠_Home.py
        --server.port 8599
        --server.headless true
        --server.address 0.0.0.0
        --browser.gatherUsageStats false
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/lfa_intern_system_test
      API_BASE_URL: http://api:8000
    depends_on:
      api:
        condition: service_healthy
    ports: ["8599:8599"]
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8599"]
      interval: 5s
      timeout: 10s
      retries: 12

  e2e-tests:
    build:
      context: .
      dockerfile: docker/Dockerfile.test
    command: >
      python3 -m pytest
        tests_e2e/test_champion_badge_regression.py
        -v -s --tb=short --no-header
    environment:
      CHAMPION_TEST_URL: http://streamlit:8599
    depends_on:
      streamlit:
        condition: service_healthy
    volumes:
      - ./tests_e2e/screenshots:/app/tests_e2e/screenshots
```

### Running containerised tests

```bash
# Full orchestrated run (build → seed DB → run → report)
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Tail test output only
docker compose -f docker-compose.test.yml logs -f e2e-tests

# Cleanup
docker compose -f docker-compose.test.yml down -v
```

### Integration with existing pre-push hook

The pre-push hook can be extended to prefer Docker when available:

```bash
# In hooks/pre-push, before starting Streamlit directly:
if command -v docker &>/dev/null && [[ -f "docker-compose.test.yml" ]]; then
    docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
    exit $?
fi
# Fallback: native lifecycle (current behaviour)
```

This makes the hook environment-aware: Docker where available, native otherwise.

---

## 6. Migration path to self-hosted CI

When the team grows, the local hooks become insufficient as the only gate
(multiple developers, parallel branches, merge queues). The architecture below
allows a **zero-rebuild migration** to self-hosted CI.

### Phase map

```
Phase 1 (now)           Phase 2                  Phase 3
─────────────           ───────────────────       ──────────────────────
Local git hooks    →    Self-hosted runner   →    Full CI pipeline
pre-commit (fast)       Same Docker image         Parallel test shards
pre-push  (E2E)         Same test command         Coverage, lint, deploy
Manual install          Auto-triggered            Merge queue enforcement
```

### Phase 2: self-hosted runner (e.g. Gitea Actions, Forgejo, GitLab CI)

Because the Docker image and test command are already defined, the CI job is
trivially small. Example for **Gitea Actions** (`.gitea/workflows/champion.yml`)
or **GitLab CI** (`.gitlab-ci.yml`):

```yaml
# .gitea/workflows/champion.yml  (Gitea Actions — syntax identical to GitHub Actions)
name: Champion Badge Guard

on: [push, pull_request]

jobs:
  champion-guard:
    runs-on: self-hosted     # your local machine or a dedicated server
    steps:
      - uses: actions/checkout@v4
      - name: Run containerised E2E guard
        run: |
          docker compose -f docker-compose.test.yml \
            up --build --abort-on-container-exit
        timeout-minutes: 5
      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: champion-screenshots
          path: tests_e2e/screenshots/
```

```yaml
# .gitlab-ci.yml  (GitLab CE self-hosted)
champion-guard:
  stage: test
  script:
    - docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
  artifacts:
    when: on_failure
    paths:
      - tests_e2e/screenshots/
  timeout: 5 minutes
```

**What does NOT change** when migrating:
- Test file (`test_champion_badge_regression.py`)
- Docker image (`docker/Dockerfile.test`)
- Test command (`python3 -m pytest ... --tb=short`)
- The `CHAMPION_TEST_URL` env var convention

**What changes**:
- Trigger moves from `git push` (client) to the CI server (server)
- Screenshots are uploaded as job artifacts instead of local files
- SKIP override becomes a CI variable (audited by the CI system)

### Protecting the main branch (Phase 2/3)

On Gitea/Forgejo/GitLab CE, the equivalent of GitHub branch protection:

```
Repository settings → Branch rules → main
  ✅ Require status checks: champion-guard
  ✅ Require pull request before merging
  ✅ Dismiss stale approvals on new commits
```

This makes the Champion guard a **required check** that blocks merge —
even if a developer pushes with `--no-verify` or skips the local hooks.

---

## 7. File inventory

| File | Layer | Purpose |
|------|-------|---------|
| `hooks/pre-commit` | L1 static | Staged-content guard, < 1s |
| `hooks/pre-push` | L2 E2E | Self-managed Streamlit lifecycle + Playwright test |
| `hooks/install-hooks.sh` | Tooling | Installs both hooks; idempotent |
| `tests_e2e/test_champion_badge_regression.py` | Test | Playwright golden-path test |
| `tests_e2e/pytest.ini` | Config | markers, maxfail, strict-markers |
| `tests_e2e/run_champion_regression.sh` | Tooling | Manual runner with pre-flight checks |
| `tests_e2e/README_CHAMPION_REGRESSION.md` | Docs | Setup, override, fallback procedure |
| `docs/quality-gate-architecture.md` | Docs | This document |
| *(planned)* `docker/Dockerfile.test` | Docker | Playwright + Python baked image |
| *(planned)* `docker-compose.test.yml` | Docker | Orchestrated DB + API + Streamlit + tests |
| *(planned)* bare-repo `hooks/pre-receive` | Server | Static guard, bypasses `--no-verify` |

---

## 8. Quick-reference decision tree

```
Developer makes a change
        │
        ▼
  git commit
        │
  [pre-commit]─── "No ranking data" in staged Python? ──▶ BLOCK
        │                                                    ↑
        │         CHAMPION guard removed?              ──▶ BLOCK
        │
  commit succeeds
        │
        ▼
   git push
        │
  [pre-push]──── FastAPI running? ─────────────────────── else BLOCK (actionable msg)
        │
        │──── Streamlit starts on :8599
        │         └─ ready within 45s? ──────────────────── else BLOCK
        │
        │──── Playwright test runs
        │         └─ CHAMPION near "No ranking data"? ───── BLOCK + screenshot
        │
  PASS → push proceeds
        │
        ▼
  [server pre-receive] ← not skippable, even with --no-verify
        │
        │──── CHAMPION guard still in performance_card.py? ─ else REJECT
        │
  push accepted on server
```
