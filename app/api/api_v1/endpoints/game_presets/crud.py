"""
CRUD operations for Game Presets
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models import GamePreset


def get_all_presets(db: Session, active_only: bool = True) -> List[GamePreset]:
    """
    Get all game presets

    Args:
        db: Database session
        active_only: If True, only return active presets

    Returns:
        List of GamePreset objects
    """
    query = db.query(GamePreset)

    if active_only:
        query = query.filter(GamePreset.is_active == True)

    return query.order_by(GamePreset.name).all()


def get_preset_by_id(db: Session, preset_id: int) -> Optional[GamePreset]:
    """
    Get game preset by ID

    Args:
        db: Database session
        preset_id: Preset ID

    Returns:
        GamePreset object or None
    """
    return db.query(GamePreset).filter(GamePreset.id == preset_id).first()


def get_preset_by_code(db: Session, code: str) -> Optional[GamePreset]:
    """
    Get game preset by code

    Args:
        db: Database session
        code: Preset code (e.g., 'gan_footvolley')

    Returns:
        GamePreset object or None
    """
    return db.query(GamePreset).filter(GamePreset.code == code).first()


def create_preset(
    db: Session,
    code: str,
    name: str,
    game_config: Dict[str, Any],
    description: Optional[str] = None,
    created_by: Optional[int] = None
) -> GamePreset:
    """
    Create new game preset

    Args:
        db: Database session
        code: Unique preset code
        name: Display name
        game_config: Complete game configuration JSON
        description: Optional description
        created_by: Optional creator user ID

    Returns:
        Created GamePreset object
    """
    preset = GamePreset(
        code=code,
        name=name,
        description=description,
        game_config=game_config,
        is_active=True,
        created_by=created_by
    )

    db.add(preset)
    db.commit()
    db.refresh(preset)

    return preset


def update_preset(
    db: Session,
    preset_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    game_config: Optional[Dict[str, Any]] = None,
    is_active: Optional[bool] = None
) -> Optional[GamePreset]:
    """
    Update game preset

    Args:
        db: Database session
        preset_id: Preset ID to update
        name: New name (optional)
        description: New description (optional)
        game_config: New game config (optional)
        is_active: New active status (optional)

    Returns:
        Updated GamePreset object or None if not found
    """
    preset = get_preset_by_id(db, preset_id)

    if not preset:
        return None

    if name is not None:
        preset.name = name
    if description is not None:
        preset.description = description
    if game_config is not None:
        preset.game_config = game_config
    if is_active is not None:
        preset.is_active = is_active

    db.commit()
    db.refresh(preset)

    return preset


def soft_delete_preset(db: Session, preset_id: int) -> Optional[GamePreset]:
    """
    Soft delete game preset (set is_active = False)

    Args:
        db: Database session
        preset_id: Preset ID to delete

    Returns:
        Updated GamePreset object or None if not found
    """
    return update_preset(db, preset_id, is_active=False)


def hard_delete_preset(db: Session, preset_id: int) -> bool:
    """
    Hard delete game preset (remove from database)

    ⚠️ WARNING: This will fail if any tournaments reference this preset

    Args:
        db: Database session
        preset_id: Preset ID to delete

    Returns:
        True if deleted, False if not found
    """
    preset = get_preset_by_id(db, preset_id)

    if not preset:
        return False

    db.delete(preset)
    db.commit()

    return True
