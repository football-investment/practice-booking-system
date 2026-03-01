"""
Pydantic schemas for Game Presets API
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Dict, Any, Optional, List
from datetime import datetime


class GameConfigBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Base game configuration structure"""
    version: str = Field(..., description="Configuration version")
    format_config: Dict[str, Any] = Field(..., description="Format-specific configuration")
    skill_config: Dict[str, Any] = Field(..., description="Skill testing configuration")
    simulation_config: Dict[str, Any] = Field(..., description="Simulation parameters")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class GamePresetBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Base game preset fields"""
    code: str = Field(..., min_length=1, max_length=50, description="Unique preset code")
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    description: Optional[str] = Field(None, description="Game description")
    game_config: Dict[str, Any] = Field(..., description="Complete game configuration")

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate code format (lowercase, underscores only)"""
        if not v.replace('_', '').isalnum():
            raise ValueError("Code must contain only alphanumeric characters and underscores")
        if v != v.lower():
            raise ValueError("Code must be lowercase")
        return v

    @field_validator('game_config')
    @classmethod
    def validate_game_config(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate required game_config sections"""
        required_sections = ['version', 'format_config', 'skill_config', 'simulation_config']
        missing = [s for s in required_sections if s not in v]
        if missing:
            raise ValueError(f"Missing required sections: {missing}")
        return v


class GamePresetCreate(GamePresetBase):
    """Schema for creating a game preset"""
    is_active: bool = Field(default=True, description="Whether preset is active")
    created_by: Optional[int] = Field(None, description="Creator user ID")


class GamePresetUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for updating a game preset"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    game_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

    @field_validator('game_config')
    @classmethod
    def validate_game_config(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate required game_config sections if provided"""
        if v is not None:
            required_sections = ['version', 'format_config', 'skill_config', 'simulation_config']
            missing = [s for s in required_sections if s not in v]
            if missing:
                raise ValueError(f"Missing required sections: {missing}")
        return v


class GamePresetResponse(GamePresetBase):
    """Schema for game preset response"""
    id: int
    is_active: bool
    is_recommended: bool = Field(default=False)
    is_locked: bool = Field(default=False)
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class GamePresetSummary(BaseModel):
    """Lightweight game preset summary"""
    id: int
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool
    is_recommended: bool = Field(default=False, description="Whether this is a recommended preset")
    is_locked: bool = Field(default=False, description="Whether configuration is locked")

    # Extracted metadata (manually populated, not from_attributes)
    skills_tested: Optional[List[str]] = Field(default=None)
    game_category: Optional[str] = None
    difficulty_level: Optional[str] = None
    recommended_player_count: Optional[Dict[str, int]] = None


class GamePresetListResponse(BaseModel):
    """Response for listing game presets"""
    presets: List[GamePresetSummary]
    total: int
    active_count: int
