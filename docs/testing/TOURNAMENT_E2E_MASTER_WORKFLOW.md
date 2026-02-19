# Tournament System - Master E2E Workflow

## 🎯 Teljes Workflow Áttekintés

Ez a dokumentum részletezi a tournament rendszer teljes E2E tesztelési folyamatát, amely 3 fő szakaszból áll:

1. **Admin létrehozza a tournamenteket** (6 db)
2. **Instructor jelentkezik APPLICATION_BASED tournamentekre** (3 db)
3. **Admin meghívja instructort OPEN_ASSIGNMENT tournamentekre** (3 db)

---

## 📊 Checkpoint Struktúra

```
START (üres DB)
    ↓
[CHECKPOINT 1] → User Registration befejezve (3 instructor regisztrálva)
    ↓
[CHECKPOINT 2] → 6 Tournament létrehozva (3 APPLICATION + 3 OPEN_ASSIGNMENT)
    ↓
[CHECKPOINT 3] → 3 APPLICATION_BASED tournament - instructor jelentkezett
    ↓
[CHECKPOINT 4] → 3 OPEN_ASSIGNMENT tournament - admin meghívta instructort
    ↓
[END] → Minden tournament confirmed instructorral
```

---

## 🔧 SCRIPT 1: Admin Creates Tournaments

**Fájl:** `tests/e2e/test_admin_create_tournament_refactored.py`

**Előfeltétel:**
- Database előkészítve (users, locations, campuses léteznek)
- Admin user: grandmaster@lfa.com
- Test instructors: pwt.* emails (3 db)

**Checkpointból indul:** Nincs (vagy CHECKPOINT 1 - users ready)

**Létrehozza:** CHECKPOINT 2

### Lépések:

#### STEP 1: Admin Login
```
1.1. Böngésző megnyitása (Firefox/Chromium - headed mode)
1.2. Navigálás: http://localhost:8501/Admin_Dashboard
1.3. Email: grandmaster@lfa.com
1.4. Password: GrandMaster2026!
1.5. Login gomb
1.6. Várunk automatikus redirect-re (Admin Dashboard)
1.7. Ellenőrizzük: URL = /Admin_Dashboard
```

#### STEP 2: Navigate to Tournaments
```
2.1. Keresés: "Tournaments" tab gomb
2.2. Kattintás a "Tournaments" tab-ra
2.3. Várakozás: Tab tartalom betöltődik (2s)
2.4. Screenshot: tournaments_tab_loaded.png
```

#### STEP 3: Create Tournament Loop (6x)

##### TOURNAMENT CONFIG:
```python
tournaments = [
    # APPLICATION_BASED (instructorok jelentkeznek)
    {
        "name": "Budapest HU League {timestamp}",
        "type": "League (Round Robin)",
        "location_index": 0,  # Budapest
        "campus": "Erste (automatikus)",
        "age_group": "AMATEUR (18+)",
        "max_players": 8,
        "enrollment_cost": 500,
        "assignment_type": "APPLICATION_BASED"
    },
    {
        "name": "Vienna AT Knockout {timestamp}",
        "type": "Single Elimination (Knockout)",
        "location_index": 1,  # Vienna
        "campus": "Erste (automatikus)",
        "age_group": "AMATEUR (18+)",
        "max_players": 8,
        "enrollment_cost": 500,
        "assignment_type": "APPLICATION_BASED"
    },
    {
        "name": "Bratislava SK Group+KO {timestamp}",
        "type": "Group Stage + Knockout",
        "location_index": 2,  # Bratislava
        "campus": "Erste (automatikus)",
        "age_group": "AMATEUR (18+)",
        "max_players": 8,
        "enrollment_cost": 500,
        "assignment_type": "APPLICATION_BASED"
    },

    # OPEN_ASSIGNMENT (admin hívja meg az instructort)
    {
        "name": "Budapest HU League INV {timestamp}",
        "type": "League (Round Robin)",
        "location_index": 0,
        "campus": "Erste (automatikus)",
        "age_group": "AMATEUR (18+)",
        "max_players": 8,
        "enrollment_cost": 500,
        "assignment_type": "OPEN_ASSIGNMENT"
    },
    {
        "name": "Vienna AT Knockout INV {timestamp}",
        "type": "Single Elimination (Knockout)",
        "location_index": 1,
        "campus": "Erste (automatikus)",
        "age_group": "AMATEUR (18+)",
        "max_players": 8,
        "enrollment_cost": 500,
        "assignment_type": "OPEN_ASSIGNMENT"
    },
    {
        "name": "Bratislava SK Group+KO INV {timestamp}",
        "type": "Group Stage + Knockout",
        "location_index": 2,
        "campus": "Erste (automatikus)",
        "age_group": "AMATEUR (18+)",
        "max_players": 8,
        "enrollment_cost": 500,
        "assignment_type": "OPEN_ASSIGNMENT"
    }
]
```

##### Loop minden tournamentre:
```
FOR idx, tournament_config IN tournaments:

    3.{idx}.1. Kattintás: "Create Tournament" tab
    3.{idx}.2. Várakozás: Form megjelenik (2s)
    3.{idx}.3. Screenshot: tournament_{idx}_form_empty.png

    3.{idx}.4. FORM KITÖLTÉS:
        a) Tournament Name: {tournament_config.name}
        b) Tournament Date: Tomorrow (input date picker)
        c) Location selectbox: Index szerint választás ({tournament_config.location_index})
           - 0 = Budapest
           - 1 = Vienna
           - 2 = Bratislava
        d) Campus selectbox: Automatikusan kiválasztódik az első campus
        e) Age Group selectbox: "AMATEUR (18+)"
        f) Tournament Type selectbox: {tournament_config.type}
           - Várakozás duration estimation megjelenésére (2s)
        g) Max Players: {tournament_config.max_players}
        h) Enrollment Cost: {tournament_config.enrollment_cost}
        i) Assignment Type selectbox: {tournament_config.assignment_type}

    3.{idx}.5. Screenshot: tournament_{idx}_form_filled.png
    3.{idx}.6. Kattintás: "Create Tournament" submit gomb
    3.{idx}.7. Várakozás: Success message (5s timeout)
    3.{idx}.8. Ellenőrzés: "Tournament created successfully!" text visible
    3.{idx}.9. Screenshot: tournament_{idx}_created.png

    3.{idx}.10. BACKEND VALIDÁCIÓ (opcionális):
        - API call: GET /tournaments (admin token)
        - Keresés: tournament name alapján
        - Ellenőrzés: status = "SEEKING_INSTRUCTOR" vagy "DRAFT"
        - Ellenőrzés: assignment_type = {tournament_config.assignment_type}

END FOR
```

#### STEP 4: Final Verification
```
4.1. API Login: grandmaster@lfa.com
4.2. GET /tournaments (admin token)
4.3. Filter: name tartalmazza timestamp-et
4.4. Assert: 6 tournament létrejött
4.5. Assert: 3 db assignment_type = "APPLICATION_BASED"
4.6. Assert: 3 db assignment_type = "OPEN_ASSIGNMENT"
4.7. Console log: Minden tournament ID, name, status
```

#### CHECKPOINT 2 Mentés:
```
PGDATABASE=lfa_intern_system pg_dump -U postgres -h localhost \
    --clean --if-exists \
    --file=tests/e2e/snapshots/after_tournament_creation.sql

echo "checkpoint=after_tournament_creation" > tests/e2e/snapshots/after_tournament_creation.meta
echo "timestamp=$(date +%Y%m%d%H%M%S)" >> tests/e2e/snapshots/after_tournament_creation.meta
echo "tournaments_created=6" >> tests/e2e/snapshots/after_tournament_creation.meta
```

**Output:** 6 tournament létrehozva DB-ben, screenshot-ok minden lépésről

---

## 🔧 SCRIPT 2: Instructor Application Workflow (APPLICATION_BASED)

**Fájl:** `tests/e2e/test_ui_instructor_application_workflow.py`

**Előfeltétel:** CHECKPOINT 2 (6 tournament létezik)

**Létrehozza:** CHECKPOINT 3

### Lépések:

#### STEP 1: Instructor Login
```
1.1. Böngésző megnyitása (Firefox - headed mode)
1.2. Navigálás: http://localhost:8501/Instructor_Dashboard
1.3. Email: pwt.V4lv3rd3jr@f1stteam.hu (első test instructor)
1.4. Password: SecurePassword123!
1.5. Login gomb
1.6. Várunk redirect-re: /Instructor_Dashboard
1.7. Screenshot: instructor_dashboard.png
```

#### STEP 2: Navigate to Tournaments
```
2.1. Kattintás: "Tournaments" tab
2.2. Várakozás: 2s
2.3. Screenshot: instructor_tournaments_tab.png
```

#### STEP 3: Find APPLICATION_BASED Tournaments
```
3.1. Keresés UI-ban vagy API-n keresztül:
    - API: GET /tournaments (instructor token)
    - Filter: assignment_type = "APPLICATION_BASED"
    - Filter: status = "SEEKING_INSTRUCTOR"
    - Filter: name NOT contains " INV"
3.2. Assert: 3 APPLICATION_BASED tournament található
3.3. Console log: Tournament IDs és nevek
```

#### STEP 4: Apply to Tournaments (Loop 3x)

```
FOR idx, tournament IN application_based_tournaments:

    4.{idx}.1. UI-ban keresés: Tournament card/row (name alapján)
    4.{idx}.2. Screenshot: tournament_{idx}_before_apply.png

    4.{idx}.3. Kattintás: "Apply" vagy "Jelentkezés" gomb
    4.{idx}.4. Várakozás: Application dialog/form megjelenik
    4.{idx}.5. Screenshot: tournament_{idx}_apply_dialog.png

    4.{idx}.6. Form kitöltés:
        - Message/Motivation textarea: "I am interested in leading this tournament!"
        - (További mezők ha vannak)

    4.{idx}.7. Kattintás: "Submit Application" gomb
    4.{idx}.8. Várakozás: Success message (3s)
    4.{idx}.9. Ellenőrzés: "Application submitted" vagy hasonló text
    4.{idx}.10. Screenshot: tournament_{idx}_applied.png

    4.{idx}.11. BACKEND VALIDÁCIÓ:
        - API: GET /tournaments/{tournament_id}/instructor-applications (admin token)
        - Assert: 1 application található
        - Assert: application.instructor_id = instructor ID
        - Assert: application.status = "PENDING"

END FOR
```

#### STEP 5: Admin Approves Applications

```
5.1. API Login: grandmaster@lfa.com → admin_token
5.2. GET /tournaments (filter: APPLICATION_BASED + timestamp)
5.3. Assert: 3 tournament található

FOR idx, tournament IN application_based_tournaments:

    5.{idx}.1. GET /tournaments/{tournament.id}/instructor-applications (admin token)
    5.{idx}.2. Assert: applications.length >= 1
    5.{idx}.3. application_id = applications[0].id

    5.{idx}.4. POST /tournaments/{tournament.id}/instructor-applications/{application_id}/approve
        Headers: Authorization: Bearer {admin_token}
        Body: {
            "response_message": "Application approved - looking forward to working with you!"
        }

    5.{idx}.5. Assert: Response status = 200
    5.{idx}.6. Console log: "✅ Application {application_id} approved for tournament {tournament.id}"

    5.{idx}.7. VALIDÁCIÓ:
        - GET /tournaments/{tournament.id}
        - Assert: status = "INSTRUCTOR_CONFIRMED" (auto-confirmation)
        - Assert: master_instructor_id = instructor.id

END FOR
```

#### STEP 6: Instructor Verifies Assignment (Optional UI Check)
```
6.1. Refresh Instructor Dashboard page
6.2. Navigate to "My Tournaments" vagy hasonló section
6.3. Assert: 3 confirmed tournament visible
6.4. Screenshot: instructor_confirmed_tournaments.png
```

#### CHECKPOINT 3 Mentés:
```
PGDATABASE=lfa_intern_system pg_dump -U postgres -h localhost \
    --clean --if-exists \
    --file=tests/e2e/snapshots/after_application_workflow.sql

echo "checkpoint=after_application_workflow" > tests/e2e/snapshots/after_application_workflow.meta
echo "timestamp=$(date +%Y%m%d%H%M%S)" >> tests/e2e/snapshots/after_application_workflow.meta
echo "application_based_confirmed=3" >> tests/e2e/snapshots/after_application_workflow.meta
```

**Output:** 3 APPLICATION_BASED tournament confirmed instructorral

---

## 🔧 SCRIPT 3: Admin Invitation Workflow (OPEN_ASSIGNMENT)

**Fájl:** `tests/e2e/test_ui_instructor_invitation_workflow.py`

**Előfeltétel:** CHECKPOINT 2 vagy CHECKPOINT 3

**Létrehozza:** CHECKPOINT 4 (FINAL)

### Lépések:

#### STEP 1: Get OPEN_ASSIGNMENT Tournaments
```
1.1. API Login: grandmaster@lfa.com → admin_token
1.2. GET /tournaments
1.3. Filter: assignment_type = "OPEN_ASSIGNMENT"
1.4. Filter: name contains " INV"
1.5. Assert: 3 tournament található
1.6. Console log: Tournament IDs és nevek
```

#### STEP 2: Get Instructor Details
```
2.1. Instructor: pwt.V4lv3rd3jr@f1stteam.hu
2.2. API Login: instructor → instructor_token
2.3. GET /users/me (instructor token)
2.4. Store: instructor_id
2.5. Console log: Instructor ID = {instructor_id}
```

#### STEP 3: Admin Invites Instructor (UI vagy API)

##### Opció A: UI-ban (Playwright)
```
FOR idx, tournament IN open_assignment_tournaments:

    3.{idx}.1. Admin Dashboard → Tournaments tab
    3.{idx}.2. Find tournament card/row: {tournament.name}
    3.{idx}.3. Screenshot: tournament_{idx}_before_invite.png

    3.{idx}.4. Kattintás: "Invite Instructor" gomb
    3.{idx}.5. Várakozás: Invite dialog megjelenik
    3.{idx}.6. Screenshot: tournament_{idx}_invite_dialog.png

    3.{idx}.7. Form kitöltés:
        - Instructor selectbox: Keresés "pwt.V4lv3rd3jr" email alapján
        - Message textarea: "You are invited to lead {tournament.name}"

    3.{idx}.8. Kattintás: "Send Invitation" gomb
    3.{idx}.9. Várakozás: Success message (3s)
    3.{idx}.10. Screenshot: tournament_{idx}_invited.png

END FOR
```

##### Opció B: API-n keresztül (gyorsabb, megbízhatóbb)
```
FOR idx, tournament IN open_assignment_tournaments:

    3.{idx}.1. POST /tournaments/{tournament.id}/invite-instructor
        Headers: Authorization: Bearer {admin_token}
        Body: {
            "instructor_id": {instructor_id},
            "message": "You are invited to lead {tournament.name}"
        }

    3.{idx}.2. Assert: Response status = 200/201
    3.{idx}.3. Console log: "✅ Invitation sent to tournament {tournament.id}"

    3.{idx}.4. VALIDÁCIÓ:
        - GET /tournaments/{tournament.id}/invitations
        - Assert: 1 invitation található
        - Assert: invitation.instructor_id = {instructor_id}
        - Assert: invitation.status = "PENDING"

END FOR
```

#### STEP 4: Instructor Views Invitations (UI)
```
4.1. Instructor Dashboard megnyitása (Playwright)
4.2. Login: pwt.V4lv3rd3jr@f1stteam.hu
4.3. Navigate: "Tournaments" tab
4.4. Navigate: "Invitations" sub-tab (ha van)
4.5. Screenshot: instructor_invitations_list.png
4.6. Assert: 3 pending invitation visible
```

#### STEP 5: Instructor Accepts Invitations

##### UI-ban:
```
FOR idx, tournament IN open_assignment_tournaments:

    5.{idx}.1. Find invitation card: {tournament.name}
    5.{idx}.2. Screenshot: invitation_{idx}_before_accept.png
    5.{idx}.3. Kattintás: "Accept" gomb
    5.{idx}.4. Várakozás: Confirm dialog (opcionális)
    5.{idx}.5. Kattintás: "Confirm Accept"
    5.{idx}.6. Várakozás: Success message
    5.{idx}.7. Screenshot: invitation_{idx}_accepted.png

END FOR
```

##### API-n keresztül (ha UI nincs kész):
```
FOR idx, tournament IN open_assignment_tournaments:

    5.{idx}.1. POST /tournaments/{tournament.id}/accept-invitation
        Headers: Authorization: Bearer {instructor_token}
        Body: {
            "response_message": "I accept this invitation!"
        }

    5.{idx}.2. Assert: Response status = 200
    5.{idx}.3. Console log: "✅ Invitation accepted for tournament {tournament.id}"

    5.{idx}.4. VALIDÁCIÓ:
        - GET /tournaments/{tournament.id}
        - Assert: status = "INSTRUCTOR_CONFIRMED"
        - Assert: master_instructor_id = {instructor_id}

END FOR
```

#### STEP 6: Final Verification
```
6.1. GET /tournaments (filter: OPEN_ASSIGNMENT + timestamp)
6.2. Assert: 3 tournament
6.3. FOR tournament:
        Assert: status = "INSTRUCTOR_CONFIRMED"
        Assert: master_instructor_id = {instructor_id}
6.4. Console log: "✅✅✅ All 3 OPEN_ASSIGNMENT tournaments confirmed!"
```

#### CHECKPOINT 4 Mentés (FINAL):
```
PGDATABASE=lfa_intern_system pg_dump -U postgres -h localhost \
    --clean --if-exists \
    --file=tests/e2e/snapshots/after_invitation_workflow.sql

echo "checkpoint=after_invitation_workflow" > tests/e2e/snapshots/after_invitation_workflow.meta
echo "timestamp=$(date +%Y%m%d%H%M%S)" >> tests/e2e/snapshots/after_invitation_workflow.meta
echo "application_based_confirmed=3" >> tests/e2e/snapshots/after_invitation_workflow.meta
echo "open_assignment_confirmed=3" >> tests/e2e/snapshots/after_invitation_workflow.meta
echo "total_tournaments=6" >> tests/e2e/snapshots/after_invitation_workflow.meta
```

---

## 🚀 FUTTATÁSI MÓDOK

### Mód 1: Teljes Workflow (From Scratch)

```bash
# 1. DB alaphelyzetbe állítás
cd tests/e2e
./reset_database_for_tests.sh

# 2. User registration (ha nincs checkpoint)
pytest test_user_registration.py --headed --slowmo 500 -v

# 3. Tournament creation (6 db)
pytest test_admin_create_tournament_refactored.py --headed --slowmo 500 -v

# 4. Application workflow (3 APPLICATION_BASED)
pytest test_ui_instructor_application_workflow.py --headed --slowmo 500 -v

# 5. Invitation workflow (3 OPEN_ASSIGNMENT)
pytest test_ui_instructor_invitation_workflow.py --headed --slowmo 500 -v
```

### Mód 2: Checkpoint-ból Indítás

```bash
# Ha már van CHECKPOINT 2 (tournaments created)
cd tests/e2e
./restore_checkpoint.sh after_tournament_creation

# Csak application + invitation workflow
pytest test_ui_instructor_application_workflow.py --headed --slowmo 500 -v
pytest test_ui_instructor_invitation_workflow.py --headed --slowmo 500 -v
```

### Mód 3: Master Test Script (Mindent egyben)

```bash
# Létrehozunk egy master test file-t amely mindent lefuttat
pytest tests/e2e/test_tournament_master_workflow.py --headed --slowmo 500 -v
```

---

## 📸 SCREENSHOT Struktúra

Minden screenshot ide kerül: `tests/e2e/screenshots/`

### Tournament Creation:
- `tournament_1_form_filled.png`
- `tournament_1_created.png`
- `tournament_2_form_filled.png`
- ... (6 tournament × 2 screenshot = 12 files)

### Application Workflow:
- `instructor_dashboard.png`
- `tournament_1_apply_dialog.png`
- `tournament_1_applied.png`
- ... (3 tournament × 2 = 6 files)

### Invitation Workflow:
- `tournament_4_invite_dialog.png`
- `tournament_4_invited.png`
- `invitation_1_accepted.png`
- ... (3 tournament × 3 = 9 files)

**Total: ~27 screenshots**

---

## ✅ SUCCESS CRITERIA

### CHECKPOINT 2:
- ✅ 6 tournament létezik DB-ben
- ✅ 3 APPLICATION_BASED (name NOT contains "INV")
- ✅ 3 OPEN_ASSIGNMENT (name contains "INV")
- ✅ Minden tournament status = "SEEKING_INSTRUCTOR" vagy "DRAFT"

### CHECKPOINT 3:
- ✅ 3 APPLICATION_BASED tournament status = "INSTRUCTOR_CONFIRMED"
- ✅ master_instructor_id = test instructor ID
- ✅ 3 instructor_application record DB-ben (status = "APPROVED")

### CHECKPOINT 4 (FINAL):
- ✅ 3 OPEN_ASSIGNMENT tournament status = "INSTRUCTOR_CONFIRMED"
- ✅ master_instructor_id = test instructor ID
- ✅ Total 6/6 tournament confirmed
- ✅ Minden tournament ready for enrollment

---

## 🐛 HIBAKEZELÉS

### Timeout Issues:
- Minden Playwright action előtt: `page.wait_for_timeout(500-2000ms)`
- Selectbox click után: `page.wait_for_timeout(1000ms)`
- Submit után: `page.wait_for_timeout(3000ms)` (API processing)

### Element Not Found:
- Retry logic: 3 attempts with 2s wait
- Screenshot mentése hiba esetén: `error_{timestamp}.png`
- Fallback API call-ra ha UI nem működik

### API Failures:
- Assert response.status_code in [200, 201]
- Log teljes response body hiba esetén
- Continue to next tournament (ne failolja az egész tesztet)

---

## 📊 PYTEST Konfiguráció

```python
# pytest.ini vagy conftest.py
[pytest]
markers =
    tournament_creation: Tournament creation tests
    tournament_application: Application workflow tests
    tournament_invitation: Invitation workflow tests
    tournament_full: Full tournament workflow (all 3 above)

# Futtatás filterrel:
pytest -m tournament_creation --headed --slowmo 500
pytest -m tournament_application --headed --slowmo 500
pytest -m tournament_invitation --headed --slowmo 500
pytest -m tournament_full --headed --slowmo 500
```

---

## 🎬 KÖVETKEZŐ LÉPÉSEK

1. **Review** - Ellenőrizzük ezt a workflow tervet
2. **Checkpoint Scripts** - Készítsünk restore/save script-eket
3. **Headed Mode Fix** - Playwright headed mode proper config
4. **Master Test** - Egyesítsük a 3 tesztet egy master file-ba (opcionális)
5. **RUN** - Futtassuk végig headed mode-ban, lépésről lépésre láthatóan

