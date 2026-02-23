# 🎯 Skill Rewards Architecture

## Core Principle: Data Integrity

**UI MUST NEVER display data that is not persisted in the database.**

This is the foundation of the player progression motor. All skill point awards must be:
1. Persisted to the database when distributed
2. Queried from the database when displayed
3. Auditable and historically accurate

---

## Database Schema

### `skill_rewards` Table

**Purpose**: Universal progression event tracking for skill point awards from tournaments, training sessions, and future activities.

**Columns**:
- `id` (INTEGER, PRIMARY KEY): Unique reward ID
- `user_id` (INTEGER, FK → users.id, NOT NULL): Which player received the reward
- `source_type` (VARCHAR(20), NOT NULL): Event type - `'TOURNAMENT'` or `'TRAINING'` (extensible for future sources)
- `source_id` (INTEGER, NOT NULL): Foreign key to tournament_id or training_id
- `skill_name` (VARCHAR(50), NOT NULL): Which skill was affected (e.g., 'aggression', 'reactions')
- `points_awarded` (INTEGER, NOT NULL): Skill points awarded (can be positive or negative)
- `created_at` (TIMESTAMP, NOT NULL, DEFAULT now()): When the reward was distributed

**Indexes**:
- `ix_skill_rewards_user_id`: Fast user lookup
- `ix_skill_rewards_source`: Fast source lookup (source_type + source_id composite)
- `ix_skill_rewards_created_at`: Historical queries

**Foreign Keys**:
- `user_id` → `users.id` (CASCADE DELETE): If user is deleted, their skill rewards are also deleted

---

## Separation of Concerns

### ❌ `FootballSkillAssessment` Table
- **Purpose**: Stores current skill **measurements** and **evaluations**
- **Use case**: Skill assessments, current player state, skill profiles
- **NOT for rewards**: This is a measurement tool, not a reward audit trail

### ✅ `skill_rewards` Table
- **Purpose**: Auditable **historical events** of skill point awards
- **Use case**: Tournament rewards, training rewards, progression tracking
- **Why separate**: Clear audit trail, extensible for multiple sources, no confusion with assessments

---

## Data Flow

### 1. Reward Distribution (POST `/tournaments/{id}/distribute-rewards`)

**Location**: [`app/api/api_v1/endpoints/tournaments/rewards.py:461-467`](app/api/api_v1/endpoints/tournaments/rewards.py#L461-L467)

**Before** (WRONG - Data Integrity Violation):
```python
# ❌ Created FootballSkillAssessment records (wrong table!)
assessment = FootballSkillAssessment(
    user_license_id=user_license.id,
    skill_name=skill_key,
    points_earned=final_points,
    # ... other fields
)
db.add(assessment)
```

**After** (CORRECT - Proper Persistence):
```python
# ✅ Create SkillReward record (auditable event)
skill_reward = SkillReward(
    user_id=user.id,
    source_type="TOURNAMENT",
    source_id=tournament.id,
    skill_name=skill_key,
    points_awarded=final_points
)
db.add(skill_reward)
```

### 2. Reward Retrieval (GET `/tournaments/{id}/distributed-rewards`)

**Location**: [`app/api/api_v1/endpoints/tournaments/rewards.py:640-658`](app/api/api_v1/endpoints/tournaments/rewards.py#L640-L658)

**Before** (WRONG - Queried Wrong Table):
```python
# ❌ Queried FootballSkillAssessment with complex joins
skill_assessments = db.query(FootballSkillAssessment).join(
    UserLicense, FootballSkillAssessment.user_license_id == UserLicense.id
).filter(
    UserLicense.user_id.in_(user_ids),
    FootballSkillAssessment.assessed_at >= tournament.start_date
).all()
```

**After** (CORRECT - Direct Query):
```python
# ✅ Query skill_rewards table directly
skill_rewards = db.query(SkillReward).filter(
    SkillReward.source_type == "TOURNAMENT",
    SkillReward.source_id == tournament_id,
    SkillReward.user_id.in_(user_ids)
).all()
```

---

## SQLAlchemy Model

**File**: [`app/models/skill_reward.py`](app/models/skill_reward.py)

```python
class SkillReward(Base):
    """Track skill point rewards from tournaments and training sessions

    Separation of concerns:
    - FootballSkillAssessment: Measurements and current state of player skills
    - SkillReward: Historical events of skill point awards from specific activities
    """
    __tablename__ = "skill_rewards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(20), nullable=False)  # 'TOURNAMENT' or 'TRAINING'
    source_id = Column(Integer, nullable=False)  # tournament_id or training_id
    skill_name = Column(String(50), nullable=False)
    points_awarded = Column(Integer, nullable=False)  # Can be positive or negative
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    user = relationship("User", back_populates="skill_rewards")
```

---

## Future Extensibility

### Adding Training Rewards

When implementing training session skill rewards:

```python
# During training completion
skill_reward = SkillReward(
    user_id=user.id,
    source_type="TRAINING",  # ✅ New source type
    source_id=training_session.id,
    skill_name="dribbling",
    points_awarded=5
)
db.add(skill_reward)
```

### Query by Source Type

```python
# Get all tournament rewards
tournament_rewards = db.query(SkillReward).filter(
    SkillReward.source_type == "TOURNAMENT"
).all()

# Get all training rewards
training_rewards = db.query(SkillReward).filter(
    SkillReward.source_type == "TRAINING"
).all()

# Get all rewards for a specific user
user_rewards = db.query(SkillReward).filter(
    SkillReward.user_id == user_id
).order_by(SkillReward.created_at.desc()).all()
```

---

## Verification Results

### Test Case: Tournament 222

**Rollback**: Deleted all existing rewards (credits, XP, skill_rewards)
```sql
DELETE FROM credit_transactions WHERE semester_id = 222 AND transaction_type = 'TOURNAMENT_REWARD';
DELETE FROM xp_transactions WHERE semester_id = 222 AND transaction_type = 'TOURNAMENT_REWARD';
DELETE FROM skill_rewards WHERE source_type = 'TOURNAMENT' AND source_id = 222;
```

**Redistribution**: Via API POST `/tournaments/222/distribute-rewards`
```
✅ Success!
   - Rewards distributed: 8
   - Total credits: 1250
   - Total XP: 350
```

**DB Verification**:
```sql
SELECT reward_type, COUNT(*), SUM(amount/points_awarded)
FROM (credits | xp | skill_rewards)
WHERE tournament = 222

Results:
- Credits:      8 transactions, 1250 total
- XP:           8 transactions, 350 total
- Skill Points: 17 rewards, 52 total
```

**Data Integrity Check** (Kylian Mbappé, user_id=13):
- **DB Query**: `{'aggression': 10, 'reactions': 8, 'acceleration': 6, 'sprint_speed': 6, 'agility': 4}`
- **API Response**: `{'aggression': 10, 'reactions': 8, 'acceleration': 6, 'sprint_speed': 6, 'agility': 4}`
- **Match**: ✅ 100% exact match

---

## Reward Calculation Logic

### Top 3 Players (Positive Rewards)
- **1st Place**: 5 skills × [+5, +4, +3, +3, +2] points (weighted by game preset skill importance)
- **2nd Place**: 4 skills × [+4, +3, +2, +2] points
- **3rd Place**: 3 skills × [+3, +2, +2] points

### Bottom 2 Players (Negative Penalties)
- **Second-to-last**: 2 skills × [-2, -1] points
- **Last Place**: 3 skills × [-3, -2, -1] points

### Weighting
Skills are selected by **game preset weight** (highest first), not randomly. The `points_awarded` is calculated as:
```python
final_points = round(base_points * (weight + 1.0))
```

---

## System Lock

Once this architecture is locked, all future progression features MUST use `skill_rewards`:
- ✅ **Tournaments**: `source_type='TOURNAMENT'`
- ✅ **Training** (future): `source_type='TRAINING'`
- ✅ **Challenges** (future): `source_type='CHALLENGE'`
- ✅ **Events** (future): `source_type='EVENT'`

**NO exceptions.** The skill_rewards table is the single source of truth for player skill progression.

---

## Migration

**File**: [`alembic/versions/2026_02_01_1413-831da85c3ff5_create_skill_rewards_table.py`](alembic/versions/2026_02_01_1413-831da85c3ff5_create_skill_rewards_table.py)

**Applied**: 2026-02-01 14:13 UTC

**Rollback**: `alembic downgrade -1` (will drop skill_rewards table and indexes)

---

## Summary

✅ **Data Integrity**: UI = DB, no phantom data
✅ **Separation of Concerns**: Assessments ≠ Rewards
✅ **Auditability**: Full historical trail of skill point awards
✅ **Extensibility**: Ready for TRAINING, CHALLENGE, EVENT sources
✅ **System Foundation**: This is the player progression motor base

**Status**: 🔒 **LOCKED** - This architecture is now the standard for all skill reward features.
