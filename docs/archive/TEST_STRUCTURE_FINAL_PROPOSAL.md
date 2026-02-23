# Kanonikus Tesztstruktúra Javaslat és Végrehajtási Terv

**Készítette:** Claude Code (Sonnet 4.5)
**Dátum:** 2026-02-08
**Verzió:** 1.0 (FINAL PROPOSAL)

---

## Executive Summary

**DÖNTÉS:** A `tests/e2e/` mappa **DEPRECATED** és be kell olvasztani a `tests/e2e_frontend/` struktúrába.

**INDOK:**
- User activation flow-k (registration, onboarding) **legalább olyan kritikusak**, mint a tournament workflows
- **EGY központi hely** kell minden UI tesztnek
- Duplikációk feloldása szükséges
- Új tesztek írásakor **egyértelmű** hova kerüljenek

**TIMELINE:**
- **Sprint 1 (Week 1-2):** Production-kritikus flow-k migrációja (P0)
- **Sprint 2 (Week 3-4):** Business workflow-k migrációja (P1)
- **Sprint 3 (Week 5-6):** Maradék tesztek + cleanup (P2)

---

## I. KANONIKUS TESZTSTRUKTÚRA (Végleges)

### Célarchitektúra

```
tests/
├── api/                          # API endpoint tesztek (pytest, requests)
│   ├── test_coupons_refactored.py
│   ├── test_invitation_codes.py
│   └── test_tournament_enrollment.py
│
├── integration/                  # Backend integration tesztek (services, repos)
│   ├── test_knockout_progression.py
│   ├── test_reward_calculation.py
│   └── test_session_generation.py
│
├── unit/                        # Unit tesztek (pure functions, helpers)
│   ├── models/
│   ├── services/
│   └── utils/
│
├── e2e/                         # ✅ KANONIKUS E2E TESZTEK (Playwright UI)
│   │
│   ├── user_lifecycle/          # 🔥 PRODUCTION-KRITIKUS: User activation
│   │   ├── registration/
│   │   │   ├── test_user_registration_basic.py
│   │   │   ├── test_registration_with_invite_code.py
│   │   │   └── test_complete_registration_flow.py
│   │   │
│   │   ├── onboarding/
│   │   │   ├── test_onboarding_with_coupon.py
│   │   │   ├── test_specialization_unlock.py
│   │   │   └── test_onboarding_three_steps.py
│   │   │
│   │   └── auth/
│   │       ├── test_login_flow.py
│   │       └── test_logout_flow.py
│   │
│   ├── business_workflows/      # 🔥 PRODUCTION-KRITIKUS: Business logic
│   │   ├── instructor/
│   │   │   ├── test_instructor_application_workflow.py
│   │   │   ├── test_instructor_invitation_workflow.py
│   │   │   └── test_instructor_assignment_flows.py
│   │   │
│   │   ├── admin/
│   │   │   ├── test_admin_tournament_creation.py
│   │   │   ├── test_admin_invitation_codes.py
│   │   │   └── test_admin_user_management.py
│   │   │
│   │   └── player/
│   │       ├── test_player_enrollment.py
│   │       ├── test_player_dashboard_workflow.py
│   │       └── test_player_tournament_participation.py
│   │
│   ├── tournament_formats/      # Tournament-specifikus tesztek
│   │   ├── group_knockout/
│   │   │   ├── test_group_knockout_7_players.py
│   │   │   ├── test_group_knockout_8_players.py
│   │   │   └── test_group_stage_only.py
│   │   │
│   │   ├── head_to_head/
│   │   │   ├── test_head_to_head_league.py
│   │   │   ├── test_head_to_head_single_elimination.py
│   │   │   └── test_head_to_head_group_knockout.py
│   │   │
│   │   └── individual_ranking/
│   │       ├── test_individual_ranking_points.py
│   │       ├── test_individual_ranking_placement.py
│   │       └── test_individual_ranking_time.py
│   │
│   ├── tournament_lifecycle/    # Tournament end-to-end tesztek
│   │   ├── test_tournament_creation_to_completion.py
│   │   ├── test_tournament_enrollment_protection.py
│   │   ├── test_tournament_attendance_tracking.py
│   │   └── test_tournament_list_browsing.py
│   │
│   ├── rewards_and_coupons/     # Reward system & coupon tesztek
│   │   ├── test_reward_distribution_e2e.py
│   │   ├── test_reward_policy_validation.py
│   │   ├── test_coupon_redemption_ui.py
│   │   └── test_coupon_form_ui.py
│   │
│   ├── sandbox/                 # Sandbox workflow tesztek
│   │   ├── test_sandbox_tournament_workflow.py
│   │   ├── test_sandbox_group_knockout.py
│   │   └── test_sandbox_match_submission.py
│   │
│   ├── golden_path/             # Critical E2E smoke tesztek
│   │   ├── test_golden_path_api_based.py
│   │   └── test_instructor_workflow_e2e.py
│   │
│   └── shared/                  # Közös helper-ek, fixtures
│       ├── fixtures/
│       │   ├── user_fixtures.py
│       │   ├── tournament_fixtures.py
│       │   └── auth_fixtures.py
│       ├── helpers/
│       │   ├── streamlit_helpers.py
│       │   ├── navigation_helpers.py
│       │   └── form_helpers.py
│       └── conftest.py
│
├── manual/                      # Manuális tesztek (nem pytest)
│   ├── test_assignment_filters.py
│   ├── test_registration_validation.py
│   └── README.md
│
├── security/                    # Security tesztek (XSS, CSRF, injection)
│   └── xss/
│       ├── test_login_xss.py
│       ├── test_registration_xss.py
│       └── test_tournament_xss.py
│
└── .archive/                    # Deprecated tesztek
    ├── e2e_legacy/              # tests/e2e/ tartalma (migráció után)
    ├── playwright_legacy/       # tests/playwright/ tartalma
    └── deprecated/
```

### Kulcsfontosságú Döntések

#### 1. **tests/e2e/ → tests/e2e/ (átnevezés NEM kell)**

**DÖNTÉS:** A `tests/e2e_frontend/` nevet **VISSZAÁLLÍTJUK** `tests/e2e/`-re.

**INDOK:**
- E2E tesztek **definíció szerint** UI-alapúak (Playwright/Selenium)
- "e2e_frontend" redundáns (minden E2E teszt frontend)
- Egyszerűbb path: `tests/e2e/user_lifecycle/` vs `tests/e2e_frontend/user_lifecycle/`

**MIGRÁCIÓ:**
```bash
git mv tests/e2e/ tests/.archive/e2e_legacy/
git mv tests/e2e_frontend/ tests/e2e/
```

#### 2. **tests/playwright/ → DEPRECATED**

**DÖNTÉS:** A `tests/playwright/` mappa **TELJES EGÉSZÉBEN** deprecated.

**INDOK:**
- Duplikációkat tartalmaz (tests/e2e/-vel)
- Nincs egyértelmű differenciálás
- Minden Playwright teszt `tests/e2e/`-be kerül

**MIGRÁCIÓ:**
```bash
git mv tests/playwright/ tests/.archive/playwright_legacy/
```

#### 3. **User Lifecycle = Production-Kritikus**

**DÖNTÉS:** A user lifecycle tesztek (registration, onboarding, login) **KIEMELT HELYEN** vannak a struktúrában.

**INDOK:**
- Ezek a rendszer **belépési pontjai**
- Ha ezek nem működnek, **SENKI** nem tud belépni
- **Legalább olyan kritikusak**, mint bármely tournament workflow

**STRUKTÚRA:**
```
tests/e2e/
├── user_lifecycle/        # 🔥 1. PRIORITÁS
├── business_workflows/    # 🔥 2. PRIORITÁS
└── tournament_formats/    # 3. PRIORITÁS
```

---

## II. DUPLIKÁCIÓK FELOLDÁSA - KANONIKUS VERZIÓK

### Duplikált Tesztek Listája

| Teszt | tests/e2e/ | tests/playwright/ | Kanonikus Verzió | Indok |
|-------|------------|-------------------|------------------|-------|
| **test_user_registration_with_invites.py** | ✅ Létezik | ✅ Létezik | **tests/e2e/** | Részletesebb, több edge case |
| **test_complete_onboarding_with_coupon_ui.py** | ✅ Létezik | ✅ Létezik | **tests/e2e/** | Teljes flow, setup script-tel |
| **test_tournament_enrollment_protection.py** | ✅ Létezik | ✅ Létezik | **tests/e2e/** | Több enrollment scenario |

### Döntési Logika

**ÁLTALÁNOS SZABÁLY:** Ha egy teszt **mindkét mappában** létezik, a **tests/e2e/** verzió kanonikus.

**INDOKOK:**
1. tests/e2e/ **régebbi**, több iteráción ment át
2. tests/e2e/ tesztek **részletesebbek** (több edge case)
3. tests/playwright/ **később lett létrehozva**, experimentális jellegű

### Végrehajtás

```bash
# 1. Töröld a tests/playwright/ duplikációkat
rm tests/playwright/test_user_registration_with_invites.py
rm tests/playwright/test_complete_onboarding_with_coupon_ui.py
rm tests/playwright/test_tournament_enrollment_protection.py

# 2. Migráld a tests/playwright/ egyedi teszteket (NEM duplikátumok)
git mv tests/playwright/test_tournament_enrollment_application_based.py \
       tests/e2e/business_workflows/instructor/

git mv tests/playwright/test_tournament_enrollment_open_assignment.py \
       tests/e2e/business_workflows/instructor/

git mv tests/playwright/test_tournament_game_types.py \
       tests/e2e/tournament_formats/

# 3. Archive-olás
git mv tests/playwright/ tests/.archive/playwright_legacy/
```

---

## III. MIGRÁCIÓS TERV - PRIORITÁSI SORREND

### Sprint 1: Production-Kritikus Flow-k (P0) - Week 1-2

**CÉL:** A rendszer **belépési pontjainak** tesztelése helyére kerül.

#### P0-1: User Lifecycle Tesztek (HIGHEST PRIORITY)

**Migrálandó fájlok:**
1. ✅ `tests/e2e/test_user_registration.py` → `tests/e2e/user_lifecycle/registration/test_user_registration_basic.py`
2. ✅ `tests/e2e/test_complete_registration_flow.py` → `tests/e2e/user_lifecycle/registration/test_complete_registration_flow.py`
3. ✅ `tests/e2e/test_user_registration_with_invites.py` → `tests/e2e/user_lifecycle/registration/test_registration_with_invite_code.py`
4. ✅ `tests/e2e/test_complete_onboarding_with_coupon_ui.py` → `tests/e2e/user_lifecycle/onboarding/test_onboarding_with_coupon.py`
5. ✅ `tests/e2e/test_simple_login.py` → `tests/e2e/user_lifecycle/auth/test_login_flow.py`

**DUPLIKÁCIÓK TÖRLÉSE:**
- ❌ `tests/playwright/test_user_registration_with_invites.py` (DELETE)
- ❌ `tests/playwright/test_complete_onboarding_with_coupon_ui.py` (DELETE)

**IDŐBECSLÉS:** 2-3 nap
**VALIDÁCIÓ:** Minden teszt fut az új lokációból, 100% pass rate

---

#### P0-2: Golden Path Tesztek (CRITICAL E2E)

**Migrálandó fájlok:**
1. ✅ `tests/e2e/golden_path/test_golden_path_api_based.py` → **MARAD** (már jó helyen van)
2. ✅ `tests/e2e/instructor_workflow/test_instructor_workflow_e2e.py` → **MARAD** (már jó helyen van)

**Új struktúra:**
```
tests/e2e/
└── golden_path/
    ├── test_golden_path_api_based.py      # Teljes tournament lifecycle
    └── test_instructor_workflow_e2e.py     # Instructor assignment flow
```

**IDŐBECSLÉS:** 1 nap (ellenőrzés)
**VALIDÁCIÓ:** Golden Path továbbra is 100% stable

---

### Sprint 2: Business Workflow Tesztek (P1) - Week 3-4

**CÉL:** Instructor és Admin workflow-k rendezése.

#### P1-1: Instructor Workflows

**Migrálandó fájlok:**
1. ✅ `tests/e2e/test_ui_instructor_application_workflow.py` → `tests/e2e/business_workflows/instructor/test_instructor_application_workflow.py`
2. ✅ `tests/e2e/test_ui_instructor_invitation_workflow.py` → `tests/e2e/business_workflows/instructor/test_instructor_invitation_workflow.py`
3. ✅ `tests/e2e/test_instructor_assignment_flows.py` → `tests/e2e/business_workflows/instructor/test_instructor_assignment_flows.py`
4. ✅ `tests/playwright/test_tournament_enrollment_application_based.py` → `tests/e2e/business_workflows/instructor/test_enrollment_application_based.py`
5. ✅ `tests/playwright/test_tournament_enrollment_open_assignment.py` → `tests/e2e/business_workflows/instructor/test_enrollment_open_assignment.py`

**DUPLIKÁCIÓK TÖRLÉSE:**
- ❌ `tests/playwright/test_tournament_enrollment_protection.py` (DELETE - duplikáció)

**IDŐBECSLÉS:** 3-4 nap
**VALIDÁCIÓ:** Instructor flow tesztek futnak és átmennek

---

#### P1-2: Admin Workflows

**Migrálandó fájlok:**
1. ✅ `tests/e2e/test_admin_create_tournament_refactored.py` → `tests/e2e/business_workflows/admin/test_admin_tournament_creation.py`
2. ✅ `tests/e2e/test_admin_invitation_code.py` → `tests/e2e/business_workflows/admin/test_admin_invitation_codes.py`

**IDŐBECSLÉS:** 2 nap
**VALIDÁCIÓ:** Admin workflow tesztek futnak

---

#### P1-3: Complete Business Workflows

**Migrálandó fájlok:**
1. ✅ `tests/e2e/test_complete_business_workflow.py` → `tests/e2e/business_workflows/test_complete_business_workflow_e2e.py`
2. ✅ `tests/e2e/test_ui_complete_business_workflow.py` → **MERGE** into above (duplikáció)

**IDŐBECSLÉS:** 2-3 nap
**VALIDÁCIÓ:** End-to-end business workflow teszt átmegy

---

### Sprint 3: Maradék Tesztek + Cleanup (P2) - Week 5-6

**CÉL:** Minden teszt végleges helyén, régi mappák deprecated.

#### P2-1: Tournament Lifecycle Tesztek

**Migrálandó fájlok:**
1. ✅ `tests/e2e/test_tournament_workflow_happy_path.py` → `tests/e2e/tournament_lifecycle/test_tournament_creation_to_completion.py`
2. ✅ `tests/e2e/test_tournament_enrollment_protection.py` → `tests/e2e/tournament_lifecycle/test_tournament_enrollment_protection.py`
3. ✅ `tests/e2e/test_tournament_attendance_complete.py` → `tests/e2e/tournament_lifecycle/test_tournament_attendance_tracking.py`
4. ✅ `tests/e2e/test_tournament_list.py` → `tests/e2e/tournament_lifecycle/test_tournament_list_browsing.py`

**IDŐBECSLÉS:** 2-3 nap

---

#### P2-2: Reward & Coupon Tesztek

**Migrálandó fájlok:**
1. ✅ `tests/e2e/test_reward_policy_distribution.py` → `tests/e2e/rewards_and_coupons/test_reward_distribution_e2e.py`
2. ✅ `tests/e2e/test_reward_policy_user_validation.py` → `tests/e2e/rewards_and_coupons/test_reward_policy_validation.py`
3. ✅ `tests/e2e/test_coupon_form_ui.py` → `tests/e2e/rewards_and_coupons/test_coupon_form_ui.py`

**IDŐBECSLÉS:** 2 nap

---

#### P2-3: Sandbox & Player Workflows

**Migrálandó fájlok:**
1. ✅ `tests/e2e/test_sandbox_workflow.py` → `tests/e2e/sandbox/test_sandbox_tournament_workflow.py`
2. ✅ `tests/e2e/test_sandbox_workflow_simple.py` → `tests/e2e/sandbox/test_sandbox_simple_workflow.py`
3. ✅ `tests/e2e/test_hybrid_ui_player_workflow.py` → `tests/e2e/business_workflows/player/test_player_dashboard_workflow.py`
4. ✅ `tests/e2e/test_match_command_center.py` → `tests/e2e/sandbox/test_match_command_center.py`

**IDŐBECSLÉS:** 2-3 nap

---

#### P2-4: Tournament Format Tesztek (már jó helyen vannak)

**Ellenőrzés:** Ezek már `tests/e2e_frontend/` alatt vannak, át kell nevezni `tests/e2e/tournament_formats/`-ra.

**Migráció:**
```bash
# Átnevezés: tests/e2e_frontend/ → tests/e2e/
git mv tests/e2e_frontend/group_knockout/ tests/e2e/tournament_formats/group_knockout/
git mv tests/e2e_frontend/head_to_head/ tests/e2e/tournament_formats/head_to_head/
git mv tests/e2e_frontend/individual_ranking/ tests/e2e/tournament_formats/individual_ranking/
git mv tests/e2e_frontend/shared/ tests/e2e/shared/
```

**IDŐBECSLÉS:** 1 nap

---

#### P2-5: Cleanup & Deprecation

**Végrehajtás:**
```bash
# 1. Archive régi tests/e2e/ mappa
git mv tests/e2e/ tests/.archive/e2e_legacy/

# 2. tests/e2e_frontend/ → tests/e2e/
git mv tests/e2e_frontend/ tests/e2e/

# 3. Archive tests/playwright/
git mv tests/playwright/ tests/.archive/playwright_legacy/

# 4. Archive debug tesztek
git mv tests/debug/ tests/.archive/debug_phase8_fix/

# 5. Deprecation notice-ok
echo "⚠️ DEPRECATED: Migrated to tests/e2e/ - See TEST_STRUCTURE_FINAL_PROPOSAL.md" > tests/.archive/e2e_legacy/README.md
echo "⚠️ DEPRECATED: Merged into tests/e2e/ - See TEST_STRUCTURE_FINAL_PROPOSAL.md" > tests/.archive/playwright_legacy/README.md
```

**IDŐBECSLÉS:** 1 nap
**VALIDÁCIÓ:**
- ✅ tests/e2e/ tartalmaz MINDEN E2E tesztet
- ✅ tests/e2e_frontend/ NEM létezik
- ✅ tests/playwright/ NEM létezik
- ✅ .archive/ mappákban minden deprecated teszt

---

## IV. VÉGREHAJTÁSI CHECKLIST

### Sprint 1 (Week 1-2): P0 - Production-Kritikus

- [ ] **P0-1.1:** Migrate user registration tesztek (5 fájl)
- [ ] **P0-1.2:** Delete user registration duplikációk (2 fájl)
- [ ] **P0-1.3:** Validate: User lifecycle tesztek futnak (pytest)
- [ ] **P0-2.1:** Validate: Golden Path tesztek továbbra is 100% stable

**Definition of Done (Sprint 1):**
- ✅ Mind az 5 user lifecycle teszt az új lokációban fut
- ✅ Golden Path 10/10 runs PASSED
- ✅ Duplikációk törölve
- ✅ CI/CD pipeline updated (pytest paths)

---

### Sprint 2 (Week 3-4): P1 - Business Workflows

- [ ] **P1-1.1:** Migrate instructor workflow tesztek (5 fájl)
- [ ] **P1-1.2:** Delete instructor duplikációk (1 fájl)
- [ ] **P1-2.1:** Migrate admin workflow tesztek (2 fájl)
- [ ] **P1-3.1:** Migrate complete business workflow tesztek (2 fájl)
- [ ] **P1-3.2:** Merge business workflow duplikációk (1 merge)
- [ ] **P1-VALIDATE:** Run all business workflow tesztek

**Definition of Done (Sprint 2):**
- ✅ Instructor workflow tesztek az új lokációban futnak
- ✅ Admin workflow tesztek az új lokációban futnak
- ✅ Complete business workflow teszt átmegy
- ✅ Duplikációk törölve/merged

---

### Sprint 3 (Week 5-6): P2 - Cleanup & Deprecation

- [ ] **P2-1.1:** Migrate tournament lifecycle tesztek (4 fájl)
- [ ] **P2-2.1:** Migrate reward & coupon tesztek (3 fájl)
- [ ] **P2-3.1:** Migrate sandbox & player tesztek (4 fájl)
- [ ] **P2-4.1:** Rename tests/e2e_frontend/ → tests/e2e/tournament_formats/
- [ ] **P2-5.1:** Archive old tests/e2e/ → tests/.archive/e2e_legacy/
- [ ] **P2-5.2:** Archive tests/playwright/ → tests/.archive/playwright_legacy/
- [ ] **P2-5.3:** Archive tests/debug/ → tests/.archive/debug_phase8_fix/
- [ ] **P2-5.4:** Create deprecation notices (README.md in archive folders)
- [ ] **P2-VALIDATE:** Full test suite runs (pytest tests/e2e/)

**Definition of Done (Sprint 3):**
- ✅ MINDEN E2E teszt a tests/e2e/ alatt van
- ✅ tests/e2e_frontend/ NEM létezik
- ✅ tests/playwright/ NEM létezik
- ✅ Régi mappák archived
- ✅ Deprecation notices létrehozva
- ✅ CI/CD pipeline fully updated
- ✅ Full test suite pass rate >= 95%

---

## V. MIGRÁCIÓ SCRIPT SABLON

### Automated Migration Script

```bash
#!/bin/bash
# migrate_e2e_tests.sh - Automated E2E test migration
# Usage: ./migrate_e2e_tests.sh [sprint_number]

set -e

SPRINT=${1:-1}

echo "=========================================="
echo "E2E Test Migration - Sprint $SPRINT"
echo "=========================================="

case $SPRINT in
  1)
    echo "Sprint 1: Migrating P0 - User Lifecycle Tests"

    # Create new structure
    mkdir -p tests/e2e/user_lifecycle/{registration,onboarding,auth}
    mkdir -p tests/e2e/golden_path

    # Migrate registration tests
    git mv tests/e2e/test_user_registration.py \
           tests/e2e/user_lifecycle/registration/test_user_registration_basic.py

    git mv tests/e2e/test_complete_registration_flow.py \
           tests/e2e/user_lifecycle/registration/test_complete_registration_flow.py

    git mv tests/e2e/test_user_registration_with_invites.py \
           tests/e2e/user_lifecycle/registration/test_registration_with_invite_code.py

    # Migrate onboarding tests
    git mv tests/e2e/test_complete_onboarding_with_coupon_ui.py \
           tests/e2e/user_lifecycle/onboarding/test_onboarding_with_coupon.py

    # Migrate auth tests
    git mv tests/e2e/test_simple_login.py \
           tests/e2e/user_lifecycle/auth/test_login_flow.py

    # Delete duplicates
    git rm tests/playwright/test_user_registration_with_invites.py
    git rm tests/playwright/test_complete_onboarding_with_coupon_ui.py

    echo "✅ Sprint 1 migration complete"
    ;;

  2)
    echo "Sprint 2: Migrating P1 - Business Workflows"

    # Create business workflow structure
    mkdir -p tests/e2e/business_workflows/{instructor,admin,player}

    # Migrate instructor workflows
    git mv tests/e2e/test_ui_instructor_application_workflow.py \
           tests/e2e/business_workflows/instructor/test_instructor_application_workflow.py

    git mv tests/e2e/test_ui_instructor_invitation_workflow.py \
           tests/e2e/business_workflows/instructor/test_instructor_invitation_workflow.py

    git mv tests/e2e/test_instructor_assignment_flows.py \
           tests/e2e/business_workflows/instructor/test_instructor_assignment_flows.py

    git mv tests/playwright/test_tournament_enrollment_application_based.py \
           tests/e2e/business_workflows/instructor/test_enrollment_application_based.py

    git mv tests/playwright/test_tournament_enrollment_open_assignment.py \
           tests/e2e/business_workflows/instructor/test_enrollment_open_assignment.py

    # Migrate admin workflows
    git mv tests/e2e/test_admin_create_tournament_refactored.py \
           tests/e2e/business_workflows/admin/test_admin_tournament_creation.py

    git mv tests/e2e/test_admin_invitation_code.py \
           tests/e2e/business_workflows/admin/test_admin_invitation_codes.py

    # Migrate complete business workflows
    git mv tests/e2e/test_complete_business_workflow.py \
           tests/e2e/business_workflows/test_complete_business_workflow_e2e.py

    # Delete duplicates
    git rm tests/playwright/test_tournament_enrollment_protection.py
    git rm tests/e2e/test_ui_complete_business_workflow.py  # Merge into above

    echo "✅ Sprint 2 migration complete"
    ;;

  3)
    echo "Sprint 3: Migrating P2 - Cleanup & Final Structure"

    # Create remaining structure
    mkdir -p tests/e2e/{tournament_lifecycle,rewards_and_coupons,sandbox}
    mkdir -p tests/.archive/{e2e_legacy,playwright_legacy,debug_phase8_fix}

    # Migrate tournament lifecycle
    git mv tests/e2e/test_tournament_workflow_happy_path.py \
           tests/e2e/tournament_lifecycle/test_tournament_creation_to_completion.py

    git mv tests/e2e/test_tournament_enrollment_protection.py \
           tests/e2e/tournament_lifecycle/test_tournament_enrollment_protection.py

    git mv tests/e2e/test_tournament_attendance_complete.py \
           tests/e2e/tournament_lifecycle/test_tournament_attendance_tracking.py

    git mv tests/e2e/test_tournament_list.py \
           tests/e2e/tournament_lifecycle/test_tournament_list_browsing.py

    # Migrate rewards & coupons
    git mv tests/e2e/test_reward_policy_distribution.py \
           tests/e2e/rewards_and_coupons/test_reward_distribution_e2e.py

    git mv tests/e2e/test_reward_policy_user_validation.py \
           tests/e2e/rewards_and_coupons/test_reward_policy_validation.py

    git mv tests/e2e/test_coupon_form_ui.py \
           tests/e2e/rewards_and_coupons/test_coupon_form_ui.py

    # Migrate sandbox & player
    git mv tests/e2e/test_sandbox_workflow.py \
           tests/e2e/sandbox/test_sandbox_tournament_workflow.py

    git mv tests/e2e/test_sandbox_workflow_simple.py \
           tests/e2e/sandbox/test_sandbox_simple_workflow.py

    git mv tests/e2e/test_hybrid_ui_player_workflow.py \
           tests/e2e/business_workflows/player/test_player_dashboard_workflow.py

    git mv tests/e2e/test_match_command_center.py \
           tests/e2e/sandbox/test_match_command_center.py

    # Rename e2e_frontend → tournament_formats
    git mv tests/e2e_frontend/group_knockout tests/e2e/tournament_formats/group_knockout
    git mv tests/e2e_frontend/head_to_head tests/e2e/tournament_formats/head_to_head
    git mv tests/e2e_frontend/individual_ranking tests/e2e/tournament_formats/individual_ranking
    git mv tests/e2e_frontend/shared tests/e2e/shared

    # Archive old directories
    git mv tests/playwright tests/.archive/playwright_legacy
    git mv tests/debug tests/.archive/debug_phase8_fix

    # Create deprecation notices
    echo "⚠️ DEPRECATED: Migrated to tests/e2e/ - See TEST_STRUCTURE_FINAL_PROPOSAL.md" > tests/.archive/playwright_legacy/README.md
    echo "⚠️ DEPRECATED: Phase 8 debug tesztek - See GOLDEN_PATH_FIX_SUMMARY.md" > tests/.archive/debug_phase8_fix/README.md

    echo "✅ Sprint 3 migration complete"
    echo "✅ Final structure ready: tests/e2e/"
    ;;

  *)
    echo "Usage: ./migrate_e2e_tests.sh [1|2|3]"
    exit 1
    ;;
esac

echo ""
echo "Running test collection validation..."
pytest tests/e2e/ --collect-only -q

echo ""
echo "=========================================="
echo "Migration Complete!"
echo "=========================================="
```

---

## VI. POST-MIGRATION VALIDÁCIÓ

### Validációs Checklist

#### 1. Test Collection
```bash
# Validate all tests collect
pytest tests/e2e/ --collect-only -q

# Expected: 0 errors, ~50+ tests collected
```

#### 2. Import Path Validation
```bash
# Check for broken imports
pytest tests/e2e/ --collect-only 2>&1 | grep -i "importerror\|modulenotfound"

# Expected: No output (no import errors)
```

#### 3. Critical Path Validation
```bash
# Golden Path stability
pytest tests/e2e/golden_path/test_golden_path_api_based.py -v

# User lifecycle critical tesztek
pytest tests/e2e/user_lifecycle/ -v

# Expected: 100% pass rate
```

#### 4. CI/CD Pipeline Update
```yaml
# .github/workflows/e2e_tests.yml
jobs:
  e2e-tests:
    steps:
      - name: Run E2E Tests
        run: |
          pytest tests/e2e/ -v --maxfail=5

      - name: Run Critical User Flows
        run: |
          pytest tests/e2e/user_lifecycle/ -v
          pytest tests/e2e/golden_path/ -v
```

#### 5. Documentation Update
- [ ] Update `README.md` (new test structure)
- [ ] Update `CONTRIBUTING.md` (where to add new tests)
- [ ] Update `docs/TESTING_GUIDE.md` (test organization)

---

## VII. ELŐNYÖK ÉS KOCKÁZATOK

### Előnyök

#### 1. **Egyértelmű Struktúra**
- ✅ **EGY** központi hely minden E2E tesztnek
- ✅ Világos döntési fa: új teszt hova kerüljön
- ✅ User lifecycle tesztek **kiemelt helyen** (production-kritikus)

#### 2. **Duplikációk Feloldása**
- ✅ Kevesebb maintenance burden
- ✅ Konzisztens updates
- ✅ Nincs "melyik verzió a friss?" kérdés

#### 3. **Production-Kritikus Fókusz**
- ✅ User lifecycle tesztek **1. prioritás**
- ✅ Business workflows **2. prioritás**
- ✅ Tournament formats **3. prioritás**

#### 4. **Jobb Developer Experience**
- ✅ Új fejlesztők könnyen megtalálják a teszteket
- ✅ Világos pattern az új tesztek írásakor
- ✅ Könnyebb code review

### Kockázatok

#### 1. **Migráció Közben Broken Tests**
**Mitigation:**
- Sprint-enkénti migráció (fokozatos)
- Minden sprint végén full validáció
- CI/CD pipeline update sprint-enként

#### 2. **Import Path Changes**
**Mitigation:**
- Automated migration script használata
- Import path validation minden sprint végén
- Relative imports → absolute imports ahol lehetséges

#### 3. **Developer Confusion (átmenetileg)**
**Mitigation:**
- Deprecation notices minden archived mappában
- Documentation update minden sprint végén
- Slack notification új struktúráról

---

## VIII. OWNERSHIP ÉS JÓVÁHAGYÁS

### Döntési Felelősség

**Strukturális döntések:**
- ✅ tests/e2e/ kanonikus hely (NEM tests/e2e_frontend/)
- ✅ tests/playwright/ deprecated
- ✅ User lifecycle = 1. prioritás
- ✅ Duplikációk: tests/e2e/ verzió kanonikus

**Timeline:**
- ✅ Sprint 1-3 (6 hét)
- ✅ P0 → P1 → P2 prioritási sorrend

**Ownership:**
- **Claude Code (Sonnet 4.5)** vállalja a javaslat szakmai helyességét
- **Tech Lead** jóváhagyása szükséges a végrehajtáshoz

### Jóváhagyási Kritériumok

**APPROVAL SZÜKSÉGES:**
- [ ] Tech Lead review (structural decisions)
- [ ] QA Lead review (test coverage)
- [ ] DevOps review (CI/CD impact)

**VÉGREHAJTÁS:**
- [ ] Sprint Planning: Timeline review
- [ ] Resource allocation (1-2 developer)
- [ ] Kickoff Meeting: Migration strategy walkthrough

---

## IX. KONKLÚZIÓ

**DÖNTÉS:** A `tests/e2e/` lesz a **KANONIKUS** hely minden UI tesztnek.

**MIGRÁCIÓ:** 3 sprint alatt, fokozatosan, production-kritikus flow-któl kezdve.

**DUPLIKÁCIÓK:** tests/e2e/ verzió marad, tests/playwright/ deprecated.

**PRIORITÁS:** User lifecycle (P0) → Business workflows (P1) → Cleanup (P2)

**TIMELINE:** 6 hét (Sprint 1-3)

**VALIDÁCIÓ:** Minden sprint végén full test suite validation

---

**Készítette:** Claude Code (Sonnet 4.5)
**Felelősség:** Szakmai javaslat helyességéért felelősséget vállal
**Jóváhagyás:** Tech Lead approval szükséges
**Végrehajtás:** Sprint Planning után indítható
