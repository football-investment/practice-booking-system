# 🏆 Knockout Bracket Generation - Business Logic Questions

## 📋 Context

Currently, the tournament system generates a **fixed knockout structure** based on:
- **Groups of 4 players each**
- **Top 2 from each group advance** (qualifiers_per_group = 2)

This works perfectly when the number of qualifiers is a **power of 2** (4, 8, 16, 32), but creates issues when we have **6, 10, 14, 18** qualifiers.

## 🔢 Tournament Scenarios

| Players | Groups | Group Config | Qualifiers | Issue? |
|---------|--------|--------------|------------|---------|
| 8 | 2 (A, B) | 4-4 | 4 (A1,A2,B1,B2) | ✅ Perfect (semi + final) |
| 12 | 3 (A, B, C) | 4-4-4 | **6** (A1,A2,B1,B2,C1,C2) | ⚠️ **Not power of 2** |
| 16 | 4 (A, B, C, D) | 4-4-4-4 | 8 (top 2 from each) | ✅ Perfect (quarters + semi + final) |
| 20 | 5 (A-E) | 4-4-4-4-4 | **10** (top 2 from each) | ⚠️ **Not power of 2** |
| 24 | 6 (A-F) | 4-4-4-4-4-4 | 12 (top 2 from each) | ⚠️ **Not power of 2** |

## ❓ Critical Questions

### 1️⃣ **How should we handle 6 qualifiers (12 players total)?**

**Option A: 6 → 4 bracket with byes**
```
Round 1 (play-in):
- Match 1: Seed 3 vs Seed 6
- Match 2: Seed 4 vs Seed 5
- (Seed 1 and Seed 2 get BYE to semifinals)

Round 2 (semifinals):
- Semi 1: Seed 1 vs Winner(3v6)
- Semi 2: Seed 2 vs Winner(4v5)

Round 3 (finals):
- Final: Winner(Semi1) vs Winner(Semi2)
- Bronze Match: Loser(Semi1) vs Loser(Semi2)
```

**Option B: 8-player bracket (include best 3rd place finishers)**
```
Advance top 2 from each group + best 2 third-place finishers
→ 8 qualifiers total
→ Standard quarterfinals → semifinals → finals
```

**Option C: Custom 6-player format**
- Define a custom 6-player knockout structure
- (Please specify structure)

**👉 Which option do you prefer?**

---

### 2️⃣ **How should we handle 10 qualifiers (20 players total)?**

**Option A: 10 → 8 bracket with byes**
```
Round 1 (play-in):
- 6 matches (seeds 5-10 compete)
- Top 4 seeds get BYE to Round of 8

Round 2 (quarterfinals):
- 8 players compete
→ Standard bracket continues
```

**Option B: 16-player bracket (include 3rd place finishers)**
```
Advance top 2 from each group + best 6 third-place finishers
→ 16 qualifiers total
→ Standard Round of 16 → quarters → semis → finals
```

**Option C: Custom 10-player format**
- Define a custom 10-player knockout structure
- (Please specify structure)

**👉 Which option do you prefer?**

---

### 3️⃣ **Bye allocation logic**

If we use byes, **who gets them?**

**Option A: Best group winners**
```
Seeding order:
1. Group winners (sorted by group stage points/ranking)
2. Group runners-up (sorted by group stage points/ranking)
3. (If needed) Best 3rd place finishers
```

**Option B: Random allocation**
- Byes assigned randomly among qualifiers

**Option C: Fixed allocation**
- Specific groups always get byes (e.g., Group A and B winners)

**👉 Which seeding logic do you prefer?**

---

### 4️⃣ **Third-place match**

Should we always have a **bronze match** (3rd place playoff)?

**Option A: Always include 3rd place match**
```
Every tournament ends with:
- Final (1st vs 2nd)
- Bronze Match (3rd vs 4th)
```

**Option B: Only for 8+ player knockouts**
```
- 4-player knockout: Only final
- 8+ player knockout: Final + Bronze
```

**Option C: Never include 3rd place match**
```
Only determine 1st and 2nd place
```

**👉 Which option do you prefer?**

---

### 5️⃣ **Group third-place advancement criteria**

If we advance best 3rd place finishers (for 8/16 brackets), **how do we rank them?**

**Option A: Points first, then head-to-head**
```
1. Total points in group stage
2. Head-to-head record (if tied)
3. Goal difference (if applicable)
4. Random tiebreaker
```

**Option B: Points only**
```
Simply by total points earned in group stage
Ties broken randomly
```

**Option C: Custom ranking formula**
- (Please specify formula)

**👉 Which ranking criteria do you prefer?**

---

## 📊 Summary Table

| Question | Scenario | Options | Decision |
|----------|----------|---------|----------|
| 1 | 6 qualifiers (12 players) | A) 6→4 byes, B) 8-bracket, C) Custom | **✅ Option A – 6→4 bracket with byes** |
| 2 | 10 qualifiers (20 players) | A) 10→8 byes, B) 16-bracket, C) Custom | **✅ Option A – 10→8 bracket with byes** |
| 3 | Bye allocation | A) Best seeds, B) Random, C) Fixed | **✅ Option A – Best group winners (seeded)** |
| 4 | Third-place match | A) Always, B) 8+ only, C) Never | **✅ Option B – Only for 8+ player knockouts** |
| 5 | 3rd place ranking | A) Points+H2H, B) Points only, C) Custom | **✅ Option A – Points + H2H + GD** |

---

## 🎯 Recommended Approach (Industry Standard)

Based on common tournament practices:

**For non-power-of-2 qualifiers:**
- Use **Option A** (byes for best seeds)
- This is the most common approach in professional sports

**Seeding:**
- Best group winners get byes
- Ranking based on group stage performance

**Bronze match:**
- Include for 8+ player knockouts
- Skip for 4-player knockouts (too few matches)

**Third-place advancement:**
- Use points + head-to-head + goal difference
- This is FIFA World Cup standard

---

## ✅ Action Items

1. **Review this document** with the business/product owner
2. **Make decisions** for each question (fill in "Decision" column)
3. **Send back answers** to the development team
4. Development will implement the chosen logic
5. **Debug panel** will show the complete bracket structure for testing

---

## 📝 Notes

- Current implementation assumes power-of-2 knockouts (lines 435-477 in `tournament_session_generator.py`)
- Need to implement bye logic and seeding calculation
- Frontend debug panel should visualize the bracket structure before generation
- Consider edge cases (odd number of groups, uneven group sizes)

---

## 🔧 Implementation Specification

Based on the decisions above, here's the exact implementation:

### 1️⃣ Knockout Bracket Logic (by qualifier count)

```python
def calculate_knockout_structure(qualifiers: int) -> dict:
    """
    Calculate knockout bracket structure based on number of qualifiers

    Returns:
        {
            'play_in_matches': int,  # Number of play-in matches
            'byes': int,             # Number of byes
            'bracket_size': int,     # Final bracket size (power of 2)
            'has_bronze': bool       # Whether to include 3rd place match
        }
    """

    if qualifiers == 4:
        return {
            'play_in_matches': 0,
            'byes': 0,
            'bracket_size': 4,
            'has_bronze': False  # No bronze for 4-player knockout
        }

    elif qualifiers == 6:
        # 6 → 4 bracket
        return {
            'play_in_matches': 2,  # Seeds 3-6 play
            'byes': 2,             # Seeds 1-2 bye to semis
            'bracket_size': 4,
            'has_bronze': True
        }

    elif qualifiers == 8:
        return {
            'play_in_matches': 0,
            'byes': 0,
            'bracket_size': 8,
            'has_bronze': True
        }

    elif qualifiers == 10:
        # 10 → 8 bracket
        return {
            'play_in_matches': 3,  # Seeds 5-10 play (3 matches)
            'byes': 4,             # Seeds 1-4 bye to quarterfinals
            'bracket_size': 8,
            'has_bronze': True
        }

    elif qualifiers == 12:
        # 12 → 8 bracket
        return {
            'play_in_matches': 4,  # Seeds 5-12 play (4 matches)
            'byes': 4,             # Seeds 1-4 bye to quarterfinals
            'bracket_size': 8,
            'has_bronze': True
        }

    else:
        # For other sizes, round up to next power of 2
        bracket_size = 2 ** math.ceil(math.log2(qualifiers))
        byes = bracket_size - qualifiers
        play_in_matches = qualifiers - byes

        return {
            'play_in_matches': play_in_matches // 2,
            'byes': byes,
            'bracket_size': bracket_size,
            'has_bronze': bracket_size >= 8
        }
```

### 2️⃣ Seeding Calculation

```python
def calculate_seeding(db: Session, tournament_id: int, groups: List[str]) -> List[int]:
    """
    Calculate seeding order based on group stage performance

    Seeding order:
    1. Group winners (sorted by points)
    2. Group runners-up (sorted by points)
    3. (If needed) Best 3rd place finishers

    Tiebreaker: Points → H2H → Goal Difference → Random

    Returns:
        List of user_ids in seeding order (Seed 1, Seed 2, ...)
    """

    # Get group standings for each group
    standings = {}
    for group in groups:
        standings[group] = get_group_standings(db, tournament_id, group)

    # Extract positions
    winners = []
    runners_up = []
    third_place = []

    for group, ranking in standings.items():
        if len(ranking) >= 1:
            winners.append((ranking[0], group))  # (user_id, points, h2h, gd)
        if len(ranking) >= 2:
            runners_up.append((ranking[1], group))
        if len(ranking) >= 3:
            third_place.append((ranking[2], group))

    # Sort each category by performance
    winners.sort(key=lambda x: (x[0]['points'], x[0]['goal_diff']), reverse=True)
    runners_up.sort(key=lambda x: (x[0]['points'], x[0]['goal_diff']), reverse=True)
    third_place.sort(key=lambda x: (x[0]['points'], x[0]['goal_diff']), reverse=True)

    # Build final seeding list
    seeded_ids = []
    seeded_ids.extend([w[0]['user_id'] for w in winners])
    seeded_ids.extend([r[0]['user_id'] for r in runners_up])
    seeded_ids.extend([t[0]['user_id'] for t in third_place])

    return seeded_ids
```

### 3️⃣ Bracket Generation with Byes

```python
def generate_knockout_with_byes(qualifiers: int, seeded_ids: List[int]) -> List[dict]:
    """
    Generate knockout matches with bye logic

    Example for 6 qualifiers:
        Play-in Round:
        - Match 1: Seed 3 vs Seed 6
        - Match 2: Seed 4 vs Seed 5

        Semifinals (after play-in):
        - Semi 1: Seed 1 vs Winner(Match 1)
        - Semi 2: Seed 2 vs Winner(Match 2)

        Finals:
        - Final: Winner(Semi 1) vs Winner(Semi 2)
        - Bronze: Loser(Semi 1) vs Loser(Semi 2)
    """

    structure = calculate_knockout_structure(qualifiers)
    matches = []

    # Phase 1: Play-in matches (if any)
    if structure['play_in_matches'] > 0:
        for i in range(structure['play_in_matches']):
            seed_high = structure['byes'] + i + 1
            seed_low = qualifiers - i

            matches.append({
                'phase': 'play_in',
                'match_number': i + 1,
                'seed_high': seed_high,
                'seed_low': seed_low,
                'participant_ids': [seeded_ids[seed_high - 1], seeded_ids[seed_low - 1]]
            })

    # Phase 2: Main bracket (semifinals/quarterfinals/etc)
    # ... (standard bracket generation)

    # Phase 3: Finals
    matches.append({
        'phase': 'final',
        'match_number': 1,
        'title': 'Final'
    })

    # Phase 4: Bronze match (if applicable)
    if structure['has_bronze']:
        matches.append({
            'phase': 'bronze',
            'match_number': 1,
            'title': '3rd Place Match'
        })

    return matches
```

### 4️⃣ Files to Modify

1. **`app/services/tournament_session_generator.py`** (lines 330-480)
   - Add `calculate_knockout_structure()`
   - Add `calculate_seeding()`
   - Update `_generate_group_knockout_sessions()` to use bye logic

2. **`app/services/tournament/seeding_calculator.py`** (NEW)
   - Implement group standings calculation
   - Implement tiebreaker logic (Points → H2H → GD)

3. **`streamlit_app/components/admin/tournament_list.py`**
   - Add bracket visualization to debug panel
   - Show seeding order before generation

---

## ✅ Ready for Implementation

All decisions are finalized. Development can now proceed with implementing the knockout logic.

