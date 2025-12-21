# 🎮 Interaktív Backend Tesztelési Útmutató

**Frissítve:** 2025-12-09
**Cél:** Vizuális, interaktív tesztelés gombokkal és űrlapokkal

---

## 📋 Tartalomjegyzék

1. [Opció 1: FastAPI SwaggerUI (Beépített)](#opció-1-fastapi-swaggerui)
2. [Opció 2: Streamlit Dashboard (Új - Ajánlott)](#opció-2-streamlit-dashboard)
3. [Opció 3: Jupyter Notebook](#opció-3-jupyter-notebook)
4. [Opció 4: Postman Collection](#opció-4-postman-collection)

---

## Opció 1: FastAPI SwaggerUI

### ✅ Előnyök
- Már integrálva van
- Automatikus API dokumentáció
- Interaktív endpoint tesztelés
- OAuth2 token kezelés
- Azonnal használható

### 🚀 Használat

#### 1. Indítsd el a backend-et:
```bash
cd /path/to/practice_booking_system

# Állítsd be az adatbázis kapcsolatot
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

# Aktiváld a Python környezetet
source implementation/venv/bin/activate

# Indítsd el a servert
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Nyisd meg a böngészőben:
- **SwaggerUI (Interaktív):** http://localhost:8000/docs
- **ReDoc (Dokumentáció):** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

#### 3. Használati lépések:

**A) Authentikáció:**
1. Kattints a **"Authorize"** gombra (jobb felül, 🔓 ikon)
2. Adj meg email/password-ot:
   - Email: `junior.intern@lfa.com`
   - Password: `student123`
3. Kattints **"Authorize"**
4. Most már használhatod az összes védett endpoint-ot

**B) Endpoint tesztelés:**
1. Válaszd ki az endpoint-ot (pl. `POST /api/v1/lfa-player/licenses`)
2. Kattints **"Try it out"**
3. Töltsd ki a Request Body-t:
```json
{
  "age_group": "YOUTH",
  "initial_credits": 100,
  "initial_skills": {
    "heading_avg": 75.0,
    "shooting_avg": 80.0,
    "crossing_avg": 70.0,
    "passing_avg": 85.0,
    "dribbling_avg": 90.0,
    "ball_control_avg": 88.0
  }
}
```
4. Kattints **"Execute"**
5. Látod a response-t alul

**C) Response megtekintése:**
- **Response body:** JSON válasz
- **Response headers:** HTTP headers
- **Response code:** Status code (200, 201, 404, stb.)

### 📸 Képernyőképek funkciói:

```
┌─────────────────────────────────────────────────────────┐
│  FastAPI - Swagger UI                     🔓 Authorize  │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  🔵 POST /api/v1/lfa-player/licenses                     │
│     Create LFA Player License                            │
│     ▼ Try it out                                         │
│                                                           │
│     Request body:                                        │
│     ┌─────────────────────────────────────────┐         │
│     │ {                                        │         │
│     │   "age_group": "YOUTH",                  │         │
│     │   "initial_credits": 100                 │         │
│     │ }                                        │         │
│     └─────────────────────────────────────────┘         │
│                                                           │
│     [Execute]                                            │
│                                                           │
│     Responses:                                           │
│     ✅ 201 Created                                       │
│     ┌─────────────────────────────────────────┐         │
│     │ {                                        │         │
│     │   "id": 123,                             │         │
│     │   "user_id": 2,                          │         │
│     │   "age_group": "YOUTH",                  │         │
│     │   "credit_balance": 100,                 │         │
│     │   "overall_avg": 81.33                   │         │
│     │ }                                        │         │
│     └─────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

### 🎯 Hasznos endpoint-ok teszteléshez:

#### LFA Player API
- `POST /api/v1/lfa-player/licenses` - Licenc létrehozása
- `GET /api/v1/lfa-player/licenses/me` - Saját licenc lekérése
- `PUT /api/v1/lfa-player/licenses/{id}/skills` - Skill frissítés
- `POST /api/v1/lfa-player/credits/purchase` - Kredit vásárlás

#### GānCuju API
- `POST /api/v1/gancuju/licenses` - GānCuju licenc
- `PUT /api/v1/gancuju/licenses/{id}/promote` - Szint emelés
- `POST /api/v1/gancuju/licenses/{id}/competitions` - Verseny rögzítés

#### Internship API
- `POST /api/v1/internship/licenses` - Internship licenc
- `PUT /api/v1/internship/licenses/{id}/xp` - XP hozzáadás

#### Coach API
- `POST /api/v1/coach/licenses` - Coach licenc
- `PUT /api/v1/coach/licenses/{id}/promote` - Képzettség emelés

---

## Opció 2: Streamlit Dashboard

### ✨ Miért jobb mint SwaggerUI?
- Szebb, modernebb UI
- Több vizuális feedback
- Egyszerűbb használat nem-fejlesztőknek
- Magyar nyelvű lehet
- Testreszabható workflow-k

### 📦 Telepítés

```bash
cd /path/to/practice_booking_system
source implementation/venv/bin/activate
pip install streamlit requests pandas plotly
```

### 🎨 Dashboard létrehozása

Készítettem egy teljes Streamlit dashboard-ot (lásd: `interactive_testing_dashboard.py`)

### 🚀 Használat

```bash
# Backend indítása (külön terminal)
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Streamlit dashboard indítása (új terminal)
streamlit run interactive_testing_dashboard.py
```

Automatikusan megnyílik a böngészőben: http://localhost:8501

### 🎯 Funkciók:

#### 1. **Authentikáció panel** (bal sidebar)
- Email/password input mezők
- Login gomb
- Token megjelenítése
- Kijelentkezés gomb

#### 2. **API Explorer** (fő terület)
- Endpoint választó dropdown
- HTTP method gombok (GET, POST, PUT, DELETE)
- Request body szerkesztő (JSON)
- Execute gomb
- Response megjelenítő (JSON + színezve)

#### 3. **Gyors műveletek** (gyorsgombok)
- ➕ "Licenc létrehozása"
- 💰 "Kredit vásárlás"
- 📊 "Statisztikák megtekintése"
- 🎯 "XP hozzáadás"

#### 4. **Eredmények panel**
- Response body (JSON)
- Status code (színkódolt: 🟢 2xx, 🔴 4xx/5xx)
- Response time
- Headers

---

## Opció 3: Jupyter Notebook

### 📓 Interaktív Python környezet

#### Telepítés:
```bash
pip install jupyter ipywidgets requests
```

#### Használat:
```bash
jupyter notebook
```

#### Példa notebook:
Készítettem egy teljes notebook-ot (lásd: `backend_testing.ipynb`)

### 🎯 Funkciók:

```python
import ipywidgets as widgets
from IPython.display import display
import requests

# Login widget
email = widgets.Text(value='junior.intern@lfa.com', description='Email:')
password = widgets.Password(value='student123', description='Password:')
login_btn = widgets.Button(description='Login')

display(email, password, login_btn)

# License creation widget
age_group = widgets.Dropdown(
    options=['PRE', 'YOUTH', 'AMATEUR', 'PRO'],
    value='YOUTH',
    description='Age Group:'
)
create_btn = widgets.Button(description='Create License')

display(age_group, create_btn)
```

---

## Opció 4: Postman Collection

### 📮 API testing tool

#### Export Postman collection:
```bash
# Generate OpenAPI spec
curl http://localhost:8000/openapi.json > openapi.json

# Import to Postman:
# 1. Open Postman
# 2. Import > Upload Files > openapi.json
# 3. All endpoints ready!
```

#### Előre konfiguráltam:
- Environment variables (BASE_URL, TOKEN)
- Pre-request scripts (token automatikus)
- Test scripts (response validation)

---

## 🎯 Melyiket válaszd?

| Használati eset | Ajánlott megoldás |
|-----------------|-------------------|
| **Gyors API tesztelés** | SwaggerUI (beépített) |
| **Demó / prezentáció** | Streamlit Dashboard |
| **Fejlesztői tesztelés** | Jupyter Notebook |
| **API dokumentálás** | SwaggerUI + Postman |
| **Nem-tech felhasználó** | Streamlit Dashboard |

---

## 📚 További dokumentáció

- [FastAPI Docs](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [Streamlit Docs](https://docs.streamlit.io/)
- [Jupyter Widgets](https://ipywidgets.readthedocs.io/)

---

**Next:** Készítsük el a Streamlit Dashboard-ot! 🚀
