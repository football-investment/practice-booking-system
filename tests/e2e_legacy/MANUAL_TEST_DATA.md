# 📋 Manuális Teszt Adatok - Streamlit Regisztráció

## 🎯 Cél
Teszteld le manuálisan a Streamlit regisztrációs formot böngészőben, hogy lásd működik-e a backend integráció.

## 🔗 URL
```
http://localhost:8501
```

## 📝 Teszt Lépések

### 1. Kattints a "Register with Invitation Code" gombra

### 2. Töltsd ki a formot ezekkel az adatokkal:

---

## ✅ KOMPLETT TESZT ADATOK

### 📧 Personal Information
- **First Name**: `Kristóf`
- **Last Name**: `Kis`
- **Nickname**: `Krisz`
- **Email**: `manual.test@f1stteam.hu`
- **Password**: `password123`
- **Phone Number**: `+36 20 123 4567`

### 🎂 Date of Birth
- **Formátum**: `YYYY/MM/DD` (ahogy a placeholder mutatja)
- **Érték**: `2016/05/15`
- **⚠️ FONTOS**: A dátum beírása után nyomj **ENTER**-t, hogy a Streamlit elfogadja!

### 🌍 Additional Information
- **Nationality**: `Hungarian`
- **Gender**: `Male` (válaszd ki a dropdown-ból)

### 🏠 Address
- **Street Address**: `Fő utca 12`
- **City**: `Budapest`
- **Postal Code**: `1011`
- **Country**: `Hungary`

### 🎟️ Invitation Code
**ÉRVÉNYES KÓD** (50 kredit, nincs email korlátozás):
```
INV-20260107-09P7U7
```

---

## 🔍 Mit Várj El

### ✅ Sikeres Regisztráció Esetén:
1. "Registration successful!" üzenet jelenik meg
2. Automatikusan bejelentkeztet a rendszer
3. 50 kredit kerül a fiókodra

### ❌ Ha Hibát Látsz:
- Figyeld meg **pontosan** milyen hibaüzenetet kapsz
- Nézd meg a böngésző **Developer Console**-ban (F12) van-e hiba
- Ellenőrizd, hogy a backend (port 8000) fut-e

---

## 🧪 Ellenőrzés az Adatbázisban

Ha sikerült a regisztráció, ellenőrizd:

```bash
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "SELECT id, email, credit_balance FROM users WHERE email = 'manual.test@f1stteam.hu';"
```

Várt eredmény:
```
 id |          email           | credit_balance
----+--------------------------+----------------
  X | manual.test@f1stteam.hu  |             50
```

És az invitation code használva lett:
```bash
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "SELECT code, is_used, used_by_user_id FROM invitation_codes WHERE code = 'INV-20260107-09P7U7';"
```

Várt eredmény:
```
        code         | is_used | used_by_user_id
---------------------+---------+-----------------
 INV-20260107-09P7U7 | t       |               X
```

---

## 🎯 EXTRA: További Invitation Kódok (Ha Többször Tesztelsz)

Ha többször akarod tesztelni, használd ezeket a kódokat (mindegyik 50 kredit, nincs email korlátozás):

1. `INV-20260107-09P7U7` ← Első teszt
2. `INV-20260107-3EV8YC` ← Második teszt
3. `INV-20260107-QFXRXT` ← Harmadik teszt

**FONTOS**: Minden kód csak **egyszer** használható!

---

## 🧹 Tisztítás (Ha Újra Akarod Tesztelni)

Ha törölni akarod a teszt usert és újra akarod használni ugyanazt a kódot:

```bash
# 1. Töröld a usert
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "DELETE FROM users WHERE email = 'manual.test@f1stteam.hu';"

# 2. Reset-eld az invitation kódot
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "UPDATE invitation_codes SET is_used = false, used_by_user_id = NULL, used_at = NULL WHERE code = 'INV-20260107-09P7U7';"
```

---

## 📸 Mit Figyelj Meg

1. **Minden mező ki van-e töltve** mielőtt rákattintanál a "Register Now" gombra
2. **Date of Birth mező**: Látszik-e a `2016/05/15` a mezőben az ENTER megnyomása után?
3. **Hibaüzenet**: Ha van, pontosan mi a szövege?
4. **Backend log**: Mit ír ki a terminal ahol a backend fut?

---

## 🆘 Gyakori Problémák

### ❌ "This invitation code has already been used"
→ Használd a másik kódot vagy reset-eld az adatbázist (lásd fent)

### ❌ "Email already registered"
→ Használj másik email címet vagy töröld a user-t (lásd fent)

### ❌ "Date of Birth" mező üres marad
→ **NYOMJ ENTER-T** a dátum beírása után!

### ❌ Nincs POST request a backendhez
→ Ellenőrizd, hogy minden mező ki van-e töltve, különösen a Date of Birth

---

## ✅ Sikerkritériumok

- [ ] Form kitöltése < 2 perc
- [ ] Dátum mező működik (ENTER után)
- [ ] "Registration successful!" üzenet megjelenik
- [ ] User létrejön az adatbázisban 50 kredittel
- [ ] Invitation code `is_used = true` lesz
- [ ] Automatikus bejelentkezés működik

---

**Jó tesztelést! 🚀**
