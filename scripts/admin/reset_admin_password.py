#!/usr/bin/env python3
"""Reset Admin password to 'adminpassword'"""

import os
import sys
from sqlalchemy import create_engine, text
from passlib.context import CryptContext

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
engine = create_engine(DATABASE_URL)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash password
new_password = "adminpassword"
password_hash = pwd_context.hash(new_password)

print(f"🔐 Resetting Admin password...")
print(f"   Email: admin@lfa.com")
print(f"   New password: {new_password}")
print(f"   Hash: {password_hash[:30]}...")

# Update password
with engine.connect() as conn:
    result = conn.execute(
        text("UPDATE users SET password_hash = :hash WHERE email = 'admin@lfa.com'"),
        {"hash": password_hash}
    )
    conn.commit()

    if result.rowcount > 0:
        print(f"✅ Password updated successfully")
        print(f"   You can now login with:")
        print(f"   Email: admin@lfa.com")
        print(f"   Password: adminpassword")
    else:
        print(f"❌ User not found")
