# 🎓 Hallgatói Státusz Visszaállítás - "Clean Slate" Tesztelési Eszköz

## 📋 Áttekintés

Ez az eszközcsomag lehetővé teszi, hogy minden hallgatót "newcomer" (újonc) státuszba állítsunk vissza, ami tiszta környezetet biztosít a teszteléshez.

## 🛠️ Használat

### 🚀 Gyors használat (ajánlott)

```bash
# 1. Jelenlegi állapot ellenőrzése
./scripts/student_reset.sh check

# 2. Előnézet - mi fog törlődni (biztonságos)
./scripts/student_reset.sh preview

# 3. Tényleges visszaállítás (megerősítéssel)
./scripts/student_reset.sh reset
```

### 📖 Részletes parancsok

```bash
# Help megjelenítése
./scripts/student_reset.sh help

# Jelenlegi hallgatói állapot vizsgálata
./scripts/student_reset.sh check

# Dry-run - előnézet (biztonságos, semmi sem törlődik)
./scripts/student_reset.sh preview

# Tényleges reset megerősítéssel
./scripts/student_reset.sh reset

# Erőltetett reset megerősítés NÉLKÜL (VESZÉLYES!)
./scripts/student_reset.sh force
```

### 🐍 Közvetlen Python használat

```bash
# Állapot ellenőrzése
python scripts/verify_student_clean_state.py

# Dry-run előnézet
python scripts/reset_students_to_newcomer.py --dry-run

# Reset megerősítéssel
python scripts/reset_students_to_newcomer.py

# Reset megerősítés nélkül (VESZÉLYES!)
python scripts/reset_students_to_newcomer.py --confirm
```

## 🗑️ Mit töröl a reset?

A script **minden hallgató** esetében törli a következőket:

### 📊 Projekt-kapcsolódó adatok
- ❌ **Projekt jelentkezések** (project_enrollments)
- ❌ **Mérföldkő haladás** (project_milestone_progress)
- ❌ **Projekt quiz jelentkezések** (project_enrollment_quiz)

### 📝 Quiz adatok
- ❌ **Quiz kísérletek** (quiz_attempts)
- ❌ **Quiz válaszok** (quiz_user_answers)

### 🎮 Gamifikáció
- ❌ **Statisztikák és XP** (user_stats)
- ❌ **Elért jutalmak** (user_achievements)

### 📅 Foglalások
- ❌ **Összes booking** (bookings)

### 🔄 Felhasználói állapot
- ❌ **Onboarding státusz** → `incomplete`-re állítva

## ✅ Mit NEM érint a reset?

- ✅ **Felhasználói fiókok** (users tábla)
- ✅ **Jelszavak és bejelentkezési adatok**
- ✅ **Projektek és órák** (projects, sessions)
- ✅ **Quiz-ek és kérdések** (quizzes, quiz_questions)
- ✅ **Szemeszterek** (semesters)
- ✅ **Oktatók adatai**

## 🔒 Biztonsági intézkedések

### ⚠️ Megerősítés szükséges
A tényleges törlés előtt explicit megerősítés szükséges:
```
Are you sure you want to reset 5 students? (type 'RESET' to confirm): RESET
```

### 🔍 Dry-run mód
Mindig használd először a `--dry-run` / `preview` módot:
```bash
./scripts/student_reset.sh preview
```

### 📊 Automatikus verifikáció
A reset után automatikusan ellenőrzi, hogy sikeres volt-e.

## 📋 Példa munkamenet

```bash
# 1. Jelenlegi állapot
$ ./scripts/student_reset.sh check
👥 Checking 5 student accounts...
❌ STUDENTS WITH REMAINING DATA (4):
  • Nagy Péter: Has 2 project enrollments, Has stats record
  • Juhász Tamás: Has 2 project enrollments, Has 2 quiz attempts

# 2. Előnézet
$ ./scripts/student_reset.sh preview
📊 TOTAL RECORDS TO BE DELETED:
  • Project Enrollments: 7
  • Quiz Attempts: 5
  • Quiz Answers: 3

# 3. Tényleges reset
$ ./scripts/student_reset.sh reset
⚠️ WARNING: This will PERMANENTLY DELETE all student progress data!
❓ Are you sure? (type 'RESET' to confirm): RESET
🎉 RESET COMPLETE!
✅ All 5 students are now in 'newcomer' status

# 4. Verifikáció
✅ SUCCESS: All students are in clean newcomer state!
🚀 Ready for testing!
```

## 🎯 Tesztelési folyamat

A reset után minden hallgató:
- 🆕 **"Newcomer" státuszban** van
- 📝 **Újra kitöltheti** a quiz-eket
- 🚀 **Újra jelentkezhet** projektekre
- 🎮 **Tiszta gamifikációs állapot**
- 📅 **Nincs korábbi booking**

## ❓ Gyakori kérdések

**Q: Biztonságos a használata?**
A: Igen, ha a `preview` móddal ellenőrzöd először.

**Q: Vissza lehet állítani a törölt adatokat?**
A: **NEM!** A törlés végleges. Mindig készíts backup-ot produkciós környezetben.

**Q: Mely hallgatók lesznek érintettek?**
A: **MINDEN** `student` szerepkörű felhasználó.

**Q: Az oktatók és adminok érintettek?**
A: **NEM**, csak a hallgatók.

## 🔧 Hibaelhárítás

```bash
# Import hiba esetén
cd /path/to/project_root
export PYTHONPATH=/path/to/project_root

# Adatbázis kapcsolat hiba
# Ellenőrizd a .env fájlt és az adatbázis elérhetőségét
```

---

**⚠️ FIGYELEM: Ez az eszköz TESZT környezethez készült! Produkciós használat előtt mindig készíts teljes backup-ot!**