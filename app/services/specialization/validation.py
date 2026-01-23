"""
Specialization Validation & Utilities
Common validation functions and enum handling for all specializations
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from app.models.specialization import SpecializationType
from app.services.specialization_config_loader import get_config_loader

logger = logging.getLogger(__name__)

# DEPRECATION SYSTEM
DEPRECATED_MAPPINGS = {
    "PLAYER": "GANCUJU_PLAYER",
    "COACH": "LFA_COACH"
}
DEPRECATION_DEADLINE = datetime(2026, 5, 18)  # 6 months from now
DEPRECATION_WARNING = """
⚠️ DEPRECATED SPECIALIZATION ID: '{old_id}'
   Use '{new_id}' instead.
   Support for '{old_id}' will be removed on {deadline}.
   Please update your code!
"""


def specialization_id_to_enum(specialization_id: str) -> Optional[SpecializationType]:
    """
    Convert string specialization ID to enum value.
    Supports both old names (PLAYER, COACH) and new names (GANCUJU_PLAYER, LFA_COACH).

    Args:
        specialization_id: String ID (e.g., "PLAYER", "GANCUJU_PLAYER", "LFA_COACH")

    Returns:
        SpecializationType enum or None if invalid
    """
    # Map old names to new enum values for backward compatibility
    legacy_mapping = {
        'PLAYER': SpecializationType.GANCUJU_PLAYER,
        'COACH': SpecializationType.LFA_COACH,
    }

    # Try legacy mapping first
    if specialization_id in legacy_mapping:
        return legacy_mapping[specialization_id]

    # Try direct enum lookup
    try:
        return SpecializationType[specialization_id]
    except KeyError:
        return None


def handle_legacy_specialization(spec_id: str) -> str:
    """
    Handle legacy specialization IDs with deprecation warning.

    Args:
        spec_id: Potentially legacy ID (PLAYER, COACH)

    Returns:
        Mapped new ID if legacy, original ID otherwise

    Raises:
        ValueError: If after deprecation deadline
    """
    if spec_id in DEPRECATED_MAPPINGS:
        new_id = DEPRECATED_MAPPINGS[spec_id]

        # Check if past deadline
        if datetime.now() > DEPRECATION_DEADLINE:
            raise ValueError(
                f"Specialization ID '{spec_id}' is no longer supported. "
                f"Use '{new_id}' instead."
            )

        # Log deprecation warning
        logger.warning(
            DEPRECATION_WARNING.format(
                old_id=spec_id,
                new_id=new_id,
                deadline=DEPRECATION_DEADLINE.strftime('%Y-%m-%d')
            )
        )

        return new_id

    return spec_id


def validate_specialization_exists(db: Session, specialization_id: str) -> bool:
    """
    Check if specialization exists and is active (HYBRID: DB only).

    This is a lightweight check for API endpoints before loading full JSON config.

    Args:
        db: Database session
        specialization_id: Specialization ID to check (handles legacy IDs)

    Returns:
        bool: True if specialization exists in DB and is active
    """
    specialization_id = handle_legacy_specialization(specialization_id)

    spec = db.query(Specialization).filter_by(
        id=specialization_id,
        is_active=True
    ).first()

    return spec is not None


def get_all_specializations(db: Session) -> List[Dict[str, Any]]:
    """
    Get all active specializations (HYBRID: DB + JSON)

    Process:
    1. Load active specializations from DB (is_active check)
    2. Load full definitions from JSON
    3. Merge and return

    This ensures:
    - Only active specializations are returned
    - Full content comes from JSON (Source of Truth)
    - DB maintains referential integrity

    Args:
        db: Database session

    Returns:
        List of specialization dicts with full details from JSON
    """
    config_loader = get_config_loader()

    # STEP 1: Get active specializations from DB
    db_specs = db.query(Specialization).filter_by(is_active=True).all()
    active_ids = {s.id for s in db_specs}  # Set for fast lookup

    # STEP 2 & 3: Load JSON configs for active specializations
    specializations = []

    for spec_enum in SpecializationType:
        spec_id = spec_enum.value

        # Skip if not active in DB
        if spec_id not in active_ids:
            continue

        try:
            # Load full definition from JSON (Source of Truth)
            display_info = config_loader.get_display_info(spec_enum)
            max_level = config_loader.get_max_level(spec_enum)

            specializations.append({
                'id': spec_id,
                'name': display_info['name'],
                'icon': display_info.get('icon', '⚽'),
                'description': display_info['description'],
                'max_levels': max_level,
                'min_age': display_info.get('min_age', 0),
                'color_theme': display_info.get('color_theme', '#000000')
            })
        except FileNotFoundError as e:
            # JSON missing for DB record - CRITICAL ERROR
            logger.error(f"CRITICAL: JSON config missing for active specialization {spec_id}: {e}")
            continue
        except Exception as e:
            logger.error(f"Error loading specialization {spec_id}: {e}")
            continue

    return specializations
