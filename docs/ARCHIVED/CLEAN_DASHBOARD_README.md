# 🎮 Clean Backend Testing Dashboard

**Professional Streamlit-based API testing tool with real-time progress tracking**

## 🚀 Quick Start

### Start Dashboard:
```bash
./start_clean_dashboard.sh
```

**Dashboard URL:** http://localhost:8501

## 🔒 Security Features

### ✅ **Admin-Only Access Control**

1. **🔐 Password Required** - Manual password input, no quick-select login
2. **✅ Role Verification** - Fetches user role from `/api/v1/users/me` endpoint
3. **🚫 Access Rejection** - Non-admin users are immediately blocked
4. **🔒 Double-Layer Protection** - Role checked both at login and main content
5. **📋 Session State** - Secure role storage and validation throughout session

**Security Enhancements (2025-12-11):**
- ✅ Removed passwordless quick-login vulnerability
- ✅ Added admin role verification
- ✅ Clear security warnings for users
- ✅ Production-ready access control

## 📋 Features

### ✨ **Key Highlights**

1. **🔐 Admin Authentication** - Secure login with password and role verification
2. **📍 Session Workflows** - Test ON-SITE, HYBRID, and VIRTUAL session workflows
3. **🎯 HYBRID Quiz Tests** - Complete unlock + attendance access control
4. **🌐 VIRTUAL Quiz Tests** - Complete time window access control
5. **📊 Real-time Progress** - See every test step as it runs
6. **📈 Visual Results** - Metrics, colored output, detailed logs

### 🧪 **Test Coverage**

#### **Session Workflow Tests:**
- Browse sessions by type
- Create booking
- Verify in My Bookings
- Get booking details
- Cancel booking

#### **HYBRID Quiz Tests:**
- ✅ Check booking requirement
- 🔓 Test quiz unlock requirement
- ✅ Test attendance requirement
- 🎯 Verify access with all requirements met
- 🚀 Start quiz attempt

#### **VIRTUAL Quiz Tests:**
- ✅ Check booking requirement
- ⏰ Test time window (before session starts)
- ⏰ Activate session (set time window)
- 🎯 Verify access within time window
- 🚀 Start quiz attempt

## 🎯 Usage Guide

### **Step 1: Login (ADMIN ONLY)**
⚠️ **IMPORTANT**: This dashboard requires ADMIN credentials.

1. Open sidebar
2. Enter admin email address
3. Enter admin password
4. Click "🔐 Login"
5. Only ADMIN role users will be granted access

### **Step 2: Reset Test State (Optional)**
- Click "🔄 Reset Test State" in sidebar
- This resets:
  - HYBRID quiz unlock status
  - Attendance records
  - VIRTUAL session time window
  - Quiz attempts

### **Step 3: Run Tests**

#### **Option A: Individual Session Tests**
1. Go to "📍 Session Workflows" tab
2. Click test button for desired session type:
   - 🏢 Test ON-SITE
   - 🔀 Test HYBRID
   - 🌐 Test VIRTUAL

#### **Option B: All Sessions at Once**
1. Go to "📍 Session Workflows" tab
2. Click "🚀 Run ALL Session Tests"
3. Watch all 3 session types tested sequentially

#### **Option C: HYBRID Quiz Test**
1. Go to "🎯 HYBRID Quiz Tests" tab
2. Click "🧪 Run HYBRID Quiz Test"
3. See 6-step access control validation

#### **Option D: VIRTUAL Quiz Test**
1. Go to "🌐 VIRTUAL Quiz Tests" tab
2. Click "🧪 Run VIRTUAL Quiz Test"
3. See 4-step time window validation

### **Step 4: View Results**
1. Go to "📊 Test Results" tab
2. See metrics: Total Steps / Passed / Failed
3. Review detailed test log with timestamps
4. Clear results when done

## 📊 Sample Test Output

```
[22:19:28] ℹ️ 🔍 Step 1: Browsing HYBRID sessions...
[22:19:28] ✅ Browse HYBRID sessions: SUCCESS
[22:19:28] ℹ️ 📝 Step 2: Creating booking for session 206...
[22:19:28] ✅ Create booking: SUCCESS (ID: 22)
[22:19:29] ℹ️ 🔍 Step 3: Verifying booking in My Bookings...
[22:19:29] ✅ Verify in My Bookings: SUCCESS
[22:19:29] ℹ️ 📋 Step 4: Getting booking details...
[22:19:29] ✅ Get booking details: SUCCESS
[22:19:29] ℹ️ 🗑️ Step 5: Cancelling booking...
[22:19:29] ✅ Cancel booking: SUCCESS
```

## 🏗️ Architecture

### **Clean Code Structure:**

```python
# Configuration (Lines 1-50)
- API endpoints
- Test accounts
- Session/Quiz IDs

# Helper Functions (Lines 51-100)
- Login
- Headers
- Logging

# Test Functions (Lines 101-500)
- test_session_workflow()
- test_hybrid_quiz_workflow()
- test_virtual_quiz_workflow()
- reset_test_state()

# Streamlit UI (Lines 501-750)
- Sidebar (Auth + Reset)
- Tab 1: Session Workflows
- Tab 2: HYBRID Quiz Tests
- Tab 3: VIRTUAL Quiz Tests
- Tab 4: Test Results
```

## 🔧 Configuration

### **API Base URL:**
```python
API_BASE_URL = "http://localhost:8000"
```

### **Database Connection:**
```python
DB_CONN_STRING = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
```

### **Admin Access:**
```python
# Only admin users can access the dashboard
# Login with your admin credentials:
ADMIN_EMAIL = "admin@yourcompany.com"
# Password: (enter your admin password at login screen)
```

**⚠️ SECURITY NOTE**: The dashboard now requires ADMIN credentials and verifies the user role. Non-admin users will be rejected.

### **Session IDs:**
```python
SESSION_IDS = {
    "ON-SITE": 203,
    "HYBRID": 206,
    "VIRTUAL": 208
}
```

### **Quiz IDs:**
```python
QUIZ_IDS = {
    "HYBRID": 1,
    "VIRTUAL": 2
}
```

## ✅ **What's Been Tested:**

### **✅ ON-SITE Sessions:**
- Browse ✅
- Create booking ✅
- Verify booking ✅
- Get details ✅
- Cancel booking ✅

### **✅ HYBRID Sessions:**
- Browse ✅
- Create booking ✅
- Quiz unlock requirement ✅
- Attendance requirement ✅
- Access with requirements ✅
- Start quiz attempt ✅

### **✅ VIRTUAL Sessions:**
- Browse ✅
- Create booking ✅
- Time window requirement ✅
- Activate session ✅
- Access within window ✅
- Start quiz attempt ✅

## 🐛 Troubleshooting

### **Dashboard won't start:**
```bash
# Check if port 8501 is available
lsof -i :8501

# Kill existing Streamlit process
pkill -f streamlit
```

### **Backend not responding:**
```bash
# Check backend status
curl http://localhost:8000/health

# Restart backend
./start_backend.sh
```

### **Database connection error:**
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check database exists
psql -U postgres -l | grep lfa_intern_system
```

### **Tests failing:**
1. Click "🔄 Reset Test State" in sidebar
2. Ensure backend is running (http://localhost:8000/health)
3. Ensure database is accessible
4. Check test accounts exist in database

## 📝 Comparison with Old Dashboard

### **Old Dashboard (617 lines):**
- ❌ Complex, hard to maintain
- ❌ No real-time progress
- ❌ Mixed responsibilities
- ❌ Unclear test flow

### **New Dashboard (750 lines):**
- ✅ Clean architecture
- ✅ Real-time progress tracking
- ✅ Separated concerns
- ✅ Clear test flow
- ✅ Better error handling
- ✅ Professional UI
- ✅ Easy to extend

## 🎨 UI Features

- **Custom CSS** for progress bars
- **Color-coded results** (success/error/warning/info)
- **Real-time spinners** during test execution
- **Metrics dashboard** (Total/Passed/Failed)
- **Responsive layout** with tabs
- **Clean, modern design**

## 🚀 Future Enhancements (Optional)

- [ ] Export test results to JSON/CSV
- [ ] Schedule automated test runs
- [ ] Compare test results over time
- [ ] Email notifications on test failure
- [ ] Integration with CI/CD pipeline

## 📚 Related Files

- `clean_testing_dashboard.py` - Main dashboard code
- `start_clean_dashboard.sh` - Quick start script
- `test_complete_quiz_workflow.py` - Command-line quiz tests
- `test_all_session_types.py` - Command-line session tests

## 🎯 Summary

**The Clean Backend Testing Dashboard provides:**
- ✅ Professional UI with Streamlit
- ✅ Real-time test progress tracking
- ✅ Complete test coverage (ON-SITE, HYBRID, VIRTUAL)
- ✅ Quiz access control validation
- ✅ Visual results with metrics
- ✅ Easy to use and maintain
- ✅ Production-ready testing tool

**Access the dashboard at:** http://localhost:8501
