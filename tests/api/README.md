# API Tests

This directory contains all backend API integration tests for the LFA Internship System.

## 📁 Directory Structure

```
tests/api/
├── README.md                          # This file
├── conftest.py                        # Pytest configuration and fixtures
├── test_coupons_refactored.py        # Coupon system API tests
├── test_invitation_codes.py           # Invitation code API tests
└── test_tournament_enrollment.py      # Tournament enrollment API tests
```

## 🧪 Test Files

### 1. `test_coupons_refactored.py`
Tests the coupon system API endpoints:
- ✅ Coupon creation (admin)
- ✅ Coupon validation
- ✅ Coupon redemption (bonus credits)
- ✅ Usage limits (single-use vs multi-use)
- ✅ Coupon expiration
- ✅ Error handling (invalid codes, expired coupons, usage limit reached)

**Key endpoints tested:**
- `POST /api/v1/coupons` - Create coupon
- `POST /api/v1/coupons/redeem` - Redeem coupon
- `GET /api/v1/coupons` - List coupons

### 2. `test_invitation_codes.py`
Tests the invitation code system for user registration:
- ✅ Invitation code generation (admin)
- ✅ Code validation during registration
- ✅ Single-use enforcement
- ✅ Code expiration
- ✅ Batch code creation
- ✅ Authorization (admin-only creation)

**Key endpoints tested:**
- `POST /api/v1/invitation-codes` - Create invitation code
- `POST /api/v1/invitation-codes/batch` - Create multiple codes
- `GET /api/v1/invitation-codes` - List invitation codes
- `POST /api/v1/auth/register` - Register with invitation code

### 3. `test_tournament_enrollment.py`
Tests tournament enrollment workflow:
- ✅ Player enrollment in tournaments
- ✅ Credit deduction on enrollment
- ✅ Enrollment status validation
- ✅ Tournament capacity limits
- ✅ Duplicate enrollment prevention
- ✅ Enrollment permission checks

**Key endpoints tested:**
- `POST /api/v1/tournaments/{id}/enroll` - Enroll in tournament
- `GET /api/v1/tournaments/{id}/enrollments` - List enrollments
- `GET /api/v1/tournaments/available` - List available tournaments for enrollment

## 🚀 Running Tests

### Run All API Tests

```bash
pytest tests/api/ -v
```

### Run Specific Test File

```bash
pytest tests/api/test_coupons_refactored.py -v
```

### Run Specific Test Function

```bash
pytest tests/api/test_coupons_refactored.py::test_create_coupon -v
```

### Run with Coverage

```bash
pytest tests/api/ --cov=app --cov-report=html -v
```

## 🎯 Pytest Options

- `-v`: Verbose output
- `-vv`: Extra verbose (shows full diff on failures)
- `-s`: Show print statements
- `-x`: Stop on first failure
- `--tb=short`: Short traceback
- `--tb=line`: One-line traceback
- `-k "keyword"`: Run tests matching keyword
- `--markers`: List all test markers

## 🛠️ Test Environment

### Required Services

FastAPI backend must be running:

```bash
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or tests can use TestClient (no server required):

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.get("/api/v1/endpoint")
```

### Database

- **PostgreSQL** database: `lfa_intern_system`
- **Connection**: `postgresql://postgres:postgres@localhost:5432/lfa_intern_system`
- **Note**: API tests typically use database transactions that are rolled back after each test

## 📋 Test Fixtures

Common fixtures available in `conftest.py`:

- `client`: FastAPI TestClient
- `db`: Database session
- `admin_token`: Admin authentication token
- `player_token`: Player authentication token
- `instructor_token`: Instructor authentication token

Example usage:

```python
def test_create_coupon(client, admin_token):
    response = client.post(
        "/api/v1/coupons",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"code": "TEST123", "bonus_credits": 100}
    )
    assert response.status_code == 201
```

## 🐛 Debugging Failed Tests

### Common Issues

1. **Database connection errors**
   - Ensure PostgreSQL is running
   - Check DATABASE_URL environment variable
   - Verify database exists

2. **Authentication errors**
   - Check token generation in conftest.py
   - Verify user credentials
   - Ensure correct role permissions

3. **Endpoint not found (404)**
   - Check API endpoint path
   - Verify FastAPI app is running
   - Check route registration

### Debugging Commands

```bash
# Run with full traceback
pytest tests/api/test_name.py -vv --tb=long

# Run with debugger on failure
pytest tests/api/test_name.py --pdb

# Run with print statements visible
pytest tests/api/test_name.py -s

# Run only failed tests from last run
pytest tests/api/ --lf
```

## 📝 Writing New API Tests

1. **Use fixtures** from `conftest.py` for authentication and database setup
2. **Use consistent naming**: `test_feature_name.py`
3. **Add docstrings** explaining what the test validates
4. **Test both success and error cases**
5. **Use descriptive assertion messages**

Example:

```python
def test_redeem_coupon_success(client, player_token):
    """Test successful coupon redemption increases player credits"""
    # Create coupon
    coupon_code = "BONUS100"
    # ... setup code ...

    # Redeem coupon
    response = client.post(
        "/api/v1/coupons/redeem",
        headers={"Authorization": f"Bearer {player_token}"},
        json={"code": coupon_code}
    )

    assert response.status_code == 200, "Coupon redemption should succeed"
    assert response.json()["credits_added"] == 100
```

## ✅ Test Coverage

Current API test coverage:
- ✅ Coupon system (creation, validation, redemption, expiration)
- ✅ Invitation codes (generation, validation, single-use enforcement)
- ✅ Tournament enrollment (enrollment, capacity, credits, permissions)

**Not yet covered** (future work):
- ⏳ User management (profile updates, password changes)
- ⏳ Session management (session creation, booking, attendance)
- ⏳ Payment processing
- ⏳ License management (renewal, upgrades)
- ⏳ XP and progression system

## 🔗 Related Documentation

- [Playwright E2E Tests](../playwright/README.md) - Frontend UI tests
- [Security Tests](../security/README.md) - Security validation tests
- [Integration Tests](../integration/README.md) - Full-stack integration tests
