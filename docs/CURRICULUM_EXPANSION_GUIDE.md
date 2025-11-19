# 📚 Curriculum Bővítési Útmutató

## 🎯 Áttekintés

Ez a dokumentum leírja, hogyan lehet a minimális curriculum struktúrát fokozatosan bővíteni valódi szakmai tartalommal.

## 🏗️ Jelenlegi Struktúra

### Alapvető felépítés:

```
Specialization (PLAYER/COACH/INTERNSHIP)
  └── Track (curriculum kategória)
       └── Module (szintenként 1 darab)
            └── Components (3 darab/modul)
                 ├── Theory (elméleti anyag)
                 ├── Quiz (tudásellenőrző)
                 └── Practice (gyakorlat)
```

### Szintek száma specializációnként:

- **PLAYER**: 8 szint → 8 modul → 24 komponens
- **COACH**: 8 szint → 8 modul → 24 komponens
- **INTERNSHIP**: 3 szint → 3 modul → 9 komponens

**Összes**: 19 modul, 57 komponens

---

## 🚀 Gyors Kezdés

### 1. Előfeltételek ellenőrzése

```bash
# Adatbázis migrációk futtatása
alembic upgrade head

# Tesztelés, hogy minden szint létezik-e
python scripts/test_curriculum_structure.py
```

### 2. Minimális struktúra generálása

```bash
# Placeholder modulok létrehozása
python scripts/create_minimal_curriculum_structure.py
```

### 3. Eredmény ellenőrzése

```bash
# Újra tesztelés
python scripts/test_curriculum_structure.py
```

---

## 📝 Manuális Bővítés Lépései

### 1. Modul Tartalom Frissítése

**SQL módszer** (gyors, közvetlen):

```sql
-- Modul leírás frissítése
UPDATE modules
SET description = 'Valódi szakmai leírás...',
    learning_objectives = '["Cél 1", "Cél 2", "Cél 3"]'::json
WHERE name = 'Level 1: Bambusz Tanítvány';
```

**Python módszer** (programozott):

```python
from app.database import SessionLocal
from app.models.track import Module

db = SessionLocal()

module = db.query(Module).filter(
    Module.name == 'Level 1: Bambusz Tanítvány'
).first()

module.description = 'Valódi szakmai leírás...'
module.learning_objectives = [
    'Alapmozgások elsajátítása',
    'Ganball™️ szabályok ismerete',
    'Csapatjáték alapok'
]

db.commit()
db.close()
```

### 2. Theory Komponens Bővítése

```python
from app.models.track import ModuleComponent

component = db.query(ModuleComponent).filter(
    ModuleComponent.type == 'theory',
    ModuleComponent.name.like('%Level 1%')
).first()

component.description = 'Részletes elméleti anyag'
component.component_data = {
    'content_type': 'markdown',
    'content': '''
# Bambusz Tanítvány - Elméleti Alapok

## Bevezetés
...valódi tartalom...

## Ganball™️ Szabályok
...
    ''',
    'resources': [
        {'type': 'video', 'url': 'https://...'},
        {'type': 'pdf', 'url': 'https://...'}
    ],
    'placeholder': False  # Jelzi, hogy már nem placeholder
}

db.commit()
```

### 3. Quiz Komponens Bővítése

```python
component = db.query(ModuleComponent).filter(
    ModuleComponent.type == 'quiz',
    ModuleComponent.name.like('%Level 1%')
).first()

component.component_data = {
    'questions': [
        {
            'id': 1,
            'type': 'multiple_choice',
            'question': 'Mi a Ganball™️ alapszabálya?',
            'options': [
                'Kézzel is játszható',
                'Csak lábbal',
                'Nincs szabály',
                'Függ a helyzetől'
            ],
            'correct_answer': 1,
            'explanation': 'A Ganball™️ lábfutball, kézzel nem érinthető.'
        },
        # ... további kérdések
    ],
    'passing_score': 80,
    'time_limit_minutes': 20,
    'placeholder': False
}

db.commit()
```

### 4. Practice Komponens Bővítése

```python
component = db.query(ModuleComponent).filter(
    ModuleComponent.type == 'practice',
    ModuleComponent.name.like('%Level 1%')
).first()

component.component_data = {
    'exercise_type': 'hands_on',
    'tasks': [
        {
            'id': 1,
            'title': 'Alapmozgások gyakorlása',
            'description': 'Vezetés 10 méteren keresztül',
            'success_criteria': 'Hibátlan végrehajtás 3-ból 3 alkalommal',
            'estimated_minutes': 15
        },
        # ... további feladatok
    ],
    'evaluation_method': 'instructor_review',
    'placeholder': False
}

db.commit()
```

---

## 🔄 Tömeges Bővítés (Batch Update)

### Szkript sablon nagy mennyiségű adat betöltésére:

```python
#!/usr/bin/env python3
"""
Batch curriculum content update
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal
from app.models.track import Track, Module, ModuleComponent
import json

def load_content_from_json(filepath: str):
    """JSON fájlból tartalom betöltése"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def update_player_curriculum():
    db = SessionLocal()

    # JSON fájl betöltése
    content = load_content_from_json('data/player_curriculum.json')

    track = db.query(Track).filter(Track.code == 'PLAYER').first()

    for level_data in content['levels']:
        module = db.query(Module).filter(
            Module.track_id == track.id,
            Module.order_in_track == level_data['level_number']
        ).first()

        if module:
            # Modul frissítése
            module.description = level_data['description']
            module.learning_objectives = level_data['objectives']

            # Komponensek frissítése
            for comp_data in level_data['components']:
                component = db.query(ModuleComponent).filter(
                    ModuleComponent.module_id == module.id,
                    ModuleComponent.type == comp_data['type']
                ).first()

                if component:
                    component.description = comp_data['description']
                    component.component_data = comp_data['data']

    db.commit()
    db.close()
    print("✅ Player curriculum frissítve")

if __name__ == '__main__':
    update_player_curriculum()
```

### JSON sablon (`data/player_curriculum.json`):

```json
{
  "specialization": "PLAYER",
  "levels": [
    {
      "level_number": 1,
      "name": "Bambusz Tanítvány",
      "description": "Alapmozgások, Ganball™️ ismeret, játékszabályok",
      "objectives": [
        "Alapmozgások elsajátítása",
        "Ganball™️ szabályok ismerete",
        "Csapatjáték alapok"
      ],
      "components": [
        {
          "type": "theory",
          "description": "Elméleti alapok - Bambusz Tanítvány",
          "data": {
            "content_type": "markdown",
            "content": "# Valódi tartalom...",
            "placeholder": false
          }
        },
        {
          "type": "quiz",
          "description": "Tudásellenőrző kvíz",
          "data": {
            "questions": [...],
            "passing_score": 80,
            "placeholder": false
          }
        },
        {
          "type": "practice",
          "description": "Gyakorlati feladatok",
          "data": {
            "tasks": [...],
            "placeholder": false
          }
        }
      ]
    }
    // ... további szintek
  ]
}
```

---

## 📊 Haladás Követése

### Placeholder státusz ellenőrzése:

```sql
-- Hány komponens még placeholder?
SELECT
    m.name AS module_name,
    mc.type,
    mc.component_data->>'placeholder' AS is_placeholder
FROM module_components mc
JOIN modules m ON mc.module_id = m.id
WHERE mc.component_data->>'placeholder' = 'true';
```

### Python ellenőrzés:

```python
from app.database import SessionLocal
from app.models.track import ModuleComponent
from sqlalchemy import func

db = SessionLocal()

placeholder_count = db.query(func.count(ModuleComponent.id)).filter(
    ModuleComponent.component_data['placeholder'].astext == 'true'
).scalar()

total_count = db.query(func.count(ModuleComponent.id)).scalar()

completion_rate = ((total_count - placeholder_count) / total_count * 100)

print(f"Kitöltöttség: {completion_rate:.1f}%")
print(f"Placeholder: {placeholder_count}/{total_count}")
```

---

## 🎓 Best Practices

### ✅ DO (Csináld):

1. **Fokozatos bővítés**: Egy specializációval kezdj
2. **Tesztelés**: Minden frissítés után futtasd a tesztet
3. **Verziókövetés**: JSON fájlokban tárold a tartalmat
4. **Backup**: Készíts mentést bővítés előtt
5. **Placeholder flag**: Állítsd `false`-ra frissítéskor

### ❌ DON'T (Ne csináld):

1. **Ne töröld** a meglévő modulokat, csak frissítsd
2. **Ne változtasd** a modul/komponens ID-kat
3. **Ne módosítsd** a struktúrát migration nélkül
4. **Ne felejts** tesztelni
5. **Ne hagyj** árva komponenseket

---

## 🧪 Folyamatos Tesztelés

### Automatizált ellenőrzés:

```bash
# CI/CD pipeline-ba beépíthető
python scripts/test_curriculum_structure.py

# Exit code ellenőrzése
if [ $? -eq 0 ]; then
    echo "✅ Curriculum struktúra rendben"
else
    echo "❌ Hiba a struktúrában"
    exit 1
fi
```

---

## 📁 Fájlszerkezet

```
practice_booking_system/
├── scripts/
│   ├── create_minimal_curriculum_structure.py  # Generátor
│   ├── test_curriculum_structure.py            # Tesztelő
│   └── batch_update_curriculum.py              # Tömeges frissítő
├── data/
│   ├── player_curriculum.json                  # Player tartalom
│   ├── coach_curriculum.json                   # Coach tartalom
│   └── internship_curriculum.json              # Internship tartalom
├── docs/
│   └── CURRICULUM_EXPANSION_GUIDE.md           # Ez a dokumentum
└── alembic/versions/
    └── 2025_10_09_2200-create_curriculum_system.py
```

---

## 🚦 Következő Lépések

1. **Futtasd a generátort**: `python scripts/create_minimal_curriculum_structure.py`
2. **Ellenőrizd**: `python scripts/test_curriculum_structure.py`
3. **Válassz egy specializációt** és kezdj el tartalmat tölteni
4. **Tesztelj gyakran**: minden nagyobb változtatás után
5. **Dokumentáld**: milyen tartalmat töltöttél fel

---

## ❓ Gyakori Kérdések

### Q: Hány komponens lehet egy modulban?

**A**: Nincs limit, de az ajánlott minimum 3 (theory, quiz, practice). Bővítheted további típusokkal: video, assignment, project stb.

### Q: Mi van, ha több modult akarok egy szinten?

**A**: Módosítsd a generátor szkriptet, vagy adj hozzá manuálisan új modulokat SQL-ben/Python-ban.

### Q: Lehet specializációnként eltérő komponens típus?

**A**: Igen! A `component_data` JSON mező tetszőleges struktúrát támogat specializációnként.

### Q: Hogyan törlöm a placeholder adatokat?

**A**: NE töröld! Frissítsd a `placeholder: false` értékre és töltsd fel valódi tartalommal.

---

## 📞 Support

Kérdések esetén:
- Nézd meg a teszt kimenetét: `python scripts/test_curriculum_structure.py`
- Ellenőrizd az adatbázis logokat
- Konzultálj a fejlesztői csapattal

---

**Utolsó frissítés**: 2025-10-25
**Verzió**: 1.0
**Készítette**: Claude Code Assistant
