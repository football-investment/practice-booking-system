# Integration Tests - PostgreSQL Persistent Data

## 🎯 Purpose

These integration tests **intentionally write to PostgreSQL** to create **persistent test data** that is **visible in the Admin Dashboard UI**.

This is **fundamentally different** from `tests/api/` which uses SQLite in-memory for isolated unit testing.

---

## 🔑 Key Difference

| Aspect | tests/api/ (Unit Tests) | tests/integration/ (This Directory) |
|--------|-------------------------|-------------------------------------|
| **Database** | SQLite `:memory:` | PostgreSQL `lfa_intern_system` |
| **Persistence** | ❌ Destroyed after test | ✅ Persists after test |
| **UI Visible** | ❌ Never visible | ✅ Visible in Admin Dashboard |
| **Purpose** | Fast unit testing | UI validation + test data seeding |
| **Email Prefix** | `api.` (irrelevant) | `api.` (visible in UI) |

---

## 🚀 Usage

### 1️⃣ Create Test Data (Seed PostgreSQL)

```bash
pytest tests/integration/test_invitation_codes_postgres.py::test_pg1_create_first_team_invitation_codes -v
```

**Result:**
- 3 invitation codes created in PostgreSQL
- Emails: `api.k1sqx1@f1stteam.hu`, `api.p3t1k3@f1stteam.hu`, `api.V4lv3rd3jr@f1stteam.hu`
- 50 bonus credits each
- **Visible in Admin Dashboard**

---

### 2️⃣ Verify in Admin Dashboard (UI Validation)

1. **Open browser**: http://localhost:8501/Admin_Dashboard
2. **Login**: `admin@lfa.com` / `admin123`
3. **Navigate to**: "Invitation Codes" section
4. **Expected**: You should see 3 codes with `api.` prefix emails

**Screenshot Example:**
```
┌─────────────────────────────────────────────────────────────┐
│ Admin Dashboard > Invitation Codes                          │
├─────────────────────────────────────────────────────────────┤
│ Code                | Email                    | Credits    │
│ INV-20260107-CONM0R | api.k1sqx1@f1stteam.hu  | 50         │
│ INV-20260107-Q4HVGO | api.p3t1k3@f1stteam.hu  | 50         │
│ INV-20260107-QP75ZA | api.V4lv3rd3jr@f1stteam.hu | 50      │
└─────────────────────────────────────────────────────────────┘
```

**This is the CRITICAL DIFFERENCE** - you can now **visually verify** in the UI that:
- API-created test data has `api.` prefix
- Playwright E2E test data has `pwt.` prefix

---

### 3️⃣ Verify in Database (SQL Query)

```bash
pytest tests/integration/test_invitation_codes_postgres.py::test_pg2_verify_codes_in_database -v
```

Or manually via psql:

```sql
psql -U postgres -d lfa_intern_system -c "
  SELECT code, invited_email, bonus_credits, is_used
  FROM invitation_codes
  WHERE invited_email LIKE 'api.%';
"
```

**Expected Output:**
```
         code        |       invited_email        | bonus_credits | is_used
---------------------+----------------------------+---------------+---------
 INV-20260107-CONM0R | api.k1sqx1@f1stteam.hu     |            50 | f
 INV-20260107-Q4HVGO | api.p3t1k3@f1stteam.hu     |            50 | f
 INV-20260107-QP75ZA | api.V4lv3rd3jr@f1stteam.hu |            50 | f
```

---

### 4️⃣ Cleanup (Manual - Only When Needed)

⚠️ **WARNING**: This deletes ALL `api.` test data from PostgreSQL!

```bash
pytest tests/integration/test_invitation_codes_postgres.py::test_pg_cleanup_api_test_data -v
```

This removes:
- All invitation codes with `api.` prefix emails
- All users with `api.` prefix emails

---

## 📊 Prefix Strategy

The **email prefix strategy** now makes sense because both test types write to PostgreSQL:

```
┌──────────────────────────────────────────────────────────────┐
│                  PostgreSQL Database                          │
│                (lfa_intern_system)                            │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  api.k1sqx1@f1stteam.hu     ← Integration Test (API)        │
│  api.p3t1k3@f1stteam.hu     ← Integration Test (API)        │
│  api.V4lv3rd3jr@f1stteam.hu ← Integration Test (API)        │
│                                                               │
│  pwt.k1sqx1@f1stteam.hu     ← E2E Test (Playwright)         │
│  pwt.p3t1k3@f1stteam.hu     ← E2E Test (Playwright)         │
│  pwt.V4lv3rd3jr@f1stteam.hu ← E2E Test (Playwright)         │
│                                                               │
│  admin@lfa.com              ← Production User                │
│  student@lfa.com            ← Production User                │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**In Admin Dashboard**, you can now **visually distinguish**:
- `api.` → Created via Integration API tests
- `pwt.` → Created via Playwright E2E tests
- No prefix → Production users

---

## 🏗️ Architecture Comparison

### Before (Confusion)

```
tests/api/test_invitation_codes.py
  ↓
SQLite :memory: (ephemeral)
  ↓
Data destroyed immediately
  ↓
❌ NOT visible in Admin UI
  ↓
❓ "Why don't I see api.* users in the dashboard?"
```

### After (Clear Purpose)

```
tests/integration/test_invitation_codes_postgres.py
  ↓
PostgreSQL lfa_intern_system (persistent)
  ↓
Data persists after test
  ↓
✅ VISIBLE in Admin UI
  ↓
✅ "I can see api.* users with 'api.' prefix!"
```

---

## 🎓 When to Use Each Test Type

### Use `tests/api/` (SQLite in-memory) when:
- ✅ Testing business logic
- ✅ Fast unit tests
- ✅ Isolated test environment
- ✅ No need for UI validation
- ✅ Standard TDD/BDD practices

### Use `tests/integration/` (PostgreSQL) when:
- ✅ Seeding test data for UI validation
- ✅ Verifying frontend displays data correctly
- ✅ Creating controlled test scenarios
- ✅ Demonstrating features to stakeholders
- ✅ Integration testing with real database

---

## 📝 Example Workflow

```bash
# 1. Clean slate
pytest tests/integration/test_invitation_codes_postgres.py::test_pg_cleanup_api_test_data -v

# 2. Seed test data
pytest tests/integration/test_invitation_codes_postgres.py::test_pg1_create_first_team_invitation_codes -v

# 3. Open Admin Dashboard
open http://localhost:8501/Admin_Dashboard

# 4. Login and verify
# You should see 3 invitation codes with api.* emails

# 5. Verify database
pytest tests/integration/test_invitation_codes_postgres.py::test_pg2_verify_codes_in_database -v
```

---

## ✅ Success Criteria

You'll know the integration tests are working correctly when:

1. ✅ Tests pass and create 3 invitation codes
2. ✅ PostgreSQL has 3 codes with `api.` prefix emails
3. ✅ Admin Dashboard shows these 3 codes
4. ✅ Each code has 50 bonus credits
5. ✅ Codes are NOT marked as used
6. ✅ You can visually distinguish `api.` from `pwt.` users in UI

---

## 🔧 Troubleshooting

### Problem: "Tests pass but I don't see codes in UI"

**Check**:
```bash
# 1. Verify PostgreSQL has the codes
psql -U postgres -d lfa_intern_system -c "SELECT * FROM invitation_codes WHERE invited_email LIKE 'api.%';"

# 2. Check if backend is running
curl http://localhost:8000/health

# 3. Check if Streamlit is running
curl http://localhost:8501
```

### Problem: "Fixture errors when running tests"

**Solution**:
```bash
# Make sure to set PYTHONPATH
PYTHONPATH=. pytest tests/integration/test_invitation_codes_postgres.py -v
```

---

## 🎉 Summary

**This directory solves the original requirement:**
> "I want to see in the Admin UI which users were created by API tests vs E2E tests"

**Solution:**
- Integration tests write to PostgreSQL with `api.` prefix
- E2E tests write to PostgreSQL with `pwt.` prefix
- Both are visible in Admin Dashboard
- Prefix strategy now has real value

**NOT** just for avoiding test conflicts in code, but for **visual identification in production UI**.

---

**Created**: 2026-01-07
**Purpose**: UI Validation + Controlled Test Data Seeding
**Database**: PostgreSQL `lfa_intern_system` (persistent)
