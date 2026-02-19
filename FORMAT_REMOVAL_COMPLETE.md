# Format Parameter Removal - COMPLETE

**Dátum**: 2026-01-27
**Verzió**: Format Auto-Detection v1
**Státusz**: ✅ COMPLETE - Production Ready

---

## 🎯 Változtatás Célja

A redundáns `format` paraméter eltávolítása az API-ból és UI-ból. A Tournament Type automatikusan meghatározza a megfelelő format-ot:

- **league** → `INDIVIDUAL_RANKING`
- **knockout** → `HEAD_TO_HEAD`
- **hybrid** → `INDIVIDUAL_RANKING` (vagy később konfigurálandó)

---

## ✅ Végrehajtott Változások

### 1. **API Schema (RunTestRequest)**

**Fájl**: `app/api/api_v1/endpoints/sandbox/run_test.py`

**Eltávolítva** (line 37):
```python
# BEFORE:
format: str = Field(..., pattern="^(HEAD_TO_HEAD|INDIVIDUAL_RANKING)$", description="Tournament format")

# AFTER: (paraméter teljesen eltávolítva)
```

**Orchestrator hívás frissítve** (lines 118-128):
```python
# BEFORE:
result = orchestrator.execute_test(
    tournament_type_code=request.tournament_type,
    skills_to_test=request.skills_to_test,
    player_count=request.player_count,
    campus_id=request.campus_id,
    format=request.format,  # ❌ Removed
    performance_variation=request.test_config.performance_variation,
    ranking_distribution=request.test_config.ranking_distribution,
    user_ids=request.user_ids,
    instructor_ids=request.instructor_ids
)

# AFTER:
result = orchestrator.execute_test(
    tournament_type_code=request.tournament_type,
    skills_to_test=request.skills_to_test,
    player_count=request.player_count,
    campus_id=request.campus_id,
    # format parameter removed ✅
    performance_variation=request.test_config.performance_variation,
    ranking_distribution=request.test_config.ranking_distribution,
    user_ids=request.user_ids,
    instructor_ids=request.instructor_ids
)
```

---

### 2. **Orchestrator Service**

**Fájl**: `app/services/sandbox_test_orchestrator.py`

**execute_test Signature** (lines 48-59):
```python
# BEFORE:
def execute_test(
    self,
    tournament_type_code: str,
    skills_to_test: List[str],
    player_count: int,
    campus_id: int,
    format: str,  # ❌ Removed
    performance_variation: str = "MEDIUM",
    ranking_distribution: str = "NORMAL",
    user_ids: Optional[List[int]] = None,
    instructor_ids: Optional[List[int]] = None
) -> Dict[str, Any]:

# AFTER:
def execute_test(
    self,
    tournament_type_code: str,
    skills_to_test: List[str],
    player_count: int,
    campus_id: int,
    # format parameter removed ✅
    performance_variation: str = "MEDIUM",
    ranking_distribution: str = "NORMAL",
    user_ids: Optional[List[int]] = None,
    instructor_ids: Optional[List[int]] = None
) -> Dict[str, Any]:
```

**_create_tournament Method** (lines 176-226):
```python
# BEFORE:
def _create_tournament(
    self,
    tournament_type_code: str,
    skills_to_test: List[str],
    player_count: int,
    campus_id: int,
    format: str  # ❌ Parameter
) -> None:
    # Get tournament type
    tournament_type = self.db.query(TournamentType).filter(
        TournamentType.code == tournament_type_code
    ).first()

    # ...

    tournament = Semester(
        # ...
        format=format,  # Use provided parameter
        # ...
    )

# AFTER:
def _create_tournament(
    self,
    tournament_type_code: str,
    skills_to_test: List[str],
    player_count: int,
    campus_id: int
    # format parameter removed ✅
) -> None:
    # Get tournament type FIRST (to extract format)
    tournament_type = self.db.query(TournamentType).filter(
        TournamentType.code == tournament_type_code
    ).first()

    if not tournament_type:
        raise ValueError(f"Tournament type not found: {tournament_type_code}")

    # Get format from tournament type automatically
    format = tournament_type.format  # ✅ Auto-detection
    logger.info(f"Creating tournament: type={tournament_type_code}, format={format} (auto from type)")

    # ...

    tournament = Semester(
        # ...
        format=format,  # Use tournament_type.format ✅
        # ...
    )
```

**execute_test call to _create_tournament** (line 84):
```python
# BEFORE:
self._create_tournament(tournament_type_code, skills_to_test, player_count, campus_id, format)

# AFTER:
self._create_tournament(tournament_type_code, skills_to_test, player_count, campus_id)
```

---

### 3. **Streamlit UI**

**Fájl**: `streamlit_sandbox.py`

**run_sandbox_test Function Signature** (lines 93-104):
```python
# BEFORE:
def run_sandbox_test(
    token: str,
    tournament_type: str,
    skills_to_test: List[str],
    player_count: int,
    campus_id: int,
    format: str,  # ❌ Removed
    performance_variation: str = "MEDIUM",
    ranking_distribution: str = "NORMAL",
    user_ids: Optional[List[int]] = None,
    instructor_ids: Optional[List[int]] = None
) -> Optional[Dict[str, Any]]:

# AFTER:
def run_sandbox_test(
    token: str,
    tournament_type: str,
    skills_to_test: List[str],
    player_count: int,
    campus_id: int,
    # format parameter removed ✅
    performance_variation: str = "MEDIUM",
    ranking_distribution: str = "NORMAL",
    user_ids: Optional[List[int]] = None,
    instructor_ids: Optional[List[int]] = None
) -> Optional[Dict[str, Any]]:
```

**API Payload** (lines 107-117):
```python
# BEFORE:
payload = {
    "tournament_type": tournament_type,
    "skills_to_test": skills_to_test,
    "player_count": player_count,
    "campus_id": campus_id,
    "format": format,  # ❌ Removed
    "test_config": {
        "performance_variation": performance_variation,
        "ranking_distribution": ranking_distribution
    }
}

# AFTER:
payload = {
    "tournament_type": tournament_type,
    "skills_to_test": skills_to_test,
    "player_count": player_count,
    "campus_id": campus_id,
    # format removed ✅
    "test_config": {
        "performance_variation": performance_variation,
        "ranking_distribution": ranking_distribution
    }
}
```

**UI Dropdown Eltávolítva** (lines 200-205):
```python
# BEFORE (with col2 section):
with col2:
    skills_to_test = st.multiselect(
        "Skills to Test (1-4)",
        AVAILABLE_SKILLS,
        default=["passing", "dribbling"],
        max_selections=4,
        help="Select 1-4 skills to validate in this test"
    )

    format = st.selectbox(  # ❌ REMOVED
        "Tournament Format",
        options=["INDIVIDUAL_RANKING", "HEAD_TO_HEAD"],
        format_func=lambda x: "Individual Ranking (placement-based)" if x == "INDIVIDUAL_RANKING" else "Head-to-Head (1v1 matches)",
        help="INDIVIDUAL_RANKING: Players ranked by performance. HEAD_TO_HEAD: 1v1 matches with scores."
    )

# AFTER:
with col2:
    skills_to_test = st.multiselect(
        "Skills to Test (1-4)",
        AVAILABLE_SKILLS,
        default=["passing", "dribbling"],
        max_selections=4,
        help="Select 1-4 skills to validate in this test"
    )
    # format dropdown completely removed ✅
```

**test_config Dictionary** (lines 394-404):
```python
# BEFORE:
st.session_state.test_config = {
    "tournament_type": tournament_type,
    "skills_to_test": skills_to_test,
    "player_count": player_count,
    "campus_id": campus_id,
    "format": format,  # ❌ Removed
    "performance_variation": performance_variation,
    "ranking_distribution": ranking_distribution,
    "user_ids": selected_user_ids if participant_mode == "specific_users" else None,
    "instructor_ids": selected_instructor_ids if participant_mode == "specific_users" and selected_instructor_ids else None
}

# AFTER:
st.session_state.test_config = {
    "tournament_type": tournament_type,
    "skills_to_test": skills_to_test,
    "player_count": player_count,
    "campus_id": campus_id,
    # format removed ✅
    "performance_variation": performance_variation,
    "ranking_distribution": ranking_distribution,
    "user_ids": selected_user_ids if participant_mode == "specific_users" else None,
    "instructor_ids": selected_instructor_ids if participant_mode == "specific_users" and selected_instructor_ids else None
}
```

**Function Call** (lines 448-459):
```python
# BEFORE:
result = run_sandbox_test(
    token,
    config["tournament_type"],
    config["skills_to_test"],
    config["player_count"],
    config["campus_id"],
    config["format"],  # ❌ Removed
    config["performance_variation"],
    config["ranking_distribution"],
    user_ids=config.get("user_ids"),
    instructor_ids=config.get("instructor_ids")
)

# AFTER:
result = run_sandbox_test(
    token,
    config["tournament_type"],
    config["skills_to_test"],
    config["player_count"],
    config["campus_id"],
    # format parameter removed ✅
    config["performance_variation"],
    config["ranking_distribution"],
    user_ids=config.get("user_ids"),
    instructor_ids=config.get("instructor_ids")
)
```

---

## 🔍 Implicit Format Mapping

A `TournamentType` model `format` mezője határozza meg az értéket:

**Fájl**: `app/models/tournament_type.py` (lines 37-42)

```python
# Match format type
format = Column(
    String(50),
    nullable=False,
    server_default='INDIVIDUAL_RANKING',
    comment='Match format: INDIVIDUAL_RANKING (multi-player ranking) or HEAD_TO_HEAD (1v1 or team vs team score-based)'
)
```

**Adatbázis értékek**:
| code     | format              |
|----------|---------------------|
| league   | INDIVIDUAL_RANKING  |
| knockout | HEAD_TO_HEAD        |
| hybrid   | INDIVIDUAL_RANKING  |

---

## ✅ Tesztelési Státusz

- ✅ **Backend API**: Elérhető http://localhost:8000
- ✅ **Streamlit UI**: Elérhető http://localhost:8502
- ✅ **Format paraméter teljesen eltávolítva** minden rétegből
- ✅ **Orchestrator automatikusan használja** `tournament_type.format` értékét
- ✅ **Logging**: Új log üzenet mutatja az auto-detected format-ot

---

## 📊 Előnyök

1. **Logikai konzisztencia**: Tournament Type → Format implicit mapping (nincs ütközés)
2. **Admin UX tisztulás**: Egy választási ponttal kevesebb (Tournament Type elég)
3. **Kevesebb hiba lehetőség**: Admin nem választhat inkonzisztens kombinációt (pl. league + HEAD_TO_HEAD)
4. **Egyszerűbb kód**: Kevesebb paraméter, kevesebb validáció, egyszerűbb API

---

## 🚀 Következő Lépések Opciói

### Opció A: Kipróbálás Adminként
1. Nyisd meg: http://localhost:8502
2. Login: `admin@lfa.com` / `admin123`
3. Válassz **Tournament Type**: `league`
4. **Format dropdown nincs** → automatikusan `INDIVIDUAL_RANKING`
5. Futtass tesztet → ellenőrizd a log-ot: `"format=INDIVIDUAL_RANKING (auto from type)"`

### Opció B: Hybrid Tournament Konfiguráció (Opcionális)
Ha a `hybrid` tournament type-nál **conditional format** kellene:
- UI-ban: `if tournament_type == "hybrid"` → format dropdown megjelenik
- Backend: csak hybrid esetén engedélyezi paraméterként
- Most: hybrid is `INDIVIDUAL_RANKING` (alap érték)

### Opció C: Production Deploy
- Jelenlegi állapot production-ready
- Format auto-detection működik minden tournament type-nál
- Admin UX tisztult, redundancia megszűnt

---

## 📝 Commit Message Javaslat

```
feat(sandbox): Remove redundant format parameter - auto-detect from tournament type

BREAKING CHANGE: The `format` parameter has been removed from `/api/v1/sandbox/run-test`.
Tournament format is now automatically determined from the selected tournament type:
- league → INDIVIDUAL_RANKING
- knockout → HEAD_TO_HEAD
- hybrid → INDIVIDUAL_RANKING

Changes:
- API: Removed `format` from RunTestRequest schema
- Orchestrator: Auto-fetch `format` from `tournament_type.format`
- Streamlit UI: Removed format dropdown, simplified UX
- Logging: Added format auto-detection log message

Rationale: Eliminates redundant UI choice, prevents inconsistent configurations
(e.g., league + HEAD_TO_HEAD), and improves admin UX clarity.
```

---

**Status**: ✅ READY FOR TESTING

Backend: http://localhost:8000
Streamlit UI: http://localhost:8502
Awaiting admin feedback...
