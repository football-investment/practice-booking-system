# Implementation Plan: Option A - Performance Card

**Date:** 2026-02-09
**Status:** APPROVED FOR IMPLEMENTATION
**Scope:** Tournament Achievements UI - Status-First Design
**Timeline:** 1-2 days development + 1 day testing

---

## 🎯 OBJECTIVE

Transform Tournament Achievements from **information log** → **performance showcase**

**Current State:** User sees raw data (Rank: #1, Points: 100)
**Target State:** User feels accomplished ("🔥 TOP 2% CHAMPION")

---

## 📋 FINAL METRIC LIST (Performance Card)

### Tier 1: Hero Status Block (Always Visible)

| UI Element | Data Source | Computation | Display Format |
|-----------|-------------|-------------|----------------|
| **Placement Badge** | `badge.badge_type` | Direct | "🥇 CHAMPION" (48px, gold gradient) |
| **Rank Context** | `badge_metadata.placement` + `badge_metadata.total_participants` | Direct | "#1 of 64 players" (16px, gray) |
| **Percentile Badge** | Computed | `(rank / total) * 100` | "🔥 TOP 2%" (24px, gradient based on tier) |

**Percentile Tier Logic:**
```python
if percentile <= 5:   → "🔥 TOP 5%"  (gold gradient)
elif percentile <= 10: → "⚡ TOP 10%" (orange gradient)
elif percentile <= 25: → "🎯 TOP 25%" (blue gradient)
else:                  → "📊 TOP 50%" (gray gradient)
```

### Tier 2: Performance Triptych (3-Column Compact)

| Metric | Data Source | Fallback Chain | Display Format |
|--------|-------------|----------------|----------------|
| **Points** | `tournament_rankings.points` | `participation.xp_awarded / 10` | "💯 100 pts" |
| **Points Context** | Computed from all rankings | Tournament average | "(Avg: 62)" gray subtitle |
| **Goals** | `tournament_rankings.goals_for` | Hide if NULL | "⚽ 12 goals" |
| **Record** | `tournament_rankings.wins/draws/losses` | Hide if all NULL | "🎯 5-0-1" (W-D-L) |

**Points Context Computation:**
```python
avg_points = AVG(tournament_rankings.points WHERE tournament_id = X)
delta = user_points - avg_points

if delta > 20:        display = f"(Dominant +{delta})"
elif delta > 0:       display = f"(Above avg +{delta})"
elif delta == 0:      display = "(Average)"
else:                 display = ""  # Don't show negative
```

### Tier 3: Rewards Line (Compact, Single Row)

| Metric | Data Source | Fallback | Display Format |
|--------|-------------|----------|----------------|
| **XP Earned** | `participation.xp_awarded` | `0` | "+599 XP" |
| **Credits Earned** | `participation.credits_awarded` | `0` | "+100 💎" |
| **Badges Count** | Count of badges for this tournament | `0` | "3 badges" |

### Tier 4: Badge Carousel (Collapsed by Default)

| Element | Data Source | Display Logic |
|---------|-------------|--------------|
| **Badge Icons** | `badge.icon` | Show first 3 icons in row |
| **Expand Button** | Count | "[+Show X badges]" if count > 3 |

---

## 🗂️ DATA SOURCE → UI MAPPING

### Primary Data Sources (In Order of Priority)

#### Source 1: Badge Metadata (Immutable Snapshot)
```python
# FROM: tournament_badges.badge_metadata (JSONB)
badge_metadata = {
    "placement": 1,              # → Rank Context
    "total_participants": 64     # → Rank Context + Percentile
}
```
**Usage:** Hero status block (placement, tournament size, percentile)
**Reliability:** ✅ Always present (set at badge creation)

#### Source 2: Tournament Rankings (Current State)
```python
# FROM: tournament_rankings (LEFT JOIN)
ranking = {
    "rank": 1,                   # → Hero status (if available)
    "points": 100.00,            # → Performance Triptych
    "wins": 5,                   # → Record
    "draws": 0,                  # → Record
    "losses": 1,                 # → Record
    "goals_for": 12,             # → Goals
    "goals_against": 4           # → Goal difference (future)
}
```
**Usage:** Performance metrics (points, record, goals)
**Reliability:** ⚠️ May be NULL (2.2% of badges have missing rankings)

#### Source 3: Tournament Participations (Rewards)
```python
# FROM: tournament_participations (LEFT JOIN)
participation = {
    "placement": 1,              # → Fallback for rank if rankings missing
    "xp_awarded": 599,           # → Rewards line
    "credits_awarded": 100,      # → Rewards line
    "skill_points_awarded": {}   # → Future: skill breakdown
}
```
**Usage:** Rewards display + fallback rank
**Reliability:** ✅ High (present for all badges with rewards)

#### Source 4: Badge Collection (Visual)
```python
# FROM: tournament_badges (filtered by semester_id)
badges = [
    {"icon": "🥇", "title": "Champion", ...},
    {"icon": "🏆", "title": "Podium Finish", ...},
    {"icon": "⚽", "title": "Participant", ...}
]
```
**Usage:** Badge carousel
**Reliability:** ✅ Always present

### API Endpoint Requirements

**Existing Endpoint (Modified):**
```
GET /api/v1/tournaments/badges/user/{user_id}
```

**Required Response Fields (Already Implemented):**
```json
{
  "badges": [
    {
      "id": 1459,
      "semester_id": 1543,
      "semester_name": "SANDBOX-TEST-LEAGUE-2026-02-09",  // ✅ Added
      "tournament_status": "REWARDS_DISTRIBUTED",          // ✅ Added
      "tournament_start_date": "2026-02-09",               // ✅ Added
      "badge_type": "CHAMPION",
      "badge_metadata": {
        "placement": 1,
        "total_participants": 6
      },
      "icon": "🥇",
      "title": "Tournament Champion"
    }
  ]
}
```

**New Endpoint Required:**
```
GET /api/v1/tournaments/{tournament_id}/performance/{user_id}
```

**Response Schema:**
```json
{
  "tournament_id": 1543,
  "user_id": 4,
  "performance": {
    "rank": 1,
    "points": 100.00,
    "wins": 5,
    "draws": 0,
    "losses": 1,
    "goals_for": 12,
    "goals_against": 4
  },
  "context": {
    "total_participants": 6,
    "avg_points": 62.00,
    "max_points": 100.00,
    "percentile": 2.0
  },
  "rewards": {
    "xp_awarded": 599,
    "credits_awarded": 100,
    "badges_earned": 3
  }
}
```

**Implementation Note:** This endpoint consolidates 2 existing API calls:
- `GET /tournaments/{id}/rankings` (performance stats)
- `GET /tournaments/{id}/rewards/{user_id}` (rewards data)

---

## 🔒 DATA CONSISTENCY RULES (Read-Only Fallback)

### Rule 1: Rank Display Fallback Chain

**Priority Order:**
```python
1. tournament_rankings.rank         (current, may change)
2. badge_metadata.placement         (immutable snapshot)
3. tournament_participations.placement  (rewards table)
4. NULL → Hide rank metric (don't show N/A)
```

**Implementation:**
```python
def get_display_rank(badge, ranking, participation):
    # Try ranking first (most current)
    if ranking and ranking.get('rank'):
        return ranking['rank'], 'current'

    # Fallback to badge metadata (snapshot)
    if badge.get('badge_metadata', {}).get('placement'):
        return badge['badge_metadata']['placement'], 'snapshot'

    # Last resort: participation table
    if participation and participation.get('placement'):
        return participation['placement'], 'participation'

    # No rank data available
    return None, None

# Usage:
rank, source = get_display_rank(badge, ranking, participation)
if rank:
    display_rank = f"#{rank}"
    if source == 'snapshot':
        logger.warning(f"Badge {badge['id']}: Using snapshot rank (current ranking missing)")
else:
    # Don't display rank metric at all (not "N/A")
    display_rank = None
```

### Rule 2: Tournament Size (Always Required)

**Validation:**
```python
total_participants = badge.get('badge_metadata', {}).get('total_participants')

if not total_participants:
    # CRITICAL: Cannot display percentile without tournament size
    logger.error(f"Badge {badge['id']}: Missing total_participants")
    # Fallback: Query tournament_rankings count
    total_participants = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == badge['semester_id']
    ).count()

    if not total_participants:
        # Last resort: Don't show percentile badge
        show_percentile = False
```

### Rule 3: Performance Stats (Graceful Degradation)

**Display Logic:**
```python
# Points: Always try to show (most important)
if ranking.points:
    show_points = True
    show_context = True if tournament_avg_points else False
else:
    show_points = False

# Goals: Hide if NULL (optional metric)
if ranking.goals_for is not None:
    show_goals = True
else:
    show_goals = False

# Record: Hide if all NULL (optional metric)
if any([ranking.wins, ranking.draws, ranking.losses]):
    show_record = True
    record_str = f"{ranking.wins or 0}-{ranking.draws or 0}-{ranking.losses or 0}"
else:
    show_record = False
```

### Rule 4: Silent Logging (No User-Facing Errors)

**Logging Strategy:**
```python
# Log inconsistencies for monitoring, but never show error to user
if ranking.rank and badge_metadata.placement:
    if ranking.rank != badge_metadata.placement:
        logger.warning(
            f"Rank mismatch: Badge {badge_id} | "
            f"Current rank={ranking.rank} | Snapshot placement={badge_metadata.placement}"
        )
        # Use snapshot (immutable) for display
        display_rank = badge_metadata.placement
```

---

## ✅ ACCEPTANCE CRITERIA

### Functional Requirements

#### AC-1: Hero Status Display
- [ ] Badge icon displays at 48px size with gradient background
- [ ] Placement badge type shows correct text (CHAMPION → "🥇 CHAMPION")
- [ ] Rank context shows format: "#X of Y players" (X = rank, Y = total)
- [ ] Percentile badge displays with correct tier icon and color
- [ ] Percentile calculation accurate: (rank / total) * 100

#### AC-2: Rank Consistency Rule
- [ ] **CRITICAL:** Champion badge NEVER displays with "Rank: N/A"
- [ ] If `ranking.rank` is NULL, fallback to `badge_metadata.placement`
- [ ] If `badge_metadata.placement` is NULL, fallback to `participation.placement`
- [ ] If all sources NULL, hide rank display entirely (don't show N/A)
- [ ] Rank mismatch logged (silent warning) but user sees snapshot placement

#### AC-3: Performance Triptych
- [ ] Points display with tournament average context if available
- [ ] Performance vs average shows "+X" for above, hides for below
- [ ] Goals display only if `goals_for` is not NULL
- [ ] Record display in "W-D-L" format only if at least one stat present
- [ ] All 3 metrics fit in single row (no wrapping) on desktop

#### AC-4: Rewards Line
- [ ] XP, Credits, Badge count display in compact single row
- [ ] Format: "+599 XP • +100 💎 • 3 badges"
- [ ] All rewards fit without wrapping

#### AC-5: Data Integrity
- [ ] No "N/A" text visible anywhere in performance card
- [ ] No empty metrics (hide metric entirely if data unavailable)
- [ ] No placeholder text ("Loading...", "---", "N/A")
- [ ] Graceful degradation: Missing data = hidden metric, not error state

### Non-Functional Requirements

#### AC-6: Performance
- [ ] Performance card renders in < 200ms (no additional API calls)
- [ ] Percentile computation < 5ms
- [ ] Tournament average computation cached per tournament
- [ ] No visible layout shift during render

#### AC-7: Visual Consistency
- [ ] Gradient colors match percentile tier (gold, orange, blue, gray)
- [ ] Icon sizes consistent across all cards
- [ ] Spacing follows 8px grid system
- [ ] Mobile responsive (stacks to single column on < 768px)

#### AC-8: Backwards Compatibility
- [ ] Works with existing 91 badges (no migration needed)
- [ ] Works with badges missing tournament_rankings (2.2% of badges)
- [ ] Works with sandbox test tournaments (total_participants = 6 or 8)
- [ ] Works with production tournaments (total_participants up to 64)

### Edge Case Requirements

#### AC-9: Edge Cases Handled
- [ ] Badge with no ranking data → Uses snapshot placement
- [ ] Tournament with 1 participant → Percentile = 100% (don't show "TOP 100%")
- [ ] Points = 0 → Display "0 pts" (not hide)
- [ ] Wins/Losses all 0 → Hide record metric
- [ ] Very long tournament name → Truncate with ellipsis at 50 chars
- [ ] Multiple badges same tournament → Performance card shows once (not per badge)

### Testing Requirements

#### AC-10: Test Coverage
- [ ] Unit test: Percentile calculation (edge cases: 1/1, 1/64, 32/64)
- [ ] Unit test: Rank fallback chain (3 scenarios)
- [ ] Unit test: Performance metric display logic (all combinations of NULL)
- [ ] Integration test: Render with real badge data (user_id=4, 91 badges)
- [ ] Visual test: Screenshot comparison (before/after)
- [ ] User test: 3-5 users confirm "easier to understand" vs current

---

## 🛠️ IMPLEMENTATION APPROACH

### Phase 1: Backend API Consolidation (4 hours)

**Task 1.1:** Create `/api/v1/tournaments/{id}/performance/{user_id}` endpoint
- Consolidate rankings + rewards in single response
- Include computed context (avg_points, percentile)
- Cache response (5 min TTL)

**Task 1.2:** Add fallback logic to existing badge endpoint
- Modify `TournamentBadge.to_dict()` to include computed percentile
- Add `display_rank` field using fallback chain
- Ensure backwards compatibility

### Phase 2: Frontend Component (6 hours)

**Task 2.1:** Create `render_performance_card()` function
- Replace metrics section in `render_tournament_accordion_item()`
- Implement hero status block HTML
- Implement performance triptych HTML
- Implement rewards line HTML

**Task 2.2:** Add percentile computation + tier logic
- Compute percentile from rank + total_participants
- Assign tier icon and gradient color
- Handle edge cases (1 participant, missing data)

**Task 2.3:** Implement rank fallback chain
- Check `ranking.rank` → `badge_metadata.placement` → `participation.placement`
- Add silent warning logging
- Hide rank if all sources NULL

### Phase 3: Testing + Refinement (4 hours)

**Task 3.1:** Unit tests
- Percentile calculation
- Rank fallback logic
- Metric display logic

**Task 3.2:** Visual testing
- Desktop render (1920x1080)
- Mobile render (375x667)
- Tablet render (768x1024)

**Task 3.3:** User acceptance testing
- Test with 3-5 internal users
- Collect feedback on clarity vs current design
- Iterate on visual hierarchy if needed

---

## 📊 SUCCESS METRICS

### Quantitative (Measured via Analytics)

| Metric | Current Baseline | Target | Measurement |
|--------|-----------------|--------|-------------|
| **Scan Time** | 8-10 sec | 2-3 sec | Eye tracking / user study |
| **Engagement** | Baseline | +15-25% | Time spent on achievements tab |
| **Return Rate** | Baseline | +10-15% | Users checking achievements weekly |

### Qualitative (Measured via User Feedback)

| Question | Target Response |
|----------|----------------|
| "Do you understand your performance at a glance?" | 80%+ "Yes" |
| "Does this feel like an accomplishment showcase?" | 80%+ "Yes" |
| "Is this clearer than the previous design?" | 80%+ "Yes" |

---

## 🚫 OUT OF SCOPE (Option B - Future Roadmap)

**NOT included in this implementation:**
- Career timeline view (Option B)
- Historical progression tracking ("📈 Improved from last month")
- Skill points breakdown display
- Goal difference computation
- Head-to-head comparisons
- Tournament tier classification (8-player vs 64-player)

**Rationale:** Option A focuses on **status-first single tournament view**. Option B (career view) is long-term engagement feature for separate implementation.

---

## ⚠️ RISKS & MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Performance degradation** (additional API call) | Low | Medium | Cache computed context, lazy load |
| **User confusion** (too much data) | Medium | High | User testing before rollout, A/B test |
| **Percentile miscalculation** (edge cases) | Low | Medium | Comprehensive unit tests, validation |
| **Rank mismatch visible to user** | Low | High | Fallback chain + silent logging |

---

## 🎯 DEFINITION OF DONE

**Implementation Complete When:**
- [ ] All 10 acceptance criteria validated (AC-1 through AC-10)
- [ ] Backend endpoint deployed to staging
- [ ] Frontend component merged to main branch
- [ ] Unit tests passing (>= 90% coverage on new code)
- [ ] Visual regression tests passing
- [ ] User acceptance testing complete (3-5 users, 80%+ positive)
- [ ] Documentation updated (this plan + API docs)
- [ ] Deployed to production
- [ ] Monitoring dashboard shows no errors for 24 hours

**Sign-Off Required From:**
- [ ] Product Owner (design approval)
- [ ] Tech Lead (code review)
- [ ] QA (test coverage + edge cases)
- [ ] User Representative (UX validation)

---

## 📞 NEXT STEPS

1. **Stakeholder Review** (Today)
   - Review this implementation plan
   - Approve metric list + acceptance criteria
   - Sign-off to proceed

2. **Development Kickoff** (Next Day)
   - Assign backend + frontend tasks
   - Set up feature branch
   - Create Jira tickets

3. **Implementation** (2 days)
   - Backend API consolidation
   - Frontend component development
   - Unit + integration tests

4. **Testing** (1 day)
   - User acceptance testing
   - Visual regression testing
   - Performance validation

5. **Deployment** (Same day as testing)
   - Deploy to staging
   - Final review
   - Deploy to production

**Total Timeline:** 3-4 days (2 dev + 1 test + 0.5 deploy)

---

**Status:** ✅ READY FOR STAKEHOLDER APPROVAL

**Prepared by:** Claude Sonnet 4.5 (Product Planning)
**Date:** 2026-02-09
**Next Action:** Stakeholder sign-off required to proceed with implementation
