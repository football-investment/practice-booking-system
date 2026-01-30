# 500 Internal Server Error - FIXED ✅

**Dátum**: 2026-01-28
**Probléma**: 500 error amikor tournament tesztet futtatnak
**Státusz**: ✅ FIXED

---

## 🔴 Probléma

User megnyomta a "Create Sandbox Tournament" gombot, és a rendszer 500 Internal Server Error-t dobott.

### Error Message:
```
TypeError: '<' not supported between instances of 'NoneType' and 'int'
```

### Stack Trace:
```
File "app/api/api_v1/endpoints/sandbox/run_test.py", line 99, in run_sandbox_test
File "app/models/tournament_type.py", line 60, in validate_player_count
TypeError: '<' not supported between instances of 'NoneType' and 'int'
```

### Root Cause:
A kód **validálta a player_count-ot MIELŐTT kiszámolta volna**:

**Hibás sorrend**:
1. Line 99: `tournament_type.validate_player_count(request.player_count)` - request.player_count **None** volt
2. Lines 122-129: player_count kiszámítása (max_players vagy default 16)

Ez logikai hiba volt, mert a `player_count` Optional lett (nem kötelező field), és a validáció futott **azelőtt**, hogy az actual értéket kiszámoltuk volna.

---

## ✅ Megoldás

**Fájl**: [app/api/api_v1/endpoints/sandbox/run_test.py](app/api/api_v1/endpoints/sandbox/run_test.py:92-136)

### Fix: Validation sorrend megcserélése

**ELŐTTE** (Lines 98-129):
```python
# Validate player count against tournament type constraints
is_valid, error_msg = tournament_type.validate_player_count(request.player_count)  # ❌ request.player_count = None!
if not is_valid:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=error_msg
    )

# Validate skills...

# Execute test
try:
    orchestrator = SandboxTestOrchestrator(db)

    # Determine player_count: use provided value, or max_players, or user_ids count, or default 16
    player_count = request.player_count
    if player_count is None:
        if request.max_players:
            player_count = request.max_players
        elif request.user_ids:
            player_count = len(request.user_ids)
        else:
            player_count = 16  # Default
```

**UTÁNA** (Fixed):
```python
# Validate skills...

# Execute test
try:
    orchestrator = SandboxTestOrchestrator(db)

    # Determine player_count: use provided value, or max_players, or user_ids count, or default 16
    player_count = request.player_count
    if player_count is None:
        if request.max_players:
            player_count = request.max_players
        elif request.user_ids:
            player_count = len(request.user_ids)
        else:
            player_count = 16  # Default

    # Validate player count against tournament type constraints (AFTER calculating actual count) ✅
    is_valid, error_msg = tournament_type.validate_player_count(player_count)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
```

**Változások**:
1. ✅ Player count kiszámítása **először**
2. ✅ Validálás **másodszor** (az actual érték ellen)
3. ✅ Skill validáció maradt az elején (independent)

---

## 🧪 Tesztelés

### Test Flow:
1. Open: http://localhost:8503
2. Login: `admin@lfa.com` / `admin123`
3. Configure tournament:
   - Location: Rio de Janeiro
   - Campus: Copacabana Beach Football Center
   - Skills: 16 skills (passzolás, lövés, cselezés, stb.)
   - Max Players: 16
   - Tournament Type: league

4. Click "Create Sandbox Tournament" ✅

### Expected Result:
- ✅ No 500 error
- ✅ Tournament created successfully
- ✅ Reward distribution executed
- ✅ Results displayed

---

## 📊 Related Changes

### Earlier Fixes (Same Session):
1. **Skill Limit**: max_items 4 → 29 (lines 33)
2. **player_count Optional**: Required → Optional (line 34)
3. **Skill Validation**: 6 hardcoded → 29 dynamic skills (lines 106-113)
4. **Player Count Auto-calc**: Added logic to calculate from max_players/user_ids (lines 122-129)

**Új fix**: Validation order (line 99 → after line 129)

---

## 🚀 Következő Lépések

### Sprint 1 Complete ✅
- ✅ Location endpoint integration
- ✅ Campus filtering by location
- ✅ Skill limit removed (4 → 29)
- ✅ player_count made optional
- ✅ 500 error fixed (validation order)

### Sprint 2: End-to-End Testing (Next)
- [ ] Run complete tournament test with 16+ skills
- [ ] Verify reward distribution
- [ ] Test all tournament types (league, knockout, hybrid)
- [ ] Test with real user selection

### Sprint 3: UX Improvements
- [ ] Save config before test execution (user request)
- [ ] Restore config on error
- [ ] Add progress indicators

---

## 💡 Lessons Learned

**Anti-Pattern Identified**:
```python
# BAD: Validate before calculating
validate(request.optional_field)
actual_value = calculate_from_optional(request.optional_field)
```

**Best Practice**:
```python
# GOOD: Calculate first, then validate
actual_value = calculate_from_optional(request.optional_field)
validate(actual_value)
```

**Általános szabály**: Ha egy field Optional, és van számítási logika hozzá, akkor **mindig előbb számítsd ki az actual értéket**, aztán validáld.

---

**Status**: ✅ READY FOR TESTING

Backend: http://localhost:8000
Streamlit V3: http://localhost:8503

Awaiting user testing...
