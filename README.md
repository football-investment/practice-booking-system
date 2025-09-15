# 🏈 Practice Booking System

**Automated Cross-Platform Practice Booking System with Comprehensive CI/CD Testing**

[![CI/CD Pipeline](https://github.com/footballinvestment/practice-booking-system/actions/workflows/cross-platform-testing.yml/badge.svg)](https://github.com/footballinvestment/practice-booking-system/actions/workflows/cross-platform-testing.yml)
[![iOS Safari Compatible](https://img.shields.io/badge/iOS%20Safari-Compatible-brightgreen.svg)](https://github.com/footballinvestment/practice-booking-system)
[![Cross Browser](https://img.shields.io/badge/Cross%20Browser-Chrome%20|%20Firefox%20|%20Safari%20|%20Edge-blue.svg)](https://github.com/footballinvestment/practice-booking-system)

## 🚀 **Quick Start**

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Git

### Installation
```bash
git clone https://github.com/footballinvestment/practice-booking-system.git
cd practice-booking-system

# Backend setup
pip install -r requirements.txt
python scripts/fresh_database_reset.py

# Frontend setup
cd frontend && npm install && cd ..

# Start both servers
./start_both.sh
```

**URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🌐 **Cross-Platform Testing**

### **Automated CI/CD Pipeline**
Every push triggers comprehensive testing across:

- **✅ Backend**: FastAPI + PostgreSQL + pytest
- **✅ Frontend**: React + Jest + build verification  
- **✅ Cross-Browser**: Chrome, Firefox, Safari, Edge
- **✅ iOS Safari**: Real device testing (iPhone, iPad)
- **✅ Performance**: Lighthouse CI (>80 score target)
- **✅ Security**: OWASP + CodeQL scanning

### **Test Accounts** 
```
Fresh Students (for onboarding testing):
- alex.newcomer@student.com / student123
- emma.fresh@student.com / student123
- mike.starter@student.com / student123

Instructor:
- sarah.johnson@instructor.com / instructor123

Admin:
- admin@devstudio.com / admin123
```

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React SPA     │───▶│   FastAPI       │───▶│  PostgreSQL     │
│   (Port 3000)   │    │   (Port 8000)   │    │   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Playwright E2E  │    │ GitHub Actions  │    │ BrowserStack    │
│    Testing      │    │    CI/CD        │    │  iOS Safari     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 📱 **Supported Platforms**

| Platform | Support | Tested |
|----------|---------|--------|
| **Chrome Desktop** | ✅ Full | Automated |
| **Firefox Desktop** | ✅ Full | Automated |
| **Safari Desktop** | ✅ Full | Automated |
| **Edge Desktop** | ✅ Full | Automated |
| **iOS Safari** | ✅ Full | BrowserStack |
| **iPad Safari** | ✅ Full | BrowserStack |
| **Chrome Mobile** | ✅ Full | Emulated |

## 🧪 **Testing**

### **Local Testing**
```bash
# Backend tests
pytest app/tests/ -v

# Frontend tests
cd frontend && npm test

# E2E tests (requires Playwright)
cd e2e-tests && npm install && npx playwright test
```

### **CI/CD Pipeline**
Tests automatically run on:
- Push to main/develop
- Pull requests
- Manual workflow dispatch

**Pipeline Duration:** 35-45 minutes (parallel execution)

## 📊 **Features**

### **Student Features**
- 🆕 **Fresh Student Onboarding** (JSON serialization fix implemented)
- 📅 **Session Booking System** (capacity management + waitlist)
- 🏃 **Project Enrollment** (with prerequisites)
- 📱 **Mobile-First Design** (iOS Safari optimized)
- 🎯 **Achievement System** (gamification)

### **Instructor Features**
- 📋 **Session Management** 
- 👥 **Student Progress Tracking**
- 📊 **Analytics Dashboard**
- 💬 **Messaging System**

### **Admin Features**
- 🔧 **System Configuration**
- 📈 **Reporting & Analytics**
- 👤 **User Management**
- 🔒 **Security Monitoring**

## ⚡ Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   cd practice_booking_system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and settings
   ```

5. **Initialize database**
   ```bash
   python init_db.py
   ```

6. **Start the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### 🎯 Default Admin Access

After initialization, you can log in with:
- **Email**: Use the admin account created during initialization
- **Password**: Check your `.env` file for the configured admin password

**⚠️ Important**: Always use secure credentials in production!

## 🔧 Configuration

### Environment Variables

Configure the following variables in your `.env` file:

```bash
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/practice_booking_system

# JWT Security
SECRET_KEY=your-super-secret-jwt-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application
APP_NAME="Practice Booking System"
DEBUG=True
API_V1_STR="/api/v1"

# Initial Admin (configure your admin credentials)
ADMIN_EMAIL=your-admin-email@company.com
ADMIN_PASSWORD=your-secure-admin-password
ADMIN_NAME=System Administrator

# Business Rules
MAX_BOOKINGS_PER_SEMESTER=10
BOOKING_DEADLINE_HOURS=24
```

### Database Setup

1. **Create PostgreSQL database**
   ```sql
   CREATE DATABASE practice_booking_system;
   CREATE USER your_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE practice_booking_system TO your_user;
   ```

2. **Run migrations** (if using Alembic)
   ```bash
   alembic upgrade head
   ```

## 📚 API Documentation

### Interactive Documentation

Once the application is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Authentication

The API uses JWT Bearer token authentication. Include the token in your requests:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:8000/api/v1/users/me
```

### API Endpoints Overview

#### 🔐 Authentication
```
POST   /api/v1/auth/login              # Login (get JWT tokens)
POST   /api/v1/auth/refresh            # Refresh access token
POST   /api/v1/auth/logout             # Logout
GET    /api/v1/auth/me                 # Get current user info
POST   /api/v1/auth/change-password    # Change password
```

#### 👥 User Management (Admin Only)
```
POST   /api/v1/users/                  # Create user
GET    /api/v1/users/                  # List users (with pagination)
GET    /api/v1/users/{id}              # Get user details
PATCH  /api/v1/users/{id}              # Update user
DELETE /api/v1/users/{id}              # Deactivate user
POST   /api/v1/users/{id}/reset-password # Reset user password
PATCH  /api/v1/users/me                # Update own profile
```

#### 📅 Semester Management
```
POST   /api/v1/semesters/              # Create semester (Admin)
GET    /api/v1/semesters/              # List semesters
GET    /api/v1/semesters/{id}          # Get semester details
PATCH  /api/v1/semesters/{id}          # Update semester (Admin)
DELETE /api/v1/semesters/{id}          # Delete semester (Admin)
```

#### 👥 Group Management
```
POST   /api/v1/groups/                 # Create group (Admin)
GET    /api/v1/groups/                 # List groups
GET    /api/v1/groups/{id}             # Get group details
PATCH  /api/v1/groups/{id}             # Update group (Admin)
DELETE /api/v1/groups/{id}             # Delete group (Admin)
POST   /api/v1/groups/{id}/users       # Add user to group (Admin)
DELETE /api/v1/groups/{id}/users/{user_id} # Remove user from group (Admin)
```

#### 🏫 Session Management
```
POST   /api/v1/sessions/               # Create session (Admin/Instructor)
GET    /api/v1/sessions/               # List sessions (with filters)
GET    /api/v1/sessions/{id}           # Get session details
PATCH  /api/v1/sessions/{id}           # Update session (Admin/Instructor)
DELETE /api/v1/sessions/{id}           # Delete session (Admin/Instructor)
```

#### 📝 Booking Management
```
POST   /api/v1/bookings/               # Create booking
GET    /api/v1/bookings/me             # Get own bookings
DELETE /api/v1/bookings/{id}           # Cancel own booking
GET    /api/v1/sessions/{id}/bookings  # Get session bookings (Admin/Instructor)
POST   /api/v1/bookings/{id}/confirm   # Confirm booking (Admin)
POST   /api/v1/bookings/{id}/cancel    # Cancel booking (Admin)
```

#### ✅ Attendance Tracking
```
POST   /api/v1/attendance/             # Create attendance record (Admin/Instructor)
GET    /api/v1/attendance/             # List attendance for session
POST   /api/v1/attendance/{booking_id}/checkin # Check in to session
PATCH  /api/v1/attendance/{id}         # Update attendance (Admin/Instructor)
```

#### ⭐ Feedback System
```
POST   /api/v1/feedback/               # Create feedback
GET    /api/v1/feedback/me             # Get own feedback
PATCH  /api/v1/feedback/{id}           # Update own feedback
DELETE /api/v1/feedback/{id}           # Delete own feedback
GET    /api/v1/sessions/{id}/feedback  # Get session feedback (Admin/Instructor)
GET    /api/v1/sessions/{id}/feedback/summary # Get feedback summary
```

#### 📊 Reporting
```
GET    /api/v1/reports/semester/{id}   # Semester report (Admin)
GET    /api/v1/reports/user/{id}       # User participation report (Admin)
GET    /api/v1/reports/export/sessions # Export sessions CSV (Admin)
```

## 👥 User Roles & Permissions

### 🔒 Permission Matrix

| Feature | Admin | Instructor | Student |
|---------|-------|------------|---------|
| User Management | ✅ Full | ❌ | ❌ |
| Semester Management | ✅ Full | ❌ | ❌ |
| Group Management | ✅ Full | ❌ | ❌ |
| Session Management | ✅ Full | ✅ Create/Edit | ❌ |
| Booking Management | ✅ Full | ✅ View/Manage | ✅ Own only |
| Attendance Tracking | ✅ Full | ✅ Sessions | ✅ Check-in only |
| Feedback Management | ✅ View All | ✅ View Sessions | ✅ Own only |
| Reporting | ✅ Full | ❌ | ❌ |

### 👤 User Role Descriptions

#### **Admin** 
- Complete system access
- User account management
- System configuration
- All reporting capabilities
- Data export functions

#### **Instructor**
- Session creation and management
- Booking oversight for their sessions
- Attendance tracking capabilities
- Feedback viewing for their sessions
- Limited to their assigned sessions

#### **Student**
- Session browsing and booking
- Attendance check-in
- Feedback submission
- Profile management
- Limited to their own data

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest app/tests/test_auth.py

# Run with verbose output
pytest -v
```

### Test Coverage

The project includes comprehensive testing:

- **Unit Tests**: Core functionality (auth, permissions, security)
- **Integration Tests**: API endpoints with database integration
- **End-to-End Tests**: Complete workflows across all user roles
- **Security Tests**: Permission boundaries and access control

**Test Results**: See `test_results.md` for detailed test documentation with 95+ test cases and 100% pass rate.

## 🚀 Production Deployment

### Docker Deployment (Recommended)

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Create docker-compose.yml**
   ```yaml
   version: '3.8'
   services:
     api:
       build: .
       ports:
         - "8000:8000"
       environment:
         - DATABASE_URL=postgresql://user:password@db:5432/practice_booking_system
       depends_on:
         - db
     
     db:
       image: postgres:13
       environment:
         - POSTGRES_DB=practice_booking_system
         - POSTGRES_USER=user
         - POSTGRES_PASSWORD=password
       volumes:
         - postgres_data:/var/lib/postgresql/data
   
   volumes:
     postgres_data:
   ```

3. **Deploy**
   ```bash
   docker-compose up -d
   ```

### Security Checklist for Production

- [ ] Change default admin credentials
- [ ] Use strong SECRET_KEY (generate with `openssl rand -hex 32`)
- [ ] Set DEBUG=False
- [ ] Configure HTTPS/TLS
- [ ] Set up proper CORS origins
- [ ] Configure database connection pooling
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy
- [ ] Set up rate limiting

### Environment Variables for Production

```bash
# Security
SECRET_KEY=your-production-secret-key-32-characters-minimum
DEBUG=False

# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# CORS (restrict to your frontend domain)
CORS_ORIGINS=["https://yourdomain.com"]
```

## 📊 Monitoring & Logging

### Health Checks

The API provides health check endpoints:

```bash
GET /health          # Basic health check
GET /              # API information
```

### Logging

Configure logging in production:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
```

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check PostgreSQL service
   sudo systemctl status postgresql
   
   # Verify connection string
   psql "postgresql://user:password@localhost:5432/database"
   ```

2. **JWT Token Issues**
   ```bash
   # Regenerate secret key
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **Permission Denied Errors**
   ```bash
   # Check user roles in database
   psql -d practice_booking_system -c "SELECT id, email, role FROM users;"
   ```

4. **Migration Issues**
   ```bash
   # Reset migrations (development only!)
   alembic downgrade base
   alembic upgrade head
   ```

### Debug Mode

Enable debug mode for development:

```bash
DEBUG=True uvicorn app.main:app --reload --log-level debug
```

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Standards

- Follow PEP 8 for Python code style
- Add type hints for all functions
- Write docstrings for public methods
- Maintain test coverage above 90%
- Use meaningful commit messages

## 📝 License

This project is proprietary software for internal company use.

## 📞 Support

For technical support or questions:

- **Documentation**: Check this README and `test_results.md`
- **API Documentation**: http://localhost:8000/docs
- **Issues**: Create an issue in the project repository

## 🔄 Changelog

### v1.0.0 (2024-08-19)

- ✅ Complete FastAPI backend implementation
- ✅ JWT authentication with role-based access control
- ✅ Comprehensive user management system
- ✅ Practice booking system with waitlists
- ✅ Attendance tracking functionality
- ✅ Feedback collection system
- ✅ Comprehensive reporting capabilities
- ✅ 95+ test cases with 100% pass rate
- ✅ Production-ready security features
- ✅ Complete API documentation

---

**🎯 Production Status**: ✅ **READY FOR DEPLOYMENT**

This system has been thoroughly tested and is ready for production use with proper security measures and comprehensive functionality as specified in the project requirements.