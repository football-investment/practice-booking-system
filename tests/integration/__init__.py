"""
Integration Tests

PostgreSQL-based integration tests that persist data to the real database.
These tests are used for UI validation and controlled test data seeding.

CRITICAL DIFFERENCE from tests/api/:
- Writes to REAL PostgreSQL database (not SQLite in-memory)
- Data PERSISTS after tests complete
- Users visible in Admin Dashboard frontend
- Purpose: Controlled test data seeding + UI validation

⚠️ WARNING: Requires manual cleanup between test runs
"""
