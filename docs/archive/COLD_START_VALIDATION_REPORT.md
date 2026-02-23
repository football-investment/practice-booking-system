# Cold-Start Validation Report

**Date:** 2026-02-11  
**Branch:** feature/performance-card-option-a  
**Database:** lfa_intern_system  

---

## Pipeline Result: ALL PHASES PASSED ✅

| Phase | Description | Tests | Result | Duration |
|-------|-------------|-------|--------|----------|
| 0 | Drop DB → Clean setup → Snapshot | 1 | ✅ PASS | ~15s |
| 0b | Seed 12 star players (FC25 skills) | 1 | ✅ PASS | ~5s |
| Snapshot | Restore `00_with_star_players`, verify integrity | manual | ✅ PASS | 0.59s restore |
| 1 | Admin login smoke check | 1 | ✅ PASS | 10.79s |
| 2 | 4 pwt user registration via UI | 9 | ✅ PASS | ~2min |
| 3 | 4 pwt user onboarding (coupon + unlock + wizard) | 4 | ✅ PASS | 396s |

---

## Phase 0: Clean DB State

Seed data created:
- `admin@lfa.com` (ADMIN, pw: admin123)
- `grandmaster@lfa.com` (INSTRUCTOR, pw: GrandMaster2026!, 21 licenses)
- 1 specialization: `LFA_FOOTBALL_PLAYER`
- 1 semester: `FALL_2026` (ONGOING)
- 1 invitation code: `TEST-E2E-2026-AUTO`
- 1 game preset: `GANFOOTVOLLEY`
- 4 onboarding coupons: `E2E-BONUS-50-USER1/2/3/4`

## Phase 0b: Star Players (IDs 3–14)

| Player | Position | DB ID | Key Skills |
|--------|----------|-------|------------|
| Kylian Mbappé | STRIKER | 3 | finishing=97, sprint_speed=97, acceleration=97 |
| Erling Haaland | STRIKER | 4 | finishing=96, heading=90, strength=88 |
| Lionel Messi | MIDFIELDER | 5 | dribbling=96, vision=96, passing=91 |
| Vinicius Jr | WINGER | 6 | dribbling=96, acceleration=96, agility=93 |
| Jude Bellingham | MIDFIELDER | 7 | reactions=88, positioning_off=87, tactical_awareness=88 |
| Mohamed Salah | WINGER | 8 | finishing=90, dribbling=91, acceleration=93 |
| Phil Foden | MIDFIELDER | 9 | dribbling=90, ball_control=91, vision=88 |
| Rodri | MIDFIELDER | 10 | tackle=85, marking=84, tactical_awareness=93 |
| Rúben Dias | DEFENDER | 11 | tackle=90, marking=92, heading=90 |
| Bukayo Saka | WINGER | 12 | dribbling=86, crossing=84, finishing=83 |
| Jamal Musiala | MIDFIELDER | 13 | dribbling=91, ball_control=90, agility=90 |
| Victor Osimhen | STRIKER | 14 | finishing=93, sprint_speed=92, strength=86 |

Snapshot `00_with_star_players`: 0.33MB, restore in 0.59s ✅

## Phase 2: Registration (IDs 15–18)

| User | Email | DB ID |
|------|-------|-------|
| Kis Péter | pwt.k1sqx1@f1rstteam.hu | 15 |
| Petike | pwt.p3t1k3@f1rstteam.hu | 16 |
| Valverde Jr | pwt.v4lv3rd3jr@f1rstteam.hu | 17 |
| Tibike | pwt.t1b1k3@f1rstteam.hu | 18 |

## Phase 3: Onboarding DB Final State

All 4 pwt users:
- `users.onboarding_completed = true` ✅
- `user_licenses.onboarding_completed = true` ✅  
- `user_licenses.football_skills` populated (29 skills @ baseline 60/100) ✅
- `user_licenses.motivation_scores` populated (position + goal) ✅
- `credit_balance = 0` (50 starting + 50 coupon − 100 unlock) ✅

---

## Bugs Found and Fixed

### BUG-1: `submit_lfa_player_onboarding` stale API helper (PRODUCTION BUG)
**File:** `streamlit_app/api_helpers_general.py:453`  
**Symptom:** Onboarding submit silently fails with `KeyError: 'shooting'`  
**Root cause:** Helper accessed old 6-key schema (`skills['shooting']`, etc.) but backend now expects JSON `{"skills": {29-key dict}}`. Form-encoded POST vs JSON POST mismatch.  
**Fix:** Replaced form_data with `json=payload` containing `{"skills": skills_dict}` matching backend contract.  
**Impact:** Every onboarding attempt in production was silently failing — `onboarding_completed` was never set to True.

### BUG-2: Registration test used wrong user group (`star_users` vs `pwt_users`)
**File:** `tests/e2e_frontend/user_lifecycle/registration/test_registration_with_invite_code.py`  
**Fix:** `_load_star_users()` → `_load_pwt_users()` reading `data["pwt_users"]`

### BUG-3: Hub load verification used hidden element
**File:** Same registration test  
**Fix:** URL-based check (`"Specialization_Hub" in page.url`) instead of hidden sidebar element

### BUG-4: `test_d8` used undefined `db` fixture
**File:** Same registration test  
**Fix:** Replaced with direct `psycopg2.connect()`

### BUG-5: Wrong email domain in hub tests (`@f1stteam.hu` → `@f1rstteam.hu`)
**File:** Same registration test  
**Fix:** Corrected domain string

### BUG-6: Onboarding test used wrong user group
**File:** `tests/e2e_frontend/user_lifecycle/onboarding/test_onboarding_with_coupon.py`  
**Fix:** `["star_users"]` → `["pwt_users"]`

### BUG-7: Goal selectbox index 0 = placeholder (disabled Complete button)
**File:** Same onboarding test  
**Fix:** `random.randint(0, n-1)` → `random.randint(1, n-1)` to skip placeholder

### BUG-8: Coupon navigation: "Back to Hub" → LFA_Player_Dashboard (not Hub)
**File:** Same onboarding test  
**Root cause:** `My_Credits.py` "Back to Hub" button routes `LFA_FOOTBALL_PLAYER` users to Dashboard  
**Fix:** Apply coupon directly on Specialization Hub page (bonus code form is also there)

### BUG-9: `coupon_usages` table blocks re-use even after `current_uses` reset
**File:** DB state management  
**Fix:** `DELETE FROM coupon_usages` + `UPDATE coupons SET current_uses = 0`

---

## Non-Deterministic Phases

| Phase | Determinism | Notes |
|-------|-------------|-------|
| Phase 0 | ✅ Fully deterministic | DB drop+create+seed is idempotent |
| Phase 0b | ✅ Fully deterministic | Fixed skill values from JSON |
| Phase 1 | ✅ Deterministic | Simple login check |
| Phase 2 | ⚠️ Partially non-deterministic | Email addresses generated from names (contain random chars). Hub load URL check is reliable, but Streamlit page load timing is inherently non-deterministic. |
| Phase 3 | ⚠️ Timing-sensitive | Position selection is random (not deterministic). Slider interactions depend on Streamlit render timing — `wait_for_timeout` values are heuristic. On slow machines the 50ms slider step delay may need tuning. |

---

## Reset Script (for re-running Phase 3)

```sql
-- Run before each Phase 3 re-run:
BEGIN;
DELETE FROM coupon_usages WHERE user_id IN (15, 16, 17, 18);
UPDATE coupons SET current_uses = 0 WHERE code LIKE 'E2E-BONUS%';
UPDATE users SET credit_balance = 50 WHERE id IN (15, 16, 17, 18);
DELETE FROM user_licenses WHERE user_id IN (15, 16, 17, 18);
UPDATE users SET onboarding_completed = false WHERE id IN (15, 16, 17, 18);
COMMIT;
```

