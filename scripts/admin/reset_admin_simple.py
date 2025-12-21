#!/usr/bin/env python3
"""Reset Admin password using app's security module"""

import os
import sys

# Set up path
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from app.core.security import get_password_hash

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
engine = create_engine(DATABASE_URL)

# Hash password using app's security module
new_password = "adminpassword"
password_hash = get_password_hash(new_password)

print(f"🔐 Resetting Admin password...")
print(f"   Email: admin@lfa.com")
print(f"   New password: {new_password}")

# Update password
with engine.connect() as conn:
    result = conn.execute(
        text("UPDATE users SET password_hash = :hash WHERE email = 'admin@lfa.com'"),
        {"hash": password_hash}
    )
    conn.commit()

    if result.rowcount > 0:
        print(f"✅ Password updated successfully")
        print(f"\n   Login credentials:")
        print(f"   Email: admin@lfa.com")
        print(f"   Password: adminpassword")
    else:
        print(f"❌ User not found")
