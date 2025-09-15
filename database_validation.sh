#!/bin/bash

# Database validation - queries to verify system state

echo "🗄️  DATABASE STATE VALIDATION"
echo "=============================="

# Try to connect to the database using different methods
# Method 1: Using Python to connect via the app

echo "1. DATABASE CONNECTION TEST:"
echo "---------------------------"

python3 -c "
import sys
sys.path.append('.')
try:
    from app.database import SessionLocal
    from app.models.user import User
    from app.models.semester import Semester
    from app.models.session import Session
    from app.models.booking import Booking
    
    db = SessionLocal()
    
    # Basic counts
    users = db.query(User).count()
    semesters = db.query(Semester).count() 
    sessions = db.query(Session).count()
    bookings = db.query(Booking).count()
    
    print(f'✅ Database connection successful')
    print(f'📊 Current database state:')
    print(f'   Users: {users}')
    print(f'   Semesters: {semesters}') 
    print(f'   Sessions: {sessions}')
    print(f'   Bookings: {bookings}')
    
    # User roles breakdown
    from app.models.user import UserRole
    admins = db.query(User).filter(User.role == UserRole.ADMIN).count()
    instructors = db.query(User).filter(User.role == UserRole.INSTRUCTOR).count()
    students = db.query(User).filter(User.role == UserRole.STUDENT).count()
    
    print(f'📋 User roles:')
    print(f'   Admins: {admins}')
    print(f'   Instructors: {instructors}')
    print(f'   Students: {students}')
    
    # Active vs inactive users
    active_users = db.query(User).filter(User.is_active == True).count()
    inactive_users = db.query(User).filter(User.is_active == False).count()
    
    print(f'👥 User status:')
    print(f'   Active: {active_users}')
    print(f'   Inactive: {inactive_users}')
    
    db.close()
    
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
"

echo ""
echo "2. RECENT ACTIVITY CHECK:"
echo "------------------------"

python3 -c "
import sys
sys.path.append('.')
try:
    from app.database import SessionLocal
    from app.models.user import User
    from app.models.booking import Booking
    from app.models.feedback import Feedback
    from app.models.attendance import Attendance
    from datetime import datetime, timedelta
    
    db = SessionLocal()
    
    # Recent activity (last 24 hours)
    recent_time = datetime.utcnow() - timedelta(hours=24)
    
    recent_users = db.query(User).filter(User.created_at >= recent_time).count()
    recent_bookings = db.query(Booking).filter(Booking.created_at >= recent_time).count()
    recent_feedback = db.query(Feedback).filter(Feedback.created_at >= recent_time).count()
    recent_attendance = db.query(Attendance).filter(Attendance.created_at >= recent_time).count()
    
    print(f'🕐 Activity in last 24 hours:')
    print(f'   New users: {recent_users}')
    print(f'   New bookings: {recent_bookings}')
    print(f'   New feedback: {recent_feedback}')
    print(f'   New attendance: {recent_attendance}')
    
    # Booking statuses
    from app.models.booking import BookingStatus
    confirmed = db.query(Booking).filter(Booking.status == BookingStatus.CONFIRMED).count()
    pending = db.query(Booking).filter(Booking.status == BookingStatus.PENDING).count()
    waitlisted = db.query(Booking).filter(Booking.status == BookingStatus.WAITLISTED).count()
    cancelled = db.query(Booking).filter(Booking.status == BookingStatus.CANCELLED).count()
    
    print(f'📝 Booking statuses:')
    print(f'   Confirmed: {confirmed}')
    print(f'   Pending: {pending}')
    print(f'   Waitlisted: {waitlisted}')
    print(f'   Cancelled: {cancelled}')
    
    db.close()
    
except Exception as e:
    print(f'❌ Recent activity check failed: {e}')
"

echo ""
echo "3. DATA INTEGRITY CHECK:"
echo "------------------------"

python3 -c "
import sys
sys.path.append('.')
try:
    from app.database import SessionLocal
    from app.models.user import User
    from app.models.session import Session
    from app.models.booking import Booking
    from app.models.attendance import Attendance
    from app.models.feedback import Feedback
    
    db = SessionLocal()
    
    # Check for orphaned records
    bookings_without_user = db.query(Booking).outerjoin(User).filter(User.id == None).count()
    bookings_without_session = db.query(Booking).outerjoin(Session).filter(Session.id == None).count()
    attendance_without_booking = db.query(Attendance).outerjoin(Booking).filter(Booking.id == None).count()
    feedback_without_session = db.query(Feedback).outerjoin(Session).filter(Session.id == None).count()
    
    print(f'🔍 Data integrity check:')
    print(f'   Bookings without user: {bookings_without_user}')
    print(f'   Bookings without session: {bookings_without_session}')
    print(f'   Attendance without booking: {attendance_without_booking}')
    print(f'   Feedback without session: {feedback_without_session}')
    
    total_issues = bookings_without_user + bookings_without_session + attendance_without_booking + feedback_without_session
    
    if total_issues == 0:
        print('✅ Data integrity: Perfect')
    else:
        print(f'⚠️  Data integrity issues found: {total_issues}')
    
    db.close()
    
except Exception as e:
    print(f'❌ Data integrity check failed: {e}')
"

echo ""
echo "4. ADMIN USER VERIFICATION:"
echo "---------------------------"

python3 -c "
import sys
sys.path.append('.')
try:
    from app.database import SessionLocal
    from app.models.user import User, UserRole
    from app.core.security import verify_password
    
    db = SessionLocal()
    
    admin_user = db.query(User).filter(
        User.email == 'admin@company.com',
        User.role == UserRole.ADMIN
    ).first()
    
    if admin_user:
        print(f'✅ Admin user exists:')
        print(f'   Name: {admin_user.name}')
        print(f'   Email: {admin_user.email}')
        print(f'   Active: {admin_user.is_active}')
        print(f'   Created: {admin_user.created_at}')
        
        # Test admin password
        if verify_password('admin123', admin_user.password_hash):
            print('✅ Admin password is correct')
        else:
            print('❌ Admin password verification failed')
    else:
        print('❌ Admin user not found!')
        
    db.close()
    
except Exception as e:
    print(f'❌ Admin verification failed: {e}')
"

echo ""
echo "5. SAMPLE DATA QUERY:"
echo "--------------------"

python3 -c "
import sys
sys.path.append('.')
try:
    from app.database import SessionLocal
    from app.models.user import User
    from app.models.semester import Semester
    from app.models.session import Session
    
    db = SessionLocal()
    
    # Show some actual data
    print('📋 Sample data from database:')
    print()
    
    print('Users (first 5):')
    users = db.query(User).limit(5).all()
    for user in users:
        print(f'   {user.id}: {user.name} ({user.email}) - {user.role.value}')
    
    print()
    print('Semesters:')
    semesters = db.query(Semester).limit(3).all()
    for semester in semesters:
        print(f'   {semester.id}: {semester.code} - {semester.name}')
        
    print()
    print('Sessions (first 3):')
    sessions = db.query(Session).limit(3).all()
    for session in sessions:
        print(f'   {session.id}: {session.title} ({session.mode.value}) - Capacity: {session.capacity}')
    
    db.close()
    
except Exception as e:
    print(f'❌ Sample data query failed: {e}')
"

echo ""
echo "=============================="
echo "Database validation complete!"
echo "=============================="