"""
Test Semester Generation System
================================
Tests the automatic semester generation for different specializations and age groups.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Admin credentials
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"


def login_admin():
    """Login as admin and get access token"""
    print("🔐 Logging in as admin...")
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ Login successful!")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None


def get_available_templates(token):
    """Get list of available semester templates"""
    print("\n📋 Fetching available templates...")
    response = requests.get(
        f"{BASE_URL}/api/v1/admin/semesters/available-templates",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        templates = response.json()["available_templates"]
        print(f"✅ Found {len(templates)} templates:")
        for t in templates:
            print(f"  - {t['specialization']} / {t['age_group']}: "
                  f"{t['cycle_type']} ({t['semester_count']} semesters/year)")
        return templates
    else:
        print(f"❌ Failed to fetch templates: {response.status_code}")
        print(response.text)
        return []


def generate_semesters(token, year, specialization, age_group):
    """Generate semesters for a specific year, specialization, and age group"""
    print(f"\n🚀 Generating semesters for {year}/{specialization}/{age_group}...")

    response = requests.post(
        f"{BASE_URL}/api/v1/admin/semesters/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "year": year,
            "specialization": specialization,
            "age_group": age_group
        }
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['message']}")
        print(f"📅 Generated {result['generated_count']} semesters:")
        for sem in result["semesters"]:
            print(f"\n  📌 {sem['code']}")
            print(f"     Name: {sem['name']}")
            print(f"     Theme: {sem['theme']}")
            print(f"     Focus: {sem['focus_description']}")
            print(f"     Period: {sem['start_date']} to {sem['end_date']}")
        return result
    else:
        print(f"❌ Failed to generate semesters: {response.status_code}")
        print(response.text)
        return None


def main():
    """Main test function"""
    print("="*80)
    print("SEMESTER GENERATION SYSTEM TEST")
    print("="*80)

    # Login
    token = login_admin()
    if not token:
        return

    # Get available templates
    templates = get_available_templates(token)

    # Test generation for each LFA_PLAYER age group
    year = 2025

    print("\n" + "="*80)
    print(f"TESTING SEMESTER GENERATION FOR {year}")
    print("="*80)

    test_cases = [
        ("LFA_PLAYER", "PRE", "Monthly (12 semesters)"),
        ("LFA_PLAYER", "YOUTH", "Quarterly (4 semesters)"),
        ("LFA_PLAYER", "AMATEUR", "Semi-annual (2 semesters)"),
        ("LFA_PLAYER", "PRO", "Annual (1 semester)")
    ]

    for spec, age_group, description in test_cases:
        print(f"\n{'='*80}")
        print(f"TEST: {spec} / {age_group} - {description}")
        print(f"{'='*80}")

        result = generate_semesters(token, year, spec, age_group)

        if result:
            print(f"\n✅ SUCCESS: Generated {result['generated_count']} semesters")
        else:
            print(f"\n❌ FAILED: Could not generate semesters")

    print("\n" + "="*80)
    print("TEST COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    main()
