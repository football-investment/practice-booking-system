# 📋 Manuális Teszt Adatok - Onboarding + Kupon Használat

## 🎯 Cél
Teszteld le manuálisan az onboarding folyamatot kupon használattal, mivel a usereknek nincs elég kreditjük (50) a specializáció feloldásához (100).

## 📊 Kiindulási Helyzet

### Regisztrált Userek (pwt. prefix):
1. **pwt.k1sqx1@f1stteam.hu** - 50 kredit (Pre kategória, 10 éves)
2. **pwt.p3t1k3@f1stteam.hu** - 50 kredit (Youth kategória, 14 éves)
3. **pwt.V4lv3rd3jr@f1stteam.hu** - 50 kredit (Amateur kategória, 22 éves)

### Specializáció Feloldási Ár:
- **100 kredit** / specializáció

### Probléma:
- Minden usernek csak **50 kreditje** van
- Szükség van **+50 kredit kupónra** hogy fel tudják oldani a specializációt

---

## 🎟️ Teszt Kuponok (50 bonus kredit)

| Kupon Kód | Érték | User | Típus |
|-----------|-------|------|-------|
| `E2E-BONUS-50-USER1` | +50 kredit | User 1 | BONUS_CREDITS |
| `E2E-BONUS-50-USER2` | +50 kredit | User 2 | BONUS_CREDITS |
| `E2E-BONUS-50-USER3` | +50 kredit | User 3 | BONUS_CREDITS |

---

## 🔄 USER 1: pwt.k1sqx1@f1stteam.hu

### Login Adatok:
- **Email**: `pwt.k1sqx1@f1stteam.hu`
- **Password**: `password123`

### Lépések:

1. **Login**
   - URL: `http://localhost:8501`
   - Email: `pwt.k1sqx1@f1stteam.hu`
   - Password: `password123`

2. **Specialization Hub betöltése**
   - Automatikusan átirányít ide (nincs még specializáció)
   - Látható kredit egyenleg: **50 credits**

3. **First Team specializáció választása**
   - Kattints a "First Team" kártyára
   - Láthatod: "💰 100 Credits" jelzést
   - Probléma: **Nincs elég kredit!** (50 < 100)

4. **Kupon applikálása**
   - Keresd a kupon input mezőt (lehet hogy "My Credits" oldalon van)
   - Vagy a Specialization Hub-on belül "Apply Coupon" gomb
   - Add meg: `E2E-BONUS-50-USER1`
   - Elvárt eredmény: +50 kredit hozzáadva → **Új egyenleg: 100 kredit**

5. **Specializáció feloldása**
   - Most kattints a "🔓 Unlock Now (100 credits)" gombra
   - Megerősítés: igen
   - Elvárt eredmény: Specializáció feloldva, **új egyenleg: 0 kredit**

6. **Onboarding befejezése**
   - User license létrejön `specialization_type = 'first_team'`
   - `onboarding_completed = true`

---

## 🔄 USER 2: pwt.p3t1k3@f1stteam.hu

### Login Adatok:
- **Email**: `pwt.p3t1k3@f1stteam.hu`
- **Password**: `password123`

### Kupon Kód:
```
E2E-BONUS-50-USER2
```

### Specializáció:
- Választható: **Goalkeeper** vagy **First Team**
- Ugyanaz a folyamat mint User 1

---

## 🔄 USER 3: pwt.V4lv3rd3jr@f1stteam.hu

### Login Adatok:
- **Email**: `pwt.V4lv3rd3jr@f1stteam.hu`
- **Password**: `password123`

### Kupon Kód:
```
E2E-BONUS-50-USER3
```

### Specializáció:
- Választható: **Goalkeeper** vagy **First Team**
- Ugyanaz a folyamat mint User 1

---

## ✅ Ellenőrzési Pontok

### 1. Kredit Egyenleg Változás
```bash
# User 1 kreditet nézd meg
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "SELECT email, credit_balance FROM users WHERE email = 'pwt.k1sqx1@f1stteam.hu';"
```

**Várt eredmény:**
- Kezdet: 50 kredit
- Kupon után: 100 kredit
- Unlock után: 0 kredit

### 2. User License Létrehozás
```bash
# Ellenőrizd hogy létrejött-e a license
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "SELECT u.email, ul.specialization_type, ul.onboarding_completed, ul.credit_balance FROM users u JOIN user_licenses ul ON u.id = ul.user_id WHERE u.email LIKE 'pwt.%';"
```

**Várt eredmény:**
```
           email            | specialization_type | onboarding_completed | credit_balance
----------------------------+---------------------+----------------------+----------------
 pwt.k1sqx1@f1stteam.hu     | first_team          | t                    |              0
```

### 3. Kupon Használat Tracking
```bash
# Ellenőrizd hogy a kupon használva lett-e
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "SELECT code, current_uses, max_uses FROM coupons WHERE code LIKE 'E2E-BONUS%';"
```

**Várt eredmény:**
```
        code        | current_uses | max_uses
--------------------+--------------+----------
 E2E-BONUS-50-USER1 |            1 |        1  ← Használva
 E2E-BONUS-50-USER2 |            0 |        1
 E2E-BONUS-50-USER3 |            0 |        1
```

---

## 🐛 Debug Parancsok

### Kredit visszaállítás (ha újra tesztelni akarod):
```bash
# User 1 kredit visszaállítása 50-re
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "UPDATE users SET credit_balance = 50 WHERE email = 'pwt.k1sqx1@f1stteam.hu';"

# License törlése
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "DELETE FROM user_licenses WHERE user_id = (SELECT id FROM users WHERE email = 'pwt.k1sqx1@f1stteam.hu');"

# Kupon reset
PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "UPDATE coupons SET current_uses = 0 WHERE code = 'E2E-BONUS-50-USER1';"
```

---

## 📝 Teszt Jegyzet Sablon

```
USER: pwt.k1sqx1@f1stteam.hu
KEZDETI KREDIT: ____
KUPON APPLIKÁLÁS: Sikeres / Sikertelen
KUPON UTÁN KREDIT: ____
SPECIALIZÁCIÓ: first_team / goalkeeper
UNLOCK: Sikeres / Sikertelen
VÉGSŐ KREDIT: ____
ONBOARDING COMPLETED: Igen / Nem
HIBÁK: ___________
```

---

## 🎯 Sikerkritériumok

- [ ] Mind a 3 user be tud jelentkezni
- [ ] Specialization Hub betölt mindegyiknek
- [ ] Kupon applikálás működik (+50 kredit)
- [ ] Specializáció feloldás működik (-100 kredit)
- [ ] User license létrejön `onboarding_completed = true`-val
- [ ] Kredit egyenleg pontosan követhető
- [ ] Kupon csak egyszer használható (max_uses = 1)

---

**Jó tesztelést! 🚀**
