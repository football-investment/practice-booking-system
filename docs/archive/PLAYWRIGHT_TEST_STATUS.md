# Playwright UI Tesztek - Jelenlegi Státusz Jelentés

**Dátum:** 2026-02-08
**Scope:** Kritikus user flow tesztek (registration, onboarding, user journeys) lokációjának és státuszának elemzése

---

## Executive Summary

**KRITIKUS PROBLÉMA:** A rendszer **legfontosabb** UI tesztjei (user registration, onboarding, business workflows) **NINCSENEK** az új, refaktorált tesztstruktúrában ([tests/e2e_frontend/](tests/e2e_frontend/)).

**Jelenlegi állapot:**
- ✅ Tournament format tesztek: Átkerültek az új struktúrába (tests/e2e_frontend/)
- ❌ Kritikus user flow tesztek: **MARADTAK** a régi mappákban (tests/e2e/, tests/playwright/)
- ❌ Duplikációk: Azonos tesztek léteznek 2+ mappában
- ❌ **NINCS EGYSÉGES STRUKTÚRA**

---

## I. Kritikus User Flow Tesztek - Pontos Lokációk

### A. USER REGISTRATION TESZTEK

#### 1. [tests/e2e/test_user_registration.py](tests/e2e/test_user_registration.py)
**Flow:** Invitation code alapú user regisztráció
**Scope:** Egyszerű regisztráció 1 user-rel
**UI Validáció:**
- Regisztrációs form kitöltése
- Invitation code beírása
- Regisztráció submit
- Sikeres regisztráció ellenőrzés

**Status:** ❌ **NEM** került át az új struktúrába

---

#### 2. [tests/e2e/test_complete_registration_flow.py](tests/e2e/test_complete_registration_flow.py)
**Flow:** TELJES user journey (registration + onboarding + coupon)
**Scope:** 3 First Team játékos regisztrációja
**UI Komponensek:**
- Registration form (@f1rstteamfc.hu email-ekkel)
- Coupon redemption UI
- Onboarding steps (3 lépés)
- Player Dashboard landing validation

**Browser:** Firefox only, headed mode, slowmo=1000
**Database:** Fresh reset required (admin + grandmaster only)

**Status:** ❌ **NEM** került át az új struktúrába

---

#### 3. [tests/e2e/test_user_registration_with_invites.py](tests/e2e/test_user_registration_with_invites.py)
**Flow:** User regisztráció invitation code-dal
**Scope:** Regisztrációs form + Hub loading validáció
**Duplikáció:** ⚠️ MAJDNEM AZONOS a [tests/playwright/test_user_registration_with_invites.py](tests/playwright/test_user_registration_with_invites.py) fájllal

**Status:** ❌ **NEM** került át az új struktúrába
**Issue:** DUPLIKÁLT verzió létezik

---

#### 4. [tests/playwright/test_user_registration_with_invites.py](tests/playwright/test_user_registration_with_invites.py)
**Flow:** User regisztráció invitation code-dal (pwt. prefix userekkel)
**Scope:** Admin creates codes → Users register → Hub loads
**Users:** 3 pwt.* prefix user (pwt.k1sqx1@f1stteam.hu, pwt.p3t1k3@f1stteam.hu, pwt.V4lv3rd3jr@f1stteam.hu)
**Browser:** Firefox headed mode

**CRITICAL REQUIREMENTS:**
- Fixed email addresses with pwt. prefix
- 50 credits per invitation code
- Age groups: Pre (6-11), Youth (12-17), Amateur (18+)
- Clean database (users created ONLY via invitation code)

**Status:** ❌ **NEM** került át az új struktúrába
**Issue:** DUPLIKÁLT verzió létezik (tests/e2e/)

---

### B. ONBOARDING TESZTEK

#### 5. [tests/e2e/test_complete_onboarding_with_coupon_ui.py](tests/e2e/test_complete_onboarding_with_coupon_ui.py)
**Flow:** Login → Coupon apply → Unlock specialization → Complete onboarding
**Prerequisites:** `python tests/e2e/setup_onboarding_coupons.py` futtatása előre
**Users:** 3 pwt. user (pwt.k1sqx1@f1stteam.hu, pwt.p3t1k3@f1stteam.hu, pwt.V4lv3rd3jr@f1stteam.hu)

**Flow részletesen:**
1. User login (50 credits)
2. Coupon apply (+50 credits → 100 total)
3. Unlock specialization (-100 credits → 0 remaining)
4. Complete onboarding (3 steps: Position, Skills, Goals)
5. Land on Player Dashboard

**UI Validáció:**
- Coupon form kitöltése
- Specialization unlock button
- Onboarding 3 lépés (step-by-step)
- Player Dashboard megjelenés

**Status:** ❌ **NEM** került át az új struktúrába
**Issue:** DUPLIKÁLT verzió létezik (tests/playwright/)

---

#### 6. [tests/playwright/test_complete_onboarding_with_coupon_ui.py](tests/playwright/test_complete_onboarding_with_coupon_ui.py)
**Flow:** Gyakorlatilag AZONOS a [tests/e2e/test_complete_onboarding_with_coupon_ui.py](tests/e2e/test_complete_onboarding_with_coupon_ui.py) fájllal
**Különbség:** Minimális fixture/helper eltérések

**Status:** ❌ **NEM** került át az új struktúrába
**Issue:** DUPLIKÁCIÓ

---

### C. LOGIN TESZTEK

#### 7. [tests/e2e/test_simple_login.py](tests/e2e/test_simple_login.py)
**Flow:** Egyszerű login flow validáció
**Scope:** Alapvető autentikáció tesztelése

**Status:** ❌ **NEM** került át az új struktúrába

---

## II. Business Workflow Tesztek

### D. INSTRUCTOR WORKFLOW TESZTEK

#### 8. [tests/e2e/test_ui_instructor_application_workflow.py](tests/e2e/test_ui_instructor_application_workflow.py)
**Flow:** TELJES UI-based workflow (Admin → Instructor → Player)

**Workflow lépései:**
1. Instructor browses open tournaments (Instructor Dashboard)
2. Instructor applies to tournament (UI)
3. Admin reviews and approves application (API for speed)
4. Instructor accepts assignment (Instructor Dashboard UI)
5. Admin opens enrollment (SEEKING_INSTRUCTOR → READY_FOR_ENROLLMENT)
6. 5 players enroll in tournament (UI loop)
7. Admin transitions to IN_PROGRESS (UI)
8. Instructor records results (UI)
9. Instructor marks tournament COMPLETED (UI)
10. Admin distributes rewards (UI)
11. Player views results and rewards (UI)

**UI Komponensek:**
- ✅ Admin Dashboard (status transitions, reward distribution)
- ✅ Instructor Dashboard (Applications tab, My Jobs tab, Result Recording)
- ✅ Player Dashboard (tournament browsing, enrollment, results)

**Status:** ❌ **NEM** került át az új struktúrába

---

#### 9. [tests/e2e/test_ui_instructor_invitation_workflow.py](tests/e2e/test_ui_instructor_invitation_workflow.py)
**Flow:** Instructor invitation workflow
**Scope:** Direct instructor assignment validáció

**Status:** ❌ **NEM** került át az új struktúrába

---

#### 10. [tests/e2e/test_instructor_assignment_flows.py](tests/e2e/test_instructor_assignment_flows.py)
**Flow:** Instructor assignment különböző flow-k
**Scope:** Application-based vs Direct assignment

**Status:** ❌ **NEM** került át az új struktúrába

---

### E. TOURNAMENT ENROLLMENT TESZTEK

#### 11. [tests/e2e/test_tournament_enrollment_protection.py](tests/e2e/test_tournament_enrollment_protection.py)
**Flow:** Tournament enrollment protection rules
**Validation:** Enrollment blocking scenarios

**Status:** ❌ **NEM** került át az új struktúrába
**Issue:** DUPLIKÁLT verzió létezik (tests/playwright/)

---

#### 12. [tests/playwright/test_tournament_enrollment_protection.py](tests/playwright/test_tournament_enrollment_protection.py)
**Flow:** Hasonló tesztek mint [tests/e2e/test_tournament_enrollment_protection.py](tests/e2e/test_tournament_enrollment_protection.py)

**Status:** ❌ **NEM** került át az új struktúrába
**Issue:** DUPLIKÁCIÓ

---

#### 13. [tests/playwright/test_tournament_enrollment_application_based.py](tests/playwright/test_tournament_enrollment_application_based.py)
**Flow:** Application-based enrollment workflow
**Scope:** Instructor application + Player enrollment

**Status:** ❌ **NEM** került át az új struktúrába

---

#### 14. [tests/playwright/test_tournament_enrollment_open_assignment.py](tests/playwright/test_tournament_enrollment_open_assignment.py)
**Flow:** Open assignment enrollment workflow
**Scope:** Direct instructor assignment + Player enrollment

**Status:** ❌ **NEM** került át az új struktúrába

---

### F. TOURNAMENT GAME TYPE TESZTEK

#### 15. [tests/playwright/test_tournament_game_types.py](tests/playwright/test_tournament_game_types.py)
**Flow:** Különböző tournament típusok validációja
**Scope:** HEAD_TO_HEAD, GROUP_STAGE, KNOCKOUT formátumok

**Status:** ❌ **NEM** került át az új struktúrába

---

### G. COMPLETE BUSINESS WORKFLOW TESZTEK

#### 16. [tests/e2e/test_complete_business_workflow.py](tests/e2e/test_complete_business_workflow.py)
**Flow:** TELJES business workflow end-to-end

**Workflow:**
1. Admin creates 2 tournaments
2. Direct instructor assignment for "GrandMaster" → Tournament 1
3. 4 instructors apply to Tournament 2
4. Admin randomly selects 1 instructor, declines 3 others
5. Selected instructor accepts assignment
6. 3 First Team players created
7. Coupons created and applied for credits
8. Players enroll in both tournaments
9. Attendance records created
10. Tournaments completed with reward distribution
11. Negative test: Instructor cannot create tournament (403)

**Status:** ❌ **NEM** került át az új struktúrába

---

#### 17. [tests/e2e/test_ui_complete_business_workflow.py](tests/e2e/test_ui_complete_business_workflow.py)
**Flow:** Teljes UI-based business workflow
**Scope:** Hasonló mint [test_complete_business_workflow.py](tests/e2e/test_complete_business_workflow.py)

**Status:** ❌ **NEM** került át az új struktúrába

---

## III. Tournament Management Tesztek

### H. ADMIN TOURNAMENT TESZTEK

#### 18. [tests/e2e/test_admin_create_tournament_refactored.py](tests/e2e/test_admin_create_tournament_refactored.py)
**Flow:** Admin tournament creation via UI
**Scope:** Tournament setup és konfiguráció

**Status:** ❌ **NEM** került át az új struktúrába

---

#### 19. [tests/e2e/test_admin_invitation_code.py](tests/e2e/test_admin_invitation_code.py)
**Flow:** Admin creates invitation codes
**Scope:** Invitation code management

**Status:** ❌ **NEM** került át az új struktúrába

---

### I. TOURNAMENT WORKFLOW TESZTEK

#### 20. [tests/e2e/test_tournament_workflow_happy_path.py](tests/e2e/test_tournament_workflow_happy_path.py)
**Flow:** Tournament happy path workflow
**Scope:** Teljes tournament lifecycle

**Status:** ❌ **NEM** került át az új struktúrába

---

#### 21. [tests/e2e/test_tournament_list.py](tests/e2e/test_tournament_list.py)
**Flow:** Tournament list megjelenítés
**Scope:** Tournament browsing UI validáció

**Status:** ❌ **NEM** került át az új struktúrába

---

#### 22. [tests/e2e/test_tournament_attendance_complete.py](tests/e2e/test_tournament_attendance_complete.py)
**Flow:** Attendance tracking workflow
**Scope:** Player check-in és attendance recording

**Status:** ❌ **NEM** került át az új struktúrába

---

### J. SANDBOX WORKFLOW TESZTEK

#### 23. [tests/e2e/test_sandbox_workflow.py](tests/e2e/test_sandbox_workflow.py)
**Flow:** Sandbox tournament workflow
**Scope:** Streamlit sandbox UI validáció

**Status:** ❌ **NEM** került át az új struktúrába

---

#### 24. [tests/e2e/test_sandbox_workflow_simple.py](tests/e2e/test_sandbox_workflow_simple.py)
**Flow:** Simplified sandbox workflow
**Scope:** Basic sandbox operations

**Status:** ❌ **NEM** került át az új struktúrába

---

## IV. Reward & Coupon Tesztek

### K. REWARD DISTRIBUTION TESZTEK

#### 25. [tests/e2e/test_reward_policy_distribution.py](tests/e2e/test_reward_policy_distribution.py)
**Flow:** Reward policy és distribution validáció
**Scope:** Reward calculation és distribution logic

**Status:** ❌ **NEM** került át az új struktúrába

---

#### 26. [tests/e2e/test_reward_policy_user_validation.py](tests/e2e/test_reward_policy_user_validation.py)
**Flow:** User-level reward validation
**Scope:** Player receives correct rewards

**Status:** ❌ **NEM** került át az új struktúrába

---

### L. COUPON TESZTEK

#### 27. [tests/e2e/test_coupon_form_ui.py](tests/e2e/test_coupon_form_ui.py)
**Flow:** Coupon form UI validáció
**Scope:** Coupon application via UI

**Status:** ❌ **NEM** került át az új struktúrába

---

## V. Player Workflow Tesztek

### M. PLAYER DASHBOARD TESZTEK

#### 28. [tests/e2e/test_hybrid_ui_player_workflow.py](tests/e2e/test_hybrid_ui_player_workflow.py)
**Flow:** Hybrid UI/API player workflow
**Scope:** Player dashboard operations

**Status:** ❌ **NEM** került át az új struktúrába

---

## VI. Match & Session Tesztek

### N. MATCH MANAGEMENT TESZTEK

#### 29. [tests/e2e/test_match_command_center.py](tests/e2e/test_match_command_center.py)
**Flow:** Match command center UI
**Scope:** Match result submission és management

**Status:** ❌ **NEM** került át az új struktúrába

---

## VII. ÚJ E2E Frontend Tesztek (Refaktorált Struktúra)

### O. FORMAT-BASED TOURNAMENT TESZTEK

#### 30. [tests/e2e_frontend/group_knockout/test_group_knockout_7_players.py](tests/e2e_frontend/group_knockout/test_group_knockout_7_players.py)
**Flow:** Group+Knockout tournament (7 players)
**Scope:** Teljes tournament lifecycle UI validáció

**Status:** ✅ **ÁT lett RENDEZVE** az új struktúrába

---

#### 31. [tests/e2e_frontend/group_knockout/test_group_stage_only.py](tests/e2e_frontend/group_knockout/test_group_stage_only.py)
**Flow:** Group stage only tournaments
**Scope:** Group stage edge cases

**Status:** ✅ **ÁT lett RENDEZVE** az új struktúrába

---

#### 32. [tests/e2e_frontend/head_to_head/test_tournament_head_to_head.py](tests/e2e_frontend/head_to_head/test_tournament_head_to_head.py)
**Flow:** Head-to-head tournament format
**Scope:** 1v1 matchup validáció

**Status:** ✅ **ÁT lett RENDEZVE** az új struktúrába

---

#### 33. [tests/e2e_frontend/individual_ranking/test_individual_ranking_full_ui_workflow.py](tests/e2e_frontend/individual_ranking/test_individual_ranking_full_ui_workflow.py)
**Flow:** Individual ranking tournament
**Scope:** Ranking submission és leaderboard

**Status:** ✅ **ÁT lett RENDEZVE** az új struktúrába

---

### P. SANDBOX WORKFLOW TESZTEK

#### 34. [tests/e2e_frontend/test_sandbox_workflow_e2e.py](tests/e2e_frontend/test_sandbox_workflow_e2e.py)
**Flow:** Sandbox workflow end-to-end (Group+Knockout)
**Scope:** Teljes sandbox flow UI validáció

**Status:** ✅ **ÁT lett RENDEZVE** az új struktúrába
**Recent Fix:** Import path fix (shared/streamlit_helpers)

---

### Q. REWARD DISTRIBUTION TESZTEK

#### 35. [tests/e2e_frontend/test_reward_distribution_e2e.py](tests/e2e_frontend/test_reward_distribution_e2e.py)
**Flow:** Reward distribution E2E
**Scope:** Reward calculation és distribution

**Status:** ✅ **ÁT lett RENDEZVE** az új struktúrába

---

## VIII. Debug Tesztek

### R. DEBUG & TROUBLESHOOTING TESZTEK

#### 36-45. [tests/debug/](tests/debug/)
**Fájlok:** 10 db test file
- test_phase8_no_queryparam.py
- test_query_param_isolation.py
- test_minimal_form.py
- test_page_reload.py
- test_participant_selection_minimal.py
- test_real_tournament_id.py
- ... stb.

**Scope:** Phase 8 debug, query param isolation, form testing
**Status:** ❌ Temporary debug tesztek (nem production)

---

## IX. Deprecated Tesztek

### S. ARCHIVED TESZTEK

#### 46. [tests/.archive/test_admin_create_tournament.py](tests/.archive/test_admin_create_tournament.py)
**Status:** Deprecated, újabb verzió létezik

---

#### 47. [tests/.archive/deprecated/test_true_golden_path_e2e.py](tests/.archive/deprecated/test_true_golden_path_e2e.py)
**Status:** Deprecated, Golden Path refaktorálva

---

## X. Refactor Scope - Mi Történt?

### Refactor Timeline

**2026-02-02:** [tests/e2e_frontend/](tests/e2e_frontend/) mappa létrehozása
```
commit d45e921b53b8fca4fb02a952d02915bfb5b45a12
feat(tests): Add Playwright E2E frontend test suite with 18/18 PASSED
```

**Scope:** Tournament format tesztek (INDIVIDUAL_RANKING, HEAD_TO_HEAD, GROUP_KNOCKOUT)

**Amit ÁTRAKTAK:**
- ✅ 15 INDIVIDUAL_RANKING config teszt
- ✅ 3 HEAD_TO_HEAD config teszt
- ✅ Reward distribution tesztek
- ✅ Sandbox workflow tesztek (tournament-based)

**Amit NEM RAKTAK ÁT:**
- ❌ User registration tesztek (4 fájl)
- ❌ Onboarding tesztek (2 fájl)
- ❌ Login tesztek (1 fájl)
- ❌ Instructor workflow tesztek (3 fájl)
- ❌ Tournament enrollment tesztek (4 fájl)
- ❌ Business workflow tesztek (2 fájl)
- ❌ Admin tournament tesztek (2 fájl)
- ❌ Tournament lifecycle tesztek (3 fájl)
- ❌ Coupon/Reward policy tesztek (3 fájl)
- ❌ Player workflow tesztek (1 fájl)
- ❌ Match management tesztek (1 fájl)

**ÖSSZESEN:**
- ✅ Áthelyezve: **7 teszt fájl** (tournament format-based)
- ❌ NEM áthelyezve: **26 teszt fájl** (user flows, business workflows)

---

## XI. Miért NEM került át?

### Feltételezett Okok

#### 1. **Tudatos Scope Korlátozás**
A refactor **NEM** tartalmazta a kritikus user flow teszteket.

**Bizonyíték:**
- Commit message: "Tournament format-based tests"
- Csak tournament-specifikus tesztek kerültek át
- User registration/onboarding **TUDATOSAN** kint maradt

#### 2. **Refactor Célja: Tournament Testing Struktúra**
A [tests/e2e_frontend/](tests/e2e_frontend/) mappa célja:
- Tournament formátumok tesztelése (HEAD_TO_HEAD, INDIVIDUAL_RANKING, GROUP_KNOCKOUT)
- Contract-first testing (data-testid)
- API-driven setup + UI validation

**NEM célja:**
- User management tesztek
- Authentication/Authorization tesztek
- Business workflow tesztek

#### 3. **Átmeneti Állapot - Félbehagyott Refactor?**
Lehetséges, hogy a refactor **NEM FEJEZŐDÖTT BE**.

**Indikációk:**
- tests/e2e/ mappa **továbbra is létezik** (nem deprecated)
- tests/playwright/ mappa **továbbra is létezik** (duplikációk)
- NINCS dokumentáció a migrációról
- NINCS deprecation notice a régi teszteken

#### 4. **Duplikációk Kezelése Függőben**
A tests/e2e/ és tests/playwright/ közötti duplikációk **NEM lettek feloldva**.

**Példák:**
- test_user_registration_with_invites.py (2 verzió)
- test_complete_onboarding_with_coupon_ui.py (2 verzió)
- test_tournament_enrollment_protection.py (2 verzió)

---

## XII. Jelenlegi Állapot - Összefoglaló

### Teszt Fájlok Száma Lokáció Szerint

| Lokáció | Fájlok Száma | Típus | Státusz |
|---------|--------------|-------|---------|
| tests/e2e/ | 31 | Kritikus user flows | ❌ Régi struktúra |
| tests/playwright/ | 6 | Duplikációk | ❌ Duplikált tesztek |
| tests/e2e_frontend/ | 7 | Tournament formats | ✅ Új struktúra |
| tests/debug/ | 10 | Debug | ⚠️ Temporary |
| tests/.archive/ | 2 | Deprecated | ⚠️ Archived |
| **ÖSSZESEN** | **56** | - | - |

### Kritikus Megállapítások

#### 1. ❌ **User Registration/Onboarding NINCSENEK az Új Struktúrában**
A rendszer **legkritikusabb** user flow tesztjei (registration, onboarding, login) **NEM** kerültek át a [tests/e2e_frontend/](tests/e2e_frontend/) mappába.

**Impact:** Új tesztek írásakor **NINCS VILÁGOS PATTERN** hova kell helyezni ezeket.

#### 2. ❌ **Duplikációk Kezelve NINCSENEK**
Azonos tesztek léteznek tests/e2e/ és tests/playwright/ mappákban.

**Példák:**
- test_user_registration_with_invites.py (2x)
- test_complete_onboarding_with_coupon_ui.py (2x)
- test_tournament_enrollment_protection.py (2x)

**Impact:** Maintenance burden, inconsistent updates

#### 3. ❌ **NINCS Egységes Struktúra**
3+ különböző mappában találhatók Playwright tesztek:
- tests/e2e/ (régi)
- tests/playwright/ (dedikált, de duplikált)
- tests/e2e_frontend/ (új, de csak tournament format tesztekre)

**Impact:** **CONFUSION** új tesztek írásakor

#### 4. ✅ **Tournament Format Tesztek Rendezettek**
A tournament-specifikus tesztek (HEAD_TO_HEAD, INDIVIDUAL_RANKING, GROUP_KNOCKOUT) **JÓL** rendezettek a [tests/e2e_frontend/](tests/e2e_frontend/) mappában.

**Pattern:**
```
tests/e2e_frontend/
├── group_knockout/
├── head_to_head/
├── individual_ranking/
└── shared/
```

#### 5. ❌ **Kritikus User Flow-k Átmeneti Állapotban**
A kritikus user flow tesztek (registration, onboarding, instructor workflows) **NEM** kerültek át az új struktúrába.

**Status:** ÁTMENETI / RENDEZETLEN

---

## XIII. Ajánlások

### A. RÖVID TÁVON (Immediate)

#### 1. **Dokumentáció: Világos Teszt Struktúra Policy**
Készíts **döntési útmutatót** arról, hogy:
- Hova kerüljenek az új user flow tesztek?
- Mi a tests/e2e/ vs tests/e2e_frontend/ közötti különbség?
- Milyen tesztek kerülnek a tests/playwright/ mappába?

**File:** `docs/TEST_STRUCTURE_POLICY.md`

#### 2. **Duplikációk Azonosítása és Dokumentálása**
Lista készítése a duplikált tesztekről:
- Melyik verzió a "kanonikus"?
- Melyiket kell törölni?
- Van-e különbség a két verzió között?

**File:** `DUPLICATE_TESTS.md`

#### 3. **Deprecation Notice**
Ha a tests/e2e/ mappa deprecated, jelöld meg:
```python
# tests/e2e/README.md
# ⚠️ DEPRECATED: Use tests/e2e_frontend/ for new tests
```

### B. KÖZÉPTÁVON (Next Sprint)

#### 4. **User Flow Tesztek Migrációja**
Helyezd át a kritikus user flow teszteket az új struktúrába:

**Javasolt struktúra:**
```
tests/e2e_frontend/
├── user_flows/
│   ├── registration/
│   │   ├── test_user_registration.py
│   │   ├── test_complete_registration_flow.py
│   │   └── test_registration_with_invites.py
│   ├── onboarding/
│   │   ├── test_onboarding_with_coupon.py
│   │   └── test_specialization_unlock.py
│   └── auth/
│       └── test_login.py
├── business_workflows/
│   ├── instructor/
│   │   ├── test_instructor_application.py
│   │   ├── test_instructor_assignment.py
│   │   └── test_instructor_invitation.py
│   └── admin/
│       ├── test_admin_tournament_creation.py
│       └── test_admin_invitation_codes.py
└── tournament_formats/
    ├── group_knockout/
    ├── head_to_head/
    └── individual_ranking/
```

#### 5. **Duplikációk Feloldása**
- Válaszd ki a kanonikus verziót (valószínűleg tests/e2e/)
- Töröld a tests/playwright/ duplikációkat
- Migráld a kanonikus verziót tests/e2e_frontend/-ba

#### 6. **tests/playwright/ Mappa Megszüntetése**
Ha minden teszt átkerült:
- tests/playwright/ → tests/.archive/playwright/
- Vagy teljes törlés

### C. HOSSZÚ TÁVON (Next Quarter)

#### 7. **tests/e2e/ Mappa Deprecation**
Miután minden teszt átkerült az új struktúrába:
- tests/e2e/ → tests/.archive/e2e_legacy/
- Update CI/CD pipelines
- Remove from pytest collection

#### 8. **Test Organization Documentation**
Teljes dokumentáció a teszt szervezésről:
- Mikor írjunk unit vs integration vs E2E tesztet?
- Hova kerüljenek az új tesztek?
- Hogyan írjunk contract-first UI teszteket?

**File:** `docs/TESTING_GUIDE.md`

---

## XIV. Kérdések a Tisztázáshoz

### 1. **Tudatos Döntés vagy Félbehagyott Refactor?**
- A user flow tesztek **TUDATOSAN** maradtak kint a refactorból?
- Vagy ez egy **félbehagyott migráció**?

### 2. **Mi a tests/e2e/ Mappa Jövője?**
- Deprecated és át kell helyezni mindent?
- Vagy párhuzamosan futnak az új struktúrával?

### 3. **Mi a tests/playwright/ Mappa Célja?**
- Miért van külön tests/playwright/ mappa?
- Miben különbözik a tests/e2e/-től?
- Deprecated?

### 4. **Hova Kerüljenek az Új User Flow Tesztek?**
- tests/e2e/?
- tests/e2e_frontend/user_flows/?
- tests/playwright/?

### 5. **Duplikációk Feloldása**
- Melyik verzió a kanonikus?
- Van-e különbség a tests/e2e/ vs tests/playwright/ verziók között?

---

## XV. Konklúzió

**Jelenlegi állapot:** ⚠️ **ÁTMENETI / RENDEZETLEN**

**Fő probléma:** A rendszer **legkritikusabb** UI tesztjei (user registration, onboarding, business workflows) **NINCSENEK** az új, refaktorált tesztstruktúrában.

**Impact:**
- ❌ Nincs világos pattern új tesztek írásakor
- ❌ Duplikációk maintenance burden-t okoznak
- ❌ Confusion arról, hogy melyik teszt mappa a "kanonikus"

**Ajánlás:**
1. **Immediate:** Dokumentáld a teszt struktúra policy-t
2. **Next Sprint:** Migráld a kritikus user flow teszteket
3. **Long-term:** Deprecate old test directories

---

**Készítette:** Claude Code (Sonnet 4.5)
**Dátum:** 2026-02-08
**Verzió:** 1.0
