#!/usr/bin/env python3
"""
Master E2E Test Setup Script

This script:
1. Resets the database (drops all tables and recreates schema)
2. Seeds the database with test data from seed_data.json

Usage:
    DATABASE_URL="postgresql://..." python scripts/master_setup.py
"""

import sys
import subprocess
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings

def main():
    print("=" * 80)
    print("🚀 MASTER E2E TEST SETUP")
    print("=" * 80)
    print()

    # Prepare environment for subprocesses
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)

    # Step 1: Reset Database
    print("📊 STEP 1: Resetting Database...")
    print("─" * 80)
    reset_script = project_root / "scripts" / "reset_database_for_tests.py"

    try:
        subprocess.run(
            [sys.executable, str(reset_script)],
            check=True,
            cwd=project_root,
            env=env
        )
        print("✅ Database reset successful")
    except subprocess.CalledProcessError as e:
        print(f"❌ Database reset FAILED: {e}")
        sys.exit(1)

    print()

    # Step 2: Seed Database from seed_data.json (skip players - they will be created by Playwright registration tests)
    print("🌱 STEP 2: Seeding Database from seed_data.json...")
    print("─" * 80)
    seed_script = project_root / "scripts" / "seed_modular.py"

    try:
        subprocess.run(
            [sys.executable, str(seed_script), "--modules", "seed_data", "--skip-players"],
            check=True,
            cwd=project_root,
            env=env
        )
        print("✅ Database seeding successful")
    except subprocess.CalledProcessError as e:
        print(f"❌ Database seeding FAILED: {e}")
        sys.exit(1)

    print()
    print("=" * 80)
    print("🎉 MASTER SETUP COMPLETE!")
    print("=" * 80)
    print()
    print("✅ Database is ready for E2E tests")
    print(f"📊 Database: {settings.DATABASE_URL}")
    print()
    print("💡 Next steps:")
    print("   - Run Playwright tests: pytest tests/playwright/")
    print("   - Run E2E suite: ./tests/playwright/run_all_e2e_tests.sh")
    print()

if __name__ == "__main__":
    main()
