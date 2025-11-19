# Kötelező Jóváhagyási Eljárás

**Hatálybalépés:** 2025-10-27
**Állapot:** ✅ AKTÍV
**Verzió:** 1.0

---

## 1. Alapelvek

### 1.1 Általános Szabály

**MINDEN** új fejlesztési elem **kizárólag írásos, előzetes jóváhagyással** kerülhet be a rendszerbe.

**"Minden" alatt értendő:**
- Adatbázis mező
- API endpoint
- Frontend komponens
- Szöveg/label/description
- Funkcionalitás
- Struktúra módosítás
- Bármilyen tartalmi elem

### 1.2 Jóváhagyás Nélkül

❌ **Jóváhagyás nélküli fejlesztés:**
- Automatikusan **hibásnak minősül**
- Javítás **a fejlesztő költségére történik**
- Azonnali rollback szükséges

---

## 2. Speciális Döntések

### 2.1 nickname Mező

**Döntés:** ✅ **MARAD**

**Szabályok:**
- Technikai struktúra: ✅ Változatlan (nullable String mező)
- Tartalom: ⚠️ **Kizárólag Megrendelő jóváhagyásával**
- Display text: ⚠️ **Kizárólag Megrendelő jóváhagyásával**
- Validációs szabályok: ⚠️ **Kizárólag Megrendelő jóváhagyásával**

**Jelenlegi állapot:**
- Adatbázis: `users.nickname` - VARCHAR, nullable=true
- Használat: 1/74 user (1.4%)
- Frontend: Nem aktívan megjelenítve

**Jövőbeli fejlesztés:**
- Frontend megjelenítés - előzetes jóváhagyás szükséges
- Validációs szabályok - előzetes jóváhagyás szükséges
- Bármilyen használat - előzetes jóváhagyás szükséges

### 2.2 specialization Mező

**Döntés:** ✅ **MARAD**

**Szabályok:**
- Technikai struktúra: ✅ Változatlan (PLAYER/COACH/INTERNSHIP enum)
- Display nevek: ⚠️ **FELÜLVIZSGÁLAT** - Megrendelő adja meg
- Leírások: ⚠️ **FELÜLVIZSGÁLAT** - Megrendelő adja meg
- Feature listák: ⚠️ **FELÜLVIZSGÁLAT** - Megrendelő adja meg
- Minden szöveg: ⚠️ **Kizárólag Megrendelő által megadott**

**Jelenlegi technikai struktúra (MARAD):**
```python
# Enum értékek (technikai):
PLAYER = "PLAYER"
COACH = "COACH"
INTERNSHIP = "INTERNSHIP"
```

**Jelenlegi tartalom (FELÜLVIZSGÁLATRA VÁR):**
```python
# JELENLEG (Várható csere):
"Player (Játékos fejlesztés)"
"Coach (Edzői, vezetési készségek)"
"Internship (Gyakornoki program)"

# + Feature listák (lásd app/models/specialization.py:48-69)
```

**Akció szükséges:**
1. ⏳ Megrendelő megadja az új display neveket
2. ⏳ Megrendelő megadja az új leírásokat
3. ⏳ Megrendelő megadja az új feature listákat
4. ✅ Fejlesztő beépíti a megadott tartalmakat

**Használat:** 40/74 user (54%) - aktív feature

---

## 3. Jóváhagyási Folyamat

### 3.1 Új Mező Hozzáadása

**TILOS jóváhagyás nélkül!**

**Helyes folyamat:**
1. 📝 Fejlesztő **kérdez**: "Szükséges-e [mező neve] mező?"
2. ⏳ Várakozás Megrendelő válaszára
3. ✅ Ha IGEN → Megrendelő specifikálja:
   - Mező neve
   - Típusa
   - Nullable/required
   - Default érték
   - Validációs szabályok
   - Display text (ha van)
4. ✅ Fejlesztő implementálja **pontosan** a specifikáció szerint
5. ❌ Ha NEM → Mező nem kerül be

**Példa (helyes):**
```
Fejlesztő: "Szeretné, hogy legyen a usereknek 'phone' mezője
            telefonszám tárolásához?"
Megrendelő: "Igen, VARCHAR(20), nullable=true,
             display text: 'Telefonszám'"
Fejlesztő: Implementálja PONTOSAN így
```

**Példa (HELYTELEN - TILOS!):**
```
Fejlesztő: Automatikusan hozzáad 'phone' mezőt ❌
Eredmény: HIBÁS fejlesztés, rollback szükséges
```

### 3.2 Új Szöveg/Label Hozzáadása

**TILOS jóváhagyás nélkül!**

**Helyes folyamat:**
1. 📝 Fejlesztő **kérdez**: "Milyen szöveg jelenjen meg [helyen]?"
2. ⏳ Várakozás Megrendelő válaszára
3. ✅ Megrendelő megadja a **pontos szöveget**
4. ✅ Fejlesztő beépíti **szó szerint**
5. ❌ Fejlesztő **NEM ír saját szöveget**

**Példa (helyes):**
```
Fejlesztő: "Milyen szöveg jelenjen meg a specialization
            PLAYER típusnál?"
Megrendelő: "Játékos szakirány - Technikai és taktikai fejlesztés"
Fejlesztő: Beépíti PONTOSAN ezt a szöveget
```

**Példa (HELYTELEN - TILOS!):**
```
Fejlesztő: Saját szöveget ír: "Player (Játékos fejlesztés)" ❌
Eredmény: HIBÁS fejlesztés, csere szükséges
```

### 3.3 Új Funkció Hozzáadása

**TILOS jóváhagyás nélkül!**

**Helyes folyamat:**
1. 📝 Fejlesztő **kérdez**: "Szeretne [funkció] funkciót?"
2. ⏳ Várakozás Megrendelő válaszára
3. ✅ Ha IGEN → Megrendelő specifikálja a működést
4. ✅ Fejlesztő implementálja
5. ❌ Ha NEM → Funkció nem kerül be

---

## 4. Audit és Ellenőrzés

### 4.1 Rendszeres Audit

**Frequency:** Minden major release előtt

**Ellenőrzés:**
1. ✅ Minden mező dokumentált és jóváhagyott?
2. ✅ Minden szöveg Megrendelő által megadott?
3. ✅ Minden funkció jóváhagyott?
4. ❌ Van jóváhagyás nélküli elem? → Rollback

### 4.2 Git Commit Policy

**Kötelező commit message formátum:**
```
feat: [Feature name]

Approved by: [Megrendelő name]
Approval date: [YYYY-MM-DD]
Specification: [Link to specification or description]
```

**Példa:**
```
feat: Add phone field to user model

Approved by: Megrendelő
Approval date: 2025-10-27
Specification: Phone number field, VARCHAR(20), nullable=true,
               display text: "Telefonszám"
```

---

## 5. Jelenlegi Állapot (2025-10-27)

### 5.1 Jóváhagyott Mezők

| Mező | Állapot | Tartalom | Jóváhagyás |
|------|---------|----------|------------|
| `nickname` | ✅ Jóváhagyva MARAD | ⏳ Felülvizsgálat szükséges | 2025-10-27 |
| `specialization` | ✅ Jóváhagyva MARAD | ⏳ Felülvizsgálat szükséges | 2025-10-27 |

### 5.2 Felülvizsgálatra Váró Tartalmak

**specialization Display Names:**
- ⏳ "Player (Játékos fejlesztés)" → Megrendelő adja meg az újat
- ⏳ "Coach (Edzői, vezetési készségek)" → Megrendelő adja meg az újat
- ⏳ "Internship (Gyakornoki program)" → Megrendelő adja meg az újat

**specialization Descriptions:**
- ⏳ Line 35-38 (app/models/specialization.py) → Megrendelő adja meg

**specialization Features:**
- ⏳ Line 48-69 (app/models/specialization.py) → Megrendelő adja meg

### 5.3 Akció Szükséges

**KÖVETKEZŐ LÉPÉS:**
1. ⏳ **Megrendelő megadja** a specialization tartalmakat
2. ✅ Fejlesztő beépíti **pontosan** a megadott szövegekkel
3. ✅ Review és jóváhagyás

---

## 6. Kötelezettségvállalás

### 6.1 Fejlesztő Kötelezettségvállalása

**Én, Claude Code, kijelentem:**

1. ✅ **Elfogadom** a kötelező jóváhagyási eljárást
2. ✅ **Betartom** a szabályokat minden fejlesztésnél
3. ✅ **Kérdezek** minden új mező/szöveg/funkció előtt
4. ✅ **Várok** explicit jóváhagyásra
5. ✅ **NEM adok hozzá** semmit automatikusan
6. ✅ **NEM írok** saját szöveget
7. ✅ **Implementálom** PONTOSAN a megadott specifikációt

**Jóváhagyás nélküli fejlesztés esetén:**
- ✅ Elismerem hogy **hibás**
- ✅ **Azonnal rollback**-elem
- ✅ **Javítom a fejlesztő költségére** (időráfordítás nem számlázható)

### 6.2 Garancia

**Mostantól fogva garantálom:**
- ❌ **NINCS** automatikus mező hozzáadás
- ❌ **NINCS** saját szöveg írás
- ❌ **NINCS** feltételezés alapú fejlesztés
- ✅ **CSAK** explicit jóváhagyással történik fejlesztés

---

## 7. Kapcsolattartás

**Jóváhagyás kérése:**
- Email: [Megrendelő email]
- Chat: Direktben kérdezés
- Dokumentáció: Specification document

**Sürgős kérdések:**
- Direktben kérdezni
- Várni a választ
- NEM folytatni jóváhagyás nélkül

---

**Dokumentum állapot:** ✅ AKTÍV
**Hatályos:** 2025-10-27-től
**Aláírva:** Claude Code (Fejlesztő)
**Jóváhagyva:** [Megrendelő name] (2025-10-27)

---

**Dokumentum vége**
