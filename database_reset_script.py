#!/usr/bin/env python3
"""
Database Reset Script for DevStudio Academy
CRITICAL: Preserves admin users while cleaning all other data
"""

import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add app to path
sys.path.append('/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Invetsment - Internship/practice_booking_system')

from app.database import get_db
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.group import Group
from app.models.session import Session as SessionModel
from app.models.booking import Booking
from app.models.attendance import Attendance
from app.models.feedback import Feedback


def clean_database_except_admin(force=False):
    """Clean all data except admin users - CRITICAL SAFETY"""
    
    print("🔒 CRITICAL: Database reset starting...")
    print("⚠️  This will delete ALL data except admin users!")
    
    if not force:
        # Safety confirmation
        try:
            confirm = input("Type 'RESET DEVSTUDIO' to confirm: ")
            if confirm != 'RESET DEVSTUDIO':
                print("❌ Reset cancelled - safety confirmation failed")
                return False
        except EOFError:
            print("❌ Reset cancelled - no input provided")
            return False
    else:
        print("🤖 FORCE MODE: Skipping confirmation for automation")
    
    db = next(get_db())
    
    try:
        print("\n🔐 1. Backing up admin users...")
        admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
        print(f"   Found {len(admin_users)} admin user(s):")
        for admin in admin_users:
            print(f"   - {admin.name} ({admin.email})")
        
        if not admin_users:
            print("❌ ERROR: No admin users found! Aborting to prevent lockout.")
            return False
        
        print("\n🧹 2. Cleaning database (preserving admins)...")
        
        # Delete in correct order (foreign key constraints)
        print("   - Deleting feedback...")
        feedback_count = db.query(Feedback).count()
        db.query(Feedback).delete()
        print(f"     ✓ {feedback_count} feedback records deleted")
        
        print("   - Deleting attendance...")
        attendance_count = db.query(Attendance).count() 
        db.query(Attendance).delete()
        print(f"     ✓ {attendance_count} attendance records deleted")
        
        print("   - Deleting bookings...")
        booking_count = db.query(Booking).count()
        db.query(Booking).delete()
        print(f"     ✓ {booking_count} booking records deleted")
        
        print("   - Deleting sessions...")
        session_count = db.query(SessionModel).count()
        db.query(SessionModel).delete()
        print(f"     ✓ {session_count} session records deleted")
        
        print("   - Clearing group-user associations...")
        # Clear many-to-many associations first
        db.execute(text("DELETE FROM group_users"))
        print("     ✓ Group-user associations cleared")
        
        print("   - Deleting groups...")
        group_count = db.query(Group).count()
        db.query(Group).delete()
        print(f"     ✓ {group_count} group records deleted")
        
        print("   - Deleting semesters...")
        semester_count = db.query(Semester).count()
        db.query(Semester).delete() 
        print(f"     ✓ {semester_count} semester records deleted")
        
        print("   - Deleting non-admin users...")
        non_admin_count = db.query(User).filter(User.role != UserRole.ADMIN).count()
        db.query(User).filter(User.role != UserRole.ADMIN).delete()
        print(f"     ✓ {non_admin_count} non-admin users deleted")
        
        print("\n💾 3. Committing changes...")
        db.commit()
        
        print("\n✅ Database cleaned successfully!")
        print("🔐 Admin users preserved:")
        remaining_admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
        for admin in remaining_admins:
            print(f"   - {admin.name} ({admin.email})")
            
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR during database reset: {e}")
        db.rollback()
        print("🔄 Database rolled back - no changes made")
        return False
        
    finally:
        db.close()


def verify_clean_state():
    """Verify database is in clean state"""
    db = next(get_db())
    
    try:
        print("\n📊 Database state after cleaning:")
        
        counts = {
            'Users': db.query(User).count(),
            'Admins': db.query(User).filter(User.role == UserRole.ADMIN).count(),
            'Semesters': db.query(Semester).count(),
            'Groups': db.query(Group).count(), 
            'Sessions': db.query(SessionModel).count(),
            'Bookings': db.query(Booking).count(),
            'Attendance': db.query(Attendance).count(),
            'Feedback': db.query(Feedback).count()
        }
        
        for table, count in counts.items():
            print(f"   {table}: {count}")
            
        # Verify only admins remain
        if counts['Users'] == counts['Admins'] and counts['Admins'] > 0:
            print("\n✅ Clean state verified - only admin users remain")
            return True
        else:
            print("\n❌ Clean state verification failed!")
            return False
            
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("🏗️  DevStudio Academy Database Reset")
    print("=" * 60)
    
    # Check for force flag
    import sys
    force_reset = '--force' in sys.argv or '-f' in sys.argv
    
    if clean_database_except_admin(force=force_reset):
        if verify_clean_state():
            print("\n🎯 Ready for DevStudio Academy data generation!")
        else:
            print("\n⚠️  Clean state verification failed - check database")
    else:
        print("\n🛑 Database reset failed - check errors above")