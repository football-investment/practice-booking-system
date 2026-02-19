"""
API Router for Game Presets
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.dependencies import get_current_user, get_current_admin_user
from app.models import User
from . import crud, schemas


router = APIRouter()


@router.get("/", response_model=schemas.GamePresetListResponse)
def list_game_presets(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    List all game presets

    Args:
        active_only: If True, only return active presets (default: True)

    Returns:
        List of game presets with summary info
    """
    presets = crud.get_all_presets(db, active_only=active_only)

    # Convert to summary format
    preset_summaries = []
    for preset in presets:
        # Manually extract metadata from JSONB
        game_config = preset.game_config or {}
        skill_config = game_config.get("skill_config", {})
        metadata = game_config.get("metadata", {})

        preset_summaries.append(
            schemas.GamePresetSummary(
                id=preset.id,
                code=preset.code,
                name=preset.name,
                description=preset.description,
                is_active=preset.is_active,
                is_recommended=preset.is_recommended,
                is_locked=preset.is_locked,
                skills_tested=skill_config.get("skills_tested", []),
                game_category=metadata.get("game_category"),
                difficulty_level=metadata.get("difficulty_level"),
                recommended_player_count=metadata.get("recommended_player_count")
            )
        )

    all_presets = crud.get_all_presets(db, active_only=False)
    active_count = sum(1 for p in all_presets if p.is_active)

    return schemas.GamePresetListResponse(
        presets=preset_summaries,
        total=len(all_presets),
        active_count=active_count
    )


@router.get("/{preset_id}", response_model=schemas.GamePresetResponse)
def get_game_preset(
    preset_id: int,
    db: Session = Depends(get_db)
):
    """
    Get game preset by ID with full configuration

    Args:
        preset_id: Preset ID

    Returns:
        Full game preset details including game_config
    """
    preset = crud.get_preset_by_id(db, preset_id)

    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game preset with ID {preset_id} not found"
        )

    return preset


@router.get("/code/{code}", response_model=schemas.GamePresetResponse)
def get_game_preset_by_code(
    code: str,
    db: Session = Depends(get_db)
):
    """
    Get game preset by code with full configuration

    Args:
        code: Preset code (e.g., 'gan_footvolley')

    Returns:
        Full game preset details including game_config
    """
    preset = crud.get_preset_by_code(db, code)

    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game preset with code '{code}' not found"
        )

    return preset


@router.post("/", response_model=schemas.GamePresetResponse, status_code=status.HTTP_201_CREATED)
def create_game_preset(
    preset_data: schemas.GamePresetCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create new game preset (Admin only)

    Args:
        preset_data: Preset configuration
        current_user: Authenticated admin user

    Returns:
        Created game preset
    """
    # Check if code already exists
    existing = crud.get_preset_by_code(db, preset_data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Game preset with code '{preset_data.code}' already exists"
        )

    # Create preset
    preset = crud.create_preset(
        db=db,
        code=preset_data.code,
        name=preset_data.name,
        game_config=preset_data.game_config,
        description=preset_data.description,
        created_by=current_user.id
    )

    return preset


@router.patch("/{preset_id}", response_model=schemas.GamePresetResponse)
def update_game_preset(
    preset_id: int,
    preset_data: schemas.GamePresetUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update game preset (Admin only)

    Args:
        preset_id: Preset ID to update
        preset_data: Updated preset data
        current_user: Authenticated admin user

    Returns:
        Updated game preset
    """
    preset = crud.update_preset(
        db=db,
        preset_id=preset_id,
        name=preset_data.name,
        description=preset_data.description,
        game_config=preset_data.game_config,
        is_active=preset_data.is_active
    )

    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game preset with ID {preset_id} not found"
        )

    return preset


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_game_preset(
    preset_id: int,
    hard_delete: bool = False,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete game preset (Admin only)

    Args:
        preset_id: Preset ID to delete
        hard_delete: If True, permanently delete. If False, soft delete (set is_active=False)
        current_user: Authenticated admin user

    Returns:
        204 No Content on success
    """
    if hard_delete:
        success = crud.hard_delete_preset(db, preset_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game preset with ID {preset_id} not found"
            )
    else:
        preset = crud.soft_delete_preset(db, preset_id)
        if not preset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game preset with ID {preset_id} not found"
            )

    return None
