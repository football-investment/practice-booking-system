# 🏗️ Curriculum Struktúra - Gyors Kezdés

## 📋 Összefoglaló

Egyszerű, moduláris curriculum rendszer **placeholder** adatokkal, amely később fokozatosan bővíthető valódi szakmai tartalommal.

---

## 🚀 Gyors Telepítés

### 1️⃣ Migráció futtatása

```bash
alembic upgrade head
```

Ez létrehozza:
- ✅ Specialization táblákat (PLAYER, COACH, INTERNSHIP)
- ✅ Level táblákat (player_levels, coach_levels, internship_levels)
- ✅ Track/Module/Component táblákat

### 2️⃣ Placeholder struktúra generálása

```bash
python scripts/create_minimal_curriculum_structure.py
```

Létrehozza:
- **3 Track**: PLAYER, COACH, INTERNSHIP
- **19 Modul**: szintenként 1 darab
- **57 Komponens**: modulonként 3 darab (theory, quiz, practice)

### 3️⃣ Tesztelés

```bash
python scripts/test_curriculum_structure.py
```

Ellenőrzi:
- ✅ Adatbázis kapcsolat
- ✅ Specializációk létezése
- ✅ Szintek száma (8, 8, 3)
- ✅ Track-ek létezése
- ✅ Modulok száma
- ✅ Komponensek száma
- ✅ Adatok integritása
- ✅ Kapcsolatok helyessége
- ✅ Skálázhatóság

---

## 📊 Jelenlegi Struktúra

```
┌─────────────────────────────────────────────────────────┐
│  PLAYER Specialization (8 szint)                        │
├─────────────────────────────────────────────────────────┤
│  Track: GānCuju™© Player Program                        │
│    └── 8 Modul (Level 1-8)                              │
│         └── 24 Komponens (3/modul)                      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  COACH Specialization (8 szint)                         │
├─────────────────────────────────────────────────────────┤
│  Track: LFA Coach Development Program                   │
│    └── 8 Modul (Level 1-8)                              │
│         └── 24 Komponens (3/modul)                      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  INTERNSHIP Specialization (3 szint)                    │
├─────────────────────────────────────────────────────────┤
│  Track: Startup Spirit Internship                       │
│    └── 3 Modul (Level 1-3)                              │
│         └── 9 Komponens (3/modul)                       │
└─────────────────────────────────────────────────────────┘
```

**Összes**: 3 Track, 19 Modul, 57 Komponens

---

## 🎯 Adatok Forrása

### ✅ **Adatbázisból származó adatok**:

- Szint nevek (pl. "Bambusz Tanítvány", "LFA Pre Football Asszisztens Edző")
- Követelmények (required_xp, required_sessions, theory_hours, practice_hours)
- Leírások, licensz címek
- Színek (PlayerLevel)

**Fájl**: `alembic/versions/2025_10_09_1030-create_specialization_level_system.py`

### 📝 **Placeholder adatok (generátor)**:

- Track-ek (name, code, description)
- Modulok (name, description, learning_objectives)
- Komponensek (theory, quiz, practice alapstruktúra)

**Fájl**: `scripts/create_minimal_curriculum_structure.py`

---

## 🔧 Szkriptek

| Szkript | Funkció | Futtatás |
|---------|---------|----------|
| **create_minimal_curriculum_structure.py** | Placeholder struktúra generálása | `python scripts/create_minimal_curriculum_structure.py` |
| **test_curriculum_structure.py** | Automatizált tesztelés | `python scripts/test_curriculum_structure.py` |

---

## 📚 Bővítési Folyamat

### 1. Egyedi modul frissítése (SQL):

```sql
UPDATE modules
SET description = 'Valódi szakmai leírás'
WHERE name = 'Level 1: Bambusz Tanítvány';
```

### 2. Komponens tartalom frissítése (Python):

```python
from app.database import SessionLocal
from app.models.track import ModuleComponent

db = SessionLocal()

component = db.query(ModuleComponent).filter(
    ModuleComponent.type == 'theory',
    ModuleComponent.name.like('%Level 1%')
).first()

component.component_data = {
    'content_type': 'markdown',
    'content': '# Valódi tartalom...',
    'placeholder': False  # Jelzi, hogy kitöltött
}

db.commit()
db.close()
```

### 3. Részletes útmutató:

Lásd: **[docs/CURRICULUM_EXPANSION_GUIDE.md](docs/CURRICULUM_EXPANSION_GUIDE.md)**

---

## ✅ Előnyök

| Szempont | Érték |
|----------|-------|
| **Memória** | ~0.1MB (kompakt) |
| **Skálázhatóság** | Kiváló (fokozatos bővítés) |
| **Tesztelhetőség** | Automatizált |
| **Karbantarthatóság** | Egyszerű |
| **Bővíthetőség** | Manuális vagy batch |

---

## 🧪 Tesztelési Kimenet Példa

```
🧪 CURRICULUM STRUKTÚRA AUTOMATIZÁLT TESZTELÉS
======================================================================

✅ PASS | Database Connection
   └─ Sikeres kapcsolat az adatbázishoz

✅ PASS | Specializations Exist
   └─ Mind a 3 specializáció megtalálható: PLAYER, COACH, INTERNSHIP

✅ PASS | PlayerLevel Count
   └─ 8 szint (várt: 8)

✅ PASS | CoachLevel Count
   └─ 8 szint (várt: 8)

✅ PASS | InternshipLevel Count
   └─ 3 szint (várt: 3)

✅ PASS | Tracks Exist
   └─ Mind a 3 track megtalálható: PLAYER, COACH, INTERNSHIP

✅ PASS | Modules for PLAYER
   └─ 8 modul (várt: 8)

✅ PASS | Components Exist
   └─ 57 komponens (19 modul × 3 = 57 minimum)

======================================================================
📈 Összesítés:
   Sikeres: 15/15 (100.0%)
   Sikertelen: 0/15

🎉 MINDEN TESZT SIKERES! A curriculum struktúra megfelelő.
======================================================================
```

---

## 📁 Fájlstruktúra

```
practice_booking_system/
├── scripts/
│   ├── create_minimal_curriculum_structure.py  ← Generátor
│   └── test_curriculum_structure.py            ← Tesztelő
├── docs/
│   └── CURRICULUM_EXPANSION_GUIDE.md           ← Bővítési útmutató
├── alembic/versions/
│   ├── 2025_10_09_1030-create_specialization_level_system.py
│   └── 2025_09_20_1600-gancuju_license_system.py
└── CURRICULUM_SETUP_README.md                  ← Ez a fájl
```

---

## 🎯 Következő Lépések

1. ✅ Migráció futtatása: `alembic upgrade head`
2. ✅ Struktúra generálása: `python scripts/create_minimal_curriculum_structure.py`
3. ✅ Tesztelés: `python scripts/test_curriculum_structure.py`
4. 📝 Tartalom töltése: Lásd [CURRICULUM_EXPANSION_GUIDE.md](docs/CURRICULUM_EXPANSION_GUIDE.md)
5. 🧪 Folyamatos tesztelés minden frissítés után

---

## ❓ Gyakori Kérdések

### Q: Mi a különbség a migration és a generátor között?

**Migration**: Táblák létrehozása + szintek feltöltése (PlayerLevel, CoachLevel stb.)
**Generátor**: Track/Module/Component placeholder adatok létrehozása

### Q: Törölhetem a placeholder adatokat?

**NE!** Frissítsd őket valódi tartalommal, és állítsd `placeholder: false`-ra.

### Q: Hol tárolom a valódi tartalmat?

JSON fájlokban (`data/player_curriculum.json`) vagy közvetlenül az adatbázisban.

### Q: Mennyi ideig tart a teljes bővítés?

Specializációnként ~2-4 óra szakmai tartalommal való feltöltés.

---

## 📞 Support

- **Teszt hiba?** → Futtasd: `python scripts/test_curriculum_structure.py`
- **Adatbázis hiba?** → Ellenőrizd: `alembic upgrade head`
- **Bővítési kérdés?** → Olvasd: `docs/CURRICULUM_EXPANSION_GUIDE.md`

---

**Készítette**: Claude Code Assistant
**Dátum**: 2025-10-25
**Verzió**: 1.0
