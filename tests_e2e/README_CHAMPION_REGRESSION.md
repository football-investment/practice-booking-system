# Champion Badge Regression Test

## Overview

This E2E test protects against a critical production bug where Champion badges
displayed "No ranking data" instead of showing the #1 ranking.

**Business Rule**: Champion badges MUST ALWAYS display ranking information
(#1 of N players), never "No ranking data".

This test runs as a **local git hook system** — fully offline, no cloud CI
required.

---

## Two-layer quality gate

| Hook | Trigger | Duration | What it checks |
|------|---------|----------|----------------|
| `pre-commit` | Every `git commit` | < 1s | Static: no hardcoded `"No ranking data"` in staged Python; CHAMPION guard not removed from `performance_card.py` |
| `pre-push` | Every `git push` | ~30–60s | E2E: starts dedicated Streamlit on port 8599, runs Playwright test, stops Streamlit |

---

## Setup

### 1 — Install hooks (once per clone)

```bash
./hooks/install-hooks.sh
```

Copies `hooks/pre-commit` → `.git/hooks/pre-commit`
and `hooks/pre-push` → `.git/hooks/pre-push`.
Idempotent: safe to run after hook updates.

### 2 — Ensure test user exists in DB (once)

The pre-push test requires `junior.intern@lfa.com` to exist with a CHAMPION badge.

```sql
-- Check it exists
SELECT id, email FROM users WHERE email = 'junior.intern@lfa.com';

-- If missing: update an existing STUDENT user
UPDATE users SET
    email             = 'junior.intern@lfa.com',
    password_hash     = '<bcrypt hash of password123>',
    onboarding_completed = true,
    specialization    = 'LFA_FOOTBALL_PLAYER'
WHERE id = <your_test_user_id>;

UPDATE user_licenses
SET onboarding_completed = true
WHERE user_id = <your_test_user_id>;

-- Ensure a CHAMPION badge with badge_metadata exists
INSERT INTO tournament_badges (
    user_id, semester_id, badge_type, badge_category,
    title, description, icon, rarity, badge_metadata, earned_at
) VALUES (
    <your_test_user_id>,
    (SELECT id FROM semesters LIMIT 1),
    'CHAMPION', 'PLACEMENT',
    '🥇 Champion', 'First place finish', '🥇', 'LEGENDARY',
    '{"placement": 1, "total_participants": 24}',
    NOW()
);
```

Generate the bcrypt hash:
```bash
source venv/bin/activate
python3 -c "import bcrypt; print(bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode())"
```

### 3 — Ensure FastAPI backend is running before pushing

The pre-push hook requires the FastAPI backend (it is not managed by the hook):

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/lfa_intern_system \
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The hook self-manages the Streamlit instance — you do **not** need to start it manually.

---

## How the pre-push hook works

```
🏆 Champion Badge Regression Guard v2  (pre-push)
   ✅ Virtual environment activated
   ✅ Playwright found
   ✅ FastAPI backend reachable
   Starting dedicated Streamlit on port 8599 ...
     Waiting for Streamlit... (2/45s)
   ✅ Streamlit ready on http://localhost:8599

   Running regression test...

   ✅ Found CHAMPION badge signal(s) at 2 line(s)
   ✅ No 'No ranking data' found near any CHAMPION badge

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ CHAMPION guard PASSED — push allowed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If regression is detected:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ❌ CHAMPION guard FAILED — PUSH BLOCKED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  REGRESSION: CHAMPION badge shows 'No ranking data'
```

The Streamlit instance is automatically stopped in both PASS and FAIL cases.

---

## Override (emergency use only)

### pre-commit override

```bash
SKIP_CHAMPION_COMMIT_CHECK=1 git commit -m "..."
```

### pre-push override

Both env vars are required. The skip is written to an audit log.

```bash
SKIP_CHAMPION_CHECK=1 SKIP_REASON="docs-only change, no Python modified" git push
```

The audit log is at `.git/hooks/champion_skip_audit.log`:
```
2026-02-10T14:30:00Z  SKIP  branch=feature/xyz  user=dev@example.com  reason=docs-only change
```

---

## Running manually

### Option 1 — Helper script
```bash
./tests_e2e/run_champion_regression.sh
```

### Option 2 — Direct pytest
```bash
source venv/bin/activate
export CHAMPION_TEST_URL="http://localhost:8501"   # or 8599 for a dedicated instance
python3 -m pytest tests_e2e/test_champion_badge_regression.py \
    -v -s --tb=short -m golden_path
```

### Option 3 — Debug mode (visible browser, full-page screenshot)
```bash
pytest tests_e2e/test_champion_badge_regression.py -k debug -s
```

---

## Tunable env vars (pre-push)

| Variable | Default | Description |
|----------|---------|-------------|
| `CHAMPION_TEST_PORT` | `8599` | Port for dedicated Streamlit test instance |
| `CHAMPION_START_TIMEOUT` | `45` | Seconds to wait for Streamlit readiness |
| `CHAMPION_DB_URL` | `postgresql://postgres:postgres@localhost:5432/lfa_intern_system` | DB URL for the Streamlit process |
| `API_BASE_URL` | `http://localhost:8000` | FastAPI backend URL |
| `CHAMPION_TEST_URL` | (set by hook) | Where Playwright points; override for manual runs |

Example — slow machine:
```bash
CHAMPION_START_TIMEOUT=90 git push
```

---

## Failure debugging

1. **Screenshot**: `tests_e2e/screenshots/champion_badge_FAILED.png`
2. **Streamlit log**: `/tmp/champion_streamlit_8599.log`
3. **Verify DB data**:
   ```sql
   SELECT badge_type,
          badge_metadata->>'placement'          AS placement,
          badge_metadata->>'total_participants' AS total_participants
   FROM tournament_badges
   JOIN users ON tournament_badges.user_id = users.id
   WHERE users.email = 'junior.intern@lfa.com'
     AND badge_type = 'CHAMPION';
   ```
4. **Verify `performance_card.py`** has the CHAMPION guard:
   ```python
   if badge_type == "CHAMPION" and not rank:
       if badges and len(badges) > 0:
           badge_metadata = badges[0].get('badge_metadata', {})
           if badge_metadata.get('placement'):
               rank = badge_metadata['placement']
   ```

---

## Fallback procedure (if hooks are broken or bypassed)

If for any reason the hooks are not firing (e.g. after a manual `.git` reset,
fresh clone without running the installer, or hooks accidentally deleted):

### Detect the problem
```bash
# Check hooks are installed
ls -la .git/hooks/pre-commit .git/hooks/pre-push

# If missing, reinstall:
./hooks/install-hooks.sh
```

### Run the E2E test manually before merging
```bash
source venv/bin/activate
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/lfa_intern_system \
  python3 -m streamlit run streamlit_app/🏠_Home.py --server.port 8501 &
sleep 20
CHAMPION_TEST_URL=http://localhost:8501 \
  python3 -m pytest tests_e2e/test_champion_badge_regression.py -v -s --tb=short
kill %1   # stop background Streamlit
```

### Verify the guard is present in source
```bash
grep -n 'badge_type == "CHAMPION"' streamlit_app/components/tournaments/performance_card.py
```
Expected output: at least one match showing the guard block.

### What the regression looks like
Champion badge card shows:
```
🥇 Champion
No ranking data
```
instead of:
```
🥇 Champion
#1 of 24 players
```

### Root cause reference
**Root cause**: `tournament_rankings` table had no entries for completed
tournaments; metrics query returned NULL for both `rank` and `total_participants`.

**Fix** (`streamlit_app/components/tournaments/performance_card.py`):
- Fallback: read `total_participants` from `badge_metadata` when metrics are missing
- CHAMPION guard: force `rank = badge_metadata['placement']` when rank is NULL

---

## Files

| File | Purpose |
|------|---------|
| `hooks/pre-commit` | Git hook — fast static check before every commit |
| `hooks/pre-push` | Git hook — full E2E test before every push (self-manages Streamlit) |
| `hooks/install-hooks.sh` | Installs both hooks into `.git/hooks/` |
| `tests_e2e/test_champion_badge_regression.py` | Playwright E2E test |
| `tests_e2e/run_champion_regression.sh` | Manual runner with pre-flight checks |
| `tests_e2e/pytest.ini` | E2E-specific pytest config |
