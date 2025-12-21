# 🔐 Streamlit Frontend - Login Information

## 🌐 Access URLs

- **Streamlit Frontend**: http://localhost:8502
- **FastAPI Backend**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

---

## 👥 Test User Accounts

### 🔴 ADMIN Users

#### Admin User #1
- **Email**: `admin@lfa.com`
- **Password**: `admin123` ✅ **VERIFIED WORKING**
- **Name**: Admin User
- **ID**: 1

#### System Administrator
- **Email**: `admin@yourcompany.com`
- **Password**: `password123` *(likely - try this first)*
- **Name**: System Administrator
- **ID**: 4

---

### 🟢 INSTRUCTOR User

#### Grand Master
- **Email**: `grandmaster@lfa.com`
- **Password**: `password123` *(likely - try this first)*
- **Name**: Grand Master
- **ID**: 3
- **Note**: This is the main instructor account with all specializations

---

### 🔵 STUDENT Users

#### Junior Intern (Main Test Student)
- **Email**: `junior.intern@lfa.com`
- **Password**: `password123` *(likely - try this first)*
- **Name**: Junior Intern
- **ID**: 2

#### Early Booker Student
- **Email**: `student.early@test.com`
- **Password**: `password123`
- **Name**: Early Booker Student
- **ID**: 2931

#### Late Booker Student
- **Email**: `student.late@test.com`
- **Password**: `password123`
- **Name**: Late Booker Student
- **ID**: 2932

#### Test Students (Additional)
- `student.test1@test.com` - Test Student 1 (ID: 2934)
- `testlow@test.com` - Test Low Credit (ID: 2943)
- `testhigh@test.com` - Test High Credit (ID: 2944)

---

## 🧪 Testing Workflow

### 1️⃣ Test Admin Access
```
1. Open: http://localhost:8502
2. Login with: admin@lfa.com / admin123
3. Test new P2 features:
   - 🎫 Coupons Management
   - 🔔 Notifications (Admin view)
   - 📍 Locations Management
   - 🏅 Assignment Review
   - 👥 Groups Management
```

### 2️⃣ Test Instructor Access
```
1. Logout admin
2. Login with: grandmaster@lfa.com / password123
3. Test new P2 features:
   - 🔔 Notifications (Instructor view)
   - 🏅 Assignment Requests
   - 💬 Messages
```

### 3️⃣ Test Student Access
```
1. Logout instructor
2. Login with: junior.intern@lfa.com / password123
3. Test P0, P1, P2 features:
   - 🏆 Achievements
   - 📜 My Licenses
   - 📝 Quizzes
   - 💬 Messages
   - 📊 Competency
   - 📚 Curriculum
   - 🎓 Certificates
   - 🔔 Notifications
```

---

## ⚙️ Services Running

| Service | Port | Status | Command |
|---------|------|--------|---------|
| Backend (FastAPI) | 8000 | ✅ Running | `uvicorn app.main:app --reload` |
| Frontend (Streamlit) | 8502 | ✅ Running | `streamlit run 🏠_Home.py` |
| Database (PostgreSQL) | 5432 | ✅ Running | `lfa_intern_system` |

---

## 📝 Notes

- **ADMIN password**: `admin123` ✅ VERIFIED
- **Instructor/Student password**: Check TESZT_FIOKOK.md or test `password123`
- All users are active and ready for testing
- Database: `lfa_intern_system` @ `localhost:5432`

---

## 🐛 Troubleshooting

### Login doesn't work?
Try these alternative passwords:
- `password123`
- `Password123`
- `admin123` (for admin users)
- `test123`

### Can't access a page?
- Check if you're logged in with the correct role
- Some pages are role-specific (Admin/Instructor/Student)

### Backend not responding?
```bash
# Check if backend is running
lsof -i :8000

# Check backend logs
tail -f logs/backend.log
```

---

**Created**: 2024-12-17
**Last Updated**: 2024-12-17 22:45
