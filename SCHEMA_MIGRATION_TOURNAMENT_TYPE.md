# Schema Migration Guide: tournament_type_id

> **Problem**: `AttributeError: property 'tournament_type_id' of 'Semester' object has no setter`
> **Root Cause**: P2 refactoring moved `tournament_type_id` from Semester column to TournamentConfiguration table
> **Impact**: 19 tests blocked (3 files affected)
> **Solution**: Create TournamentConfiguration objects instead of setting property directly

---

## 🏗️ Architecture Changes (P2 Refactoring)

### BEFORE (P1 - Direct Column)

```python
class Semester(Base):
    __tablename__ = "semesters"

    # Direct column (DEPRECATED)
    tournament_type_id = Column(Integer, ForeignKey('tournament_types.id'))
    participant_type = Column(String(50))
    max_players = Column(Integer)
    # ... other config fields
```

**Fixture pattern (OLD - BROKEN)**:
```python
tournament = Semester(
    code="LEAGUE-2025",
    name="League Tournament",
    tournament_type_id=league_type.id,  # ❌ NO SETTER!
    participant_type="INDIVIDUAL",
    max_players=16,
    # ... other fields
)
db.add(tournament)
db.commit()
```

---

### AFTER (P2 - Separate Configuration Table)

```python
# Semester model (app/models/semester.py)
class Semester(Base):
    __tablename__ = "semesters"

    # Relationship to configuration
    tournament_config_obj = relationship(
        "TournamentConfiguration",
        uselist=False,
        back_populates="tournament",
        cascade="all, delete-orphan"
    )

    # Read-only property (backward compatibility)
    @property
    def tournament_type_id(self) -> int:
        """Backward compatible property"""
        if self.tournament_config_obj:
            return self.tournament_config_obj.tournament_type_id
        return None
```

```python
# TournamentConfiguration model (app/models/tournament_configuration.py)
class TournamentConfiguration(Base):
    __tablename__ = "tournament_configurations"

    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey('semesters.id'), unique=True, nullable=False)

    # Actual columns (writable)
    tournament_type_id = Column(Integer, ForeignKey('tournament_types.id'), nullable=True)
    participant_type = Column(String(50), default="INDIVIDUAL")
    max_players = Column(Integer, nullable=True)
    # ... all other config fields
```

---

## ✅ Migration Pattern (3 Options)

### Option 1: Nested Object (RECOMMENDED)

**Pros**: Single `db.add()`, clean, atomic
**Cons**: Requires all config in one place

```python
from app.models.semester import Semester
from app.models.tournament_configuration import TournamentConfiguration

tournament = Semester(
    code="LEAGUE-2025",
    name="League Tournament",
    start_date=date.today(),
    end_date=date.today() + timedelta(days=30),
    status=SemesterStatus.READY_FOR_ENROLLMENT,
    tournament_status="ENROLLMENT_OPEN",
    specialization_type="LFA_FOOTBALL_PLAYER",
    age_group="YOUTH",
    enrollment_cost=500,

    # ✅ NEW: Create config via relationship
    tournament_config_obj=TournamentConfiguration(
        tournament_type_id=league_type.id,  # ✅ This works!
        participant_type="INDIVIDUAL",
        max_players=16,
        is_multi_day=False,
        match_duration_minutes=90,
        break_duration_minutes=15,
        parallel_fields=2,
        scoring_type="HEAD_TO_HEAD",
        # ... other config fields
    )
)
db.add(tournament)
db.commit()
```

---

### Option 2: Separate Creation (Good for complex fixtures)

**Pros**: Clear separation, easier to debug
**Cons**: Requires flush() to get tournament.id

```python
# Step 1: Create tournament
tournament = Semester(
    code="LEAGUE-2025",
    name="League Tournament",
    start_date=date.today(),
    end_date=date.today() + timedelta(days=30),
    status=SemesterStatus.READY_FOR_ENROLLMENT,
    tournament_status="ENROLLMENT_OPEN",
    # ... other semester fields
)
db.add(tournament)
db.flush()  # ✅ Get tournament.id without committing

# Step 2: Create configuration
tournament_config = TournamentConfiguration(
    semester_id=tournament.id,  # ✅ Now we have the ID
    tournament_type_id=league_type.id,
    participant_type="INDIVIDUAL",
    max_players=16,
    # ... other config fields
)
db.add(tournament_config)
db.commit()  # ✅ Commit both together
```

---

### Option 3: Assignment After Creation

**Pros**: Mimics old pattern most closely
**Cons**: Requires flush(), slightly verbose

```python
# Create tournament
tournament = Semester(
    code="LEAGUE-2025",
    name="League Tournament",
    # ... other semester fields
)
db.add(tournament)
db.flush()

# Create and assign configuration
tournament.tournament_config_obj = TournamentConfiguration(
    semester_id=tournament.id,
    tournament_type_id=league_type.id,
    participant_type="INDIVIDUAL",
    max_players=16,
    # ... other config fields
)
db.commit()
```

---

## 📋 Migration Checklist

For each affected test fixture:

1. ✅ **Identify old pattern**: Look for `Semester(tournament_type_id=...)`
2. ✅ **Check required config fields**:
   - `tournament_type_id` (nullable, for HEAD_TO_HEAD)
   - `participant_type` (default="INDIVIDUAL")
   - `max_players` (nullable)
   - `match_duration_minutes`, `break_duration_minutes`, `parallel_fields`
   - `scoring_type`, `measurement_unit`, `ranking_direction`
   - `number_of_rounds` (for some formats)
3. ✅ **Choose migration option**: Usually Option 1 (nested) is cleanest
4. ✅ **Update fixture code**: Replace direct assignment with relationship
5. ✅ **Test fixture creation**: Verify no errors
6. ✅ **Update assertions**: If tests check `tournament.tournament_type_id`, they should still work (property)

---

## 🎯 Field Mapping Reference

### Semester Fields (kept in semesters table)

```python
# Tournament information
code, name, start_date, end_date
status, tournament_status
specialization_type, age_group
theme, focus_description
campus_id, location_id
master_instructor_id
enrollment_cost
created_at, updated_at
```

### TournamentConfiguration Fields (moved to tournament_configurations table)

```python
# Tournament type & format
tournament_type_id          # FK to tournament_types (League, Swiss, Knockout, etc.)

# Participant configuration
participant_type            # "INDIVIDUAL", "TEAM", "MIXED"
is_multi_day               # True/False
max_players                # Integer or NULL

# Schedule configuration
match_duration_minutes     # 90, 45, etc.
break_duration_minutes     # 15, 10, etc.
parallel_fields            # 1, 2, 3, etc.

# Scoring configuration
scoring_type               # "HEAD_TO_HEAD", "TIME_BASED", "SCORE_BASED", etc.
measurement_unit           # "SECONDS", "POINTS", "GOALS", etc.
ranking_direction          # "ASC" (lower better), "DESC" (higher better)
number_of_rounds           # For SWISS, LEAGUE formats

# Session generation tracking
assignment_type            # "MANUAL", "AUTO"
sessions_generated         # True/False
sessions_generated_at      # DateTime
enrollment_snapshot        # JSONB
```

---

## 🔍 Common Patterns in Tests

### Pattern 1: HEAD_TO_HEAD Tournament

**OLD**:
```python
tournament = Semester(
    tournament_type_id=league_type.id,
    scoring_type="HEAD_TO_HEAD",
    max_players=16,
    ...
)
```

**NEW**:
```python
tournament = Semester(
    ...,
    tournament_config_obj=TournamentConfiguration(
        tournament_type_id=league_type.id,
        scoring_type="HEAD_TO_HEAD",
        participant_type="INDIVIDUAL",
        max_players=16,
        match_duration_minutes=90,
        break_duration_minutes=15,
        parallel_fields=2,
    )
)
```

---

### Pattern 2: INDIVIDUAL_RANKING Tournament

**OLD**:
```python
tournament = Semester(
    tournament_type_id=None,  # No type for IR
    scoring_type="TIME_BASED",
    measurement_unit="SECONDS",
    ranking_direction="ASC",
    ...
)
```

**NEW**:
```python
tournament = Semester(
    ...,
    tournament_config_obj=TournamentConfiguration(
        tournament_type_id=None,  # ✅ Still NULL for IR
        scoring_type="TIME_BASED",
        measurement_unit="SECONDS",
        ranking_direction="ASC",
        participant_type="INDIVIDUAL",
    )
)
```

---

### Pattern 3: Tournament WITHOUT Configuration (Simple Case)

Some tests might not need tournament config at all:

**OK to omit**:
```python
# Simple tournament (no HEAD_TO_HEAD logic, no session generation)
tournament = Semester(
    code="SIMPLE-2025",
    name="Simple Tournament",
    start_date=date.today(),
    end_date=date.today() + timedelta(days=30),
    status=SemesterStatus.READY_FOR_ENROLLMENT,
    tournament_status="ENROLLMENT_OPEN",
    # No tournament_config_obj needed
)
```

**When config is required**:
- Test checks `tournament.tournament_type_id`
- Test calls session generation endpoints
- Test validates HEAD_TO_HEAD logic
- Test checks scoring/ranking

---

## 🚨 Common Errors & Fixes

### Error 1: No setter for tournament_type_id

```python
# ❌ BROKEN
tournament.tournament_type_id = league_type.id

# ✅ FIXED
tournament.tournament_config_obj = TournamentConfiguration(
    tournament_type_id=league_type.id
)
```

---

### Error 2: Missing semester_id in TournamentConfiguration

```python
# ❌ BROKEN (if using separate creation)
config = TournamentConfiguration(
    tournament_type_id=league_type.id
)
# Missing semester_id!

# ✅ FIXED
db.add(tournament)
db.flush()  # Get tournament.id
config = TournamentConfiguration(
    semester_id=tournament.id,  # ✅ Now set
    tournament_type_id=league_type.id
)
```

---

### Error 3: Unique constraint violation

```python
# ❌ BROKEN (creating 2 configs for same tournament)
config1 = TournamentConfiguration(semester_id=tournament.id, ...)
config2 = TournamentConfiguration(semester_id=tournament.id, ...)  # ❌ Duplicate!

# ✅ FIXED (1:1 relationship)
# Only create ONE config per tournament
tournament.tournament_config_obj = TournamentConfiguration(...)
```

---

## 📊 Migration Progress Tracking

### Files to Update:

- [ ] `app/tests/test_tournament_session_generation_api.py` (~30 fixtures)
- [ ] `app/tests/test_critical_flows.py` (~10 fixtures)
- [ ] `app/tests/test_tournament_cancellation_e2e.py` (~10 fixtures)

**Total**: ~50 fixture updates

---

### Verification Steps:

1. ✅ No `AttributeError: property 'tournament_type_id' of 'Semester' object has no setter`
2. ✅ Test can read `tournament.tournament_type_id` (property works)
3. ✅ Test can create fixtures without errors
4. ✅ Test assertions pass

---

## 💡 Pro Tips

1. **Import TournamentConfiguration**: Don't forget!
   ```python
   from app.models.tournament_configuration import TournamentConfiguration
   ```

2. **Use Option 1 (nested)** for most cases - cleanest and most readable

3. **Check if config is needed**: Not all tests need `tournament_config_obj`

4. **Copy-paste config template**: Most HEAD_TO_HEAD configs are similar
   ```python
   tournament_config_obj=TournamentConfiguration(
       tournament_type_id=X,  # Only thing that changes
       participant_type="INDIVIDUAL",
       max_players=16,
       match_duration_minutes=90,
       break_duration_minutes=15,
       parallel_fields=2,
       scoring_type="HEAD_TO_HEAD",
   )
   ```

5. **Test incrementally**: Fix one file at a time, run tests after each

---

**Created**: 2026-02-23
**Author**: Schema Refactoring Sprint
**Status**: ✅ READY FOR USE
**Next**: Apply pattern to 50 fixtures across 3 test files
