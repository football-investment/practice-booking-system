# Champion Badge Regression Test

## Overview

This E2E test protects against a critical production bug where Champion badges
displayed "No ranking data" instead of showing the #1 ranking.

**Business Rule**: Champion badges MUST ALWAYS display ranking information
(#1 of N players), never "No ranking data".

This test runs as a **local git pre-push hook** — fully offline, no cloud CI
required.

---

## How It Works

### Pre-push hook (automatic)

After running `./hooks/install-hooks.sh` once, every `git push` triggers:

```
🏆 Champion Badge Regression Guard (pre-push)
   ✅ Streamlit is running
   🧪 Running regression test...
   ✅ Found CHAMPION badge signal(s) at 2 line(s)
   ✅ No 'No ranking data' found near any CHAMPION badge
   ✅ CHAMPION guard PASSED — push allowed
```

If the regression is present:

```
   ❌ CHAMPION guard FAILED — PUSH BLOCKED
   REGRESSION DETECTED: CHAMPION badge shows 'No ranking data'
```

### Test strategy

1. Login as `junior.intern@lfa.com` (headless Playwright)
2. Navigate to LFA Player Dashboard via JS (sidebar CSS-hidden)
3. Expand all accordions to surface badge cards
4. Sliding-window assertion (15 lines): if CHAMPION appears anywhere,
   "No ranking data" must NOT appear within that window
5. Save `tests_e2e/screenshots/champion_badge_PASS.png` on success,
   `champion_badge_FAILED.png` on failure

---

## Setup

### 1 — Install the hook (once per clone)

```bash
./hooks/install-hooks.sh
```

This copies `hooks/pre-push` → `.git/hooks/pre-push` and makes it executable.
Idempotent: safe to run again after hook updates.

### 2 — Create test user in DB (once)

The hook requires a user `junior.intern@lfa.com` with a CHAMPION badge.

```sql
-- Update an existing STUDENT user or create one
UPDATE users SET
    email        = 'junior.intern@lfa.com',
    password_hash = '<bcrypt hash of password123>',
    onboarding_completed = true,
    specialization = 'LFA_FOOTBALL_PLAYER'
WHERE id = <your_test_user_id>;

UPDATE user_licenses SET onboarding_completed = true
WHERE user_id = <your_test_user_id>;

INSERT INTO tournament_badges (
    user_id, semester_id, badge_type, badge_category,
    title, description, icon, rarity, badge_metadata, earned_at
) VALUES (
    <your_test_user_id>,
    <any_valid_semester_id>,
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

### 3 — Ensure Streamlit is running before pushing

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/lfa_intern_system \
  streamlit run streamlit_app/🏠_Home.py --server.port 8501
```

---

## Running Manually

### Option 1 — Helper script
```bash
./tests_e2e/run_champion_regression.sh
```

### Option 2 — Direct pytest
```bash
source venv/bin/activate
python3 -m pytest tests_e2e/test_champion_badge_regression.py \
    -v -s --tb=short -m golden_path
```

### Option 3 — Debug mode (visible browser, full-page screenshot)
```bash
pytest tests_e2e/test_champion_badge_regression.py -k debug -s
```

---

## Emergency Override

If you must push without Streamlit running (e.g. docs-only change):

```bash
SKIP_CHAMPION_CHECK=1 git push
```

**Document your reason** — this override bypasses a safety check.

---

## Failure Debugging

1. **Screenshot**: `tests_e2e/screenshots/champion_badge_FAILED.png`
2. **Verify DB data**:
   ```sql
   SELECT badge_type,
          badge_metadata->>'placement'          AS placement,
          badge_metadata->>'total_participants' AS total_participants
   FROM tournament_badges
   JOIN users ON tournament_badges.user_id = users.id
   WHERE users.email = 'junior.intern@lfa.com'
     AND badge_type = 'CHAMPION';
   ```
3. **Verify performance_card.py** has the CHAMPION guard:
   ```python
   # CRITICAL PRODUCT RULE: CHAMPION badge MUST have rank
   if badge_type == "CHAMPION" and not rank:
       if badges and len(badges) > 0:
           badge_metadata = badges[0].get('badge_metadata', {})
           if badge_metadata.get('placement'):
               rank = badge_metadata['placement']
   ```

---

## Files

| File | Purpose |
|------|---------|
| `hooks/pre-push` | Git hook — runs before every push |
| `hooks/install-hooks.sh` | Installs hooks into `.git/hooks/` |
| `tests_e2e/test_champion_badge_regression.py` | Playwright E2E test |
| `tests_e2e/run_champion_regression.sh` | Manual runner with pre-flight checks |
| `tests_e2e/pytest.ini` | E2E-specific pytest config |

---

## Root Cause Reference

**Symptom**: Champion badge showed "No ranking data" instead of "#1 of 24 players"

**Root cause**: `tournament_rankings` table had no entries for completed tournaments;
metrics query returned NULL for both `rank` and `total_participants`.

**Fix** (`streamlit_app/components/tournaments/performance_card.py`):
- Fallback: read `total_participants` from `badge_metadata` when metrics are missing
- CHAMPION guard: force `rank = badge_metadata['placement']` when rank is NULL
