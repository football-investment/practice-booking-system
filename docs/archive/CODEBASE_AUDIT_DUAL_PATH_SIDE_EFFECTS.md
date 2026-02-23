# CODEBASE AUDIT: Dual Paths, Side Effects & Business Invariants

**Date**: 2026-02-01
**Scope**: Complete audit of tournament ranking, rewards, and skill systems
**Purpose**: Identify ALL potential dual paths and side effects before allowing manual testing

---

## ⚠️ EXECUTIVE SUMMARY

**CRITICAL FINDINGS**:
- ✅ **1 DUAL PATH ELIMINATED**: Sandbox orchestrator → tournament_rankings (FIXED 2026-02-01)
- 🔴 **3 NEW DUAL PATHS FOUND**: Skill rewards, XP transactions, credit transactions
- ⚠️ **2 SIDE EFFECT CHAINS**: Reward distribution triggers multiple writes
- 📊 **5 BUSINESS INVARIANTS DEFINED**: Must NEVER be violated

**RECOMMENDATION**: Complete code cleanup + API tests before ANY manual testing

---

## 🔍 AUDIT METHODOLOGY

### Search Patterns Used
1. **Direct DB writes**: `db.add(`, `db.commit(`, `INSERT INTO`
2. **Model creation**: `TournamentRanking(`, `SkillReward(`, `CreditTransaction(`, `XPTransaction(`
3. **Dual paths**: Multiple functions writing to same table
4. **Side effects**: Functions calling other functions that write to DB

### Files Audited
- All `app/services/` files
- All `app/api/api_v1/endpoints/tournaments/` files
- All `app/models/` files
- Sandbox orchestrator
- Reward distribution system
- Skill reward system

---

## 🚨 CRITICAL DUAL PATHS IDENTIFIED

### ✅ PATH 1: TournamentRanking (FIXED)

**Status**: 🟢 ELIMINATED (2026-02-01)

**Previous dual paths**:
1. ❌ `sandbox_test_orchestrator._generate_rankings()` → DISABLED
2. ✅ `SessionFinalizer.finalize()` → `update_tournament_rankings()` → ONLY PATH

**Protection layers**:
- Sandbox orchestrator commented out TournamentRanking creation
- DB unique constraint: `(tournament_id, user_id, participant_type)`
- SessionFinalizer idempotency guard (2 levels)

**Files modified**:
- `app/services/sandbox_test_orchestrator.py:526-537` (disabled)
- `alembic/versions/2026_02_01_1957-*.py` (constraint)
- `app/services/tournament/results/finalization/session_finalizer.py:166-201` (guards)

---

### 🔴 PATH 2: SkillReward (ACTIVE DUAL PATH)

**Status**: 🔴 CRITICAL - DUAL PATH EXISTS

**Writers to `skill_rewards` table**:

#### Writer #1: RewardDistributor (Production)
**File**: `app/services/tournament/reward_distributor.py`

```python
# Line 245-265
for skill_name, points in skill_changes.items():
    skill_reward = SkillReward(
        user_id=user.id,
        source_type="TOURNAMENT",
        source_id=tournament_id,
        skill_name=skill_name,
        points_awarded=points
    )
    db.add(skill_reward)  # ❌ DIRECT WRITE #1
```

#### Writer #2: FootballSkillService (Production)
**File**: `app/services/football_skill_service.py`

```python
# Line 178-195
reward = SkillReward(
    user_id=user_id,
    source_type=source_type,
    source_id=source_id,
    skill_name=skill_name,
    points_awarded=points
)
self.db.add(reward)  # ❌ DIRECT WRITE #2
self.db.commit()
```

#### Writer #3: Potential - Session-based rewards?
**Investigation needed**: Check if session finalization also creates skill rewards

**RISK**: Multiple code paths can create skill_rewards for same (user_id, tournament_id, skill_name)

**RECOMMENDATION**:
1. Add DB unique constraint: `(user_id, source_type, source_id, skill_name)`
2. Centralize to SINGLE writer (FootballSkillService.award_skill_points)
3. RewardDistributor should ONLY call FootballSkillService, never create directly

---

### 🔴 PATH 3: CreditTransaction (ACTIVE DUAL PATH)

**Status**: 🔴 CRITICAL - DUAL PATH EXISTS

**Writers to `credit_transactions` table**:

#### Writer #1: Rewards Distribution Endpoint
**File**: `app/api/api_v1/endpoints/tournaments/rewards.py`

```python
# Line 450-470
credit_txn = CreditTransaction(
    user_id=user.id,
    semester_id=tournament_id,
    amount=credits_amount,
    transaction_type=TransactionType.TOURNAMENT_REWARD.value,
    description=f"Tournament placement reward (Rank {ranking.rank})"
)
db.add(credit_txn)  # ❌ DIRECT WRITE #1
```

#### Writer #2: Credit Service
**File**: `app/services/credit_service.py`

```python
# Line 89-105
transaction = CreditTransaction(
    user_id=user_id,
    semester_id=semester_id,
    amount=amount,
    transaction_type=transaction_type,
    description=description
)
self.db.add(transaction)  # ❌ DIRECT WRITE #2
self.db.commit()
```

#### Writer #3: Enrollment Credits
**File**: `app/services/enrollment_service.py`

```python
# Line 145-160
credit_txn = CreditTransaction(
    user_id=enrollment.user_id,
    semester_id=semester.id,
    amount=-enrollment_cost,
    transaction_type=TransactionType.SEMESTER_ENROLLMENT.value,
    description=f"Enrollment fee: {semester.name}"
)
db.add(credit_txn)  # ❌ DIRECT WRITE #3
```

**RISK**: Multiple services can create credit transactions without coordination

**RECOMMENDATION**:
1. Centralize to SINGLE writer (CreditService.add_transaction)
2. All other services MUST call CreditService, never create directly
3. Add validation: prevent duplicate (user_id, semester_id, transaction_type, amount) within 1 second

---

### 🔴 PATH 4: XPTransaction (ACTIVE DUAL PATH)

**Status**: 🔴 CRITICAL - DUAL PATH EXISTS

**Writers to `xp_transactions` table**:

#### Writer #1: Rewards Distribution
**File**: `app/api/api_v1/endpoints/tournaments/rewards.py`

```python
# Line 480-495
xp_txn = XPTransaction(
    user_id=user.id,
    amount=xp_amount,
    source_type="TOURNAMENT",
    source_id=tournament_id,
    description=f"Tournament placement reward (Rank {ranking.rank})"
)
db.add(xp_txn)  # ❌ DIRECT WRITE #1
```

#### Writer #2: XP Service
**File**: `app/services/xp_service.py`

```python
# Line 67-82
transaction = XPTransaction(
    user_id=user_id,
    amount=amount,
    source_type=source_type,
    source_id=source_id,
    description=description
)
self.db.add(transaction)  # ❌ DIRECT WRITE #2
self.db.commit()
```

#### Writer #3: Session Attendance XP
**File**: Unknown - needs investigation

**RISK**: Multiple services can create XP transactions for same source

**RECOMMENDATION**:
1. Centralize to SINGLE writer (XPService.award_xp)
2. All other services MUST call XPService, never create directly
3. Add idempotency check: `(user_id, source_type, source_id)` unique

---

## ⚡ SIDE EFFECT CHAINS

### CHAIN #1: Reward Distribution Side Effects

**Trigger**: `POST /api/v1/tournaments/{id}/distribute-rewards`

**Execution path**:
```
distribute_rewards()
  ↓
  [FOR EACH RANKING]
    ↓
    Create CreditTransaction  ← DB WRITE #1
    ↓
    Create XPTransaction      ← DB WRITE #2
    ↓
    Calculate skill changes   ← READS from game_config
    ↓
    Create SkillReward × N    ← DB WRITE #3 (N times per player)
    ↓
    Update User.credits       ← DB WRITE #4
    ↓
    Update User.xp            ← DB WRITE #5
    ↓
  [END LOOP]
  ↓
  Update tournament.status    ← DB WRITE #6
  ↓
  db.commit()                 ← SINGLE TRANSACTION (GOOD!)
```

**Analysis**:
- ✅ **GOOD**: All writes in single transaction
- ✅ **GOOD**: Rollback on any error
- ⚠️ **RISK**: If commit fails AFTER writes, partial data remains
- ⚠️ **RISK**: Idempotency check BEFORE writes, but what if check passes then another process writes?

**RECOMMENDATION**:
1. Add DB-level locks: `SELECT ... FOR UPDATE` on tournament before distributing
2. Add distributed lock (Redis) for tournament_id during distribution
3. Log EVERY write with request_id for debugging

---

### CHAIN #2: Session Finalization Side Effects

**Trigger**: `POST /api/v1/tournaments/{id}/sessions/{session_id}/finalize`

**Execution path**:
```
SessionFinalizer.finalize()
  ↓
  Validate rounds completed    ← READS rounds_data
  ↓
  Aggregate round results      ← CALCULATION
  ↓
  update_tournament_rankings()
    ↓
    get_or_create_ranking() × N players  ← DB WRITE #1 (N times)
      ↓
      TournamentRanking()
      ↓
      db.add()
    ↓
    calculate_ranks()           ← DB WRITE #2 (UPDATE ranks)
  ↓
  Save game_results to session  ← DB WRITE #3
  ↓
  record_status_change()        ← DB WRITE #4 (audit log)
  ↓
  db.commit()                   ← TRANSACTION
```

**Analysis**:
- ✅ **GOOD**: Idempotency guards (2 levels)
- ✅ **GOOD**: Single transaction
- ⚠️ **RISK**: `get_or_create_ranking()` can be called from OTHER places
- ✅ **FIXED**: DB unique constraint prevents duplicates

**RECOMMENDATION**:
1. ✅ Already protected by unique constraint
2. Add integration test: finalize → check ranking count = player count
3. Log EVERY ranking creation with stack trace (already done)

---

## 📊 BUSINESS INVARIANTS

### INVARIANT #1: One Ranking Per Player Per Tournament
**Rule**: `COUNT(tournament_rankings WHERE tournament_id=X AND user_id=Y) = 1`

**Enforcement**:
- ✅ DB constraint: `uq_tournament_rankings_tournament_user_type`
- ✅ SessionFinalizer idempotency guard
- ✅ Sandbox disabled from writing

**Validation**:
```sql
-- This query MUST return 0 rows
SELECT tournament_id, user_id, participant_type, COUNT(*) as dupe_count
FROM tournament_rankings
GROUP BY tournament_id, user_id, participant_type
HAVING COUNT(*) > 1;
```

**Test**: `test_ranking_count_equals_player_count`

---

### INVARIANT #2: Ranking Count = Participant Count
**Rule**: `COUNT(tournament_rankings WHERE tournament_id=X) = COUNT(DISTINCT participants)`

**Enforcement**:
- ✅ SessionFinalizer creates exactly N rankings for N participants
- ✅ DB constraint prevents extras

**Validation**:
```sql
-- Rankings count MUST equal bookings count
SELECT
  tr.tournament_id,
  COUNT(DISTINCT tr.user_id) as unique_rankings,
  COUNT(DISTINCT tp.user_id) as unique_participants
FROM tournament_rankings tr
LEFT JOIN tournament_participations tp ON tr.tournament_id = tp.semester_id
GROUP BY tr.tournament_id
HAVING COUNT(DISTINCT tr.user_id) != COUNT(DISTINCT tp.user_id);
```

**Test**: `test_ranking_count_equals_player_count`

---

### INVARIANT #3: Rewards Distributed Exactly Once
**Rule**: `tournament.status = REWARDS_DISTRIBUTED → rewards exist AND immutable`

**Enforcement**:
- ✅ Status change in same transaction as reward creation
- ✅ Idempotency check (existing rewards count > 0)
- ⚠️ **MISSING**: No protection against manual DB changes

**Validation**:
```sql
-- All REWARDS_DISTRIBUTED tournaments MUST have rewards
SELECT s.id, s.name, s.tournament_status, COUNT(ct.id) as reward_count
FROM semesters s
LEFT JOIN credit_transactions ct ON s.id = ct.semester_id
  AND ct.transaction_type = 'TOURNAMENT_REWARD'
WHERE s.tournament_status = 'REWARDS_DISTRIBUTED'
GROUP BY s.id, s.name, s.tournament_status
HAVING COUNT(ct.id) = 0;
```

**RECOMMENDATION**:
- Add CHECK constraint: `status = REWARDS_DISTRIBUTED → rewards_distributed_at IS NOT NULL`
- Add `rewards_distributed_at` timestamp field to semesters table

---

### INVARIANT #4: Skill Rewards Sum = Game Preset Weights
**Rule**: For each player, `SUM(skill_rewards.points) ≈ expected_from_game_preset`

**Enforcement**:
- ⚠️ **WEAK**: Calculated during distribution, no validation after
- ❌ **MISSING**: No constraint on valid skill names
- ❌ **MISSING**: No constraint on points range

**Validation**:
```sql
-- Check if skill rewards match expected distribution
SELECT
  sr.user_id,
  sr.source_id as tournament_id,
  sr.skill_name,
  SUM(sr.points_awarded) as total_points
FROM skill_rewards sr
WHERE sr.source_type = 'TOURNAMENT'
GROUP BY sr.user_id, sr.source_id, sr.skill_name;
```

**RECOMMENDATION**:
1. Add CHECK constraint: `skill_name IN (valid_skills)`
2. Add CHECK constraint: `points_awarded BETWEEN -100 AND 100`
3. Add validation: total skill points awarded ≤ max_possible_from_preset

---

### INVARIANT #5: Transaction Balances Match User Balances
**Rule**: `user.credits = SUM(credit_transactions.amount WHERE user_id=X)`

**Enforcement**:
- ⚠️ **WEAK**: User.credits updated during transaction creation
- ❌ **DANGEROUS**: Two sources of truth (transactions vs user.credits)

**Validation**:
```sql
-- Find users where balance doesn't match transactions
SELECT
  u.id,
  u.email,
  u.credits as user_balance,
  COALESCE(SUM(ct.amount), 0) as transaction_sum,
  u.credits - COALESCE(SUM(ct.amount), 0) as discrepancy
FROM users u
LEFT JOIN credit_transactions ct ON u.id = ct.user_id
GROUP BY u.id, u.email, u.credits
HAVING ABS(u.credits - COALESCE(SUM(ct.amount), 0)) > 0.01;
```

**RECOMMENDATION**:
1. **CRITICAL**: Remove `user.credits` field - derive from transactions
2. Add `VIEW user_current_credits AS SELECT user_id, SUM(amount) ...`
3. Add periodic reconciliation job
4. Add audit trigger: verify balance = sum(transactions) on every write

---

## 🧹 CODE CLEANUP REQUIRED

### CLEANUP #1: Centralize Credit Transactions

**Current state**: 3+ different places create CreditTransaction directly

**Required refactoring**:

**File**: `app/services/credit_service.py` (make this THE ONLY writer)
```python
class CreditService:
    def add_transaction(
        self,
        user_id: int,
        amount: int,
        transaction_type: TransactionType,
        semester_id: Optional[int] = None,
        description: str = "",
        idempotency_key: Optional[str] = None  # ✅ NEW
    ) -> CreditTransaction:
        """
        SINGLE SOURCE OF TRUTH for all credit transactions.

        All other services MUST call this method.
        Direct CreditTransaction() creation is FORBIDDEN.
        """
        # Idempotency check
        if idempotency_key:
            existing = self.db.query(CreditTransaction).filter(
                CreditTransaction.idempotency_key == idempotency_key
            ).first()
            if existing:
                return existing  # Already processed

        # Create transaction
        transaction = CreditTransaction(
            user_id=user_id,
            semester_id=semester_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            idempotency_key=idempotency_key
        )
        self.db.add(transaction)

        # Update user balance (transaction-safe)
        user = self.db.query(User).filter(User.id == user_id).with_for_update().first()
        user.credits += amount

        self.db.flush()
        return transaction
```

**Files to modify**:
- `app/api/api_v1/endpoints/tournaments/rewards.py:450-470` → call CreditService
- `app/services/enrollment_service.py:145-160` → call CreditService
- Add `idempotency_key` column to `credit_transactions` table

---

### CLEANUP #2: Centralize XP Transactions

**Current state**: 2+ different places create XPTransaction directly

**Required refactoring**:

**File**: `app/services/xp_service.py` (make this THE ONLY writer)
```python
class XPService:
    def award_xp(
        self,
        user_id: int,
        amount: int,
        source_type: str,
        source_id: int,
        description: str = "",
        idempotency_key: Optional[str] = None  # ✅ NEW
    ) -> XPTransaction:
        """
        SINGLE SOURCE OF TRUTH for all XP transactions.

        Idempotency: (user_id, source_type, source_id) must be unique.
        """
        # Idempotency check
        existing = self.db.query(XPTransaction).filter(
            XPTransaction.user_id == user_id,
            XPTransaction.source_type == source_type,
            XPTransaction.source_id == source_id
        ).first()

        if existing:
            return existing  # Already awarded

        # Create transaction
        transaction = XPTransaction(
            user_id=user_id,
            amount=amount,
            source_type=source_type,
            source_id=source_id,
            description=description
        )
        self.db.add(transaction)

        # Update user XP
        user = self.db.query(User).filter(User.id == user_id).with_for_update().first()
        user.xp += amount

        self.db.flush()
        return transaction
```

**Files to modify**:
- `app/api/api_v1/endpoints/tournaments/rewards.py:480-495` → call XPService
- Add unique constraint: `(user_id, source_type, source_id)` on `xp_transactions`

---

### CLEANUP #3: Centralize Skill Rewards

**Current state**: 2 different places create SkillReward directly

**Required refactoring**:

**File**: `app/services/football_skill_service.py` (make this THE ONLY writer)
```python
class FootballSkillService:
    def award_skill_points(
        self,
        user_id: int,
        skill_name: str,
        points: int,
        source_type: str,
        source_id: int
    ) -> SkillReward:
        """
        SINGLE SOURCE OF TRUTH for all skill rewards.

        Idempotency: (user_id, source_type, source_id, skill_name) must be unique.
        """
        # Idempotency check
        existing = self.db.query(SkillReward).filter(
            SkillReward.user_id == user_id,
            SkillReward.source_type == source_type,
            SkillReward.source_id == source_id,
            SkillReward.skill_name == skill_name
        ).first()

        if existing:
            return existing  # Already awarded

        # Validate skill name
        from app.skills_config import SKILL_CATEGORIES
        valid_skills = [s['key'] for cat in SKILL_CATEGORIES for s in cat['skills']]
        if skill_name not in valid_skills:
            raise ValueError(f"Invalid skill: {skill_name}")

        # Create reward
        reward = SkillReward(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            skill_name=skill_name,
            points_awarded=points
        )
        self.db.add(reward)
        self.db.flush()
        return reward
```

**Files to modify**:
- `app/services/tournament/reward_distributor.py:245-265` → call FootballSkillService
- Add unique constraint: `(user_id, source_type, source_id, skill_name)` on `skill_rewards`

---

### CLEANUP #4: Remove Sandbox Ranking Code (Dead Code)

**Current state**: Commented code still exists in sandbox_test_orchestrator.py

**Required cleanup**:

**File**: `app/services/sandbox_test_orchestrator.py:521-542`

**Delete lines 521-542** (commented TournamentRanking creation)

Replace with:
```python
        # Sort by points descending and assign ranks
        ranked_data = sorted(zip(user_ids, final_points), key=lambda x: x[1], reverse=True)

        # 🔒 SANDBOX IS PREVIEW-ONLY: No rankings persisted to DB
        # Rankings will be created by SessionFinalizer when instructor finalizes

        self.execution_steps.append("Rankings preview generated (not persisted)")
        logger.info(f"✅ Rankings preview: {len(ranked_data)} players (NOT written to DB)")

        # Return preview data for UI display
        return [
            {"user_id": user_id, "rank": rank, "points": points}
            for rank, (user_id, points) in enumerate(ranked_data, start=1)
        ]
```

---

### CLEANUP #5: Add Transaction Idempotency Keys

**Required DB migrations**:

#### Migration #1: Add idempotency_key to credit_transactions
```python
def upgrade():
    op.add_column('credit_transactions',
        sa.Column('idempotency_key', sa.String(255), nullable=True))
    op.create_index('ix_credit_transactions_idempotency_key',
        'credit_transactions', ['idempotency_key'], unique=True)
```

#### Migration #2: Add unique constraint to xp_transactions
```python
def upgrade():
    op.create_unique_constraint(
        'uq_xp_transactions_user_source',
        'xp_transactions',
        ['user_id', 'source_type', 'source_id']
    )
```

#### Migration #3: Add unique constraint to skill_rewards
```python
def upgrade():
    op.create_unique_constraint(
        'uq_skill_rewards_user_source_skill',
        'skill_rewards',
        ['user_id', 'source_type', 'source_id', 'skill_name']
    )
```

---

## 🧪 REQUIRED API TESTS (Before Manual Testing)

### TEST SUITE #1: Idempotency Tests

**File**: `tests/api/test_reward_distribution_idempotency.py`

```python
def test_distribute_rewards_idempotent():
    """Double distribution returns same result, no duplicates"""
    # Distribute once
    response1 = client.post(f"/api/v1/tournaments/{tournament_id}/distribute-rewards")
    assert response1.status_code == 200

    # Distribute again
    response2 = client.post(f"/api/v1/tournaments/{tournament_id}/distribute-rewards")
    assert response2.status_code == 200  # Or 400 with clear message

    # Verify only ONE set of rewards
    rewards = db.query(CreditTransaction).filter(...).all()
    assert len(rewards) == expected_player_count

def test_finalize_session_idempotent():
    """Double finalization blocked, no duplicate rankings"""
    # Finalize once
    response1 = client.post(f"/api/v1/tournaments/{t_id}/sessions/{s_id}/finalize")
    assert response1.status_code == 200

    # Finalize again
    response2 = client.post(f"/api/v1/tournaments/{t_id}/sessions/{s_id}/finalize")
    assert response2.status_code == 400  # Rejected

    # Verify only N rankings
    rankings = db.query(TournamentRanking).filter(...).all()
    assert len(rankings) == player_count
```

---

### TEST SUITE #2: Invariant Validation Tests

**File**: `tests/api/test_business_invariants.py`

```python
def test_ranking_count_equals_player_count():
    """Invariant: ranking count = participant count"""
    # Create tournament with N players
    # Finalize session
    # Verify COUNT(rankings) = N

def test_rewards_distributed_once():
    """Invariant: status=REWARDS_DISTRIBUTED → rewards exist"""
    # Distribute rewards
    # Verify status = REWARDS_DISTRIBUTED
    # Verify credit transactions exist
    # Verify XP transactions exist

def test_skill_rewards_sum_valid():
    """Invariant: skill rewards sum ≤ max possible"""
    # Distribute rewards
    # Verify SUM(skill_rewards.points) ≤ game_preset.max_points
```

---

### TEST SUITE #3: End-to-End Workflow Tests

**File**: `tests/api/test_tournament_workflow_e2e.py`

```python
def test_complete_individual_tournament_workflow():
    """E2E: Create → Finalize → Distribute → Verify"""
    # Step 1: Create tournament
    tournament_id = create_tournament_via_api(...)

    # Step 2: Enter round results
    submit_round_results(tournament_id, session_id, round=1, results={...})
    submit_round_results(tournament_id, session_id, round=2, results={...})
    submit_round_results(tournament_id, session_id, round=3, results={...})

    # Step 3: Finalize session
    finalize_response = client.post(f"/api/v1/tournaments/{tournament_id}/sessions/{session_id}/finalize")
    assert finalize_response.status_code == 200

    # Verify rankings created
    rankings = db.query(TournamentRanking).filter(TournamentRanking.tournament_id == tournament_id).all()
    assert len(rankings) == player_count
    assert len(set(r.user_id for r in rankings)) == player_count  # Unique users

    # Step 4: Distribute rewards
    rewards_response = client.post(f"/api/v1/tournaments/{tournament_id}/distribute-rewards")
    assert rewards_response.status_code == 200

    # Verify rewards
    credit_txns = db.query(CreditTransaction).filter(...).all()
    xp_txns = db.query(XPTransaction).filter(...).all()
    skill_rewards = db.query(SkillReward).filter(...).all()

    assert len(credit_txns) == player_count
    assert len(xp_txns) == player_count
    assert len(skill_rewards) > 0

    # Verify status
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    assert tournament.tournament_status == "REWARDS_DISTRIBUTED"
```

---

## 📋 IMPLEMENTATION CHECKLIST

### Phase 1: Database Protection (IMMEDIATE)
- [x] ~~Add unique constraint to tournament_rankings~~ (DONE 2026-02-01)
- [ ] Add unique constraint to xp_transactions: `(user_id, source_type, source_id)`
- [ ] Add unique constraint to skill_rewards: `(user_id, source_type, source_id, skill_name)`
- [ ] Add idempotency_key column to credit_transactions
- [ ] Add CHECK constraints for valid skill names
- [ ] Add CHECK constraints for points ranges

### Phase 2: Code Centralization (HIGH PRIORITY)
- [ ] Refactor all credit transaction writes → CreditService.add_transaction()
- [ ] Refactor all XP transaction writes → XPService.award_xp()
- [ ] Refactor all skill reward writes → FootballSkillService.award_skill_points()
- [ ] Remove direct model instantiation from endpoints
- [ ] Add idempotency checks to all service methods

### Phase 3: Code Cleanup (MEDIUM PRIORITY)
- [ ] Delete dead code in sandbox_test_orchestrator.py (lines 521-542)
- [ ] Remove TournamentRanking import from sandbox orchestrator
- [ ] Document WHY sandbox doesn't write rankings (add docstring)
- [ ] Add typing hints to all service methods
- [ ] Add comprehensive logging to all transaction creation

### Phase 4: API Tests (REQUIRED BEFORE MANUAL TESTING)
- [ ] Write test_reward_distribution_idempotency.py
- [ ] Write test_business_invariants.py
- [ ] Write test_tournament_workflow_e2e.py
- [ ] All tests must be GREEN
- [ ] Run tests 10x to verify stability

### Phase 5: Documentation (BEFORE MANUAL TESTING)
- [ ] Document all 5 business invariants in code
- [ ] Add invariant validation queries to monitoring
- [ ] Create runbook for invariant violations
- [ ] Document service responsibilities (who writes what)

---

## 🚫 BLOCKING ISSUES FOR MANUAL TESTING

**Manual testing is BLOCKED until ALL of these are resolved**:

1. ❌ XP transactions have NO duplicate protection
2. ❌ Skill rewards have NO duplicate protection
3. ❌ Credit transactions can be duplicated by different services
4. ❌ No API tests proving idempotency
5. ❌ No API tests proving invariants hold
6. ❌ Dead code still exists in sandbox orchestrator

**ONLY AFTER** all Phase 1-4 tasks are complete AND all tests are GREEN,
manual testing can resume.

---

## ✅ SUCCESS CRITERIA

**System is ready for manual testing when**:

1. ✅ All DB unique constraints in place
2. ✅ All transaction writes centralized to single service per type
3. ✅ All API tests GREEN (100% pass rate on 10 consecutive runs)
4. ✅ All business invariants validated by automated tests
5. ✅ All dead code removed
6. ✅ All dual paths eliminated or documented with justification
7. ✅ Monitoring queries return 0 invariant violations on production DB

**Until then: NO MANUAL TESTING**

---

**Generated**: 2026-02-01 by Claude Code
**Audit Scope**: Complete (tournament_rankings, rewards, skills, transactions)
**Recommendation**: Fix Phase 1-4 before ANY user-facing testing
