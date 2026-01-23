# Test Data Fixtures - JSON-Based Test Configuration

## Overview

This directory contains JSON-based test data fixtures for E2E Playwright tests. Instead of hardcoding test data in Python files, we use a centralized JSON configuration that's:

- ✅ **Easy to maintain** - Change test data without touching code
- ✅ **Schema-validated** - Catches errors early with JSON Schema validation
- ✅ **Type-safe** - Clear data structure defined in schema
- ✅ **Reusable** - Same data across multiple tests
- ✅ **Readable** - Non-developers can understand and modify test data

## Files

### `test_data_schema.json`
JSON Schema defining the structure and validation rules for test data.

Defines:
- User types (admin, instructor, player)
- Locations and campuses
- Tournament templates
- Coupons

### `tournament_test_data.json`
Main test data file for tournament E2E tests.

Contains:
- 1 admin user
- 1 grandmaster instructor (with LFA_COACH level 8 licenses)
- 3 test players (onboarded, with addresses)
- 2 locations with campuses
- 2 tournament templates (APPLICATION_BASED and OPEN_ASSIGNMENT)
- 3 enrollment coupons

### `data_loader.py`
Python module for loading and accessing test data.

Provides:
- JSON loading with schema validation
- Convenient accessor methods (get_admin, get_player, etc.)
- Date calculations for tournaments
- Credential helpers

## Usage

### In Pytest Tests

```python
def test_something(test_data, admin_credentials):
    """Test using fixture data"""
    # Get admin credentials (from fixture)
    email = admin_credentials["email"]
    password = admin_credentials["password"]

    # Or access directly
    admin = test_data.get_admin()

    # Get specific player
    player = test_data.get_player(email="pwt.k1sqx1@f1stteam.hu")

    # Get tournament template
    tournament = test_data.get_tournament(assignment_type="APPLICATION_BASED")

    # Get tournament with calculated dates
    tournament_with_dates = test_data.get_tournament_with_dates(
        assignment_type="APPLICATION_BASED"
    )
```

### Available Fixtures

#### `test_data` (session-scoped)
Main fixture providing access to all test data.

```python
def test_example(test_data):
    admin = test_data.get_admin()
    instructor = test_data.get_instructor(email="grandmaster@lfa.com")
    player = test_data.get_player(index=0)
    location = test_data.get_location(name="Budapest Sports Complex")
    tournament = test_data.get_tournament(assignment_type="APPLICATION_BASED")
    coupon = test_data.get_coupon(code="E2E-ENROLL-500-USER1")
```

#### `admin_credentials` (function-scoped)
Returns `{"email": "...", "password": "..."}` for admin.

```python
def test_admin_login(admin_credentials):
    email = admin_credentials["email"]
    password = admin_credentials["password"]
```

#### `instructor_credentials` (function-scoped)
Returns `{"email": "...", "password": "..."}` for grandmaster instructor.

#### `player_credentials` (function-scoped)
Returns `{"email": "...", "password": "..."}` for first player.

## Data Accessor Methods

### Users

```python
# Get admin (first by default)
admin = test_data.get_admin()
admin = test_data.get_admin(index=0)

# Get instructor
instructor = test_data.get_instructor()  # First instructor
instructor = test_data.get_instructor(email="grandmaster@lfa.com")
instructor = test_data.get_instructor(index=0)

# Get player
player = test_data.get_player()  # First player
player = test_data.get_player(email="pwt.k1sqx1@f1stteam.hu")
player = test_data.get_player(index=1)

# Get all players
all_players = test_data.get_all_players()

# Get credentials for any user
creds = test_data.get_credentials(email="admin@lfa.com")
# Returns: {"email": "admin@lfa.com", "password": "admin123"}
```

### Locations

```python
# Get location
location = test_data.get_location()  # First location
location = test_data.get_location(name="Budapest Sports Complex")
location = test_data.get_location(index=0)

# Get campus from location
campus = test_data.get_campus(
    location_name="Budapest Sports Complex",
    campus_index=0
)
```

### Tournaments

```python
# Get tournament by assignment type
tournament = test_data.get_tournament(assignment_type="APPLICATION_BASED")
tournament = test_data.get_tournament(assignment_type="OPEN_ASSIGNMENT")

# Get tournament by name (partial match)
tournament = test_data.get_tournament(name="APPLICATION")

# Get tournament by index
tournament = test_data.get_tournament(index=0)

# Get tournament with calculated dates
tournament = test_data.get_tournament_with_dates(
    assignment_type="APPLICATION_BASED"
)
# Returns tournament dict with added fields:
# - start_date: "2026-01-27" (calculated from start_date_offset_days)
# - end_date: "2026-01-27" (same day)
```

### Coupons

```python
# Get coupon by code
coupon = test_data.get_coupon(code="E2E-ENROLL-500-USER1")

# Get coupon assigned to player
coupon = test_data.get_coupon(assigned_to="pwt.k1sqx1@f1stteam.hu")

# Get all coupons for a player
coupons = test_data.get_coupons_for_player("pwt.k1sqx1@f1stteam.hu")
```

## Example: Before vs After

### Before (Hardcoded)

```python
def test_tournament_creation(page: Page):
    # Hardcoded credentials
    ADMIN_EMAIL = "admin@lfa.com"
    ADMIN_PASSWORD = "admin123"

    # Hardcoded tournament data
    TOURNAMENT_NAME = "E2E Test Tournament"
    MAX_PLAYERS = 5
    ENROLLMENT_COST = 500

    # Login
    page.get_by_label("Email").fill(ADMIN_EMAIL)
    page.get_by_label("Password").fill(ADMIN_PASSWORD)
    # ...
```

### After (JSON Fixtures)

```python
def test_tournament_creation(page: Page, test_data, admin_credentials):
    # All data from JSON
    tournament = test_data.get_tournament_with_dates(
        assignment_type="APPLICATION_BASED"
    )

    # Login
    page.get_by_label("Email").fill(admin_credentials["email"])
    page.get_by_label("Password").fill(admin_credentials["password"])

    # Use tournament data
    # tournament["name"]
    # tournament["max_players"]
    # tournament["enrollment_cost"]
    # tournament["start_date"]  # Auto-calculated!
```

## Adding New Test Data

### 1. Edit `tournament_test_data.json`

```json
{
  "users": {
    "instructors": [
      {
        "email": "new.instructor@lfa.com",
        "password": "SecurePass123!",
        "name": "New Instructor",
        "role": "INSTRUCTOR",
        "licenses": [
          {
            "specialization_type": "LFA_COACH",
            "current_level": 5,
            "is_active": true
          }
        ]
      }
    ]
  }
}
```

### 2. Use in Tests

```python
def test_with_new_instructor(test_data):
    instructor = test_data.get_instructor(email="new.instructor@lfa.com")
    assert instructor["licenses"][0]["current_level"] == 5
```

## Schema Validation

All data is validated on load. If JSON doesn't match schema, you'll get a clear error:

```
ValueError: Test data validation failed: 'email' is a required property
```

This catches typos and missing fields before tests run!

## Creating Custom Fixture Files

You can create multiple fixture files for different test scenarios:

```python
# Load custom fixture
from fixtures.data_loader import TestDataLoader

custom_data = TestDataLoader(fixture_name="my_custom_data")
```

Then create `fixtures/my_custom_data.json` following the same schema.

## Best Practices

1. **Don't hardcode test data** - Always use fixtures
2. **Keep JSON DRY** - Reuse data across tests
3. **Use descriptive names** - Make data self-documenting
4. **Validate early** - Schema catches errors immediately
5. **Use calculated dates** - Let `get_tournament_with_dates()` compute dates
6. **Document changes** - Add comments in JSON for complex data

## Running Examples

```bash
# Run example tests
pytest tests/playwright/example_test_with_fixtures.py -v

# Test specific example
pytest tests/playwright/example_test_with_fixtures.py::test_example_get_tournament_data -v
```

## Troubleshooting

### "No admin users found in test data"
- Check `tournament_test_data.json` has `users.admins` array
- Verify JSON is valid (use a JSON validator)

### "Validation failed: ..."
- Check `test_data_schema.json` for required fields
- Ensure all required fields are present in JSON
- Check field types match (string vs integer, etc.)

### "User with email '...' not found"
- Verify email exists in JSON
- Check for typos in email address
- Remember email matching is case-sensitive

## See Also

- `example_test_with_fixtures.py` - Comprehensive usage examples
- `test_data_schema.json` - Full schema documentation
- `tournament_test_data.json` - Current test data
