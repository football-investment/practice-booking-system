# Tournament Baseline Status - Reference Examples

**Date**: 2026-01-25
**Status**: Updated reward configs, pending final re-distribution

---

## 🏆 Tournament 1: TOURN-20260125-001 - NIKE Speed Test

### Current Configuration (Updated)

**Tournament Details**:
- **Code**: `TOURN-20260125-001`
- **Name**: 🇧🇷 BR - "NIKE Speed Test!" - RIO
- **Format**: INDIVIDUAL_RANKING
- **Measurement**: Time-based (seconds, Lower is Better)
- **Template**: Championship

**Enabled Skills** ✅:
```json
[
  {"skill": "speed", "weight": 2.0, "category": "PHYSICAL", "enabled": true},
  {"skill": "agility", "weight": 1.5, "category": "PHYSICAL", "enabled": true}
]
```

**Why These Skills?**
- **Speed (2.0x)**: Primary metric - sprint performance
- **Agility (1.5x)**: Secondary factor - quick footwork during acceleration

**Rewards Configuration**:
- **1st Place**: 1000 credits, 2.0x XP, "Speed Champion" 🥇 badge
- **2nd Place**: 600 credits, 1.5x XP, "Speed Runner-Up" 🥈 badge
- **3rd Place**: 400 credits, 1.3x XP, "Speed Bronze" 🥉 badge
- **Participation**: 50 credits, 1.0x XP

**Skill Point Distribution** (Expected after re-distribution):
| Placement | Base Points | Speed Points | Agility Points | Total Points | Bonus XP |
|-----------|-------------|--------------|----------------|--------------|----------|
| 1st       | 10.0        | 5.7          | 4.3            | 10.0         | ~100     |
| 2nd       | 7.0         | 4.0          | 3.0            | 7.0          | ~70      |
| 3rd       | 5.0         | 2.9          | 2.1            | 5.0          | ~50      |
| 4th-8th   | 1.0         | 0.6          | 0.4            | 1.0          | ~10      |

---

## 🏋️ Tournament 2: TOURN-20260125-002 - Plank Competition

### Current Configuration (Updated)

**Tournament Details**:
- **Code**: `TOURN-20260125-002`
- **Name**: 🇧🇷 BR - "Plank Competition" - RIO
- **Format**: INDIVIDUAL_RANKING
- **Measurement**: Time-based (seconds, Higher is Better)
- **Template**: Standard

**Enabled Skills** ✅:
```json
[
  {"skill": "stamina", "weight": 2.5, "category": "PHYSICAL", "enabled": true}
]
```

**Why These Skills?**
- **Stamina (2.5x)**: Primary metric - endurance for static plank hold
- **Note**: Originally planned "strength" skill not available in current system, using only stamina

**Rewards Configuration**:
- **1st Place**: 500 credits, 1.5x XP, "Plank Champion" 💪 badge
- **2nd Place**: 300 credits, 1.3x XP, "Plank Runner-Up" 🥈 badge
- **3rd Place**: 200 credits, 1.2x XP, "Plank Bronze" 🥉 badge
- **Participation**: 25 credits, 1.0x XP

**Skill Point Distribution** (Expected after re-distribution):
| Placement | Base Points | Stamina Points | Total Points | Bonus XP |
|-----------|-------------|----------------|--------------|----------|
| 1st       | 10.0        | 10.0           | 10.0         | ~100     |
| 2nd       | 7.0         | 7.0            | 7.0          | ~70      |
| 3rd       | 5.0         | 5.0            | 5.0          | ~50      |
| 4th-8th   | 1.0         | 1.0            | 1.0          | ~10      |

---

## 📊 Current Status

### Reward Config Status
- ✅ **TOURN-20260125-001**: Updated to use `speed` + `agility` (official skills)
- ✅ **TOURN-20260125-002**: Updated to use `stamina` (official skill)
- ❌ **Previous configs**: Used non-existent skills (`core_strength`, `mental_toughness`, `endurance`)

### Distribution Status
- ⚠️ **Old distribution present**: Rewards already distributed with OLD custom skills
- ⏳ **Re-distribution needed**: Must run re-distribution with NEW configs

### Participants
Both tournaments have **8 participants** with placements:
- TOURN-20260125-001: 8 players (Kylian Mbappé 1st, Lamine Jamal 2nd, Martin Ødegaard 3rd, ...)
- TOURN-20260125-002: 8 players (Kylian Mbappé 1st, Cole Palmer 2nd, Lamine Jamal 3rd, ...)

---

## 🔄 Next Steps

### 1. Run Final Re-Distribution

Execute `redistribute_tournaments_final.py` to:
- Delete old reward records (with invalid skills)
- Recalculate rewards using NEW reward_config
- Award skill points for `speed`, `agility`, `stamina` (valid skills)
- Update credits, XP, badges

**Command**:
```bash
python redistribute_tournaments_final.py
```

**Expected Outcome**:
- ✅ TOURN-20260125-001: 8 participants with speed + agility skill points
- ✅ TOURN-20260125-002: 8 participants with stamina skill points
- ✅ No invalid skill names in database

### 2. Verify Results

```sql
-- Check skill points awarded (should only show speed, agility, stamina)
SELECT
  s.code,
  u.email,
  tp.placement,
  jsonb_pretty(tp.skill_points_awarded) as skill_points,
  tp.credits_awarded,
  tp.xp_awarded
FROM tournament_participations tp
JOIN semesters s ON tp.semester_id = s.id
JOIN users u ON tp.user_id = u.id
WHERE s.code IN ('TOURN-20260125-001', 'TOURN-20260125-002')
ORDER BY s.code, tp.placement;
```

**Expected**:
- TOURN-20260125-001: Only `speed` and `agility` in skill_points_awarded
- TOURN-20260125-002: Only `stamina` in skill_points_awarded
- No `core_strength`, `mental_toughness`, `endurance` (invalid skills)

### 3. Mark as Baseline

Once re-distribution is complete:
- ✅ TOURN-20260125-001 → **Baseline example** for INDIVIDUAL_RANKING (time-based, lower is better)
- ✅ TOURN-20260125-002 → **Baseline example** for INDIVIDUAL_RANKING (time-based, higher is better)
- ✅ Both tournaments use **valid system skills** from `ALL_AVAILABLE_SKILLS`
- ✅ Both tournaments follow **admin guide examples**

---

## ⚠️ Known Issues (Before Re-Distribution)

### Issue 1: Invalid Skills in Old Distribution
**Problem**: Previous distribution used non-existent skills:
- `core_strength` (not in `ALL_AVAILABLE_SKILLS`)
- `mental_toughness` (not in `ALL_AVAILABLE_SKILLS`)
- `endurance` (not in `ALL_AVAILABLE_SKILLS`)

**Impact**: Runtime validation would log errors and fall back to legacy table

**Fix**: Re-distribution will replace with valid skills (`speed`, `agility`, `stamina`)

### Issue 2: Mismatched Credits/XP
**Problem**: Old distribution used different credit amounts (150/100/50 for Speed Test, 200/120/80 for Plank)

**Impact**: Not aligned with admin guide examples (Championship: 1000/600/400, Standard: 500/300/200)

**Fix**: Re-distribution will use correct template values

---

## ✅ Post Re-Distribution

After running `redistribute_tournaments_final.py`:

### TOURN-20260125-001 (NIKE Speed Test)
- ✅ Skills: `speed` (2.0x), `agility` (1.5x)
- ✅ 1st Place: 1000 credits, 2.0x XP, Champion badge
- ✅ Skill points distributed proportionally by weight
- ✅ **Reference Example** for speed-based tournaments

### TOURN-20260125-002 (Plank Competition)
- ✅ Skills: `stamina` (2.5x)
- ✅ 1st Place: 500 credits, 1.5x XP, Champion badge
- ✅ 100% of skill points go to stamina (single skill)
- ✅ **Reference Example** for endurance-based tournaments

---

## 📚 Documentation Alignment

These tournaments now match the examples in:
- [ADMIN_GUIDE_TOURNAMENT_SKILL_SELECTION.md](ADMIN_GUIDE_TOURNAMENT_SKILL_SELECTION.md)
  - Example 1: NIKE Speed Test ✅
  - Example 2: Plank Competition ✅

**Difference from Guide**:
- Guide Example 2 shows `stamina` (2.5x) + `strength` (1.5x)
- Actual Implementation: Only `stamina` (2.5x)
- **Reason**: `strength` skill not in current `ALL_AVAILABLE_SKILLS` list

**Recommendation**: Add `strength` skill to system if core strength is a key metric for future tournaments.

---

## 🎯 Conclusion

**Current Status**:
- ✅ Reward configs updated with valid skills
- ⏳ Re-distribution pending (use `redistribute_tournaments_final.py`)

**After Re-Distribution**:
- ✅ Both tournaments become **baseline reference examples**
- ✅ All skills validated and documented
- ✅ Ready for production use as templates

**Next Phase**: Content + Events (reward system complete)
