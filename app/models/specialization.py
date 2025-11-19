"""
🎓 User Specialization Models and Enums
Defines the Player/Coach specialization system for the LFA education platform
"""
import enum
from typing import Optional


class SpecializationType(enum.Enum):
    """User specialization types for the LFA education system

    4 SPECIALIZÁCIÓ:
    - GANCUJU_PLAYER: 4000 éves Cuju hagyomány (8 öv rendszer)
    - LFA_FOOTBALL_PLAYER: LFA Football játékos (4 korosztály, 8 szint)
    - LFA_COACH: LFA Coach (4 korosztály, 8 szint, 14+ belépés)
    - INTERNSHIP: Gyakornoki program (3 szint, startup fókusz)

    HYBRID ARCHITECTURE:
    - Enum provides TYPE SAFETY only (string constants)
    - JSON configs provide CONTENT (names, descriptions, features)
    - Service layer bridges DB validation + JSON content

    ❌ NO HELPER METHODS - use SpecializationConfigLoader instead!
    """
    GANCUJU_PLAYER = "GANCUJU_PLAYER"           # Formerly: PLAYER
    LFA_FOOTBALL_PLAYER = "LFA_FOOTBALL_PLAYER" # NEW!
    LFA_COACH = "LFA_COACH"                     # Formerly: COACH
    INTERNSHIP = "INTERNSHIP"                   # Unchanged