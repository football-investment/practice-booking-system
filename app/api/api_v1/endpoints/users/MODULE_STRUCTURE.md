# Users Module Structure

```
app/api/api_v1/endpoints/users/
├── __init__.py (31 lines)              # Router Aggregator
│   └── Combines all sub-routers → exports unified router
│
├── helpers.py (151 lines)              # Shared Utilities
│   ├── calculate_pagination()
│   ├── validate_email_unique()
│   ├── validate_nickname()
│   ├── get_user_statistics()
│   └── serialize_enum_value()
│
├── crud.py (230 lines, 5 endpoints)    # CRUD Operations
│   ├── POST   /                        # Create user (Admin)
│   ├── GET    /                        # List users (Admin/Instructor)
│   ├── GET    /{user_id}              # Get user (Admin)
│   ├── PATCH  /{user_id}              # Update user (Admin)
│   └── DELETE /{user_id}              # Delete user (Admin)
│
├── profile.py (127 lines, 4 endpoints) # Profile Management
│   ├── GET    /me                      # Get own profile
│   ├── PATCH  /me                      # Update own profile
│   ├── POST   /{user_id}/reset-password  # Reset password (Admin)
│   └── GET    /check-nickname/{nickname}  # Check nickname
│
├── search.py (50 lines, 1 endpoint)    # Search
│   └── GET    /search                  # Search users (Admin)
│
├── credits.py (188 lines, 3 endpoints) # Credits & Billing
│   ├── POST   /request-invoice         # Request invoice
│   ├── GET    /credit-balance          # Get balance
│   └── GET    /me/credit-transactions  # Get transactions
│
└── instructor_analytics.py (518 lines, 3 endpoints)  # Instructor Features
    ├── GET    /instructor/students                    # List students
    ├── GET    /instructor/students/{student_id}       # Student details
    └── GET    /instructor/students/{student_id}/progress  # Progress
```

## Dependency Graph

```
                    ┌─────────────┐
                    │ __init__.py │
                    │  (Router)   │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐   ┌──────────────┐   ┌────────────────────┐
    │ crud.py  │   │  profile.py  │   │ instructor_       │
    │          │   │              │   │ analytics.py      │
    └────┬─────┘   └──────┬───────┘   └─────────┬─────────┘
         │                │                      │
         │                │                      │
         └────────────────┼──────────────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │ helpers.py  │
                   │ (Utilities) │
                   └─────────────┘
                          ▲
           ┌──────────────┼──────────────┐
           │              │              │
           ▼              ▼              ▼
    ┌──────────┐   ┌────────────┐   ┌─────────┐
    │search.py │   │ credits.py │   │ Models  │
    └──────────┘   └────────────┘   │ Database│
                                     │ Schemas │
                                     └─────────┘
```

## Import Flow

```python
# Main API Router (app/api/api_v1/api.py)
from app.api.api_v1.endpoints.users import router as users_router
api_router.include_router(users_router, prefix="/users", tags=["users"])

# Users __init__.py
from . import crud, profile, search, credits, instructor_analytics
router.include_router(profile.router)
router.include_router(instructor_analytics.router)
router.include_router(search.router)
router.include_router(credits.router)
router.include_router(crud.router)

# Individual modules import helpers
from .helpers import calculate_pagination, validate_nickname, get_user_statistics

# All modules import from root level (5 dots)
from .....database import get_db
from .....models.user import User
from .....dependencies import get_current_user
```

## Route Resolution Order

**Important:** Routes are registered in specific order to avoid conflicts:

1. **Profile routes** (`/me`, `/check-nickname/{nickname}`) - Most specific
2. **Instructor routes** (`/instructor/students/*`) - Specific prefix
3. **Search routes** (`/search`) - Specific endpoint
4. **Credits routes** (`/request-invoice`, `/credit-balance`, `/me/credit-transactions`)
5. **CRUD routes** (`/{user_id}`) - Catch-all pattern (must be last)

This ensures:
- `GET /users/me` → profile.py (not caught by `/{user_id}`)
- `GET /users/instructor/students` → instructor_analytics.py
- `GET /users/123` → crud.py

## Module Responsibilities

| Module | Responsibility | Access Control |
|--------|---------------|----------------|
| **helpers.py** | Shared utilities | N/A (internal only) |
| **crud.py** | User management | Admin (list: Admin/Instructor) |
| **profile.py** | Self-service | All authenticated users |
| **search.py** | User search | Admin only |
| **credits.py** | Billing/credits | All authenticated users |
| **instructor_analytics.py** | Student tracking | Instructor only |

## Testing Strategy

### Unit Tests
```python
# Test helpers independently
test_calculate_pagination()
test_validate_email_unique()
test_validate_nickname()
test_get_user_statistics()

# Test each endpoint module
test_crud_operations()
test_profile_management()
test_search_functionality()
test_credit_operations()
test_instructor_analytics()
```

### Integration Tests
```python
# Test router aggregation
test_all_routes_registered()
test_route_path_ordering()
test_route_access_control()

# Test cross-module functionality
test_profile_update_with_validation()
test_instructor_student_access()
```

## Maintenance Guidelines

### Adding New Endpoints

1. **Determine module**: Choose appropriate module based on functionality
2. **Add route**: Add endpoint to chosen module's router
3. **Update helpers**: Extract shared logic to helpers.py if reused
4. **Test import**: Verify router still loads all routes
5. **Update docs**: Add to REFACTORING_SUMMARY.md

### Modifying Existing Endpoints

1. **Locate module**: Find endpoint in appropriate module
2. **Update logic**: Modify endpoint function
3. **Update helpers**: If validation/utility logic changed
4. **Test**: Ensure route still accessible
5. **Verify**: No breaking changes to API contract

### Best Practices

- Keep helpers.py pure (no side effects)
- Use descriptive function names
- Document complex validation logic
- Maintain consistent error messages
- Preserve Hungarian messages where needed
- Follow existing import patterns
