# 🎓 STUDENT ROLE API ENDPOINTS

**Access Level**: Requires Authentication + Student Role  
**Base URL**: `http://localhost:8000/api/v1/`  
**Authentication**: `Authorization: Bearer {access_token}`

---

## 📚 SESSION BOOKING SYSTEM

### GET `/bookings/`
- **Purpose**: Get all bookings (admin/instructor access)
- **Access Level**: Admin/Instructor only
- **Parameters**: Query filters for semester, status, date range
- **Response**: List of all system bookings with user details
- **Student Access**: ❌ Not accessible to students

### GET `/bookings/my`
- **Purpose**: Get current student's bookings
- **Access Level**: Student (own data only)
- **Parameters**: 
  - `status` (optional): Filter by booking status
  - `upcoming` (optional): Show only future bookings
- **Response**:
  ```json
  {
    "bookings": [
      {
        "id": 123,
        "session_id": 456,
        "status": "confirmed",
        "booking_date": "2025-09-24T10:00:00Z",
        "session": {
          "title": "Football Training",
          "date_start": "2025-09-25T14:00:00Z",
          "location": "Training Ground A"
        }
      }
    ],
    "total": 1
  }
  ```
- **Error Codes**: 
  - `401` - Invalid/expired token
  - `403` - Not a student role

### POST `/bookings/`
- **Purpose**: Book a training session
- **Access Level**: Student (with payment verification)
- **Payment Required**: ✅ Must have verified payment status
- **Request Body**:
  ```json
  {
    "session_id": 456,
    "notes": "Looking forward to training"
  }
  ```
- **Response**:
  ```json
  {
    "id": 789,
    "session_id": 456, 
    "status": "confirmed",
    "booking_date": "2025-09-24T10:00:00Z",
    "message": "Successfully booked session"
  }
  ```
- **Error Codes**:
  - `402` - Payment verification required
  - `409` - Session already booked or full
  - `404` - Session not found
  - `400` - Booking deadline passed

### PUT `/bookings/{booking_id}/cancel`
- **Purpose**: Cancel a booking
- **Access Level**: Student (own bookings only)
- **Parameters**: `booking_id` - ID of booking to cancel
- **Response**:
  ```json
  {
    "id": 789,
    "status": "cancelled",
    "cancelled_at": "2025-09-24T10:30:00Z"
  }
  ```
- **Error Codes**:
  - `403` - Not your booking
  - `400` - Cannot cancel (too close to session time)
  - `404` - Booking not found

---

## 🧠 QUIZ SYSTEM

### GET `/quizzes/available`
- **Purpose**: Get available quizzes for student
- **Access Level**: Student
- **Response**: List of quizzes student can take
- **Filters**: By category, difficulty, completion status

### GET `/quizzes/{quiz_id}`
- **Purpose**: Get quiz details for taking
- **Access Level**: Student
- **Response**: Quiz questions and metadata
- **Security**: Anti-cheating measures applied

### POST `/quizzes/start`
- **Purpose**: Start a quiz attempt
- **Access Level**: Student
- **Request Body**:
  ```json
  {
    "quiz_id": 123
  }
  ```
- **Response**: Quiz attempt ID and start time

### POST `/quizzes/submit`
- **Purpose**: Submit quiz answers
- **Access Level**: Student
- **Request Body**:
  ```json
  {
    "attempt_id": 456,
    "answers": [
      {"question_id": 1, "answer": "A"},
      {"question_id": 2, "answer": "B"}
    ]
  }
  ```
- **Response**: Score and completion details

### GET `/quizzes/attempts/my`
- **Purpose**: Get student's quiz attempt history
- **Access Level**: Student (own attempts only)
- **Response**: List of completed attempts with scores

---

## 📋 PROJECT SYSTEM

### GET `/projects/`
- **Purpose**: Get available projects for enrollment
- **Access Level**: Student
- **Parameters**: Filter by category, difficulty, semester
- **Response**: List of open projects with enrollment info

### GET `/projects/my`
- **Purpose**: Get student's enrolled projects
- **Access Level**: Student (own enrollments only)
- **Response**: Active project enrollments with progress

### POST `/projects/{project_id}/enroll`
- **Purpose**: Enroll in a project
- **Access Level**: Student (with payment verification)
- **Payment Required**: ✅ Must have verified payment status
- **Prerequisites**: May require completed quizzes
- **Response**: Enrollment confirmation

### GET `/projects/{project_id}/progress`
- **Purpose**: View project progress and milestones
- **Access Level**: Student (enrolled projects only)
- **Response**: Progress tracking and milestone completion

---

## 🎯 GAMIFICATION SYSTEM

### GET `/gamification/profile`
- **Purpose**: Get student's gamification profile
- **Access Level**: Student (own profile only)
- **Response**: 
  ```json
  {
    "level": 15,
    "experience_points": 2500,
    "achievements": ["first_booking", "quiz_master"],
    "badges": ["punctual", "team_player"],
    "leaderboard_position": 23
  }
  ```

### GET `/gamification/achievements`
- **Purpose**: Get available and earned achievements
- **Access Level**: Student
- **Response**: Achievement catalog with progress

### GET `/gamification/leaderboard`
- **Purpose**: View leaderboard (anonymous)
- **Access Level**: Student
- **Response**: Top performers without personal details

---

## 💳 PAYMENT VERIFICATION

### GET `/payment-verification/students/{student_id}/status`
- **Purpose**: Check payment verification status
- **Access Level**: Student (own status only) / Admin (all students)
- **Response**:
  ```json
  {
    "student_id": 123,
    "payment_verified": true,
    "verified_at": "2025-09-01T00:00:00Z",
    "verified_by_admin": "admin@example.com"
  }
  ```

---

## 🔒 STUDENT ACCESS RESTRICTIONS

1. **Data Isolation**: Students can only access their own data
2. **Payment Gates**: Booking and project enrollment require payment verification
3. **Quiz Integrity**: Anti-cheating measures in quiz system
4. **Session Limits**: Cannot book past capacity or deadline
5. **Role Validation**: All endpoints check student role before access

---

## 🧪 TESTING EXAMPLES

### Book a Session
```bash
curl -X POST http://localhost:8000/api/v1/bookings/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id": 456, "notes": "First training session"}'
```

### Get My Bookings
```bash
curl -X GET http://localhost:8000/api/v1/bookings/my \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Start a Quiz
```bash
curl -X POST http://localhost:8000/api/v1/quizzes/start \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"quiz_id": 123}'
```