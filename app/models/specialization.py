"""
🎓 User Specialization Models and Enums
Defines the Player/Coach specialization system for the LFA education platform
"""
import enum
from typing import Optional


class SpecializationType(enum.Enum):
    """User specialization types for the LFA education system

    7 SPECIALIZÁCIÓ:
    - GANCUJU_PLAYER: 4000 éves Cuju hagyomány (8 öv rendszer)
    - LFA_PLAYER_PRE: LFA Football PRE (4-8 év, havi szemeszterek)
    - LFA_PLAYER_YOUTH: LFA Football Youth (8-14 év, negyedéves)
    - LFA_PLAYER_AMATEUR: LFA Football Amateur (14+ év, féléves)
    - LFA_PLAYER_PRO: LFA Football PRO (16+ év, éves)
    - LFA_COACH: LFA Coach (4 korosztály, 8 szint, 14+ belépés)
    - INTERNSHIP: Gyakornoki program (3 szint, startup fókusz)

    HYBRID ARCHITECTURE:
    - Enum provides TYPE SAFETY only (string constants)
    - JSON configs provide CONTENT (names, descriptions, features)
    - Service layer bridges DB validation + JSON content

    ❌ NO HELPER METHODS - use SpecializationConfigLoader instead!
    """
    GANCUJU_PLAYER = "GANCUJU_PLAYER"           # Formerly: PLAYER
    LFA_PLAYER_PRE = "LFA_PLAYER_PRE"           # NEW: 4-8 years, monthly
    LFA_PLAYER_YOUTH = "LFA_PLAYER_YOUTH"       # NEW: 8-14 years, quarterly
    LFA_PLAYER_AMATEUR = "LFA_PLAYER_AMATEUR"   # NEW: 14+ years, semi-annual
    LFA_PLAYER_PRO = "LFA_PLAYER_PRO"           # NEW: 16+ years, annual
    LFA_FOOTBALL_PLAYER = "LFA_FOOTBALL_PLAYER" # DEPRECATED - kept for backwards compatibility
    LFA_COACH = "LFA_COACH"                     # Formerly: COACH
    INTERNSHIP = "INTERNSHIP"                   # Unchanged