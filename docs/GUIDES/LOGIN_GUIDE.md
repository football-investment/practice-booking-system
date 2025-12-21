# 🔐 Login Útmutató - LFA Admin Dashboard

**Dátum:** 2025-12-19
**Verzió:** Production Ready

---

## 🎯 HELYES LOGIN FOLYAMAT

### ✅ HELYES MÓDSZER:

1. **Nyisd meg:** http://localhost:8505 (Home page - Login screen)
2. **Jelentkezz be:**
   - Email: `admin@lfa.com`
   - Password: `adminpassword` (vagy amit beállítottál)
3. **Auto Redirect:** Automatikusan átirányít az Admin Dashboard-ra
4. **Session Persist:** URL query params-ban tárolva

---

## ❌ HIBÁS MÓDSZER:

**NE nyisd meg közvetlenül:** http://localhost:8505/pages/Admin_Dashboard

**Miért nem?**
- Nincs session state → "Not authenticated" error
- Direct URL bypass nem biztonságos
- Query params hiányoznak

---

## 📂 FÁJL STRUKTÚRA

```
streamlit_app/
├── 🏠_Home.py              ← LOGIN PAGE (root)
├── pages/
│   ├── Admin_Dashboard.py  ← Admin dashboard (requires auth)
│   ├── Instructor_Dashboard.py
│   └── Student_Dashboard.py
├── config.py
├── session_manager.py
└── api_helpers.py
```

**FONTOS:** `🏠_Home.py` a **root**-ban van, nem a `pages/`-ben!

---

## 🔄 SESSION PERSISTENCE

### URL Query Params Módszer:

**Login után az URL:**
```
http://localhost:8505?session_token=eyJ...&session_user=%7B%22id%22...
```

**Query params:**
- `session_token`: JWT token
- `session_user`: JSON-encoded user data

**Előny:** Survives page refresh! ✅

### Session State:

```python
st.session_state['session_token'] = "eyJ..."
st.session_state['session_user'] = {"id": 1, "email": "admin@lfa.com", ...}
st.session_state['session_role'] = "admin"
```

---

## 🚪 AUTO REDIRECT LOGIKA

### Home.py Login Flow:

```python
# 1. User bejelentkezik
success, error, response_data = login_user(email, password)

if success:
    # 2. Token kinyerése
    token = response_data.get("access_token")

    # 3. User data lekérése
    user_data = get_current_user(token)

    # 4. Session mentése
    st.session_state['session_token'] = token
    st.session_state['session_user'] = user_data

    # 5. URL query params mentése
    save_session_to_url(token, user_data)

    # 6. Auto redirect role szerint
    if role == 'admin':
        st.switch_page("pages/Admin_Dashboard.py")
    elif role == 'instructor':
        st.switch_page("pages/Instructor_Dashboard.py")
    else:
        st.switch_page("pages/Student_Dashboard.py")
```

---

## 🛡️ SECURITY FEATURES

### 1. Auth Check on Every Page:

```python
# pages/Admin_Dashboard.py
if SESSION_TOKEN_KEY not in st.session_state:
    restore_session_from_url()  # Try to restore from URL

if SESSION_TOKEN_KEY not in st.session_state:
    st.error("❌ Not authenticated")
    st.stop()  # Block access!
```

### 2. Role-Based Access:

```python
user = st.session_state[SESSION_USER_KEY]
if user.get('role') != 'admin':
    st.error("❌ Access denied. Admin role required.")
    st.stop()
```

### 3. Cookie-Based Backend Auth:

```python
# API calls use cookies
response = requests.get(
    f"{API_BASE_URL}/api/v1/admin/...",
    cookies={"access_token": token},  # ← Cookie auth!
    timeout=30
)
```

---

## 🐛 TROUBLESHOOTING

### Probléma: "Not authenticated" error

**OK:** Direct URL-en nyitottad meg az Admin Dashboard-ot

**Megoldás:**
1. Klikk a linkre: http://localhost:8505
2. Login a Home page-en
3. Auto redirect fog történni

---

### Probléma: "StreamlitAPIException: Could not find page"

**OK:** `st.switch_page("🏠_Home.py")` nem működik `pages/`-ből

**Megoldás:** Használj linket:
```python
st.markdown("### 🔗 [Click here to go to Login Page](http://localhost:8505)")
```

---

### Probléma: Session elvész refresh után

**OK:** Query params nem lettek mentve

**Megoldás:**
```python
save_session_to_url(token, user_data)
```

---

## 📊 LOGIN CREDENTIALS

### Admin User:
- **Email:** `admin@lfa.com`
- **Password:** `adminpassword`
- **Role:** `ADMIN`

### Test Instructor:
- **Email:** `instructor@lfa.com`
- **Password:** `instructor123`
- **Role:** `INSTRUCTOR`

### Test Student:
- **Email:** `student@lfa.com`
- **Password:** `student123`
- **Role:** `STUDENT`

---

## 🎯 COMPLETE LOGIN TEST

### Terminal Test:

```bash
# 1. Check backend is running
curl -s http://localhost:8000/health
# Expected: {"status":"healthy"}

# 2. Check frontend is running
curl -s -I http://localhost:8505 | head -1
# Expected: HTTP/1.1 200 OK

# 3. Test login API
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@lfa.com","password":"adminpassword"}' \
  -c /tmp/cookies.txt
# Expected: {"access_token": "eyJ..."}
```

---

## ✅ QUICK START

```bash
# 1. Start backend
cd practice_booking_system
./start_backend.sh

# 2. Start frontend (in new terminal)
cd practice_booking_system
./start_streamlit_app.sh

# 3. Open browser
open http://localhost:8505

# 4. Login
# Email: admin@lfa.com
# Password: adminpassword

# 5. ✅ Auto redirect to Admin Dashboard!
```

---

## 🎉 SUCCESS INDICATORS

### Login Successful:
- ✅ "Welcome back, Admin User!" message
- ✅ URL changes to include query params
- ✅ Auto redirect to Admin Dashboard
- ✅ Sidebar shows user info

### Session Persisted:
- ✅ Page refresh keeps you logged in
- ✅ Navigation between pages works
- ✅ URL query params visible

---

## 🔗 USEFUL LINKS

- **Home (Login):** http://localhost:8505
- **Admin Dashboard:** http://localhost:8505/Admin_Dashboard (auto redirect after login)
- **Backend API:** http://localhost:8000
- **API Health:** http://localhost:8000/health

---

**Megjegyzés:** A font preload warning **NEM hiba**, csak browser optimization. Figyelmen kívül hagyható! ✅
