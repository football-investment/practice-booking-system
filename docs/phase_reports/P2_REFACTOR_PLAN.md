# P2 Refactoring Plan: Separate Tournament Configuration

**Status**: 📋 Planning Phase
**Priority**: Medium
**Estimated Effort**: 6-8 hours
**Depends On**: P0 ✅, P1 ✅

---

## Goal

Separate tournament **configuration** from tournament **information** by creating a dedicated `TournamentConfiguration` table. This achieves full layer separation and moves all tournament-specific business logic out of the `Semester` model.

---

## Current State (After P1)

### Semester Model Structure

```
┌─────────────────────────────────────────────┐
│  SEMESTER MODEL (semesters table)           │
├─────────────────────────────────────────────┤
│  ✅ Tournament Information:                 │
│     - code, name, dates                     │
│     - campus_id, location_id                │
│     - specialization_type, age_group        │
│     - theme, focus_description              │
├─────────────────────────────────────────────┤
│  ⚠️  Tournament Configuration (TO MOVE):    │
│     - tournament_type_id (FK)               │
│     - participant_type                      │
│     - is_multi_day                          │
│     - match_duration_minutes                │
│     - break_duration_minutes                │
│     - parallel_fields                       │
│     - scoring_type                          │
│     - measurement_unit                      │
│     - ranking_direction                     │
│     - number_of_rounds                      │
│     - assignment_type                       │
│     - max_players                           │
│     - sessions_generated                    │
│     - sessions_generated_at                 │
│     - enrollment_snapshot                   │
├─────────────────────────────────────────────┤
│  ✅ Game Configuration:                     │
│     - game_preset_id (FK)                   │
│     - game_config (JSONB)                   │
│     - game_config_overrides (JSONB)         │
├─────────────────────────────────────────────┤
│  ✅ Reward Configuration (P1):              │
│     - reward_config_obj (relationship)      │
│     - TournamentRewardConfig table (1:1)    │
└─────────────────────────────────────────────┘
```

---

## Target State (After P2)

### Clean Architecture Layers

```
┌─────────────────────────────────────────────┐
│  SEMESTER (Tournament Information)          │
│  - code, name, dates                        │
│  - campus_id, location_id                   │
│  - specialization_type, age_group           │
│  - theme, status                            │
├─────────────────────────────────────────────┤
│  TOURNAMENT_CONFIGURATION (NEW)             │
│  - tournament_type_id (FK)                  │
│  - participant_type, max_players            │
│  - schedule config (match/break duration)   │
│  - scoring config (type, unit, direction)   │
│  - session generation tracking              │
├─────────────────────────────────────────────┤
│  GAME_CONFIGURATION (Stays in Semester)     │
│  - game_preset_id, game_config              │
├─────────────────────────────────────────────┤
│  REWARD_CONFIGURATION (P1 - Separate)       │
│  - TournamentRewardConfig table             │
└─────────────────────────────────────────────┘
```

---

## Detailed Design

### 1. New Model: TournamentConfiguration

```python
class TournamentConfiguration(Base):
    __tablename__ = "tournament_configurations"

    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey('semesters.id'), unique=True, nullable=False)

    # Tournament Type & Participants
    tournament_type_id = Column(Integer, ForeignKey('tournament_types.id'), nullable=True)
    participant_type = Column(String(50), default="INDIVIDUAL")
    is_multi_day = Column(Boolean, default=False)
    max_players = Column(Integer, nullable=True)

    # Schedule Configuration
    match_duration_minutes = Column(Integer, nullable=True)
    break_duration_minutes = Column(Integer, nullable=True)
    parallel_fields = Column(Integer, default=1)

    # Scoring Configuration (INDIVIDUAL_RANKING only)
    scoring_type = Column(String(50), default="PLACEMENT")
    measurement_unit = Column(String(50), nullable=True)
    ranking_direction = Column(String(10), nullable=True)
    number_of_rounds = Column(Integer, default=1)

    # Assignment Configuration
    assignment_type = Column(String(30), nullable=True)

    # Session Generation Tracking
    sessions_generated = Column(Boolean, default=False)
    sessions_generated_at = Column(DateTime, nullable=True)
    enrollment_snapshot = Column(JSONB, nullable=True)

    # Audit timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    tournament = relationship("Semester", back_populates="tournament_config_obj")
    tournament_type = relationship("TournamentType", foreign_keys=[tournament_type_id])
```

---

### 2. Migration Strategy

#### Migration P2.1: Create TournamentConfiguration Table

```python
def upgrade():
    # 1. Create tournament_configurations table
    op.create_table(
        'tournament_configurations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('semester_id', sa.Integer(), nullable=False),
        sa.Column('tournament_type_id', sa.Integer(), nullable=True),
        sa.Column('participant_type', sa.String(50), server_default='INDIVIDUAL'),
        sa.Column('is_multi_day', sa.Boolean(), server_default='false'),
        sa.Column('max_players', sa.Integer(), nullable=True),
        sa.Column('match_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('break_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('parallel_fields', sa.Integer(), server_default='1'),
        sa.Column('scoring_type', sa.String(50), server_default='PLACEMENT'),
        sa.Column('measurement_unit', sa.String(50), nullable=True),
        sa.Column('ranking_direction', sa.String(10), nullable=True),
        sa.Column('number_of_rounds', sa.Integer(), server_default='1'),
        sa.Column('assignment_type', sa.String(30), nullable=True),
        sa.Column('sessions_generated', sa.Boolean(), server_default='false'),
        sa.Column('sessions_generated_at', sa.DateTime(), nullable=True),
        sa.Column('enrollment_snapshot', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tournament_type_id'], ['tournament_types.id']),
        sa.UniqueConstraint('semester_id')
    )

    # 2. Migrate data from semesters table
    op.execute("""
        INSERT INTO tournament_configurations (
            semester_id, tournament_type_id, participant_type, is_multi_day,
            max_players, match_duration_minutes, break_duration_minutes,
            parallel_fields, scoring_type, measurement_unit, ranking_direction,
            number_of_rounds, assignment_type, sessions_generated,
            sessions_generated_at, enrollment_snapshot, created_at
        )
        SELECT
            id, tournament_type_id,
            COALESCE(participant_type, 'INDIVIDUAL'),
            COALESCE(is_multi_day, false),
            max_players, match_duration_minutes, break_duration_minutes,
            COALESCE(parallel_fields, 1),
            COALESCE(scoring_type, 'PLACEMENT'),
            measurement_unit, ranking_direction,
            COALESCE(number_of_rounds, 1),
            assignment_type,
            COALESCE(sessions_generated, false),
            sessions_generated_at, enrollment_snapshot,
            COALESCE(created_at, now())
        FROM semesters
        WHERE tournament_type_id IS NOT NULL
           OR max_players IS NOT NULL
           OR sessions_generated = true
    """)

    # 3. Drop old columns from semesters
    op.drop_column('semesters', 'tournament_type_id')
    op.drop_column('semesters', 'participant_type')
    op.drop_column('semesters', 'is_multi_day')
    op.drop_column('semesters', 'max_players')
    op.drop_column('semesters', 'match_duration_minutes')
    op.drop_column('semesters', 'break_duration_minutes')
    op.drop_column('semesters', 'parallel_fields')
    op.drop_column('semesters', 'scoring_type')
    op.drop_column('semesters', 'measurement_unit')
    op.drop_column('semesters', 'ranking_direction')
    op.drop_column('semesters', 'number_of_rounds')
    op.drop_column('semesters', 'assignment_type')
    op.drop_column('semesters', 'sessions_generated')
    op.drop_column('semesters', 'sessions_generated_at')
    op.drop_column('semesters', 'enrollment_snapshot')
```

---

### 3. Backward Compatibility

#### Semester Model Updates

```python
class Semester(Base):
    # Tournament configuration (P2: separate table)
    tournament_config_obj = relationship(
        "TournamentConfiguration",
        uselist=False,
        back_populates="tournament",
        cascade="all, delete-orphan"
    )

    # Backward-compatible properties
    @property
    def tournament_type_id(self) -> Optional[int]:
        if self.tournament_config_obj:
            return self.tournament_config_obj.tournament_type_id
        return None

    @property
    def max_players(self) -> Optional[int]:
        if self.tournament_config_obj:
            return self.tournament_config_obj.max_players
        return None

    @property
    def participant_type(self) -> str:
        if self.tournament_config_obj:
            return self.tournament_config_obj.participant_type
        return "INDIVIDUAL"

    # ... (all other config fields as properties)

    @property
    def format(self) -> str:
        """
        Format derived from tournament_type (via config relationship)
        """
        if self.tournament_config_obj and self.tournament_config_obj.tournament_type_id:
            tt_config = self.tournament_config_obj.tournament_type
            if tt_config:
                return tt_config.format

        # Fallback to game_preset
        if self.game_preset_id and self.game_preset:
            format_config = self.game_preset.game_config.get('format_config', {})
            if format_config:
                return list(format_config.keys())[0]

        return "INDIVIDUAL_RANKING"
```

---

### 4. Code Updates Required

#### Files to Update:

1. **app/models/tournament_configuration.py** (NEW)
   - Create TournamentConfiguration model

2. **app/models/semester.py**
   - Remove configuration columns
   - Add `tournament_config_obj` relationship
   - Add backward-compatible `@property` methods for all config fields

3. **app/models/__init__.py**
   - Import TournamentConfiguration

4. **app/services/sandbox_test_orchestrator.py**
   - Create separate TournamentConfiguration when creating tournaments

5. **app/api/api_v1/endpoints/tournaments/generator.py** (if exists)
   - Create TournamentConfiguration separately

6. **app/api/api_v1/endpoints/tournaments/lifecycle.py**
   - Update configuration endpoints to use new table

---

### 5. Benefits

✅ **Clean Separation of Concerns**
- Tournament Information (Semester): What & When
- Tournament Configuration (TournamentConfiguration): How
- Game Configuration (game_config): Simulation Rules
- Reward Configuration (TournamentRewardConfig): Rewards

✅ **Auditability**
- Track when configuration changes (`created_at`, `updated_at`)
- Enable versioning in future

✅ **Flexibility**
- Configuration can be changed without affecting tournament info
- Future: Share configurations across tournaments

✅ **Data Integrity**
- 1:1 relationship enforced
- Cascade delete (config removed when tournament deleted)

---

## Testing Checklist

- [ ] Migration runs without errors
- [ ] Data migration successful (all tournaments with config migrated)
- [ ] New table created, old columns removed
- [ ] Models import correctly
- [ ] Backward-compatible properties work
- [ ] `semester.format` still derives from tournament_type
- [ ] Sandbox orchestrator creates separate config
- [ ] API endpoints use new table
- [ ] Existing tournaments load correctly

---

## Risk Assessment

### Low Risk ✅
- Similar pattern to P1 (proven successful)
- Backward compatibility via properties
- No API contract changes
- Migration is reversible

### Mitigation
- Comprehensive testing before merge
- Rollback plan in place
- Property-based access ensures transparency

---

## Rollback Plan

```bash
# Downgrade migration
alembic downgrade -1

# This will:
# 1. Re-add configuration columns to semesters
# 2. Migrate data back from tournament_configurations
# 3. Drop tournament_configurations table
```

---

## Timeline

1. **Phase 1**: Model & Migration (2-3 hours)
   - Create TournamentConfiguration model
   - Write migration P2.1
   - Add relationship to Semester

2. **Phase 2**: Backward Compatibility (1-2 hours)
   - Add @property methods to Semester
   - Update format derivation logic

3. **Phase 3**: Code Updates (2-3 hours)
   - Update orchestrators
   - Update API endpoints (if any)

4. **Phase 4**: Testing (1-2 hours)
   - Run migration locally
   - Test all properties
   - Test sandbox creation
   - Verify data integrity

---

## Next Steps After P2

### P3: Separate Game Configuration (Optional)
- Create `game_configurations` table
- Move `game_config`, `game_config_overrides` from Semester
- Enable versioning for game config changes

---

**Status**: ✅ READY FOR IMPLEMENTATION
**Prerequisite**: P0 ✅, P1 ✅ merged to main

