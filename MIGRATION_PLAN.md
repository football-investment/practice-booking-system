# 🚀 LFA SZAKIRÁNY RENDSZER ÁTDOLGOZÁSI TERV

## 📊 **JELENLEGI HELYZET ELEMZÉS**

### **✅ Teknológiai Stack Confirmálva:**
- Backend: FastAPI + Python 3.13 + SQLAlchemy 2.0
- Frontend: React 19.1.1 + React Router + Axios  
- Database: PostgreSQL
- Authentication: JWT

### **⚠️ Fő Problémák Azonosítva:**
1. **Hibás prerequisite logika** - `app/api/api_v1/endpoints/progression.py`
2. **XP infláció kezelhető** - ~43 XP/kérdés (nem kritikus)
3. **Hiányzó payment rendszer** - Admin manuális kezelés szükséges
4. **Licensz rendszer hiányzik** - Teljes új implementáció

---

## 🎯 **PRIORIAS ALAPÚ MEGVALÓSÍTÁSI TERV**

### **FÁZIS 1: KRITIKUS INFRASTRUKTÚRA [1-2 hét]**
**Prioritás: MAGAS** 🔴

#### 1.1 Database Schema Átdolgozás
```sql
-- Szakirány payment tábla
CREATE TABLE semester_payments (
  id SERIAL PRIMARY KEY,
  student_id INT NOT NULL,
  semester_id VARCHAR(50) NOT NULL,
  specialization_id VARCHAR(50) NOT NULL,
  payment_status VARCHAR(20) DEFAULT 'PENDING',
  payment_amount DECIMAL(10,2),
  payment_date TIMESTAMP NULL,
  admin_user_id INT,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (student_id) REFERENCES users(id),
  FOREIGN KEY (admin_user_id) REFERENCES users(id),
  UNIQUE(student_id, semester_id, specialization_id)
);

-- Licensz tábla
CREATE TABLE digital_licenses (
  id VARCHAR(100) PRIMARY KEY,
  student_id INT NOT NULL,
  specialization_id VARCHAR(50) NOT NULL,
  level INT NOT NULL,
  license_title VARCHAR(500) NOT NULL,
  issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  valid_until TIMESTAMP NULL,
  qr_code_data TEXT,
  verification_url VARCHAR(500),
  status VARCHAR(20) DEFAULT 'ACTIVE',
  
  FOREIGN KEY (student_id) REFERENCES users(id)
);
```

#### 1.2 Hibás API Endpoints Eltávolítása
- ❌ DELETE `/api/specializations/prerequisites`
- ❌ DELETE `/api/specializations/transitions` 
- ❌ DELETE `/api/specializations/validate-switch`

#### 1.3 User Specialization Progress Refactor
```python
# Új student_specializations tábla
CREATE TABLE student_specializations (
  id SERIAL PRIMARY KEY,
  student_id INT NOT NULL,
  specialization_id VARCHAR(50) NOT NULL,
  semester_id VARCHAR(50) NOT NULL,
  current_level INT DEFAULT 1,
  total_xp INT DEFAULT 0,
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  status VARCHAR(20) DEFAULT 'ACTIVE',
  
  FOREIGN KEY (student_id) REFERENCES users(id),
  UNIQUE(student_id, specialization_id, semester_id)
);
```

---

### **FÁZIS 2: ADMIN PAYMENT RENDSZER [1 hét]**
**Prioritás: MAGAS** 🔴

#### 2.1 Admin Backend API
```python
# /app/api/api_v1/endpoints/admin_payments.py
@router.post("/admin/payments")
async def create_semester_payment(
    student_id: int,
    semester_id: str,
    specialization_id: str,
    amount: float,
    current_admin: User = Depends(get_current_admin_user)
):
    # Admin payment logic
```

#### 2.2 Admin Frontend Interface
```javascript
// /frontend/src/pages/admin/PaymentManager.js
const PaymentManager = () => {
  // Semester payment interface for admins
  // Student list with payment toggles per specialization
}
```

---

### **FÁZIS 3: STUDENT VÁLASZTÁSI LOGIKA [3-4 nap]**
**Prioritás: MAGAS** 🔴

#### 3.1 Új Specializáció Választó
```python
# Backend logic
async def get_available_specializations(student_id: int, semester_id: str):
    payments = await db.query("""
        SELECT specialization_id 
        FROM semester_payments 
        WHERE student_id = ? AND semester_id = ? AND payment_status = 'PAID'
    """, [student_id, semester_id])
    
    return [p.specialization_id for p in payments]
```

#### 3.2 Frontend Refactor
- ❌ Töröld `PrerequisitesBadge` komponenst
- ❌ Töröld `TransitionRulesSection` komponenst
- ✅ Új `SpecializationSelector` komponens

---

### **FÁZIS 4: XP RENDSZER JAVÍTÁS [2-3 nap]**
**Prioritás: KÖZEPES** 🟡

#### 4.1 XP Súlyozás Módosítása
```python
# Jelenlegi: ~43 XP/kérdés
# Új rendszer:
XP_SOURCES = {
    'ADAPTIVE_LEARNING': {
        'baseXP': 5,           # 43 -> 5 XP
        'dailyLimit': 500,     # Napi maximum
    },
    'QUIZ_COMPLETION': 250,    # Quiz teljesítés
    'PROJECT_MILESTONE': 1000, # Milestone teljesítés
    'SESSION_ATTENDANCE': 200  # Session részvétel
}
```

---

### **FÁZIS 5: DIGITÁLIS LICENSZ RENDSZER [1-2 hét]**
**Prioritás: ALACSONY** 🟢

#### 5.1 Licensz Generáció
```python
class LicenseGenerator:
    async def generate_license(self, student_id: int, specialization: str, level: int):
        # Requirements check
        # QR code generation
        # PDF creation
        # Email sending
```

#### 5.2 Szükséges Library-k
```bash
pip install qrcode[pil] reportlab jinja2 sendgrid
```

---

## ⚡ **AZONNALI AKCIÓ TERV**

### **🔥 KRITIKUS LÉPÉSEK (MA):**
1. ✅ **Database backup elkészült** 
2. 🔧 **Hibás progression endpoint kikommentezése**
3. 🗄️ **Payment tábla létrehozása**
4. 👥 **Admin payment API implementálása**

### **📅 1 HETES CÉL:**
- ✅ Admin tud payment-eket beállítani
- ✅ Student csak fizetett specializációkat látja
- ✅ Hibás prerequisite logika eltávolítva

### **📅 2 HETES CÉL:**
- ✅ XP rendszer normalizálva
- ✅ Alapvető licensz generálás működik
- ✅ Tesztelés és validáció kész

---

## 🛠️ **IMPLEMENTÁCIÓ KEZDÉS**

### **Step 1: Hibás Endpoints Letiltása**
```python
# Kommenteld ki: /app/api/api_v1/endpoints/progression.py
# router.get("/progression/validate")  # DISABLE
# router.post("/progression/switch")   # DISABLE
```

### **Step 2: Payment Tábla Létrehozása**
```sql
-- Futtasd PostgreSQL-ben
\c practice_booking_system;
-- [SQL script a fentiből]
```

### **Step 3: Admin API Endpoint**
```python
# Hozd létre: /app/api/api_v1/endpoints/admin_payments.py
# [Python kód a fentiből]
```

---

## 🤔 **ELDÖNTENDŐ KÉRDÉSEK**

1. **Email Service:** SendGrid, Mailgun vagy egyszerű SMTP?
2. **Payment Amounts:** Fix összegek specializációnként?
3. **License Validity:** 2-3 év érvényesség?
4. **Rollout Timeline:** Fokozatos vagy egyszerre az összes user?

---

## 📞 **KÖVETKEZŐ LÉPÉS**

**Válaszd meg a kérdéseket** és **jelezd hogy melyik fázist kezdjük el első**! 

Javaslatom: **FÁZIS 1.2** - Hibás endpoints letiltása és payment tábla létrehozása.

Ready to start? 🚀