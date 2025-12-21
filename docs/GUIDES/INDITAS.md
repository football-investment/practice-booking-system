# 🚀 GYORS INDÍTÁS - Interaktív Dashboard

## 📋 Lépések (2 terminál kell!)

---

## Terminal 1️⃣ - Backend indítása

```bash
cd "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"

export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

source implementation/venv/bin/activate

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**✅ Működik ha látod:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## Terminal 2️⃣ - Streamlit Dashboard indítása

**ÚJ TERMINAL-ban (ne zárd be az előzőt!):**

```bash
cd "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"

source implementation/venv/bin/activate

streamlit run interactive_testing_dashboard.py
```

**✅ Működik ha látod:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

**Automatikusan megnyílik a böngésződben!** 🎉

---

## 🎮 Használat

### 1. Bejelentkezés (bal menü)
- Email: `junior.intern@lfa.com`
- Password: `student123`
- Kattints: **🔓 Bejelentkezés**

### 2. Gyors teszt
- Menj a **"⚡ Gyors tesztek"** tab-ra
- Kattints: **➕ Licenc létrehozása**
- ✅ Látod: "Licenc létrehozva!"

### 3. Részletek
- Kattints: **📊 Saját licenc lekérése**
- Látod az adatokat!

---

## 🆘 Ha nem indul el

### Backend hiba?
```bash
# Ellenőrizd a PostgreSQL-t:
brew services start postgresql@14

# Próbáld újra a Terminal 1 parancsokat
```

### Streamlit hiba?
```bash
# Telepítsd újra:
pip install streamlit pandas plotly requests

# Próbáld újra a Terminal 2 parancsokat
```

---

## 🎯 Gyors linkek

- **Dashboard:** http://localhost:8501
- **Backend API:** http://localhost:8000
- **SwaggerUI:** http://localhost:8000/docs

---

**Készen vagy! Használd a Dashboard-ot! 🚀**
