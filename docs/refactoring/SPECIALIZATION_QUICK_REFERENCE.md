# Specialization Service - Quick Reference

## Import Cheat Sheet

### Old Way (Still Works)
```python
from app.services.specialization_service import SpecializationService

service = SpecializationService(db)
service.enroll_user(user_id, "GANCUJU_PLAYER")
service.get_student_progress(student_id, "LFA_COACH")
```

### New Way (Recommended)

#### Using the Wrapper Class
```python
from app.services.specialization import SpecializationService

service = SpecializationService(db)
service.enroll_user(user_id, "GANCUJU_PLAYER")
```

#### Using Generic Functions
```python
from app.services.specialization import (
    enroll_user,
    get_student_progress,
    update_progress,
    get_level_requirements
)

enroll_user(db, user_id, "GANCUJU_PLAYER")
progress = get_student_progress(db, student_id, "LFA_COACH")
```

#### Using Specialization-Specific Functions (Best)
```python
from app.services.specialization import (
    enroll_lfa_player,
    get_lfa_player_progress,
    update_lfa_player_progress
)

enroll_lfa_player(db, user_id)
progress = get_lfa_player_progress(db, student_id)
update_lfa_player_progress(db, student_id, xp_gained=100)
```

## Available Functions by Module

### validation.py
```python
from app.services.specialization import (
    specialization_id_to_enum,        # Convert string ID to enum
    handle_legacy_specialization,      # Handle deprecated IDs
    validate_specialization_exists,    # Check if spec exists
    get_all_specializations,           # Get all active specs
)
```

### common.py
```python
from app.services.specialization import (
    get_level_requirements,     # Get level config
    get_student_progress,       # Get/create progress
    can_level_up,              # Check level-up eligibility
    update_progress,           # Update progress + auto level-up
    get_all_levels,           # Get all levels for spec
    enroll_user,              # Enroll in specialization
)
```

### lfa_player.py
```python
from app.services.specialization import (
    enroll_lfa_player,
    get_lfa_player_level_requirements,
    get_lfa_player_progress,
    update_lfa_player_progress,
    get_all_lfa_player_levels,
)
```

### lfa_coach.py
```python
from app.services.specialization import (
    enroll_lfa_coach,
    get_lfa_coach_level_requirements,
    get_lfa_coach_progress,
    update_lfa_coach_progress,
    get_all_lfa_coach_levels,
)
```

### gancuju.py
```python
from app.services.specialization import (
    enroll_gancuju_player,
    get_gancuju_player_level_requirements,
    get_gancuju_player_progress,
    update_gancuju_player_progress,
    get_all_gancuju_player_levels,
)
```

### internship.py
```python
from app.services.specialization import (
    enroll_internship,
    get_internship_level_requirements,
    get_internship_progress,
    update_internship_progress,
    get_all_internship_levels,
)
```

## Common Use Cases

### 1. Enroll User in Specialization

**Old:**
```python
service = SpecializationService(db)
result = service.enroll_user(user_id, "GANCUJU_PLAYER")
```

**New (Generic):**
```python
from app.services.specialization import enroll_user
result = enroll_user(db, user_id, "GANCUJU_PLAYER")
```

**New (Specific):**
```python
from app.services.specialization import enroll_lfa_player
result = enroll_lfa_player(db, user_id)
```

### 2. Get Student Progress

**Old:**
```python
service = SpecializationService(db)
progress = service.get_student_progress(student_id, "LFA_COACH")
```

**New (Generic):**
```python
from app.services.specialization import get_student_progress
progress = get_student_progress(db, student_id, "LFA_COACH")
```

**New (Specific):**
```python
from app.services.specialization import get_lfa_coach_progress
progress = get_lfa_coach_progress(db, student_id)
```

### 3. Update Progress

**Old:**
```python
service = SpecializationService(db)
result = service.update_progress(
    student_id,
    "GANCUJU_PLAYER",
    xp_gained=100,
    sessions_completed=1
)
```

**New (Generic):**
```python
from app.services.specialization import update_progress
result = update_progress(
    db,
    student_id,
    "GANCUJU_PLAYER",
    xp_gained=100,
    sessions_completed=1
)
```

**New (Specific):**
```python
from app.services.specialization import update_lfa_player_progress
result = update_lfa_player_progress(
    db,
    student_id,
    xp_gained=100,
    sessions_completed=1
)
```

### 4. Get All Specializations

**Old:**
```python
service = SpecializationService(db)
specs = service.get_all_specializations()
```

**New:**
```python
from app.services.specialization import get_all_specializations
specs = get_all_specializations(db)
```

### 5. Get Level Requirements

**Old:**
```python
service = SpecializationService(db)
level = service.get_level_requirements("GANCUJU_PLAYER", 3)
```

**New (Generic):**
```python
from app.services.specialization import get_level_requirements
level = get_level_requirements(db, "GANCUJU_PLAYER", 3)
```

**New (Specific):**
```python
from app.services.specialization import get_lfa_player_level_requirements
level = get_lfa_player_level_requirements(db, 3)
```

### 6. Check if Can Level Up

**Old:**
```python
service = SpecializationService(db)
can_level = service.can_level_up(progress)
```

**New:**
```python
from app.services.specialization import can_level_up
can_level = can_level_up(db, progress)
```

## When to Use Each Approach

### Use Wrapper Class When:
- Migrating old code gradually
- Need to maintain existing API
- Working with legacy code

### Use Generic Functions When:
- Specialization type is dynamic
- Building generic features
- Working with multiple specialization types

### Use Specific Functions When:
- Specialization type is known at compile time
- Building spec-specific features
- Want type safety and clarity

## Migration Strategy

### Phase 1: No Changes Required
- All existing code works as-is
- Old import path redirects to new module

### Phase 2: Update Imports (Optional)
```python
# Change this:
from app.services.specialization_service import SpecializationService

# To this:
from app.services.specialization import SpecializationService
```

### Phase 3: Use Direct Functions (Recommended)
```python
# Instead of:
service = SpecializationService(db)
service.enroll_user(user_id, "GANCUJU_PLAYER")

# Use:
from app.services.specialization import enroll_lfa_player
enroll_lfa_player(db, user_id)
```

## Benefits of New Approach

1. **Clearer Dependencies**: Function signatures show exactly what's needed
2. **Easier Testing**: Pure functions, no mocking
3. **Better IDE Support**: Type hints and autocomplete
4. **Modular Structure**: Each specialization is independent
5. **Performance**: Slightly lower memory usage (no class instances)

## FAQ

### Q: Do I need to change my existing code?
**A:** No, all existing code continues to work unchanged.

### Q: Which import path should I use?
**A:** For new code, use `from app.services.specialization import ...`

### Q: Should I use the wrapper class or direct functions?
**A:** For new code, prefer direct functions (generic or specific).

### Q: How do I add a new specialization?
**A:** Create a new file (e.g., `lfa_football.py`) with the same structure as existing spec modules.

### Q: Are there any breaking changes?
**A:** No, this refactoring is 100% backward compatible.

### Q: What if I find a bug?
**A:** Check the backup file at `app/services/specialization_service.py.backup` for reference.

## File Structure Reference

```
app/services/
├── specialization_service.py          # Redirect (backward compat)
├── specialization_service.py.backup   # Original backup
└── specialization/
    ├── __init__.py                    # Public API + wrapper
    ├── validation.py                  # Validation & legacy
    ├── common.py                      # Shared logic
    ├── lfa_player.py                 # LFA_PLAYER specific
    ├── lfa_coach.py                  # LFA_COACH specific
    ├── gancuju.py                    # GANCUJU_PLAYER alias
    └── internship.py                 # INTERNSHIP specific
```
