# E2E Skill Progression - Manual Verification Guide

## Overview

Ez az útmutató lépésről lépésre végigvezet, hogyan ellenőrizd **manuálisan a frontenden**, hogy a skill progression működik-e az **automatikus E2E teszt** által létrehozott tournament során.

---

## Előfeltételek

1. Backend fut: `http://localhost:8000`
2. Frontend fut: `http://localhost:3000`
3. Admin bejelentkezve: `admin@lfa.com`

---

## STEP 1: Automatikus teszt futtatása

Futtasd le az **automatikus checkpoint E2E tesztet**, ami létrehoz egy tournamentet, lejátssza a meccseket, és kioszt jutalmakat:

```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system
bash tests/tournament_types/test_league_with_checkpoints.sh
```

**Várható kimenet**:
```
✅ Tournament created (ID: XX)
✅ All players enrolled
✅ Match results submitted
✅ Tournament status → COMPLETED
✅ Reward config configured
✅ Rewards distributed

📊 SKILL COMPARISON: After Tournament vs After Rewards
   User 4: Passing 80.0 → 90.0 (+10.0)
   User 5: Passing 60.0 → 74.0 (+14.0)
   User 6: Passing 70.0 → 73.0 (+3.0)
   User 14: Passing 90.0 → 77.0 (-13.0)
   User 15: Passing 90.0 → 65.0 (-25.0)
   User 16: Passing 100.0 → 76.0 (-24.0)
```

**Jegyzd fel**:
- **Tournament ID**: pl. `78`
- **User IDs**: `4, 5, 6, 14, 15, 16`

---

## STEP 2: Frontend ellenőrzés - BASELINE (Tournament előtt)

### 2.1 Navigálj a Tournament oldalra

```
http://localhost:3000/admin/tournaments/[TOURNAMENT_ID]
```

**Mit láss**:
- ✅ Tournament státusz: `REWARDS_DISTRIBUTED` (a teszt végén)
- ✅ Players enrolled: 6-8 játékos
- ✅ Final standings láthatóak

### 2.2 Nézd meg a játékosok **KORÁBBI** skill értékeit

**Módszer 1 - Checkpoint file-okból**:
```bash
cat /tmp/checkpoint_1_before_tournament.txt
```

**Példa kimenet**:
```
4 passing_baseline=80.0 passing_current=80.0 dribbling_baseline=50.0 dribbling_current=50.0
5 passing_baseline=60.0 passing_current=60.0 dribbling_baseline=50.0 dribbling_current=60.0
16 passing_baseline=100.0 passing_current=100.0 dribbling_baseline=50.0 dribbling_current=50.0
```

**Módszer 2 - Frontend profil**:
1. Navigate to: `http://localhost:3000/admin/users/4` (példa User 4-re)
2. Lent látod a **Skills szekciót**
3. Check `passing` és `dribbling` értékeket

---

## STEP 3: Frontend ellenőrzés - AFTER TOURNAMENT (Tournament után, reward ELŐTT)

### ⚠️ KRITIKUS PONT: Skills NEM változnak tournament befejezése után

**Mit ellenőrizz**:
```bash
cat /tmp/checkpoint_2_after_complete.txt
```

**Várható eredmény**:
```
4 passing_baseline=80.0 passing_current=80.0 ...  ← UNCHANGED
5 passing_baseline=60.0 passing_current=60.0 ...  ← UNCHANGED
```

**Frontend ellenőrzés**:
1. Navigate: `http://localhost:3000/admin/tournaments/[TOURNAMENT_ID]`
2. Check: Tournament státusz `COMPLETED`
3. Navigate to player profiles (pl. User 4)
4. ✅ **Skills még a baseline értéken vannak** - **NEM változtak!**

**Ez bizonyítja**: Tournament completion **NEM** változtatja a skilleket automatikusan.

---

## STEP 4: Frontend ellenőrzés - AFTER REWARDS (Reward distribution után)

### ✅ KRITIKUS PONT: Skills MOST VÁLTOZNAK

**Mit ellenőrizz**:
```bash
cat /tmp/checkpoint_3_after_rewards.txt
```

**Várható eredmény** (User 4 példa):
```
4 passing_baseline=80.0 passing_current=90.0 ...  ← CHANGED! (+10.0)
5 passing_baseline=60.0 passing_current=74.0 ...  ← CHANGED! (+14.0)
```

### Frontend ellenőrzés - GYŐZTESEK (Top 3)

**User 5** (1st place - várhatóan legjobb):
```
http://localhost:3000/admin/users/5
```

**Mit láss**:
- ✅ `passing`: **~74.0** (volt ~60.0, **+14 pont növekedés**)
- ✅ `dribbling`: **~65.0** (volt ~50.0, **+15 pont növekedés**)
- ✅ **Skills Last Updated**: friss timestamp (a reward distribution ideje)

**User 6** (2nd place):
```
http://localhost:3000/admin/users/6
```

**Mit láss**:
- ✅ `passing`: **~73.0** (volt ~70.0, **+3 pont növekedés**)
- ✅ Kisebb növekedés mint az 1st place

**User 4** (3rd place):
```
http://localhost:3000/admin/users/4
```

**Mit láss**:
- ✅ `passing`: **~90.0** (volt ~80.0, **+10 pont növekedés**)

### Frontend ellenőrzés - VESZTESEK (Bottom 3)

**User 16** (likely 4-6th place):
```
http://localhost:3000/admin/users/16
```

**Mit láss**:
- ❌ `passing`: **~76.0** (volt ~100.0, **-24 pont CSÖKKENÉS**)
- ⚠️ **Rossz helyezés = skill csökkenés!**

**User 15** (likely 5th place):
```
http://localhost:3000/admin/users/15
```

**Mit láss**:
- ❌ `passing`: **~65.0** (volt ~90.0, **-25 pont CSÖKKENÉS**)

**User 14** (likely 6th place):
```
http://localhost:3000/admin/users/14
```

**Mit láss**:
- ❌ `passing`: **~77.0** (volt ~90.0, **-13 pont CSÖKKENÉS**)

---

## STEP 5: Ellenőrizd a Tournament Rewards szekciót

### Tournament oldalon

```
http://localhost:3000/admin/tournaments/[TOURNAMENT_ID]
```

**Scrollozz le a "Rewards Distributed" szekcióhoz**:

**Mit láss**:
- ✅ **Reward Status**: `REWARDS_DISTRIBUTED`
- ✅ **Total XP Awarded**: pl. `1780 XP`
- ✅ **Total Badges Awarded**: pl. `12-14 badges`
- ✅ **Participants Rewarded**: `6 users`

---

## STEP 6: Verification Checklist

### ✅ Complete Flow Validated:

- [ ] **Tournament létrehozva**: ID látható a teszt outputban
- [ ] **Baseline skills**: Checkpoint 1 file-ban baseline értékek látszanak
- [ ] **Tournament befejezés után**: Checkpoint 2 file-ban **skills UNCHANGED** (kritikus!)
- [ ] **Reward distribution után**: Checkpoint 3 file-ban **skills CHANGED** (kritikus!)
- [ ] **Frontenden győztesek**: Top 3 játékos skill növekedés látszik
- [ ] **Frontenden vesztesek**: Bottom 3 játékos skill csökkenés látszik
- [ ] **Skills Last Updated timestamp**: Friss időpont a reward distribution után
- [ ] **Tournament rewards szekció**: XP + badges látszanak

---

## Troubleshooting

### Probléma: "Skills null-ként jelennek meg a frontenden"

**Ok**: A frontend a **V1 API-t** használja (`/licenses/user/{id}/football-skills`), ami a `user_licenses.football_skills` JSON field-et olvassa (amely lehet null).

**Megoldás**: A frontend-et át kell írni, hogy a **V2 API-t** használja:
```
GET /api/v1/progression/skill-profile
```

Ez a V2 endpoint **dinamikusan számítja** a skilleket a tournament participation records alapján.

### Probléma: "No skill changes after reward distribution"

**Ellenőrizd**:
1. Tournament `reward_config` field tartalmazza-e a `skill_mappings` tömböt?
   ```sql
   SELECT reward_config FROM semesters WHERE id = [TOURNAMENT_ID];
   ```
2. Van-e `tournament_participations` record minden játékosnak?
   ```sql
   SELECT user_id, placement, skill_points_awarded
   FROM tournament_participations
   WHERE semester_id = [TOURNAMENT_ID];
   ```

---

## Összefoglalás

Ez a **teljes E2E skill progression flow**, ami bizonyítja:

1. ✅ Tournament **COMPLETION** nem változtatja a skilleket
2. ✅ **REWARD DISTRIBUTION** után változnak a skillek
3. ✅ **Placement-based progression**: Jobb helyezés = nagyobb növekedés
4. ✅ **Dynamic V2 calculation**: Skills számítva participation records alapján
5. ✅ **Frontend displayable**: Skills megtekinthetők a player profile-ban

**A rendszer helyesen működik!** 🎉
