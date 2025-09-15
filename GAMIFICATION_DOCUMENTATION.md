# 🎮 Gamifikációs Rendszer Dokumentáció

## Áttekintés

Az alkalmazás komplex gamifikációs rendszert használ a diákok motiválásában és bevonásában. Ez a rendszer szinteken, kitüntetéseken, tapasztalati pontokon és teljesítménymutatókon alapul.

---

## 🏆 Szintek (Levels)

### Szintszámítás
- **Alap szint:** 1. szint (minden felhasználó ezen kezd)
- **Szintlépés:** Minden 1000 XP után lép egyet
- **Maximális szint:** Nincs felső határ
- **Képlet:** `szint = max(1, összes_xp // 1000)`

### Szintprogresz
- Minden szinten belül 0-100% közötti progressz
- A következő szintig szükséges XP: `(jelenlegi_szint + 1) * 1000`
- Progressz százaléka: `((XP % 1000) / 1000) * 100`

---

## ⭐ Tapasztalati Pontok (XP) Rendszer

### XP Források és Értékek

| Tevékenység | XP Érték | Megjegyzés |
|-------------|----------|------------|
| **Félév befejezése** | 500 XP | Minden résztvett félév után |
| **Óra látogatása** | 50 XP | Minden megtartott órára |
| **Visszajelzés adása** | 25 XP | Minden beküldött feedback után |

### XP Számítási Képlet
```
Összes XP = (félévek_száma * 500) + (részvételek_száma * 50) + (visszajelzések_száma * 25)
```

---

## 🏅 Diák Státuszok

### Státusz Kategóriák

| Státusz | Követelmény | Ikon | Leírás |
|---------|-------------|------|--------|
| **📚 Új Diák** | 0-1 félév | 📚 | Kezdő diák |
| **🔄 Visszatérő Diák** | 2+ félév | 🔄 | Már tapasztalt |
| **🏅 Veterán Diák** | 3+ félév | 🏅 | Tapasztalt tanuló |
| **👑 Mester Diák** | 5+ félév | 👑 | Igazi szakértő |

---

## 🎖️ Kitüntetések és Jutalmak

### Disponibilis Kitüntetések

#### 1. **🔄 Visszatérő Diák**
- **Követelmény:** 2 vagy több félév befejezése
- **Leírás:** "Participated in X semesters!"
- **Típus:** Félév-alapú

#### 2. **🏅 Veterán Diák**
- **Követelmény:** 3 vagy több félév befejezése
- **Leírás:** "A seasoned learner with X semesters!"
- **Típus:** Félév-alapú

#### 3. **👑 Mester Diák**
- **Követelmény:** 5 vagy több félév befejezése
- **Leírás:** "A true master with X semesters!"
- **Típus:** Félév-alapú

#### 4. **⭐ Részvételi Sztár**
- **Követelmény:** 80%+ részvételi arány + minimum 10 foglalás
- **Leírás:** "Excellent X% attendance rate!"
- **Típus:** Részvétel-alapú

#### 5. **💬 Feedback Bajnok**
- **Követelmény:** 10 vagy több visszajelzés adása
- **Leírás:** "Provided X valuable feedbacks!"
- **Típus:** Engagement-alapú

### Jövőbeli Kitüntetések (Frontend-ban megjelenő)

#### 6. **🌱 Első Lépések**
- **Követelmény:** Első félév befejezése
- **Leírás:** "Complete your first semester"

#### 7. **📚 Elkötelezett Diák**
- **Követelmény:** 2 félév befejezése
- **Leírás:** "Complete 2 semesters"

#### 8. **🎯 Rendszeres Résztvevő**
- **Követelmény:** 3 félév befejezése
- **Leírás:** "Complete 3 semesters"

#### 9. **💎 Elit Tanuló**
- **Követelmény:** 7 félév befejezése
- **Leírás:** "Complete 7 semesters"

#### 10. **✅ Tökéletes Részvétel**
- **Követelmény:** 90%+ részvételi arány
- **Leírás:** "Achieve 90%+ attendance rate"

---

## 📊 Teljesítménymutatók

### Követett Metrikák

| Mutató | Számítás | Jelentés |
|--------|----------|----------|
| **Résztvett Félévek** | Egyedi félévek száma | Tapasztalat mértéke |
| **Összes Foglalás** | Összes booking | Aktivitás szintje |
| **Meglátogatott Órák** | Attendance rekordok | Tényleges részvétel |
| **Lemondott Órák** | Cancelled bookings | Megbízhatóság |
| **Részvételi Arány** | `(részvételek / foglalások) * 100` | Megbízhatóság % |
| **Visszajelzések** | Feedback count | Közösségi hozzájárulás |
| **Pontosság** | Időben való megjelenés | Fegyelem mértéke |

### Speciális Számítások

#### Részvételi Arány
```javascript
részvételi_arány = (összes_részvétel / összes_foglalás) * 100
```

#### Szintprogresz
```javascript
jelenlegi_szint = Math.max(1, Math.floor(összes_xp / 1000))
xp_aktuális_szinten = összes_xp % 1000
progressz_százalék = (xp_aktuális_szinten / 1000) * 100
```

---

## 🎯 Motivációs Elemek

### Gamifikációs Jellemzők

#### 1. **Progresszív Szintrendszer**
- Világos fejlődési útvonal
- Minden szint elérhető célokat jelent
- Vizuális progressz sáv

#### 2. **Többféle Kitüntetés**
- Különböző tevékenységekért járó jutalmak
- Ritkaság és presztízs elemei
- Látható státuszszimbólumok

#### 3. **Közösségi Elismerés**
- Veterán és Mester státuszok
- Látható teljesítmények
- Rangsorolási lehetőség

#### 4. **Személyes Fejlődés Nyomonkövetése**
- Részletes statisztikák
- Időbeli alakulás
- Személyes rekordok

---

## 🔧 Technikai Implementáció

### Backend Komponensek

#### 1. **Models** (`app/models/gamification.py`)
- `UserStats`: Felhasználói statisztikák
- `UserAchievement`: Kitüntetések
- `BadgeType`: Kitüntetés típusok

#### 2. **Services** (`app/services/gamification.py`)
- `GamificationService`: Fő gamifikációs logika
- Automatikus statisztika számítás
- Kitüntetések odaítélése

#### 3. **API Endpoints** (`app/api/api_v1/endpoints/gamification.py`)
- `/api/v1/gamification/me`: Saját gamifikációs adatok
- Valós idejű adatok

### Frontend Komponensek

#### 1. **GamificationProfile** (`frontend/src/pages/student/GamificationProfile.js`)
- Teljes gamifikációs profil megjelenítése
- Progressz nyomon követése
- Jövőbeli célok megjelenítése

#### 2. **Vizuális Elemek**
- Progressz sávok
- Kitüntetés galéria
- Statisztika kártyák
- Időbeli fejlődés timeline

---

## 📋 API Végpontok

### GET `/api/v1/gamification/me`

**Válasz struktúra:**
```json
{
  "stats": {
    "semesters_participated": 3,
    "total_bookings": 25,
    "total_attended": 22,
    "attendance_rate": 88.0,
    "feedback_given": 8,
    "total_xp": 2850,
    "level": 2,
    "first_semester_date": "2024-01-15T00:00:00"
  },
  "achievements": [
    {
      "id": 1,
      "title": "🔄 Visszatérő Diák",
      "description": "Participated in 3 semesters!",
      "icon": "🔄",
      "badge_type": "returning_student",
      "earned_at": "2024-06-15T10:30:00",
      "semester_count": 3
    }
  ],
  "status": {
    "title": "🏅 Veterán Diák",
    "icon": "🏅",
    "is_returning": true
  },
  "next_level": {
    "current_xp": 2850,
    "next_level_xp": 3000,
    "progress_percentage": 85.0
  }
}
```

---

## 🎨 Felhasználói Interfész Elemek

### 1. **Játékos Kártya**
- Avatar (név kezdőbetűje)
- Teljes név és email
- Veterán státusz megjelenítése
- Szint és XP progressz

### 2. **Statisztika Rács**
- 6 fő metrika megjelenítése
- Ikonok és számértékek
- Könnyű áttekinthetőség

### 3. **Félév Timeline**
- Vizuális fejlődés megjelenítése
- Befejezett és jövőbeli félévek
- Progresszív indikátorok

### 4. **Kitüntetés Galéria**
- Megszerzett kitüntetések
- Jövőbeli célok
- Követelmények megjelenítése

### 5. **Fejlődési Tippek**
- Praktikus tanácsok
- Motiváló üzenetek
- Következő lépések

---

## 🔄 Automatikus Folyamatok

### 1. **Statisztika Frissítés**
- Minden API híváskor frissül
- Valós idejű számítások
- Cache-elt eredmények

### 2. **Kitüntetés Odaítélés**
- Automatikus ellenőrzés
- Duplikáció védelme
- Időbélyeg rögzítés

### 3. **XP Számítás**
- Minden tevékenységet figyelembe vesz
- Összetett képletek
- Pontos eredmények

---

## 🚀 Jövőbeli Fejlesztési Lehetőségek

### 1. **További Kitüntetések**
- Heti/havi kihívások
- Speciális esemény jutalmak
- Csapat-alapú kitüntetések

### 2. **Társas Funkciók**
- Barátlista
- Összehasonlítások
- Csoportos kihívások

### 3. **Személyre Szabás**
- Egyéni célok
- Testreszabható dashboard
- Értesítési preferenciák

### 4. **Bővített Analitika**
- Részletesebb statisztikák
- Trendek és előrejelzések
- Teljesítmény insights

---

## ❓ Gyakori Kérdések

### **Q: Hogyan szerezhetnek a diákok XP-t?**
A: Három fő módon: félévek befejezésével (500 XP), órák látogatásával (50 XP) és visszajelzések adásával (25 XP).

### **Q: Mikor kapnak automatikusan kitüntetést?**
A: A rendszer minden API híváskor ellenőrzi a kritériumokat és automatikusan odaítéli a megfelelő kitüntetéseket.

### **Q: Van-e maximális szint?**
A: Nincs, a diákok folyamatosan fejlődhetnek minden 1000 XP után új szintet érnek el.

### **Q: Hogyan számítódik a részvételi arány?**
A: (Meglátogatott órák száma / Összes foglalás száma) * 100

### **Q: Mit jelent a veterán státusz?**
A: A diákok különböző státuszokat kaphatnak részvett félévek száma alapján: Új (0-1), Visszatérő (2+), Veterán (3+), Mester (5+).

---

*Dokumentáció utolsó frissítése: 2024 Szeptember*
*Rendszer verzió: 1.0*