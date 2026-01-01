"""
🏫 Location Validation Service
Validates semester creation based on location capabilities (PARTNER vs CENTER)

Business Rules:
- PARTNER locations: Can host Tournament + Mini Season only
- CENTER locations: Can host all types including Academy Season
"""
from sqlalchemy.orm import Session
from typing import Dict, List
from app.models.location import Location, LocationType
from app.models.specialization import SpecializationType


class LocationValidationService:
    """Service for validating location capabilities vs semester types"""

    # Semester types that require CENTER location (Academy Seasons only)
    CENTER_ONLY_TYPES = [
        SpecializationType.LFA_PLAYER_PRE_ACADEMY,
        SpecializationType.LFA_PLAYER_YOUTH_ACADEMY,
        SpecializationType.LFA_PLAYER_AMATEUR_ACADEMY,  # NEW: AMATEUR Academy
        SpecializationType.LFA_PLAYER_PRO_ACADEMY        # NEW: PRO Academy
    ]

    # Semester types allowed at PARTNER locations (Mini Seasons + Tournaments)
    PARTNER_ALLOWED_TYPES = [
        # Mini Seasons (quarterly/monthly)
        SpecializationType.LFA_PLAYER_PRE,
        SpecializationType.LFA_PLAYER_YOUTH,
        SpecializationType.LFA_PLAYER_AMATEUR,  # MOVED: Now quarterly mini season
        SpecializationType.LFA_PLAYER_PRO,      # MOVED: Now quarterly mini season
        # General types (also used for tournaments)
        SpecializationType.LFA_FOOTBALL_PLAYER,
        SpecializationType.LFA_COACH,
        SpecializationType.GANCUJU_PLAYER,
        SpecializationType.INTERNSHIP
    ]

    @staticmethod
    def can_create_semester_at_location(
        location_id: int,
        specialization_type: SpecializationType,
        db: Session
    ) -> Dict:
        """
        Check if a location can host a semester of given type.

        Returns:
        {
            "allowed": bool,
            "location_type": str,
            "reason": str or None
        }
        """
        # Get location
        location = db.query(Location).filter(Location.id == location_id).first()

        if not location:
            return {
                "allowed": False,
                "location_type": None,
                "reason": "Location not found"
            }

        location_type = location.location_type

        # CENTER locations can host anything
        if location_type == LocationType.CENTER:
            return {
                "allowed": True,
                "location_type": "CENTER",
                "reason": None
            }

        # PARTNER locations - check restrictions
        if location_type == LocationType.PARTNER:
            # Check if semester type is Academy or Annual (CENTER only)
            if specialization_type in LocationValidationService.CENTER_ONLY_TYPES:
                return {
                    "allowed": False,
                    "location_type": "PARTNER",
                    "reason": f"Academy Season és Annual programok csak CENTER helyszínen hozhatók létre. {location.city} PARTNER szintű helyszín."
                }

            # PARTNER can host Mini Seasons, Tournaments, and other types
            return {
                "allowed": True,
                "location_type": "PARTNER",
                "reason": None
            }

        return {
            "allowed": False,
            "location_type": str(location_type),
            "reason": "Ismeretlen helyszín típus"
        }

    @staticmethod
    def get_allowed_semester_types(location_id: int, db: Session) -> List[str]:
        """Get list of semester types this location can host"""
        location = db.query(Location).filter(Location.id == location_id).first()

        if not location:
            return []

        if location.location_type == LocationType.CENTER:
            # CENTER can host all types
            return [
                "Tournament (minden korosztály)",
                "Mini Season (PRE, YOUTH, AMATEUR, PRO)",
                "Academy Season (PRE, YOUTH, AMATEUR, PRO)"
            ]
        else:
            # PARTNER can host Tournament + Mini Season only
            return [
                "Tournament (minden korosztály)",
                "Mini Season (PRE, YOUTH, AMATEUR, PRO)"
            ]

    @staticmethod
    def get_location_type_display(location_type: LocationType) -> str:
        """Get human-readable location type display"""
        if location_type == LocationType.CENTER:
            return "🏫 CENTER (Teljes hozzáférés)"
        else:
            return "🤝 PARTNER"

    @staticmethod
    def get_location_capabilities(location_type: LocationType) -> str:
        """Get location capabilities description"""
        if location_type == LocationType.CENTER:
            return "✅ Tornák, Mini Szezonok, Academy Szezonok"
        else:
            return "✅ Tornák, Mini Szezonok"
