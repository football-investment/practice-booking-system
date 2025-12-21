# 🎟️ Invitation Code Workflow Dashboard

## 📋 Áttekintés

**Production-ready user regisztráció invitation code-okkal**

Ez a dashboard teszteli a teljes invitation code alapú regisztrációs folyamatot:
1. Admin létrehoz egy invitation code-ot
2. Student regisztrál az invitation code-dal (saját jelszót választ!)
3. Rendszer ellenőrzi a regisztrációt

---

## 🚀 Indítás

### **Gyors indítás:**
```bash
./start_invitation_workflow.sh
```

### **Dashboard elérhető:**
- **URL:** http://localhost:8503
- **Port:** 8503

---

## 🔐 Bejelentkezési Adatok

### **Admin hozzáférés:**
- **Email:** `admin@lfa.com`
- **Jelszó:** `admin123`

⚠️ **Fontos:** Ez egy ADMIN-ONLY dashboard. Csak administrator role-lal lehet belépni!

---

## 📋 Workflow Lépések

### **🎯 Step 1: Admin létrehoz Invitation Code-ot**

**Ki végzi:** ADMIN
**Amit csinál:**
1. Bejelentkezés admin account-tal
2. Kitölti az invitation form-ot:
   - **Invited Person Name:** Pl. "Test Student"
   - **Email Restriction:** (Opcionális) Konkrét email cím, vagy hagyja üresen
   - **Bonus Credits:** Hány credit jár a kódhoz (pl. 10)
   - **Notes:** Belső jegyzet (opcionális)
3. Kattints: **"🎟️ Create Invitation Code"**

**Eredmény:**
- ✅ Generált invitation code (pl. `INV-20251211-A3F2E8`)
- 💰 Bonus credits megjelennek
- 🔵 Step 2 aktiválódik

**API Endpoint:**
```
POST /admin/invitation-codes
```

---

### **🎯 Step 2: Student regisztrál az Invitation Code-dal**

**Ki végzi:** STUDENT (új felhasználó)
**Amit csinál:**
1. Látja a generált invitation code-ot
2. Kitölti a regisztrációs form-ot:
   - **Email:** Új student email címe (pl. `student@example.com`)
   - **Full Name:** Teljes név (pl. "Test Student")
   - **Choose Password:** **SAJÁT JELSZÓ VÁLASZTÁSA** (min 6 karakter)
   - **Invitation Code:** Automatikusan kitöltve a Step 1-ből
3. Kattints: **"📝 Register"**

**Eredmény:**
- ✅ Student account létrehozva
- 🎁 Bonus credits hozzáadva az accounthoz
- 🔑 Automatikus bejelentkezés (access token kiadva)
- 🔵 Step 3 aktiválódik

**API Endpoint:**
```
POST /api/v1/auth/register-with-invitation
```

**Fontos különbség a régi megoldástól:**
- ❌ **RÉGI:** Admin adta meg a student jelszavát (rossz!)
- ✅ **ÚJ:** Student választja a saját jelszavát (helyes!)

---

### **🎯 Step 3: Rendszer ellenőrzi a regisztrációt**

**Ki végzi:** SYSTEM (automatikus)
**Amit csinál:**
1. Kattints: **"🔍 Verify Registration"**
2. Rendszer lekéri a student account adatokat
3. Ellenőrzi:
   - Email helyes
   - Account aktív
   - Bonus credits megkapva
   - Role beállítva (STUDENT)

**Eredmény:**
- ✅ Verification successful
- 📊 Student account részletek megjelennek (JSON formátumban)
- 🎉 **TELJES WORKFLOW SIKERES!**

---

## 📊 Dashboard Funkciók

### **1. Real-time Workflow Tracking**
- Minden lépés státusza látható: ⏸️ pending, 🔵 active, ✅ done, ❌ error
- 3 oszlopos layout - minden step külön column-ban

### **2. Workflow Logs**
- Időbélyeggel ellátott log üzenetek
- Színkódolt üzenetek: ✅ success, ❌ error, ⚠️ warning, ℹ️ info
- Real-time frissítés minden műveletről

### **3. Workflow Control**
- **Reset Workflow:** Teljes workflow újrakezdése
- **Logout:** Admin kijelentkezés

### **4. Status Summary**
- Minden step státusza metrikus formátumban
- Vizuális visszajelzés a haladásról

---

## 🎯 Tesztelési Forgatókönyv

### **Scenario 1: Sikeres regisztráció (Happy Path)**

1. **Admin bejelentkezés**
   - Email: `admin@lfa.com`
   - Jelszó: `admin123`

2. **Invitation code létrehozása**
   - Name: `Test Student 1`
   - Email: Hagyd üresen (nincs email korlátozás)
   - Credits: `10`
   - Notes: `Test invitation`
   - ✅ Code generálva: pl. `INV-20251211-ABC123`

3. **Student regisztráció**
   - Email: `student1@test.com`
   - Name: `Test Student 1`
   - Password: `teszt123456`
   - Code: `INV-20251211-ABC123` (automatikusan kitöltve)
   - ✅ Regisztráció sikeres

4. **Verification**
   - Kattints "Verify Registration"
   - ✅ Account ellenőrizve
   - Látható: 10 credit az accounton

5. **Reset & Újra**
   - Kattints "Reset Workflow"
   - Tesztelj új userrel!

---

### **Scenario 2: Email korlátozással**

1. **Invitation code email korlátozással**
   - Name: `VIP Student`
   - Email: `vip@example.com` ← **Email korlátozás!**
   - Credits: `20`

2. **Student próbálkozik ROSSZ email-lel**
   - Email: `wrong@example.com`
   - Code: `INV-20251211-XYZ789`
   - ❌ **Hiba:** "This invitation code is restricted to vip@example.com"

3. **Student próbálkozik JÓ email-lel**
   - Email: `vip@example.com`
   - Code: `INV-20251211-XYZ789`
   - ✅ **Sikeres!**

---

### **Scenario 3: Kód újrafelhasználás**

1. **Első student használja a kódot**
   - Email: `student1@test.com`
   - Code: `INV-20251211-TEST01`
   - ✅ Sikeres regisztráció

2. **Második student próbálja ugyanazt a kódot**
   - Email: `student2@test.com`
   - Code: `INV-20251211-TEST01`
   - ❌ **Hiba:** "This invitation code has already been used"

---

## 🔍 Mi történik a háttérben?

### **Backend API calls:**

1. **Step 1: Admin creates invitation**
   ```
   POST /admin/invitation-codes
   Headers: Authorization: Bearer {admin_token}
   Body: {
     "invited_name": "Test Student",
     "invited_email": null,
     "bonus_credits": 10,
     "notes": "Test code"
   }
   Response: {
     "code": "INV-20251211-ABC123",
     "bonus_credits": 10,
     ...
   }
   ```

2. **Step 2: Student registers**
   ```
   POST /api/v1/auth/register-with-invitation
   Body: {
     "email": "student@example.com",
     "password": "student123",
     "name": "Test Student",
     "invitation_code": "INV-20251211-ABC123"
   }
   Response: {
     "access_token": "eyJ0eXAi...",
     "refresh_token": "eyJ0eXAi...",
     "token_type": "bearer"
   }
   ```

3. **Step 3: Verify student info**
   ```
   GET /api/v1/users/me
   Headers: Authorization: Bearer {student_token}
   Response: {
     "id": 123,
     "email": "student@example.com",
     "name": "Test Student",
     "role": "STUDENT",
     "credit_balance": 10,
     "is_active": true
   }
   ```

---

## 🎁 Invitation Code Adatbázis Séma

### **invitation_codes tábla:**
```sql
CREATE TABLE invitation_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,          -- INV-20251211-ABC123
    invited_name VARCHAR(200) NOT NULL,        -- Kinek szól
    invited_email VARCHAR(200),                -- Email korlátozás (optional)
    bonus_credits INTEGER NOT NULL,            -- Bonus creditek
    is_used BOOLEAN DEFAULT FALSE,             -- Használva-e
    used_by_user_id INTEGER,                   -- Ki használta
    used_at TIMESTAMP,                         -- Mikor használta
    created_by_admin_id INTEGER,               -- Melyik admin készítette
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,                      -- Lejárati dátum (optional)
    notes TEXT                                 -- Admin jegyzetek
);
```

---

## 📈 Előnyök az új megoldásnak

### **Régi megoldás (A opció):**
- ❌ Admin adja meg a student jelszavát
- ❌ Nem biztonságos
- ❌ Nem production-ready
- ❌ Admin látja a student jelszavát
- ✅ Gyors teszteléshez jó

### **Új megoldás (B opció):**
- ✅ Student választja a saját jelszavát
- ✅ Biztonságos
- ✅ Production-ready
- ✅ Admin NEM látja a student jelszavát
- ✅ Email korlátozás opció
- ✅ Bonus credit rendszer
- ✅ Invitation code tracking
- ✅ Audit log támogatás

---

## 🎉 Sikeres Workflow

Ha minden lépés ✅ done státuszban van:
- 🎉 **"Complete Invitation Code Workflow Successful!"** üzenet
- 🎈 Balloon animáció
- 💡 "Reset Workflow" ajánlat új teszt indításához

---

## 🛠️ Hibaelhárítás

### **"Failed to create invitation code"**
- Ellenőrizd, hogy admin be van-e jelentkezve
- Ellenőrizd, hogy backend fut-e (http://localhost:8000)
- Nézd meg a backend logokat

### **"Invalid invitation code"**
- Ellenőrizd, hogy jó kódot másolod be
- Invitation code case-sensitive (de a backend UPPER()-re konvertálja)

### **"This invitation code has already been used"**
- Ez várható! Minden kód csak egyszer használható
- Hozz létre új invitation code-ot Step 1-ben

### **"Email already registered"**
- A student email már létezik az adatbázisban
- Használj másik email címet

---

## 📚 Kapcsolódó Fájlok

### **Backend:**
- [app/api/api_v1/endpoints/auth.py](app/api/api_v1/endpoints/auth.py) - Register endpoint
- [app/api/api_v1/endpoints/invitation_codes.py](app/api/api_v1/endpoints/invitation_codes.py) - Invitation CRUD
- [app/models/invitation_code.py](app/models/invitation_code.py) - Invitation Code model

### **Frontend:**
- [invitation_code_workflow_dashboard.py](invitation_code_workflow_dashboard.py) - Ez a dashboard
- [start_invitation_workflow.sh](start_invitation_workflow.sh) - Indító script

### **Dokumentáció:**
- [BCRYPT_ERROR_INVESTIGATION_AND_FIX.md](BCRYPT_ERROR_INVESTIGATION_AND_FIX.md) - Bcrypt verzió kompatibilitás fix

---

## ✅ Következő Lépések

1. **Teszteld a Happy Path-ot** (Scenario 1)
2. **Teszteld az Email korlátozást** (Scenario 2)
3. **Teszteld a kód újrafelhasználást** (Scenario 3)
4. **Ellenőrizd az adatbázist** direct SQL query-vel:
   ```sql
   SELECT * FROM invitation_codes ORDER BY created_at DESC LIMIT 5;
   SELECT * FROM users ORDER BY id DESC LIMIT 5;
   ```

---

**Dashboard ready!** 🚀

**URL:** http://localhost:8503

**Login:** admin@lfa.com / admin123
