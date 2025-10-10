# ⚙️ ADMIN ROLE API ENDPOINTS

**Access Level**: Requires Authentication + Admin Role  
**Base URL**: `http://localhost:8000/api/v1/`  
**Authentication**: `Authorization: Bearer {access_token}`

---

## 👥 USER MANAGEMENT

### POST `/users/`
- **Purpose**: Create new user account
- **Access Level**: Admin only
- **Request Body**:
  ```json
  {
    "name": "John Doe",
    "email": "john.doe@example.com",
    "password": "secure_password",
    "role": "STUDENT",
    "is_active": true,
    "specialization": "MIDFIELDER"
  }
  ```
- **Response**: Created user details (without password)
- **Validation**: Email uniqueness, strong password requirements
- **Audit**: Tracks creation by admin user

### GET `/users/`
- **Purpose**: List all users with filters
- **Access Level**: Admin only
- **Parameters**:
  - `role` (optional): Filter by user role
  - `is_active` (optional): Filter by active status
  - `search` (optional): Search by name or email
  - `skip` (optional): Pagination offset
  - `limit` (optional): Results per page (max 100)
- **Response**:
  ```json
  {
    "users": [
      {
        "id": 123,
        "name": "John Doe",
        "email": "john@example.com", 
        "role": "STUDENT",
        "is_active": true,
        "created_at": "2025-09-01T00:00:00Z",
        "last_login": "2025-09-24T08:30:00Z",
        "stats": {
          "total_bookings": 15,
          "completed_sessions": 12,
          "quiz_attempts": 8
        }
      }
    ],
    "total": 156,
    "page": 1,
    "per_page": 20
  }
  ```

### PUT `/users/{user_id}`
- **Purpose**: Update user details
- **Access Level**: Admin only
- **Request Body**: Partial user update (role, status, profile)
- **Response**: Updated user details
- **Security**: Password changes require separate endpoint

### DELETE `/users/{user_id}`
- **Purpose**: Deactivate user account
- **Access Level**: Admin only
- **Response**: Confirmation of deactivation
- **Safety**: Soft delete - preserves data integrity

---

## 💳 PAYMENT VERIFICATION

### GET `/payment-verification/students`
- **Purpose**: List students with payment verification status
- **Access Level**: Admin only
- **Parameters**:
  - `verified` (optional): Filter by verification status
  - `semester_id` (optional): Filter by semester
- **Response**:
  ```json
  {
    "students": [
      {
        "id": 123,
        "name": "John Doe",
        "email": "john@example.com",
        "payment_verified": false,
        "semester_fee_amount": 150.00,
        "verification_deadline": "2025-10-01T00:00:00Z"
      }
    ]
  }
  ```

### POST `/payment-verification/students/{student_id}/verify`
- **Purpose**: Mark student payment as verified
- **Access Level**: Admin only
- **Request Body**:
  ```json
  {
    "amount": 150.00,
    "payment_method": "BANK_TRANSFER",
    "reference_number": "TXN123456",
    "notes": "Payment confirmed via bank statement"
  }
  ```
- **Response**: Verification confirmation
- **Side Effects**: Enables booking/enrollment for student

### POST `/payment-verification/students/{student_id}/unverify`
- **Purpose**: Remove payment verification (emergency use)
- **Access Level**: Admin only
- **Response**: Verification removal confirmation
- **Side Effects**: Blocks student bookings/enrollments

---

## 📊 SYSTEM ANALYTICS

### GET `/analytics/dashboard`
- **Purpose**: Get system-wide analytics dashboard
- **Access Level**: Admin only
- **Response**:
  ```json
  {
    "overview": {
      "total_users": 245,
      "active_students": 198,
      "active_instructors": 12,
      "total_sessions_this_month": 89,
      "booking_rate": 87.5
    },
    "user_growth": {
      "new_registrations_this_month": 23,
      "retention_rate": 92.1,
      "churn_analysis": { ... }
    },
    "financial": {
      "payment_verification_rate": 94.2,
      "outstanding_payments": 12,
      "revenue_projection": 28500.00
    },
    "engagement": {
      "session_completion_rate": 89.7,
      "quiz_participation": 78.3,
      "project_enrollment_rate": 65.4
    }
  }
  ```

### GET `/reports/financial`
- **Purpose**: Generate financial reports
- **Access Level**: Admin only
- **Parameters**: Date range, export format
- **Response**: Payment tracking and revenue analysis

### GET `/reports/usage`
- **Purpose**: System usage and performance reports
- **Access Level**: Admin only
- **Response**: Session utilization, popular features, user activity

---

## 🎓 ACADEMIC MANAGEMENT

### GET `/semesters/`
- **Purpose**: List all academic semesters
- **Access Level**: Admin only
- **Response**: Semester list with enrollment stats

### POST `/semesters/`
- **Purpose**: Create new academic semester
- **Access Level**: Admin only
- **Request Body**:
  ```json
  {
    "name": "Spring 2026",
    "start_date": "2026-01-15",
    "end_date": "2026-05-15", 
    "enrollment_deadline": "2026-01-01",
    "fee_amount": 150.00
  }
  ```

### GET `/groups/`
- **Purpose**: Manage user groups and permissions
- **Access Level**: Admin only
- **Response**: Group hierarchy and member lists

---

## 🔒 SYSTEM SECURITY

### GET `/users/{user_id}/audit-log`
- **Purpose**: View user activity audit trail
- **Access Level**: Admin only
- **Response**: Chronological list of user actions
- **Privacy**: Sensitive for compliance/security investigations

### POST `/users/{user_id}/reset-password`
- **Purpose**: Force password reset for user
- **Access Level**: Admin only
- **Request Body**: New temporary password or reset token
- **Security**: Requires user to change on next login

### GET `/debug/system-status`
- **Purpose**: System health and performance monitoring
- **Access Level**: Admin only
- **Response**: Server stats, database performance, error rates
- **Production**: Should be disabled in production environment

---

## 📱 NOTIFICATION MANAGEMENT

### GET `/notifications/system`
- **Purpose**: Manage system-wide notifications
- **Access Level**: Admin only
- **Response**: Global announcements and alerts

### POST `/notifications/broadcast`
- **Purpose**: Send notification to user groups
- **Access Level**: Admin only
- **Request Body**:
  ```json
  {
    "recipient_groups": ["STUDENT", "INSTRUCTOR"],
    "title": "System Maintenance Notice",
    "message": "Scheduled maintenance on Sunday 2-4 AM",
    "priority": "HIGH",
    "expires_at": "2025-10-15T00:00:00Z"
  }
  ```

---

## ⚠️ CRITICAL ADMIN RESPONSIBILITIES

1. **Data Protection**: Access to all user data requires justification
2. **Payment Verification**: Financial responsibility for student access
3. **User Management**: Account creation/deactivation audit trail
4. **System Security**: Monitor for suspicious activity
5. **Compliance**: Ensure GDPR/privacy regulation compliance
6. **Backup Management**: Data integrity and disaster recovery

---

## 🧪 TESTING EXAMPLES

### Create User
```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Student",
    "email": "new.student@example.com",
    "password": "SecurePass123!",
    "role": "STUDENT"
  }'
```

### Verify Payment
```bash
curl -X POST http://localhost:8000/api/v1/payment-verification/students/123/verify \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 150.00,
    "payment_method": "BANK_TRANSFER",
    "reference_number": "TXN789"
  }'
```

### Get System Analytics
```bash
curl -X GET http://localhost:8000/api/v1/analytics/dashboard \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

**⚠️ SECURITY WARNING**: Admin endpoints have access to sensitive data and system controls. Use with extreme caution and ensure proper audit logging.