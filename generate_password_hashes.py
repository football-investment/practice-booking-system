#!/usr/bin/env python3
"""
🔐 LFA Password Hash Generator
Generate secure password hashes for futballista test accounts
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.security import get_password_hash

def generate_lfa_password_hashes():
    """Generate password hashes for all LFA test accounts"""
    
    password = "FootballMaster2025!"
    hash_value = get_password_hash(password)
    
    print("🔐 LFA Test Account Password Hashes")
    print("=" * 50)
    print(f"Password: {password}")
    print(f"Hash: {hash_value}")
    print("")
    print("📝 Use this hash in SQL INSERT statements:")
    print(f"    password_hash = '{hash_value}'")
    print("")
    print("👥 This hash will work for all 9 futballista accounts:")
    print("   • Lionel Messi (messi@lfa.test)")
    print("   • Cristiano Ronaldo (ronaldo@lfa.test)")
    print("   • Neymar Jr. (neymar@lfa.test)")
    print("   • Kylian Mbappé (mbappe@lfa.test)")
    print("   • Pep Guardiola (guardiola@lfa.test)")
    print("   • Carlo Ancelotti (ancelotti@lfa.test)")
    print("   • Jürgen Klopp (klopp@lfa.test)")
    print("   • Diego Maradona (maradona@lfa.test)")
    print("   • Pelé (pele@lfa.test)")
    print("")
    print("🚀 Ready for seed data creation!")

if __name__ == "__main__":
    generate_lfa_password_hashes()