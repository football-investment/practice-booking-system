# 👨‍🏫 INSTRUCTOR ROLE API ENDPOINTS

**Access Level**: Requires Authentication + Instructor Role  
**Base URL**: `http://localhost:8000/api/v1/`  
**Authentication**: `Authorization: Bearer {access_token}`

---

## 📊 ANALYTICS & REPORTING

### GET `/analytics/metrics`
- **Purpose**: Get performance analytics for instructor's sessions
- **Access Level**: Instructor/Admin
- **Parameters**:
  - `start_date` (optional): ISO date format (YYYY-MM-DD)
  - `end_date` (optional): ISO date format (YYYY-MM-DD)  
  - `semester_id` (optional): Filter by semester
- **Response**:
  ```json
  {
    "sessions": {
      "total": 45,
      "completed": 42,
      "cancelled": 3,
      "completion_rate": 93.3
    },
    "bookings": {
      "total": 234,
      "confirmed": 210,
      "cancelled": 24,
      "show_up_rate": 89.7
    },
    "attendance": {
      "total_attendees": 198,
      "average_per_session": 4.7,
      "punctuality_rate": 85.4
    },
    "student_engagement": {
      "active_students": 67,
      "repeat_bookings": 156,
      "satisfaction_score": 4.6
    }
  }
  ```

### GET `/analytics/student-performance`
- **Purpose**: Analyze student performance in instructor's sessions
- **Access Level**: Instructor (own sessions only)
- **Response**: Student progress and engagement metrics

### GET `/analytics/session-trends`
- **Purpose**: Session booking and attendance trends over time
- **Access Level**: Instructor/Admin
- **Response**: Time series data for dashboard charts

---

## 🎯 SESSION MANAGEMENT

### POST `/sessions/`
- **Purpose**: Create a new training session
- **Access Level**: Instructor
- **Request Body**:
  ```json
  {
    "title": "Advanced Football Training",
    "description": "Focus on tactical positioning and ball control",
    "date_start": "2025-10-01T14:00:00Z",
    "date_end": "2025-10-01T16:00:00Z",
    "location": "Training Ground A",
    "capacity": 20,
    "specialization": "GOALKEEPER",
    "difficulty_level": "ADVANCED"
  }
  ```
- **Response**: Created session with ID and details
- **Validation**: Date conflicts, capacity limits, location availability

### GET `/sessions/instructor/my`
- **Purpose**: Get sessions created by instructor
- **Access Level**: Instructor (own sessions only)
- **Parameters**: Filter by date range, status, upcoming only
- **Response**: List of instructor's sessions with booking counts

### PATCH `/sessions/{session_id}`
- **Purpose**: Update session details
- **Access Level**: Instructor (own sessions only)
- **Request Body**: Partial session update
- **Response**: Updated session details
- **Restrictions**: Cannot modify past sessions with bookings

### DELETE `/sessions/{session_id}`
- **Purpose**: Cancel/delete a session
- **Access Level**: Instructor (own sessions only)
- **Response**: Confirmation of deletion
- **Side Effects**: Notifies booked students, refunds if applicable

---

## 👥 STUDENT MONITORING

### GET `/sessions/{session_id}/bookings`
- **Purpose**: View students booked for a specific session
- **Access Level**: Instructor (own sessions only)
- **Response**:
  ```json
  {
    "session_id": 456,
    "bookings": [
      {
        "id": 789,
        "student": {
          "id": 123,
          "name": "John Doe",
          "email": "john@example.com",
          "specialization": "MIDFIELDER"
        },
        "booking_date": "2025-09-20T10:00:00Z",
        "status": "confirmed",
        "notes": "First time attending"
      }
    ],
    "total_bookings": 12,
    "capacity": 20,
    "waitlist": 0
  }
  ```

### GET `/users/students`
- **Purpose**: Get list of students for instructor oversight
- **Access Level**: Instructor
- **Parameters**: Search, filter by project enrollment
- **Response**: Student list with basic info and progress

### GET `/users/{student_id}/progress`
- **Purpose**: View detailed student progress
- **Access Level**: Instructor (students in their sessions/projects)
- **Response**: Comprehensive progress tracking
- **Privacy**: Limited to students instructor has worked with

---

## 📝 ATTENDANCE TRACKING

### POST `/attendance/`
- **Purpose**: Mark student attendance for session
- **Access Level**: Instructor (own sessions only)
- **Request Body**:
  ```json
  {
    "session_id": 456,
    "student_id": 123,
    "status": "PRESENT",
    "notes": "Excellent participation",
    "arrival_time": "2025-10-01T14:05:00Z"
  }
  ```
- **Response**: Attendance record confirmation

### GET `/attendance/session/{session_id}`
- **Purpose**: Get attendance records for a session
- **Access Level**: Instructor (own sessions only)
- **Response**: List of attendance records with student details

### PATCH `/attendance/{attendance_id}`
- **Purpose**: Update attendance record
- **Access Level**: Instructor (own sessions only)
- **Response**: Updated attendance details

---

## 💬 FEEDBACK MANAGEMENT  

### GET `/feedback/session/{session_id}`
- **Purpose**: View feedback for instructor's session
- **Access Level**: Instructor (own sessions only)
- **Response**: Anonymous student feedback and ratings

### POST `/feedback/respond`
- **Purpose**: Respond to student feedback
- **Access Level**: Instructor
- **Request Body**:
  ```json
  {
    "feedback_id": 789,
    "instructor_response": "Thank you for the feedback. I'll focus more on individual technique next time.",
    "improvement_plan": "Add 15 minutes of one-on-one coaching per session"
  }
  ```

### GET `/feedback/summary`
- **Purpose**: Get aggregated feedback summary
- **Access Level**: Instructor (own sessions only)
- **Response**: Feedback trends and improvement areas

---

## 📋 PROJECT MANAGEMENT

### GET `/projects/my-projects`
- **Purpose**: Get projects managed by instructor
- **Access Level**: Instructor (own projects only)
- **Response**: Projects with enrollment and progress data

### GET `/projects/{project_id}/students`
- **Purpose**: View students enrolled in instructor's project
- **Access Level**: Instructor (own projects only)
- **Response**: Student list with project progress

### PATCH `/projects/{project_id}/students/{student_id}/grade`
- **Purpose**: Grade student project work
- **Access Level**: Instructor (own projects only)
- **Request Body**: Grade and feedback
- **Response**: Updated student grade

---

## 📱 NOTIFICATIONS & MESSAGING

### GET `/messages/`
- **Purpose**: Get instructor's messages
- **Access Level**: Instructor (own messages only)
- **Response**: Conversation threads with students and admins

### POST `/messages/`
- **Purpose**: Send message to student or admin
- **Access Level**: Instructor
- **Request Body**:
  ```json
  {
    "recipient_id": 123,
    "subject": "Session Feedback",
    "content": "Great improvement in your passing accuracy!"
  }
  ```

---

## 🔒 INSTRUCTOR ACCESS PERMISSIONS

1. **Session Ownership**: Full control over created sessions
2. **Student Data**: Access limited to students in instructor's sessions/projects
3. **Analytics Scope**: Only data related to instructor's activities
4. **Feedback Access**: Can view feedback for own sessions
5. **Grading Authority**: Can grade students in assigned projects
6. **Communication**: Can message students and admins

---

## 🧪 TESTING EXAMPLES

### Create a Session
```bash
curl -X POST http://localhost:8000/api/v1/sessions/ \
  -H "Authorization: Bearer YOUR_INSTRUCTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Defensive Tactics Training",
    "date_start": "2025-10-01T14:00:00Z",
    "date_end": "2025-10-01T16:00:00Z",
    "location": "Field 1",
    "capacity": 16
  }'
```

### Get Analytics
```bash
curl -X GET "http://localhost:8000/api/v1/analytics/metrics?start_date=2025-09-01&end_date=2025-09-30" \
  -H "Authorization: Bearer YOUR_INSTRUCTOR_TOKEN"
```

### Mark Attendance
```bash
curl -X POST http://localhost:8000/api/v1/attendance/ \
  -H "Authorization: Bearer YOUR_INSTRUCTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 456,
    "student_id": 123,
    "status": "PRESENT"
  }'
```