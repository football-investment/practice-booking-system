# 🏆 Tournament - Teljes Workflow (E2E Perspective)

**Dokumentum célja:** Részletes lista minden lépésről a tournament folyamatban, amit E2E tesztekkel kellene lefedni.

---

## 📋 PHASE 1: Setup & User Management

### 1.1 Admin Creates Users (NINCS E2E LEFEDETTSÉG)

```
┌─────────────────────────────────────────────────────────────┐
│ ADMIN DASHBOARD → Users Tab                                 │
├─────────────────────────────────────────────────────────────┤
│ 1. Admin clicks "Create User"                               │
│ 2. Admin fills form:                                        │
│    - Email                                                  │
│    - Name                                                   │
│    - Role (INSTRUCTOR / STUDENT)                            │
│    - Date of Birth                                          │
│    - Specialization (for students)                          │
│ 3. Admin submits                                            │
│ 4. System sends email with temporary password (?)           │
│ 5. User appears in user list                                │
└─────────────────────────────────────────────────────────────┘

E2E Test Needed:
- test_admin_can_create_instructor_user
- test_admin_can_create_student_user
- test_created_user_appears_in_list
- test_user_can_login_with_credentials
```

**Jelenlegi Státusz:** ❌ NINCS E2E teszt (csak API fixture)

---

## 📋 PHASE 2: Tournament Creation

### 2.1 Admin Creates Tournament Semester (NINCS E2E LEFEDETTSÉG)

```
┌─────────────────────────────────────────────────────────────┐
│ ADMIN DASHBOARD → Tournaments Tab → Create Semester         │
├─────────────────────────────────────────────────────────────┤
│ 1. Admin clicks "Create Tournament Semester"                │
│ 2. Admin fills form:                                        │
│    - Name (e.g., "Spring 2024 Goalkeeper Tournament")       │
│    - Specialization (GOALKEEPER / STRIKER / etc.)           │
│    - Start Date                                             │
│    - End Date                                               │
│    - is_active (checkbox)                                   │
│ 3. Admin submits                                            │
│ 4. Semester appears in tournament list                      │
│ 5. Semester is visible to students (if is_active=True)      │
└─────────────────────────────────────────────────────────────┘

E2E Test Needed:
- test_admin_can_create_tournament_semester
- test_tournament_semester_appears_in_list
- test_active_tournament_visible_to_students
- test_inactive_tournament_not_visible_to_students
```

**Jelenlegi Státusz:** ❌ NINCS E2E teszt (csak API fixture)

---

### 2.2 Admin Creates Tournament Sessions (NINCS E2E LEFEDETTSÉG)

```
┌─────────────────────────────────────────────────────────────┐
│ ADMIN DASHBOARD → Tournaments → Select Semester → Sessions  │
├─────────────────────────────────────────────────────────────┤
│ 1. Admin selects a tournament semester                      │
│ 2. Admin clicks "Create Session"                            │
│ 3. Admin fills form:                                        │
│    - Date & Time                                            │
│    - Instructor (dropdown)                                  │
│    - Location                                               │
│    - Max Participants                                       │
│    - Session Type (TOURNAMENT - auto-set?)                  │
│    - is_tournament_game = True (KRITIKUS!)                  │
│ 4. Admin submits                                            │
│ 5. Session appears in semester's session list               │
│ 6. Session becomes available for student booking            │
└─────────────────────────────────────────────────────────────┘

E2E Test Needed:
- test_admin_can_create_tournament_session
- test_tournament_session_has_correct_flags (is_tournament_game=True)
- test_tournament_session_appears_in_list
- test_instructor_sees_assigned_tournament_session
```

**Jelenlegi Státusz:** ❌ NINCS E2E teszt (csak API fixture)

---

## 📋 PHASE 3: Student Enrollment

### 3.1 Student Views Available Tournaments (NINCS E2E LEFEDETTSÉG)

```
┌─────────────────────────────────────────────────────────────┐
│ STUDENT DASHBOARD → Available Sessions                      │
├─────────────────────────────────────────────────────────────┤
│ 1. Student logs in                                          │
│ 2. Student navigates to "Available Sessions"                │
│ 3. Student sees tournament sessions:                        │
│    - Filtered by their specialization                       │
│    - Only future sessions                                   │
│    - Only sessions with available spots                     │
│ 4. Student sees session details:                            │
│    - Date & Time                                            │
│    - Instructor name                                        │
│    - Location                                               │
│    - Available spots (e.g., "3/10 spots taken")             │
│    - "Book" button                                          │
└─────────────────────────────────────────────────────────────┘

E2E Test Needed:
- test_student_sees_tournament_sessions_for_their_specialization
- test_student_does_not_see_other_specialization_tournaments
- test_student_sees_available_spots_count
- test_student_does_not_see_past_tournament_sessions
```

**Jelenlegi Státusz:** ❌ NINCS E2E teszt

---

### 3.2 Student Books Tournament Session (NINCS E2E LEFEDETTSÉG)

```
┌─────────────────────────────────────────────────────────────┐
│ STUDENT DASHBOARD → Available Sessions → Book               │
├─────────────────────────────────────────────────────────────┤
│ 1. Student clicks "Book" on a tournament session            │
│ 2. System creates booking:                                  │
│    - status = PENDING (or CONFIRMED?)                       │
│    - attendance_status = None (not yet marked)              │
│ 3. Student sees confirmation message                        │
│ 4. Booking appears in "My Sessions"                         │
│ 5. Available spots count decrements                         │
└─────────────────────────────────────────────────────────────┘

E2E Test Needed:
- test_student_can_book_tournament_session
- test_booking_appears_in_my_sessions
- test_available_spots_decremented_after_booking
- test_student_cannot_double_book_same_session
```

**Jelenlegi Státusz:** ❌ NINCS E2E teszt (csak API fixture létrehozza a booking-ot)

---

### 3.3 Student Manages Bookings (NINCS E2E LEFEDETTSÉG)

```
┌─────────────────────────────────────────────────────────────┐
│ STUDENT DASHBOARD → My Sessions                             │
├─────────────────────────────────────────────────────────────┤
│ 1. Student navigates to "My Sessions"                       │
│ 2. Student sees their tournament bookings:                  │
│    - Upcoming tournaments                                   │
│    - Booking status (PENDING / CONFIRMED)                   │
│    - Attendance status (if marked)                          │
│ 3. Student can cancel booking (if allowed):                 │
│    - Click "Cancel" button                                  │
│    - Confirm cancellation                                   │
│    - Booking removed from list                              │
│    - Available spot opens up again                          │
└─────────────────────────────────────────────────────────────┘

E2E Test Needed:
- test_student_sees_their_tournament_bookings
- test_student_can_cancel_tournament_booking
- test_cancelled_booking_reopens_spot
```

**Jelenlegi Státusz:** ❌ NINCS E2E teszt

---

## 📋 PHASE 4: Instructor Tournament Execution

### 4.1 Instructor Views Assigned Tournaments (RÉSZBEN LEFEDVE)

```
┌─────────────────────────────────────────────────────────────┐
│ INSTRUCTOR DASHBOARD → Check-in & Groups → Tournaments      │
├─────────────────────────────────────────────────────────────┤
│ 1. Instructor logs in                                       │ ✅ LEFEDVE
│ 2. Instructor navigates to Instructor Dashboard             │ ✅ LEFEDVE
│ 3. Instructor clicks "Check-in & Groups" tab                │ ✅ LEFEDVE
│ 4. Instructor clicks "Tournament Sessions" sub-tab          │ ✅ LEFEDVE
│ 5. Instructor sees list of assigned tournament sessions:    │ ✅ LEFEDVE
│    - Today & upcoming tournaments                           │
│    - Session details (date, time, location)                 │
│    - Student count (e.g., "5 students booked")              │
│    - "Select ➡️" button                                     │ ✅ LEFEDVE
└─────────────────────────────────────────────────────────────┘

E2E Test Needed:
- test_instructor_sees_assigned_tournament_sessions ✅ (részben)
- test_instructor_does_not_see_unassigned_tournaments
- test_instructor_sees_correct_student_count
```

**Jelenlegi Státusz:** ✅ ~50% LEFEDVE (a referencia teszt ezt csinálja)

---

### 4.2 Instructor Marks Attendance (2-Button Rule) (20% LEFEDVE)

```
┌─────────────────────────────────────────────────────────────┐
│ TOURNAMENT SESSION CHECK-IN                                  │
├─────────────────────────────────────────────────────────────┤
│ 1. Instructor clicks "Select ➡️" on a tournament            │ ✅ LEFEDVE
│ 2. Instructor sees student list with attendance buttons     │ ✅ LEFEDVE
│ 3. FOR EACH STUDENT:                                        │
│    - Student name                                           │ ✅ LEFEDVE
│    - ONLY 2 buttons: "✅ Present" & "❌ Absent"             │ ✅ LEFEDVE (TESZT VALIDÁLJA!)
│    - NO "⏰ Late" button                                    │ ✅ LEFEDVE (TESZT VALIDÁLJA!)
│    - NO "🎫 Excused" button                                │ ✅ LEFEDVE (TESZT VALIDÁLJA!)
│                                                              │
│ 4. Instructor clicks "✅ Present" for Student A             │ ❌ NINCS LEFEDVE (1 click van, nem validált)
│ 5. System updates attendance:                               │ ❌ NINCS LEFEDVE
│    - attendance_status = PRESENT                            │
│    - Button changes state (highlighted / disabled?)         │
│    - Count updated (e.g., "3/5 marked")                     │
│                                                              │
│ 6. Instructor clicks "❌ Absent" for Student B              │ ❌ NINCS LEFEDVE
│ 7. System updates attendance:                               │ ❌ NINCS LEFEDVE
│    - attendance_status = ABSENT                             │
│                                                              │
│ 8. Instructor sees attendance summary:                      │ ❌ NINCS LEFEDVE
│    - "3 Present, 2 Absent"                                  │
│                                                              │
│ 9. (Optional) Instructor "finalizes" attendance             │ ❌ NINCS LEFEDVE (ha van ilyen funkció)
└─────────────────────────────────────────────────────────────┘

E2E Test Needed:
- test_tournament_shows_only_2_buttons ✅ KÉSZ!
- test_instructor_can_mark_student_present ❌ NINCS
- test_instructor_can_mark_student_absent ❌ NINCS
- test_attendance_updates_immediately ❌ NINCS
- test_instructor_sees_attendance_summary ❌ NINCS
- test_instructor_cannot_mark_late_for_tournament ❌ NINCS (backend validált, UI nem)
- test_instructor_cannot_mark_excused_for_tournament ❌ NINCS
```

**Jelenlegi Státusz:** ✅ 20% LEFEDVE (csak button megjelenítés validált, működés NINCS)

---

### 4.3 Instructor Edits Attendance (NINCS E2E LEFEDETTSÉG)

```
┌─────────────────────────────────────────────────────────────┐
│ EDIT ATTENDANCE (If Allowed)                                │
├─────────────────────────────────────────────────────────────┤
│ 1. Instructor realizes a mistake (marked wrong status)      │
│ 2. Instructor clicks the opposite button:                   │
│    - Was PRESENT → Click "❌ Absent"                        │
│    - Was ABSENT → Click "✅ Present"                        │
│ 3. System updates attendance                                │
│ 4. Summary updates                                          │
└─────────────────────────────────────────────────────────────┘

E2E Test Needed:
- test_instructor_can_change_attendance_from_present_to_absent
- test_instructor_can_change_attendance_from_absent_to_present
```

**Jelenlegi Státusz:** ❌ NINCS E2E teszt

---

## 📋 PHASE 5: Admin Monitoring

### 5.1 Admin Views Tournament Reports (NINCS E2E LEFEDETTSÉG)

```
┌─────────────────────────────────────────────────────────────┐
│ ADMIN DASHBOARD → Tournaments → Reports                     │
├─────────────────────────────────────────────────────────────┤
│ 1. Admin selects a tournament semester                      │
│ 2. Admin sees attendance reports:                           │
│    - Per session: attendance rate (e.g., "80% present")     │
│    - Per student: participation history                     │
│    - Per instructor: sessions conducted                     │
│ 3. Admin can export reports (CSV / PDF?)                    │
└─────────────────────────────────────────────────────────────┘

E2E Test Needed:
- test_admin_sees_tournament_attendance_summary
- test_admin_sees_student_participation_stats
```

**Jelenlegi Státusz:** ❌ NINCS E2E teszt

---

### 5.2 Admin Closes Tournament Semester (NINCS E2E LEFEDETTSÉG)

```
┌─────────────────────────────────────────────────────────────┐
│ ADMIN DASHBOARD → Tournaments → Close Semester              │
├─────────────────────────────────────────────────────────────┤
│ 1. Admin clicks "Close Tournament Semester"                 │
│ 2. System sets is_active = False                            │
│ 3. Tournament no longer visible to students                 │
│ 4. Historical data preserved for reporting                  │
└─────────────────────────────────────────────────────────────┘

E2E Test Needed:
- test_admin_can_close_tournament_semester
- test_closed_tournament_not_visible_to_students
```

**Jelenlegi Státusz:** ❌ NINCS E2E teszt

---

## 📊 ÖSSZEFOGLALÓ - E2E Lefedettség

| Phase | Lépések száma | E2E Lefedettség | Megjegyzés |
|-------|---------------|-----------------|------------|
| **Phase 1: User Management** | 5 | ❌ 0% | API fixture létrehozza, UI flow NINCS tesztelve |
| **Phase 2: Tournament Creation** | 10 | ❌ 0% | API fixture létrehozza, UI flow NINCS tesztelve |
| **Phase 3: Student Enrollment** | 10 | ❌ 0% | Egyáltalán NINCS lefedve |
| **Phase 4: Instructor Execution** | 15 | ✅ 20% | **CSAK button megjelenítés validált** |
| **Phase 5: Admin Monitoring** | 5 | ❌ 0% | Egyáltalán NINCS lefedve |
| **TOTAL** | **45 lépés** | **~5%** | **43/45 lépés NINCS E2E tesztelve** |

---

## 🎯 Mi a Jelenlegi Referencia Teszt VALÓDI Lefedettség?

```python
# tests/e2e/test_tournament_attendance_complete.py

def test_tournament_attendance_shows_only_2_buttons(...):
    """
    MIT TESZT VALÓBAN:
    ✅ Instructor bejelentkezés
    ✅ Navigáció: Dashboard → Check-in tab → Tournament sub-tab
    ✅ Session lista megjelenítése
    ✅ Session kiválasztása ("Select ➡️")
    ✅ Student lista megjelenítése
    ✅ Gombok számlálása:
       - Present buttons: 5 db ✅
       - Absent buttons: 5 db ✅
       - Late buttons: 0 db ✅ (KRITIKUS!)
       - Excused buttons: 0 db ✅ (KRITIKUS!)
    ✅ 1x kattintás a "Present" gombra (de nincs validálás hogy működött)

    MIT NEM TESZT:
    ❌ Attendance mentődik-e az adatbázisba
    ❌ Attendance summary frissül-e
    ❌ Lehet-e módosítani (Present → Absent)
    ❌ Backend validáció (API hiba esetén mi történik)
    ❌ Több student megjelölése
    ❌ Session finalization (ha van ilyen)

    LEFEDETTSÉG: ~5% a teljes tournament workflow-ból
    """
```

---

## 💡 Következtetés

**Amit VALÓBAN átadtunk:**
1. ✅ **1 szűk scope E2E teszt** - Tournament session 2-gombos szabály validálása (button rendering)
2. ✅ **Fixture infrastruktúra** - API-alapú test data létrehozás
3. ✅ **Dokumentáció** - Hogyan írj hasonló teszteket

**Amit NEM adtunk át:**
1. ❌ Teljes tournament workflow E2E lefedettség
2. ❌ Admin flow-k tesztelése
3. ❌ Student flow-k tesztelése
4. ❌ Instructor flow teljes lefedettség (csak button rendering)

**Valódi lefedettség:** ~5% (1 speciális business rule validálása)

---

## 🚀 Javasolt Következő Lépések

Ha a teljes tournament workflow E2E lefedettség a cél, a következő teszteket kellene megírni (prioritás szerint):

### HIGH Priority
1. `test_student_can_book_tournament_session` - Student enrollment flow
2. `test_instructor_can_mark_multiple_students_present` - Tényleges attendance marking
3. `test_admin_can_create_tournament_semester` - Admin setup flow

### MEDIUM Priority
4. `test_instructor_can_change_attendance_status` - Attendance editing
5. `test_student_sees_tournament_sessions_filtered_by_specialization` - Student filtering
6. `test_admin_can_create_tournament_session_with_instructor` - Session setup

### LOW Priority
7. `test_admin_sees_tournament_attendance_summary` - Reporting
8. `test_closed_tournament_not_visible_to_students` - Lifecycle management

**Becsült munka:** 15-20 további E2E teszt szükséges a teljes workflow lefedettsé
ghez.

---

**Utolsó frissítés:** 2026-01-03
**Készítette:** Claude Sonnet 4.5
