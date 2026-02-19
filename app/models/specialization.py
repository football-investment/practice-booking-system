"""
🎓 User Specialization Models and Enums
Defines the Player/Coach specialization system for the LFA education platform
"""
import enum


class SpecializationType(enum.Enum):
    """Specialization types for users and semesters/seasons

    ═══════════════════════════════════════════════════════════════════════════
    4 USER LICENSE TYPES (what users can BE in user_licenses table):
    ═══════════════════════════════════════════════════════════════════════════
    - LFA_COACH: Coach license (8 levels, teaches players/coaches)
    - LFA_FOOTBALL_PLAYER: Player license (8 levels, ONE unified specialization)
    - GANCUJU_PLAYER: GānCuju player (8 belt system)
    - INTERNSHIP: Internship program (3 levels)

    ═══════════════════════════════════════════════════════════════════════════
    11 SEMESTER/SEASON TYPES (what semesters teach - semesters table ONLY):
    ═══════════════════════════════════════════════════════════════════════════
    - LFA_PLAYER_PRE: Mini Seasons for PRE age group (5-13 years, monthly M01-M12) - SEASON TYPE ONLY
    - LFA_PLAYER_YOUTH: Mini Seasons for YOUTH age group (14-18 years, quarterly Q1-Q4) - SEASON TYPE ONLY
    - LFA_PLAYER_AMATEUR: Mini Seasons for AMATEUR age group (14+ years, quarterly Q1-Q4) - SEASON TYPE ONLY
    - LFA_PLAYER_PRO: Mini Seasons for PRO age group (14+ years, quarterly Q1-Q4) - SEASON TYPE ONLY
    - LFA_PLAYER_PRE_ACADEMY: Academy Season for PRE (5-13 years, full year Jul-Jun) - SEASON TYPE ONLY
    - LFA_PLAYER_YOUTH_ACADEMY: Academy Season for YOUTH (14-18 years, full year Jul-Jun) - SEASON TYPE ONLY
    - LFA_PLAYER_AMATEUR_ACADEMY: Academy Season for AMATEUR (14+ years, full year Jul-Jun) - SEASON TYPE ONLY
    - LFA_PLAYER_PRO_ACADEMY: Academy Season for PRO (14+ years, full year Jul-Jun) - SEASON TYPE ONLY
    - GANCUJU_PLAYER: Also used for seasons
    - LFA_COACH: Also used for seasons
    - INTERNSHIP: Also used for seasons

    ⚠️ CRITICAL RULES:
    ═══════════════════════════════════════════════════════════════════════════
    1. Users can ONLY have these in user_licenses.specialization_type:
       - LFA_COACH
       - LFA_FOOTBALL_PLAYER (NOT PRE/YOUTH/AMATEUR/PRO!)
       - GANCUJU_PLAYER
       - INTERNSHIP

    2. Semesters can have these in semesters.specialization_type:
       - LFA_PLAYER_PRE/YOUTH/AMATEUR/PRO (for age-specific semesters)
       - LFA_FOOTBALL_PLAYER (for tournaments/general sessions)
       - LFA_COACH, GANCUJU_PLAYER, INTERNSHIP

    3. Age groups (PRE/YOUTH/AMATEUR/PRO) are determined by:
       - User's age AT SEASON START (July 1)
       - Season lock: stays fixed for entire season (July 1 - June 30)
       - Follows international football practice
    """
    # User license types (CAN be assigned to users)
    GANCUJU_PLAYER = "GANCUJU_PLAYER"
    LFA_FOOTBALL_PLAYER = "LFA_FOOTBALL_PLAYER"  # ✅ User license - unified player specialization
    LFA_COACH = "LFA_COACH"
    INTERNSHIP = "INTERNSHIP"

    # Season/semester types ONLY (NEVER assigned to users as license!)
    LFA_PLAYER_PRE = "LFA_PLAYER_PRE"           # ⚠️ SEMESTER type only (NOT user license)
    LFA_PLAYER_YOUTH = "LFA_PLAYER_YOUTH"       # ⚠️ SEMESTER type only (NOT user license)
    LFA_PLAYER_AMATEUR = "LFA_PLAYER_AMATEUR"   # ⚠️ SEMESTER type only (NOT user license)
    LFA_PLAYER_PRO = "LFA_PLAYER_PRO"           # ⚠️ SEMESTER type only (NOT user license)

    # NEW: Academy Season types (full-year programs, July 1 - June 30)
    LFA_PLAYER_PRE_ACADEMY = "LFA_PLAYER_PRE_ACADEMY"             # ⚠️ SEMESTER type only - PRE Academy
    LFA_PLAYER_YOUTH_ACADEMY = "LFA_PLAYER_YOUTH_ACADEMY"         # ⚠️ SEMESTER type only - YOUTH Academy
    LFA_PLAYER_AMATEUR_ACADEMY = "LFA_PLAYER_AMATEUR_ACADEMY"     # ⚠️ SEMESTER type only - AMATEUR Academy
    LFA_PLAYER_PRO_ACADEMY = "LFA_PLAYER_PRO_ACADEMY"             # ⚠️ SEMESTER type only - PRO Academy