"""
Specialization Configuration Loader

Loads specialization definitions from JSON config files.
This allows for easy updates to level requirements, XP ranges, and other
specialization-specific data without modifying Python code.
"""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from functools import lru_cache

from ..models.specialization import SpecializationType


class SpecializationConfigLoader:
    """
    Loads and caches specialization configurations from JSON files.

    Config files are located in: config/specializations/

    Example structure:
    config/
      specializations/
        gancuju_player.json
        lfa_football_player.json
        lfa_coach.json
        internship.json
    """

    # Map SpecializationType enum values to config file names
    CONFIG_FILE_MAP = {
        SpecializationType.GANCUJU_PLAYER: "gancuju_player.json",
        SpecializationType.LFA_FOOTBALL_PLAYER: "lfa_football_player.json",
        SpecializationType.LFA_COACH: "lfa_coach.json",
        SpecializationType.INTERNSHIP: "internship.json",
    }

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the config loader.

        Args:
            config_dir: Optional custom config directory path.
                       Defaults to: <project_root>/config/specializations/
        """
        if config_dir is None:
            # Get project root (4 levels up from this file)
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "config" / "specializations"

        self.config_dir = Path(config_dir)

        if not self.config_dir.exists():
            raise ValueError(f"Config directory not found: {self.config_dir}")

    @lru_cache(maxsize=10)
    def load_config(self, specialization: SpecializationType) -> Dict[str, Any]:
        """
        Load configuration for a specific specialization.

        Args:
            specialization: The specialization type enum value

        Returns:
            Dict containing the full specialization configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If JSON is invalid or required fields are missing
        """
        # Get config file name
        config_file = self.CONFIG_FILE_MAP.get(specialization)
        if not config_file:
            raise ValueError(f"No config file mapping for specialization: {specialization}")

        # Load JSON file
        config_path = self.config_dir / config_file
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {config_path}: {e}")

        # Validate required fields
        self._validate_config(config, specialization)

        return config

    def _validate_config(self, config: Dict[str, Any], specialization: SpecializationType) -> None:
        """
        Validate that config contains all required fields.

        Args:
            config: The loaded config dict
            specialization: The specialization type (for error messages)

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ["id", "name", "description", "min_age", "levels"]
        missing_fields = [f for f in required_fields if f not in config]

        if missing_fields:
            raise ValueError(
                f"Config for {specialization} missing required fields: {missing_fields}"
            )

        # Validate levels array
        if not isinstance(config["levels"], list) or len(config["levels"]) == 0:
            raise ValueError(f"Config for {specialization} must have at least one level")

        # Validate each level has required fields
        level_required_fields = ["level", "name", "xp_required", "xp_max"]
        for idx, level in enumerate(config["levels"]):
            missing = [f for f in level_required_fields if f not in level]
            if missing:
                raise ValueError(
                    f"Level {idx} in {specialization} config missing fields: {missing}"
                )

    def get_level_config(self, specialization: SpecializationType, level: int) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific level within a specialization.

        Args:
            specialization: The specialization type
            level: The level number (1-based)

        Returns:
            Dict containing level configuration, or None if level doesn't exist
        """
        config = self.load_config(specialization)
        levels = config.get("levels", [])

        for level_config in levels:
            if level_config.get("level") == level:
                return level_config

        return None

    def get_xp_range(self, specialization: SpecializationType, level: int) -> tuple[int, int]:
        """
        Get XP range (min, max) for a specific level.

        Args:
            specialization: The specialization type
            level: The level number

        Returns:
            Tuple of (xp_required, xp_max) for the level

        Raises:
            ValueError: If level doesn't exist
        """
        level_config = self.get_level_config(specialization, level)
        if not level_config:
            raise ValueError(f"Level {level} not found for {specialization}")

        return (level_config["xp_required"], level_config["xp_max"])

    def get_max_level(self, specialization: SpecializationType) -> int:
        """
        Get the maximum level number for a specialization.

        Args:
            specialization: The specialization type

        Returns:
            The highest level number
        """
        config = self.load_config(specialization)
        levels = config.get("levels", [])
        return max(level["level"] for level in levels)

    def get_level_name(self, specialization: SpecializationType, level: int, english: bool = False) -> str:
        """
        Get the display name for a level.

        Args:
            specialization: The specialization type
            level: The level number
            english: If True, return English name (if available), otherwise return default name

        Returns:
            The level name string
        """
        level_config = self.get_level_config(specialization, level)
        if not level_config:
            return f"Level {level}"

        if english and "name_en" in level_config:
            return level_config["name_en"]

        return level_config.get("name", f"Level {level}")

    def get_level_requirements(self, specialization: SpecializationType, level: int) -> Dict[str, Any]:
        """
        Get requirements for reaching a specific level.

        Args:
            specialization: The specialization type
            level: The level number

        Returns:
            Dict containing requirements (theory_hours, practice_hours, skills, etc.)
        """
        level_config = self.get_level_config(specialization, level)
        if not level_config:
            return {}

        return level_config.get("requirements", {})

    def get_age_groups(self, specialization: SpecializationType) -> List[Dict[str, Any]]:
        """
        Get age group definitions for specializations that use them
        (LFA_FOOTBALL_PLAYER, LFA_COACH).

        Args:
            specialization: The specialization type

        Returns:
            List of age group definitions, or empty list if not applicable
        """
        config = self.load_config(specialization)
        return config.get("age_groups", [])

    def get_display_info(self, specialization: SpecializationType) -> Dict[str, Any]:
        """
        Get display information (name, description, icon, color theme).

        Args:
            specialization: The specialization type

        Returns:
            Dict with display-related fields
        """
        config = self.load_config(specialization)
        return {
            "id": config.get("id"),
            "name": config.get("name"),
            "description": config.get("description"),
            "icon": config.get("icon"),
            "color_theme": config.get("color_theme"),
            "min_age": config.get("min_age"),
        }

    def clear_cache(self) -> None:
        """
        Clear the config cache. Useful for testing or when configs are updated.
        """
        self.load_config.cache_clear()


# Global singleton instance
_loader_instance: Optional[SpecializationConfigLoader] = None


def get_config_loader() -> SpecializationConfigLoader:
    """
    Get the global config loader singleton instance.

    Returns:
        SpecializationConfigLoader instance
    """
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = SpecializationConfigLoader()
    return _loader_instance


def load_specialization_config(specialization: SpecializationType) -> Dict[str, Any]:
    """
    Convenience function to load a specialization config.

    Args:
        specialization: The specialization type

    Returns:
        Dict containing the full specialization configuration
    """
    loader = get_config_loader()
    return loader.load_config(specialization)
