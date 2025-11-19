# ⚠️ DEPRECATION NOTICE - Specialization IDs

**Date:** 2025-11-18
**Deadline:** 2026-05-18 (6 months)

---

## 📢 WHAT'S CHANGING?

We are **renaming** two specialization IDs to better reflect their associated programs:

| Old ID (Deprecated) | New ID | Status | Removal Date |
|---------------------|--------|--------|--------------|
| `PLAYER` | `GANCUJU_PLAYER` | ⚠️ Deprecated | 2026-05-18 |
| `COACH` | `LFA_COACH` | ⚠️ Deprecated | 2026-05-18 |

---

## 🔧 WHY THE CHANGE?

The new naming convention clearly identifies:
- **GANCUJU_PLAYER**: GānCuju™© 8-level player progression system
- **LFA_COACH**: London Football Academy coach certification program

This improves code clarity and prevents confusion with other specialization tracks.

---

## 🚦 BACKWARD COMPATIBILITY

### **Current Behavior (Until 2026-05-18)**

✅ **Both old and new IDs work**:
```python
# Old ID (deprecated but still works)
service.enroll_user(user_id, "PLAYER")
# ⚠️ Logs warning: "PLAYER is deprecated, use GANCUJU_PLAYER"

# New ID (recommended)
service.enroll_user(user_id, "GANCUJU_PLAYER")
# ✅ No warnings
```

### **After 2026-05-18**

❌ **Old IDs will be rejected**:
```python
service.enroll_user(user_id, "PLAYER")
# ❌ Raises ValueError: "PLAYER is no longer supported. Use GANCUJU_PLAYER instead."
```

---

## 📝 MIGRATION GUIDE

### **For API Consumers**

If you're using the REST API, update your requests:

```diff
POST /api/v1/specializations/me
{
-  "specialization": "PLAYER"
+  "specialization": "GANCUJU_PLAYER"
}
```

```diff
POST /api/v1/specializations/me
{
-  "specialization": "COACH"
+  "specialization": "LFA_COACH"
}
```

### **For Python Code**

Update any direct service calls:

```diff
from app.services.specialization_service import SpecializationService

service = SpecializationService(db)

# Update player enrollment
-service.enroll_user(user_id, "PLAYER")
+service.enroll_user(user_id, "GANCUJU_PLAYER")

# Update coach enrollment
-service.enroll_user(user_id, "COACH")
+service.enroll_user(user_id, "LFA_COACH")

# Update progress queries
-service.get_student_progress(student_id, "PLAYER")
+service.get_student_progress(student_id, "GANCUJU_PLAYER")

-service.get_student_progress(student_id, "COACH")
+service.get_student_progress(student_id, "LFA_COACH")
```

### **For Frontend Code**

Update React components:

```diff
// Update form values
const [specialization, setSpecialization] = useState('GANCUJU_PLAYER'); // or 'LFA_COACH'

// Update API calls
-const response = await apiService.selectSpecialization('PLAYER');
+const response = await apiService.selectSpecialization('GANCUJU_PLAYER');
```

---

## 🔍 HOW TO FIND USAGE

### **Search Your Codebase**

```bash
# Find all instances of deprecated IDs
grep -r '"PLAYER"' .
grep -r "'PLAYER'" .
grep -r '"COACH"' .
grep -r "'COACH'" .

# Use ripgrep (rg) for faster results
rg '"PLAYER"' --type py
rg '"COACH"' --type js
```

### **Check Logs**

During the grace period, every use of deprecated IDs logs a warning:

```
⚠️ DEPRECATED SPECIALIZATION ID: 'PLAYER'
   Use 'GANCUJU_PLAYER' instead.
   Support for 'PLAYER' will be removed on 2026-05-18.
   Please update your code!
```

Monitor your application logs for these warnings and update the affected code.

---

## ✅ VERIFICATION

After updating your code, verify the changes:

### **Run Tests**
```bash
# Backend tests
pytest app/tests/test_specialization_deprecation.py -v

# Age validation tests
pytest app/tests/test_e2e_age_validation.py -v
```

### **Manual Testing**
1. Log in to the application
2. Navigate to specialization selection
3. Select a specialization
4. Check logs for deprecation warnings
5. If you see warnings, update the frontend code

---

## 📊 MIGRATION CHECKLIST

Use this checklist to track your migration:

- [ ] Search codebase for `"PLAYER"` and `'PLAYER'`
- [ ] Search codebase for `"COACH"` and `'COACH'`
- [ ] Update API endpoint calls
- [ ] Update Python service calls
- [ ] Update frontend components
- [ ] Update configuration files
- [ ] Update documentation
- [ ] Run backend tests
- [ ] Run frontend tests
- [ ] Deploy to staging environment
- [ ] Monitor logs for deprecation warnings
- [ ] Fix any remaining issues
- [ ] Deploy to production
- [ ] Verify no deprecation warnings in production logs

---

## 🆘 SUPPORT

If you have questions or need help with migration:

1. **Check logs**: Deprecation warnings show exactly which code needs updating
2. **Review tests**: See [test_specialization_deprecation.py](app/tests/test_specialization_deprecation.py) for examples
3. **Read docs**: See [CODE_COMPLEXITY_AUDIT.md](CODE_COMPLEXITY_AUDIT.md) for additional context
4. **Report issues**: Open an issue in the repository

---

## 📅 TIMELINE

| Date | Milestone |
|------|-----------|
| **2025-11-18** | Deprecation announced, backward compatibility enabled |
| **2026-02-18** | 3 months remaining - second reminder |
| **2026-04-18** | 1 month remaining - final reminder |
| **2026-05-18** | Old IDs removed, migration complete |

---

## 🎯 SUMMARY

**Action Required**: Update all references from `PLAYER` → `GANCUJU_PLAYER` and `COACH` → `LFA_COACH` before 2026-05-18.

**Grace Period**: 6 months of backward compatibility (old IDs work with warnings).

**Impact**: Low - system continues working during grace period, warnings help identify code to update.

**Testing**: Comprehensive test coverage ensures smooth transition ([test_specialization_deprecation.py](app/tests/test_specialization_deprecation.py)).
