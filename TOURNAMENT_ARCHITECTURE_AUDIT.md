# Tournament Architektúra Audit & Refaktorálási Javaslatok

**Dátum:** 2026-01-28
**Státusz:** 🔴 Refaktorálásra szorul
**Prioritás:** P0-P1 (Azonnal), P2-P3 (Középtáv)

---

## 📋 Összefoglaló

Az audit során **jelentős architektúrális problémákat** azonosítottunk a tournament létrehozási folyamatban:

### 🔴 Fő Problémák

1. **Nincs clean separation of concerns** - Minden a `Semester` model-ben keveredik
2. **Redundáns adattárolás** - `format`, `tournament_type`, skill mappings duplikálva
3. **Semantic confusion** - `game_config` vs `reward_config` átfedés
4. **Deprecated mezők** - Régi string-based fields még használatban
5. **API contract hiányosságok** - Nincs `game_preset_id`, reward_config a request-ben

### ✅ Cél: 3 Tiszta Réteg

```
┌────────────────────────────────────────┐
│  TOURNAMENT INFORMATION LAYER          │  ← Helyszín, időpont, alap info
├────────────────────────────────────────┤
│  CONFIGURATION LAYER                   │  ← Format, max players, assignment
├────────────────────────────────────────┤
│  GAME CONFIGURATION LAYER              │  ← Skills, weights, game mechanics
│    ├─ Game Config (preset-based)       │
│    └─ Reward Config (separate!)        │
└────────────────────────────────────────┘
```

---

## 🔍 Részletes Elemzés

### 1. JELENLEGI ÁLLAPOT: Semester Model Overload

#### 1.1 Tournament Information Layer ✅ (Jó)

```python
# app/models/semester.py (lines 40-60)
class Semester(Base):
    code = Column(String, unique=True)
    name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    campus_id = Column(Integer, ForeignKey("campuses.id"))
    location_id = Column(Integer, ForeignKey("locations.id"))
    specialization_type = Column(Enum(SpecializationType))
    age_group = Column(String)
    theme = Column(String)
```

**Értékelés:** ✅ Tiszta, jól definiált réteg

---

#### 1.2 Configuration Layer ⚠️ (Részben problémás)

```python
# Jó mezők:
tournament_type_id = Column(Integer, ForeignKey("tournament_types.id"))
assignment_type = Column(String)
max_participants = Column(Integer)

# 🔴 PROBLÉMA 1: Redundáns format field
format = Column(String)  # HEAD_TO_HEAD vagy INDIVIDUAL_RANKING
# ↑ EZ DERIVED lehet tournament_type.format-ból!

# 🔴 PROBLÉMA 2: Deprecated string field
tournament_type = Column(String)  # "league", "knockout" - STRING!
# ↑ Van tournament_type_id (FK), ez felesleges!
```

**Értékelés:** ⚠️ Redundancia és deprecated fields

---

#### 1.3 Game Configuration Layer 🔴 (Súlyos keveredés)

```python
# Preset-based (ÚJ, JÓ):
game_preset_id = Column(Integer, ForeignKey("game_presets.id"))
game_config = Column(JSONB)
game_config_overrides = Column(JSONB)

# 🔴 PROBLÉMA 3: Reward config ITT van (rossz hely!)
reward_config = Column(JSONB)
reward_policy_name = Column(String)
reward_policy_snapshot = Column(JSONB)

# 🔴 PROBLÉMA 4: Skill mappings relationship (duplikáció)
skill_mappings = relationship("TournamentSkillMapping")
# ↑ game_config.skill_config.skills_tested SZINTÉN tartalmazza!
# ↑ reward_config.skill_mappings SZINTÉN tartalmazza!

# 🔴 PROBLÉMA 5: Match timing (game-specific, nem kéne itt)
match_duration_minutes = Column(Integer)
break_duration_minutes = Column(Integer)

# 🔴 PROBLÉMA 6: Tournament type-specific fields
parallel_fields = Column(Integer)
scoring_type = Column(String)
measurement_unit = Column(String)
ranking_direction = Column(String)
number_of_rounds = Column(Integer)
```

**Értékelés:** 🔴 Erős keveredés, túl sok felelősség

---

### 2. KONKRÉT REDUNDANCIA PÉLDÁK

#### 2.1 Format Field Duplikáció

```python
# TournamentType.format
tournament_type = TournamentType.query.get(1)
tournament_type.format  # → "HEAD_TO_HEAD"

# Semester.format (REDUNDÁNS!)
semester = Semester.query.get(10)
semester.format  # → "HEAD_TO_HEAD"
semester.tournament_type.format  # → UGYANAZ!

# ⚠️ Mi van, ha eltérnek?
# Ha admin megváltoztatja a Semester.format-ot,
# de a tournament_type_id nem változik?
# → INKONZISZTENCIA!
```

**Megoldás:**
```python
# Format mint derived property:
@property
def format(self) -> str:
    """Auto-derive from tournament_type"""
    if self.tournament_type_id:
        return self.tournament_type.format
    return "INDIVIDUAL_RANKING"  # Default
```

---

#### 2.2 Skill Mappings Triplikáció

```python
# 1. TournamentSkillMapping (külön tábla)
TournamentSkillMapping:
    semester_id = 10
    skill_key = "speed"
    weight = 1.5
    enabled = True

# 2. game_config.skill_config (JSONB)
semester.game_config = {
    "skill_config": {
        "skills_tested": ["speed", "agility"],
        "skill_weights": {"speed": 1.5, "agility": 1.0}
    }
}

# 3. reward_config.skill_mappings (JSONB)
semester.reward_config = {
    "skill_mappings": [
        {"skill": "speed", "weight": 1.5, "placement_bonuses": {...}}
    ]
}

# 🔴 UGYANAZ A "speed" skill 3 HELYEN!
# Ha admin megváltoztatja az egyik weight-et, frissül a másik kettő?
```

**Megoldás:** Single source of truth - csak `game_config.skill_config`

---

#### 2.3 Tournament Type String vs FK

```python
# DEPRECATED field (string)
semester.tournament_type = "league"  # String!

# NEW field (FK)
semester.tournament_type_id = 5
semester.tournament_type.code = "league"  # Ugyanaz!

# ⚠️ Ki garantálja, hogy egyeznek?
```

**Megoldás:** Remove deprecated `tournament_type` string field

---

### 3. API CONTRACT HIÁNYOSSÁGOK

#### 3.1 Jelenlegi RunTestRequest Schema

```python
# app/api/api_v1/endpoints/sandbox/run_test.py
class RunTestRequest(BaseModel):
    tournament_type: str  # 🔴 String! FK kellene
    tournament_name: str
    format: str  # 🔴 Redundáns - derived!
    campus_id: int

    # Game config
    skills_to_test: List[str]
    skill_weights: Optional[Dict[str, float]]

    # 🔴 HIÁNYZIK:
    # game_preset_id: int  ← NEM szerepel!
    # reward_config: Dict  ← NEM szerepel!

    # Game-specific
    draw_probability: float
    home_win_probability: float
    random_seed: Optional[int]
```

**Probléma:** Nem tükrözi a rétegeket, hiányos

---

#### 3.2 Ideális Request Schema (Rétegezett)

```python
class TournamentCreateRequest(BaseModel):
    """Clean, layered tournament creation"""

    # Layer 1: Tournament Information
    info: TournamentInfo = Field(...)

    # Layer 2: Configuration
    config: TournamentConfiguration = Field(...)

    # Layer 3: Game Configuration
    game_config: GameConfiguration = Field(...)

    # Layer 4: Reward Configuration
    reward_config: RewardConfiguration = Field(...)

class TournamentInfo(BaseModel):
    name: str
    campus_id: int
    start_date: date
    end_date: date
    age_group: Optional[str]

class TournamentConfiguration(BaseModel):
    tournament_type_id: int  # FK, not string!
    assignment_type: str
    max_players: int
    pricing_credits: Optional[int]

class GameConfiguration(BaseModel):
    game_preset_id: int
    overrides: Optional[Dict[str, Any]]  # draw_prob, etc.

class RewardConfiguration(BaseModel):
    template_name: str
    custom_rewards: Optional[Dict[str, Any]]
```

---

### 4. STREAMLIT UI FLOW PROBLÉMA

#### 4.1 Jelenlegi: Egyetlen Hatalmas Form

```python
# streamlit_sandbox_v3_admin_aligned.py (lines 240-800)
def render_configuration_screen():
    # MINDENT egy lapon gyűjt:

    # Section 0: Game Type (Preset)
    game_preset_id = st.selectbox(...)

    # Section 1: Location
    campus_id = st.selectbox(...)

    # Section 2: Reward Config
    skill_weights = st.slider(...)
    first_place_credits = st.number_input(...)

    # Section 3: Tournament Format
    format_selected = st.selectbox(...)
    tournament_name = st.text_input(...)

    # Section 4: Tournament Config
    max_players = st.slider(...)

    # Section 7: Advanced (Game Config Overrides)
    draw_probability = st.slider(...)

    # ⚠️ PROBLÉMA: Nem tiszta, melyik réteg melyik
    # Admin nem látja: Tournament Info vs Config vs Game Config
```

#### 4.2 Ajánlott: Rétegezett UI

```python
def render_configuration_screen():
    # SEPARATED LAYERS:

    st.markdown("## 📋 Tournament Information")
    with st.container():
        name = st.text_input("Tournament Name")
        campus = st.selectbox("Campus")
        dates = st.date_input("Date Range")

    st.markdown("---")
    st.markdown("## ⚙️ Tournament Configuration")
    with st.container():
        tournament_type_id = st.selectbox("Type", tournament_types)
        # Format auto-derived!
        st.info(f"Format: {selected_type.format} (auto)")
        max_players = st.slider("Max Players")
        assignment = st.selectbox("Assignment Type")

    st.markdown("---")
    st.markdown("## 🎮 Game Configuration")
    with st.container():
        preset_id = st.selectbox("Game Preset", presets)
        # Show preset preview
        if st.checkbox("Override Preset"):
            draw_prob = st.slider(...)

    st.markdown("---")
    st.markdown("## 🏆 Reward Configuration")
    with st.container():
        reward_template = st.selectbox("Template")
        # Show template preview
        if st.checkbox("Customize Rewards"):
            first_place = st.number_input(...)
```

**Előny:** Vizuálisan is elkülönülnek a rétegek

---

## 🔧 REFAKTORÁLÁSI JAVASLATOK

### Prioritás: P0 (KRITIKUS - Azonnal)

#### P0.1: Deprecated Fields Eltávolítása

**Idő:** 1-2 óra
**Hatás:** Confusion csökkentés, clean codebase

```python
# REMOVE from Semester model:
tournament_type: str  # Use tournament_type_id!

# REMOVE legacy location fields:
location_city: str
location_venue: str
location_address: str
# Already have: campus_id, location_id (FK)
```

**Migration:**
```sql
-- Check no data loss
SELECT COUNT(*) FROM semesters
WHERE tournament_type IS NOT NULL
  AND tournament_type_id IS NULL;

-- Expected: 0 rows (all migrated)

-- Drop column
ALTER TABLE semesters DROP COLUMN tournament_type;
ALTER TABLE semesters DROP COLUMN location_city;
ALTER TABLE semesters DROP COLUMN location_venue;
ALTER TABLE semesters DROP COLUMN location_address;
```

---

#### P0.2: Format Field → Derived Property

**Idő:** 2 óra
**Hatás:** Single source of truth, no redundancy

```python
# BEFORE:
format = Column(String)  # Stored in DB

# AFTER:
@property
def format(self) -> str:
    """Derive format from tournament_type"""
    if self.tournament_type_id and self.tournament_type:
        return self.tournament_type.format
    elif self.game_preset_id and self.game_preset:
        # Extract from preset if no tournament_type
        format_config = self.game_preset.game_config.get('format_config', {})
        if format_config:
            return list(format_config.keys())[0]  # First format key
    return "INDIVIDUAL_RANKING"  # Default fallback
```

**Migration:**
```sql
-- Verify consistency first
SELECT id, format, tournament_type_id,
       (SELECT format FROM tournament_types tt WHERE tt.id = semesters.tournament_type_id) as derived_format
FROM semesters
WHERE format != (SELECT format FROM tournament_types tt WHERE tt.id = semesters.tournament_type_id);

-- Expected: 0 rows (all consistent)

-- Drop column
ALTER TABLE semesters DROP COLUMN format;
```

**UPDATE Code:**
- `app/models/semester.py`: Add `@property format`
- `app/api/api_v1/endpoints/semesters/crud.py`: Remove format from INSERT
- `app/services/sandbox_test_orchestrator.py`: Remove format assignment
- `streamlit_sandbox_v3_admin_aligned.py`: Display format as derived

---

### Prioritás: P1 (MAGAS - 1-2 héten belül)

#### P1.1: Reward Config Szeparálása → Külön Tábla

**Idő:** 4-6 óra
**Hatás:** Clean layer separation, auditability

**Új tábla:**
```python
class TournamentRewardConfig(Base):
    __tablename__ = "tournament_reward_configs"

    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), unique=True)
    reward_policy_name = Column(String)
    reward_policy_snapshot = Column(JSONB)
    reward_config = Column(JSONB)  # ← Move from Semester
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationship
    tournament = relationship("Semester", back_populates="reward_config_obj")
```

**Semester frissítés:**
```python
# REMOVE:
reward_config = Column(JSONB)
reward_policy_name = Column(String)
reward_policy_snapshot = Column(JSONB)

# ADD:
reward_config_obj = relationship("TournamentRewardConfig",
                                  uselist=False,
                                  back_populates="tournament")

@property
def reward_config(self) -> Dict:
    """Backward compatible property"""
    if self.reward_config_obj:
        return self.reward_config_obj.reward_config
    return {}
```

**Migration:**
```python
def upgrade():
    # Create table
    op.create_table(
        'tournament_reward_configs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('semester_id', sa.Integer(), sa.ForeignKey('semesters.id')),
        sa.Column('reward_policy_name', sa.String()),
        sa.Column('reward_policy_snapshot', sa.dialects.postgresql.JSONB()),
        sa.Column('reward_config', sa.dialects.postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Migrate existing data
    op.execute("""
        INSERT INTO tournament_reward_configs (semester_id, reward_policy_name, reward_policy_snapshot, reward_config)
        SELECT id, reward_policy_name, reward_policy_snapshot, reward_config
        FROM semesters
        WHERE reward_config IS NOT NULL
    """)

    # Drop old columns
    op.drop_column('semesters', 'reward_config')
    op.drop_column('semesters', 'reward_policy_name')
    op.drop_column('semesters', 'reward_policy_snapshot')
```

---

#### P1.2: Skill Mappings Tisztázása

**Idő:** 3-4 óra
**Hatás:** Remove duplication, single source of truth

**Probléma azonosítás:**
```python
# Currently skills in 3 places:
# 1. TournamentSkillMapping (table)
# 2. game_config.skill_config (JSONB)
# 3. reward_config.skill_mappings (JSONB)

# WHO IS THE SOURCE OF TRUTH?
```

**Megoldás:** `game_config.skill_config` = single source

```python
# KEEP: game_config.skill_config
{
    "skill_config": {
        "skills_tested": ["speed", "agility"],
        "skill_weights": {"speed": 1.5, "agility": 1.0}
    }
}

# REMOVE: TournamentSkillMapping table
# (Redundáns, ha game_config.skill_config létezik)

# CLARIFY: reward_config.skill_mappings
# → Only placement_bonuses and reward-specific config
{
    "skill_mappings": [
        {
            "skill": "speed",  # ← Reference to game_config.skill_config
            "placement_bonuses": {  # ← Reward-only info
                "top_3": {"enabled": True, "bonus_xp": 10}
            }
        }
    ]
}
```

**Migration:**
```sql
-- Option 1: Drop TournamentSkillMapping table
-- (If game_config always has skills)
DROP TABLE tournament_skill_mappings;

-- Option 2: Keep as cache/denormalization
-- Add FK to ensure consistency
ALTER TABLE tournament_skill_mappings
ADD CONSTRAINT check_skill_in_game_config
CHECK (skill_key IN (
    SELECT jsonb_array_elements_text(
        game_config->'skill_config'->'skills_tested'
    ) FROM semesters WHERE id = semester_id
));
```

---

### Prioritás: P2 (KÖZEPES - 1-2 hónapon belül)

#### P2.1: Tournament Configuration Tábla

**Idő:** 6-8 óra
**Hatás:** Full separation of concerns

```python
class TournamentConfiguration(Base):
    __tablename__ = "tournament_configurations"

    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), unique=True)
    tournament_type_id = Column(Integer, ForeignKey("tournament_types.id"))
    assignment_type = Column(String)
    max_players = Column(Integer)
    pricing_credits = Column(Integer)
    created_at = Column(DateTime)

    tournament = relationship("Semester", back_populates="config")
```

**Semester leegyszerűsítése:**
```python
# Semester csak Tournament Info:
code, name, start_date, end_date
campus_id, location_id
status, created_at

# Configuration külön:
config = relationship("TournamentConfiguration", uselist=False)
```

---

#### P2.2: Game Configuration Tábla

**Idő:** 4-6 óra
**Hatás:** Audit trail, versioning

```python
class GameConfiguration(Base):
    __tablename__ = "game_configurations"

    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"))
    game_preset_id = Column(Integer, ForeignKey("game_presets.id"))
    game_config = Column(JSONB)  # Complete config
    overrides = Column(JSONB)    # Just deltas
    version = Column(Integer, default=1)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    tournament = relationship("Semester", back_populates="game_config_obj")
```

---

### Prioritás: P3 (ALACSONY - Jövőbeli)

#### P3.1: UI Refactoring

**Idő:** 8-10 óra
**Hatás:** Better UX, clear layers

- Rétegezett form UI (fent leírva)
- Wizárd-szerű flow (Next/Previous buttons)
- Layer preview before submission

---

## 📊 ÖSSZESÍTŐ TÁBLÁZAT

| Prioritás | Feladat | Idő | Hatás | Implementálás |
|-----------|---------|-----|-------|---------------|
| **P0** | Deprecated fields remove | 1-2h | ⭐⭐⭐ Confusion csökkentés | Azonnal |
| **P0** | Format → derived property | 2h | ⭐⭐⭐ Single source of truth | Azonnal |
| **P1** | Reward config → külön tábla | 4-6h | ⭐⭐⭐ Clean separation | 1-2 hét |
| **P1** | Skill mappings cleanup | 3-4h | ⭐⭐ Remove duplication | 1-2 hét |
| **P2** | TournamentConfiguration tábla | 6-8h | ⭐⭐ Full layer separation | 1-2 hónap |
| **P2** | GameConfiguration tábla | 4-6h | ⭐ Versioning | 1-2 hónap |
| **P3** | UI refactoring | 8-10h | ⭐ Better UX | Jövőbeli |

---

## 🎯 JAVASOLT IMPLEMENTÁCIÓS SORREND

### Sprint 1 (Azonnal - 1 hét)

**Cél:** Clean up redundancy & deprecated fields

1. ✅ Create feature branch: `refactor/tournament-architecture`
2. 🔧 P0.1: Remove deprecated fields (migration)
3. 🔧 P0.2: Format → derived property (migration)
4. ✅ Tests: Verify all tournaments still load
5. ✅ Deploy to staging
6. ✅ User acceptance testing
7. ✅ Deploy to production

**Deliverable:** Cleaner Semester model, no redundant fields

---

### Sprint 2 (2-3 hét)

**Cél:** Separate reward configuration

1. 🔧 P1.1: Create TournamentRewardConfig model
2. 🔧 P1.1: Migration script (move data)
3. 🔧 P1.1: Update orchestrator (create reward config separately)
4. 🔧 P1.1: Update API endpoints
5. ✅ Tests: Reward distribution still works
6. ✅ Deploy to staging
7. ✅ Deploy to production

**Deliverable:** Reward config as separate entity

---

### Sprint 3 (1-2 hónap)

**Cél:** Full separation (Config & Game Config tables)

1. 🔧 P2.1: TournamentConfiguration model
2. 🔧 P2.2: GameConfiguration model
3. 🔧 Migrations: Move data to new tables
4. 🔧 Update all CRUD operations
5. ✅ Full regression testing
6. ✅ Deploy

**Deliverable:** Clean 3-layer architecture

---

## 📝 KÖVETKEZTETÉSEK

### Jelenlegi Állapot

❌ **Nem megfelelő:**
- Minden a Semester model-ben (God object anti-pattern)
- Redundáns mezők (format, tournament_type)
- Semantic confusion (game_config vs reward_config overlap)
- Deprecated fields zavarják a kódot
- API contract nem tükrözi a rétegeket

### Ajánlott Irány

✅ **Clean Architecture:**
- 3 tiszta réteg: Info → Config → Game Config
- Reward config külön entitás (P1)
- Format és skills single source of truth (P0)
- Clear API contracts (P1)
- Opcionális: Külön táblák minden réteghez (P2)

### Gyors Win-ek (P0)

**1 hét alatt elérhető:**
- Deprecated mezők eltávolítása
- Format redundancia megszüntetése
- Tisztább kódbázis
- Jobb dokumentáltság

### Hosszú Távú Előnyök (P1-P2)

**1-2 hónap múlva:**
- Separate reward configuration → auditability
- Separate game configuration → versioning
- Clean layer separation → maintainability
- Better API contracts → developer experience

---

## 🚀 ACTION ITEMS

### Azonnali (Ma-Holnap)

- [ ] Döntés: Melyik prioritással indulunk? (Javaslat: P0)
- [ ] Feature branch létrehozása: `refactor/tournament-architecture`
- [ ] P0.1 migration elkészítése (deprecated fields)
- [ ] P0.2 migration elkészítése (format → property)

### Következő Sprint

- [ ] P1.1 tervezés (reward config szeparálás)
- [ ] Database schema review
- [ ] API contract design

### Dokumentáció

- [ ] Architecture decision record (ADR) készítése
- [ ] Migration guide írása
- [ ] Developer onboarding update

---

**Készítette:** Claude Code (Architecture Audit Agent)
**Verzió:** 1.0
**Következő Review:** P0 implementálás után
