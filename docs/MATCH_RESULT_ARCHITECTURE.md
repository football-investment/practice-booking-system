# Match Result Architecture - Complete Flow Documentation

## 🎯 Core Principle

**USER RECORDS MATCH RESULTS (match-scoped performance data)**
**BACKEND DERIVES TOURNAMENT RANKINGS (aggregated from all match results)**

---

## 📋 Example: 8-Player Tournament (2 Groups + Knockout)

### Tournament Structure

**Total Players:** 8
**Group Stage:** 2 groups of 4 players each
**Knockout Stage:** Top 2 from each group qualify

#### Group A
- **13** - Kylian Mbappé
- **15** - Cole Palmer
- **4** - Tamás Juhász
- **6** - Péter Barna

#### Group B
- **14** - Lamine Yamal
- **16** - Martin Ødegaard
- **5** - Péter Nagy
- **7** - Tibor Lénárt

---

## 1️⃣ GROUP STAGE - Match Result Recording

### Group A - Round 1 (Example)

**UI Shows:**
```
✅ Step 2: Record Match Results

ℹ️ Recording Match Results
You are entering the results for THIS MATCH ONLY.
The overall tournament ranking will be calculated automatically based on ALL match results.

Record Final Positions (Match Result)
Select the position each player finished in this match (1st - 4th)

Kylian Mbappé     Position: [1st ▼]   💎 3.0 pts
Cole Palmer       Position: [2nd ▼]   💎 2.0 pts
Tamás Juhász      Position: [3rd ▼]   💎 1.0 pts
Péter Barna       Position: [4th ▼]   💎 0 pts

📊 Points to be Awarded (This Match Only)
#1 Kylian Mbappé   3 pts
#2 Cole Palmer     2 pts
#3 Tamás Juhász    1 pts
#4 Péter Barna     0 pts

Total points awarded: 6.0 pts
```

**User Submits:**
```json
{
  "results": [
    {"user_id": 13, "placement": 1},
    {"user_id": 15, "placement": 2},
    {"user_id": 4, "placement": 3},
    {"user_id": 6, "placement": 4}
  ]
}
```

**Backend Processing:**

1. **Validate:** Match participants match (✅ 4 players expected)
2. **Derive Rankings:** placement → rank (1→1st, 2→2nd, 3→3rd, 4→4th)
3. **Calculate Points:**
   - user_id 13: rank 1 → +3 pts
   - user_id 15: rank 2 → +2 pts
   - user_id 4: rank 3 → +1 pts
   - user_id 6: rank 4 → +0 pts

4. **Update tournament_rankings Table:**
   ```sql
   INSERT INTO tournament_rankings (tournament_id, user_id, total_points, matches_played)
   VALUES
     (14, 13, 3.0, 1),  -- Kylian
     (14, 15, 2.0, 1),  -- Cole
     (14, 4, 1.0, 1),   -- Tamás
     (14, 6, 0.0, 1);   -- Péter Barna
   ```

5. **Store Raw Match Result:**
   ```json
   {
     "match_format": "INDIVIDUAL_RANKING",
     "submitted_at": "2026-01-22T20:00:00",
     "raw_results": [
       {"user_id": 13, "placement": 1},
       {"user_id": 15, "placement": 2},
       {"user_id": 4, "placement": 3},
       {"user_id": 6, "placement": 4}
     ],
     "derived_rankings": [
       {"user_id": 13, "rank": 1},
       {"user_id": 15, "rank": 2},
       {"user_id": 4, "rank": 3},
       {"user_id": 6, "rank": 4}
     ],
     "points_awarded": {
       "13": 3.0,
       "15": 2.0,
       "4": 1.0,
       "6": 0.0
     }
   }
   ```

---

### After 3 Rounds in Group A (Cumulative)

**Tournament Rankings (Derived by Backend):**

| Rank | Player | Total Points | Matches |
|------|--------|-------------|---------|
| 1st  | Kylian Mbappé (13) | 9.0 | 3 |
| 2nd  | Cole Palmer (15) | 6.0 | 3 |
| 3rd  | Tamás Juhász (4) | 3.0 | 3 |
| 4th  | Péter Barna (6) | 0.0 | 3 |

**Key Point:** User NEVER set this ranking! Backend aggregated from 3 match results.

---

## 2️⃣ KNOCKOUT STAGE - Prerequisite Validation

### Knockout Session (Session ID 53)

**Database State:**
```sql
SELECT id, title, participant_user_ids
FROM sessions
WHERE id = 53;

-- Result:
-- id: 53
-- title: "Round of 4 - Match 1"
-- participant_user_ids: NULL  ⚠️
```

**When Instructor Opens This Match:**

**API Response:**
```json
{
  "active_match": null,
  "message": "Match participants not yet determined. Prerequisites not met.",
  "prerequisite_status": {
    "ready": false,
    "reason": "Knockout matches require group stage results to determine qualified participants.",
    "action_required": "Complete all group stage matches first."
  }
}
```

**UI Shows:**
```
⚠️ Cannot Start This Match
Knockout matches require group stage results to determine qualified participants.
Action Required: Complete all group stage matches first.

This knockout match requires completed group stage results to determine qualified participants.
```

**Match BLOCKED until:**
1. All Group A matches completed (3/3 ✅)
2. All Group B matches completed (3/3 ✅)
3. Backend runs `knockout_participant_resolver` service
4. Top 2 from each group assigned to knockout sessions

---

## 3️⃣ KNOCKOUT PARTICIPANT RESOLUTION (Future Service)

### After All Group Matches Complete

**Backend Service Runs:**
```python
# knockout_participant_resolver.py

# Get Group A top 2
group_a_top2 = db.query(TournamentRanking).filter(
    TournamentRanking.tournament_id == 14,
    TournamentRanking.user_id.in_([13, 15, 4, 6])  # Group A
).order_by(TournamentRanking.total_points.desc()).limit(2).all()

# Result: [13 (Kylian), 15 (Cole)]

# Get Group B top 2
group_b_top2 = db.query(TournamentRanking).filter(
    TournamentRanking.tournament_id == 14,
    TournamentRanking.user_id.in_([14, 16, 5, 7])  # Group B
).order_by(TournamentRanking.total_points.desc()).limit(2).all()

# Result: [14 (Lamine), 7 (Tibor)] (example)

# Update Semi-Final 1: Group A 1st vs Group B 2nd
db.execute(
    text("UPDATE sessions SET participant_user_ids = :ids WHERE id = 53"),
    {"ids": [13, 7]}  # Kylian vs Tibor
)

# Update Semi-Final 2: Group B 1st vs Group A 2nd
db.execute(
    text("UPDATE sessions SET participant_user_ids = :ids WHERE id = 54"),
    {"ids": [14, 15]}  # Lamine vs Cole
)
```

**Now Knockout Matches Can Start!**

---

## 4️⃣ FINAL STANDINGS (After All Matches)

**Tournament Leaderboard (Derived Automatically):**

| Final Rank | Player | Total Points | Group | Knockout |
|------------|--------|-------------|-------|----------|
| 🥇 1st | Tibor (7) | 15.0 | Group B 1st | Won Final |
| 🥈 2nd | Kylian (13) | 12.0 | Group A 1st | Lost Final |
| 🥉 3rd | Lamine (14) | 10.0 | Group B 2nd | Won 3rd Place |
| 4th | Cole (15) | 8.0 | Group A 2nd | Lost 3rd Place |

---

## 🔑 Key Architectural Points

### ✅ USER RECORDS (Match-Scoped)
- Final positions in THIS match (1st-4th)
- Match notes (optional)
- **SCOPE:** Only match participants (NOT tournament-wide)

### ❌ USER DOES NOT RECORD
- Tournament rankings (backend aggregates)
- Points (backend calculates)
- Who qualifies for knockout (backend determines)
- Bracket advancement (backend logic)

### 🤖 BACKEND DERIVES
1. **Rankings:** From match results (placement → rank)
2. **Points:** Formula + multipliers
3. **Cumulative Standings:** Aggregation across all matches
4. **Qualification:** Top N from groups
5. **Bracket Logic:** Pairing rules

---

## 📊 Database Flow

### Match Result Storage
```sql
-- sessions.game_results (JSONB)
{
  "match_format": "INDIVIDUAL_RANKING",
  "raw_results": [...],           -- What user submitted
  "derived_rankings": [...],      -- Backend calculated
  "points_awarded": {...}         -- Backend calculated
}
```

### Tournament Rankings (Cumulative)
```sql
-- tournament_rankings table
tournament_id | user_id | total_points | matches_played
-------------|---------|--------------|---------------
14           | 13      | 12.0         | 5
14           | 15      | 8.0          | 5
14           | 14      | 10.0         | 5
14           | 7       | 15.0         | 5
```

---

## 🎯 UI Text Templates

### Info Box
```
ℹ️ Recording Match Results
You are entering the results for THIS MATCH ONLY.
The overall tournament ranking will be calculated automatically based on ALL match results.
```

### Form Title
```
Record Final Positions (Match Result)
Select the position each player finished in this match (1st - Nth)
```

### Validation
```
⚠️ Please record final positions for all N present players in THIS match
```

### Points Preview
```
📊 Points to be Awarded (This Match Only)
```

### Prerequisite Block
```
⚠️ Cannot Start This Match
Knockout matches require group stage results to determine qualified participants.
Action Required: Complete all group stage matches first.
```

---

## ✅ Conclusion

**The system is architecturally correct:**
- Match results = match-scoped input
- Tournament rankings = derived aggregation
- UI = match result entry ONLY
- Backend = all calculations and logic

**No manual ranking, no tournament-wide scope, no user-controlled points.**
