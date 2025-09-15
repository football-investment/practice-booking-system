#!/usr/bin/env python3
"""
Database Cleanup Script
=======================

This script safely removes test data from the database while preserving:
- All admin accounts
- Essential system data (semesters, etc.)
- Database structure

⚠️  IMPORTANT: This will create a backup before cleanup!

Run with: python database_cleanup.py
"""

import os
import subprocess
import datetime
from typing import List

def create_backup() -> str:
    """Create a database backup before cleanup"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"practice_booking_system_backup_{timestamp}.sql"
    backup_path = os.path.join(os.getcwd(), "backups", backup_filename)
    
    # Create backups directory if it doesn't exist
    os.makedirs("backups", exist_ok=True)
    
    print(f"🔄 Creating database backup: {backup_filename}")
    
    cmd = [
        "pg_dump",
        "-h", "localhost",
        "-U", "lovas.zoltan",
        "-d", "practice_booking_system",
        "-f", backup_path,
        "--no-password"
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Backup created successfully: {backup_path}")
        return backup_path
    except subprocess.CalledProcessError as e:
        print(f"❌ Backup failed: {e}")
        print(f"Error output: {e.stderr}")
        raise

def get_admin_users() -> List[int]:
    """Get list of admin user IDs to preserve"""
    cmd = [
        "psql", "-h", "localhost", "-U", "lovas.zoltan", 
        "-d", "practice_booking_system", "-t", "-c",
        "SELECT id FROM users WHERE role = 'ADMIN';"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    admin_ids = [int(line.strip()) for line in result.stdout.strip().split('\n') if line.strip()]
    
    print(f"🔒 Found {len(admin_ids)} admin users to preserve: {admin_ids}")
    return admin_ids

def execute_sql(sql: str) -> None:
    """Execute SQL command safely"""
    cmd = [
        "psql", "-h", "localhost", "-U", "lovas.zoltan", 
        "-d", "practice_booking_system", "-c", sql
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Executed: {sql[:100]}...")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to execute: {sql[:100]}...")
        print(f"Error: {e.stderr}")
        raise

def cleanup_database(admin_ids: List[int]) -> None:
    """Clean up test data while preserving admin accounts"""
    
    print("\n🧹 Starting database cleanup...")
    
    # Convert admin IDs to string for SQL
    admin_ids_str = ','.join(map(str, admin_ids))
    
    # 1. Delete quiz-related data
    print("📝 Cleaning quiz data...")
    execute_sql("DELETE FROM quiz_user_answers;")
    execute_sql("DELETE FROM quiz_attempts;")
    execute_sql("DELETE FROM quiz_answer_options;")
    execute_sql("DELETE FROM quiz_questions;")
    execute_sql("DELETE FROM quizzes;")
    
    # 2. Delete user-related data (except admins)
    print("👥 Cleaning user-related data...")
    execute_sql("DELETE FROM user_achievements;")
    execute_sql("DELETE FROM user_stats;")
    execute_sql("DELETE FROM notifications;")
    execute_sql("DELETE FROM feedback;")
    execute_sql("DELETE FROM attendance;")
    
    # 3. Delete bookings and sessions
    print("📅 Cleaning sessions and bookings...")
    execute_sql("DELETE FROM bookings;")
    execute_sql("DELETE FROM sessions;")
    
    # 4. Delete project-related data
    print("📁 Cleaning project data...")
    execute_sql("DELETE FROM project_milestone_progress;")
    execute_sql("DELETE FROM project_sessions;")
    execute_sql("DELETE FROM project_enrollments;")
    execute_sql("DELETE FROM project_milestones;")
    execute_sql("DELETE FROM projects;")
    
    # 5. Delete groups
    print("👥 Cleaning group data...")
    execute_sql("DELETE FROM group_users;")
    execute_sql("DELETE FROM groups;")
    
    # 6. Delete non-admin users
    print("🗑️  Removing test users (preserving admins)...")
    execute_sql(f"DELETE FROM users WHERE role != 'ADMIN' AND id NOT IN ({admin_ids_str});")
    
    print("✅ Database cleanup completed!")

def verify_cleanup(admin_ids: List[int]) -> None:
    """Verify that cleanup was successful"""
    print("\n🔍 Verifying cleanup...")
    
    # Check remaining users
    cmd = [
        "psql", "-h", "localhost", "-U", "lovas.zoltan", 
        "-d", "practice_booking_system", "-c",
        "SELECT role, COUNT(*) FROM users GROUP BY role;"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    print("👥 Remaining users by role:")
    print(result.stdout)
    
    # Check if any test data remains
    tables_to_check = [
        "bookings", "sessions", "projects", "quizzes", 
        "quiz_attempts", "feedback", "notifications"
    ]
    
    for table in tables_to_check:
        cmd = [
            "psql", "-h", "localhost", "-U", "lovas.zoltan", 
            "-d", "practice_booking_system", "-t", "-c",
            f"SELECT COUNT(*) FROM {table};"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        count = int(result.stdout.strip())
        status = "✅" if count == 0 else "⚠️ "
        print(f"{status} {table}: {count} records")

def main():
    """Main cleanup process"""
    print("🚀 PRACTICE BOOKING SYSTEM - DATABASE CLEANUP")
    print("=" * 50)
    
    try:
        # Step 1: Create backup
        backup_path = create_backup()
        
        # Step 2: Get admin users to preserve
        admin_ids = get_admin_users()
        
        if not admin_ids:
            print("❌ No admin users found! Aborting cleanup for safety.")
            return
        
        # Step 3: Confirm cleanup
        print(f"\n⚠️  WARNING: This will delete ALL test data!")
        print(f"📁 Backup saved: {backup_path}")
        print(f"🔒 Preserving {len(admin_ids)} admin users")
        
        confirm = input("\nDo you want to proceed? (type 'YES' to confirm): ")
        if confirm != 'YES':
            print("❌ Cleanup cancelled by user.")
            return
        
        # Step 4: Execute cleanup
        cleanup_database(admin_ids)
        
        # Step 5: Verify results
        verify_cleanup(admin_ids)
        
        print(f"\n🎉 Database cleanup completed successfully!")
        print(f"📁 Backup available at: {backup_path}")
        
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        print("💡 Your database backup is safe and can be restored if needed.")
        return 1

if __name__ == "__main__":
    main()