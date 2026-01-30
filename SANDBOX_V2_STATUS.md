# Sandbox v2 - Aktuális Állapot és Felhasználás

**Dátum**: 2026-01-27
**Verzió**: Phase 2 COMPLETE
**Állapot**: MVP működik, production-közeli döntésre vár

---

## 🎯 Mire Jó Most (Admin Szemmel)

### 1. **Valós User Tesztelés Tournament Lifecycle-n**
- Admin kiválaszt **konkrét valós usereket** (nem random pool)
- Lefuttat egy teljes tournament lifecycle-t (create → enroll → rankings → rewards → verdict)
- Látja, hogy **adott userekre** milyen hatása lenne egy tournament konfigurációnak

**Use Case**:
*"Van 4 junior internem (ID: 15, 13, 14, 16). Megnézem, hogy egy LEAGUE tournament passing + shooting skill-ekkel hogyan változtatná meg a skill profiljukat."*

### 2. **Skill Progression Előzetes Tesztelés**
- **BEFORE snapshot**: Sandbox látja a skill értékeket tournament előtt
- **AFTER calculation**: Reward distribution után újraszámolja
- **Delta visualization**: Top/Bottom performers alapján látható, ki mennyit fejlődött

**Use Case**:
*"Tesztelni akarom az új skill mapping konfigurációt, mielőtt éles tournamentre használnám. Sandbox-ban lefuttatom, látom a skill változásokat, és ha jó → átemelem production-be."*

### 3. **Admin-Grade Test Builder**
- **User Selection UI**: Keresés, checkbox, skill preview
- **Instructor Assignment** (opcionális): Látszik, de még nincs hatása
- **Teljes konfiguráció**: Tournament type, skills, player count, advanced options

**Use Case**:
*"Új tournament type-ot (pl. hybrid) tesztelek valós user selection-nel, hogy lássam, működik-e a ranking logika és a reward distribution."*

---

## 💼 Milyen Döntésekhez Használható

### ✅ Jelenleg Támogatott Döntések

1. **Tournament Configuration Testing**
   - "Ez a tournament type + skill mapping kombináció működik-e?"
   - "WORKING / NOT_WORKING" verdict azonnal látható

2. **Skill Impact Preview (egyirányú)**
   - "Ha ezeket a usereket ebbe a tournamentbe rakom, mennyit változnak a skilljei?"
   - Top 3 / Bottom 2 performers láthatók

3. **Real User Impact Szimuláció**
   - "Adott 4-8-16 user sorsát követem végig egy tournament flow-n"
   - Látom: enrollment, ranking, reward, skill change

### ⚠️ Korlátozott/Hiányzó Döntéstámogatás

1. **Előzetes Impact Kalkuláció** (nincs preview endpoint)
   - ❌ "Mielőtt lefuttatom, szeretném látni, mi LENNE a hatás"
   - Jelenleg: csak POST után látod az eredményt

2. **Instructor Hatás Számítás** (instructor_ids nincs felhasználva)
   - ❌ "Ha ezt az instructort rendelem hozzá, javul-e a skill gain?"
   - Jelenleg: instructor_ids átmegy, de nincs logika mögötte

3. **Multi-Scenario Összehasonlítás** (nincs batch mode)
   - ❌ "3 különböző konfigurációt szeretnék párhuzamosan futtatni, és összehasonlítani"
   - Jelenleg: egyesével kell futtatni

4. **Historical Tracking** (nincs perzisztens tárolás)
   - ❌ "Múlt heti sandbox futtatás eredményét szeretném újra megnézni"
   - Jelenleg: minden test tournament SANDBOX-* prefix-szel marad DB-ben, de nincs UI rá

---

## 🚧 Mi Hiányzik Production-Közeli Állapothoz

### Kritikus Hiányosságok

1. **Preview/Impact Endpoint (Phase 3 candidate)**
   ```
   POST /sandbox/preview
   Request: { user_ids, tournament_config, skills }
   Response: {
     estimated_skill_changes: {...},
     risk_assessment: "LOW/MEDIUM/HIGH",
     recommendation: "..."
   }
   ```
   **Miért kell**: Admin nem akarja "vakban" lefuttatni a tesztet, előbb megnézné a várható hatást.

2. **Instructor Logic Implementation**
   - `instructor_ids` paraméter átmegy, de nincs felhasználva
   - Nincs instructor impact a skill gain-re (pl. +10% bonus, specialty matching)
   - **Miért kell**: Admin-grade test builder ígérete jelenleg félkész

3. **Sandbox Test History & Comparison UI**
   - Nincs: "Sandbox futtatások listája" screen
   - Nincs: "Test #123 vs Test #124" összehasonlítás
   - **Miért kell**: Döntéshozáshoz kell látni: "múltkor X konfig → Y eredmény, most Z konfig → ?"

4. **Result Export & Sharing**
   - Nincs: CSV export, PDF report
   - Nincs: "Share with instructor" funkció
   - **Miért kell**: Admin le akarja menteni az eredményt, meg akarja osztani kollégákkal

### Finomhangolás

5. **User Selection UX Fejlesztés**
   - Jelenleg: 50 user checkbox list → nehezen kezelhető
   - Kellene: pagination, multi-filter (specialization + skill range), bulk select

6. **Validation & Constraints**
   - Nincs: "user_ids count != player_count" esetén warning
   - Nincs: "user has no active license" pre-check
   - **Miért kell**: Admin ne kapjon NOT_WORKING verdictet apró konfigurációs hiba miatt

7. **Admin Dashboard Integráció**
   - Jelenleg: standalone Streamlit app (localhost:8502)
   - Kellene: beépítve admin dashboard "Testing" tab-ba
   - **Miért kell**: Admin ne 2 külön UI-t használjon

---

## 📊 Jelenlegi Állapot Summary

| Feature | Status | Production-Ready? |
|---------|--------|-------------------|
| Real user selection API | ✅ DONE | ✅ Yes |
| Streamlit UI prototype | ✅ DONE | ⚠️ MVP (standalone) |
| Verdict calculation | ✅ DONE | ✅ Yes |
| Skill progression tracking | ✅ DONE | ✅ Yes |
| Top/Bottom performers | ✅ DONE | ✅ Yes |
| Instructor assignment (parameter) | ✅ DONE | ❌ No logic behind |
| Preview/Impact estimation | ❌ TODO | ❌ Critical missing |
| Test history & comparison | ❌ TODO | ⚠️ Nice to have |
| Admin dashboard integration | ❌ TODO | ⚠️ UX issue |

---

## 🎯 Ajánlás: Következő Lépések Opciói

### Opció A: v3 - Preview & Impact Becslés
**Scope**: Preview endpoint + impact kalkuláció
**Cél**: Admin lássa ELŐRE a várható hatást, mielőtt lefuttatná
**Idő**: ~1-2 nap
**Érték**: ⭐⭐⭐⭐⭐ (kritikus döntéstámogatás)

### Opció B: Admin Dashboard Integráció
**Scope**: Streamlit → React/Vue konverzió, beépítés admin UI-ba
**Cél**: Unified UX, admin 1 helyen használja
**Idő**: ~2-3 nap
**Érték**: ⭐⭐⭐⭐ (UX javulás)

### Opció C: MVP Lezárás + Production Deploy
**Scope**: Jelenlegi állapot clean-up, dokumentáció, deployment
**Cél**: Használható admin tool, korlátokkal
**Idő**: ~0.5 nap
**Érték**: ⭐⭐⭐ (gyors value delivery, korlátokkal)

### Opció D: Instructor Logic + Test History
**Scope**: Instructor impact számítás + sandbox history UI
**Cél**: Teljes Phase 2 promise teljesítése
**Idő**: ~1.5 nap
**Érték**: ⭐⭐⭐⭐ (feature completeness)

---

## 🔍 Tesztelési Útmutató (Admin)

### Quick Start
1. **Backend indítás**:
   ```bash
   DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Streamlit UI indítás**:
   ```bash
   streamlit run streamlit_sandbox.py --server.port 8502
   ```

3. **Böngésző**: http://localhost:8502

4. **Login**: `admin@lfa.com` / `admin123`

5. **User Selection**:
   - Nyisd ki: "👥 User Selection (Phase 2 - Admin-Grade)"
   - ✅ Checkbox: "Use custom user selection"
   - Válassz 4-8 usert
   - Kattints: "🚀 Run Sandbox Test"

6. **Eredmény**: Verdict + Skill Progression + Top/Bottom Performers

### API Tesztelés (Postman/curl)
```bash
# 1. Get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@lfa.com","password":"admin123"}'

# 2. Run test with real users
curl -X POST http://localhost:8000/api/v1/sandbox/run-test \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tournament_type": "league",
    "skills_to_test": ["passing", "dribbling"],
    "player_count": 4,
    "user_ids": [15, 13, 14, 16]
  }'
```

---

## 🏁 Döntési Pont

**Most itt vagyunk**: Phase 2 DONE, MVP működik, valós user selection-nel
**Kérdés admin részére**:
1. Kipróbálod a Streamlit UI-t (localhost:8502)?
2. Elég-e ez MVP-nek, vagy kell v3 (preview)?
3. Integráljuk admin dashboard-ba, vagy marad standalone?

**Várom a döntést, utána folytatjuk.** 🎯
