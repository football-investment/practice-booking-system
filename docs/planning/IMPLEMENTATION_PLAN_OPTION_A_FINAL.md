# Implementation Plan: Option A - Performance Card (FINAL APPROVED)

**Date:** 2026-02-09
**Status:** ✅ APPROVED - Ready for Implementation
**Timeline:** 3-4 days (17 hours total)

---

## ✅ STAKEHOLDER APPROVALS

**Product Owner:** ✅ Approved with 3 mandatory modifications
**Tech Review:** ✅ Backend minimalism validated (no new endpoint)
**Data Strategy:** ✅ Single source of truth defined (tournament_rankings)
**Architecture:** ✅ Reusability strategy approved

---

## 🎯 OBJECTIVE

Transform Tournament Achievements from **information log** → **performance showcase**

**User Experience Goal:**
- Before: "I was #1" (neutral information)
- After: "I DOMINATED 🔥 TOP 2% of 64 players" (status + accomplishment)

---

## 📋 APPROVED MODIFICATIONS

### ✅ Modification 1: Backend Minimalism

**Decision:** NO new API endpoint

**Justification:** [TECHNICAL_JUSTIFICATION_BACKEND.md](TECHNICAL_JUSTIFICATION_BACKEND.md)
- 2 extra queries per tournament (≤2 rule satisfied)
- Existing endpoints sufficient (rankings + rewards)
- Frontend caching handles performance
- Zero deployment risk

**Implementation:**
- Use existing `GET /tournaments/{id}/rankings`
- Use existing `GET /tournaments/{id}/rewards/{user_id}`
- Compute `avg_points` in frontend (< 1ms for 64 players)

### ✅ Modification 2: Data Integrity Fix (PRIORITY)

**Decision:** `tournament_rankings.rank` is single source of truth

**Strategy:** [DATA_INTEGRITY_STRATEGY.md](DATA_INTEGRITY_STRATEGY.md)

**Hierarchy:**
```
1. tournament_rankings.rank         [AUTHORITY - Current Truth]
2. tournament_participations.placement  [FALLBACK - Rewards Snapshot]
3. badge_metadata.placement         [DISPLAY ONLY - Creation Snapshot]
```

**Implementation:**
1. Badge creation uses `ranking.rank` (not participation.placement)
2. UI fallback chain (ranking → participation → badge_metadata)
3. Quality gate: Raise error if badge awarded without ranking
4. Production safety alert: Champion badge with rank > 3

**Migration:** 2 inconsistent badges (1140, 1160) require investigation

### ✅ Modification 3: Reusability Strategy

**Decision:** Performance Card = Reusable Component (not single-use UI)

**Strategy:** [REUSABILITY_STRATEGY_PERFORMANCE_CARD.md](REUSABILITY_STRATEGY_PERFORMANCE_CARD.md)

**Implementation:**
- Create standalone `performance_card.py` component
- Support 3 size variants (compact, normal, large)
- Context-aware styling (accordion, profile, share)
- Export stub for future PNG generation

**Cost:** +4 hours upfront
**Benefit:** +18 hours saved (future use cases: profile, social share, email digest)

---

## 📊 FINAL METRIC LIST (9 Metrics)

### Tier 1: Hero Status Block (Always Visible)

| UI Element | Data Source | Fallback Chain | Display Format |
|-----------|-------------|----------------|----------------|
| **Placement Badge** | `badge.badge_type` | N/A | "🥇 CHAMPION" (48px, gradient) |
| **Rank Context** | `ranking.rank` + `badge_metadata.total_participants` | `participation.placement` → `badge_metadata.placement` → Hide | "#1 of 64 players" (16px) |
| **Percentile Badge** | Computed: `(rank / total) * 100` | N/A | "🔥 TOP 2%" (24px, tier gradient) |

**Percentile Tiers:**
- ≤5%: 🔥 TOP 5% (gold)
- ≤10%: ⚡ TOP 10% (orange)
- ≤25%: 🎯 TOP 25% (blue)
- >25%: 📊 TOP 50% (gray)

### Tier 2: Performance Triptych (3 Columns)

| Metric | Data Source | Fallback | Display Format |
|--------|-------------|----------|----------------|
| **Points** | `ranking.points` | Hide if NULL | "💯 100 pts" |
| **Points Context** | Computed: `AVG(rankings.points)` | Hide if < 2 participants | "(Avg: 62)" gray subtitle |
| **Goals** | `ranking.goals_for` | Hide if NULL | "⚽ 12 goals" |
| **Record** | `ranking.wins/draws/losses` | Hide if all NULL | "🎯 5-0-1 W-D-L" |

### Tier 3: Rewards Line (Compact)

| Metric | Data Source | Fallback | Display Format |
|--------|-------------|----------|----------------|
| **XP + Credits** | `participation.xp_awarded + credits_awarded` | `0` | "+599 XP • +100 💎" |
| **Badge Count** | Count badges for tournament | `0` | "3 badges" |

### Tier 4: Badge Carousel (Collapsed by Default)

| Element | Display Logic |
|---------|--------------|
| Badge Icons | First 3 visible |
| Expand Button | "[+Show X badges]" if count > 3 |

---

## 🗂️ DATA SOURCE MAPPING

### API Calls (No New Endpoints)

**1. Badges (Already Called)**
```
GET /api/v1/tournaments/badges/user/{user_id}

Used For:
- Badge identity (type, icon, title)
- Tournament metadata (semester_name, status, start_date)
- Badge metadata (placement snapshot, total_participants)
```

**2. Rankings (Lazy Load on Accordion Expand)**
```
GET /api/v1/tournaments/{tournament_id}/rankings

Used For:
- Rank (authority source)
- Points, wins, draws, losses, goals_for
- Tournament context (compute avg_points from all rankings)
```

**3. Rewards (Lazy Load on Accordion Expand)**
```
GET /api/v1/tournaments/{tournament_id}/rewards/{user_id}

Used For:
- XP earned
- Credits earned
```

**Total Queries:**
- Initial load: 1 (badges)
- Per accordion expand: 2 (rankings + rewards)

**Caching:**
- Session state caching (frontend)
- 5-min backend cache (existing)

---

## 🔒 DATA CONSISTENCY RULES

### Rule 1: Rank Fallback Chain

```python
def get_display_rank(badge, ranking, participation):
    """
    Get rank for display with authority-based fallback.

    Hierarchy:
    1. ranking.rank (authority - current truth)
    2. participation.placement (fallback - rewards table)
    3. badge_metadata.placement (last resort - snapshot)
    4. None (hide metric)
    """
    # Try ranking first (AUTHORITY)
    if ranking and ranking.get('rank'):
        return ranking['rank'], 'current'

    # Fallback to participation
    if participation and participation.get('placement'):
        logger.warning(f"Badge {badge['id']}: Using participation.placement (ranking missing)")
        return participation['placement'], 'fallback_participation'

    # Last resort: badge metadata
    if badge.get('badge_metadata', {}).get('placement'):
        logger.warning(f"Badge {badge['id']}: Using badge_metadata.placement (ranking + participation missing)")
        return badge['badge_metadata']['placement'], 'snapshot'

    # No rank data
    logger.error(f"Badge {badge['id']}: No rank data from any source")
    return None, None
```

### Rule 2: Production Safety Alert

```python
def validate_placement_consistency(badge, display_rank):
    """
    Alert on suspicious badge-rank combinations (data drift detection).
    """
    if badge['badge_type'] in ['CHAMPION', 'RUNNER_UP', 'THIRD_PLACE']:
        expected = {'CHAMPION': 1, 'RUNNER_UP': 2, 'THIRD_PLACE': 3}[badge['badge_type']]

        if display_rank and display_rank > 3:
            # RED FLAG: Champion badge but rank > 3
            logger.error(
                f"DATA DRIFT DETECTED: Badge {badge['id']} | "
                f"Type={badge['badge_type']} (expects #{expected}) | "
                f"Actual rank={display_rank} | "
                f"User={badge['user_id']} | Tournament={badge['semester_id']}"
            )
            # Trigger ops alert (critical)
            send_ops_alert(
                severity='HIGH',
                message=f"Badge-Ranking inconsistency: Badge {badge['id']}"
            )
```

### Rule 3: Quality Gate (Badge Creation)

**Backend Modification Required (Future):**
```python
def award_placement_badge(user_id, tournament_id):
    """
    Award badge using tournament_rankings as authority source.
    """
    # Get ranking (AUTHORITY)
    ranking = get_tournament_ranking(user_id, tournament_id)
    if not ranking:
        raise ValueError(f"Cannot award badge: No ranking found for user {user_id}")

    placement = ranking.rank  # Use ranking as source of truth

    # Validate participation exists
    participation = get_participation(user_id, tournament_id)
    if not participation:
        raise ValueError(f"Cannot award badge: No participation record found")

    # Quality gate: Warn on inconsistency
    if participation.placement and participation.placement != placement:
        logger.warning(
            f"Placement mismatch: ranking.rank={placement}, "
            f"participation.placement={participation.placement}. Using ranking.rank."
        )

    # Create badge with ranking.rank as source
    badge = create_badge(
        user_id=user_id,
        tournament_id=tournament_id,
        badge_type=get_badge_type(placement),
        badge_metadata={
            "placement": placement,  # From ranking (authority)
            "total_participants": get_total_participants(tournament_id),
            "source": "tournament_rankings"
        }
    )
```

---

## 🏗️ COMPONENT ARCHITECTURE (Reusable)

### File Structure

```
streamlit_app/
├── components/
│   ├── tournaments/
│   │   ├── __init__.py
│   │   ├── performance_card.py          ← NEW: Reusable component
│   │   ├── performance_card_styles.py   ← NEW: Style presets
│   │   ├── tournament_achievement_accordion.py  ← MODIFIED: Use performance_card
│   │   └── tournament_filters.py
```

### Component API

```python
# performance_card.py

from typing import Dict, Any, Literal

CardSize = Literal["compact", "normal", "large"]

def render_performance_card(
    tournament_data: Dict[str, Any],
    size: CardSize = "normal",
    show_badges: bool = True,
    show_rewards: bool = True,
    context: str = "accordion"
) -> None:
    """
    Render tournament performance card.

    Args:
        tournament_data: {
            'tournament_id': int,
            'tournament_name': str,
            'badges': List[Dict],
            'metrics': {
                'rank': int, 'points': float, 'wins': int, 'draws': int, 'losses': int,
                'goals_for': int, 'avg_points': float, 'total_participants': int,
                'xp_earned': int, 'credits_earned': int
            }
        }
        size: "compact" (80px) | "normal" (240px) | "large" (320px)
        show_badges: Whether to render badge carousel
        show_rewards: Whether to render rewards line
        context: "accordion" | "profile" | "share" | "email"
    """
    # Implementation
    pass
```

### Size Variants

| Variant | Height | Use Case |
|---------|--------|----------|
| **Compact** | 80px | Player profile, timeline |
| **Normal** | 240px | Tournament accordion (default) |
| **Large** | 320px | Detail modal, showcase |

---

## ✅ ACCEPTANCE CRITERIA (Final)

### Functional Requirements

#### AC-1: Hero Status Display
- [ ] Badge icon displays at 48px (normal size) with gradient background
- [ ] Rank context: "#X of Y players" format (X=rank, Y=total_participants)
- [ ] Percentile badge shows correct tier (🔥/⚡/🎯/📊) with gradient color
- [ ] Percentile calculation accurate: `(rank / total) * 100`

#### AC-2: Rank Consistency Rule ⚠️ CRITICAL
- [ ] **Champion badge NEVER displays with "Rank: N/A"**
- [ ] Fallback chain implemented: ranking.rank → participation.placement → badge_metadata.placement
- [ ] If all sources NULL → Hide rank metric (don't show N/A)
- [ ] Rank mismatch logged (silent warning) but user sees valid rank from fallback

#### AC-3: Performance Triptych
- [ ] Points display with tournament average context if ≥2 participants
- [ ] Performance delta shows "+X" for above average (hide if below)
- [ ] Goals display only if `goals_for` is not NULL
- [ ] Record displays "W-D-L" format only if at least one stat present
- [ ] All 3 metrics fit in single row (no wrapping) on desktop (≥768px)

#### AC-4: Rewards Line
- [ ] XP, Credits, Badge count display in compact single row
- [ ] Format: "+599 XP • +100 💎 • 3 badges"
- [ ] Fits without wrapping

#### AC-5: Data Integrity
- [ ] **NO "N/A" text anywhere in performance card**
- [ ] Missing data = hidden metric (not error state)
- [ ] No placeholder text ("Loading...", "---")
- [ ] Graceful degradation for all metrics

### Data Integrity Requirements

#### AC-D1: Source of Truth (CRITICAL)
- [ ] `tournament_rankings.rank` used as primary source (authority)
- [ ] Fallback chain implemented correctly (ranking → participation → badge_metadata)
- [ ] Production safety alert triggers on Champion badge with rank > 3
- [ ] All inconsistencies logged (silent warning, no user-facing error)

#### AC-D2: Quality Gate (Future - Not Blocking)
- [ ] Badge creation service modified to use `ranking.rank` as source
- [ ] Badge creation fails if `ranking` is NULL (no silent failures)
- [ ] 2 existing inconsistent badges investigated (migration plan documented)

### Reusability Requirements

#### AC-R1: Component Architecture
- [ ] `performance_card.py` created as standalone component
- [ ] Component can be imported and used in ANY page
- [ ] Not coupled to accordion (works in profile, share, email contexts)

#### AC-R2: Size Variants
- [ ] Compact (80px), Normal (240px), Large (320px) variants implemented
- [ ] Size variants correctly apply styling
- [ ] Responsive: Stacks to single column on mobile (< 768px)

#### AC-R3: Future-Proof
- [ ] Style presets centralized in `performance_card_styles.py`
- [ ] Export stub exists: `export_performance_card_image()` (for future PNG)
- [ ] Component documented in README.md

### Performance Requirements

#### AC-P1: Performance
- [ ] Performance card renders in < 200ms (no additional API calls beyond existing)
- [ ] Percentile computation < 5ms
- [ ] Tournament average computation < 10ms (< 64 players)
- [ ] No visible layout shift during render

### Backwards Compatibility

#### AC-B1: Compatibility
- [ ] Works with 91 existing badges (no DB migration)
- [ ] Works with 2.2% badges missing rankings (uses fallback)
- [ ] Works with sandbox tournaments (6 players) and production (64 players)
- [ ] Existing accordion functionality preserved (expand/collapse, pagination, search)

---

## 🛠️ IMPLEMENTATION PHASES

### Phase 1: Backend Data Integrity Fix (4 hours)

**Tasks:**
- [ ] Implement rank fallback chain in `fetch_tournament_metrics()` function
- [ ] Add production safety alert (Champion badge + rank > 3)
- [ ] Add logging for rank source (current, fallback_participation, snapshot)
- [ ] Test fallback chain with 2 inconsistent badges (1140, 1160)

**Deliverables:**
- Modified `tournament_achievement_accordion.py` (fetch function)
- Logging infrastructure for data drift detection
- Test cases for 3-tier fallback

### Phase 2: Reusable Component Creation (6 hours)

**Tasks:**
- [ ] Create `performance_card.py` (standalone component)
- [ ] Create `performance_card_styles.py` (style presets, color palettes)
- [ ] Implement hero status block (badge icon, rank context, percentile)
- [ ] Implement performance triptych (points, goals, record)
- [ ] Implement rewards line (XP, credits, badge count)
- [ ] Implement size variants (compact, normal, large)
- [ ] Add export stub: `export_performance_card_image()`

**Deliverables:**
- `performance_card.py` (250 lines)
- `performance_card_styles.py` (100 lines)
- Component README.md

### Phase 3: Accordion Integration (3 hours)

**Tasks:**
- [ ] Refactor `render_tournament_accordion_item()` to use `render_performance_card()`
- [ ] Remove hardcoded metrics section (replace with component call)
- [ ] Test with 91 existing badges (user_id=4)
- [ ] Test responsive layout (desktop, tablet, mobile)
- [ ] Test expand/collapse behavior

**Deliverables:**
- Modified `tournament_achievement_accordion.py` (refactored)
- Visual regression tests (before/after screenshots)

### Phase 4: Testing & Validation (4 hours)

**Tasks:**
- [ ] Unit tests: Percentile calculation (edge cases: 1/1, 1/64, 32/64)
- [ ] Unit tests: Rank fallback chain (3 scenarios + NULL handling)
- [ ] Unit tests: Performance metric display logic (all NULL combinations)
- [ ] Integration test: Render with real data (user_id=4, 91 badges)
- [ ] Visual test: Screenshot comparison (before/after)
- [ ] User test: 3-5 internal users (UX feedback)
- [ ] Performance test: Render time < 200ms

**Deliverables:**
- Test suite (pytest)
- Visual regression tests
- User feedback summary (80%+ positive = pass)

---

## 📊 SUCCESS METRICS

### Quantitative

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Scan Time** | 8-10 sec | 2-3 sec | User testing (5 users) |
| **Information Density** | 4 metrics | 9 metrics | UI audit |
| **Screen Space** | 400px height | 320px height | Visual inspection |
| **Data Utilization** | 55% | 85% | Metric count / available fields |

### Qualitative

| Question | Target Response |
|----------|----------------|
| "Do you understand your performance at a glance?" | ≥80% "Yes" |
| "Is this clearer than the previous design?" | ≥80% "Yes" |
| "Does this feel like an accomplishment showcase?" | ≥80% "Yes" |

---

## 🚫 OUT OF SCOPE

**NOT included in this implementation:**

- ❌ Career timeline view (Option B) → Future roadmap
- ❌ Historical progression tracking → Separate feature
- ❌ Skill points breakdown display → Separate feature
- ❌ Goal difference computation → Minor metric, defer
- ❌ PNG export implementation → Stub only (full impl later)
- ❌ Email digest integration → Week 4 (separate sprint)
- ❌ Social share integration → Week 3 (separate sprint)
- ❌ Player profile integration → Week 2 (separate sprint)

**Focus:** Status-first single tournament view in Tournament Achievements accordion

---

## ⚠️ RISKS & MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Performance degradation** (2 API calls) | Low | Medium | Frontend caching (session_state), lazy load |
| **User confusion** (too much data) | Medium | High | User testing before rollout (≥80% clarity) |
| **Percentile miscalculation** (edge cases) | Low | Medium | Comprehensive unit tests (1/1, 1/64, etc.) |
| **Rank mismatch visible** (data drift) | Low | High | Fallback chain + production safety alert |
| **Reusability overhead** (extra dev time) | Low | Low | +4 hours upfront, +18 hours saved later |

---

## 🎯 DEFINITION OF DONE

**Implementation Complete When:**

- [ ] ✅ All 5 functional acceptance criteria validated (AC-1 to AC-5)
- [ ] ✅ Data integrity requirements met (AC-D1)
- [ ] ✅ Reusability requirements met (AC-R1 to AC-R3)
- [ ] ✅ Performance requirements met (AC-P1: < 200ms render)
- [ ] ✅ Backwards compatibility verified (AC-B1: 91 badges tested)
- [ ] ✅ Unit tests passing (≥90% coverage on new code)
- [ ] ✅ Visual regression tests passing (screenshot diff)
- [ ] ✅ User testing complete (3-5 users, ≥80% positive)
- [ ] ✅ Documentation updated (component README, API docs)
- [ ] ✅ Code review approved (Tech Lead)
- [ ] ✅ Deployed to staging
- [ ] ✅ Production deployment
- [ ] ✅ Monitoring dashboard: No errors for 24 hours

**Sign-Off Required From:**
- [ ] Product Owner (UX validation)
- [ ] Tech Lead (code review + architecture)
- [ ] QA (test coverage + edge cases)
- [ ] User Representative (3-5 users tested)

---

## 📅 TIMELINE

| Phase | Duration | Tasks | Deliverables |
|-------|----------|-------|--------------|
| **Phase 1: Data Integrity** | 4 hours | Fallback chain, safety alerts | Modified fetch function |
| **Phase 2: Component** | 6 hours | Create reusable component | `performance_card.py` + styles |
| **Phase 3: Integration** | 3 hours | Refactor accordion | Modified accordion file |
| **Phase 4: Testing** | 4 hours | Unit + integration + user tests | Test suite + feedback |
| **TOTAL** | **17 hours** | | |

**Calendar Timeline:**
- **Day 1 (8h):** Phase 1 (4h) + Phase 2 start (4h)
- **Day 2 (8h):** Phase 2 finish (2h) + Phase 3 (3h) + Phase 4 start (3h)
- **Day 3 (4h):** Phase 4 finish (1h) + Deploy to staging (1h) + User testing (2h)
- **Day 4 (2h):** Production deployment + monitoring

**Total:** 3-4 days (22 hours including deployment)

---

## 📞 NEXT STEPS

**Status:** ✅ APPROVED - Ready for Implementation

**Immediate Actions:**

1. **Create Feature Branch** (Now)
   ```bash
   git checkout -b feature/performance-card-option-a
   ```

2. **Assign Tasks** (Now)
   - Backend data integrity: [Developer A]
   - Component creation: [Developer B]
   - Integration + testing: [Developer A + B]

3. **Kickoff Development** (Day 1)
   - Phase 1: Data integrity fix (4h)
   - Phase 2: Component creation (start 4h)

4. **Daily Standup** (Every morning)
   - Blockers review
   - Progress check vs timeline

5. **User Testing** (Day 3)
   - 3-5 internal users
   - Collect feedback (≥80% positive = pass)

6. **Deployment** (Day 4)
   - Staging deploy → Final review → Production
   - Monitor for 24 hours

---

## 📋 MANDATORY PRE-IMPLEMENTATION CHECKLIST

**Before Starting Development:**

- [x] ✅ Technical justification reviewed (no new endpoint)
- [x] ✅ Data integrity strategy approved (tournament_rankings = authority)
- [x] ✅ Reusability strategy approved (standalone component)
- [x] ✅ Implementation plan reviewed
- [x] ✅ Acceptance criteria understood
- [x] ✅ Timeline realistic (17 hours)
- [x] ✅ Stakeholder approval received

**All checks passed → GO for implementation**

---

**Status:** ✅ FINAL PLAN APPROVED
**Blockers:** None
**Dependencies:** None
**Ready:** ✅ Development can start immediately

---

**Prepared by:** Claude Sonnet 4.5
**Date:** 2026-02-09
**Last Updated:** 2026-02-09 18:00 UTC

**Related Documents:**
- [TECHNICAL_JUSTIFICATION_BACKEND.md](TECHNICAL_JUSTIFICATION_BACKEND.md)
- [DATA_INTEGRITY_STRATEGY.md](DATA_INTEGRITY_STRATEGY.md)
- [REUSABILITY_STRATEGY_PERFORMANCE_CARD.md](REUSABILITY_STRATEGY_PERFORMANCE_CARD.md)
- [PRODUCT_AUDIT_TOURNAMENT_ACHIEVEMENTS.md](PRODUCT_AUDIT_TOURNAMENT_ACHIEVEMENTS.md)
- [AUDIT_SUMMARY_EXECUTIVE.md](AUDIT_SUMMARY_EXECUTIVE.md)
