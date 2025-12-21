#!/usr/bin/env python3
"""Reset Grand Master password to 'grandmaster123'"""

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
new_password = "grandmaster123"
password_hash = pwd_context.hash(new_password)

print(f"🔐 Resetting Grand Master password...")
print(f"   Email: grandmaster@lfa.com")
print(f"   New password: {new_password}")
print(f"   Hash: {password_hash[:30]}...")

# Update password
with engine.connect() as conn:
    result = conn.execute(
        text("UPDATE users SET password_hash = :hash WHERE email = 'grandmaster@lfa.com'"),
        {"hash": password_hash}
    )
    conn.commit()

    if result.rowcount > 0:
        print(f"✅ Password updated successfully")
    else:
        print(f"❌ User not found")
