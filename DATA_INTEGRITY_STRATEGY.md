# Data Integrity Strategy: Placement Source of Truth

**Date:** 2026-02-09
**Status:** CRITICAL - Required before implementation
**Issue:** Badge-Ranking inconsistency (2.2% of badges)

---

## 🚨 PROBLEM STATEMENT

**Observed Issue:**
```
Badge #1140: CHAMPION (placement=1 in metadata)
Ranking:    rank=8 (current state)

→ Badge says "#1", System says "#8"
→ Which is correct?
```

**Root Cause:**
```
Timeline:
11:43:33 → Badge created (placement=1, source: participation table)
11:50:22 → Ranking updated (rank=8, recalculated)

→ Badge metadata = immutable snapshot
→ Ranking = mutable current state
→ NO SYNC between them
```

**Frequency:** 2 out of 91 badges (2.2%)

---

## 🎯 SINGLE SOURCE OF TRUTH DECISION

### Proposed Hierarchy (Authority Order)

```
1️⃣ tournament_rankings.rank         [AUTHORITY - Current Truth]
2️⃣ tournament_participations.placement  [FALLBACK - Rewards Snapshot]
3️⃣ badge_metadata.placement         [DISPLAY ONLY - Creation Snapshot]
```

**Reasoning:**

**Why `tournament_rankings` is Authority:**
- Reflects current, calculated state
- Updated when tournament logic changes (tiebreakers, corrections)
- Used for leaderboards, analytics, admin views
- **If ranking changes → This is the new truth**

**Why NOT `badge_metadata`:**
- Immutable snapshot at creation time
- Historical record, not current state
- Cannot be updated (JSONB field, no FK)
- Should be display-only, not source of truth

**Why NOT `tournament_participations`:**
- Primarily for rewards calculation (XP, credits)
- May not sync with final rankings (awarded before finalization)
- Secondary concern: badges, not placement

---

## 🔧 IMPLEMENTATION STRATEGY

### Strategy 1: Ranking as Authority (RECOMMENDED)

**Principle:** Rankings table is source of truth. Badge metadata is display snapshot.

#### 1.1 Badge Creation Rule

**BEFORE (Current - Broken):**
```python
def award_placement_badge(user_id, tournament_id):
    # Uses participation.placement (may not be final)
    participation = get_participation(user_id, tournament_id)
    placement = participation.placement  # ❌ May be provisional

    badge = create_badge(
        user_id=user_id,
        tournament_id=tournament_id,
        badge_type=get_badge_type(placement),
        badge_metadata={"placement": placement, ...}
    )
```

**AFTER (Fixed - Consistent):**
```python
def award_placement_badge(user_id, tournament_id):
    # Use ranking as source of truth
    ranking = get_tournament_ranking(user_id, tournament_id)

    if not ranking:
        raise ValueError(f"Cannot award badge: No ranking found for user {user_id} in tournament {tournament_id}")

    placement = ranking.rank  # ✅ Authority source

    # Validate participation exists (rewards calculated)
    participation = get_participation(user_id, tournament_id)
    if not participation:
        raise ValueError(f"Cannot award badge: No participation record found")

    # Quality gate: Ensure consistency
    if participation.placement and participation.placement != placement:
        logger.warning(
            f"Placement mismatch: ranking.rank={placement}, participation.placement={participation.placement}. "
            f"Using ranking.rank as authority."
        )

    badge = create_badge(
        user_id=user_id,
        tournament_id=tournament_id,
        badge_type=get_badge_type(placement),
        badge_metadata={
            "placement": placement,  # From ranking (authority)
            "total_participants": get_total_participants(tournament_id),
            "source": "tournament_rankings"  # For debugging
        }
    )
```

#### 1.2 UI Display Rule

**Frontend Logic:**
```python
def get_display_rank(badge, ranking, participation):
    """
    Get rank for display with fallback chain.

    Hierarchy:
    1. ranking.rank (authority - current truth)
    2. participation.placement (fallback - rewards snapshot)
    3. badge_metadata.placement (last resort - creation snapshot)
    4. None (hide metric)
    """
    # Try ranking first (authority)
    if ranking and ranking.get('rank'):
        return ranking['rank'], 'current'

    # Fallback to participation (rewards table)
    if participation and participation.get('placement'):
        logger.warning(f"Badge {badge['id']}: Using participation.placement (ranking missing)")
        return participation['placement'], 'fallback_participation'

    # Last resort: badge metadata (snapshot)
    if badge.get('badge_metadata', {}).get('placement'):
        logger.warning(f"Badge {badge['id']}: Using badge_metadata.placement (ranking + participation missing)")
        return badge['badge_metadata']['placement'], 'snapshot'

    # No rank data available
    logger.error(f"Badge {badge['id']}: No rank data available from any source")
    return None, None
```

#### 1.3 Ranking Update Trigger

**When Ranking Changes:**
```python
def update_tournament_ranking(tournament_id, user_id, new_rank):
    """
    Update ranking and sync dependent tables.
    """
    # Update ranking (authority)
    ranking = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id,
        TournamentRanking.user_id == user_id
    ).first()

    old_rank = ranking.rank
    ranking.rank = new_rank
    db.commit()

    # Check if badge exists
    badge = db.query(TournamentBadge).filter(
        TournamentBadge.semester_id == tournament_id,
        TournamentBadge.user_id == user_id,
        TournamentBadge.badge_type.in_(['CHAMPION', 'RUNNER_UP', 'THIRD_PLACE'])
    ).first()

    if badge:
        old_placement = badge.badge_metadata.get('placement')
        if old_placement != new_rank:
            logger.warning(
                f"Ranking change detected: Badge {badge.id} | "
                f"Old rank={old_placement}, New rank={new_rank}. "
                f"Badge metadata NOT updated (immutable snapshot). "
                f"UI will display new rank from ranking table."
            )

            # OPTION A: Don't update badge (badge = historical snapshot)
            # UI will use ranking.rank for display

            # OPTION B: Update badge metadata (sync with new truth)
            # badge.badge_metadata['placement'] = new_rank
            # badge.badge_metadata['updated_at'] = datetime.now()
            # badge.badge_metadata['update_reason'] = 'ranking_recalculation'
            # db.commit()

    # Sync participation table (optional - depends on business logic)
    participation = db.query(TournamentParticipation).filter(
        TournamentParticipation.semester_id == tournament_id,
        TournamentParticipation.user_id == user_id
    ).first()

    if participation and participation.placement != new_rank:
        logger.info(f"Syncing participation.placement: {participation.placement} → {new_rank}")
        participation.placement = new_rank
        db.commit()
```

**Decision Point:** Should badge metadata be updated when ranking changes?

**Option A: Badge = Immutable Snapshot** (RECOMMENDED)
- Badge metadata stays as-is (historical record)
- UI displays ranking.rank (current truth)
- User sees: "You were #1 at the time, but final ranking is #8"

**Option B: Badge = Always Current**
- Badge metadata updated when ranking changes
- UI always consistent with ranking
- User sees: "You are #8" (loses historical context)

**Recommendation:** Option A (Immutable) → Preserves historical record

---

### Strategy 2: Participation as Authority (NOT RECOMMENDED)

**Why NOT:**
- Participation table is for rewards (XP, credits)
- Rewards may be calculated before final ranking
- Mixing concerns: rewards ≠ placement

**Only use if:** Ranking table is unreliable or will be deprecated

---

## 📊 PRODUCTION SAFETY RULE

### Rule: Champion Badge with Suspicious Rank

**Trigger Condition:**
```python
if badge.badge_type in ['CHAMPION', 'RUNNER_UP', 'THIRD_PLACE']:
    expected_placement = {
        'CHAMPION': 1,
        'RUNNER_UP': 2,
        'THIRD_PLACE': 3
    }[badge.badge_type]

    display_rank, source = get_display_rank(badge, ranking, participation)

    if display_rank and display_rank > 3:
        # RED FLAG: Placement badge but rank > 3
        logger.error(
            f"DATA DRIFT DETECTED: Badge {badge.id} | "
            f"Type={badge.badge_type} (expects #{expected_placement}) | "
            f"Actual rank={display_rank} (source={source}) | "
            f"User={badge.user_id} | Tournament={badge.semester_id}"
        )

        # Trigger alert
        send_alert_to_ops(
            severity='HIGH',
            message=f"Badge-Ranking inconsistency: Badge {badge.id} shows {badge.badge_type} but rank={display_rank}"
        )
```

**Action on Trigger:**
- Log error (high severity)
- Send alert to ops team
- Continue rendering (use fallback chain, don't block user)
- Ops investigates why ranking changed

**Why This Matters:**
- Detects admin errors (manual ranking changes)
- Detects bugs in ranking calculation logic
- Prevents silent data corruption

---

## 🔄 MIGRATION PLAN (For 2 Inconsistent Badges)

### Current State
```sql
SELECT
    tb.id as badge_id,
    tb.badge_type,
    tb.badge_metadata->>'placement' as badge_placement,
    tr.rank as ranking_rank,
    tp.placement as participation_placement
FROM tournament_badges tb
LEFT JOIN tournament_rankings tr ON tr.tournament_id = tb.semester_id AND tr.user_id = tb.user_id
LEFT JOIN tournament_participations tp ON tp.semester_id = tb.semester_id AND tp.user_id = tb.user_id
WHERE tb.id IN (1140, 1160);

Results:
Badge 1140: CHAMPION, badge_placement=1, ranking_rank=8, participation_placement=1
Badge 1160: THIRD_PLACE, badge_placement=3, ranking_rank=8, participation_placement=3
```

### Investigation Required

**For Badge 1140 (CHAMPION but rank=8):**

**Question:** Is rank=8 the correct current state, or was badge correct at creation?

**Check tournament history:**
```sql
-- Was this tournament recalculated?
SELECT * FROM tournament_rankings_history WHERE tournament_id=220 AND user_id=4;

-- If no history table, check logs:
grep "tournament_id=220" /var/log/backend.log | grep "ranking_update"
```

**Possible Scenarios:**

1. **Ranking was recalculated (badge was correct initially)**
   - Action: Keep ranking=8 as authority, badge metadata = historical snapshot
   - UI displays: rank=8 (from ranking table)
   - Badge title updated: "Tournament Participant" (not Champion)

2. **Badge was awarded incorrectly (ranking=8 is correct)**
   - Action: Revoke CHAMPION badge, award participation badge
   - Update badge_type + metadata

3. **User was disqualified after badge award**
   - Action: Keep badge (earned at the time), display current rank=8
   - Add metadata: `{"disqualified": true, "original_placement": 1}`

**Decision:** Requires business stakeholder input (not technical decision)

---

## ✅ FINAL RECOMMENDATION

### Single Source of Truth: `tournament_rankings.rank`

**Implementation Checklist:**

- [x] **Badge Creation:** Use `ranking.rank` as source (not participation.placement)
- [x] **UI Display:** Fallback chain (ranking → participation → badge_metadata)
- [x] **Ranking Update:** Log inconsistencies, don't auto-update badge (immutable)
- [x] **Production Safety:** Alert on Champion badge with rank > 3
- [ ] **Migration:** Investigate 2 inconsistent badges (stakeholder decision needed)
- [ ] **Quality Gate:** Raise error if badge awarded without ranking
- [ ] **Documentation:** Update badge creation flow diagram

### Data Flow Diagram

```
Tournament Ends
    ↓
Final Rankings Calculated (tournament_rankings.rank) ← AUTHORITY
    ↓
Participation Rewards Calculated (tournament_participations.placement)
    ↓
    ├─→ Validate: ranking.rank == participation.placement
    │       ↓ YES: Proceed
    │       ↓ NO: Log warning, use ranking.rank
    ↓
Badge Awarded (badge_metadata.placement = ranking.rank)
    ↓
Badge Metadata = Immutable Snapshot
    ↓
UI Display: Uses ranking.rank (fallback to badge_metadata if ranking missing)
```

---

## 🎯 ACCEPTANCE CRITERIA (Data Integrity)

- [ ] **AC-D1:** All new badges use `ranking.rank` as placement source
- [ ] **AC-D2:** Badge creation fails if `ranking` is NULL (quality gate)
- [ ] **AC-D3:** UI fallback chain implemented (ranking → participation → badge_metadata)
- [ ] **AC-D4:** Production safety alert triggers on Champion badge with rank > 3
- [ ] **AC-D5:** 100% of new badges have consistent placement (ranking == badge_metadata)
- [ ] **AC-D6:** Existing 2 inconsistent badges investigated (resolution documented)

---

**Status:** ✅ Strategy defined - Ready for implementation
**Blockers:** Migration decision for 2 inconsistent badges (stakeholder input needed)
**Next Step:** Implement badge creation quality gate + UI fallback chain

---

**Prepared by:** Claude Sonnet 4.5
**Date:** 2026-02-09
**Priority:** CRITICAL (blocks Performance Card implementation)
