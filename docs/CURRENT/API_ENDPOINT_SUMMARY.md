# 📡 API ENDPOINT SUMMARY

**Dátum**: 2025-12-17
**API Verzió**: v1
**Base URL**: `http://localhost:8000/api/v1`

---

## 🎯 ÁTTEKINTÉS

**Total Endpoints**: 349 endpoints across 47 files
**Authentication**: JWT Bearer Token
**Documentation**: http://localhost:8000/docs (Swagger UI)

---

## 📑 ENDPOINT KATEGÓRIÁK

### Authentication & Authorization (10 endpoints)
**File**: [auth.py](app/api/api_v1/endpoints/auth.py)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | ❌ | User login |
| POST | `/auth/register` | ❌ | User registration |
| POST | `/auth/refresh` | ✅ | Refresh JWT token |
| POST | `/auth/password-reset` | ❌ | Request password reset |
| POST | `/auth/password-reset/confirm` | ❌ | Confirm password reset |
| POST | `/auth/logout` | ✅ | User logout |
| GET | `/auth/me` | ✅ | Get current user |

---

### Users (11 endpoints)
**File**: [users.py](app/api/api_v1/endpoints/users.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/users/` | ✅ | ADMIN | List all users |
| GET | `/users/{id}` | ✅ | ANY | Get user by ID |
| PUT | `/users/{id}` | ✅ | ADMIN/SELF | Update user |
| DELETE | `/users/{id}` | ✅ | ADMIN | Delete user |
| GET | `/users/{id}/licenses` | ✅ | ANY | Get user licenses |
| GET | `/users/{id}/achievements` | ✅ | ANY | Get user achievements |
| GET | `/users/{id}/statistics` | ✅ | ANY | Get user statistics |
| GET | `/users/instructor/{id}/students` | ✅ | INSTRUCTOR | Get instructor's students |
| GET | `/users/instructor/{id}/student/{student_id}` | ✅ | INSTRUCTOR | Get student details |

**N+1 Risk**: ⚠️ HIGH (See [API Endpoint Audit - users.py](API_ENDPOINT_AUDIT_COMPLETE.md#5-userspy---instructor-students-endpoint))

---

### Sessions (9 endpoints)
**File**: [sessions.py](app/api/api_v1/endpoints/sessions.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/sessions/` | ✅ | ANY | List sessions (with filters) |
| POST | `/sessions/` | ✅ | INSTRUCTOR/ADMIN | Create session |
| GET | `/sessions/{id}` | ✅ | ANY | Get session details |
| PUT | `/sessions/{id}` | ✅ | INSTRUCTOR/ADMIN | Update session |
| DELETE | `/sessions/{id}` | ✅ | ADMIN | Delete session |
| GET | `/sessions/{id}/bookings` | ✅ | INSTRUCTOR/ADMIN | Get session bookings |
| GET | `/sessions/{id}/attendance` | ✅ | INSTRUCTOR/ADMIN | Get session attendance |
| GET | `/sessions/my-sessions` | ✅ | INSTRUCTOR | Get instructor's sessions |

**Filters**:
- `specialization`: Filter by specialization type
- `session_type`: ONSITE/HYBRID/VIRTUAL
- `start_date`, `end_date`: Date range
- `instructor_id`: Filter by instructor
- `available_only`: Only sessions with spots

**Best Practice**: ✅ EXCELLENT query optimization (see [API Endpoint Audit - sessions.py](API_ENDPOINT_AUDIT_COMPLETE.md#8-sessionspy---list-sessions-endpoint))

---

### Bookings (10 endpoints)
**File**: [bookings.py](app/api/api_v1/endpoints/bookings.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/bookings/` | ✅ | STUDENT | Create booking |
| GET | `/bookings/my-bookings` | ✅ | STUDENT | Get user bookings |
| GET | `/bookings/{id}` | ✅ | ANY | Get booking details |
| DELETE | `/bookings/{id}` | ✅ | STUDENT | Cancel booking |
| POST | `/bookings/{id}/confirm` | ✅ | ADMIN | Confirm waitlist booking |

**Session Rules**:
- ✅ Rule #1: 24h booking deadline enforced
- ✅ Rule #2: 12h cancellation deadline enforced

**N+1 Risk**: ⚠️ HIGH (See [API Endpoint Audit - bookings.py](API_ENDPOINT_AUDIT_COMPLETE.md#4-bookingspy---get-my-bookings-endpoint))

---

### Attendance (5 endpoints)
**File**: [attendance.py](app/api/api_v1/endpoints/attendance.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/attendance/` | ✅ | STUDENT | Check in to session |
| POST | `/attendance/mark` | ✅ | INSTRUCTOR | Mark attendance (two-way confirmation) |
| GET | `/attendance/` | ✅ | ADMIN | List all attendance records |
| GET | `/attendance/my-attendance` | ✅ | STUDENT | Get student attendance history |
| GET | `/attendance/instructor-overview` | ✅ | INSTRUCTOR | Get instructor dashboard |

**Session Rules**:
- ✅ Rule #3: 15min check-in window enforced

**N+1 Risk**: 🔴 CRITICAL (See [API Endpoint Audit - attendance.py](API_ENDPOINT_AUDIT_COMPLETE.md#2-attendancepy---instructor-overview-endpoint))

---

### Feedback (8 endpoints)
**File**: [feedback.py](app/api/api_v1/endpoints/feedback.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/feedback/` | ✅ | STUDENT | Submit feedback |
| GET | `/feedback/my-feedback` | ✅ | STUDENT | Get student feedback history |
| GET | `/feedback/session/{id}` | ✅ | ANY | Get session feedback |
| GET | `/feedback/instructor/{id}` | ✅ | ANY | Get instructor ratings |
| GET | `/feedback/{id}` | ✅ | ANY | Get feedback details |

**Session Rules**:
- ✅ Rule #4: 24h feedback window enforced

**Rating Constraint**: 1.0 ≤ rating ≤ 5.0

---

### Licenses (10 endpoints)
**File**: [licenses.py](app/api/api_v1/endpoints/licenses.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/licenses/` | ✅ | STUDENT | Create user license |
| GET | `/licenses/my-licenses` | ✅ | STUDENT | Get user licenses |
| GET | `/licenses/{id}` | ✅ | ANY | Get license details |
| PUT | `/licenses/{id}/upgrade` | ✅ | STUDENT | Upgrade license level |
| PUT | `/licenses/{id}/renew` | ✅ | STUDENT | Renew license |
| POST | `/licenses/{id}/verify-payment` | ✅ | ADMIN | Verify payment |
| GET | `/licenses/{id}/credits` | ✅ | STUDENT | Get credit balance |
| GET | `/licenses/user/{user_id}/all-skills` | ✅ | ANY | Get football skills |

**License Levels**:
- **LFA Player**: 8 levels (Prospect → Icon)
- **LFA Coach**: 8 levels (Assistant Coach → Legendary Coach)
- **Internship**: 3 levels (Junior → Lead Intern)

---

### Projects (22 endpoints)
**File**: [projects.py](app/api/api_v1/endpoints/projects.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/projects/` | ✅ | ANY | List projects |
| POST | `/projects/` | ✅ | INSTRUCTOR | Create project |
| GET | `/projects/{id}` | ✅ | ANY | Get project details |
| PUT | `/projects/{id}` | ✅ | INSTRUCTOR | Update project |
| DELETE | `/projects/{id}` | ✅ | INSTRUCTOR | Delete project |
| POST | `/projects/{id}/enroll` | ✅ | STUDENT | Enroll in project (quiz required) |
| GET | `/projects/{id}/milestones` | ✅ | ANY | Get project milestones |
| POST | `/projects/{id}/milestones/{milestone_id}/submit` | ✅ | STUDENT | Submit milestone |
| GET | `/projects/{id}/waitlist` | ✅ | INSTRUCTOR | Get project waitlist |
| ... | ... | ... | ... | (13 more endpoints) |

**N+1 Risk**: ⚠️ MEDIUM (See [API Endpoint Audit - projects.py](API_ENDPOINT_AUDIT_COMPLETE.md#7-projectspy---list-projects-endpoint))

---

### Semesters (6 endpoints)
**File**: [semesters.py](app/api/api_v1/endpoints/semesters.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/semesters/` | ✅ | ANY | List semesters |
| POST | `/semesters/` | ✅ | ADMIN | Create semester |
| GET | `/semesters/{id}` | ✅ | ANY | Get semester details |
| PUT | `/semesters/{id}` | ✅ | ADMIN | Update semester |
| GET | `/semesters/active` | ✅ | ANY | Get active semesters |

**Semester Status Lifecycle**:
```
DRAFT → ENROLLMENT_OPEN → ENROLLMENT_CLOSED → ACTIVE → IN_PROGRESS → COMPLETED → ARCHIVED
```

---

### Semester Enrollments (11 endpoints) 🆕
**File**: [semester_enrollments.py](app/api/api_v1/endpoints/semester_enrollments.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/semester-enrollments/` | ✅ | STUDENT | Enroll in semester |
| GET | `/semester-enrollments/my-enrollments` | ✅ | STUDENT | Get user enrollments |
| GET | `/semester-enrollments/{id}` | ✅ | ANY | Get enrollment details |
| PUT | `/semester-enrollments/{id}/verify-payment` | ✅ | ADMIN | Verify payment |
| GET | `/semester-enrollments/semester/{id}` | ✅ | ADMIN | Get semester enrollments |

**New Feature**: Multi-specialization enrollment per semester

---

### Instructor Assignments (11 endpoints) 🆕
**File**: [instructor_assignments.py](app/api/api_v1/endpoints/instructor_assignments.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/instructor-assignments/request` | ✅ | ADMIN | Create assignment request |
| GET | `/instructor-assignments/requests` | ✅ | INSTRUCTOR | Get assignment requests |
| POST | `/instructor-assignments/accept/{id}` | ✅ | INSTRUCTOR | Accept assignment |
| POST | `/instructor-assignments/decline/{id}` | ✅ | INSTRUCTOR | Decline assignment |
| GET | `/instructor-assignments/my-assignments` | ✅ | INSTRUCTOR | Get instructor assignments |

**Filters**:
- `specialization_type`: Filter by specialization
- `location_id`: Filter by location
- `time_period`: Q1/Q2/Q3/Q4 or M01-M12

**New Feature**: Demand-driven instructor assignment workflow

---

### Instructor Availability (6 endpoints) 🆕
**File**: [instructor_availability.py](app/api/api_v1/endpoints/instructor_availability.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/instructor-availability/` | ✅ | INSTRUCTOR | Create availability window |
| GET | `/instructor-availability/my-availability` | ✅ | INSTRUCTOR | Get instructor availability |
| PUT | `/instructor-availability/{id}` | ✅ | INSTRUCTOR | Update availability |
| DELETE | `/instructor-availability/{id}` | ✅ | INSTRUCTOR | Delete availability |
| GET | `/instructor-availability/search` | ✅ | ADMIN | Search available instructors |

---

### Quizzes (15 endpoints)
**File**: [quiz.py](app/api/api_v1/endpoints/quiz.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/quizzes/available` | ✅ | STUDENT | Get available quizzes |
| GET | `/quizzes/{id}` | ✅ | ANY | Get quiz details |
| POST | `/quizzes/{id}/attempt` | ✅ | STUDENT | Start quiz attempt |
| POST | `/quizzes/attempts/{id}/submit` | ✅ | STUDENT | Submit quiz attempt |
| GET | `/quizzes/my-attempts` | ✅ | STUDENT | Get user attempts |

**Session Rules**:
- ✅ Rule #5: Session-type quiz (HYBRID/VIRTUAL unlock)

**Quiz Types**: 8 question types (Multiple Choice, True/False, Short Answer, Long Answer, Matching, Scenario, Ordering, Calculation)

---

### GānCuju Belt System (8 endpoints) 🆕
**File**: [gancuju.py](app/api/api_v1/endpoints/gancuju.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/gancuju/belts` | ✅ | STUDENT | Get user belt progression |
| POST | `/gancuju/belts/promote` | ✅ | INSTRUCTOR | Promote student belt |
| GET | `/gancuju/skills` | ✅ | STUDENT | Get skill assessments |
| POST | `/gancuju/skills/assess` | ✅ | INSTRUCTOR | Assess defending skills |

**Defending Skills** (5 sub-skills):
- Jockeying
- Block Tackle
- Poke Tackle
- Slide Tackle
- Marking

---

### LFA Player (8 endpoints) 🆕
**File**: [lfa_player.py](app/api/api_v1/endpoints/lfa_player.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/lfa-player/progress` | ✅ | STUDENT | Get LFA Player progress |
| GET | `/lfa-player/skills` | ✅ | STUDENT | Get football skills |
| POST | `/lfa-player/skills/update` | ✅ | INSTRUCTOR | Update skill assessment |

---

### Reports (7 endpoints)
**File**: [reports.py](app/api/api_v1/endpoints/reports.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/reports/export-csv` | ✅ | ADMIN | Export sessions to CSV |
| GET | `/reports/attendance-report` | ✅ | ADMIN | Attendance report |
| GET | `/reports/instructor-performance` | ✅ | ADMIN | Instructor performance report |

**N+1 Risk**: 🔥 CRITICAL (See [API Endpoint Audit - reports.py](API_ENDPOINT_AUDIT_COMPLETE.md#1-reportspy---csv-export-endpoint))
**Performance**: 501 queries → 4 queries (99.2% improvement needed!)

---

### Analytics (5 endpoints)
**File**: [analytics.py](app/api/api_v1/endpoints/analytics.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/analytics/dashboard` | ✅ | ADMIN | Admin dashboard analytics |
| GET | `/analytics/student/{id}` | ✅ | INSTRUCTOR | Student analytics |
| GET | `/analytics/instructor/{id}` | ✅ | ADMIN | Instructor analytics |

---

### Invoices (6 endpoints) 🆕
**File**: [invoices.py](app/api/api_v1/endpoints/invoices.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/invoices/request` | ✅ | STUDENT | Request invoice |
| GET | `/invoices/my-invoices` | ✅ | STUDENT | Get user invoices |
| GET | `/invoices/{id}` | ✅ | ANY | Get invoice details |
| PUT | `/invoices/{id}/mark-paid` | ✅ | ADMIN | Mark invoice as paid |

**Payment Reference**: SWIFT-compatible format

---

### Coupons (7 endpoints) 🆕
**File**: [coupons.py](app/api/api_v1/endpoints/coupons.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/coupons/` | ✅ | ADMIN | Create coupon |
| GET | `/coupons/` | ✅ | ADMIN | List coupons |
| POST | `/coupons/validate` | ✅ | STUDENT | Validate coupon code |
| POST | `/coupons/apply` | ✅ | STUDENT | Apply coupon |

**Coupon Types**: PERCENT, FIXED, CREDITS

---

### Locations (6 endpoints) 🆕
**File**: [locations.py](app/api/api_v1/endpoints/locations.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/locations/` | ✅ | ANY | List locations |
| POST | `/locations/` | ✅ | ADMIN | Create location |
| GET | `/locations/{id}` | ✅ | ANY | Get location details |
| PUT | `/locations/{id}` | ✅ | ADMIN | Update location |
| DELETE | `/locations/{id}` | ✅ | ADMIN | Delete location |

---

### Invitation Codes (5 endpoints) 🆕
**File**: [invitation_codes.py](app/api/api_v1/endpoints/invitation_codes.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/invitation-codes/` | ✅ | ADMIN | Create invitation code |
| GET | `/invitation-codes/validate/{code}` | ❌ | PUBLIC | Validate code |
| POST | `/invitation-codes/redeem` | ✅ | STUDENT | Redeem code |

**Bonus Credits**: Partner codes provide bonus credits

---

### Motivation Assessment (2 endpoints) 🆕
**File**: [motivation.py](app/api/api_v1/endpoints/motivation.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/motivation/submit` | ✅ | STUDENT | Submit motivation assessment |
| GET | `/motivation/{user_id}` | ✅ | INSTRUCTOR | Get user motivation |

---

### License Renewal (4 endpoints) 🆕
**File**: [license_renewal.py](app/api/api_v1/endpoints/license_renewal.py)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/license-renewal/request` | ✅ | STUDENT | Request license renewal |
| GET | `/license-renewal/my-renewals` | ✅ | STUDENT | Get renewal history |
| PUT | `/license-renewal/{id}/approve` | ✅ | ADMIN | Approve renewal |

---

## 📊 PERFORMANCE METRICS

### Query Count by Endpoint (Estimated)

| Endpoint | Queries | Status | Priority |
|----------|---------|--------|----------|
| `GET /reports/export-csv` | 501 | 🔥 CRITICAL | P0 |
| `GET /attendance/instructor-overview` | 101 | 🔴 HIGH | P0 |
| `GET /bookings/my-bookings` | 151 | 🔴 HIGH | P0 |
| `GET /attendance/` | 201 | 🔴 HIGH | P0 |
| `GET /users/instructor/{id}/students` | 71 | 🔴 HIGH | P0 |
| `GET /sessions/` | 4 | ✅ OPTIMAL | - |

**Full Performance Audit**: [docs/CURRENT/API_ENDPOINT_AUDIT_COMPLETE.md](docs/CURRENT/API_ENDPOINT_AUDIT_COMPLETE.md)

---

## 🔒 AUTHENTICATION

### JWT Token Format

```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "role": "STUDENT",
  "exp": 1234567890
}
```

### Authorization Header

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 📚 RELATED DOCUMENTATION

- **API Endpoint Audit**: [API_ENDPOINT_AUDIT_COMPLETE.md](API_ENDPOINT_AUDIT_COMPLETE.md) - N+1 query fixes
- **System Architecture**: [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) - Architecture overview
- **Session Rules**: [SESSION_RULES_ETALON.md](SESSION_RULES_ETALON.md) - Business rules
- **Database Audit**: [DATABASE_STRUCTURE_AUDIT_COMPLETE.md](DATABASE_STRUCTURE_AUDIT_COMPLETE.md) - Database structure

---

**Document Készítő**: Claude Sonnet 4.5
**Dátum**: 2025-12-17
**Total Endpoints**: 349
**Endpoint Files**: 47

---

**END OF API ENDPOINT SUMMARY**
