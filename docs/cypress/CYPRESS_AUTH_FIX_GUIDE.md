# Cypress Auth Fix Guide — enrollment_409_live.cy.js

> **Issue**: 401 Unauthorized - Player login fails
> **Test**: `tests_cypress/cypress/e2e/student/enrollment_409_live.cy.js`
> **Impact**: 1/439 Cypress tests failing (99.77% pass rate)
> **Priority**: CRITICAL - blocks 100% E2E validation

---

## Problem

The test `enrollment_409_live.cy.js` fails in the `before` hook with:

```
CypressError: `cy.request()` failed on:
http://localhost:8000/api/v1/auth/login

The response we received from your web server was:
  > 401: Unauthorized
```

**Root Cause**: Test DB doesn't have the expected player account with correct credentials.

---

## Expected Credentials (from cypress.config.js)

```javascript
playerEmail:    'rdias@manchestercity.com'
playerPassword: 'TestPlayer2026'
```

---

## Solution Options

### Option 1: Seed Player Account to Test DB (Recommended)

**Execute SQL**:
```sql
-- Connect to test database
\c practice_booking_test

-- Check if player exists
SELECT id, email, first_name, last_name FROM users WHERE email = 'rdias@manchestercity.com';

-- If not exists, insert player
INSERT INTO users (
    email,
    password_hash,
    first_name,
    last_name,
    role,
    is_active,
    created_at,
    updated_at
) VALUES (
    'rdias@manchestercity.com',
    -- Password hash for 'TestPlayer2026' (use your actual hashing function)
    '$2b$12$HASH_HERE',  -- Generate with: passlib.hash.bcrypt.hash('TestPlayer2026')
    'Ruben',
    'Dias',
    'PLAYER',
    true,
    NOW(),
    NOW()
) RETURNING id;

-- Add player profile/onboarding data if needed
INSERT INTO player_profiles (user_id, onboarding_completed_at, ...)
VALUES (...);
```

**Or use Python script**:
```python
from app.core.security import get_password_hash
from app.models.user import User
from app.db.session import SessionLocal

db = SessionLocal()

# Create player
player = User(
    email='rdias@manchestercity.com',
    password_hash=get_password_hash('TestPlayer2026'),
    first_name='Ruben',
    last_name='Dias',
    role='PLAYER',
    is_active=True
)
db.add(player)
db.commit()
db.refresh(player)

print(f"Player created: ID={player.id}")
```

---

### Option 2: Update Test to Use Existing Player

**Find existing player**:
```sql
SELECT email, role FROM users WHERE role = 'PLAYER' AND is_active = true LIMIT 1;
```

**Update cypress.config.js**:
```javascript
env: {
    playerEmail: 'actual.player@example.com',  // Use existing email
    playerPassword: 'ActualPassword123'        // Use actual password
}
```

---

### Option 3: Create Test Fixture Script

**Create**: `tests_cypress/scripts/seed_test_users.py`

```python
#!/usr/bin/env python3
"""Seed test users for Cypress E2E tests"""

from app.core.security import get_password_hash
from app.models.user import User
from app.db.session import SessionLocal

def seed_test_users():
    db = SessionLocal()

    # Player for E2E tests
    player_email = 'rdias@manchestercity.com'

    # Check if exists
    existing = db.query(User).filter(User.email == player_email).first()
    if existing:
        print(f"✓ Player {player_email} already exists (ID={existing.id})")
        return

    # Create player
    player = User(
        email=player_email,
        password_hash=get_password_hash('TestPlayer2026'),
        first_name='Ruben',
        last_name='Dias',
        role='PLAYER',
        is_active=True
    )
    db.add(player)
    db.commit()
    db.refresh(player)

    print(f"✓ Created player {player_email} (ID={player.id})")

if __name__ == '__main__':
    seed_test_users()
```

**Run before Cypress tests**:
```bash
python tests_cypress/scripts/seed_test_users.py
npm run cy:run:critical
```

---

## Verification

After seeding, verify the fix:

```bash
# Run the specific failing test
cd tests_cypress
npx cypress run --spec "cypress/e2e/student/enrollment_409_live.cy.js"

# Expected output:
# ✓ All 6 tests passing
# ✓ No 401 errors
```

Then run full critical suite:
```bash
npm run cy:run:critical

# Expected: 439/439 passing (100%)
```

---

## Quick Fix (5 minutes)

If you just need to get tests passing NOW:

```bash
# 1. Connect to test DB
psql practice_booking_test

# 2. Quick check
SELECT email, role FROM users WHERE email = 'rdias@manchestercity.com';

# 3. If not exists, create with temporary password
-- Use Option 1 SQL above

# 4. Run test
cd tests_cypress && npm run cy:run:critical
```

---

## Prevention

**Add to CI/CD pipeline**:
```yaml
# .github/workflows/cypress-e2e.yml
- name: Seed Test Users
  run: python tests_cypress/scripts/seed_test_users.py

- name: Run Cypress E2E
  run: npm run cy:run:critical
```

---

**Status**: READY TO FIX
**Effort**: 5-30 minutes
**Impact**: Cypress suite 99.77% → 100%
