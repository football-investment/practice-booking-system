# 🔴 KRITIKUS: UserRole Enum Inkonzisztencia

**Dátum:** 2025-12-23
**Státusz:** DOKUMENTÁLT - Működik, de figyelmet igényel
**Prioritás:** Közepes (működik, de zavaró lehet)

---

## 🔍 Probléma Leírása

A `UserRole` enum **eltérő formátumot használ** a Python modellben és az adatbázisban:

### Python Model (`app/models/user.py`)
```python
class UserRole(enum.Enum):
    ADMIN = "admin"        # kisbetűs érték
    INSTRUCTOR = "instructor"  # kisbetűs érték
    STUDENT = "student"    # kisbetűs érték
```

### PostgreSQL Adatbázis
```sql
SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'userrole');

 enumlabel
------------
 ADMIN         -- NAGYBETŰS
 INSTRUCTOR    -- NAGYBETŰS
 STUDENT       -- NAGYBETŰS
```

---

## ⚠️ Implikációk

### ✅ Működik (SQLAlchemy automatikus konverzió)
- **Python → DB írás:** SQLAlchemy automatikusan konvertálja `"instructor"` → `"INSTRUCTOR"`
- **DB → Python olvasás:** SQLAlchemy automatikusan konvertálja `"INSTRUCTOR"` → `UserRole.INSTRUCTOR` enum
- **API enum paraméterek:** FastAPI automatikusan kezeli a konverziót (pl. `role: Optional[UserRole]`)

### ❌ NEM működik (natív SQL query-k)
```python
# ❌ HIBÁS - nem talál semmit
db.execute("SELECT * FROM users WHERE role = 'instructor'")

# ✅ HELYES - működik
db.execute("SELECT * FROM users WHERE role = 'INSTRUCTOR'")
```

### ⚠️ Zavaró (API documentation)
- **OpenAPI/Swagger docs:** A dropdown `"admin"`, `"instructor"`, `"student"` (kisbetűs)
- **De az adatbázisban:** `"ADMIN"`, `"INSTRUCTOR"`, `"STUDENT"` (nagybetűs)
- Ez zavarhatja a fejlesztőket, akik direktben nézik az adatbázist

---

## 📝 Példák a Helyes Használatra

### 1. API Query Paraméter (Streamlit → Backend)
```python
# ✅ HELYES - FastAPI automatikusan kezeli
params = {
    "role": "instructor",  # kisbetűs (Python enum érték)
    "is_active": True
}
response = requests.get(f"{API_URL}/users/", params=params, headers=headers)
```

**Miért működik?**
- FastAPI a `role: Optional[UserRole]` paramétert automatikusan konvertálja enum objektummá
- SQLAlchemy az enum objektumot automatikusan konvertálja adatbázis formátumra (`INSTRUCTOR`)

### 2. SQLAlchemy ORM Query
```python
# ✅ HELYES - ORM automatikusan konvertál
instructors = db.query(User).filter(User.role == UserRole.INSTRUCTOR).all()
```

### 3. Nyers SQL (psql, SQL script)
```sql
-- ✅ HELYES - nagybetűs
SELECT * FROM users WHERE role = 'INSTRUCTOR';

-- ❌ HIBÁS - nem talál semmit
SELECT * FROM users WHERE role = 'instructor';
```

---

## 🛠️ Jelenlegi Implementáció

### Streamlit API Helper (`streamlit_app/api_helpers_instructors.py:117`)
```python
def get_available_instructors(token: str) -> List[Dict[str, Any]]:
    url = f"{get_api_url()}/users/"
    params = {
        "role": "instructor",  # ✅ Helyes - kisbetűs (Python enum érték)
        "is_active": True,
        "size": 100
    }
    response = requests.get(url, params=params, headers=get_headers(token))
    response.raise_for_status()
    return response.json().get("users", [])
```

**Státusz:** ✅ Működik helyesen (FastAPI automatikusan konvertál)

---

## 🔧 Ha Javítani Kellene (Opcionális)

Ha egységesíteni szeretnénk, két lehetőség van:

### Opció A: Python model → Nagybetűs (Breaking Change!)
```python
class UserRole(enum.Enum):
    ADMIN = "ADMIN"
    INSTRUCTOR = "INSTRUCTOR"
    STUDENT = "STUDENT"
```

**Hatás:**
- ✅ Konzisztens Python és DB között
- ❌ BREAKING CHANGE: Minden API request frissítése szükséges
- ❌ Meglévő JSON config fájlok frissítése szükséges

### Opció B: Adatbázis → Kisbetűs (Alembic migráció)
```sql
-- Alembic migration
ALTER TYPE userrole RENAME TO userrole_old;
CREATE TYPE userrole AS ENUM ('admin', 'instructor', 'student');
ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::text::userrole;
DROP TYPE userrole_old;
```

**Hatás:**
- ✅ Konzisztens Python és DB között
- ❌ Komplex migráció (enum rename PostgreSQL-ben bonyolult)
- ❌ Esetleges downtime migráció közben

---

## ✅ Ajánlott Megoldás

**NE változtassuk meg!** Az jelenlegi setup működik, mert:
1. SQLAlchemy automatikusan kezeli a konverziót
2. FastAPI automatikusan kezeli az enum paramétereket
3. Nincs production bug

**Ehelyett:**
- ✅ Dokumentáljuk (ez a fájl)
- ✅ Code review-ban figyeljünk rá
- ✅ Új fejlesztőknek megemlítjük onboarding során

---

## 📊 Adatbázis Státusz Ellenőrzés

```bash
# Enum értékek ellenőrzése
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c \
  "SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'userrole');"

# Jelenlegi felhasználók role szerint
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c \
  "SELECT role, COUNT(*) FROM users GROUP BY role;"
```

**Várható output:**
```
 enumlabel
------------
 ADMIN
 INSTRUCTOR
 STUDENT

 role    | count
---------+-------
 ADMIN      | 2
 INSTRUCTOR | 1
 STUDENT    | 11
```

---

## 🎯 Következtetés

- ✅ **Jelenlegi állapot:** Működik, dokumentált
- ✅ **API hívások:** `"instructor"` (kisbetűs) helyes
- ✅ **SQL query-k:** `'INSTRUCTOR'` (nagybetűs) helyes
- ⚠️ **Figyelem:** Új fejlesztőknek meg kell említeni
- ❌ **NE változtassuk:** Működik, nincs breaking change szükség

**Utolsó ellenőrzés:** 2025-12-23
**Grand Master instruktor státusz:** 1 aktív instruktor (grandmaster@lfa.com), nincs master pozícióban
