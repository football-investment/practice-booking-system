#!/usr/bin/env python3
"""
Database initialization script
Creates tables and initial admin user
"""
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import create_database
from app.core.init_admin import create_initial_admin

def main():
    print("Initializing database...")
    
    try:
        # Create all tables
        create_database()
        print("✓ Database tables created successfully")
        
        # Create initial admin user
        create_initial_admin()
        print("✓ Initial admin user created successfully")
        
        print("\nDatabase initialization completed!")
        print("You can now start the application with: uvicorn app.main:app --reload")
        
    except Exception as e:
        print(f"❌ Error during database initialization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()