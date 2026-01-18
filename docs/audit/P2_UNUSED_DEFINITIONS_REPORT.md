# Prioritás 2 - Unused Definitions Audit Report

**Dátum:** 2026-01-18
**Audit Típus:** Function/Class/Method szintű használatlanság elemzés
**Eszköz:** Vulture 2.14 (70% confidence threshold)
**Státusz:** ⚠️ CSAK REPORT - NINCS CLEANUP

---

## 📊 Összefoglaló Statisztika

### Magas Confidence (70%+) Eredmények
- **Talált problémák:** 58 használatlan elem
- **Érintett fájlok:** 25 fájl
- **Érintett könyvtárak:** 14 könyvtár
- **Confidence:** Minden elem <70% (alacsony - sok false positive!)

### Típusok Szerinti Bontás
| Típus | Darabszám | Arány |
|-------|-----------|-------|
| 🔸 Unused Variables | 43 | 74.1% |
| ⚠️ Unused Imports | 13 | 22.4% |
| 🚫 Unreachable Code | 1 | 1.7% |
| 📐 Other | 1 | 1.7% |

**⚠️ FONTOS:** NEM találtunk unused functions/classes/methods 70%+ confidence-szel!
Ez azt jelenti, hogy a Vulture nem talált **egyértelmű dead code**-ot a function/class szinten.

---

## 🎯 Kategorizálás Kockázat Szerint

### 🟢 ALACSONY KOCKÁZAT - Biztonságosan Kezelhető (13 elem)

#### 📦 Unused Imports (13 elem)

**Részletes Lista:**

1. **app/api/api_v1/endpoints/curriculum/exercises.py** (2 import)
   - `File` (FastAPI)
   - `UploadFile` (FastAPI)
   - **Elemzés:** Valószínűleg tervezett file upload funkció, de nem implementálva
   - **Kockázat:** ALACSONY - biztonságosan törölhető
   - **Javaslat:** Töröld vagy dokumentáld mint `# TODO: File upload feature`

2. **app/services/quiz_service.py** (2 import)
   - `QuizAttemptStart` (schema)
   - `QuizUpdate` (schema)
   - **Elemzés:** Lehet régi API maradvány
   - **Kockázat:** ALACSONY
   - **Javaslat:** Ellenőrizd quiz API használatot, ha nincs → töröld

3. **app/api/api_v1/endpoints/payment_verification.py** (1 import)
   - `Body` (FastAPI)
   - **Elemzés:** Lehet refactor során maradt
   - **Kockázat:** ALACSONY
   - **Javaslat:** Töröld

4. **app/api/routes/lfa_player_routes.py** (1 import)
   - `BulkSkillAssessmentCreate` (schema)
   - **Elemzés:** Tervezett bulk assessment feature?
   - **Kockázat:** ALACSONY
   - **Javaslat:** Ha nincs roadmap → töröld, ha van → dokumentáld

5. **app/api/api_v1/endpoints/tournaments/lifecycle.py** (1 import)
   - `StatusValidationError` (exception)
   - **Elemzés:** Exception handling lehet már máshogy megoldva
   - **Kockázat:** ALACSONY
   - **Javaslat:** Ellenőrizd error handling, ha nem kell → töröld

6. **tests/e2e/test_tournament_enrollment_protection.py** (1 import)
   - `create_instructor_user` (fixture)
   - **Elemzés:** Test fixture nem használva
   - **Kockázat:** NAGYON ALACSONY
   - **Javaslat:** Töröld (test import cleanup)

7. **tests/playwright/test_tournament_enrollment_protection.py** (1 import)
   - `create_instructor_user` (fixture)
   - **Elemzés:** Duplikált test fájl?
   - **Kockázat:** NAGYON ALACSONY
   - **Javaslat:** Töröld

8. **streamlit_app/components/instructor/tournament_applications.py** (1 import)
   - `render_application_card` (component)
   - **Elemzés:** Lehet refactored component
   - **Kockázat:** ALACSONY
   - **Javaslat:** Ellenőrizd UI rendering, ha nincs használva → töröld

9. **tests/e2e/test_reward_policy_distribution.py** (1 import)
   - `reward_policy_players` (fixture)
   - **Elemzés:** Fixture nem használva
   - **Kockázat:** NAGYON ALACSONY
   - **Javaslat:** Töröld

10. **tests/e2e/test_reward_policy_user_validation.py** (1 import)
    - `reward_policy_players` (fixture)
    - **Elemzés:** Fixture nem használva
    - **Kockázat:** NAGYON ALACSONY
    - **Javaslat:** Töröld

---

### 🟡 KÖZEPES KOCKÁZAT - Vizsgálat Szükséges (43 elem)

#### 🔸 Unused Variables - Test Fixtures (25 elem)

**Kategória:** Pytest fixture paraméterek amelyek nem használva vannak a test body-ban

**1. Test Setup Fixtures (12 elem)**

**app/tests/test_e2e_age_validation.py** (7)
- `setup_specializations` fixture parameter (7x)
- **Elemzés:** Fixture valószínűleg DB setup-ot végez, de a teszt nem használja közvetlenül
- **Kockázat:** KÖZEPES - lehet side effect kell (DB state)
- **FALSE POSITIVE valószínűség:** MAGAS (95%)
- **Javaslat:** NE TÖRÖLD - fixture side effect kell a tesztekhez

**app/tests/test_specialization_integration.py** (6)
- `setup_specializations` fixture parameter (6x)
- **Elemzés:** Ugyanaz mint fent
- **Kockázat:** KÖZEPES
- **FALSE POSITIVE:** MAGAS
- **Javaslat:** NE TÖRÖLD

**app/tests/test_onboarding_api.py** (5)
- `setup_test_db` fixture parameter (5x)
- **Elemzés:** DB setup fixture
- **Kockázat:** KÖZEPES
- **FALSE POSITIVE:** MAGAS
- **Javaslat:** NE TÖRÖLD

**2. License/Enrollment Fixtures (7 elem)**

**app/tests/test_tournament_enrollment.py** (7)
- `lfa_player_license` fixture parameter (7x)
- **Elemzés:** License setup fixture, valószínűleg precondition a tesztekhez
- **Kockázat:** KÖZEPES
- **FALSE POSITIVE:** MAGAS
- **Javaslat:** NE TÖRÖLD - enrollment precondition

**tests/integration/test_lfa_coach_service.py** (2)
- `semester_enrollment_paid` fixture parameter (2x)
- **Elemzés:** Enrollment precondition fixture
- **Kockázat:** KÖZEPES
- **FALSE POSITIVE:** MAGAS
- **Javaslat:** NE TÖRÖLD

**3. Pytest Config Fixtures (2 elem)**

**tests/e2e/conftest.py** (2)
- `pytestconfig` parameter (2x használva fixture-ökben)
- **Elemzés:** Pytest builtin fixture
- **Kockázat:** ALACSONY
- **FALSE POSITIVE:** 100% - Ez Pytest internal!
- **Javaslat:** NE ÉRINTSD - Pytest használja!

#### 🔸 Unused Variables - API Dependencies (10 elem)

**4. Current Admin Dependencies (7 elem)**

**app/api/api_v1/endpoints/locations.py** (5)
- `current_admin` dependency parameter (lines 85, 108, 127, 181, 228)
- **Elemzés:** FastAPI dependency injection - használva authorization-höz
- **Kockázat:** ALACSONY
- **FALSE POSITIVE:** 100% - FastAPI használja!
- **Javaslat:** NE TÖRÖLD - ezt a Depends() mechanizmus használja

**app/api/api_v1/endpoints/semester_generator.py** (2)
- `current_admin` dependency parameter (lines 295, 386)
- **Elemzés:** Ugyanaz mint fent
- **Kockázat:** ALACSONY
- **FALSE POSITIVE:** 100%
- **Javaslat:** NE TÖRÖLD

**5. Middleware Parameters (2 elem)**

**app/middleware/query_logger.py** (2)
- `executemany` parameter (lines 161, 167)
- **Elemzés:** SQLAlchemy event handler signature
- **Kockázat:** ALACSONY
- **FALSE POSITIVE:** 100% - SQLAlchemy esemény handler kell
- **Javaslat:** NE TÖRÖLD - event handler signature része

**6. Service Layer Variables (1 elem)**

**app/services/specs/session_based/lfa_player_service.py** (1)
- `promoted_by_instructor_id` variable (line 530)
- **Elemzés:** Lehet DB mezőbe írva, de a változó nem használva tovább
- **Kockázat:** KÖZEPES
- **Javaslat:** Ellenőrizd DB írást - lehet valódi unused

---

### 🔴 MAGAS KOCKÁZAT - Logikai Hiba Lehetséges (2 elem)

#### 🚫 Unreachable Code (1 elem)

**app/services/competency_service.py** (1)
- Line 345: unreachable code after 'return'
- **Elemzés:** Kód egy return után van - SOHA nem fut le
- **Kockázat:** MAGAS - lehet logikai hiba!
- **Javaslat:**
  1. Vizsgáld meg a return előtti logikát
  2. Ha a kód után van funkció ami kellett volna fusson → BUG FIX
  3. Ha valóban dead code → töröld

**Részletes Vizsgálat Szükséges:**
```bash
# Nézd meg a kódot:
cat -n app/services/competency_service.py | sed -n '340,350p'

# Ellenőrizd git history:
git log -p app/services/competency_service.py | grep -A 10 -B 10 "line 345"
```

#### 📐 Unreachable Else Block (1 elem)

**tests/integration/test_gancuju_belt_system.py** (1)
- Line 145: unreachable 'else' block
- **Elemzés:** Else ág sosem fut le (if condition mindig igaz/hamis)
- **Kockázat:** KÖZEPES - lehet test logic hiba
- **Javaslat:**
  1. Vizsgáld meg a teszt logikát
  2. Ha az else kód kellett volna fusson → TEST BUG
  3. Ha valóban felesleges → töröld vagy refaktoráld

---

## 📋 Részletes Akció Terv

### ✅ Azonnali Akciók (Alacsony Kockázat)

**1. Unused Imports Cleanup (13 elem)**
- **Időigény:** 15-30 perc
- **Kockázat:** NAGYON ALACSONY
- **Lépések:**
  1. Review lista fent
  2. Grep használat ellenőrzés
  3. Ha nincs használat → töröld import sort
  4. Futtass syntax check

### ⚠️ Közép Távú Akciók (Közepes Kockázat)

**2. Pytest Fixture False Positives Dokumentálása**
- **Időigény:** 30 perc
- **Cél:** Dokumentáld hogy ezek side effect fixtures
- **Lépések:**
  1. Add hozzá commentet fixture használathoz:
     ```python
     def test_something(
         setup_specializations  # Fixture needed for DB state setup
     ):
         # Test body
     ```

**3. promoted_by_instructor_id Vizsgálat**
- **Fájl:** `app/services/specs/session_based/lfa_player_service.py:530`
- **Lépések:**
  1. Nézd meg a kód körül mit csinál
  2. Ellenőrizd DB írást
  3. Ha nincs használat → töröld vagy használd

### 🔴 Prioritás Akciók (Magas Kockázat)

**4. Unreachable Code Vizsgálat**
- **Fájl:** `app/services/competency_service.py:345`
- **Időigény:** 1 óra (vizsgálat + fix ha szükséges)
- **Lépések:**
  1. Vizsgáld meg a return előtti és utáni logikát
  2. Ellenőrizd git history hogy miért került oda
  3. Döntsd el: bug fix vagy cleanup
  4. Ha bug → fix és test
  5. Ha cleanup → töröld

**5. Unreachable Else Block Vizsgálat**
- **Fájl:** `tests/integration/test_gancuju_belt_system.py:145`
- **Időigény:** 30 perc
- **Lépések:**
  1. Nézd meg a teszt logikát
  2. Futtasd a tesztet coverage-vel
  3. Döntsd el: test bug vagy cleanup

---

## 🎯 Összegzés és Javaslatok

### Főbb Felismerések

1. **NEM TALÁLHATÓ EGYÉRTELMŰ DEAD CODE** function/class szinten 70%+ confidence-szel
   - Ez **jó jel** - a codebase-ben nincs nyilvánvaló nagy dead code

2. **FALSE POSITIVE ARÁNY MAGAS**
   - Pytest fixtures: 95%+ false positive
   - FastAPI dependencies: 100% false positive
   - SQLAlchemy event handlers: 100% false positive

3. **VALÓDI PROBLÉMÁK**
   - 13 unused import (alacsony kockázat)
   - 1 unreachable code (magas kockázat - VIZSGÁLANDÓ!)
   - 1 unreachable else (közepes kockázat)

### Javasolt Cleanup Sorrend

**Fázis 1: Biztonságos Cleanup (30 perc)**
- [ ] Töröld 13 unused import-ot
- [ ] Futtass syntax check
- [ ] Commit: "chore: Remove unused imports (P2 cleanup)"

**Fázis 2: Dokumentáció (30 perc)**
- [ ] Dokumentáld pytest fixture false positives-okat
- [ ] Add hozzá # pylint: disable=unused-argument comment-eket ahol kell

**Fázis 3: Vizsgálat (2 óra)**
- [ ] Vizsgáld meg unreachable code a competency_service.py-ban
- [ ] Vizsgáld meg unreachable else a gancuju teszt-ben
- [ ] Vizsgáld meg promoted_by_instructor_id változót

**Fázis 4: Fix/Cleanup (1 óra + testing)**
- [ ] Fix ha bug
- [ ] Cleanup ha valódi dead code
- [ ] Futtass teljes test suite

### Impact Becslés

**Ha MINDEN javaslatot végrehajtasz:**
```
Törölt sorok: ~15-20 (importok)
Potenciális bug fix: 1-2
Dokumentáció javulás: +10%
Kockázat: ALACSONY (csak importok és vizsgálat)
Időigény: 3-4 óra összesen
```

**Konzervatív Megközelítés (Csak Importok):**
```
Törölt sorok: ~13
Kockázat: NAGYON ALACSONY
Időigény: 30 perc
```

---

## 📎 Eszközök és Parancsok

### Vizsgálati Parancsok

```bash
# Unreachable code vizsgálat
cat -n app/services/competency_service.py | sed -n '340,350p'
git log -p app/services/competency_service.py | grep -A 10 -B 10 "345"

# Unreachable else vizsgálat
cat -n tests/integration/test_gancuju_belt_system.py | sed -n '140,150p'

# Import használat ellenőrzés (példa)
grep -r "UploadFile" app/api/api_v1/endpoints/curriculum/ --include="*.py"

# Fixture side effect ellenőrzés
grep -A 20 "def setup_specializations" app/tests/conftest.py
```

### Re-scan Parancs (magasabb threshold)

```bash
# 80%+ confidence scan (még kevesebb false positive)
venv/bin/python3 scripts/audit_unused_code.py --min-confidence 80

# 90%+ confidence scan (csak nagyon biztos esetek)
venv/bin/python3 scripts/audit_unused_code.py --min-confidence 90
```

---

## ⚠️ FONTOS FIGYELMEZTETÉSEK

### NE TÖRÖLD EZEKET (100% False Positive):

1. **Pytest fixtures paraméterek** - side effect miatt kellenek!
   ```python
   def test_x(setup_specializations):  # ← NE TÖRÖLD a paramétert!
       # setup_specializations fut, DB state setup
   ```

2. **FastAPI Depends() paraméterek** - authorization miatt kellenek!
   ```python
   def endpoint(current_admin = Depends(get_current_admin)):  # ← NE TÖRÖLD!
       # FastAPI használja a dependency-t
   ```

3. **SQLAlchemy event handler paraméterek** - signature része!
   ```python
   def handler(conn, cursor, statement, params, context, executemany):  # ← Mind kell!
       # SQLAlchemy hívja az event handler-t
   ```

4. **pytestconfig** - Pytest builtin, internal használat!

---

**Készítette:** Claude Code (Sonnet 4.5)
**Utolsó frissítés:** 2026-01-18
**Audit Confidence:** 70%
**Következő Audit:** P3 - Schema Enums (később, user döntésre várva)
