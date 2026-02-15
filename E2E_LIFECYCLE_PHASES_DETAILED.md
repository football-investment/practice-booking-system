# E2E Lifecycle Phases - Detailed Specification

**Date**: 2026-02-10
**Purpose**: Pontosan definiálni minden lifecycle phase-t, lépésről lépésre

---

## Phase 0: Clean DB Setup → 📸 Snapshot

**Cél**: Tiszta, reprodukálható kezdőállapot létrehozása minden tesztfutáshoz.

**Mit csinál pontosan**:

Ez a phase előkészíti az adatbázist a teszteléshez úgy, hogy egy teljesen üres, de működőképes állapotot hoz létre. Először leállítja az összes futó adatbázis kapcsolatot, majd törli az összes létező táblát a `lfa_intern_system` adatbázisból. Ezután lefuttatja az összes Alembic migrációt, amelyek létrehozzák az aktuális séma szerinti táblastruktúrát. Miután a séma kész, a phase beinjektál minimális rendszeradatokat, amelyek **nélkülözhetetlenek** a rendszer működéséhez, de **nem helyettesítik a UI tesztelést**:
- Létrehoz egy `LFA_FOOTBALL_PLAYER` specialization type-ot a `specialization_types` táblában
- Létrehoz egy aktív `FALL_2026` szemesztert `ACTIVE` státusszal a `semesters` táblában
- Létrehoz egy **test invitation code**-ot (`TEST-E2E-2026-AUTO`) az `invitation_codes` táblában, amelynek `status='active'`, `max_uses=100`, és `specialization_type='LFA_FOOTBALL_PLAYER'` - ezt használja majd a Phase 1 a regisztrációhoz
- Betölti a `game_types` táblába az alapvető játéktípusokat (pl. GânFootvolley), mert ezek nélkül tournament nem hozható létre

**KRITIKUS**: Ezt a phase-t **nem UI-on keresztül** teszi, mert ezek rendszerszintű konfigurációk, nem user-facing funkciók. A user workflow (regisztráció, onboarding, tournament) viszont **csak UI-on keresztül** történik.

Végül a phase elmenti az adatbázis teljes állapotát egy `00_clean_db.sql` snapshot fájlba a `tests_e2e/snapshots/` mappába `pg_dump` használatával. Ez a snapshot tartalmaz minden táblát DROP és CREATE utasításokkal, így bármikor tökéletesen reprodukálható a kiindulási állapot.

**Output**:
- Adatbázis: üres user/tournament táblák, minimal system data
- Snapshot: `tests_e2e/snapshots/00_clean_db.sql`
- DB state: 0 user, 0 tournament, 1 invitation code, 1 specialization, 1 semester

---

## Phase 1: User Registration via UI → 📸 Snapshot

**Cél**: Tesztelni a valós user registration flow-t Playwright-tal, ahogyan egy új user regisztrálna.

**Mit csinál pontosan**:

A phase először visszaállítja az adatbázist a Phase 0 snapshotjára (`00_clean_db.sql`), így biztosan tiszta állapotból indul. Ezután elindít egy headless Chromium böngészőt Playwright-tal, és navigál a `http://localhost:8501` Streamlit home oldalra. A page betöltése után megvárja, amíg a UI teljesen renderelődik (`networkidle` state), majd megkeresi a **"📝 Register with Invitation Code"** gombot. Playwright klikkel erre a gombra, ami átirányítja a user-t a regisztrációs form-ra.

A form-ban a következő mezőket tölti ki Playwright `.fill()` metódussal:
- **First Name**: `E2E`
- **Last Name**: `Test User`
- **Nickname**: `E2E Tester`
- **Email**: `e2e_test_user@lfa.com`
- **Password**: `TestPass123!`
- **Phone**: `+36 20 123 4567`
- **Date of Birth**: `1995-05-15` (st.date_input widget-en keresztül)
- **Nationality**: `Hungarian`
- **Gender**: `Male` (selectbox dropdown)
- **Street Address**: `Test Street 42`
- **City**: `Budapest`
- **Postal Code**: `1011`
- **Country**: `Hungary`
- **Invitation Code**: `TEST-E2E-2026-AUTO` (az a code, amit Phase 0 seedelt)

Miután minden mező kitöltve, Playwright klikkel a **"Register"** submit gombra. A UI JavaScript submitolja a formot a FastAPI backend `/api/v1/auth/register` endpointjára. A phase megvárja a response-t (akár 10 másodpercig, mert lehet lassú a backend), és ellenőrzi, hogy nincs-e error message a UI-on (pl. "Registration failed").

Ezután a phase **direkt adatbázis query-vel** verifikálja, hogy a user tényleg létrejött-e:
- SQL query: `SELECT id, email, name, onboarding_completed FROM users WHERE email = 'e2e_test_user@lfa.com'`
- Ellenőrzi: `email == 'e2e_test_user@lfa.com'`
- Ellenőrzi: `onboarding_completed == false` (KRITIKUS: még NEM onboarded)
- Ellenőrzi: van `id` (a user mentésre került)

Ha minden assertion pass, a phase `pg_dump`-pal elmenti az adatbázis jelenlegi állapotát a `01_user_registered.sql` snapshot fájlba. Ez a snapshot tartalmazza a regisztrált usert, de `onboarding_completed=false` státusszal.

**Output**:
- Adatbázis: 1 user (`e2e_test_user@lfa.com`), onboarding_completed=false
- Snapshot: `tests_e2e/snapshots/01_user_registered.sql`
- Screenshot: `tests_e2e/screenshots/phase_01_registration_success.png`

---

## Phase 2: Onboarding Flow via UI → 📸 Snapshot

**Cél**: Tesztelni a teljes onboarding wizard-ot UI-on keresztül, hogy user `onboarding_completed=true` státuszba kerüljön.

**Mit csinál pontosan**:

A phase visszaállítja az adatbázist a Phase 1 snapshotjára (`01_user_registered.sql`), így a user már létezik, de még nincs onboardolva. Playwright elindít egy új browser sessiont és navigál a Streamlit home page-re (`http://localhost:8501`). Mivel még nincs bejelentkezve, a login formot látja.

Playwright kitölti a login formot:
- **Email**: `e2e_test_user@lfa.com` (Phase 1-ben regisztrált user)
- **Password**: `TestPass123!`

Klikk a **"🔐 Login"** gombra. A backend visszaad egy JWT tokent, a Streamlit session_state-be menti, és a UI auto-redirectel. Mivel a usernek még nincs unlocked specializációja, a Streamlit logika szerint átirányítja a **Specialization Hub** oldalra.

A Specialization Hub-on Playwright megkeresi a **"LFA Football Player"** specialization kártyát (ez az egyetlen elérhető a seed data alapján), és klikkel a **"Unlock Specialization"** gombra. Ez egy POST request-et küld a `/api/v1/user-licenses/` endpointra, ami létrehoz egy `user_license` record-ot a `user_licenses` táblában `is_active=true` és `onboarding_completed=false` értékekkel.

A UI ezután automatikusan átnavigál az **LFA Player Onboarding** oldalra (`pages/LFA_Player_Onboarding.py`). Playwright most végigmegy a **6-step wizard**-on:

**Step 1: Profile & Position**
- Position selector dropdown: választ egy pozíciót (pl. `STRIKER`)
- Klikk: **"Next"** gomb

**Step 2-5: Skills (4 kategória)**
- Minden skill kategóriára (Technical, Physical, Mental, Tactical):
  - Playwright végigmegy az összes slider-en (st.slider widget)
  - Minden slidert **random 40-80 közötti értékre** állít (hogy ne default 50-en maradjon)
  - Klikk: **"Next"** gomb minden kategória után

**Step 6: Goals**
- Kitölti a textarea-t: `My goal is to become a professional football player and improve my skills through LFA training.`
- Klikk: **"Complete Onboarding"** submit gomb

A backend a `/api/v1/user-licenses/{license_id}/complete-onboarding` endpointra POST-olja az adatokat, ami:
- Update-eli a `user_licenses` táblában: `onboarding_completed = true`
- Menteni a position és skills adatokat a megfelelő táblákba

A UI átirányít az **LFA Player Dashboard**-ra, és megjelenik egy success message: `"✅ Onboarding completed! Welcome to LFA Football Player."`

Playwright ekkor **SQL query-vel verifikálja**:
```sql
SELECT ul.onboarding_completed, ul.is_active
FROM user_licenses ul
JOIN users u ON ul.user_id = u.id
WHERE u.email = 'e2e_test_user@lfa.com'
  AND ul.specialization_type = 'LFA_FOOTBALL_PLAYER';
```
- Ellenőrzi: `onboarding_completed == true` ← **KRITIKUS**
- Ellenőrzi: `is_active == true`

Ha pass, elmenti a `02_user_onboarded.sql` snapshotot.

**Output**:
- Adatbázis: user_license.onboarding_completed=true, position saved, skills saved
- Snapshot: `tests_e2e/snapshots/02_user_onboarded.sql`
- Screenshot: `tests_e2e/screenshots/phase_02_onboarding_complete.png`

---

## Phase 3: Sandbox Environment Check → 📸 Snapshot

**Cél**: Verifikálni, hogy az onboarded user hozzáfér-e az LFA Player Dashboard-hoz és a sandbox környezet működik.

**Mit csinál pontosan**:

A phase visszaállítja a Phase 2 snapshotot (`02_user_onboarded.sql`), így a user már teljesen onboarded. Playwright új browser sessiont indít és bejelentkezik ugyanazokkal a credentials-ekkel (`e2e_test_user@lfa.com` / `TestPass123!`). Most viszont a Streamlit már **automatikusan a Player Dashboard-ra** redirectel, mert:
- User-nek van active license (`is_active=true`)
- License onboarding completed (`onboarding_completed=true`)

A dashboard betöltődik, és Playwright ellenőrzi a következőket:

**UI Element Checks**:
- `page.text_content('body')` tartalmazza: `"LFA Player Dashboard"` vagy `"Player Dashboard"` stringet
- `page.text_content('body')` tartalmazza: user nevét (`E2E Test User`)
- Nincs Streamlit error (`[data-testid="stException"]` selector **nem** található)
- Nincs "Traceback" vagy "NoneType error" a page-en

**Sidebar Navigation Check**:
Playwright megpróbálja kinyitni a sidebar-t (ha be van csukva), majd ellenőrzi, hogy a következő navigation linkek **léteznek**:
- `My Profile`
- `Tournament Achievements` (vagy hasonló tournament oldal)
- `My Credits` (ha van ilyen funkció)

Ha bármelyik link hiányzik vagy error van, a teszt fail-el.

**Screenshot Capture**:
Playwright full-page screenshot-ot készít: `phase_03_dashboard_loaded.png`

**No Database Verification Needed** ebben a phase-ben, mert csak UI state-et ellenőrzünk. Ha a dashboard UI betöltődött error nélkül, a sandbox működik.

Végül elmenti a `03_sandbox_ready.sql` snapshotot, bár ez megegyezik a Phase 2 snapshottal (nem történt adatbázis változás), de **konzisztencia** miatt külön snapshot file kell.

**Output**:
- Adatbázis: unchanged (same as Phase 2)
- Snapshot: `tests_e2e/snapshots/03_sandbox_ready.sql`
- Screenshot: `tests_e2e/screenshots/phase_03_dashboard_loaded.png`
- Verification: UI error-free, navigation links exist

---

## Phase 4: Tournament Creation via UI → 📸 Snapshot

**Cél**: Létrehozni egy tournament-et UI-on keresztül "Quick Test" módban, hogy badge-eket generáljon.

**Mit csinál pontosan**:

A phase visszaállítja a Phase 3 snapshotot (`03_sandbox_ready.sql`), így a user bejelentkezett és sandbox-ban van. Playwright navigál a **Tournament Sandbox** oldalra (vagy ahogyan a UI-ban hívják). Ez lehet egy külön oldal vagy egy tab a dashboardon belül - a test adaptálja a meglévő `test_01_quick_test_full_flow.py` logikáját.

**Tournament Configuration Form Fill**:

1. **New Tournament Button**: Playwright klikkel a `"➕ New Tournament"` vagy `"🆕 Create New Tournament"` gombra
2. **Wait for Form**: `page.wait_for_load_state("networkidle")` hogy a form betöltődjön
3. **Tournament Mode Selection**:
   - Megkeresi a `"⚡Quick Test (Auto-complete)"` radio buttont
   - Klikkel rá (ez egy special mode, ami automatikusan lefuttatja a tournament-et)
4. **Game Type Selection** (ha szükséges):
   - Selectbox-ból választ (pl. `GânFootvolley`)
5. **Tournament Type** (pl. League/Knockout):
   - Selectbox: `"League"` (vagy default)
6. **Player Count**:
   - Number input field: `8` (8 játékos, hogy CHAMPION badge legyen értelmes)
7. **Skills to Test** (ha editable):
   - Default skills elfogadása (vagy random kiválasztás)

**Submit & Wait for Completion**:

Playwright klikkel a **"✅ Create Tournament"** gombra. A backend ekkor:
- Létrehoz egy `semester` record-ot `COMPLETED` státusszal
- Generál 8 fake player-t (auto-enrollment Quick Test módban)
- Lefuttat matcheket
- Kiszámolja standings-ot
- **Award badges**-t:
  - Rank 1 player: `CHAMPION` badge + `badge_metadata: {placement: 1, total_participants: 8}`
  - Rank 2 player: `RUNNER_UP` badge + metadata
  - Rank 3 player: `THIRD_PLACE` badge + metadata
  - Minden player: `TOURNAMENT_PARTICIPANT` badge (metadata=null)

A Quick Test mode **auto-completes**, tehát nem kell manual matcheket játszani. Playwright vár (polling loop, max 30 másodperc), amíg a UI-on megjelenik a **"Results"** screen vagy **"Tournament Completed"** message.

**Verification After Completion**:

Playwright **SQL query-vel** ellenőrzi:
```sql
-- Tournament created
SELECT id, code, status FROM semesters
WHERE code LIKE '%QUICK-TEST%' OR status = 'COMPLETED'
ORDER BY created_at DESC LIMIT 1;

-- Badges awarded (focusing on CHAMPION)
SELECT badge_type, badge_metadata
FROM tournament_badges
WHERE semester_id = (SELECT id FROM semesters ORDER BY created_at DESC LIMIT 1)
  AND badge_type = 'CHAMPION';
```

Assertions:
- Van legalább 1 `COMPLETED` tournament a DB-ben
- Van legalább 1 `CHAMPION` badge
- `CHAMPION` badge `badge_metadata` **nem null**
- `badge_metadata` tartalmazza: `{"placement": 1, "total_participants": 8}`

Ha minden assertion pass, screenshot (`phase_04_tournament_results.png`) és snapshot (`04_tournament_completed.sql`).

**Output**:
- Adatbázis: 1 tournament (COMPLETED), 8+ badges (including CHAMPION with metadata)
- Snapshot: `tests_e2e/snapshots/04_tournament_completed.sql`
- Screenshot: `tests_e2e/screenshots/phase_04_tournament_results.png`

---

## Phase 5: Badge DB & API Verification → 📸 Snapshot

**Cél**: Verifikálni, hogy a backend **helyesen serializ álja** a badge metadata-t az API-n keresztül.

**Mit csinál pontosan**:

A phase visszaállítja a Phase 4 snapshotot (`04_tournament_completed.sql`), így a tournament és badge-ek léteznek. Ez a phase **NEM UI teszt**, hanem **backend API contract teszt**. Nem használ Playwright-ot, csak Python `requests` library-t.

**Step 1: Get User ID from DB**:
```python
import psycopg2
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()
cursor.execute("SELECT id FROM users WHERE email = 'e2e_test_user@lfa.com'")
user_id = cursor.fetchone()[0]
```

**Step 2: Direct Database Verification**:
```sql
SELECT
    tb.badge_type,
    tb.badge_metadata,
    s.code AS tournament_code
FROM tournament_badges tb
JOIN semesters s ON tb.semester_id = s.id
WHERE tb.user_id = %s AND tb.badge_type = 'CHAMPION'
ORDER BY tb.created_at DESC
LIMIT 1;
```

Assertions:
- Query returns at least 1 row (user has CHAMPION badge)
- `badge_metadata` column **is not null** (JSON object)
- `badge_metadata['placement']` == 1
- `badge_metadata['total_participants']` == 8

**Step 3: API Contract Verification**:

Login via API to get JWT token:
```python
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "e2e_test_user@lfa.com", "password": "TestPass123!"}
)
token = response.json()["access_token"]
```

Call badges API:
```python
response = requests.get(
    f"http://localhost:8000/api/v1/tournaments/badges/user/{user_id}",
    headers={"Authorization": f"Bearer {token}"}
)
badges = response.json()["badges"]
```

**CRITICAL REGRESSION CHECK** (ezt teszteli a Phase 5):

Assertions on API response:
1. Response status code == 200
2. `badges` is a list
3. Find CHAMPION badge in list: `champion = next(b for b in badges if b["badge_type"] == "CHAMPION")`
4. **CRITICAL**: `champion` dictionary has key `"badge_metadata"` (NOT `"metadata"`)
   - Ha `"metadata"` key található → **FAIL** (ez a commit 2f38506 bug)
   - Ha `"badge_metadata"` hiányzik → **FAIL**
5. `champion["badge_metadata"]` is a dict (not null, not string)
6. `champion["badge_metadata"]["placement"]` == 1
7. `champion["badge_metadata"]["total_participants"]` == 8

**Ez a phase** fogja elkapni a jövőben, ha valaki visszahozza a `"metadata"` → `"badge_metadata"` serialization bug-ot.

Végül snapshot: `05_badges_awarded.sql` (de ez megegyezik Phase 4-gyel, mert nem történt DB változás, csak ellenőriztük).

**Output**:
- Adatbázis: unchanged (same as Phase 4)
- Snapshot: `tests_e2e/snapshots/05_badges_awarded.sql`
- API verification: badge_metadata key correct, placement/total_participants values correct

---

## Phase 6: UI Badge Display → 📸 Snapshot

**Cél**: Verifikálni, hogy a frontend **helyesen jeleníti meg** a CHAMPION badge-et ranking adatokkal.

**Mit csinál pontosan**:

A phase visszaállítja a Phase 5 snapshotot (`05_badges_awarded.sql`). Playwright új browser sessiont indít, bejelentkezik (`e2e_test_user@lfa.com`), és navigál az **LFA Player Dashboard** oldalra, majd a **"🏆 Tournament Achievements"** szekcióhoz.

**Navigation to Tournament Achievements**:

Ha a Tournament Achievements egy külön oldal:
- Playwright klikkel a sidebar linkre: `"Tournament Achievements"`

Ha egy section a dashboard-on:
- Playwright scroll-ol az oldalon, amíg meg nem találja a `"🏆 Tournament Achievements"` heading-et

**Expand Accordions** (ha collapsed):

A tournament achievements általában accordion/expander komponensekben vannak (`st.expander` Streamlit-ben). Playwright végigmegy az összes `[data-testid="stExpander"]` elementen és klikkel a header-re, hogy kinyissa őket:
```python
expanders = page.locator('[data-testid="stExpander"]').all()
for expander in expanders:
    try:
        expander.locator("summary").click()
        time.sleep(0.3)  # Wait for animation
    except:
        pass  # Already expanded or error
```

**Verify CHAMPION Badge Visible**:

Playwright `page.text_content('body')` hívással megkapja az **egész oldal text tartalmát**, majd ellenőrzi:

1. **CHAMPION keyword presence**:
   - `"CHAMPION"` string szerepel valahol a page-en
   - Vagy `"Champion"` vagy `"🏆 Champion"` (case-insensitive check)

2. **Ranking data presence** (CRITICAL REGRESSION CHECK):
   - `"#1 of 8 players"` string **szerepel** a page-en
   - VAGY általánosabban: regex match `r"#\d+ of \d+ players"`
   - Ez azt jelenti, hogy a `badge_metadata.placement` és `badge_metadata.total_participants` eljutott a frontend-re

3. **NO "No ranking data" text** (REGRESSION CHECK):
   - `"No ranking data"` string **NEM szerepel** a page-en
   - Ha szerepel → **FAIL** (ez a bug, amit a commit a013113 és 569808f fixelt)

**Window-based Sliding Check** (mint a `test_champion_badge_regression.py`-ben):

A phase split-eli a page text-et sorokra, majd 15-soros window-kat használ:
```python
lines = page_text.split('\n')
for i, line in enumerate(lines):
    if "CHAMPION" in line:
        window_start = max(0, i - 2)
        window_end = min(len(lines), i + 15)
        window_text = '\n'.join(lines[window_start:window_end])

        # Check if "No ranking data" is in same window as CHAMPION
        if "No ranking data" in window_text:
            raise AssertionError("REGRESSION: CHAMPION badge shows 'No ranking data'")
```

Ez megakadályozza a false positive-ot, amikor egy másik badge-nek van "No ranking data", de a CHAMPION-nak nincs.

**Screenshot Capture**:

Full-page screenshot: `phase_06_champion_badge_display.png`

Végül snapshot: `06_ui_verified.sql` (no DB changes, but final state capture).

**Output**:
- Adatbázis: unchanged (same as Phase 5)
- Snapshot: `tests_e2e/snapshots/06_ui_verified.sql`
- Screenshot: `tests_e2e/screenshots/phase_06_champion_badge_display.png`
- UI verification: CHAMPION visible, ranking data shown, NO "No ranking data" error

---

## Összefoglaló

**Phase 0**: Adatbázis reset + minimal system seed → tiszta kiindulási állapot
**Phase 1**: UI registration flow → user létrehozva, onboarding_completed=false
**Phase 2**: UI onboarding wizard → user_license.onboarding_completed=true
**Phase 3**: Dashboard UI check → sandbox környezet működik, nincs error
**Phase 4**: Tournament creation UI → Quick Test lefut, badges awarded with metadata
**Phase 5**: API contract test → badge_metadata serialization helyes (nem "metadata" key)
**Phase 6**: UI badge display → CHAMPION látható, "#1 of X players" megjelenik

**Full pipeline runtime estimate**: ~90-120 másodperc (headless mode)

**Snapshot restore time**: ~2-3 másodperc/phase (pg_dump restore gyors)

**Debugging benefit**: Ha Phase 5 fail-el → visszaállsz Phase 4 snapshotra, újrafuttatsz 10 másodperc alatt, nem kell 60 másodpercet várni az elejétől.
