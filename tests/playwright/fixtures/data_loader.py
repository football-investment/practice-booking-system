"""
Test Data Loader - JSON-based test fixture management

Loads and validates test data from JSON files against the schema.
Provides easy access to test users, locations, tournaments, etc.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import jsonschema


class TestDataLoader:
    """Load and validate test data from JSON fixtures"""

    def __init__(self, fixture_name: str = "tournament_test_data"):
        """
        Initialize test data loader.

        Args:
            fixture_name: Name of the JSON fixture file (without .json extension)
        """
        self.fixture_dir = Path(__file__).parent
        self.fixture_path = self.fixture_dir / f"{fixture_name}.json"
        self.schema_path = self.fixture_dir / "test_data_schema.json"

        # Load data
        self.data = self._load_json(self.fixture_path)
        self.schema = self._load_json(self.schema_path)

        # Validate
        self._validate()

    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON file"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _validate(self):
        """Validate data against schema"""
        try:
            jsonschema.validate(instance=self.data, schema=self.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Test data validation failed: {e.message}")

    # ========================================================================
    # USER ACCESSORS
    # ========================================================================

    def get_admin(self, index: int = 0) -> Dict[str, Any]:
        """Get admin user by index (default: first admin)"""
        admins = self.data.get('users', {}).get('admins', [])
        if not admins:
            raise ValueError("No admin users found in test data")
        return admins[index]

    def get_instructor(self, email: Optional[str] = None, index: int = 0) -> Dict[str, Any]:
        """
        Get instructor by email or index.

        Args:
            email: Instructor email (optional)
            index: Instructor index if email not provided

        Returns:
            Instructor data dict
        """
        instructors = self.data.get('users', {}).get('instructors', [])
        if not instructors:
            raise ValueError("No instructors found in test data")

        if email:
            for instructor in instructors:
                if instructor.get('email') == email:
                    return instructor
            raise ValueError(f"Instructor with email '{email}' not found")

        return instructors[index]

    def get_player(self, email: Optional[str] = None, index: int = 0) -> Dict[str, Any]:
        """
        Get player by email or index.

        Args:
            email: Player email (optional)
            index: Player index if email not provided

        Returns:
            Player data dict (includes onboarding_data if present)
        """
        players = self.data.get('users', {}).get('players', [])
        if not players:
            raise ValueError("No players found in test data")

        if email:
            for player in players:
                if player.get('email') == email:
                    return player
            raise ValueError(f"Player with email '{email}' not found")

        return players[index]

    def get_all_players(self) -> List[Dict[str, Any]]:
        """Get all test players"""
        return self.data.get('users', {}).get('players', [])

    # ========================================================================
    # LOCATION ACCESSORS
    # ========================================================================

    def get_location(self, name: Optional[str] = None, index: int = 0) -> Dict[str, Any]:
        """Get location by name or index"""
        locations = self.data.get('locations', [])
        if not locations:
            raise ValueError("No locations found in test data")

        if name:
            for loc in locations:
                if loc.get('name') == name:
                    return loc
            raise ValueError(f"Location '{name}' not found")

        return locations[index]

    def get_campus(self, location_name: str, campus_index: int = 0) -> Dict[str, Any]:
        """Get campus from a location"""
        location = self.get_location(name=location_name)
        campuses = location.get('campuses', [])
        if not campuses:
            raise ValueError(f"No campuses found for location '{location_name}'")
        return campuses[campus_index]

    # ========================================================================
    # TOURNAMENT ACCESSORS
    # ========================================================================

    def get_tournament(self, name: Optional[str] = None, assignment_type: Optional[str] = None, index: int = 0) -> Dict[str, Any]:
        """
        Get tournament by name, assignment type, or index.

        Args:
            name: Tournament name (partial match)
            assignment_type: Filter by assignment type (OPEN_ASSIGNMENT or APPLICATION_BASED)
            index: Tournament index if no filters provided

        Returns:
            Tournament template data
        """
        tournaments = self.data.get('tournaments', [])
        if not tournaments:
            raise ValueError("No tournaments found in test data")

        # Filter by assignment_type
        if assignment_type:
            tournaments = [t for t in tournaments if t.get('assignment_type') == assignment_type]

        # Filter by name (partial match)
        if name:
            tournaments = [t for t in tournaments if name.lower() in t.get('name', '').lower()]

        if not tournaments:
            raise ValueError(f"No tournaments found matching criteria")

        return tournaments[index]

    def get_tournament_with_dates(self, **kwargs) -> Dict[str, Any]:
        """
        Get tournament template with calculated dates.

        Returns tournament dict with:
        - start_date: Calculated from start_date_offset_days
        - end_date: Same as start_date (single-day tournament)
        """
        tournament = self.get_tournament(**kwargs)

        # Calculate dates
        offset_days = tournament.get('start_date_offset_days', 7)
        start_date = datetime.now() + timedelta(days=offset_days)

        # Add calculated fields
        tournament['start_date'] = start_date.strftime('%Y-%m-%d')
        tournament['end_date'] = start_date.strftime('%Y-%m-%d')  # Same day tournament

        return tournament

    # ========================================================================
    # COUPON ACCESSORS
    # ========================================================================

    def get_coupon(self, code: Optional[str] = None, assigned_to: Optional[str] = None, index: int = 0) -> Dict[str, Any]:
        """
        Get coupon by code or assigned email.

        Args:
            code: Coupon code
            assigned_to: User email the coupon is assigned to
            index: Coupon index if no filters

        Returns:
            Coupon data dict
        """
        coupons = self.data.get('coupons', [])
        if not coupons:
            raise ValueError("No coupons found in test data")

        if code:
            for coupon in coupons:
                if coupon.get('code') == code:
                    return coupon
            raise ValueError(f"Coupon '{code}' not found")

        if assigned_to:
            for coupon in coupons:
                if coupon.get('assigned_to_email') == assigned_to:
                    return coupon
            raise ValueError(f"No coupon assigned to '{assigned_to}'")

        return coupons[index]

    def get_coupons_for_player(self, email: str) -> List[Dict[str, Any]]:
        """Get all coupons assigned to a specific player"""
        coupons = self.data.get('coupons', [])
        return [c for c in coupons if c.get('assigned_to_email') == email]

    # ========================================================================
    # CONVENIENCE METHODS
    # ========================================================================

    def get_credentials(self, email: str) -> Dict[str, str]:
        """
        Get login credentials for any user by email.

        Returns:
            Dict with 'email' and 'password' keys
        """
        # Search in all user types
        all_users = (
            self.data.get('users', {}).get('admins', []) +
            self.data.get('users', {}).get('instructors', []) +
            self.data.get('users', {}).get('players', [])
        )

        for user in all_users:
            if user.get('email') == email:
                return {
                    'email': user['email'],
                    'password': user['password']
                }

        raise ValueError(f"User with email '{email}' not found")
