# 🧪 Tesztforgatókönyv - Practice Booking System

## 📋 Rendszer Állapot és Elérhetőség

### ✅ Szolgáltatások Futtatása
- **Backend**: `http://localhost:8000` ✅ Működik
- **Frontend**: `http://localhost:3000` ✅ Működik
- **API Dokumentáció**: `http://localhost:8000/docs`

### 🔐 Tesztfelhasználók

| Szerep | Email | Jelszó | Token (7 napig érvényes) |
|--------|-------|--------|---------------------------|
| **Student** | `test.student@devstudio.com` | `testpass123` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LnN0dWRlbnRAZGV2c3R1ZGlvLmNvbSIsImV4cCI6MTc1NzkxNDg3OCwidHlwZSI6ImFjY2VzcyJ9.d4m_k6bQqjMCiLB4Yv-xivU3S_CW_5zZGNuK3ZRnqEk` |
| **Instructor** | `test.instructor@devstudio.com` | `instructor123` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Lmluc3RydWN0b3JAZGV2c3R1ZGlvLmNvbSIsImV4cCI6MTc1NzkxNDg3OCwidHlwZSI6ImFjY2VzcyJ9.297Y2dYD_31a-seH0bi6_yZh-9fOpFibT2Ik3O4s5DM` |

---

## 🎯 1. JELENLÉT IGAZOLÁS (Attendance) TESZTELÉSE

### 1.1 Student Check-in Funkció

**API Tesztelés:**
```bash
# 1. Token beállítása
export STUDENT_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LnN0dWRlbnRAZGV2c3R1ZGlvLmNvbSIsImV4cCI6MTc1NzkxNDg3OCwidHlwZSI6ImFjY2VzcyJ9.d4m_k6bQqjMCiLB4Yv-xivU3S_CW_5zZGNuK3ZRnqEk"

# 2. Check-in végrehajtása (Booking ID: 1)
curl -X POST "http://localhost:8000/api/v1/attendance/1/checkin" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Tesztelési check-in"}' \
  | python3 -m json.tool
```

**Elvárt Eredmény:**
```json
{
    "user_id": 9,
    "session_id": 1,
    "booking_id": 1,
    "status": "present",
    "notes": "Tesztelési check-in",
    "id": 1,
    "check_in_time": "2025-09-15T05:12:16.966630",
    "check_out_time": null,
    "marked_by": null,
    "created_at": "2025-09-15T07:12:16.972475",
    "updated_at": "2025-09-15T07:12:16.972481"
}
```

**Frontend Tesztelés:**
1. Belépés: `http://localhost:3000/login`
2. Student credentials használata
3. Navigálás: Dashboard → Sessions → Check-in gomb
4. Ellenőrzés: "Present" státusz megjelenése

### 1.2 Instructor Attendance Overview

**API Tesztelés:**
```bash
# 1. Instructor token beállítása
export INSTRUCTOR_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Lmluc3RydWN0b3JAZGV2c3R1ZGlvLmNvbSIsImV4cCI6MTc1NzkxNDg3OCwidHlwZSI6ImFjY2VzcyJ9.297Y2dYD_31a-seH0bi6_yZh-9fOpFibT2Ik3O4s5DM"

# 2. Attendance overview lekérése
curl -X GET "http://localhost:8000/api/v1/attendance/instructor/overview" \
  -H "Authorization: Bearer $INSTRUCTOR_TOKEN" \
  | python3 -m json.tool
```

**Elvárt Eredmény:**
```json
{
    "sessions": [
        {
            "id": 1,
            "title": "Test Attendance Session",
            "current_bookings": 1,
            "attendance_count": 1,
            "date_start": "2025-09-15T04:56:52.029599",
            "date_end": "2025-09-15T07:11:52.029599"
        }
    ],
    "total": 1,
    "page": 1,
    "size": 50
}
```

---

## 📊 2. PROJEKT HALADÁS (Milestone) TESZTELÉSE

### 2.1 Student Project Progress

**API Tesztelés:**
```bash
# Projekt haladás lekérése (Project ID: 2)
curl -X GET "http://localhost:8000/api/v1/projects/2/progress" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  | python3 -m json.tool
```

**Elvárt Eredmény:**
```json
{
    "project_title": "Test Milestone Project",
    "enrollment_status": "active",
    "progress_status": "planning",
    "completion_percentage": 0.0,
    "overall_progress": 0,
    "sessions_completed": 0,
    "sessions_remaining": 8,
    "milestone_progress": [],
    "next_milestone": null
}
```

**Frontend Tesztelés:**
1. Student belépés után navigálás: Projects → My Projects
2. Project progress oldal elérése: `/student/projects/2/progress`
3. Milestone tracker komponens megjelenítése
4. Progress ring és statisztikák ellenőrzése

### 2.2 Instructor Project Management

**Frontend Tesztelés:**
1. Instructor belépés: `http://localhost:3000/login`
2. Navigálás: Dashboard → Projects → Student Progress
3. Test Student haladásának megtekintése
4. Milestone jóváhagyási funkciók elérhetősége

---

## 🖥️ 3. FRONTEND FUNKCIONALITÁS VALIDÁLÁSA

### 3.1 Hallgatói Felület

**Tesztelendő URL-ek:**
```
✅ Login: http://localhost:3000/login
✅ Dashboard: http://localhost:3000/student/dashboard
⏳ Sessions: http://localhost:3000/student/sessions
⏳ Projects: http://localhost:3000/student/projects
⏳ My Projects: http://localhost:3000/student/projects/my
⏳ Project Progress: http://localhost:3000/student/projects/2/progress
⏳ Bookings: http://localhost:3000/student/bookings
⏳ Gamification: http://localhost:3000/student/gamification
```

**Tesztelési Lépések:**
1. **Login tesztelés**
   - Helyes credentials: `test.student@devstudio.com` / `testpass123`
   - Helytelen credentials visszautasítása
   - Sikeres bejelentkezés után dashboard átirányítás

2. **Navigation tesztelés**
   - Sidebar menü működése
   - Breadcrumb navigáció
   - Back button funkciók

3. **Data Loading tesztelés**
   - Loading spinner megjelenése
   - Error handling
   - Empty state üzenetek

### 3.2 Instruktori Felület

**Tesztelendő URL-ek:**
```
✅ Login: http://localhost:3000/login
✅ Dashboard: http://localhost:3000/instructor/dashboard
⏳ Sessions: http://localhost:3000/instructor/sessions
⏳ Projects: http://localhost:3000/instructor/projects
⏳ Students: http://localhost:3000/instructor/students
⏳ Attendance: http://localhost:3000/instructor/attendance
```

---

## 🧪 4. SPECIÁLIS FUNKCIÓK TESZTELÉSE

### 4.1 Achievement System

**API Tesztelés:**
```bash
# Gamification adatok lekérése
curl -X GET "http://localhost:8000/api/v1/gamification/me" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  | python3 -m json.tool
```

**Frontend Tesztelés:**
1. Gamification profile megtekintése
2. Badge-ek és achievements megjelenítése
3. XP progress tracking

### 4.2 Real-time Features

**Tesztelendő Funkciók:**
- Auto-refresh komponensek
- Real-time attendance updates
- Live session status
- Progress updates

---

## ⚠️ 5. HIBAKEZELÉS TESZTELÉSE

### 5.1 API Error Handling

**Tesztelendő Esetek:**
1. **Lejárt token**: 401 Unauthorized
2. **Hiányzó jogosultság**: 403 Forbidden  
3. **Nem létező resource**: 404 Not Found
4. **Validation error**: 422 Unprocessable Entity

### 5.2 Frontend Error Handling

**Tesztelendő Esetek:**
1. Network connection hibák
2. API timeout
3. Invalid data responses
4. Route not found (404)

---

## 📱 6. RESPONSIVITÁS TESZTELÉSE

**Tesztelendő Eszközök:**
- Desktop: 1920x1080, 1366x768
- Tablet: iPad (768x1024)
- Mobile: iPhone (375x667), Android (360x640)

**Tesztelendő Elemek:**
- Navigation menü collapse/expand
- Table responsivitás
- Button és input field méretezés
- Chart és progress bar scaling

---

## 🔍 7. TELJESÍTMÉNY VALIDÁLÁSA

### 7.1 API Response Times

**Elvárt Értékek:**
- Health check: < 100ms
- Authentication: < 500ms
- Data queries: < 1000ms
- Complex operations: < 2000ms

### 7.2 Frontend Load Times

**Elvárt Értékek:**
- Initial page load: < 3s
- Route transitions: < 500ms
- Component renders: < 200ms

---

## ✅ 8. TESZT EREDMÉNYEK ÖSSZEFOGLALÁSA

### Backend API ✅
- [x] Attendance check-in működik
- [x] Instructor overview működik
- [x] Project progress API működik
- [x] Authentication working
- [x] Error handling proper

### Frontend Működőképesség ⏳
- [x] Login page accessible
- [x] Basic navigation working
- [ ] Full functionality validation pending
- [ ] Mobile responsiveness check needed

### Tesztadatok ✅
- [x] Test users created
- [x] Test session with booking
- [x] Test project with enrollment
- [x] Attendance record created

---

## 🚀 KÖVETKEZŐ LÉPÉSEK

1. **Frontend teljes funkcionális tesztelés**
2. **Mobile responsivitás validálása**  
3. **User experience tesztelés**
4. **Performance optimization**
5. **Error scenario completion**

**Általános állapot: 🟢 READY FOR TESTING**

Backend és core funkciók működnek, frontend elérhetőségi teszt következhet.