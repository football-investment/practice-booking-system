# 📅 Semester Dátum-generálási Logika – Technikai Elemzés

**Dátum:** 2025-12-13
**Dokumentum célja:** A jelenlegi semester generálási logika részletes ismertetése és az alternatív javaslat összehasonlítása

---

## 1️⃣ JELENLEGI IMPLEMENTÁCIÓ – Részletes Leírás

### 🔧 Technikai Architektúra

**Fájlok:**
- `app/api/api_v1/endpoints/semester_generator.py` - Generálási logika
- `app/services/semester_templates.py` - Template definíciók

### 📐 Dátumkezelési Logika

#### **A. Relatív Hétfő-Vasárnap Számítás**

A rendszer **NEM fix dátumokkal dolgozik**, hanem **relatív számítással**:

```python
def get_first_monday(year: int, month: int) -> date:
    """Get the first Monday of a given month"""
    d = date(year, month, 1)
    # Find first Monday
    while d.weekday() != 0:  # 0 = Monday
        d += timedelta(days=1)
    return d

def get_last_sunday(year: int, month: int) -> date:
    """Get the last Sunday of a given month"""
    # Start from last day of month
    if month == 12:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)

    # Find last Sunday
    while d.weekday() != 6:  # 6 = Sunday
        d -= timedelta(days=1)
    return d
```

**Működés:**
1. **Start date**: Az adott hónap **első hétfője**
2. **End date**: Az adott hónap **utolsó vasárnapja**
3. **Automatikus adaptálás**: Nem fix dátumok, hanem naptár-alapú számítás

#### **B. Szökőév és Hónaphossz Kezelés**

✅ **Automatikus kezelés Python `datetime` könyvtárral:**

```python
# Február utolsó napjának számítása (szökőév-biztos)
if month == 12:
    d = date(year + 1, 1, 1) - timedelta(days=1)  # Dec 31
else:
    d = date(year, month + 1, 1) - timedelta(days=1)  # Következő hónap előtti nap
```

- **2024**: Február 29 (szökőév) ✅
- **2025**: Február 28 (nem szökőév) ✅
- **2026**: Február 28 (nem szökőév) ✅
- **2028**: Február 29 (szökőév) ✅

**Python automatikusan kezeli**, nincs szükség manuális logikára!

---

### 📊 Generálási Típusok

#### **1. Monthly (PRE korosztály) - 12 semester/év**

```python
def generate_monthly_semesters(year: int, template: dict, db: Session):
    for theme_data in template["themes"]:
        month = theme_data["month"]  # 1-12

        # Példa: Január 2026
        start = get_first_monday(2026, 1)  # 2026-01-05 (hétfő)
        end = get_last_sunday(2026, 1)     # 2026-01-25 (vasárnap)
```

**Eredmény példa (2026):**
- **M01 (Jan)**: 2026-01-05 → 2026-01-25 (3 hét + 6 nap)
- **M02 (Feb)**: 2026-02-02 → 2026-02-22 (3 hét)
- **M03 (Mar)**: 2026-03-02 → 2026-03-29 (4 hét)

⚠️ **PROBLÉMA:** Hónapok között **LYUKAK** keletkeznek!
- Jan vége: 01-25
- Feb kezdés: 02-02
- **GAP: 7 nap (01-26 → 02-01)**

#### **2. Quarterly (YOUTH korosztály) - 4 semester/év**

```python
def generate_quarterly_semesters(year: int, template: dict, db: Session):
    for theme_data in template["themes"]:
        months = theme_data["months"]  # [1,2,3] vagy [4,5,6] stb.

        # Q1: Jan-Mar
        start = get_first_monday(year, months[0])     # Jan első hétfő
        end = get_last_sunday(year, months[-1])       # Mar utolsó vasárnap
```

**Eredmény példa (2026):**
- **Q1**: 2026-01-05 → 2026-03-29 (12 hét)
- **Q2**: 2026-04-06 → 2026-06-28 (12 hét)

⚠️ **PROBLÉMA:** Quarterek között **LYUKAK**!
- Q1 vége: 03-29
- Q2 kezdés: 04-06
- **GAP: 7 nap (03-30 → 04-05)**

#### **3. Semi-Annual (AMATEUR korosztály) - 2 semester/év**

```python
def generate_semiannual_semesters(year: int, template: dict, db: Session):
    # Fall semester: Sep-Feb (keresztül év határ!)
    if start_month > end_month:
        start = get_first_monday(year, start_month)      # Sep 2026
        end = get_last_sunday(year + 1, end_month)       # Feb 2027
```

**Eredmény példa (2026):**
- **Fall**: 2026-09-07 → 2027-02-28 (25 hét)
- **Spring**: 2027-03-01 → 2027-08-29 (26 hét)

⚠️ **PROBLÉMA:**
- Fall vége: 02-28 (vasárnap)
- Spring kezdés: 03-01 (hétfő)
- **NEM hétfő!** (csak véletlenül jó ez a példában)

#### **4. Annual (PRO korosztály) - 1 semester/év**

```python
def generate_annual_semesters(year: int, template: dict, db: Session):
    # Season: Jul-Jun (keresztül év határ!)
    start = get_first_monday(year, 7)        # Jul 2026
    end = get_last_sunday(year + 1, 6)       # Jun 2027
```

**Eredmény példa (2026/27):**
- **Season**: 2026-07-06 → 2027-06-27 (51 hét)

---

## 2️⃣ JELENLEGI MEGOLDÁS – PROBLÉMÁK

### ❌ **Kritikus Hibák**

1. **LYUKAK (GAPS) a semesterek között**
   - Hónapok/quarterek között 1-7 napos szünetek
   - Nincs folyamatos lefedettség

2. **NEM garantált Hétfő-Vasárnap átmenet**
   - Csak a hónapon BELÜL garantált
   - Hónapok KÖZÖTT NEM

3. **Nem skálázható több évre**
   - Admin csak 1 évet generál egyszerre
   - Multi-year planning nehézkes

4. **Fix template függőség**
   - Nehéz módosítani a logikát
   - Minden age group-hoz saját logika

### ✅ **Előnyök**

1. ✅ **Automatikus szökőév kezelés**
2. ✅ **Hétfő-vasárnap garantált egy hónapon belül**
3. ✅ **Egyszerű kód, könnyen érthető**

---

## 3️⃣ JAVASOLT ALTERNATÍVA – Dinamikus, Naptár-alapú Generálás

### 🎯 Koncepció

```python
def generate_continuous_semesters(
    year: int,
    semester_count: int,  # 12, 4, 2, vagy 1
    location_id: int
) -> List[Semester]:
    """
    Dinamikus semester generálás lyukmentes lefedettséggel.

    Logika:
    1. Kezdőnap: {year}-01-01 első hétfője
    2. Semester hossz: 365 nap / semester_count
    3. Egymás utáni hétfő-vasárnap blokkok
    4. NINCS lyuk, NINCS átfedés
    """

    # 1. Év első hétfője
    start_of_year = date(year, 1, 1)
    while start_of_year.weekday() != 0:  # Első hétfő
        start_of_year += timedelta(days=1)

    # 2. Semester hossz számítás
    days_in_year = 366 if is_leap_year(year) else 365
    semester_duration_days = days_in_year // semester_count

    semesters = []
    current_start = start_of_year

    for i in range(semester_count):
        # 3. Következő semester kezdete (hétfő)
        current_end = current_start + timedelta(days=semester_duration_days - 1)

        # Vasárnapra igazítás
        while current_end.weekday() != 6:  # Vasárnap
            current_end -= timedelta(days=1)

        semester = Semester(
            start_date=current_start,
            end_date=current_end,
            ...
        )
        semesters.append(semester)

        # 4. Következő hétfő (NINCS lyuk!)
        current_start = current_end + timedelta(days=1)
        while current_start.weekday() != 0:  # Hétfő
            current_start += timedelta(days=1)

    return semesters
```

### ✅ **Előnyök**

1. ✅ **NINCS lyuk** - 100% lefedettség
2. ✅ **Garantált hétfő-vasárnap átmenetek**
3. ✅ **Automatikus szökőév kezelés**
4. ✅ **Egyszerűbb admin UX** - csak évet kell választani
5. ✅ **Skálázható** - több év egyszerre generálható
6. ✅ **Egységes logika** - minden age group ugyanaz

### ⚠️ **Kockázatok**

1. ⚠️ **Nem hónap-alapú határok**
   - Semester nem esik egybe hónap végekkel
   - Marketing szempontból zavaró lehet

2. ⚠️ **Fix semester hossz**
   - Minden semester kb. azonos hosszú
   - Nincs rugalmasság

3. ⚠️ **Template vesztés**
   - Elvesznek a marketing témák (pl. "Christmas Champions")
   - Egyedi fókuszok nehezen kezelhetők

---

## 4️⃣ ÖSSZEHASONLÍTÓ TÁBLÁZAT

| Szempont | Jelenlegi (Hónap-alapú) | Javasolt (Folyamatos) |
|----------|-------------------------|----------------------|
| **Lyukmentes lefedettség** | ❌ Vannak gapek (1-7 nap) | ✅ 100% lefedettség |
| **Hétfő-Vasárnap átmenet** | ⚠️ Csak hónapon belül | ✅ Mindig garantált |
| **Szökőév kezelés** | ✅ Automatikus | ✅ Automatikus |
| **Marketing témák** | ✅ Havi/negyedéves témák | ❌ Elvesznek |
| **Admin UX egyszerűség** | ⚠️ Sok template | ✅ Egyszerű |
| **Rugalmasság** | ✅ Age group-onként eltérő | ❌ Fix logika |
| **Skálázhatóság** | ⚠️ 1 év/generálás | ✅ Multi-year |
| **Kód komplexitás** | ⚠️ 4 külön függvény | ✅ 1 univerzális |

---

## 5️⃣ HIBRID JAVASLAT – A LEGJOBB MINDKÉT VILÁGBÓL

### 🎯 Koncepció

**Kombináljuk a két megközelítést:**

1. **Hónap-alapú kezdőpontok** (marketing témák megőrzése)
2. **Automatikus gap-filling logika** (lyukmentes lefedettség)
3. **Opcionális hétfő-vasárnap igazítás**

```python
def generate_hybrid_semesters(year: int, template: dict, location_id: int):
    """
    Hibrid semester generálás:
    - Hónaponkénti kezdőpontok (marketing témák)
    - Gap-filling logika (lyukmentes lefedettség)
    """
    semesters = []
    last_end_date = None

    for theme_data in template["themes"]:
        if last_end_date is None:
            # Első semester: hónap első hétfője
            start = get_first_monday(year, theme_data["month"])
        else:
            # Következő semester: előző után AZONNAL (gap-free)
            start = last_end_date + timedelta(days=1)
            # Hétfőre igazítás
            while start.weekday() != 0:
                start += timedelta(days=1)

        # Vége: hónap utolsó vasárnapja
        end = get_last_sunday(year, theme_data["month"])

        semester = Semester(start_date=start, end_date=end, ...)
        semesters.append(semester)
        last_end_date = end

    return semesters
```

### ✅ **Hibrid Előnyök**

1. ✅ Megmaradnak a marketing témák
2. ✅ Lyukmentes lefedettség (gap-filling)
3. ✅ Hétfő-vasárnap garantált
4. ✅ Rugalmas age group-onként

---

## 6️⃣ AJÁNLÁS & DÖNTÉSI MÁTRIX

### 🏆 **Végső Ajánlás: HIBRID MEGOLDÁS**

**Indoklás:**
1. ✅ **Marketing értéket megőrzi** (témák, fókuszok)
2. ✅ **Technikai problémákat megold** (gapek, átmenetek)
3. ✅ **Minimális változtatás szükséges** (inkrementális javítás)

### 📋 **Implementációs Terv**

**PHASE 1: Gap-Filling Logika (P0 - Kritikus)**
- Fix: Gapek megszüntetése hónapok között
- Fájl: `semester_generator.py` módosítás
- Tesztelés: 2026-2029 adatokkal

**PHASE 2: Multi-Year Support (P1 - Magas)**
- Admin generálhat 2-3 évet egyszerre
- UI: Year range picker

**PHASE 3: Template Optimization (P2 - Közepes)**
- Egyszerűsített template struktúra
- Marketing témák konfigurálhatósága

---

## 7️⃣ DÖNTÉSI KÉRDÉSEK

Kérem válaszoljatok az alábbi kérdésekre:

1. **Marketing témák fontossága**: Mennyire kritikus, hogy a semesterek hónap-alapú témákhoz igazodjanak?
   - ☐ Kritikus (HIBRID megoldás)
   - ☐ Közepes (HIBRID vagy Folyamatos)
   - ☐ Nem fontos (Folyamatos megoldás)

2. **Gap-ek elfogadhatósága**: Elfogadható-e, ha vannak 1-7 napos szünetek a semesterek között?
   - ☐ Igen (jelenlegi megtartása)
   - ☐ NEM (HIBRID vagy Folyamatos szükséges)

3. **Multi-year prioritás**: Mennyire fontos, hogy egyszerre több évet lehessen generálni?
   - ☐ Magas prioritás (azonnal kell)
   - ☐ Közepes prioritás (később)
   - ☐ Alacsony prioritás (nem kell)

---

**Készítette:** Claude AI Assistant
**Dátum:** 2025-12-13
**Verzió:** 1.0
