# Sandbox Skill Progression Validation Plan

**Created:** 2026-02-08 22:00
**Priority:** IMMEDIATE
**Owner:** QA Team
**Deadline:** TBD (to be set by team lead)

---

## Objective

Validate that skill points change correctly based on tournament results across different scenarios using the Tournament Sandbox testing environment.

---

## Scope

### 1️⃣ Tournament Scenarios to Test

| Scenario ID | Tournament Type | Description | Expected Skill Impact |
|-------------|-----------------|-------------|----------------------|
| S1 | League | Full season, all players participate | Winners gain skills, losers lose skills |
| S2 | Knockout | Single elimination | High variance based on bracket position |
| S3 | Hybrid | Group stage → Knockout | Gradual skill changes in groups, sharp in knockout |
| S4 | Individual Ranking | 7 players, head-to-head | Linear skill progression based on final rank |
| S5 | Group Stage Only | No knockout phase | Lower skill volatility |

### 2️⃣ Player Profiles to Test

| Profile Type | Description | Test Purpose |
|--------------|-------------|--------------|
| Star Player | High initial skills | Verify top-tier skill ceiling behavior |
| Average Player | Mid-range skills | Standard skill progression |
| Beginner | Low initial skills | Floor behavior & rapid improvement potential |
| Mixed Group | Star + Average + Beginner | Relative skill changes validation |

### 3️⃣ Skill Metrics to Track

**Per Player, Per Tournament:**
- Initial skill values (all 29 skills)
- Final skill values (all 29 skills)
- Skill delta (Δ = Final - Initial)
- XP gained/lost
- Level changes
- Tournament placement (1st, 2nd, 3rd, etc.)

---

## Test Execution Protocol

### Phase 1: Environment Setup (15 min)
1. Verify sandbox environment is running
2. Seed database with test players:
   - 3× Star players (skill avg: 80-90)
   - 4× Average players (skill avg: 50-60)
   - 3× Beginner players (skill avg: 20-30)
3. Record initial skill baselines

### Phase 2: Iterative Tournament Runs (2 hours)

**For each scenario (S1-S5):**

1. **Pre-Tournament:**
   - Export player skills to CSV: `sandbox_S{id}_pre.csv`
   - Document tournament configuration (type, player count, format)

2. **Execute Tournament:**
   - Run full tournament simulation via sandbox UI
   - Record match results
   - Capture tournament winner & podium

3. **Post-Tournament:**
   - Export player skills to CSV: `sandbox_S{id}_post.csv`
   - Calculate skill deltas
   - Record XP & level changes

4. **Data Collection:**
   ```
   Tournament: S{id}
   Players: [list]
   Winner: {name} (Initial Skills: X, Final Skills: Y, Δ: Z)
   2nd Place: {name} (Initial Skills: X, Final Skills: Y, Δ: Z)
   ...
   Last Place: {name} (Initial Skills: X, Final Skills: Y, Δ: Z)
   ```

### Phase 3: Validation Analysis (30 min)

**Expected Business Logic:**
1. ✅ Winner gains skills (positive Δ)
2. ✅ Losers lose skills (negative Δ)
3. ✅ Skill delta magnitude correlates with placement
4. ✅ Star players hit skill ceiling (max ~95-100)
5. ✅ Beginners hit skill floor (min ~10-15)
6. ✅ XP gain/loss follows tournament performance

**Validation Checks:**
- [ ] Top 3 players have positive skill deltas
- [ ] Bottom 3 players have negative skill deltas
- [ ] Winner has largest positive delta
- [ ] Last place has largest negative delta
- [ ] No skill exceeds maximum threshold (100)
- [ ] No skill drops below minimum threshold (10)
- [ ] XP changes align with skill changes

---

## Deliverables

### 1. Raw Data Files
Location: `tests/sandbox_validation/results/`

```
sandbox_S1_league_pre.csv
sandbox_S1_league_post.csv
sandbox_S1_league_summary.md

sandbox_S2_knockout_pre.csv
sandbox_S2_knockout_post.csv
sandbox_S2_knockout_summary.md

... (repeat for S3-S5)
```

### 2. Consolidated Report
File: `SANDBOX_VALIDATION_REPORT.md`

**Contents:**
- Executive summary (Pass/Fail for each scenario)
- Skill progression charts (delta visualization)
- Business logic violations (if any)
- Edge cases discovered
- Recommendations

### 3. Test Execution Log
File: `sandbox_validation_log.txt`

**Format:**
```
[2026-02-08 22:05] S1 - Pre-tournament baseline captured
[2026-02-08 22:10] S1 - Tournament execution started
[2026-02-08 22:25] S1 - Tournament completed, Winner: Player_A
[2026-02-08 22:27] S1 - Post-tournament skills captured
[2026-02-08 22:30] S1 - Validation: PASS
...
```

---

## Roles & Responsibilities

| Role | Responsibility | Owner |
|------|---------------|-------|
| **Test Executor** | Run sandbox tournaments, capture data | QA Engineer |
| **Data Analyst** | Calculate deltas, generate charts | QA Lead |
| **Validator** | Verify business logic compliance | Product Owner |
| **Documenter** | Compile final report | Tech Writer |

---

## Timeline

**Proposed Schedule:**
- **Setup:** Day 1, Morning (2 hours)
- **Execution:** Day 1-2 (4 hours total, can be split)
- **Analysis:** Day 2, Afternoon (2 hours)
- **Report:** Day 3, Morning (1 hour)

**Total Effort:** ~9 hours across 3 days

---

## Success Criteria

**PASS Conditions:**
1. ✅ All 5 scenarios execute without errors
2. ✅ Skill deltas follow expected patterns (winner +, loser -)
3. ✅ No business logic violations detected
4. ✅ Edge cases (ceiling/floor) behave correctly

**FAIL Conditions:**
1. ❌ Winner loses skills (logic inversion)
2. ❌ Skills exceed bounds (>100 or <10)
3. ❌ XP changes inconsistent with skills
4. ❌ Sandbox environment crashes/hangs

---

## Escalation Path

**If validation fails:**
1. Document specific failure case (scenario, players, results)
2. Create P0 bug ticket with reproduction steps
3. Escalate to backend dev team (skill calculation logic)
4. Block release until fix & re-validation

---

## Commands Reference

### Start Sandbox Environment
```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system
source venv/bin/activate
streamlit run streamlit_sandbox.py --server.port 8502 --server.headless false
```

### Export Player Skills (SQL)
```sql
-- Pre-tournament baseline
COPY (
  SELECT u.id, u.email, u.name,
         ps.passing, ps.dribbling, ps.shooting, ps.defending, ps.physical, ps.pace
         -- ... (all 29 skills)
  FROM users u
  JOIN player_skills ps ON u.id = ps.user_id
  WHERE u.id IN (1, 2, 3, ...)  -- test player IDs
) TO '/tmp/sandbox_S1_pre.csv' CSV HEADER;
```

### Calculate Skill Deltas (Python)
```python
import pandas as pd

pre = pd.read_csv('sandbox_S1_pre.csv')
post = pd.read_csv('sandbox_S1_post.csv')

delta = post.set_index('id') - pre.set_index('id')
delta.to_csv('sandbox_S1_delta.csv')
```

---

## Notes

- Sandbox tests are **isolated from production** - no impact on live users
- Use **test database** (`lfa_intern_system_test`) for sandbox runs
- Reset player skills between scenarios to ensure independence
- Document any unexpected behaviors immediately

---

**Status:** PENDING TEAM ASSIGNMENT
**Next Action:** Set deadline & assign QA engineer
