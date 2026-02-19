# Users Module

Modular user management system for the Practice Booking System.

## Overview

This module provides all user-related API endpoints, refactored from a single 1,113-line file into 6 focused modules with shared utilities.

### Key Features
- **16 API endpoints** across 6 modules
- **Zero breaking changes** from original implementation
- **5 helper functions** eliminating code duplication
- **Full test coverage** support
- **Production ready** with comprehensive documentation

---

## Module Structure

```
users/
├── __init__.py                     # Router aggregator (31 lines)
├── helpers.py                      # Shared utilities (151 lines, 5 functions)
├── crud.py                         # CRUD operations (230 lines, 5 endpoints)
├── profile.py                      # Profile management (127 lines, 4 endpoints)
├── search.py                       # User search (50 lines, 1 endpoint)
├── credits.py                      # Credits & billing (188 lines, 3 endpoints)
├── instructor_analytics.py         # Instructor features (518 lines, 3 endpoints)
├── README.md                       # This file
├── QUICK_REFERENCE.md              # Quick lookup guide
├── REFACTORING_SUMMARY.md          # Metrics and overview
├── MODULE_STRUCTURE.md             # Architecture diagrams
└── BEFORE_AFTER_COMPARISON.md      # Migration details
```

---

## Quick Start

### Import the module
```python
from app.api.api_v1.endpoints.users import router

# Router includes all 16 endpoints
app.include_router(router, prefix="/users", tags=["users"])
```

### Use helper functions
```python
from app.api.api_v1.endpoints.users.helpers import (
    calculate_pagination,
    validate_email_unique,
    validate_nickname,
    get_user_statistics,
    serialize_enum_value
)
```

---

## Endpoints by Module

### crud.py (5 endpoints)
Admin/Instructor user management

```
POST   /                  # Create user (Admin only)
GET    /                  # List users (Admin: all, Instructor: students)
GET    /{user_id}         # Get user with stats (Admin only)
PATCH  /{user_id}         # Update user (Admin only)
DELETE /{user_id}         # Soft delete user (Admin only)
```

### profile.py (4 endpoints)
Self-service profile management

```
GET    /me                         # Get own profile
PATCH  /me                         # Update own profile
GET    /check-nickname/{nickname}  # Check nickname availability
POST   /{user_id}/reset-password   # Reset password (Admin only)
```

### search.py (1 endpoint)
User search functionality

```
GET    /search            # Search users by name/email (Admin only)
```

### credits.py (3 endpoints)
Credits and billing management

```
POST   /request-invoice          # Request invoice for credits
GET    /credit-balance           # Get credit balance
GET    /me/credit-transactions   # Get transaction history
```

### instructor_analytics.py (3 endpoints)
Instructor student tracking

```
GET    /instructor/students                        # List students
GET    /instructor/students/{student_id}           # Student details
GET    /instructor/students/{student_id}/progress  # Progress tracking
```

### helpers.py (5 functions)
Shared utilities

```python
calculate_pagination()     # Pagination logic (page/size + skip/limit)
validate_email_unique()    # Email uniqueness check
validate_nickname()        # Nickname validation (format + availability)
get_user_statistics()      # User stats (bookings, sessions, feedback)
serialize_enum_value()     # Enum to string conversion
```

---

## Access Control

| Endpoint | Admin | Instructor | Student | Public |
|----------|-------|------------|---------|--------|
| POST / | ✓ | ✗ | ✗ | ✗ |
| GET / | ✓ | ✓* | ✗ | ✗ |
| GET /{user_id} | ✓ | ✗ | ✗ | ✗ |
| PATCH /{user_id} | ✓ | ✗ | ✗ | ✗ |
| DELETE /{user_id} | ✓ | ✗ | ✗ | ✗ |
| GET /me | ✓ | ✓ | ✓ | ✗ |
| PATCH /me | ✓ | ✓ | ✓ | ✗ |
| POST /{user_id}/reset-password | ✓ | ✗ | ✗ | ✗ |
| GET /check-nickname/{nickname} | ✓ | ✓ | ✓ | ✗ |
| GET /search | ✓ | ✗ | ✗ | ✗ |
| POST /request-invoice | ✓ | ✓ | ✓ | ✗ |
| GET /credit-balance | ✓ | ✓ | ✓ | ✗ |
| GET /me/credit-transactions | ✓ | ✓ | ✓ | ✗ |
| GET /instructor/students | ✗ | ✓ | ✗ | ✗ |
| GET /instructor/students/{student_id} | ✗ | ✓ | ✗ | ✗ |
| GET /instructor/students/{student_id}/progress | ✗ | ✓ | ✗ | ✗ |

\* Instructors can only see students in `GET /`

---

## Examples

### Create a user (Admin only)
```python
POST /api/v1/users/
Content-Type: application/json
Authorization: Bearer <admin_token>

{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "role": "student",
  "phone": "+36301234567"
}
```

### Update own profile
```python
PATCH /api/v1/users/me
Content-Type: application/json
Authorization: Bearer <user_token>

{
  "phone": "+36307654321",
  "emergency_contact": "Jane Doe",
  "emergency_phone": "+36309876543"
}
```

### Search users (Admin only)
```python
GET /api/v1/users/search?q=john&role=student&limit=10
Authorization: Bearer <admin_token>
```

### Check nickname availability
```python
GET /api/v1/users/check-nickname/john_doe
Authorization: Bearer <user_token>

Response:
{
  "available": true,
  "message": "Remek! Ez a becenév elérhető."
}
```

### Request invoice
```python
POST /api/v1/users/request-invoice
Content-Type: application/json
Authorization: Bearer <user_token>

{
  "amount": 1000
}

Response:
{
  "status": "success",
  "message": "Invoice request sent to admin for 1000 credits...",
  "payment_reference": "LFA-20251221-143052-00001-A3F2",
  "invoice_id": 1
}
```

### Get instructor's students
```python
GET /api/v1/users/instructor/students?page=1&size=20
Authorization: Bearer <instructor_token>

Response:
{
  "students": [
    {
      "id": 123,
      "name": "Student Name",
      "email": "student@example.com",
      "enrollments": [...]
    }
  ],
  "total": 45,
  "page": 1,
  "size": 20
}
```

---

## Performance Optimizations

### Eager Loading
```python
# Avoids N+1 queries
query = db.query(User).options(joinedload(User.licenses))
```

### Batch Fetching
```python
# Fetch all enrollments in single query
enrollments = db.query(ProjectEnrollment).options(
    joinedload(ProjectEnrollment.project)
).filter(ProjectEnrollment.user_id.in_(student_ids)).all()
```

### Pagination Support
```python
# Both page/size and skip/limit modes supported
offset, page_size, current_page = calculate_pagination(page, size, skip, limit)
```

---

## Validation Rules

### Email
- Must be unique across all users
- Standard email format validation
- Case-insensitive duplicate check

### Nickname
- Length: 3-30 characters
- Allowed: Letters (including Hungarian), numbers, underscore
- Not allowed: Reserved words (admin, system, etc.)
- Case-insensitive uniqueness check

### Phone Numbers
- Emergency phone must differ from user phone
- Format validation (Hungarian format preferred)

### Passwords
- Minimum 8 characters (enforced by schema)
- Hashed using bcrypt
- Never returned in responses

---

## Error Handling

### Common HTTP Status Codes

```
200 OK                    # Successful GET/PATCH
201 Created               # Successful POST
204 No Content            # Successful DELETE
400 Bad Request           # Validation error
401 Unauthorized          # Missing/invalid token
403 Forbidden             # Insufficient permissions
404 Not Found             # User not found
409 Conflict              # Email/nickname already exists
500 Internal Server Error # Server error
```

### Error Response Format

```json
{
  "detail": "User with this email already exists"
}
```

---

## Testing

### Unit Tests
```bash
# Test helper functions
pytest app/tests/test_users_helpers.py -v

# Test individual modules
pytest app/tests/test_users_crud.py -v
pytest app/tests/test_users_profile.py -v
pytest app/tests/test_users_credits.py -v
```

### Integration Tests
```bash
# Test all endpoints
pytest app/tests/integration/test_users_api.py -v

# Test with coverage
pytest app/tests/ --cov=app/api/api_v1/endpoints/users --cov-report=html
```

### Manual Testing
```bash
# Verify imports
python3 -c "from app.api.api_v1.endpoints.users import router"

# Count routes
python3 -c "from app.api.api_v1.endpoints.users import router; \
            print(f'Routes: {len(router.routes)}')"

# List all routes
python3 -c "from app.api.api_v1.endpoints.users import router; \
            [print(f'{list(r.methods)[0]:6s} {r.path}') for r in router.routes]"
```

---

## Documentation

### Quick References
- **QUICK_REFERENCE.md** - Fast lookup for common tasks
- **REFACTORING_SUMMARY.md** - Metrics and statistics
- **MODULE_STRUCTURE.md** - Architecture and diagrams
- **BEFORE_AFTER_COMPARISON.md** - Migration details

### API Documentation
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI spec: `/openapi.json`

---

## Maintenance

### Adding New Endpoints

1. Choose appropriate module based on functionality
2. Add endpoint to module's router
3. Extract shared logic to helpers.py if reused
4. Update tests
5. Update documentation

### Modifying Endpoints

1. Locate endpoint in appropriate module
2. Update function implementation
3. Update helper functions if needed
4. Run tests to verify no breaking changes
5. Update API documentation if contract changed

### Code Quality Guidelines

- Keep modules under 300 lines (except instructor_analytics)
- Extract shared logic to helpers.py
- Use type hints for better IDE support
- Document complex business logic
- Preserve Hungarian error messages
- Maintain consistent response formats

---

## Dependencies

### Internal
```python
from .....database import get_db
from .....dependencies import get_current_user, get_current_admin_user
from .....models.user import User, UserRole
from .....schemas.user import UserSchema, UserCreate, UserUpdate
from .....core.security import get_password_hash
```

### External
```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func, or_
```

---

## Changelog

### Version 1.0 (2024-12-21)
- Initial modular refactoring
- Extracted 6 modules from monolithic users.py
- Added 5 helper functions
- Added comprehensive documentation
- All 16 endpoints working
- Zero breaking changes

---

## Support

For issues or questions:
1. Check QUICK_REFERENCE.md for common tasks
2. Review MODULE_STRUCTURE.md for architecture
3. See BEFORE_AFTER_COMPARISON.md for migration details
4. Check inline code documentation
5. Contact development team

---

## License

Internal use only - Practice Booking System
Copyright © 2024 Football Investment

---

**Status:** Production Ready ✓  
**Version:** 1.0  
**Last Updated:** December 21, 2024  
**Total Routes:** 16  
**Total Lines:** 1,295 (excluding docs)
