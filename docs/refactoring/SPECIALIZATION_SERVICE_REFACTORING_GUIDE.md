# 🎓 Specialization_Service.py Refactoring Guide
**Step-by-Step Manual** - Spec-based module separation

---

## 📋 Overview

**Source:** `app/services/specialization_service.py` (624 lines, 1 file)
**Target:** `app/services/specialization/` (5 modules, ~150 lines each)

**Estimated Time:** 4-6 hours

---

## 🗂️ Target Structure

```
app/services/specialization/
├── __init__.py              # Public API (40 lines)
├── validation.py            # Validation & utilities (120 lines)
├── lfa_player.py           # LFA_PLAYER spec logic (150 lines)
├── lfa_coach.py            # LFA_COACH spec logic (150 lines)
├── gancuju.py              # GANCUJU_PLAYER spec logic (100 lines)
└── internship.py           # INTERNSHIP spec logic (100 lines)
```

---

## 📝 STEP 1: Create `validation.py`

**File:** `app/services/specialization/validation.py`

**Purpose:** Common validation, enum conversion, legacy handling

**Functions to move:**
- `_specialization_id_to_enum()` (lines 41-67)
- `_handle_legacy_specialization()` (lines 68-103)
- `validate_specialization_exists()` (lines 104-127)
- `get_all_specializations()` (lines 523-583)

**Template:**

```python
"""
Specialization Validation & Utilities
Common validation functions and enum handling for all specializations
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from ...models.specialization import SpecializationType
from ..specialization_config_loader import get_config_loader

logger = logging.getLogger(__name__)

# DEPRECATION SYSTEM
DEPRECATED_MAPPINGS = {
    "PLAYER": "GANCUJU_PLAYER",
    "COACH": "LFA_COACH"
}
DEPRECATION_DEADLINE = datetime(2026, 5, 18)
DEPRECATION_WARNING = """
⚠️ DEPRECATED SPECIALIZATION ID: '{old_id}'
   Use '{new_id}' instead.
   Support for '{old_id}' will be removed on {deadline}.
   Please update your code!
"""


def specialization_id_to_enum(specialization_id: str) -> Optional[SpecializationType]:
    """
    Convert string specialization ID to enum value

    Args:
        specialization_id: String ID (e.g., "PLAYER", "GANCUJU_PLAYER")

    Returns:
        SpecializationType enum or None if invalid
    """
    # COPY lines 41-67 here (remove self.)
    # ...


def handle_legacy_specialization(spec_id: str) -> str:
    """
    Handle legacy specialization IDs with deprecation warnings

    Args:
        spec_id: Specialization ID (may be legacy)

    Returns:
        Modern specialization ID
    """
    # COPY lines 68-103 here
    # ...


def validate_specialization_exists(specialization_id: str) -> bool:
    """
    Validate that a specialization configuration exists

    Args:
        specialization_id: Specialization ID to validate

    Returns:
        True if exists, False otherwise
    """
    # COPY lines 104-127 here (remove self.)
    # Use get_config_loader() directly
    # ...


def get_all_specializations() -> List[Dict[str, Any]]:
    """
    Get all available specializations

    Returns:
        List of specialization configurations
    """
    # COPY lines 523-583 here
    # ...
```

**Action Items:**
1. Create file `app/services/specialization/validation.py`
2. Copy deprecation constants
3. Copy 4 validation functions
4. Remove all `self.` references
5. Replace `self.config_loader` → `get_config_loader()`

---

## 🎮 STEP 2: Create `lfa_player.py`

**File:** `app/services/specialization/lfa_player.py`

**Purpose:** LFA_PLAYER (GānCuju) specific logic

**Functions:** Filtered versions of generic functions for LFA_PLAYER only

**Template:**

```python
"""
LFA_PLAYER (GānCuju) Specialization Service
Handles progression, enrollment, and level management for GānCuju players
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging

from ...models.specialization import SpecializationType
from ..specialization_config_loader import get_config_loader
from .validation import specialization_id_to_enum, validate_specialization_exists

logger = logging.getLogger(__name__)

SPECIALIZATION_ID = "GANCUJU_PLAYER"


def enroll_lfa_player(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Enroll user in LFA_PLAYER specialization

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Enrollment result dictionary
    """
    # Reuse generic enroll_user logic but hardcoded for GANCUJU_PLAYER
    # COPY relevant parts from lines 128-196
    # ...


def get_lfa_player_level_requirements(level: int) -> Optional[Dict[str, Any]]:
    """
    Get level requirements for LFA_PLAYER

    Args:
        level: Level number

    Returns:
        Level requirements dict
    """
    # COPY from lines 197-268, filter for GANCUJU_PLAYER
    # ...


def get_lfa_player_progress(db: Session, student_id: int) -> Dict[str, Any]:
    """
    Get student progress in LFA_PLAYER specialization

    Args:
        db: Database session
        student_id: Student ID

    Returns:
        Progress dictionary
    """
    # COPY from lines 269-364, filter for GANCUJU_PLAYER
    # ...


def get_all_lfa_player_levels() -> List[Dict[str, Any]]:
    """
    Get all LFA_PLAYER levels

    Returns:
        List of level configurations
    """
    # COPY from lines 584-624, filter for GANCUJU_PLAYER
    # ...
```

**Action Items:**
1. Create file
2. Copy generic functions
3. Filter/hardcode for `GANCUJU_PLAYER` only
4. Remove `self.db` → use `db` parameter

---

## 👨‍🏫 STEP 3: Create `lfa_coach.py`

**File:** `app/services/specialization/lfa_coach.py`

**Purpose:** LFA_COACH specific logic

**Template:** Same structure as `lfa_player.py`, but for `LFA_COACH`

```python
"""
LFA_COACH Specialization Service
Handles coaching license progression and certification
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import logging

from ...models.specialization import SpecializationType
from ..specialization_config_loader import get_config_loader
from .validation import specialization_id_to_enum, validate_specialization_exists

logger = logging.getLogger(__name__)

SPECIALIZATION_ID = "LFA_COACH"


def enroll_lfa_coach(db: Session, user_id: int) -> Dict[str, Any]:
    """Enroll user in LFA_COACH specialization"""
    # Similar to lfa_player.py but for LFA_COACH
    # ...


def get_lfa_coach_level_requirements(level: int) -> Optional[Dict[str, Any]]:
    """Get level requirements for LFA_COACH"""
    # ...


def get_lfa_coach_progress(db: Session, student_id: int) -> Dict[str, Any]:
    """Get student progress in LFA_COACH"""
    # ...


def get_all_lfa_coach_levels() -> List[Dict[str, Any]]:
    """Get all LFA_COACH levels"""
    # ...
```

---

## 🥋 STEP 4: Create `gancuju.py`

**File:** `app/services/specialization/gancuju.py`

**Purpose:** GANCUJU_PLAYER specific logic (if different from LFA_PLAYER)

**Note:** This might be merged with `lfa_player.py` if they're the same

---

## 💼 STEP 5: Create `internship.py`

**File:** `app/services/specialization/internship.py`

**Purpose:** INTERNSHIP specific logic

**Template:**

```python
"""
INTERNSHIP Specialization Service
Handles internship program progression (3 levels)
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import logging

from ...models.specialization import SpecializationType
from ..specialization_config_loader import get_config_loader
from .validation import specialization_id_to_enum, validate_specialization_exists

logger = logging.getLogger(__name__)

SPECIALIZATION_ID = "INTERNSHIP"


def enroll_internship(db: Session, user_id: int) -> Dict[str, Any]:
    """Enroll user in INTERNSHIP program"""
    # ...


def get_internship_level_requirements(level: int) -> Optional[Dict[str, Any]]:
    """Get level requirements for INTERNSHIP"""
    # ...


def get_internship_progress(db: Session, student_id: int) -> Dict[str, Any]:
    """Get student progress in INTERNSHIP"""
    # ...


def get_all_internship_levels() -> List[Dict[str, Any]]:
    """Get all INTERNSHIP levels (3 levels only)"""
    # ...
```

---

## 🔌 STEP 6: Create `__init__.py` (Public API)

**File:** `app/services/specialization/__init__.py`

```python
"""
Specialization Service
Modular specialization system with validation and spec-specific logic

Provides both generic functions and spec-specific imports
"""

# Validation & Common
from .validation import (
    specialization_id_to_enum,
    handle_legacy_specialization,
    validate_specialization_exists,
    get_all_specializations
)

# LFA_PLAYER (GānCuju)
from .lfa_player import (
    enroll_lfa_player,
    get_lfa_player_level_requirements,
    get_lfa_player_progress,
    get_all_lfa_player_levels
)

# LFA_COACH
from .lfa_coach import (
    enroll_lfa_coach,
    get_lfa_coach_level_requirements,
    get_lfa_coach_progress,
    get_all_lfa_coach_levels
)

# INTERNSHIP
from .internship import (
    enroll_internship,
    get_internship_level_requirements,
    get_internship_progress,
    get_all_internship_levels
)


__all__ = [
    # Validation
    'specialization_id_to_enum',
    'handle_legacy_specialization',
    'validate_specialization_exists',
    'get_all_specializations',

    # LFA_PLAYER
    'enroll_lfa_player',
    'get_lfa_player_level_requirements',
    'get_lfa_player_progress',
    'get_all_lfa_player_levels',

    # LFA_COACH
    'enroll_lfa_coach',
    'get_lfa_coach_level_requirements',
    'get_lfa_coach_progress',
    'get_all_lfa_coach_levels',

    # INTERNSHIP
    'enroll_internship',
    'get_internship_level_requirements',
    'get_internship_progress',
    'get_all_internship_levels'
]


# Backward Compatibility Wrapper (Optional)
class SpecializationService:
    """
    DEPRECATED: Backward compatibility wrapper

    Use direct function imports or spec-specific functions
    """

    def __init__(self, db):
        self.db = db

    def validate_specialization_exists(self, specialization_id: str) -> bool:
        return validate_specialization_exists(specialization_id)

    def enroll_user(self, user_id: int, specialization_id: str):
        # Route to appropriate spec function
        if specialization_id == "GANCUJU_PLAYER":
            return enroll_lfa_player(self.db, user_id)
        elif specialization_id == "LFA_COACH":
            return enroll_lfa_coach(self.db, user_id)
        elif specialization_id == "INTERNSHIP":
            return enroll_internship(self.db, user_id)
        else:
            raise ValueError(f"Unknown specialization: {specialization_id}")

    def get_level_requirements(self, specialization_id: str, level: int):
        if specialization_id == "GANCUJU_PLAYER":
            return get_lfa_player_level_requirements(level)
        elif specialization_id == "LFA_COACH":
            return get_lfa_coach_level_requirements(level)
        elif specialization_id == "INTERNSHIP":
            return get_internship_level_requirements(level)

    def get_student_progress(self, student_id: int, specialization_id: str):
        if specialization_id == "GANCUJU_PLAYER":
            return get_lfa_player_progress(self.db, student_id)
        elif specialization_id == "LFA_COACH":
            return get_lfa_coach_progress(self.db, student_id)
        elif specialization_id == "INTERNSHIP":
            return get_internship_progress(self.db, student_id)

    def get_all_specializations(self):
        return get_all_specializations()
```

---

## 🔄 STEP 7: Update Import Paths

**Search for imports:**
```bash
grep -r "from.*specialization_service import\|import.*specialization_service" app/ --include="*.py"
```

**Update patterns:**

### OLD:
```python
from app.services.specialization_service import SpecializationService

service = SpecializationService(db)
result = service.enroll_user(user_id, "GANCUJU_PLAYER")
```

### NEW (Function-based):
```python
from app.services.specialization import enroll_lfa_player

result = enroll_lfa_player(db, user_id)
```

### BACKWARD COMPATIBLE:
```python
from app.services.specialization import SpecializationService

service = SpecializationService(db)  # Still works
result = service.enroll_user(user_id, "GANCUJU_PLAYER")
```

---

## ✅ STEP 8: Testing

### Unit Tests
- [ ] Test `enroll_lfa_player()` creates correct license
- [ ] Test `enroll_lfa_coach()` creates correct license
- [ ] Test `enroll_internship()` creates correct license
- [ ] Test level requirements retrieval
- [ ] Test progress calculation

### Integration Tests
- [ ] Enroll user in multiple specs
- [ ] Level up in each spec
- [ ] Validate spec-specific logic

---

## 🗑️ STEP 9: Cleanup

```bash
# Backup
mv app/services/specialization_service.py app/services/specialization_service.py.backup

# Test
pytest app/tests/ -v

# If success, delete backup
rm app/services/specialization_service.py.backup
```

---

## 📊 Progress Tracking

- [ ] STEP 1: Create `validation.py`
- [ ] STEP 2: Create `lfa_player.py`
- [ ] STEP 3: Create `lfa_coach.py`
- [ ] STEP 4: Create `gancuju.py` (or merge with lfa_player)
- [ ] STEP 5: Create `internship.py`
- [ ] STEP 6: Create `__init__.py`
- [ ] STEP 7: Update imports
- [ ] STEP 8: Testing
- [ ] STEP 9: Cleanup

---

**Estimated Time:** 4-6 hours
**Difficulty:** ⭐⭐⭐⚪⚪ (3/5)
**Next:** `masters.py` refactoring
