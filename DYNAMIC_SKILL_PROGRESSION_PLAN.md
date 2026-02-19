# 🎯 Dynamic Skill Progression System - Technical Plan

**Date**: 2026-01-25
**Status**: 📋 Planning Phase
**Goal**: Transform static skill rewards into dynamic, progression-based player development

---

## 🔍 Current State Analysis

### ✅ What We Have
1. **Skill Assessment System** (`FootballSkillAssessment`)
   - Instructor-driven manual assessments
   - Valid skills: `heading`, `shooting`, `crossing`, `passing`, `dribbling`, `ball_control`
   - Cached in `UserLicense.football_skills` (JSONB)
   - Average calculation based on assessment history

2. **Tournament Reward System** (Just Completed)
   - Placement-based skill point distribution
   - Valid skills: `speed`, `agility`, `stamina`, `ball_control`, `shooting`, `passing`, `dribbling`, `positioning`, `decision_making`
   - Currently stored in `TournamentParticipation.skill_points_awarded` (JSONB)
   - **NOT integrated with user profile**

3. **Player Dashboard**
   - Shows onboarding self-assessment values
   - Static display (e.g., "Heading 8/10")
   - Average Skill Level calculated from initial values
   - **Does not reflect tournament performance**

### ❌ What's Missing
1. **No connection** between tournament rewards → player skill profile
2. **No dynamic updates** to skill values based on performance
3. **No progression tracking** over time
4. **Two separate skill systems** (assessment vs tournament)

---

## 🏗️ Proposed Architecture

### 1️⃣ **Unified Skill Model**

#### A) **Skill Ontology Mapping**

Map tournament skills → player profile skills:

```python
SKILL_MAPPING = {
    # Tournament Skill → Player Profile Skill(s)
    "speed": ["speed"],  # NEW: Add to player profile
    "agility": ["agility"],  # NEW: Add to player profile
    "stamina": ["stamina"],  # NEW: Add to player profile
    "ball_control": ["ball_control"],  # EXISTING
    "shooting": ["shooting"],  # EXISTING
    "passing": ["passing"],  # EXISTING
    "dribbling": ["dribbling"],  # EXISTING
    "positioning": ["positioning"],  # NEW: Add to player profile
    "decision_making": ["decision_making"],  # NEW: Add to player profile
    "heading": ["heading"],  # EXISTING (only in profile)
    "crossing": ["crossing"],  # EXISTING (only in profile)
}
```

**Decision**: Expand `VALID_SKILLS` to include all tournament skills.

---

### 2️⃣ **Data Model: Player Skill Profile**

#### Schema Changes

**Option A: Extend `UserLicense.football_skills`** (RECOMMENDED)

```python
# Current structure (static baseline)
UserLicense.football_skills = {
    "heading": 80.0,  # Self-assessment from onboarding
    "shooting": 100.0,
    "crossing": 70.0,
    # ...
}

# NEW structure (dynamic progression)
UserLicense.football_skills = {
    "heading": {
        "current_level": 80.5,  # Dynamic value
        "baseline": 80.0,  # Onboarding self-assessment (never changes)
        "total_delta": 0.5,  # Sum of all deltas applied
        "last_updated": "2026-01-25T10:30:00Z",
        "assessment_count": 5,  # Number of assessments
        "tournament_wins": 2  # Tournaments where this skill was rewarded
    },
    "shooting": {
        "current_level": 102.3,
        "baseline": 100.0,
        "total_delta": 2.3,
        "last_updated": "2026-01-25T11:45:00Z",
        "assessment_count": 8,
        "tournament_wins": 3
    },
    # ...
}
```

**Migration Strategy**:
```python
# Convert old format to new format
def migrate_skill_format(old_skills):
    new_skills = {}
    for skill_name, value in old_skills.items():
        new_skills[skill_name] = {
            "current_level": value,
            "baseline": value,
            "total_delta": 0.0,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "assessment_count": 0,
            "tournament_wins": 0
        }
    return new_skills
```

**Option B: New Table `UserSkillProfile`** (More Normalized)

```sql
CREATE TABLE user_skill_profiles (
    id SERIAL PRIMARY KEY,
    user_license_id INTEGER REFERENCES user_licenses(id),
    skill_name VARCHAR(50) NOT NULL,
    current_level FLOAT NOT NULL DEFAULT 0.0,
    baseline_level FLOAT NOT NULL DEFAULT 0.0,
    total_delta FLOAT NOT NULL DEFAULT 0.0,
    last_updated TIMESTAMP DEFAULT NOW(),
    assessment_count INTEGER DEFAULT 0,
    tournament_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_license_id, skill_name)
);
```

**Recommendation**: **Option A** for simplicity, with migration plan to Option B if performance becomes an issue.

---

### 3️⃣ **Skill Delta Calculation Formula**

#### Base Formula

```python
def calculate_skill_delta(
    placement: int,
    skill_weight: float,
    total_weight: float,
    base_skill_points: float
) -> float:
    """
    Calculate skill delta from tournament performance

    Args:
        placement: Tournament placement (1-8+)
        skill_weight: Weight of this skill in tournament config (e.g., 2.0)
        total_weight: Sum of all enabled skill weights (e.g., 3.5)
        base_skill_points: Base points for placement (10/7/5/1)

    Returns:
        Skill delta to apply (in percentage points)

    Example:
        NIKE Speed Test (Championship) - 1st Place
        placement=1 → base_skill_points=10.0
        speed: weight=2.0, total_weight=3.5
        skill_proportion = 2.0 / 3.5 = 0.571
        raw_points = 10.0 * 0.571 = 5.71

        DELTA CONVERSION (scale to feel growth):
        delta = raw_points * DELTA_MULTIPLIER
        delta = 5.71 * 0.125 = 0.714 ≈ +0.7 percentage points
    """
    skill_proportion = skill_weight / total_weight
    raw_points = base_skill_points * skill_proportion

    # Scale to noticeable delta (12.5% of raw points - mid-range, tunable)
    DELTA_MULTIPLIER = 0.125  # Range: 0.10 - 0.15 (configurable)
    delta = raw_points * DELTA_MULTIPLIER

    return round(delta, 2)
```

#### Progression Scale

```python
PLACEMENT_BASE_POINTS = {
    1: 10.0,  # 1st place → max 1.25 delta per skill
    2: 7.0,   # 2nd place → max 0.875 delta per skill
    3: 5.0,   # 3rd place → max 0.625 delta per skill
    "4+": 1.0 # 4th+ place → max 0.125 delta per skill
}

# Example outcomes (single skill, weight 2.0, total weight 2.0):
# 1st: +1.25 points → 5 tournaments = +6.25 points
# 2nd: +0.875 points → 7 tournaments = +6.1 points
# 3rd: +0.625 points → 10 tournaments = +6.25 points
# 4th+: +0.125 points → 50 tournaments = +6.25 points

# Example outcomes (multi-skill, speed weight 2.0, total weight 3.5):
# 1st: +0.71 speed points → 9 tournaments = +6.4 points
# 2nd: +0.50 speed points → 13 tournaments = +6.5 points
# 3rd: +0.36 speed points → 18 tournaments = +6.5 points
```

**Rationale**:
- **Noticeable progression**: 0.625-1.25 points per win feels rewarding
- **Medium-term motivation**: 5-10 tournaments needed for +3-6 points
- **Realistic growth**: From 80→85 takes ~6-8 tournaments (was 15-20)
- **Balanced**: 2.5x faster growth than original, still requires dedication

---

### 4️⃣ **Average Skill Level Calculation**

#### Current Formula

```python
def calculate_average_skill_level(skills: Dict[str, float]) -> float:
    """
    Calculate average from static baseline values
    """
    if not skills:
        return 0.0
    return sum(skills.values()) / len(skills)
```

#### NEW Formula (Dynamic)

```python
def calculate_average_skill_level_dynamic(skills: Dict[str, Dict]) -> float:
    """
    Calculate average from current_level values

    Args:
        skills: Dict of skill_name → skill_profile

    Returns:
        Average skill level (0-100)

    Example:
        skills = {
            "heading": {"current_level": 80.5, ...},
            "shooting": {"current_level": 102.3, ...},
            "crossing": {"current_level": 70.0, ...},
            "passing": {"current_level": 85.2, ...},
            "dribbling": {"current_level": 90.1, ...},
            "ball_control": {"current_level": 88.0, ...},
            "speed": {"current_level": 75.3, ...},
            "agility": {"current_level": 78.7, ...},
            "stamina": {"current_level": 82.0, ...}
        }

        average = (80.5 + 102.3 + 70.0 + 85.2 + 90.1 + 88.0 + 75.3 + 78.7 + 82.0) / 9
        average = 750.1 / 9 = 83.3
    """
    if not skills:
        return 0.0

    current_levels = [
        skill_data.get("current_level", skill_data.get("baseline", 0.0))
        for skill_data in skills.values()
    ]

    if not current_levels:
        return 0.0

    return round(sum(current_levels) / len(current_levels), 1)
```

---

### 5️⃣ **Skill Update Service**

#### Core Service

```python
# app/services/skill_progression_service.py

from sqlalchemy.orm import Session
from typing import Dict, Optional
from datetime import datetime, timezone

from ..models.license import UserLicense
from ..models.tournament_achievement import TournamentParticipation
from ..services.football_skill_service import FootballSkillService


class SkillProgressionService:
    """Service for applying tournament skill deltas to player profiles"""

    DELTA_MULTIPLIER = 0.125  # Scale down raw points to delta (12.5% - mid-range of 0.10-0.15)

    def __init__(self, db: Session):
        self.db = db
        self.skill_service = FootballSkillService(db)

    def apply_tournament_skill_deltas(
        self,
        user_license_id: int,
        tournament_participation_id: int
    ) -> Dict[str, Dict]:
        """
        Apply skill deltas from tournament to player profile

        Args:
            user_license_id: UserLicense ID
            tournament_participation_id: TournamentParticipation ID

        Returns:
            Updated skill profile
        """
        # Get tournament participation
        participation = self.db.query(TournamentParticipation).filter(
            TournamentParticipation.id == tournament_participation_id
        ).first()

        if not participation or not participation.skill_points_awarded:
            return {}

        # Get user license
        license = self.db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).first()

        if not license:
            raise ValueError(f"UserLicense {user_license_id} not found")

        # Ensure skills dict exists
        if not license.football_skills:
            license.football_skills = {}

        # Migrate old format if needed
        license.football_skills = self._ensure_new_format(license.football_skills)

        # Apply deltas
        for skill_name, raw_points in participation.skill_points_awarded.items():
            delta = self._calculate_delta(raw_points)
            license.football_skills = self._apply_skill_delta(
                license.football_skills,
                skill_name,
                delta
            )

        # Mark as modified
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(license, 'football_skills')

        self.db.commit()

        return license.football_skills

    def _ensure_new_format(self, skills: Dict) -> Dict:
        """Migrate old format to new format if needed"""
        if not skills:
            return {}

        # Check if already new format
        first_skill = next(iter(skills.values()), None)
        if isinstance(first_skill, dict) and "current_level" in first_skill:
            return skills  # Already new format

        # Migrate
        new_skills = {}
        for skill_name, value in skills.items():
            new_skills[skill_name] = {
                "current_level": float(value),
                "baseline": float(value),
                "total_delta": 0.0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "assessment_count": 0,
                "tournament_count": 0
            }
        return new_skills

    def _calculate_delta(self, raw_points: float) -> float:
        """Convert raw skill points to delta"""
        return round(raw_points * self.DELTA_MULTIPLIER, 2)

    def _apply_skill_delta(
        self,
        skills: Dict,
        skill_name: str,
        delta: float
    ) -> Dict:
        """Apply delta to a specific skill with 100.0 cap"""
        if skill_name not in skills:
            # Initialize new skill
            skills[skill_name] = {
                "current_level": 50.0,  # Default starting level
                "baseline": 50.0,
                "total_delta": 0.0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "assessment_count": 0,
                "tournament_count": 0
            }

        skill = skills[skill_name]
        new_level = skill["current_level"] + delta

        # Apply hard cap at 100.0
        skill["current_level"] = round(min(100.0, new_level), 1)
        skill["total_delta"] = round(skill["total_delta"] + delta, 2)
        skill["last_updated"] = datetime.now(timezone.utc).isoformat()
        skill["tournament_count"] = skill.get("tournament_count", 0) + 1

        return skills

    def get_skill_profile(self, user_license_id: int) -> Dict:
        """Get current skill profile"""
        license = self.db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).first()

        if not license or not license.football_skills:
            return {}

        return self._ensure_new_format(license.football_skills)

    def calculate_average_level(self, user_license_id: int) -> float:
        """Calculate average skill level"""
        skills = self.get_skill_profile(user_license_id)

        if not skills:
            return 0.0

        current_levels = [
            skill_data["current_level"]
            for skill_data in skills.values()
        ]

        return round(sum(current_levels) / len(current_levels), 1)
```

---

### 6️⃣ **Integration Points**

#### A) **Tournament Reward Distribution**

Modify `app/services/tournament/tournament_reward_orchestrator.py`:

```python
from ..skill_progression_service import SkillProgressionService

def distribute_tournament_rewards(tournament_id: int, db: Session):
    """
    Distribute rewards AND update skill profiles
    """
    # ... existing reward distribution logic ...

    # NEW: Apply skill deltas to player profiles
    skill_service = SkillProgressionService(db)

    for participation in participations:
        if participation.user_license_id and participation.skill_points_awarded:
            try:
                skill_service.apply_tournament_skill_deltas(
                    user_license_id=participation.user_license_id,
                    tournament_participation_id=participation.id
                )
            except Exception as e:
                logger.error(f"Failed to apply skill deltas for participation {participation.id}: {e}")
                # Continue with other participants
```

#### B) **Dashboard API**

New endpoint: `/api/v1/users/me/skill-profile`

```python
@router.get("/me/skill-profile")
def get_my_skill_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get player's dynamic skill profile
    """
    # Get active license
    license = db.query(UserLicense).filter(
        UserLicense.user_id == current_user.id,
        UserLicense.is_active == True
    ).first()

    if not license:
        raise HTTPException(404, "No active license found")

    skill_service = SkillProgressionService(db)

    return {
        "user_license_id": license.id,
        "specialization": license.specialization_type,
        "skills": skill_service.get_skill_profile(license.id),
        "average_level": skill_service.calculate_average_level(license.id),
        "total_assessments": skill_service.get_total_assessment_count(license.id),
        "total_tournaments": skill_service.get_total_tournament_count(license.id)
    }
```

---

### 7️⃣ **UI/UX Changes**

#### Player Dashboard Updates

**Before**:
```
Speed: 85 / 100
Agility: 80 / 100
Average: 81.7 / 100
```

**After**:
```
Speed: 85.3 / 100 🔥 ADVANCED ↑ +0.3 (from 85.0 baseline)
  └─ 🏆 2 tournament wins | 📊 5 assessments | Last: 5 days ago
Agility: 80.7 / 100 ⚡ INTERMEDIATE ↑ +0.7 (from 80.0 baseline)
  └─ 🏆 3 tournament wins | 📊 4 assessments | Last: 12 days ago

Ball Control: 96.8 / 100 💎 MASTER ↑ +3.8 (from 93.0 baseline)
  └─ 🏆 8 tournament wins | 📊 12 assessments | Last: 2 days ago
  └─ 🏅 Badge: "Ball Control Maestro" (95+ skill)

Average Skill Level: 87.6 / 100 🔥 ADVANCED ↑ +1.6
```

#### Skill History View

```
📈 Skill Progression: Speed

Current Level: 85.3 / 100
Baseline (Onboarding): 85.0 / 100
Total Growth: +0.3

Recent Updates:
• 2026-01-25: +0.3 from 🏆 NIKE Speed Test (1st place)
• 2026-01-20: +0.2 from 📊 Instructor Assessment
• 2026-01-15: +0.1 from 🏆 Sprint Challenge (2nd place)
```

---

### 8️⃣ **Balancing & Tuning**

#### Progression Curve Parameters

```python
# Tunable parameters
DELTA_MULTIPLIER = 0.125  # Base: 12.5% of raw points (range: 0.10-0.15, testable)

# Caps
MAX_SKILL_LEVEL = 100.0  # Hard cap at 100 (skill values cannot exceed 100)
MIN_SKILL_LEVEL = 0.0

# Decay mechanism for inactive players
DECAY_ENABLED = True
DECAY_RATE_PER_MONTH = 0.75  # -0.75 points per month (mid-range of 0.5-1.0)
DECAY_THRESHOLD_DAYS = 30  # Start decay after 30 days of inactivity
DECAY_APPLIES_TO = ["tournament_only"]  # Only skills gained from tournaments decay
DECAY_MIN_LEVEL = "baseline"  # Can't decay below baseline (onboarding value)

# Bonus multipliers (optional, disabled initially)
FIRST_PLACE_BONUS = 1.0  # Disabled (set to 1.0)
STREAK_BONUS = 1.0  # Disabled (set to 1.0)
```

#### Skill Display Tiers

Visual indicators for skill progression levels (max 100):

```python
def get_skill_display_tier(skill_level: float) -> str:
    """
    Determine visual tier for skill display

    Args:
        skill_level: Skill value (0-100)

    Returns:
        Tier identifier for UI rendering
    """
    if skill_level >= 95:
        return "MASTER"  # 💎 Master (near-perfect)
    elif skill_level >= 85:
        return "ADVANCED"  # 🔥 Advanced
    elif skill_level >= 70:
        return "INTERMEDIATE"  # ⚡ Intermediate
    elif skill_level >= 50:
        return "DEVELOPING"  # 📈 Developing
    else:
        return "BEGINNER"  # 🌱 Beginner
```

**Note**: Elite motivation and recognition will be handled through a separate **badge/achievement system** (not skill values).
Players at 95+ skill level can earn special badges for exceptional mastery.

#### Decay Mechanism

```python
def apply_skill_decay(
    skill_profile: Dict,
    last_tournament_date: datetime,
    current_date: datetime
) -> Dict:
    """
    Apply decay to skills based on inactivity

    Rules:
    1. Decay starts after 30 days of no tournament participation
    2. Decay rate: -0.75 points per month
    3. Only tournament-gained deltas decay (baseline preserved)
    4. Decay stops at baseline level

    Example:
        Baseline: 80.0
        Current: 85.3 (after 3 tournament wins)
        30 days inactive → Current: 84.55 (-0.75)
        60 days inactive → Current: 83.8 (-1.5)
        90 days inactive → Current: 83.05 (-2.25)
        Cannot go below 80.0 (baseline)
    """
    days_inactive = (current_date - last_tournament_date).days

    if days_inactive < DECAY_THRESHOLD_DAYS:
        return skill_profile  # No decay yet

    months_inactive = (days_inactive - DECAY_THRESHOLD_DAYS) / 30
    total_decay = months_inactive * DECAY_RATE_PER_MONTH

    for skill_name, skill_data in skill_profile.items():
        current = skill_data["current_level"]
        baseline = skill_data["baseline"]

        if current <= baseline:
            continue  # Already at or below baseline

        # Apply decay, but don't go below baseline
        new_level = max(baseline, current - total_decay)
        skill_data["current_level"] = round(new_level, 1)

        # Track decay amount
        actual_decay = current - new_level
        skill_data["total_decay_applied"] = skill_data.get("total_decay_applied", 0.0) + actual_decay

    return skill_profile
```

#### Testing Scenarios

```python
# Scenario 1: Consistent Winner (Single Skill Focus)
# Player wins 5 tournaments (1st place, speed skill, weight 2.0, total weight 2.0)
# Expected: +1.25 per tournament × 5 = +6.25 points
# Baseline: 80 → Result: 86.25 (rounded to 86.3)
# Timeline: ~5 months (1 tournament per month)

# Scenario 2: Steady Participant (Single Skill Focus)
# Player places 3rd in 10 tournaments (speed skill, weight 2.0, total weight 2.0)
# Expected: +0.625 per tournament × 10 = +6.25 points
# Baseline: 80 → Result: 86.25 (rounded to 86.3)
# Timeline: ~10 months

# Scenario 3: Mixed Performance (Multi-Skill Tournament)
# NIKE Speed Test: speed (2.0x) + agility (1.5x) = total weight 3.5
# 5× 1st place:
#   - Speed: +0.71 × 5 = +3.6
#   - Agility: +0.54 × 5 = +2.7
# 10× 3rd place:
#   - Speed: +0.36 × 10 = +3.6
#   - Agility: +0.27 × 10 = +2.7
# Baseline: speed 80, agility 75
# Result: speed 86.8, agility 79.4
# Timeline: ~15 tournaments over 1.5 years

# Scenario 4: Master Player with Decay
# Starting: speed 97.5 (baseline 85, delta +12.5 from 20+ tournaments)
# Becomes inactive for 3 months (90 days)
# Decay: -0.75 × 2 months (after 30-day threshold) = -1.5
# Result: speed 96.0
# Returns and wins 1st place (+1.25) → speed 97.25
# Still in MASTER tier (95+), maintains elite status

# Scenario 5: Skill Cap Test
# Starting: speed 98.0 (exceptional player, MASTER tier)
# Wins 1st place three times (+1.25 × 3 = +3.75)
# Expected: 98.0 + 3.75 = 101.75 → Capped at 100.0
# Result: speed 100.0 (MASTER tier, capped at maximum)
# Player earns special badge: "Speed Perfectionist" (reached 100)
```

---

### 9️⃣ **Migration Plan**

#### Phase 1: Data Migration (Week 1)

1. ✅ Add `SkillProgressionService`
2. ✅ Create migration script for existing `football_skills` JSONB
3. ✅ Add backward compatibility for old format
4. ✅ Test migration on dev database

#### Phase 2: Historical Backfill (Week 1-2)

**Goal**: Recalculate skill deltas from existing tournament participations to create accurate historical progression.

```python
# scripts/backfill_skill_progression.py

"""
Backfill historical tournament skill deltas into player profiles

This script:
1. Fetches all completed tournaments with reward_config
2. For each tournament participation, recalculates skill deltas
3. Applies deltas to UserLicense.football_skills in chronological order
4. Preserves baseline values from onboarding
5. Creates complete historical progression timeline
"""

from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Semester, TournamentParticipation, UserLicense
from app.schemas.reward_config import TournamentRewardConfig
from app.services.skill_progression_service import SkillProgressionService
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backfill_tournament_skill_progression():
    """
    Backfill skill progression from historical tournaments
    """
    db = next(get_db())
    skill_service = SkillProgressionService(db)

    # Get all completed tournaments with reward configs
    tournaments = db.query(Semester).filter(
        Semester.specialization_type.in_(['TOURNAMENT_SPEED', 'TOURNAMENT_STAMINA', 'TOURNAMENT_HYBRID']),
        Semester.reward_config.isnot(None),
        Semester.end_date < datetime.now(timezone.utc)  # Only completed
    ).order_by(Semester.end_date.asc()).all()  # Chronological order

    logger.info(f"Found {len(tournaments)} completed tournaments to backfill")

    # Track stats
    total_participations = 0
    total_skills_updated = 0
    errors = []

    for tournament in tournaments:
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing: {tournament.name} ({tournament.tournament_code})")
        logger.info(f"End Date: {tournament.end_date}")

        try:
            # Parse reward config
            config = TournamentRewardConfig(**tournament.reward_config)
            enabled_skills = [s.skill for s in config.enabled_skills]
            logger.info(f"Enabled skills: {enabled_skills}")

            # Get all participations
            participations = db.query(TournamentParticipation).filter(
                TournamentParticipation.semester_id == tournament.id
            ).all()

            logger.info(f"Found {len(participations)} participations")

            for participation in participations:
                if not participation.skill_points_awarded:
                    continue

                total_participations += 1

                # Get user license
                if not participation.user_license_id:
                    logger.warning(f"  Participation {participation.id} has no user_license_id, skipping")
                    continue

                try:
                    # Apply skill deltas (this handles migration + delta calculation)
                    updated_skills = skill_service.apply_tournament_skill_deltas(
                        user_license_id=participation.user_license_id,
                        tournament_participation_id=participation.id
                    )

                    skills_changed = len(participation.skill_points_awarded)
                    total_skills_updated += skills_changed

                    logger.info(
                        f"  ✓ User {participation.user_id}: "
                        f"Updated {skills_changed} skills from placement {participation.placement}"
                    )

                except Exception as e:
                    error_msg = f"Failed to apply deltas for participation {participation.id}: {e}"
                    logger.error(f"  ❌ {error_msg}")
                    errors.append(error_msg)

        except Exception as e:
            error_msg = f"Failed to process tournament {tournament.id}: {e}"
            logger.error(f"❌ {error_msg}")
            errors.append(error_msg)

    # Summary
    logger.info(f"\n{'='*80}")
    logger.info("BACKFILL COMPLETE")
    logger.info(f"{'='*80}")
    logger.info(f"Tournaments processed: {len(tournaments)}")
    logger.info(f"Participations processed: {total_participations}")
    logger.info(f"Total skill updates: {total_skills_updated}")
    logger.info(f"Errors: {len(errors)}")

    if errors:
        logger.error("\nErrors encountered:")
        for error in errors[:10]:  # Show first 10
            logger.error(f"  - {error}")

    db.close()


if __name__ == "__main__":
    backfill_tournament_skill_progression()
```

**Backfill Execution Plan**:
1. Run on staging database first
2. Verify skill progression looks correct for sample users
3. Export before/after snapshots for validation
4. Run on production during low-traffic window
5. Monitor for anomalies

**Validation Queries**:
```sql
-- Check skill progression after backfill
SELECT
    u.email,
    ul.football_skills->'speed'->>'current_level' as speed_current,
    ul.football_skills->'speed'->>'baseline' as speed_baseline,
    ul.football_skills->'speed'->>'total_delta' as speed_delta,
    ul.football_skills->'speed'->>'tournament_count' as tournament_count
FROM user_licenses ul
JOIN users u ON ul.user_id = u.id
WHERE ul.football_skills ? 'speed'
ORDER BY (ul.football_skills->'speed'->>'tournament_count')::int DESC
LIMIT 10;
```

#### Phase 3: Integration (Week 2)

1. ✅ Integrate with tournament reward distribution
2. ✅ Add API endpoints for skill profile
3. ✅ Update dashboard UI components
4. ✅ Add skill progression history view
5. ✅ Add elite tier visual indicators

#### Phase 4: Testing & Tuning (Week 3)

1. ✅ Test with real tournament data
2. ✅ Verify backfilled data accuracy
3. ✅ Tune `DELTA_MULTIPLIER` based on feedback (range: 0.10-0.15)
4. ✅ Test decay mechanism with simulated inactivity
5. ✅ Add admin tools for manual skill adjustments
6. ✅ Document for admins and instructors

#### Phase 5: Production Launch (Week 4)

1. ✅ Deploy to production
2. ✅ Monitor skill progression metrics
3. ✅ Collect user feedback
4. ✅ Iterate based on data
5. ✅ Enable decay mechanism after 1 month of monitoring

---

### 🔟 **Admin Tools**

#### Skill Adjustment Interface

```python
@router.post("/admin/users/{user_id}/skills/adjust")
def adjust_user_skill(
    user_id: int,
    skill_name: str,
    adjustment: float,
    reason: str,
    current_admin: User = Depends(require_admin)
):
    """
    Manual skill adjustment by admin

    Use cases:
    - Correct migration errors
    - Apply instructor feedback
    - Compensate for system bugs
    """
    # Apply adjustment
    # Log in audit table
    pass
```

---

## 📊 Success Metrics

### Engagement Metrics
- **Skill Progression Rate**: Average delta per tournament
- **Player Retention**: Players with 5+ tournaments in 3 months
- **Motivation Score**: Player survey responses

### System Health
- **Average Skill Level Growth**: Should be +0.5-1.0 per month
- **Profile Update Frequency**: Tournament → profile lag < 5 minutes
- **Data Consistency**: 100% of tournament rewards applied to profiles

---

## 🚀 Next Steps

### Immediate Actions (This Week)
1. ✅ Review and approve this technical plan
2. ✅ Create `SkillProgressionService` class
3. ✅ Write migration script
4. ✅ Add unit tests

### Short-Term (Next 2 Weeks)
1. Integrate with tournament rewards
2. Update dashboard UI
3. Deploy to staging

### Long-Term (Next Month)
1. Add skill progression analytics dashboard
2. Implement decay mechanism (optional)
3. Add AI-powered skill recommendations

---

## 🤔 Design Decisions (Resolved)

1. **Skill Caps**: ✅ **APPROVED**
   - **Hard cap at 100** (skill values cannot exceed 100)
   - Visual tiers: BEGINNER (0-49), DEVELOPING (50-69), INTERMEDIATE (70-84), ADVANCED (85-94), MASTER (95-100)
   - **Elite motivation**: Handled through separate **badge/achievement system** (not skill values)
   - Special badges awarded for reaching 95+ (e.g., "Speed Master", "Ball Control Perfectionist")

2. **Decay Mechanism**: ✅ **APPROVED**
   - Enabled after 30 days of inactivity
   - Rate: -0.75 points per month (mid-range of 0.5-1.0)
   - Only affects tournament-gained deltas, baseline preserved
   - Cannot decay below baseline value

3. **Delta Multiplier**: ✅ **APPROVED**
   - Set to 0.125 (12.5% of raw points)
   - Testable range: 0.10-0.15
   - Results in noticeable but balanced progression
   - ~6-8 tournaments for +5 skill points

4. **Historical Backfill**: ✅ **APPROVED**
   - Recalculate all past tournament participations
   - Apply deltas in chronological order
   - Create complete historical progression timeline
   - Validate before/after with SQL queries

5. **Assessment vs Tournament Priority**: ✅ **CONFIRMED**
   - Both apply independently (additive)
   - Instructor assessments: Manual, subjective
   - Tournament deltas: Automated, performance-based
   - No conflicts, complementary systems

6. **Multi-Specialization**: ✅ **CONFIRMED**
   - Separate skill profiles per license (UserLicense.football_skills)
   - LFA Player license has different skills than LFA Coach license
   - Correct architecture already in place

---

## 📚 Documentation Needed

1. **Admin Guide**: How to interpret skill progression
2. **User Guide**: What skill deltas mean
3. **API Documentation**: New endpoints
4. **Migration Guide**: For existing data

---

## 📋 Implementation Checklist

### Pre-Implementation ✅ COMPLETE
- [x] Technical plan approved
- [x] Delta multiplier finalized (0.125, range 0.10-0.15)
- [x] Skill cap defined (100 max, no values above 100)
- [x] Visual tiers defined (BEGINNER → DEVELOPING → INTERMEDIATE → ADVANCED → MASTER)
- [x] Elite motivation via badge system (separate from skill values)
- [x] Decay mechanism specified (30 days, -0.75/month)
- [x] Backfill strategy documented
- [x] Testing scenarios defined
- [x] Migration plan established

### Phase 1: Core Service (Week 1) ⏳ PENDING
- [ ] Create `SkillProgressionService` class
- [ ] Implement `_ensure_new_format()` migration
- [ ] Implement `apply_tournament_skill_deltas()`
- [ ] Implement `apply_skill_decay()`
- [ ] Implement `get_skill_display_tier()`
- [ ] Add unit tests (90%+ coverage)
- [ ] Test on dev database

### Phase 2: Backfill (Week 1-2) ⏳ PENDING
- [ ] Create `scripts/backfill_skill_progression.py`
- [ ] Run on staging database
- [ ] Validate sample user progressions
- [ ] Export before/after snapshots
- [ ] Run on production (low-traffic window)
- [ ] Verify with SQL queries

### Phase 3: Integration (Week 2) ⏳ PENDING
- [ ] Integrate with `tournament_reward_orchestrator.py`
- [ ] Add API endpoint `/api/v1/users/me/skill-profile`
- [ ] Update dashboard UI with tier indicators (BEGINNER → MASTER)
- [ ] Add skill progression history view
- [ ] Add "last active" timestamps
- [ ] Add skill cap enforcement (max 100.0)

### Phase 4: Testing & Tuning (Week 3) ⏳ PENDING
- [ ] Test all 5 testing scenarios
- [ ] Verify backfilled data accuracy
- [ ] Tune delta multiplier if needed
- [ ] Test decay with simulated dates
- [ ] Add admin skill adjustment tool
- [ ] Create admin documentation

### Phase 5: Production Launch (Week 4) ⏳ PENDING
- [ ] Deploy to production
- [ ] Monitor skill progression metrics
- [ ] Collect user feedback
- [ ] Enable decay after 1 month
- [ ] Create player-facing documentation

---

**Status**: ✅ **READY FOR IMPLEMENTATION**
**All Parameters Finalized**:
- Delta: 0.125 (12.5% of raw points)
- Cap: 100 (hard maximum, no values above 100)
- Tiers: 5 visual levels (BEGINNER → MASTER)
- Elite badges: Separate achievement system for 95+ skills
- Decay: 30 days → -0.75/month
- Backfill: Complete historical recalculation

**Next Step**: Begin Phase 1 - Create SkillProgressionService
**Expected Timeline**: 4-5 weeks to production
