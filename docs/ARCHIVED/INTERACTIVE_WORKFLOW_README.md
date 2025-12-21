# 🎮 Interactive Workflow Testing Dashboard

**Step-by-step testing with role-based action buttons**

## 📋 Overview

This dashboard provides an **interactive, step-by-step testing experience** where:
- Each workflow step has dedicated action buttons for different roles (Admin, Student, Instructor)
- Buttons are **conditionally enabled** based on previous step completion
- Real-time visual feedback shows workflow progress
- All actions are logged with timestamps

## 🚀 Quick Start

### Start the Dashboard:
```bash
./start_interactive_workflow.sh
```

**Dashboard URL:** http://localhost:8502

### Login (ADMIN ONLY):
1. Email: `admin@lfa.com`
2. Password: `admin123`
3. Click "🔐 Login"

## 📋 Current Features (Phase 1)

### ✅ Step 1: Admin Creates New User
**Role:** ADMIN

**Action:** Create a new student user

**Fields:**
- Student Email (e.g., `test.student@example.com`)
- Password (e.g., `password123`)
- Full Name (e.g., `Test Student`)

**Button:** "👤 Create Student User"

**State Flow:**
- ⏸️ **Pending** → 🔵 **Active** → ✅ **Done** or ❌ **Error**

### ✅ Step 2: Student First Login
**Role:** STUDENT

**Action:** Login with newly created credentials

**Fields:**
- Email (auto-filled from Step 1)
- Password (auto-filled from Step 1)

**Button:** "🔐 Student Login" (disabled until Step 1 complete)

**State Flow:**
- ⏸️ **Waiting for Step 1** → 🔵 **Active** → ✅ **Done** or ❌ **Error**

## 🎯 Workflow Logic

### Button Enabling Rules:

1. **Step 1 (Admin Creates User)**
   - Always enabled (unless already done)
   - Admin must be logged in

2. **Step 2 (Student Login)**
   - ⏸️ **DISABLED** if Step 1 is not complete
   - 🔵 **ENABLED** only after Step 1 succeeds
   - Shows waiting message until Step 1 done

### Visual States:

| State | Icon | Meaning |
|-------|------|---------|
| **Pending** | ⏸️ | Step not started yet |
| **Active** | 🔵 | Step ready to execute |
| **Done** | ✅ | Step completed successfully |
| **Error** | ❌ | Step failed |

## 📊 Dashboard Sections

### 1. **Admin Login (Sidebar)**
- Secure admin authentication
- Role verification
- Logout functionality

### 2. **Workflow Control (Sidebar)**
- 🔄 **Reset Workflow** - Clear all steps and start over

### 3. **Workflow Steps (Main Area)**
- Two-column layout showing current steps
- Form inputs for each step
- Conditional button enabling
- Real-time status updates

### 4. **Workflow Logs**
- Timestamped action log
- Color-coded messages (success/error/info/warning)
- Full audit trail of all actions

### 5. **Workflow Status Summary**
- Quick overview of all step states
- Visual metrics for each step
- Completion status

## 🔒 Security Features

### ✅ **Admin-Only Access Control**
1. **Password Required** - Manual password input, no quick-select login
2. **Role Verification** - Fetches user role from `/api/v1/users/me` endpoint
3. **Access Rejection** - Non-admin users are immediately blocked
4. **Double-Layer Protection** - Role checked both at login and main content

## 🧪 How to Test

### Test Scenario: Create User → Student Login

1. **Start Dashboard**
   ```bash
   ./start_interactive_workflow.sh
   ```

2. **Login as Admin**
   - Open sidebar
   - Enter admin credentials
   - Click "🔐 Login"

3. **Step 1: Create User**
   - Fill in student email (e.g., `testuser@example.com`)
   - Enter password (e.g., `test123`)
   - Enter full name (e.g., `Test User`)
   - Click "👤 Create Student User"
   - Wait for ✅ success confirmation

4. **Step 2: Student Login**
   - Notice button is now enabled
   - Credentials auto-filled from Step 1
   - Click "🔐 Student Login"
   - Wait for ✅ success confirmation

5. **Check Results**
   - View workflow logs for detailed action history
   - Check workflow status summary for completion

6. **Reset and Test Again** (Optional)
   - Click "🔄 Reset Workflow" in sidebar
   - Run through steps again with different user

## 📝 Sample Output

### Workflow Logs:
```
[14:23:15] ℹ️ Admin logged in: admin@lfa.com
[14:23:20] ℹ️ Admin creating user: testuser@example.com
[14:23:21] ✅ User created successfully: testuser@example.com
[14:23:25] ℹ️ Student attempting login: testuser@example.com
[14:23:26] ✅ Student logged in successfully: testuser@example.com
```

### Workflow Status:
```
Step 1: Create User     ✅
Step 2: Student Login   ✅

🎉 Workflow Phase 1 Complete! Ready to proceed to next steps.
```

## 🏗️ Architecture

### File Structure:
```python
# Configuration (Lines 1-30)
- API endpoints
- Admin credentials
- Step states

# Session State (Lines 31-60)
- Admin authentication
- Workflow state tracking
- Data storage
- Logs

# Helper Functions (Lines 61-150)
- add_log()
- admin_login()
- create_student_user()
- student_login()
- reset_workflow()

# Streamlit UI (Lines 151-500)
- Sidebar (Admin auth + Reset)
- Step 1: Admin creates user
- Step 2: Student login
- Workflow logs
- Status summary
```

## 🔧 Configuration

### API Base URL:
```python
API_BASE_URL = "http://localhost:8000"
```

### Admin Credentials:
```python
ADMIN_EMAIL = "admin@lfa.com"
# Password: admin123 (enter at login screen)
```

### Port Configuration:
- **Dashboard:** Port 8502
- **Backend API:** Port 8000

## 🐛 Troubleshooting

### Dashboard won't start:
```bash
# Check if port 8502 is available
lsof -i :8502

# Kill existing Streamlit process
pkill -f streamlit
```

### Backend not responding:
```bash
# Check backend status
curl http://localhost:8000/health

# Restart backend
./start_backend.sh
```

### User creation fails:
1. Check backend logs for errors
2. Verify admin token is valid
3. Ensure email doesn't already exist
4. Check database connection

### Student login fails:
1. Verify user was created in Step 1
2. Check password matches
3. Wait a moment for database to sync
4. Check workflow logs for error details

## 🎯 Design Principles

### 1. **Step-by-Step Progression**
- One step at a time
- Clear dependencies
- Cannot skip steps

### 2. **Role-Based Actions**
- Each step clearly labeled with role
- Appropriate actions for each role
- Admin controls testing flow

### 3. **Conditional Enabling**
- Buttons disabled until prerequisites met
- Visual feedback on why button disabled
- Clear waiting messages

### 4. **Real-Time Feedback**
- Immediate success/error messages
- Timestamped action logs
- Visual state indicators

### 5. **Easy Reset**
- One-click workflow reset
- Start over quickly
- Test multiple scenarios

## 📈 Future Enhancements (Phase 2+)

### Planned Next Steps:
- [ ] Step 3: Student creates booking
- [ ] Step 4: Instructor unlocks quiz
- [ ] Step 5: Instructor marks attendance
- [ ] Step 6: Student accesses quiz
- [ ] Step 7: Student submits quiz
- [ ] Step 8: Instructor reviews submission

### Possible Features:
- [ ] Multiple workflow paths (ON-SITE, HYBRID, VIRTUAL)
- [ ] Export workflow logs to JSON/CSV
- [ ] Compare workflow runs
- [ ] Automated assertions/validations
- [ ] Integration with automated tests

## 📚 Related Files

- `interactive_workflow_dashboard.py` - Main dashboard code
- `start_interactive_workflow.sh` - Quick start script
- `clean_testing_dashboard.py` - Automated testing dashboard
- `test_complete_quiz_workflow.py` - CLI quiz workflow tests

## 🎯 Summary

**The Interactive Workflow Testing Dashboard provides:**

- ✅ **Step-by-step testing** - Clear workflow progression
- ✅ **Role-based actions** - Admin, Student, Instructor buttons
- ✅ **Conditional enabling** - Smart button states based on prerequisites
- ✅ **Real-time feedback** - Instant success/error messages
- ✅ **Visual workflow tracking** - Clear state indicators
- ✅ **Secure admin access** - Password + role verification
- ✅ **Complete audit trail** - Timestamped action logs
- ✅ **Easy reset** - Quick workflow restart for multiple tests

**Phase 1 Complete:** Admin creates user → Student first login

**Access the dashboard at:** http://localhost:8502

## ✅ Testing Checklist

### Before Testing:
- [ ] Backend is running (`./start_backend.sh`)
- [ ] Database is accessible
- [ ] Admin user exists in database
- [ ] Port 8502 is available

### During Testing:
- [ ] Admin can login successfully
- [ ] Step 1: Admin can create new user
- [ ] Step 2: Button is disabled until Step 1 complete
- [ ] Step 2: Button enables after Step 1 success
- [ ] Step 2: Student can login with new credentials
- [ ] Workflow logs show all actions
- [ ] Status summary shows correct states

### After Testing:
- [ ] Workflow shows complete status
- [ ] Can reset workflow successfully
- [ ] Can run workflow again with different user
- [ ] All logs are accurate and timestamped

---

**Ready to test?** Run `./start_interactive_workflow.sh` and let's go! 🚀
