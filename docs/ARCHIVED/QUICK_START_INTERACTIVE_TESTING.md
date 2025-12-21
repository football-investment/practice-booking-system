# 🚀 Gyors Indítási Útmutató - Interaktív Backend Tesztelés

**5 perc alatt működő interaktív tesztelés!**

---

## 🎯 Mi ez?

3 féle interaktív tesztelési lehetőség:
1. **SwaggerUI** (beépített, azonnal működik)
2. **Streamlit Dashboard** (✨ AJÁNLOTT - szép UI)
3. **Jupyter Notebook** (fejlesztőknek)

---

## ⚡ Opció 1: SwaggerUI (Leggyorsabb)

### 1️⃣ Backend indítása
```bash
cd "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"

export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
source implementation/venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2️⃣ Megnyitás böngészőben
**👉 http://localhost:8000/docs**

### 3️⃣ Használat
1. Kattints **"Authorize"** (🔓 ikon, jobb felül)
2. Bejelentkezés:
   - **Email:** `junior.intern@lfa.com`
   - **Password:** `student123`
3. Kattints **"Authorize"**
4. Most már próbálhatsz bármilyen endpoint-ot!

### ✨ Példa: Licenc létrehozása
1. Keresd meg: `POST /api/v1/lfa-player/licenses`
2. Kattints **"Try it out"**
3. Töltsd ki:
```json
{
  "age_group": "YOUTH",
  "initial_credits": 100
}
```
4. Kattints **"Execute"**
5. Látod a választ alul! ✅

---

## 🎨 Opció 2: Streamlit Dashboard (AJÁNLOTT)

### 1️⃣ Egyszerű indítás
```bash
cd "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"
./start_interactive_testing.sh
```

**VAGY** manuálisan:

### 1️⃣ Backend indítása (külön terminal)
```bash
cd "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
source implementation/venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2️⃣ Dashboard indítása (új terminal)
```bash
cd "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"
source implementation/venv/bin/activate
streamlit run interactive_testing_dashboard.py
```

### 3️⃣ Megnyitás
Automatikusan megnyílik: **http://localhost:8501**

### 🎯 Funkciók:

#### Bal oldali menü:
- 🔐 **Bejelentkezés**
- ⚡ **Gyors műveletek** (előre konfigurált)
- 📜 **Kérés előzmények**

#### Fő terület - 4 Tab:
1. **API Explorer** - Bármilyen endpoint kipróbálható
2. **Gyors tesztek** - Egy kattintással működő tesztek
3. **Eredmények** - Statisztikák, előzmények
4. **Dokumentáció** - Használati útmutató

#### Gyors műveletek (1 kattintás):
- ➕ Licenc létrehozása (LFA Player, GānCuju, Internship)
- 📊 Licenc lekérése
- 💰 Kredit vásárlás
- 🎯 XP hozzáadás

---

## 📓 Opció 3: Jupyter Notebook

### 1️⃣ Telepítés
```bash
pip install jupyter ipywidgets
```

### 2️⃣ Indítás
```bash
jupyter notebook
```

### 3️⃣ Új notebook létrehozása
Lásd: `backend_testing.ipynb` (hamarosan)

---

## 🎯 Melyiket válaszd?

| Használati eset | Megoldás | Előny |
|-----------------|----------|-------|
| **Gyors tesztelés** | SwaggerUI | Azonnal működik |
| **Demó/prezentáció** | Streamlit | Szép, modern UI |
| **Nem-tech user** | Streamlit | Magyarul, intuitív |
| **Fejlesztés** | SwaggerUI | API docs + tesztelés |
| **Kutatás** | Jupyter | Interaktív Python |

---

## 📸 Streamlit Dashboard képek

### Bejelentkezési képernyő
```
┌──────────────────────────────┐
│  🔐 Authentikáció            │
├──────────────────────────────┤
│  📧 Email                    │
│  ┌──────────────────────┐   │
│  │ junior.intern@lfa... │   │
│  └──────────────────────┘   │
│                              │
│  🔑 Password                 │
│  ┌──────────────────────┐   │
│  │ ********             │   │
│  └──────────────────────┘   │
│                              │
│  [🔓 Bejelentkezés]          │
└──────────────────────────────┘
```

### Gyors tesztek képernyő
```
┌────────────────────────────────────────┐
│  ⚡ Gyors tesztek                      │
├────────────────────────────────────────┤
│                                        │
│  🏃 LFA Player műveletek              │
│  ┌─────────────────────────────────┐  │
│  │ Age Group: [YOUTH ▼]           │  │
│  │ Kreditek:  [100        ]       │  │
│  │                                 │  │
│  │ [➕ Licenc létrehozása]        │  │
│  └─────────────────────────────────┘  │
│                                        │
│  🥋 GānCuju műveletek                 │
│  🎓 Internship műveletek              │
│  👨‍🏫 Coach műveletek                  │
└────────────────────────────────────────┘
```

### API Explorer képernyő
```
┌─────────────────────────────────────────┐
│  🔍 API Endpoint Explorer               │
├─────────────────────────────────────────┤
│  Kategória: [LFA Player ▼]             │
│  Method:    [POST ▼]                   │
│  Endpoint:  /api/v1/lfa-player/licenses│
│                                         │
│  📝 Request Body:                       │
│  ┌───────────────────────────────────┐ │
│  │ {                                 │ │
│  │   "age_group": "YOUTH",           │ │
│  │   "initial_credits": 100          │ │
│  │ }                                 │ │
│  └───────────────────────────────────┘ │
│                                         │
│  [🚀 Végrehajtás]  [🗑️ Törlés]       │
│                                         │
│  📥 Válasz:                            │
│  ✅ 201 - Sikeres kérés (0.15s)       │
│  ┌───────────────────────────────────┐ │
│  │ {                                 │ │
│  │   "id": 123,                      │ │
│  │   "user_id": 2,                   │ │
│  │   "age_group": "YOUTH",           │ │
│  │   "credit_balance": 100           │ │
│  │ }                                 │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

## 🆘 Hibaelhárítás

### ❌ Backend nem elérhető
```bash
# Ellenőrizd hogy a backend fut-e:
curl http://localhost:8000/docs

# Ha nem, indítsd el:
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### ❌ Streamlit nem található
```bash
# Telepítsd:
pip install streamlit pandas plotly
```

### ❌ 401 Unauthorized hiba
- Ellenőrizd hogy bejelentkeztél-e
- Próbálj ki egy másik teszt fiókot
- Jelentkezz ki és vissza

### ❌ PostgreSQL nem elérhető
```bash
# Indítsd el a PostgreSQL-t:
brew services start postgresql@14

# Ellenőrizd:
psql -U postgres -d lfa_intern_system -c "SELECT 1"
```

---

## 📚 További dokumentáció

- **Teljes útmutató:** [INTERACTIVE_TESTING_GUIDE.md](INTERACTIVE_TESTING_GUIDE.md)
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Test Suite Report:** [TEST_SUITE_100_PERCENT_COMPLETE.md](TEST_SUITE_100_PERCENT_COMPLETE.md)

---

## 🎓 Példa workflow

### Teljes teszt workflow (Streamlit):

1. **Indítsd el mindkét service-t**
   ```bash
   # Terminal 1 - Backend
   ./start_backend.sh  # vagy manuálisan

   # Terminal 2 - Dashboard
   ./start_interactive_testing.sh
   ```

2. **Jelentkezz be** (bal sidebar)
   - Email: `junior.intern@lfa.com`
   - Password: `student123`

3. **Gyors teszt - LFA Player licenc**
   - Menj a **"Gyors tesztek"** tab-ra
   - Válaszd **"LFA Player műveletek"**
   - Kattints **"Licenc létrehozása"**
   - Látod: ✅ Licenc létrehozva!

4. **Nézd meg a licenc adatait**
   - Kattints **"Saját licenc lekérése"**
   - Látod: Age Group, Overall Avg, Credit Balance

5. **Próbálj ki egyéni endpoint-ot**
   - Menj az **"API Explorer"** tab-ra
   - Válaszd: `PUT /api/v1/lfa-player/licenses/{id}/skills`
   - Adj meg Resource ID-t
   - Módosítsd a skill-t
   - Kattints **"Végrehajtás"**

6. **Nézd meg az eredményeket**
   - Menj az **"Eredmények"** tab-ra
   - Látod az összes kérést táblázatban
   - Statisztikák: sikeres kérések, átlagos válaszidő

---

## ✨ Pro tippek

### SwaggerUI tippek:
- 💡 Használd a **"Schema"** gombot példa JSON generálásához
- 💡 **CTRL+Enter** = Execute shortcut
- 💡 Response headers-ben látod a request-id-t (debugging)

### Streamlit tippek:
- 💡 **R** billentyű = refresh
- 💡 Session State megőrzi a tokent
- 💡 Response history automatikusan mentődik
- 💡 JSON válaszok automatikusan formázottak

---

**🎉 Kész! Most már interaktívan tesztelheted a backend-et!**

Kérdés? Lásd: [INTERACTIVE_TESTING_GUIDE.md](INTERACTIVE_TESTING_GUIDE.md)
