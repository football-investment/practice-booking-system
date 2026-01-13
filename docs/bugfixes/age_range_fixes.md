# Hibás Korhatárok - Teljes Lista és Javítási Terv

## Dátum: 2025-12-28

---

## 🎯 Helyes Korhatárok (LFA Player)

**FINAL BUSINESS RULES:**
- **PRE**: 5-13 év (automatikus, nem lehet felülírni)
- **YOUTH**: 14-18 év (automatikus alapértelmezett, instructor felülírhatja AMATEUR/PRO-ra)
- **AMATEUR**: 14+ év (instructor rendeli hozzá)
- **PRO**: 14+ év (instructor rendeli hozzá)

**HIBÁS RÉGI KORHATÁROK** (amiket javítani kell):
- ❌ PRE: 5-8 év
- ❌ YOUTH: 9-14 év
- ❌ AMATEUR: 14-15 év
- ❌ PRO: 16+ év

---

## 📋 Javítandó Fájlok Listája

### ✅ MÁR JAVÍTVA (3 fájl):

1. ✅ **streamlit_app/pages/LFA_Player_Onboarding.py** - Age category display logic (Lines 232-239)
2. ✅ **streamlit_app/pages/LFA_Player_Dashboard.py** - `get_age_category_for_season()` és `get_age_category_info()` (Lines 201-248)
3. ✅ **config/specializations/lfa_football_player.json** - Age group definitions (Lines 12-31) - RÉSZBEN (lásd alább)

---

### ⚠️ KRITIKUS - Javítandó Config Fájlok (2 hely):

#### 1. **config/specializations/lfa_football_player.json**

**Probléma**: A `requirements.min_age` mezők még mindig 16-ot tartalmaznak a PRO szintekhez

**Hibás sorok**:
- Line 150: `"min_age": 16` (Level 7 - PRO)
- Line 167: `"min_age": 16` (Level 8 - PRO Elite)

**Javítás**:
- Mindkettőt 14-re kell változtatni (14+ év, instructor hozzárendelt)

**Indoklás**:
- A PRO kategória 14 éves kortól elérhető, DE csak instructor hozzárendeléssel
- A `min_age: 16` azt jelenti, hogy 16 év alatt nem kaphat PRO licenszt
- Ez ELLENTMOND az új szabályoknak, ahol 14+ instructor dönt

---

### 🔧 BACKEND - Python Fájlok (8 fájl, ~30+ hely):

#### 2. **app/models/specialization.py**

**Hibás sorok** (docstring):
- Line 23: `LFA_PLAYER_PRE: Semesters for PRE age group (5-8 years)`
- Line 24: `LFA_PLAYER_YOUTH: Semesters for YOUTH age group (9-14 years)`
- Line 25: `LFA_PLAYER_AMATEUR: Semesters for AMATEUR age group (14-15 years)`

**Javítás**:
```python
- LFA_PLAYER_PRE: Semesters for PRE age group (5-13 years) - SEASON TYPE ONLY
- LFA_PLAYER_YOUTH: Semesters for YOUTH age group (14-18 years) - SEASON TYPE ONLY
- LFA_PLAYER_AMATEUR: Semesters for AMATEUR age group (14+ years, instructor assigned) - SEASON TYPE ONLY
```

---

#### 3. **app/api/web_routes/helpers.py**

**Hibás sorok** (get_lfa_age_category függvény):
- Line 112: `- PRE (5-8 years): Foundation Years - Monthly semesters`
- Line 113: `- YOUTH (9-14 years): Technical Development - Quarterly semesters`
- Line 124: `return "PRE", "PRE (Foundation Years)", "5-8 years", f"Age {age} - Monthly training blocks"`
- Line 126: `return "YOUTH", "YOUTH (Technical Development)", "9-14 years", f"Age {age} - Quarterly programs"`

**Javítás**:
```python
- Line 112: "PRE (5-13 years): Foundation Years - Monthly semesters"
- Line 113: "YOUTH (14-18 years): Technical Development - Quarterly semesters"
- Line 124: return "PRE", "PRE (Foundation Years)", "5-13 years", f"Age {age} - Monthly training blocks"
- Line 126: return "YOUTH", "YOUTH (Technical Development)", "14-18 years", f"Age {age} - Quarterly programs"
```

**PLUS**: A függvény logikáját is javítani kell (5-13 → PRE, 14-18 → YOUTH)

---

#### 4. **app/api/web_routes/dashboard.py**

**Hibás sorok** (duplikált függvény):
- Line 462: `- PRE (5-8 years): Foundation Years - Monthly semesters`
- Line 463: `- YOUTH (9-14 years): Technical Development - Quarterly semesters`
- Line 476: `return "PRE", "PRE (Foundation Years)", "5-8 years", f"Age {age} - Monthly training blocks"`
- Line 478: `return "YOUTH", "YOUTH (Technical Development)", "9-14 years", f"Age {age} - Quarterly programs"`

**Javítás**: Ugyanaz, mint helpers.py

---

#### 5. **app/api/web_routes/admin.py**

**Hibás sorok** (3 display map, 6 sor összesen):
- Line 509: `"LFA_PLAYER_PRE": "LFA Player PRE (Ages 5-8)"`
- Line 510: `"LFA_PLAYER_YOUTH": "LFA Player Youth (Ages 9-14)"`
- Line 589: `"LFA_PLAYER_PRE": "LFA Player PRE (Ages 5-8)"`
- Line 590: `"LFA_PLAYER_YOUTH": "LFA Player Youth (Ages 9-14)"`
- Line 649: `"LFA_PLAYER_PRE": "LFA Player PRE (Ages 5-8)"`
- Line 650: `"LFA_PLAYER_YOUTH": "LFA Player Youth (Ages 9-14)"`

**Javítás**:
```python
"LFA_PLAYER_PRE": "LFA Player PRE (Ages 5-13)"
"LFA_PLAYER_YOUTH": "LFA Player Youth (Ages 14-18)"
```

---

#### 6. **app/api/web_routes/instructor_dashboard.py**

**Hibás sorok** (3 display map, 6 sor összesen):
- Line 132: `"LFA_PLAYER_PRE": "LFA Player PRE (Ages 5-8)"`
- Line 133: `"LFA_PLAYER_YOUTH": "LFA Player Youth (Ages 9-14)"`
- Line 212: `"LFA_PLAYER_PRE": "LFA Player PRE (Ages 5-8)"`
- Line 213: `"LFA_PLAYER_YOUTH": "LFA Player Youth (Ages 9-14)"`
- Line 272: `"LFA_PLAYER_PRE": "LFA Player PRE (Ages 5-8)"`
- Line 273: `"LFA_PLAYER_YOUTH": "LFA Player Youth (Ages 9-14)"`

**Javítás**: Ugyanaz, mint admin.py

---

#### 7. **app/utils/age_requirements.py**

**Hibás sorok** (docstring/display text):
- Line 53: `level_info = "Pre Level (Ages 5-8)"`
- Line 55: `level_info = "Youth Level (Ages 9-14)"`

**Javítás**:
```python
level_info = "Pre Level (Ages 5-13)"
level_info = "Youth Level (Ages 14-18)"
```

---

#### 8. **app/services/specs/semester_based/lfa_coach_service.py**

**Hibás sorok** (LFA Coach age group descriptions, 10+ sor):
- Line 12: `1. PRE_ASSISTANT - LFA Pre Football Assistant Coach (Ages 5-8)`
- Line 13: `2. PRE_HEAD - LFA Pre Football Head Coach (Ages 5-8)`
- Line 14: `3. YOUTH_ASSISTANT - LFA Youth Football Assistant Coach (Ages 9-14)`
- Line 15: `4. YOUTH_HEAD - LFA Youth Football Head Coach (Ages 9-14)`
- Line 51: `'PRE_ASSISTANT',         # L1 - Pre (5-8) Assistant`
- Line 52: `'PRE_HEAD',              # L2 - Pre (5-8) Head`
- Line 53: `'YOUTH_ASSISTANT',       # L3 - Youth (9-14) Assistant`
- Line 54: `'YOUTH_HEAD',            # L4 - Youth (9-14) Head`
- Line 65: `'age_group': 'Pre (5-8 years)'`
- Line 81: `'age_group': 'Pre (5-8 years)'`
- Line 97: `'age_group': 'Youth (9-14 years)'`
- Line 113: `'age_group': 'Youth (9-14 years)'`
- Line 415: `achievements.append({"name": "Youth Specialist", "description": "Certified to coach Youth (9-14)"})`

**Javítás**:
```python
"Ages 5-8" → "Ages 5-13"
"Ages 9-14" → "Ages 14-18"
"Youth (9-14)" → "Youth (14-18)"
```

**MEGJEGYZÉS**: Ez a Coach service, nem Player! De konzisztenciát kell tartani.

---

### 📝 TESZTEK - Frissítendő Assertions (2 fájl):

#### 9. **tests/integration/test_lfa_coach_service.py**

**Hibás sor**:
- Line 277: Teszt assertion, ami a régi korhatárokat ellenőrzi

**Javítás**: Frissíteni kell az elvárásokat az új korhatárokkal

---

#### 10. **tests/integration/test_lfa_coach_service_simple.py**

**Hibás sorok**:
- Line 110: Teszt assertion
- Lines 265-268: Teszt assertions

**Javítás**: Ugyanaz, mint fent

---

### 🗂️ DOKUMENTÁCIÓ - Frissítendő (4 fájl):

#### 11. **AGE_CATEGORY_IMPLEMENTATION_SUMMARY.md**
- Ez már tartalmazza a helyes korhatárokat, de lehet régi példák vannak benne

#### 12. **app/templates/about_specializations.html**
- Lehet, hogy van benne korhatár leírás

#### 13. **implementation/01_database_migration/01_create_lfa_player_licenses.sql**
- SQL script - csak dokumentációs célból van

#### 14. **implementation/01_database_migration/04_create_coach_licenses.sql**
- SQL script - csak dokumentációs célból van

#### 15. **config/specializations/internship.json**
- Lehet, hogy van benne LFA Player hivatkozás

#### 16. **config/specializations/lfa_coach.json**
- Coach config - lehet benne korhatár leírás

---

## 🎯 Javítási Sorrend

### FÁZIS 1 - KRITIKUS (Config fájl):
1. ✅ config/specializations/lfa_football_player.json (Lines 150, 167) - `min_age: 16 → 14`

### FÁZIS 2 - BACKEND (Python fájlok):
2. app/models/specialization.py (3 sor)
3. app/api/web_routes/helpers.py (4 sor)
4. app/api/web_routes/dashboard.py (4 sor)
5. app/api/web_routes/admin.py (6 sor)
6. app/api/web_routes/instructor_dashboard.py (6 sor)
7. app/utils/age_requirements.py (2 sor)
8. app/services/specs/semester_based/lfa_coach_service.py (13 sor)

### FÁZIS 3 - TESZTEK:
9. tests/integration/test_lfa_coach_service.py
10. tests/integration/test_lfa_coach_service_simple.py

### FÁZIS 4 - DOKUMENTÁCIÓ (később):
11-16. Dokumentációs fájlok

---

## 📊 Összesítés

**Összesen**: 16 fájl
- ✅ **Javítva**: 3 fájl (Onboarding, Dashboard, Config részben)
- ⚠️ **Javítandó kritikus**: 1 fájl (Config min_age)
- 🔧 **Javítandó backend**: 7 fájl (~38 sor)
- 📝 **Javítandó tesztek**: 2 fájl (~5 sor)
- 🗂️ **Dokumentáció**: 6 fájl (később)

**Következő lépés**: FÁZIS 1 - Config fájl min_age javítása

---
