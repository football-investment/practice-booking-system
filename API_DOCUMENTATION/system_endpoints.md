# 🔧 SYSTEM & INTERNAL API ENDPOINTS

**Access Level**: System/Development Use  
**Base URL**: `http://localhost:8000/api/v1/`  
**Authentication**: Varies by endpoint

---

## 🩺 HEALTH & DEBUG ENDPOINTS

### GET `/debug/system-status`
- **Purpose**: System health monitoring and diagnostics
- **Access Level**: Admin/Development only
- **Authentication**: Admin JWT required
- **Response**:
  ```json
  {
    "status": "healthy",
    "timestamp": "2025-09-24T16:52:00Z",
    "version": "1.0.0",
    "database": {
      "status": "connected",
      "connection_count": 12,
      "response_time_ms": 45
    },
    "memory": {
      "used_mb": 256,
      "available_mb": 2048,
      "usage_percent": 12.5
    },
    "services": {
      "auth_service": "running",
      "notification_service": "running",
      "file_service": "running"
    }
  }
  ```
- **Production**: ⚠️ Should be disabled in production

### GET `/debug/test-connection`
- **Purpose**: Test database connectivity
- **Access Level**: Development only
- **Response**: Connection status and latency

### POST `/debug/simulate-error`
- **Purpose**: Trigger test errors for monitoring
- **Access Level**: Development only
- **Request Body**: Error type and parameters

---

## 🔔 NOTIFICATION SYSTEM

### GET `/notifications/`
- **Purpose**: Get user's notifications
- **Access Level**: Authenticated users (own notifications)
- **Parameters**: 
  - `unread_only` (boolean): Show only unread notifications
  - `limit` (int): Maximum results (default 20)
- **Response**:
  ```json
  {
    "notifications": [
      {
        "id": 456,
        "title": "Session Reminder",
        "message": "Your training session starts in 1 hour",
        "type": "REMINDER",
        "priority": "MEDIUM",
        "read": false,
        "created_at": "2025-09-24T15:00:00Z",
        "expires_at": "2025-09-25T14:00:00Z"
      }
    ],
    "unread_count": 3,
    "total": 15
  }
  ```

### PATCH `/notifications/{notification_id}/read`
- **Purpose**: Mark notification as read
- **Access Level**: Authenticated users (own notifications)
- **Response**: Updated notification status

### DELETE `/notifications/{notification_id}`
- **Purpose**: Delete notification
- **Access Level**: User (own notifications) or Admin
- **Response**: Deletion confirmation

---

## 💬 MESSAGING SYSTEM

### GET `/messages/`
- **Purpose**: Get user's message threads
- **Access Level**: Authenticated users
- **Parameters**: Filter by sender, date range, unread status
- **Response**: Message thread list with preview

### POST `/messages/`
- **Purpose**: Send new message
- **Access Level**: Authenticated users
- **Request Body**:
  ```json
  {
    "recipient_id": 123,
    "subject": "Session Feedback",
    "content": "Great job in today's training session!",
    "priority": "NORMAL",
    "message_type": "FEEDBACK"
  }
  ```

### GET `/messages/{thread_id}`
- **Purpose**: Get full message thread
- **Access Level**: Thread participants only
- **Response**: Complete conversation history

---

## 📈 PROGRESSION TRACKING

### GET `/progression/progress`
- **Purpose**: Get user's learning progression
- **Access Level**: Student (own progress) or Instructor/Admin
- **Response**:
  ```json
  {
    "user_id": 123,
    "overall_progress": 67.5,
    "level": 8,
    "experience_points": 3450,
    "tracks": [
      {
        "track_name": "Defensive Skills",
        "progress_percent": 75.0,
        "completed_milestones": 6,
        "total_milestones": 8,
        "current_level": "INTERMEDIATE"
      }
    ],
    "recent_achievements": [
      {
        "id": "first_goal",
        "name": "First Goal Scorer",
        "earned_at": "2025-09-20T14:30:00Z"
      }
    ]
  }
  ```

### POST `/progression/progress/update`
- **Purpose**: Update user progression (system internal)
- **Access Level**: System/Instructor only
- **Request Body**: Progress increments and milestone completions

---

## 🎯 SPECIALIZATION & TRACKS

### GET `/specializations/`
- **Purpose**: List available football specializations
- **Access Level**: Authenticated users
- **Response**: Specialization catalog with requirements

### GET `/tracks/`
- **Purpose**: Get educational track information
- **Access Level**: Authenticated users
- **Response**:
  ```json
  {
    "tracks": [
      {
        "id": 1,
        "name": "Professional Development Track",
        "description": "Advanced training for competitive play",
        "specializations": ["STRIKER", "MIDFIELDER", "DEFENDER"],
        "duration_weeks": 16,
        "prerequisites": ["basic_skills_quiz"],
        "certification_available": true
      }
    ]
  }
  ```

### POST `/parallel-specializations/enroll`
- **Purpose**: Enroll in multiple specialization tracks
- **Access Level**: Student (with payment verification)
- **Request Body**: List of specialization IDs
- **Payment Required**: ✅ Must have verified payment

---

## 🏆 CERTIFICATE MANAGEMENT

### GET `/certificates/available`
- **Purpose**: List certificates user can earn
- **Access Level**: Student
- **Response**: Available certifications with requirements

### POST `/certificates/request`
- **Purpose**: Request certificate issuance
- **Access Level**: Student (completed requirements)
- **Request Body**: Certificate type and supporting evidence

### GET `/certificates/my`
- **Purpose**: Get user's earned certificates
- **Access Level**: Student (own certificates)
- **Response**: Certificate collection with verification codes

---

## 🏮 GANCUJU LICENSE SYSTEM

### GET `/licenses/`
- **Purpose**: View GānCuju™️©️ licensing information
- **Access Level**: Admin only
- **Response**: License status, usage metrics, compliance data

### POST `/licenses/validate`
- **Purpose**: Validate system license
- **Access Level**: System internal
- **Request Body**: License key and validation parameters

---

## 🤖 ADAPTIVE LEARNING

### GET `/adaptive-learning/recommendations`
- **Purpose**: Get AI-powered learning recommendations
- **Access Level**: Student
- **Response**:
  ```json
  {
    "recommendations": [
      {
        "type": "SESSION",
        "title": "Ball Control Workshop",
        "reason": "Based on your recent quiz results",
        "confidence_score": 0.87,
        "session_id": 456
      },
      {
        "type": "QUIZ",
        "title": "Tactical Awareness Assessment", 
        "reason": "To identify knowledge gaps",
        "confidence_score": 0.92,
        "quiz_id": 789
      }
    ]
  }
  ```

### POST `/adaptive-learning/feedback`
- **Purpose**: Provide learning feedback to AI system
- **Access Level**: Student
- **Request Body**: Learning outcome and satisfaction data

---

## 🔒 SYSTEM SECURITY FEATURES

1. **Rate Limiting**: Implemented on authentication and sensitive endpoints
2. **JWT Validation**: All protected endpoints verify token signature and expiration
3. **Role-Based Access**: Strict role checking before endpoint access
4. **Data Isolation**: Users can only access their own data
5. **Audit Logging**: All admin actions are logged for compliance
6. **Payment Gates**: Booking/enrollment blocked without payment verification

---

## 📊 INTEGRATION POINTS

### Frontend API Calls
- **Authentication Flow**: Login → Token Storage → Authenticated Requests
- **Real-time Updates**: WebSocket connections for notifications
- **File Uploads**: Secure file handling for project submissions
- **Error Handling**: Consistent error format across all endpoints

### Third-Party Integrations
- **Payment Processing**: Integration hooks for payment verification
- **Email Service**: Notification and communication delivery
- **Analytics**: Data export for business intelligence tools
- **Backup Systems**: Automated data backup and recovery

---

## 🧪 SYSTEM TESTING

### Performance Benchmarks
- **Response Time**: < 200ms for simple queries, < 1s for complex analytics
- **Throughput**: Supports 100+ concurrent users
- **Database**: Optimized queries with proper indexing
- **Caching**: Redis caching for frequent data access

### Security Testing
- **Penetration Testing**: Regular security audits
- **SQL Injection**: Protected via parameterized queries
- **XSS Protection**: Input validation and sanitization
- **CSRF Prevention**: Token-based request validation

---

**🔧 MAINTENANCE NOTES**: 
- Debug endpoints should be disabled in production
- System endpoints require careful monitoring
- Internal APIs need rate limiting and access controls