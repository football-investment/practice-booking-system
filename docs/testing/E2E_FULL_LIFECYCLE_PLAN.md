# 🎯 E2E Testing - Teljes Tournament Lifecycle Implementációs Terv

**Cél:** A teljes tournament workflow E2E lefedettése, elejétől a végéig, összefüggő folyamatként.

**Időráfordítás:** Nem szempont - a teljes bizonyosság a cél.

---

## 📋 Implementációs Stratégia

### Két Megközelítés Párhuzamosan

**1. Izolált Phase Tesztek** (Building Blocks)
- Minden phase külön tesztelhető
- Gyors feedback loop
- Könnyebb debuggolás
- ~15-20 teszt

**2. Teljes Lifecycle Integráció Teszt** (Golden Path)
- Egyetlen hosszú teszt: regisztrációtól lezárásig
- Validálja a teljes összefüggő folyamatot
- **EZ A LEGFONTOSABB TESZT**
- 1 komplex teszt

---

## 🏗️ PHASE 1: User Lifecycle

### Tesztek (Prioritási Sorrend)

#### 1.1 Admin Creates Instructor User
**Fájl:** `tests/e2e/test_user_lifecycle.py`

```python
@pytest.mark.e2e
@pytest.mark.user_lifecycle
def test_admin_can_create_instructor_user(page: Page, admin_token: str):
    """
    E2E: Admin creates a new instructor user via UI.

    Flow:
    1. Admin login
    2. Navigate to Admin Dashboard → Users
    3. Click "Create User"
    4. Fill form:
       - Email: test_instructor_{timestamp}@test.com
       - Name: Test Instructor
       - Role: INSTRUCTOR
       - Date of Birth
    5. Submit
    6. Verify: User appears in user list
    7. Verify: User can login with generated credentials
    8. Cleanup: Delete user
    """
```

**Előkészület szükséges:**
- Fel kell térképezni az Admin Dashboard user management UI-t
- Azonosítani kell a form mezőket és selector-okat
- Meg kell érteni a credential generation flow-t (email? manual password?)

**Becsült idő:** 2-3 óra (UI felfedezés + implementáció)

---

#### 1.2 Admin Creates Student User with Specialization
**Fájl:** `tests/e2e/test_user_lifecycle.py`

```python
@pytest.mark.e2e
@pytest.mark.user_lifecycle
def test_admin_can_create_student_with_specialization(page: Page, admin_token: str):
    """
    E2E: Admin creates a student user with specialization.

    Flow:
    1. Admin login
    2. Navigate to Users
    3. Create Student user
    4. Assign specialization (GOALKEEPER)
    5. Verify user appears in list with correct specialization
    6. Verify student can login
    7. Cleanup
    """
```

**Becsült idő:** 1-2 óra (hasonló az instructor-hoz)

---

#### 1.3 Student Onboarding Flow (If Exists)
**Fájl:** `tests/e2e/test_user_lifecycle.py`

```python
@pytest.mark.e2e
@pytest.mark.user_lifecycle
def test_student_completes_onboarding(page: Page):
    """
    E2E: New student completes onboarding process.

    Flow (ha van ilyen):
    1. Student first login
    2. Onboarding wizard appears
    3. Student fills profile info
    4. Student selects specialization (if not admin-assigned)
    5. Onboarding complete
    6. Student sees dashboard
    """
```

**KÉRDÉS:** Van-e onboarding flow? Ha nincs, skip.

**Becsült idő:** 1-2 óra (ha van ilyen flow)

---

**Phase 1 Össz becsült idő:** 4-7 óra

---

## 🏗️ PHASE 2: Admin Tournament Creation

### Tesztek

#### 2.1 Admin Creates Tournament Semester
**Fájl:** `tests/e2e/test_tournament_admin_setup.py`

```python
@pytest.mark.e2e
@pytest.mark.tournament_admin
def test_admin_can_create_tournament_semester(page: Page, admin_token: str):
    """
    E2E: Admin creates a new tournament semester.

    Flow:
    1. Admin login
    2. Navigate to Admin Dashboard → Tournaments
    3. Click "Create Tournament Semester"
    4. Fill form:
       - Name: "Test Tournament Spring 2024"
       - Specialization: GOALKEEPER
       - Start Date: today
       - End Date: today + 90 days
       - is_active: True
    5. Submit
    6. Verify: Semester appears in tournament list
    7. Verify: Semester visible to students (separate test)
    8. Cleanup: Delete semester
    """
```

**Előkészület:**
- Fel kell térképezni Admin Dashboard → Tournaments UI-t
- Form selector-ok azonosítása
- Date picker kezelés Playwright-ban

**Becsült idő:** 2-3 óra

---

#### 2.2 Admin Creates Tournament Session with Instructor
**Fájl:** `tests/e2e/test_tournament_admin_setup.py`

```python
@pytest.mark.e2e
@pytest.mark.tournament_admin
def test_admin_can_create_tournament_session_with_instructor(
    page: Page,
    admin_token: str,
    test_instructor: dict  # Fixture létrehozza
):
    """
    E2E: Admin creates tournament session and assigns instructor.

    Flow:
    1. Admin login
    2. Admin creates tournament semester (setup)
    3. Admin navigates to semester → Sessions
    4. Click "Create Session"
    5. Fill form:
       - Date: today + 7 days
       - Time: 18:00
       - Instructor: test_instructor (dropdown)
       - Location: "Test Field"
       - Max Participants: 10
       - is_tournament_game: True (auto-set or manual?)
    6. Submit
    7. Verify: Session appears in list
    8. Verify: is_tournament_game = True
    9. Verify: Instructor assigned
    10. Cleanup
    """
```

**Becsült idő:** 2-3 óra

---

#### 2.3 Admin Publishes Tournament (Makes it Active)
**Fájl:** `tests/e2e/test_tournament_admin_setup.py`

```python
@pytest.mark.e2e
@pytest.mark.tournament_admin
def test_admin_published_tournament_visible_to_students(
    page: Page,
    admin_token: str,
    test_student: dict
):
    """
    E2E: Published tournament becomes visible to students.

    Flow:
    1. Admin creates tournament semester (is_active=True)
    2. Admin creates tournament session
    3. Student login
    4. Student navigates to "Available Sessions"
    5. Verify: Tournament session visible
    6. Verify: Filtered by student's specialization
    7. Cleanup
    """
```

**Becsült idő:** 2 óra

---

**Phase 2 Össz becsült idő:** 6-8 óra

---

## 🏗️ PHASE 3: Student Enrollment

### Tesztek

#### 3.1 Student Views Available Tournament Sessions
**Fájl:** `tests/e2e/test_tournament_student_enrollment.py`

```python
@pytest.mark.e2e
@pytest.mark.tournament_student
def test_student_sees_tournament_sessions_for_their_specialization(
    page: Page,
    tournament_with_session: dict  # Fixture
):
    """
    E2E: Student sees tournament sessions filtered by specialization.

    Flow:
    1. Create tournament for GOALKEEPER specialization (fixture)
    2. Create student with GOALKEEPER specialization
    3. Student login
    4. Navigate to "Available Sessions"
    5. Verify: Tournament session visible
    6. Verify: Session details correct (date, instructor, location)
    7. Verify: Available spots count correct
    8. Cleanup
    """
```

**Becsült idő:** 2 óra

---

#### 3.2 Student Books Tournament Session
**Fájl:** `tests/e2e/test_tournament_student_enrollment.py`

```python
@pytest.mark.e2e
@pytest.mark.tournament_student
def test_student_can_book_tournament_session(
    page: Page,
    tournament_with_session: dict
):
    """
    E2E: Student successfully books a tournament session.

    Flow:
    1. Setup: Tournament session exists (fixture)
    2. Student login
    3. Navigate to "Available Sessions"
    4. Click "Book" on tournament session
    5. Verify: Confirmation message appears
    6. Navigate to "My Sessions"
    7. Verify: Booking appears in list
    8. Verify: Booking status (PENDING or CONFIRMED)
    9. Go back to "Available Sessions"
    10. Verify: Available spots decremented
    11. Cleanup
    """
```

**Becsült idő:** 2-3 óra

---

#### 3.3 Student Cannot Double-Book Same Session
**Fájl:** `tests/e2e/test_tournament_student_enrollment.py`

```python
@pytest.mark.e2e
@pytest.mark.tournament_student
def test_student_cannot_double_book_tournament_session(
    page: Page,
    tournament_with_session: dict
):
    """
    E2E: System prevents student from booking same session twice.

    Flow:
    1. Student books a tournament session (setup)
    2. Student navigates back to "Available Sessions"
    3. Verify: "Book" button disabled OR not visible for booked session
    4. OR: If clickable, shows error message
    5. Cleanup
    """
```

**Becsült idő:** 1 óra

---

#### 3.4 Student Cancels Tournament Booking
**Fájl:** `tests/e2e/test_tournament_student_enrollment.py`

```python
@pytest.mark.e2e
@pytest.mark.tournament_student
def test_student_can_cancel_tournament_booking(
    page: Page,
    tournament_with_session: dict
):
    """
    E2E: Student cancels their tournament booking.

    Flow:
    1. Student has booked tournament session (setup)
    2. Student navigates to "My Sessions"
    3. Click "Cancel" on booking
    4. Confirm cancellation (if confirmation dialog)
    5. Verify: Booking removed from "My Sessions"
    6. Navigate to "Available Sessions"
    7. Verify: Available spot count incremented
    8. Verify: "Book" button now enabled
    9. Cleanup
    """
```

**Becsült idő:** 2 óra

---

**Phase 3 Össz becsült idő:** 7-8 óra

---

## 🏗️ PHASE 4: Instructor Tournament Execution (COMPLETE)

### Tesztek

#### 4.1 Instructor Views Assigned Tournament Sessions
**Fájl:** `tests/e2e/test_tournament_instructor_execution.py`

```python
@pytest.mark.e2e
@pytest.mark.tournament_instructor
def test_instructor_sees_assigned_tournament_sessions(
    page: Page,
    tournament_with_session: dict
):
    """
    E2E: Instructor sees only their assigned tournament sessions.

    Flow:
    1. Create tournament session assigned to instructor A (fixture)
    2. Create another tournament assigned to instructor B
    3. Login as instructor A
    4. Navigate to Instructor Dashboard → Check-in → Tournament
    5. Verify: Sees session A
    6. Verify: Does NOT see session B
    7. Cleanup
    """
```

**Becsült idő:** 1-2 óra

---

#### 4.2 Instructor Marks Attendance - Complete Flow
**Fájl:** `tests/e2e/test_tournament_instructor_execution.py`

```python
@pytest.mark.e2e
@pytest.mark.tournament_instructor
def test_instructor_can_mark_attendance_complete_flow(
    page: Page,
    tournament_with_session: dict
):
    """
    E2E: Instructor marks attendance for all students (TELJES FLOW).

    Flow:
    1. Tournament session with 5 students booked (fixture)
    2. Instructor login
    3. Navigate to tournament check-in
    4. Select tournament session
    5. Verify: 5 students listed
    6. Verify: ONLY 2 buttons per student (Present, Absent)
    7. Mark Student A: Present
    8. Verify: Attendance saved (button state change OR API check)
    9. Mark Student B: Absent
    10. Verify: Attendance saved
    11. Mark Students C, D, E: Present
    12. Verify: Attendance summary: "4 Present, 1 Absent"
    13. Verify: Attendance persisted (refresh page, still correct)
    14. Cleanup
    """
```

**Becsült idő:** 2-3 óra (részben már van, de bővíteni kell)

---

#### 4.3 Instructor Can Change Attendance Status
**Fájl:** `tests/e2e/test_tournament_instructor_execution.py`

```python
@pytest.mark.e2e
@pytest.mark.tournament_instructor
def test_instructor_can_change_attendance_from_present_to_absent(
    page: Page,
    tournament_with_session: dict
):
    """
    E2E: Instructor realizes mistake and changes attendance.

    Flow:
    1. Instructor marks Student A as PRESENT (setup)
    2. Instructor clicks "Absent" for Student A
    3. Verify: Status changed to ABSENT
    4. Verify: Summary updated ("0 Present, 1 Absent")
    5. Refresh page
    6. Verify: Status persisted
    7. Cleanup
    """
```

**Becsült idő:** 1-2 óra

---

#### 4.4 Instructor CANNOT Mark Late/Excused for Tournament
**Fájl:** `tests/e2e/test_tournament_instructor_execution.py`

```python
@pytest.mark.e2e
@pytest.mark.tournament_instructor
def test_instructor_cannot_mark_late_for_tournament_ui_validation(
    page: Page,
    tournament_with_session: dict
):
    """
    E2E: UI prevents instructor from marking Late/Excused for tournaments.

    Flow:
    1. Instructor opens tournament check-in
    2. Verify: NO "Late" button visible
    3. Verify: NO "Excused" button visible
    4. (Backend already validated - this is UI confirmation)

    This complements the existing test:
    - test_tournament_attendance_shows_only_2_buttons (already exists)
    """
```

**Megjegyzés:** Ez részben már létezik (`test_tournament_attendance_complete.py`), de bővíthető.

**Becsült idő:** 1 óra (bővítés)

---

**Phase 4 Össz becsült idő:** 5-8 óra

---

## 🏗️ PHASE 5: Admin Monitoring & Closure

### Tesztek

#### 5.1 Admin Views Tournament Attendance Summary
**Fájl:** `tests/e2e/test_tournament_admin_monitoring.py`

```python
@pytest.mark.e2e
@pytest.mark.tournament_admin
def test_admin_sees_tournament_attendance_summary(
    page: Page,
    tournament_with_marked_attendance: dict  # Új fixture
):
    """
    E2E: Admin views attendance reports for tournament.

    Flow:
    1. Setup: Tournament session with attendance marked (fixture)
       - 3 students PRESENT
       - 2 students ABSENT
    2. Admin login
    3. Navigate to Admin Dashboard → Tournaments → Reports
    4. Select tournament semester
    5. Verify: Sees attendance summary
       - "3 Present, 2 Absent (60% attendance rate)"
    6. Verify: Per-student breakdown visible
    7. Cleanup
    """
```

**Előkészület:**
- Fel kell térképezni az Admin reports UI-t (ha létezik)
- Ha nincs ilyen UI, lehet hogy csak backend API-n keresztül elérhető

**Becsült idő:** 2-3 óra (+ UI felfedezés)

---

#### 5.2 Admin Closes Tournament Semester
**Fájl:** `tests/e2e/test_tournament_admin_monitoring.py`

```python
@pytest.mark.e2e
@pytest.mark.tournament_admin
def test_admin_can_close_tournament_semester(
    page: Page,
    admin_token: str
):
    """
    E2E: Admin closes tournament semester (sets is_active=False).

    Flow:
    1. Admin creates tournament semester (is_active=True)
    2. Admin navigates to Tournaments
    3. Click "Close" or "Deactivate" on semester
    4. Confirm action
    5. Verify: Semester is_active = False
    6. Login as student
    7. Navigate to "Available Sessions"
    8. Verify: Closed tournament NOT visible
    9. Cleanup
    """
```

**Becsült idő:** 2 óra

---

**Phase 5 Össz becsült idő:** 4-5 óra

---

## 🌟 GOLDEN TEST: Full Lifecycle Integration

### The Ultimate E2E Test

**Fájl:** `tests/e2e/test_tournament_full_lifecycle.py`

```python
@pytest.mark.e2e
@pytest.mark.critical
@pytest.mark.full_lifecycle
def test_tournament_complete_lifecycle_end_to_end(
    page: Page,
    browser_context: BrowserContext  # Multi-user simulation
):
    """
    🌟 CRITICAL E2E TEST: Complete Tournament Lifecycle

    This is THE definitive E2E test that validates the entire
    tournament workflow from creation to closure.

    Full Flow:
    ==========

    PHASE 1: USER SETUP
    -------------------
    1. Admin creates instructor user
    2. Admin creates 3 student users (all GOALKEEPER specialization)
    3. Verify users can login

    PHASE 2: TOURNAMENT CREATION
    ----------------------------
    4. Admin creates tournament semester:
       - Name: "E2E Test Tournament"
       - Specialization: GOALKEEPER
       - Dates: today → today+90
       - is_active: True
    5. Admin creates tournament session:
       - Date: today + 7 days
       - Instructor: created instructor
       - Max: 10 students
       - is_tournament_game: True
    6. Verify session visible in admin dashboard

    PHASE 3: STUDENT ENROLLMENT
    ---------------------------
    7. Student A logs in
    8. Student A sees tournament session in "Available Sessions"
    9. Student A books tournament session
    10. Verify booking appears in "My Sessions"
    11. Repeat for Students B and C
    12. Verify: 3/10 spots taken

    PHASE 4: INSTRUCTOR EXECUTION
    -----------------------------
    13. Instructor logs in
    14. Instructor navigates to tournament check-in
    15. Instructor sees the tournament session
    16. Instructor opens student list
    17. Verify: 3 students listed (A, B, C)
    18. Verify: ONLY 2 buttons per student (Present, Absent)
    19. Instructor marks:
        - Student A: PRESENT
        - Student B: PRESENT
        - Student C: ABSENT
    20. Verify: Attendance summary: "2 Present, 1 Absent"
    21. Verify: Attendance persisted in database

    PHASE 5: ADMIN MONITORING
    -------------------------
    22. Admin logs in
    23. Admin views tournament reports
    24. Verify: Sees attendance summary (2/3 present = 67%)
    25. Admin closes tournament semester
    26. Verify: is_active = False

    PHASE 6: VERIFICATION
    ---------------------
    27. Student A logs in
    28. Navigate to "Available Sessions"
    29. Verify: Closed tournament NOT visible
    30. Navigate to "My Sessions" (past sessions)
    31. Verify: Past tournament booking visible with attendance (PRESENT)

    CLEANUP
    -------
    32. Delete tournament semester (cascades)
    33. Delete users

    Duration: ~5-10 minutes (long test, but comprehensive)
    """

    # Multi-context setup for simulating different users
    admin_page = page  # Main page for admin
    instructor_context = browser_context.new_page()
    student_a_context = browser_context.new_page()
    student_b_context = browser_context.new_page()
    student_c_context = browser_context.new_page()

    try:
        # Implementation here...
        # (Teljes flow implementálása)

        pass

    finally:
        # Cleanup contexts
        instructor_context.close()
        student_a_context.close()
        student_b_context.close()
        student_c_context.close()
```

**Becsült idő:** 6-8 óra (komplex, de ez a LEGFONTOSABB teszt)

---

## 📊 Összefoglaló

| Phase | Tesztek száma | Becsült idő | Prioritás |
|-------|---------------|-------------|-----------|
| Phase 1: User Lifecycle | 2-3 | 4-7 óra | HIGH |
| Phase 2: Admin Tournament Setup | 3 | 6-8 óra | HIGH |
| Phase 3: Student Enrollment | 4 | 7-8 óra | HIGH |
| Phase 4: Instructor Execution | 4 | 5-8 óra | CRITICAL ⭐ |
| Phase 5: Admin Monitoring | 2 | 4-5 óra | MEDIUM |
| **Golden Test: Full Lifecycle** | **1** | **6-8 óra** | **CRITICAL ⭐⭐⭐** |
| **TOTAL** | **15-17 tesztek** | **32-44 óra** | - |

**Becsült teljes munkaidő:** 32-44 óra (4-6 munkanap)

---

## 🚀 Implementációs Sorrend (Javasolt)

### Sprint 1: Core Flows (1-2 nap)
1. ✅ Phase 2.1: Admin creates tournament semester
2. ✅ Phase 2.2: Admin creates tournament session
3. ✅ Phase 3.2: Student books tournament
4. ✅ Phase 4.2: Instructor marks attendance (COMPLETE flow)

**Miért ez első:** Ez a minimális "happy path" - ha ez működik, a többi buildelhet rá.

### Sprint 2: User Management (0.5-1 nap)
5. ✅ Phase 1.1: Admin creates instructor
6. ✅ Phase 1.2: Admin creates student

### Sprint 3: Edge Cases & Validation (0.5-1 nap)
7. ✅ Phase 3.3: Student cannot double-book
8. ✅ Phase 3.4: Student cancels booking
9. ✅ Phase 4.3: Instructor changes attendance

### Sprint 4: Monitoring & Closure (0.5-1 nap)
10. ✅ Phase 5.1: Admin views reports
11. ✅ Phase 5.2: Admin closes tournament

### Sprint 5: Golden Test (1 nap)
12. ✅ **Full Lifecycle Integration Test** 🌟

---

## 🎯 Sikerességi Kritériumok

A teljes tournament lifecycle E2E lefedettség akkor tekinthető **KÉSZ**-nek, ha:

1. ✅ Mind a 15-17 izolált teszt PASSED
2. ✅ **Golden Test (Full Lifecycle) PASSED** 🌟🌟🌟
3. ✅ Tesztek futnak CI-ben (opcionális, de ajánlott)
4. ✅ Minden teszt self-contained (saját fixture setup + cleanup)
5. ✅ Tesztek futási ideje: < 30 perc összesen
6. ✅ Dokumentáció frissítve az új tesztekkel

---

## 📝 Következő Lépések

**MOST:**
1. ✅ Ezt a tervet átnézed és jóváhagyod
2. ✅ Eldöntjük a prioritási sorrendet
3. ✅ Indulunk az implementációval

**KÉRDÉSEK ELŐTTE:**
- Van-e user registration UI flow? (vagy csak admin hozza létre a user-eket?)
- Van-e onboarding wizard?
- Admin Dashboard Tournaments UI jelenlegi állapota? (fel kell még térképezni?)
- Van-e reports UI az Admin-ban? (vagy csak API?)

Jóváhagyod ezt a tervet? Van bármi, amit módosítanál a prioritásokon vagy a scope-on?

---

**Készítette:** Claude Sonnet 4.5
**Dátum:** 2026-01-03
**Projekt:** LFA Football Investment - Tournament E2E Testing
**Státusz:** Terv jóváhagyásra vár
