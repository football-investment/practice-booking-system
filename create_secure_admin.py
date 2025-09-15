#!/usr/bin/env python3
"""
🔒 SECURE ADMIN USER CREATION
Creates admin user from environment variables ONLY
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.models.user import User, UserRole
    from app.database import engine, SessionLocal
    from app.core.security import get_password_hash
except ImportError:
    logger.error("Cannot import app modules. Run from project root.")
    sys.exit(1)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def main():
    # Get credentials from environment
    admin_email = os.getenv('ADMIN_EMAIL')
    admin_password = os.getenv('ADMIN_PASSWORD')
    admin_name = os.getenv('ADMIN_NAME', 'System Administrator')
    
    if not admin_email or not admin_password:
        logger.error("❌ ADMIN_EMAIL and ADMIN_PASSWORD must be set in environment")
        sys.exit(1)
    
    if len(admin_password) < 8:
        logger.error("❌ Admin password must be at least 8 characters")
        sys.exit(1)
    
    logger.info(f"🔒 Creating admin user: {admin_email}")
    
    try:
        with SessionLocal() as db:
            # Check existing admin
            existing = db.query(User).filter(User.email == admin_email).first()
            
            if existing:
                logger.info("⚠️ Admin exists, updating password...")
                existing.password_hash = get_password_hash(admin_password)
                existing.role = UserRole.ADMIN
                existing.is_active = True
            else:
                logger.info("🆕 Creating new admin user...")
                admin_user = User(
                    email=admin_email,
                    name=admin_name,
                    password_hash=get_password_hash(admin_password),
                    role=UserRole.ADMIN,
                    is_active=True
                )
                db.add(admin_user)
            
            db.commit()
            
            # Verify
            admin = db.query(User).filter(User.email == admin_email).first()
            if admin and admin.role == UserRole.ADMIN:
                logger.info("✅ Admin user created/updated successfully!")
                logger.info(f"   ID: {admin.id}")
                logger.info(f"   Email: {admin.email}")
                logger.info(f"   Role: {admin.role}")
            else:
                logger.error("❌ Admin verification failed!")
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()