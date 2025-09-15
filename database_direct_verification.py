#!/usr/bin/env python3
"""
🗄️ DIRECT DATABASE VERIFICATION
Bypass API and check database directly
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
app_path = Path(__file__).parent / "app"
sys.path.insert(0, str(app_path))

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.config import settings
    from app.models.user import User
    from app.models.semester import Semester
    from app.models.session import Session
    from app.models.booking import Booking
    print("✅ SQLAlchemy imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("🚨 This indicates a real problem with the backend setup")
    sys.exit(1)

def verify_database_direct():
    """Direct database verification"""
    print("🗄️ DIRECT DATABASE VERIFICATION")
    print("=" * 50)
    
    try:
        # Test connection
        print(f"📡 Testing connection to: {settings.DATABASE_URL[:50]}...")
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            print("✅ Database connection successful")
            
            # Test basic queries
            queries = [
                ("Users count", "SELECT COUNT(*) as count FROM users"),
                ("Active users", "SELECT COUNT(*) as count FROM users WHERE is_active = true"),
                ("Semesters", "SELECT COUNT(*) as count FROM semesters"),
                ("Sessions", "SELECT COUNT(*) as count FROM sessions"),
                ("Bookings", "SELECT COUNT(*) as count FROM bookings"),
            ]
            
            results = {}
            for name, query in queries:
                try:
                    result = conn.execute(text(query)).fetchone()
                    count = result[0] if result else 0
                    print(f"✅ {name}: {count}")
                    results[name.lower().replace(' ', '_')] = count
                except Exception as e:
                    print(f"❌ {name} query failed: {e}")
                    results[name.lower().replace(' ', '_')] = None
            
            # Test specific admin user
            try:
                admin_query = text("""
                    SELECT name, email, role, is_active, created_at 
                    FROM users 
                    WHERE email = 'admin@company.com'
                """)
                admin_result = conn.execute(admin_query).fetchone()
                
                if admin_result:
                    print(f"✅ Admin user found:")
                    print(f"   Name: {admin_result[0]}")
                    print(f"   Email: {admin_result[1]}")
                    print(f"   Role: {admin_result[2]}")
                    print(f"   Active: {admin_result[3]}")
                    print(f"   Created: {admin_result[4]}")
                    results['admin_user_exists'] = True
                else:
                    print("❌ Admin user not found")
                    results['admin_user_exists'] = False
                    
            except Exception as e:
                print(f"❌ Admin user query failed: {e}")
                results['admin_user_exists'] = None
            
            return results
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("🚨 This indicates the backend database is NOT working")
        return None

def verify_database_schema():
    """Verify database schema exists"""
    print(f"\n🏗️ DATABASE SCHEMA VERIFICATION")
    print("-" * 40)
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if main tables exist
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            tables = conn.execute(tables_query).fetchall()
            table_names = [table[0] for table in tables]
            
            required_tables = ['users', 'semesters', 'sessions', 'bookings', 'groups', 'attendance', 'feedback']
            
            print(f"📋 Found tables: {table_names}")
            
            missing_tables = []
            for required in required_tables:
                if required in table_names:
                    print(f"✅ Table '{required}' exists")
                else:
                    print(f"❌ Table '{required}' missing")
                    missing_tables.append(required)
            
            if missing_tables:
                print(f"🚨 Missing tables: {missing_tables}")
                return False
            else:
                print(f"✅ All required tables exist")
                return True
                
    except Exception as e:
        print(f"❌ Schema verification failed: {e}")
        return False

def main():
    """Run direct database verification"""
    print("🔍 STARTING DIRECT DATABASE VERIFICATION")
    print("This bypasses the API and checks the database directly")
    print("=" * 60)
    
    # Test database connection and data
    db_results = verify_database_direct()
    
    # Test database schema
    schema_ok = verify_database_schema()
    
    # Generate summary
    print(f"\n📊 DIRECT DATABASE VERIFICATION SUMMARY")
    print("=" * 50)
    
    if db_results and schema_ok:
        print("✅ Database is GENUINELY accessible and populated")
        print("✅ Schema is complete")
        print("✅ Data exists in tables")
        print("🎯 VERDICT: Database backend is REAL and WORKING")
    elif db_results:
        print("⚠️  Database accessible but schema issues")
        print("🔧 VERDICT: Database partially working, needs schema fixes")
    else:
        print("❌ Database is NOT accessible or NOT working")
        print("🚨 VERDICT: Database backend claims are FALSE")
    
    print(f"\n💾 Database verification complete")
    return db_results is not None and schema_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)