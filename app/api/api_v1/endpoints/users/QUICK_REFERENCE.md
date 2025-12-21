# Users Module - Quick Reference Guide

## Where to Find Endpoints

### Need to create/list/update/delete users?
→ **crud.py** (5 endpoints)
- Admin/Instructor can list users
- Admin-only for create/update/delete

### Need to manage user profiles?
→ **profile.py** (4 endpoints)
- Get/update own profile
- Check nickname availability
- Admin can reset passwords

### Need to search for users?
→ **search.py** (1 endpoint)
- Admin-only search by name/email

### Need to handle credits/billing?
→ **credits.py** (3 endpoints)
- Request invoices
- Check credit balance
- View transaction history

### Need instructor features?
→ **instructor_analytics.py** (3 endpoints)
- View students
- Student details
- Progress tracking

### Need shared utilities?
→ **helpers.py** (5 functions)
- Pagination
- Validation
- Statistics

---

## Common Tasks

### Add a new endpoint

1. **Choose module** based on functionality:
   - User management → crud.py
   - Self-service → profile.py
   - Search → search.py
   - Billing → credits.py
   - Instructor → instructor_analytics.py

2. **Add endpoint** to chosen module:
```python
@router.get("/new-endpoint")
def my_new_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Implementation
    return {"status": "success"}
```

3. **Import helper** if needed:
```python
from .helpers import calculate_pagination, validate_email_unique
```

4. **Test** the route:
```bash
python3 -c "from app.api.api_v1.endpoints.users import router; \
            print(len(router.routes))"
```

### Add a helper function

1. **Add to helpers.py**:
```python
def my_helper_function(param1, param2):
    """Helper description"""
    # Implementation
    return result
```

2. **Import in module**:
```python
from .helpers import my_helper_function
```

3. **Use in endpoint**:
```python
result = my_helper_function(value1, value2)
```

### Update existing endpoint

1. **Find endpoint** using this guide
2. **Edit function** in appropriate module
3. **Update helpers** if validation/utility logic changed
4. **Test** endpoint still works

---

## Import Patterns

### Within modules (import helpers)
```python
from .helpers import calculate_pagination
```

### From root (5 dots - same level as original)
```python
from .....database import get_db
from .....models.user import User
from .....dependencies import get_current_user
from .....schemas.user import UserSchema
```

### Avoiding circular imports
```python
# Import at module level (top of file)
from .....models.project import Project, ProjectEnrollment

# Not inline (within function) - unless truly circular
```

---

## Testing Checklist

### After making changes

```bash
# 1. Verify imports work
python3 -c "from app.api.api_v1.endpoints.users import router"

# 2. Count routes (should be 16+)
python3 -c "from app.api.api_v1.endpoints.users import router; \
            print(f'Routes: {len(router.routes)}')"

# 3. Check syntax
python3 -m py_compile app/api/api_v1/endpoints/users/*.py

# 4. Run unit tests (if available)
pytest app/tests/test_users/ -v

# 5. Run integration tests
pytest app/tests/integration/test_users_api.py -v
```

---

## File Sizes

| File | Lines | Keep Under |
|------|-------|-----------|
| helpers.py | 151 | 200 |
| crud.py | 230 | 300 |
| profile.py | 127 | 200 |
| search.py | 50 | 100 |
| credits.py | 188 | 250 |
| instructor_analytics.py | 518 | 600 |

If a module exceeds its threshold, consider splitting further.

---

## Troubleshooting

### "Module not found" error
- Check import dots: should be 5 dots (.....)
- Verify __init__.py exists
- Check file naming (lowercase, no typos)

### "Route not found" error
- Check __init__.py includes all routers
- Verify route order (specific before catch-all)
- Test: `python3 -c "from app.api.api_v1.endpoints.users import router; [print(r.path) for r in router.routes]"`

### "Circular import" error
- Move import to function level (temporary fix)
- Refactor to remove circular dependency (proper fix)
- Check import order in __init__.py

### "Helper function not found" error
- Verify function exists in helpers.py
- Check import: `from .helpers import function_name`
- Verify function is not misspelled

---

## Best Practices

1. **Keep modules focused**
   - Each module has single responsibility
   - Max 300 lines (except instructor_analytics)

2. **Use helpers for shared logic**
   - Don't duplicate validation
   - Extract common patterns

3. **Maintain consistent style**
   - Same error message format
   - Same response structure
   - Same documentation format

4. **Document complex logic**
   - Hungarian messages preserved
   - Business rules explained
   - Edge cases noted

5. **Test before committing**
   - All routes still work
   - No syntax errors
   - Imports resolve correctly

---

## Quick Commands

```bash
# Navigate to users module
cd app/api/api_v1/endpoints/users

# List all files
ls -lh

# Count lines in each file
wc -l *.py

# Find specific endpoint
grep -r "def create_user" .

# Test imports
python3 -c "from app.api.api_v1.endpoints.users import router"

# Count routes
python3 -c "from app.api.api_v1.endpoints.users import router; print(len(router.routes))"

# List all routes
python3 -c "from app.api.api_v1.endpoints.users import router; [print(f'{list(r.methods)[0]:6s} {r.path}') for r in sorted(router.routes, key=lambda x: x.path)]"
```

---

## Module Dependencies

```
helpers.py         → None (pure utilities)
crud.py            → helpers.py
profile.py         → helpers.py
search.py          → None (simple query)
credits.py         → None (simple queries)
instructor_analytics.py → helpers.py
__init__.py        → All modules
```

---

## Contact

For questions or issues with this module structure:
1. Check this QUICK_REFERENCE.md
2. Review MODULE_STRUCTURE.md for architecture
3. Read BEFORE_AFTER_COMPARISON.md for migration details
4. See REFACTORING_SUMMARY.md for overview

---

**Last Updated:** December 21, 2024
**Module Version:** 1.0
**Total Routes:** 16
**Status:** Production Ready ✓
