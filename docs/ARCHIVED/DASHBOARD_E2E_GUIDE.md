# 🎮 Dashboard E2E Journey Tests - Gyors Útmutató

## ✅ Kész! Az E2E Journey Tesztek már futtathatók a dashboardon!

### 🚀 Gyors indítás (2 lépés)

#### 1. Dashboard indítása
```bash
./start_dashboard.sh
```

#### 2. Böngészőben megnyitni
```
http://localhost:8501
```

---

## 📋 Használat lépésről lépésre

### 1️⃣ Bejelentkezés
- **Bal oldali menü** → Bejelentkezési űrlap
- Válassz teszt fiókot:
  - **Student**: `junior.intern@lfa.com` / `junior123`
  - **Instructor**: `grandmaster@lfa.com` / `admin123`
  - **Admin**: `admin@lfa.com` / `admin123`

### 2️⃣ E2E Journey Tests fül
- Kattints a **"🧪 E2E Journey Tests"** tabra
- Ez az új 4. fül a dashboard-on

### 3️⃣ Journey teszt futtatása
1. **Válaszd ki a futtatási módot**:
   - **Sequential (sorban)**: Egy journey egyszerre (ajánlott)
   - **Parallel (párhuzamos)**: Minden journey egyszerre
   - **Single (egyedi)**: Csak egy konkrét journey

2. **Állítsd be a késleltetést**:
   - **10 sec**: Gyors tesztelés (alapértelmezett)
   - **180 sec**: 3 perces éles szimuláció

3. **Kattints a "🚀 Journey Tesztek Futtatása" gombra**

### 4️⃣ Eredmények megtekintése
- **Valós idejű kimenet**: Látod a journey-k futását
- **Progress bar**: Vizuális feedback
- **Eredmény összefoglaló**: Sikeres/sikertelen lépések
- **Részletes táblázatok**: Minden lépés státusza
- **Generált riportok**: JSON + HTML fájlok

---

## 🎯 Mit csinál az E2E Journey Test?

### 🎓 Student Journey (6 lépés)
```
1. ✅ Get Profile → User profil
2. ✅ Get LFA Player License → Játékos licenc
3. ✅ Get GānCuju License → Öv szint
4. ✅ Get Internship License → XP és level
5. ✅ Browse Sessions → Session-ök
6. ✅ My Bookings → Foglalások
```

### 👨‍🏫 Instructor Journey (2 lépés)
```
1. ✅ Get Profile → Instructor profil
2. ⚠️ Get Coach License → Coach cert (lehet 404)
```

### 👑 Admin Journey (4 lépés)
```
1. ✅ Get Profile → Admin profil
2. ✅ List All Users → User lista
3. ✅ System Health → Health check
4. ✅ List Semesters → Szemeszterek
```

---

## 📊 Várható eredmények

| Journey | Lépések | Várható siker |
|---------|---------|---------------|
| Student | 6 | 100% (6/6) |
| Instructor | 2 | 50-100% (1-2/2) |
| Admin | 4 | 100% (4/4) |

---

## 🎨 Dashboard funkciók

### Real-time Progress
- ⏳ Valós idejű kimenet stream
- 📊 Progress bar frissítés
- 🎯 Lépésenkénti státusz

### Eredmény vizualizáció
- ✅ Sikeres lépések zöld színnel
- ❌ Hibás lépések piros színnel
- 📈 Sikeres arány metrikák
- ⏱️ Futási idők

### Riportok
- 📄 **JSON riport**: `journey_test_report_YYYYMMDD_HHMMSS.json`
- 📄 **HTML riport**: `journey_test_report_YYYYMMDD_HHMMSS.html`

---

## 💡 Tippek

### Időzítés beállítása
```python
# Gyors teszt (10s lépésenként)
delay_seconds = 10

# Éles szimuláció (3 perc session completion)
delay_seconds = 180
```

### Több journey egyszerre
- **Parallel mód**: Minden journey párhuzamosan fut
- **Hasznos**: Terhelésteszt, gyors feedback
- **Figyelem**: Backend terhelés magasabb

### Single journey debug
- **Single mód**: Csak egy journey fut
- **Hasznos**: Specifikus endpoint debug
- **Példa**: Csak Student Journey tesztelése

---

## 🔧 Hibaelhárítás

### Dashboard nem indul
```bash
# Streamlit telepítése
pip install streamlit

# Dashboard indítása
streamlit run interactive_testing_dashboard.py
```

### Backend nem elérhető
```bash
# Backend indítása
./start_backend.sh

# Vagy manuálisan
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Journey teszt hiba
1. **Ellenőrizd a backend-et**: `curl http://localhost:8000/docs`
2. **Nézd meg a riportot**: `journey_test_report_*.json`
3. **Konzol kimenet**: Expander-ben teljes log

---

## 🎉 Összefoglalás

**✅ KÉSZ! Most már:**
1. ✅ Dashboard-on futtathatod az E2E journey teszteket
2. ✅ Valós időben követheted a haladást
3. ✅ Vizuális feedback-et kapsz
4. ✅ Generált riportokat kapsz (JSON + HTML)
5. ✅ Gombokkal aktiválhatod a teszteket

**🚀 Indítás:**
```bash
./start_dashboard.sh
```

**🌐 Megnyitás böngészőben:**
```
http://localhost:8501
```

**🧪 Kattints a "🧪 E2E Journey Tests" fülre és nyomd meg a gombot!**

---

## 📚 További dokumentáció

- **Automatikus tesztek**: `AUTOMATED_TESTING_COMPLETE.md`
- **E2E Journey tesztek**: `E2E_JOURNEY_TESTS_COMPLETE.md`
- **Gyors indítás**: `GYORS_TESZT_INDITAS.md`
- **Teszt fiókok**: `TESZT_FIOKOK.md`

---

**🎮 Élvezd az interaktív tesztelést!** 🚀
