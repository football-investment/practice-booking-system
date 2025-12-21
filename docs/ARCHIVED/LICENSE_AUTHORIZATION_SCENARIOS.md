# 🔐 Licenc Jogosultságok - Részletes Szcenáriók

## Probléma Megfogalmazása

**Kérdés:** Mire jogosít fel egy instruktor licenc?

**Példa:** Grand Master rendelkezik:
- 8x GānCuju PLAYER licenc (Level 1-8)
- 8x LFA COACH licenc (Level 1-8)
- 5x INTERNSHIP licenc (Level 1-5)

**Mit taníthat ezekkel?**

---

## 📋 Szcenáriók Vizsgálata

### Szcenárió 1: 🏫 **Semester Master Instructor**

**Kérdés:** Milyen szemeszternek lehet Master Instructor?

**Jelenlegi állapot:**
```python
# Semester model
master_instructor_id = Column(Integer, ForeignKey('users.id'), nullable=True)
specialization_type = Column(String(50), nullable=True)  # LFA_PLAYER_PRE, GANCUJU_PLAYER_YOUTH stb.
age_group = Column(String(20), nullable=True)  # PRE, YOUTH, AMATEUR, PRO
```

**Licenc ellenőrzés opciók:**

#### **Opció 1A: Bármely licenc = Master Instructor (jelenlegi)**
- Grand Master PLAYER Level 1 licenccel → lehet Master bármely PLAYER szemeszternek
- ✅ Egyszerű
- ❌ Nem veszi figyelembe a szint progressziót

#### **Opció 1B: Licenc szint ≥ szemeszter korlátja**
```
Példa:
- LFA PLAYER PRE szemeszter → minimum PLAYER Level 1 licenc
- LFA PLAYER YOUTH szemeszter → minimum PLAYER Level 3 licenc
- LFA PLAYER AMATEUR szemeszter → minimum PLAYER Level 5 licenc
- LFA PLAYER PRO szemeszter → minimum PLAYER Level 8 licenc
```

---

### Szcenárió 2: 📚 **Session Tanítás**

**Kérdés:** Milyen sessiont taníthat az instruktor?

**Jelenlegi Session model:**
```python
instructor_id = Column(Integer, ForeignKey("users.id"))
target_specialization = Column(Enum(SpecializationType), nullable=True)
```

**Licenc ellenőrzés opciók:**

#### **Opció 2A: Csak azonos specialization**
```
PLAYER licenc → csak PLAYER sessiont taníthat
COACH licenc → csak COACH sessiont taníthat
INTERNSHIP licenc → csak INTERNSHIP sessiont taníthat
```

#### **Opció 2B: Kereszt-tanítás (COACH licenc mindent fedez)**
```
COACH Level 1-2 (LFA PRE) → taníthat LFA PLAYER PRE sessiont
COACH Level 3-4 (LFA YOUTH) → taníthat LFA PLAYER YOUTH sessiont
COACH Level 5-6 (LFA AMATEUR) → taníthat LFA PLAYER AMATEUR sessiont
COACH Level 7-8 (LFA PRO) → taníthat LFA PLAYER PRO sessiont
```

**Logika:** COACH licenc = tanítói képesítés, ezért taníthat PLAYER sessiont is!

---

### Szcenárió 3: 🎯 **Instructor Assignment (Admin által)**

**Kérdés:** Admin melyik instructort látja elérhetőnek egy semester-hez?

**Jelenlegi állapot:**
```python
# GET /api/v1/instructor-assignments/available-instructors?semester_id=X
# Visszaadja: összes instructor + availability windows
```

**Licenc szűrés opciók:**

#### **Opció 3A: Szigorú specialization match**
```
LFA_PLAYER_PRE semester →
  csak olyan instructor, akinek van PLAYER licenc
```

#### **Opció 3B: COACH licenc = univerzális**
```
LFA_PLAYER_PRE semester →
  PLAYER licenc VAGY COACH Level 1-2 licenc
```

#### **Opció 3C: Licenc szint figyelembevétele**
```
LFA_PLAYER_PRO semester →
  PLAYER Level 8 VAGY COACH Level 7-8

LFA_PLAYER_PRE semester →
  PLAYER Level 1+ VAGY COACH Level 1+
```

---

### Szcenárió 4: 🏀 **GānCuju vs LFA Edzői Jogosultságok**

**Kérdés:** PLAYER licenc taníthat-e COACH sessiont?

**Logika:**
```
PLAYER licenc = játékos képesítés
  → NEM taníthat COACH sessiont (nincs edzői képesítés)

COACH licenc = edzői képesítés
  → TANÍTHAT PLAYER sessiont (edző ismeri a játékot)
```

**Példa:**
```
Grand Master PLAYER Level 8 (Dragon Wisdom):
  ✅ Taníthat PLAYER sessiont
  ❌ NEM taníthat COACH sessiont (nincs COACH licenc)

Grand Master COACH Level 8 (LFA PRO Head):
  ✅ Taníthat COACH sessiont
  ✅ Taníthat PLAYER sessiont (edző ismeri a technikákat)
```

---

### Szcenárió 5: 🎓 **INTERNSHIP Licenc Jogosultságok**

**Kérdés:** INTERNSHIP licenc mire jogosít?

**Lehetőségek:**

#### **Opció 5A: Csak INTERNSHIP sessiont taníthat**
```
INTERNSHIP licenc → csak INTERNSHIP specialization sessiont
```

#### **Opció 5B: Adminisztratív jogok**
```
INTERNSHIP Level 3+ → lehet Master Instructor
INTERNSHIP Level 5 (Principal) → látja az analytics dashboardot
```

---

## 🧠 Javasolt Logika

### **1. Semester Master Instructor jogosultság**

```python
def can_be_master_instructor(instructor, semester):
    """
    Ellenőrzi, hogy instructor lehet-e Master a semesternek.
    """
    semester_spec = semester.specialization_type  # pl. "LFA_PLAYER_PRE"
    semester_age_group = semester.age_group  # pl. "PRE"

    # 1. Kell PLAYER VAGY COACH licenc
    required_spec = extract_base_spec(semester_spec)  # "PLAYER" vagy "COACH"

    # 2. Ellenőrzi licenceket
    for license in instructor.licenses:
        if license.specialization_type == required_spec:
            # Minimum szint ellenőrzése age_group alapján
            min_level = get_min_level_for_age_group(semester_age_group)
            if license.current_level >= min_level:
                return True

        # COACH licenc univerzális (taníthat PLAYER sessiont is)
        if license.specialization_type == "COACH":
            min_level = get_min_coach_level_for_age_group(semester_age_group)
            if license.current_level >= min_level:
                return True

    return False


def get_min_level_for_age_group(age_group):
    """PLAYER licenc minimum szint age_group alapján."""
    return {
        "PRE": 1,      # Level 1+ (Bamboo Student)
        "YOUTH": 3,    # Level 3+ (Flexible Reed)
        "AMATEUR": 5,  # Level 5+ (Strong Root)
        "PRO": 8       # Level 8 (Dragon Wisdom)
    }.get(age_group, 1)


def get_min_coach_level_for_age_group(age_group):
    """COACH licenc minimum szint age_group alapján."""
    return {
        "PRE": 1,      # Level 1-2 (LFA PRE Assistant/Head)
        "YOUTH": 3,    # Level 3-4 (LFA YOUTH Assistant/Head)
        "AMATEUR": 5,  # Level 5-6 (LFA AMATEUR Assistant/Head)
        "PRO": 7       # Level 7-8 (LFA PRO Assistant/Head)
    }.get(age_group, 1)
```

---

### **2. Session Tanítás jogosultság**

```python
def can_teach_session(instructor, session):
    """
    Ellenőrzi, hogy instructor taníthatja-e a sessiont.
    """
    target_spec = session.target_specialization  # pl. "LFA_PLAYER_PRE"

    # 1. Mixed session (mindenki taníthatja)
    if session.mixed_specialization:
        return True

    # 2. Kell PLAYER VAGY COACH licenc
    base_spec = extract_base_spec(target_spec)  # "PLAYER"
    age_group = extract_age_group(target_spec)  # "PRE"

    for license in instructor.licenses:
        # Pontos match
        if license.specialization_type == base_spec:
            min_level = get_min_level_for_age_group(age_group)
            if license.current_level >= min_level:
                return True

        # COACH licenc univerzális
        if license.specialization_type == "COACH" and base_spec == "PLAYER":
            min_level = get_min_coach_level_for_age_group(age_group)
            if license.current_level >= min_level:
                return True

    return False
```

---

### **3. Admin Instructor Availability szűrés**

```python
def filter_available_instructors(semester):
    """
    Admin által látható instructorok szűrése licenc alapján.
    """
    all_instructors = get_all_instructors_with_availability()

    qualified_instructors = []
    for instructor in all_instructors:
        if can_be_master_instructor(instructor, semester):
            qualified_instructors.append({
                "instructor": instructor,
                "matching_licenses": get_matching_licenses(instructor, semester)
            })

    return qualified_instructors


def get_matching_licenses(instructor, semester):
    """
    Visszaadja azokat a licenceket, amik megfelelnek a semesternek.
    """
    matching = []
    semester_age_group = semester.age_group

    for license in instructor.licenses:
        if license.specialization_type == "PLAYER":
            if license.current_level >= get_min_level_for_age_group(semester_age_group):
                matching.append(license)

        elif license.specialization_type == "COACH":
            if license.current_level >= get_min_coach_level_for_age_group(semester_age_group):
                matching.append(license)

    return matching
```

---

## 📊 Példa: Grand Master Jogosultságai

### **Grand Master licencek:**
```
PLAYER:
  🤍 Level 1 - Bamboo Student
  💛 Level 2 - Morning Dew
  💚 Level 3 - Flexible Reed
  💙 Level 4 - Sky River
  🤎 Level 5 - Strong Root
  🩶 Level 6 - Winter Moon
  🖤 Level 7 - Midnight Guardian
  ❤️ Level 8 - Dragon Wisdom

COACH:
  👨‍🏫 Level 1 - LFA PRE Assistant
  👨‍🏫 Level 2 - LFA PRE Head
  👨‍🏫 Level 3 - LFA YOUTH Assistant
  👨‍🏫 Level 4 - LFA YOUTH Head
  👨‍🏫 Level 5 - LFA AMATEUR Assistant
  👨‍🏫 Level 6 - LFA AMATEUR Head
  👨‍🏫 Level 7 - LFA PRO Assistant
  👨‍🏫 Level 8 - LFA PRO Head

INTERNSHIP:
  🔰 Level 1-5 (Junior → Principal)
```

### **Mit taníthat Grand Master?**

#### **LFA PLAYER PRE semester:**
- ✅ PLAYER Level 1+ licenc (van: Level 1-8) ✅
- ✅ COACH Level 1-2 licenc (van: Level 1-8) ✅
- **Eredmény: TANÍTHAT**

#### **LFA PLAYER YOUTH semester:**
- ✅ PLAYER Level 3+ licenc (van: Level 3-8) ✅
- ✅ COACH Level 3-4 licenc (van: Level 3-8) ✅
- **Eredmény: TANÍTHAT**

#### **LFA PLAYER AMATEUR semester:**
- ✅ PLAYER Level 5+ licenc (van: Level 5-8) ✅
- ✅ COACH Level 5-6 licenc (van: Level 5-8) ✅
- **Eredmény: TANÍTHAT**

#### **LFA PLAYER PRO semester:**
- ✅ PLAYER Level 8 licenc (van: Level 8) ✅
- ✅ COACH Level 7-8 licenc (van: Level 7-8) ✅
- **Eredmény: TANÍTHAT**

#### **GānCuju PLAYER sessiont:**
- ✅ PLAYER licenc (van: Level 1-8) ✅
- **Eredmény: TANÍTHAT**

#### **LFA COACH sessiont:**
- ✅ COACH licenc (van: Level 1-8) ✅
- **Eredmény: TANÍTHAT**

#### **INTERNSHIP sessiont:**
- ✅ INTERNSHIP licenc (van: Level 1-5) ✅
- **Eredmény: TANÍTHAT**

---

## ❓ Kérdések Tisztázásra

1. **COACH licenc taníthat-e PLAYER sessiont?**
   - Javaslatom: **IGEN** (edző ismeri a technikákat)

2. **PLAYER licenc taníthat-e COACH sessiont?**
   - Javaslatom: **NEM** (játékos ≠ edzői képesítés)

3. **Licenc szint számít-e?**
   - Javaslatom: **IGEN** (PRO sessiont csak Level 7-8 taníthat)

4. **INTERNSHIP licenc mire jogosít?**
   - Javaslatom: Csak INTERNSHIP sessiont + adminisztratív jogok magasabb szinten

5. **Licenc megszerzési dátum fontos?**
   - Javaslatom: **IGEN, NAGYON!** (múltbeli dátum = tapasztalat)

---

## 🎯 Következő Lépések

1. **Döntés** a fenti szcenáriókról
2. **Licenc dátum frissítése** (múltbeli dátumok Grand Masternek)
3. **Jogosultság ellenőrzés implementálása** backend-en
4. **Admin UI frissítése** (csak qualified instructorokat mutassa)

**Mit szeretnél először megbeszélni?**
