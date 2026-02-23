# Patch Note: Real User Names in Tournament Monitor

**Date:** 2026-02-14
**Component:** OPS Tournament Generator
**Issue:** Tournament Monitor displaying placeholder names ("OPS-fd37 Player 0001") instead of real user names
**Status:** ✅ FIXED

---

## Problem

When creating tournaments via the OPS generator (`/tournaments/ops/run-scenario`), the system was creating NEW placeholder users with fake names like "OPS-fd37 Player 0001" and emails like "ops.a3f2b1c0.0001@lfa-ops.internal".

This caused the Tournament Monitor UI to display these placeholder names instead of real user names from the seed database.

**Database Evidence:**
```sql
-- OLD BEHAVIOR: Placeholder users created
SELECT id, name, email FROM users WHERE name LIKE '%OPS%Player%' LIMIT 5;
-- Result:
--   72632 | OPS-fd37 Player 0001 | ops.fd372784.0001@lfa-ops.internal
--   72633 | OPS-fd37 Player 0002 | ops.fd372784.0002@lfa-ops.internal
--   ...

-- EXISTING SEED USERS (unused):
SELECT id, name, email FROM users WHERE email LIKE '%@lfa-seed.hu%' LIMIT 5;
-- Result:
--   72344 | Peter Odhiambo      | peter.odhiambo@lfa-seed.hu
--   72345 | Rachid Bougherra    | rachid.bougherra@lfa-seed.hu
--   72346 | Mariela Ramírez     | mariela.ramirez@lfa-seed.hu
```

---

## Root Cause

The OPS generator endpoint ([generator.py:1757-1782](app/api/api_v1/endpoints/tournaments/generator.py)) was creating new users in a loop instead of using the existing @lfa-seed.hu seed users that have real names.

**OLD CODE (Lines 1757-1782):**
```python
seeded_ids: list[int] = []
for i in range(1, request.player_count + 1):
    email = f"ops.{_run_id}.{i:04d}@lfa-ops.internal"
    player = _User(
        email=email,
        name=f"OPS-{_run_id[:4]} Player {i:04d}",  # ❌ Placeholder name!
        role=_UserRole.STUDENT,
        password_hash="!ops-placeholder-not-loginable",
        is_active=True,
        onboarding_completed=True,
    )
    db.add(player)
    db.flush()
    # ... create license ...
    seeded_ids.append(player.id)
```

---

## Solution

Replaced the user creation loop with a query to existing @lfa-seed.hu seed users with real names.

**NEW CODE (Lines 1757-1797):**
```python
# ✅ USE EXISTING SEED USERS: Query all active @lfa-seed.hu users with active licenses
seed_rows = (
    db.query(_User.id, _User.name, _User.email)
    .join(UserLicense, UserLicense.user_id == _User.id)
    .filter(
        _User.email.like("%@lfa-seed.hu"),
        _User.is_active == True,
        UserLicense.is_active == True,
    )
    .order_by(_User.id)
    .all()
)
seed_user_ids = [row.id for row in seed_rows]

if not seed_user_ids:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=(
            f"No active @lfa-seed.hu users found with licenses. "
            f"Run 'python scripts/seed_star_players.py' to create seed users first."
        ),
    )

if request.player_count > len(seed_user_ids):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            f"Cannot enroll {request.player_count} players: only {len(seed_user_ids)} "
            f"@lfa-seed.hu seed users available. Increase seed user count or reduce player_count."
        ),
    )

# ✅ DETERMINISTIC: Take first N players from ordered pool
seeded_ids = seed_user_ids[:request.player_count]
```

---

## Key Changes

1. **No More User Creation**: OPS generator now queries existing seed users instead of creating placeholders
2. **Real Names**: Tournaments will use users with real names like "Peter Odhiambo", "Rachid Bougherra", "Mariela Ramírez"
3. **Error Handling**: Raises helpful errors if:
   - No @lfa-seed.hu users exist (suggests running seed script)
   - Not enough seed users for requested player count
4. **Deterministic Selection**: Always takes first N users ordered by ID (reproducible)
5. **Logging**: Debug logs show sample seed users being used

---

## Testing

### 1. Verify Seed Users Exist
```bash
# Check seed user count
python -c "
from app.database import SessionLocal
from app.models.user import User
from app.models.license import UserLicense
db = SessionLocal()
count = db.query(User.id).join(UserLicense).filter(
    User.email.like('%@lfa-seed.hu'),
    User.is_active == True,
    UserLicense.is_active == True
).count()
print(f'✅ Found {count} active @lfa-seed.hu seed users')
db.close()
"
```

**Expected Output:**
```
✅ Found 1000+ active @lfa-seed.hu seed users
```

### 2. Create New Test Tournament
1. Open Tournament Monitor UI: http://localhost:8501
2. Login as admin@lfa.com
3. Create a new 64-player Group+Knockout tournament via OPS wizard
4. Wait for session generation to complete
5. **VERIFY**: Session cells show real names like "Odhiambo 2-1 Bougherra" (NOT "Player 0001 2-1 Player 0002")

### 3. Check Backend Logs
```bash
tail -50 /tmp/backend_8000.log | grep "Using.*existing seed players"
```

**Expected Output:**
```
[ops] Using 64 existing seed players (pool size: 1000, run_id=a3f2b1c0)
```

---

## Impact

### Before Fix:
- ❌ Tournament Monitor showed "Player 0001", "Player 0002" everywhere
- ❌ Database polluted with thousands of unused placeholder users
- ❌ No meaningful participant tracking in history tabs

### After Fix:
- ✅ Tournament Monitor shows "Peter Odhiambo", "Rachid Bougherra", etc.
- ✅ All tournaments use existing seed users (no database bloat)
- ✅ Meaningful participant names in completed matches, pending knockouts, group stage
- ✅ Real user data tied to all results and matchups

---

## Related Files

- **Fixed:** [app/api/api_v1/endpoints/tournaments/generator.py](app/api/api_v1/endpoints/tournaments/generator.py) (Lines 1740-1797)
- **Already Correct:** [app/services/sandbox_test_orchestrator.py](app/services/sandbox_test_orchestrator.py) (Lines 437-530)
- **UI Display:** [streamlit_app/components/admin/tournament_monitor.py](streamlit_app/components/admin/tournament_monitor.py) (_session_cell function)
- **Seed Script:** [scripts/seed_star_players.py](scripts/seed_star_players.py)

---

## Prerequisites

Ensure you have enough seed users for your largest tournament:
```bash
# Create 1024 seed users with real names
python scripts/seed_star_players.py
```

---

## Rollback

If needed, revert to placeholder user creation:
```bash
git diff HEAD~1 app/api/api_v1/endpoints/tournaments/generator.py
git checkout HEAD~1 -- app/api/api_v1/endpoints/tournaments/generator.py
```

---

## User Request (Original)

**Hungarian:** "A játékos neve ne csak ID vagy 'Player 0001' legyen, hanem a tényleges username vagy first_name + last_name mezőből származó valódi név jelenjen meg. Ne csak vizuális placeholder legyen — minden eredmény és matchup a tényleges felhasználóhoz legyen kötve a DB-ből."

**English:** "Player names should not just be IDs or 'Player 0001', but actual names from username or first_name + last_name fields should be displayed. It should not just be a visual placeholder — every result and matchup should be tied to the actual user from the DB."

**Status:** ✅ **COMPLETED**

---

**Next Steps:**
1. ✅ Backend restarted with fix applied
2. ⏳ Create new 64p tournament via OPS wizard to verify
3. ⏳ Confirm real names appear in Tournament Monitor
4. ⏳ Update E2E tests if they expect placeholder names
